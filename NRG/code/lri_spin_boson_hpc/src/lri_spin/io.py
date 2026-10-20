"""Crash-safe numerical records. No pickle. Locks are owned by the solver process."""
from __future__ import annotations
import contextlib,fcntl,hashlib,json,os,platform,tempfile
from pathlib import Path
import numpy as np
import scipy
from threadpoolctl import threadpool_info

class Interrupted(RuntimeError):pass
class IntegrityError(RuntimeError):pass
class AlreadyRunning(RuntimeError):pass

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def source_hash():
    h=hashlib.sha256();root=Path(__file__).resolve().parent
    for p in sorted(root.glob('*.py')):
        h.update(p.name.encode());h.update(p.read_bytes())
    return h.hexdigest()

def identity(cfg,alpha,kind,backend='dense',sector_workers=1,**extras):
    libs=[]
    for d in threadpool_info():
        libs.append({k:d.get(k) for k in ('internal_api','prefix','version','architecture','threading_layer')})
    libs.sort(key=lambda d:json.dumps(d,sort_keys=True))
    return {'schema':1,'source_sha256':source_hash(),'config':cfg.asdict(),'alpha':alpha,
            'kind':kind,'backend':backend,'sector_workers':sector_workers,'extras':extras,
            'runtime':{'python':platform.python_version(),'numpy':np.__version__,
                       'scipy':scipy.__version__,'machine':platform.machine(),'blas':libs}}

def _atomic(path,writer,binary=True):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb' if binary else 'w') as f:
            writer(f);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
        # fsync containing directory so rename is durable where filesystem supports it.
        dfd=os.open(path.parent,os.O_DIRECTORY)
        try:os.fsync(dfd)
        finally:os.close(dfd)
    finally:
        if os.path.exists(name):os.unlink(name)

def write_record(path,ident,payload):
    body={'identity':ident,'payload':payload};blob={'sha256':hashlib.sha256(canonical(body)).hexdigest(),**body}
    _atomic(path,lambda f:f.write(json.dumps(blob,indent=2,allow_nan=False).encode()+b'\n'))

def read_record(path,ident=None):
    d=json.loads(Path(path).read_text())
    if not isinstance(d,dict) or set(d)!= {'sha256','identity','payload'}:
        raise IntegrityError('Not a versioned result record')
    body={k:d[k] for k in ('identity','payload')}
    if hashlib.sha256(canonical(body)).hexdigest()!=d['sha256']:raise IntegrityError('Result checksum mismatch')
    if ident is not None and canonical(d['identity'])!=canonical(ident):raise IntegrityError('Source/config/runtime mismatch')
    return d['payload']

def _arr_hash(a):
    return hashlib.sha256(str(a.dtype).encode()+canonical(list(a.shape))+a.tobytes(order='C')).hexdigest()

def save_state(path,ident,state):
    arrays={k:np.ascontiguousarray(v) for k,v in state.items() if k!='meta'}
    if any(a.dtype!=np.float64 for a in arrays.values()):raise TypeError('Checkpoint arrays must be float64')
    meta={'identity':ident,'metadata':state['meta'],'arrays':{k:_arr_hash(a) for k,a in arrays.items()}}
    meta['sha256']=hashlib.sha256(canonical(meta)).hexdigest()
    arrays['__metadata__']=np.frombuffer(canonical(meta),dtype=np.uint8)
    _atomic(path,lambda f:np.savez(f,**arrays))

def load_state(path,ident):
    try:
        with np.load(path,allow_pickle=False) as d:
            m=json.loads(d['__metadata__'].tobytes())
            sh=m.pop('sha256')
            if hashlib.sha256(canonical(m)).hexdigest()!=sh:raise IntegrityError('Checkpoint metadata hash mismatch')
            if canonical(m['identity'])!=canonical(ident):raise IntegrityError('Checkpoint source/config/runtime mismatch')
            if set(d.files)!=set(m['arrays'])|{'__metadata__'}:raise IntegrityError('Checkpoint inventory mismatch')
            arrays={k:np.array(d[k],copy=True) for k in m['arrays']}
            for k,a in arrays.items():
                if a.dtype!=np.float64 or not np.all(np.isfinite(a)) or _arr_hash(a)!=m['arrays'][k]:
                    raise IntegrityError('Invalid checkpoint array '+k)
            arrays['meta']=m['metadata']
            return arrays
    except IntegrityError:raise
    except Exception as exc:raise IntegrityError(f'Cannot read checkpoint: {exc}') from exc

@contextlib.contextmanager
def claim(path):
    """Never unlink a flock lock: replacement would allow two inode owners."""
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with open(p,'a+') as f:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise AlreadyRunning(str(p))
        f.seek(0);f.truncate();f.write(str(os.getpid())+'\n');f.flush()
        try:yield
        finally:fcntl.flock(f,fcntl.LOCK_UN)
