"""Atomic content-checked graphs, checkpoints and result envelopes.

No pickle is loaded. An abandoned output lock is never stolen automatically.
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import fields
from contextlib import contextmanager
import hashlib,json,os,shutil,socket,tempfile,time,uuid
import numpy as np
from .basis import Graph

SCHEMA='lri-coeff-v1'
def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(obj):return hashlib.sha256(canonical(obj)).hexdigest()
def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(2**20),b''):h.update(block)
    return h.hexdigest()
def source_digest():
    base=Path(__file__).parent
    return digest({p.name:file_sha(p) for p in sorted(base.iterdir()) if p.suffix in ('.py','.cpp')})
def atomic_json(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(canonical(obj)+b'\n');f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
        try:
            d=os.open(path.parent,os.O_RDONLY);os.fsync(d);os.close(d)
        except OSError:pass
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def envelope(payload):return {'schema':SCHEMA,'payload':payload,'sha256':digest(payload)}
def read_envelope(path):
    a=json.loads(Path(path).read_text())
    if a.get('schema')!=SCHEMA or digest(a['payload'])!=a.get('sha256'):raise ValueError(f'Invalid result/checkpoint checksum: {path}')
    return a['payload']

@contextmanager
def output_lock(output,identity):
    lock=Path(str(output)+'.lock');lock.parent.mkdir(parents=True,exist_ok=True)
    try:lock.mkdir()
    except FileExistsError:raise FileExistsError(f'Output is claimed: {lock}. No automatic stale-lock recovery; verify the old job has terminated before manual removal.')
    token=uuid.uuid4().hex
    owner=dict(token=token,identity=identity,host=socket.gethostname(),pid=os.getpid(),created=time.time(),slurm_job=os.environ.get('SLURM_JOB_ID'),slurm_task=os.environ.get('SLURM_ARRAY_TASK_ID'))
    atomic_json(lock/'owner.json',owner)
    try:yield token
    finally:
        try:
            if json.loads((lock/'owner.json').read_text())['token']==token:
                (lock/'owner.json').unlink();lock.rmdir()
        except (OSError,ValueError,KeyError):pass

def graph_key(L,degree,pmax):
    return digest(dict(L=L,degree=degree,pmax=pmax,builder=file_sha(Path(__file__).with_name('basis.py'))))
def cached_graph(cache,L,degree,pmax,max_states,max_bytes):
    if cache is None:return Graph.build(L,degree,pmax,max_states,max_bytes),False
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True);key=graph_key(L,degree,pmax);dest=cache/key
    if dest.exists():
        meta=read_envelope(dest/'graph.json')
        if meta['key']!=key:raise ValueError('Graph cache identity mismatch')
        vals=meta['scalars'].copy()
        for name,rec in meta['arrays'].items():
            p=dest/(name+'.npy')
            if file_sha(p)!=rec['sha256']:raise ValueError('Corrupt graph cache: '+name)
            ar=np.load(p,mmap_mode='r',allow_pickle=False)
            if list(ar.shape)!=rec['shape'] or str(ar.dtype)!=rec['dtype']:raise ValueError('Graph cache array metadata mismatch')
            vals[name]=ar
        g=Graph(**vals)
        if g.n>max_states or g.nbytes>max_bytes:raise MemoryError('Cached graph exceeds requested guard')
        return g,True
    g=Graph.build(L,degree,pmax,max_states,max_bytes)
    tmp=Path(tempfile.mkdtemp(prefix='building-',dir=cache))
    try:
        vals={};arrays={}
        for field in fields(Graph):
            name=field.name;v=getattr(g,name)
            if isinstance(v,np.ndarray):
                p=tmp/(name+'.npy');np.save(p,v,allow_pickle=False)
                arrays[name]=dict(sha256=file_sha(p),shape=list(v.shape),dtype=str(v.dtype))
            else:vals[name]=v
        atomic_json(tmp/'graph.json',envelope(dict(key=key,scalars=vals,arrays=arrays)))
        try:os.rename(tmp,dest)
        except OSError:
            if not dest.exists():raise
    finally:
        if tmp.exists():shutil.rmtree(tmp)
    return g,False

CK_ARRAYS=('mm','mv','norms','mf','me')
def save_checkpoint(engine,root,identity):
    root=Path(root)/identity;root.mkdir(parents=True,exist_ok=True)
    gen='generation-'+uuid.uuid4().hex;tmp=root/(gen+'.partial');tmp.mkdir();dest=root/gen
    files={}
    def store(name,a):
        p=tmp/(name+'.npy');np.save(p,a,allow_pickle=False)
        files[name]=dict(sha256=file_sha(p),shape=list(a.shape),dtype=str(a.dtype))
    try:
        for name in ('r','g','E'):store(name,getattr(engine,name))
        for i,c in enumerate(engine.channels):
            store(f'psi_{i}',c.psi)
            for name in CK_ARRAYS:
                a=getattr(c,name)
                if a is not None:store(f'{name}_{i}',a)
        meta=dict(identity=identity,completed_order=engine.completed_order,moments_done=engine.moments_done,upper_done=engine.upper_done,files=files,timings=engine.stats)
        atomic_json(tmp/'metadata.json',envelope(meta));os.rename(tmp,dest)
        previous=None
        if (root/'latest.json').exists():previous=read_envelope(root/'latest.json')['generation']
        atomic_json(root/'latest.json',envelope(dict(identity=identity,generation=gen)))
        # Keep current + one predecessor. Unpublished partial generations are
        # harmless; clean them only offline after the jobs have stopped.
        for p in root.glob('generation-*'):
            if p.is_dir() and not p.name.endswith('.partial') and p.name not in (gen,previous):shutil.rmtree(p)
        return dest
    except BaseException:
        # The last published generation remains valid.
        if tmp.exists():shutil.rmtree(tmp)
        raise

def load_checkpoint(engine,root,identity):
    root=Path(root)/identity
    if not (root/'latest.json').exists():return False
    latest=read_envelope(root/'latest.json')
    gen=latest['generation']
    if latest['identity']!=identity or Path(gen).name!=gen:raise ValueError('Checkpoint identity/path mismatch')
    directory=root/gen;meta=read_envelope(directory/'metadata.json')
    if meta['identity']!=identity:raise ValueError('Checkpoint identity mismatch')
    arrays={}
    for name,rec in meta['files'].items():
        if Path(name).name!=name:raise ValueError('Unsafe checkpoint array name')
        p=directory/(name+'.npy')
        if file_sha(p)!=rec['sha256']:raise ValueError('Corrupt checkpoint '+name)
        a=np.load(p,allow_pickle=False)
        if list(a.shape)!=rec['shape'] or str(a.dtype)!=rec['dtype'] or not np.all(np.isfinite(a)):raise ValueError('Invalid checkpoint '+name)
        arrays[name]=a
    for name in ('r','g','E'):
        if arrays[name].shape!=getattr(engine,name).shape:raise ValueError('Checkpoint shape mismatch')
        getattr(engine,name)[:]=arrays[name]
    for i,c in enumerate(engine.channels):
        if arrays[f'psi_{i}'].shape!=c.psi.shape:raise ValueError('Wavefunction checkpoint shape mismatch')
        c.psi[:]=arrays[f'psi_{i}']
        for name in CK_ARRAYS:
            if f'{name}_{i}' in arrays:setattr(c,name,arrays[f'{name}_{i}'])
    engine.completed_order=meta['completed_order'];engine.moments_done=meta['moments_done'];engine.upper_done=meta['upper_done'];engine.stats=meta['timings']
    if not 0<=engine.completed_order<=engine.h or not 0<=engine.moments_done<=len(engine.channels) or not engine.h<=engine.upper_done<=engine.d:raise ValueError('Invalid checkpoint stage')
    return True
