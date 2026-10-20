#!/usr/bin/env python3
"""Deterministic C8 task planning, resumable workers and bounded-memory reduction (order-eight generalization of
the reviewed C7 engine: 16-value rows, loop orders 2..8, and an exact all-tree mode with one deterministic replicate).

A task is a contiguous part of one (replicate, graph) stream. It is NOT a new
independent replicate. The merger requires complete, nonoverlapping coverage.
Standard library only, except net generation (SciPy/NumPy) and error statistics.
"""
from __future__ import annotations
import argparse, decimal, hashlib, heapq, json, math, os, shutil, signal, socket, sqlite3, struct, subprocess, sys, tempfile, time
from pathlib import Path
from typing import Any
D=decimal.Decimal
ROOT=Path(__file__).resolve().parents[1]
SCHEMA='c8-campaign-1'
NW=8;NV=2*NW;TOP=8 # slots per channel, values per row, top loop order of the target coefficient C8

def tree_count(L:int)->int:
    """Ordered trees of the exact mode: (L+1)!/2 vertex orders (reflection pairs) times Catalan(L) binary shapes."""
    return math.factorial(L+1)//2*math.comb(2*L,L)//(L+1)

def digest(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def umask()->int:
    u=os.umask(0);os.umask(u);return u

def publish(p:Path,text:str)->None:
    p.parent.mkdir(parents=True,exist_ok=True)
    fd,t=tempfile.mkstemp(prefix=p.name+'.tmp.',dir=p.parent)
    try:
        os.fchmod(fd,0o666&~umask()) # mkstemp is always 0600; shared project directories need the umask.
        with os.fdopen(fd,'w') as f:f.write(text);f.flush();os.fsync(f.fileno())
        os.link(t,p) # Atomic no-clobber publish on the same filesystem.
    finally:
        os.unlink(t)

def commit(tmp:str,p:Path)->None:
    """Publish a finished temporary file. An identical existing output is reused, a different one is an error."""
    try:
        try:os.link(tmp,p)
        except FileExistsError:
            if digest(Path(tmp))!=digest(p):raise FileExistsError('existing output differs from recomputation: '+str(p))
    finally:os.unlink(tmp)

def publish_or_verify(p:Path,text:str)->bool:
    """Idempotent publish of deterministic content; returns False when an identical file already existed."""
    p.parent.mkdir(parents=True,exist_ok=True);existed=p.exists()
    fd,t=tempfile.mkstemp(prefix=p.name+'.tmp.',dir=p.parent);os.fchmod(fd,0o666&~umask())
    with os.fdopen(fd,'w') as f:f.write(text);f.flush();os.fsync(f.fileno())
    commit(t,p);return not existed

def dump(p:Path,obj:Any)->None:publish(p,json.dumps(obj,indent=2,allow_nan=False)+'\n')
def read(p:Path)->Any:return json.loads(p.read_text(),parse_float=D)

def inventory(inputs:Path,L:int)->list[dict]:
    rows=[]
    with (inputs/f'L{L}_coord.txt').open() as f:
        l,ng=map(int,f.readline().split())
        if l!=L:raise ValueError('inventory loop mismatch')
        for gi in range(ng):
            a=f.readline().split()
            if int(a[0])!=gi:raise ValueError('noncanonical graph order')
            rows.append(dict(id=gi,wa=a[1],wb=a[2],power=int(a[3]),primitive=int(a[4]),terms=int(a[5])))
            for _ in range(int(a[5])):
                if not f.readline():raise ValueError('truncated inventory')
    return rows

def net_file(path:Path,B:int,dim:int,seed:int,bits:int=52)->dict:
    import numpy as np
    import scipy
    from scipy.stats import qmc
    rng=np.random.default_rng(seed)
    with path.open('xb') as f:
        f.write(struct.pack('<III',B,dim,bits))
        for r in range(B):
            engine=qmc.Sobol(d=dim,scramble=True,bits=bits,seed=int(rng.integers(1,2**32-1)))
            mat=engine._sv.copy();state=engine._shift.copy();points=[]
            for n in range(16):
                if n:state^=mat[:,(n&-n).bit_length()-1]
                points.append(state.copy())
            if not np.array_equal(np.array(points,dtype=np.float64)/2**bits,engine.random_base2(4)):
                raise ArithmeticError('Sobol internals differ from checked public API')
            f.write(mat.astype('<u8').tobytes())
    return {'matrix_seed':seed,'scipy':scipy.__version__,'replicates':B,'dimensions':dim,'bits':bits,'checked_points_per_replicate':16}

def plan_counts(inputs:Path,L:int,mode:str,selection:str,counts:Path|None,points:int,multiplier:int)->tuple[list,list[int]]:
    """(inventory rows, complete per-graph sample vector) of a campaign: counts file or uniform points, exact-zero
    lists, the L7 channel condition and the selection, times the sample multiplier. Shared by plan() and design."""
    rows=inventory(inputs,L);ng=len(rows);out=[points]*ng
    if counts:
        toks=list(map(int,counts.read_text().split()))
        if len(toks)!=1+2*ng or toks[0]!=ng:raise ValueError('counts length mismatch')
        if sorted(toks[1::2])!=list(range(ng)):raise ValueError('invalid/duplicate count ids')
        for gi,n in zip(toks[1::2],toks[2::2]):out[gi]=n
    zeros=set()
    zp=inputs/f'exact_zero_L{L}.txt'
    if zp.exists():
        z=list(map(int,zp.read_text().split()))
        if z[0]!=len(z)-1:raise ValueError('invalid zero-graph file')
        zeros=set(z[1:])
    for r in rows:
        gi=r['id'];n=out[gi]
        if n<0:raise ValueError('negative sample count')
        # At the top loop only the 3c-b channel enters C8 (checked against the affine map by tools/affine8.py).
        keep=r['terms']>0 and gi not in zeros and (L<TOP or abs(3*D(r['wb'])-D(r['wa']))>=D('1e-17'))
        if mode=='qmc':keep=keep and not r['power']
        if selection=='power':keep=keep and bool(r['power'])
        if selection=='free':keep=keep and not r['power']
        if selection=='nonprimitive':keep=keep and not r['primitive'] and not r['power']
        if selection=='primitive':keep=keep and bool(r['primitive']) and not r['power']
        out[gi]=(tree_count(L) if mode=='exact' else n*multiplier) if keep else 0
        if mode=='qmc' and out[gi] and (out[gi]&(out[gi]-1)):raise ValueError('each QMC graph total must be a power of two')
    return rows,out

def campaign_inputs(directory:Path,m:dict)->Path:
    p=Path(m['inputs']);return p if p.is_absolute() else (directory/p).resolve()

def plan(a:argparse.Namespace)->None:
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'manifest.json').exists() or (out/'sobol.net').exists() or any(out.glob('tasks_*.txt')):raise FileExistsError('Use a new campaign directory')
    inputs=a.inputs.resolve();exe=a.executable.resolve()
    if not exe.is_file():raise FileNotFoundError('Build the executable first')
    if a.threads<1 or a.shards<1 or a.multiplier<1 or a.checkpoint_tasks<1:raise ValueError('Positive sizes required')
    if (a.mode=='exact')!=(a.replicates==1) or a.replicates<1:raise ValueError('exact mode has exactly one deterministic replicate; sampled modes need >=2 independent replicates')
    if a.mode=='exact' and (a.counts or a.multiplier!=1):raise ValueError('exact mode enumerates every ordered tree; no counts or multiplier')
    if not 0<float(a.rate)<=1:raise ValueError('rate outside (0,1]')
    if not 0<=a.seed<2**64 or a.matrix_seed<0:raise ValueError('invalid random seed')
    if a.chunk_points<0 or a.tile<1 or a.tile>1048576 or not 1<=a.scratch_mib<=65536:raise ValueError('invalid chunk/tile/scratch size')
    rows,counts=plan_counts(inputs,a.L,a.mode,a.selection,a.counts,a.points,a.multiplier);ng=len(rows)
    if not any(counts):raise ValueError('no active graphs')
    degrees=[0] if a.mode=='qmc' else sorted(set(a.degrees))
    if a.mode in ('power','exact') and (not degrees or min(degrees)<1 or max(degrees)>254):raise ValueError('positive quadrature degrees required')
    roles={}
    for name in [f'L{a.L}_coord.txt',f'cgamma_L{a.L}.txt']:
        p=inputs/name;roles[name]=digest(p)
    ix=inputs/f'L{a.L}_coord.txt.idx'
    if ix.exists():roles[ix.name]=digest(ix)
    zp=inputs/f'exact_zero_L{a.L}.txt' # the exact-zero list decides the active set (plan_counts): hashed with the other inputs
    roles[zp.name]=digest(zp) if zp.exists() else 'absent'
    if a.mode in ('power','exact'):
        for N in degrees:
            p=inputs/f'cw_L{a.L}_N{N}.txt' # C8 reads portable order-eight weights only
            roles[p.name]=digest(p)
    netinfo=None;nettmp=None
    try:
        if a.mode=='qmc':
            nettmp=out/f'.sobol.net.tmp.{os.getpid()}'
            if a.net:
                shutil.copyfile(a.net,nettmp)
                B,dim,bits=struct.unpack('<III',nettmp.read_bytes()[:12])
                if B<a.replicates or dim<2*a.L-1:raise ValueError('provided net has insufficient replicates/dimensions')
                netinfo={'source':str(a.net.resolve()),'replicates':B,'dimensions':dim,'bits':bits}
            else:netinfo=net_file(nettmp,a.replicates,2*a.L-1,a.matrix_seed)
            if max(counts)>2**netinfo['bits']:raise ValueError('sample count exceeds Sobol bit depth')
            netinfo['sha256']=digest(nettmp)
        # Partition a complete stream into contiguous intervals; random streams are unchanged.
        work=[]
        for rep in range(a.replicates):
            for gi,total in enumerate(counts):
                if not total:continue
                block=a.chunk_points or total
                for start in range(0,total,block):
                    stop=min(total,start+block)
                    work.append((len(work),rep,gi,start,stop,total))
        nshards=min(a.shards,len(work));bins=[[] for _ in range(nshards)];costs=[(0,i) for i in range(nshards)];heapq.heapify(costs)
        # Scheduling changes allocation to workers, never allocation of statistical samples.
        cost=lambda w:(w[4]-w[3])*max(8,rows[w[2]]['terms'])*sum((n+1)**(a.L-1) if n else 1 for n in degrees)
        for w in sorted(work,key=lambda w:(-cost(w),w[0])):
            load,i=heapq.heappop(costs);bins[i].append(w);heapq.heappush(costs,(load+cost(w),i))
        shards=[]
        for i,items in enumerate(bins):
            items.sort();p=out/f'tasks_{i:06d}.txt'
            publish(p,f'C8TASKS1 {ng} {len(items)}\n'+''.join(' '.join(map(str,w))+'\n' for w in items))
            shards.append({'id':i,'file':p.name,'sha256':digest(p),'work_units':len(items),'predicted_cost':sum(cost(w) for w in items)})
        # Inputs inside the enclosing production directory are recorded relative to the campaign, so it can move.
        try:inputs.relative_to(out.parent);where=os.path.relpath(inputs,out)
        except ValueError:where=str(inputs)
        manifest={'schema':SCHEMA,'mode':a.mode,'L':a.L,'degrees':degrees,'seed':a.seed,'rate':str(D(a.rate)),'replicates':a.replicates,'inventory_count':ng,
            'counts':counts,'selection':a.selection,'inputs':where,'input_sha256':roles,'executable':str(exe),'executable_sha256':digest(exe),'net':netinfo,
            'threads':a.threads,'tile':a.tile,'scratch_mib':a.scratch_mib,'checkpoint_tasks':a.checkpoint_tasks,'chunk_points':a.chunk_points,'shards':shards,
            'total_work_units':len(work),'samples_per_degree':sum(counts)*a.replicates,
            'statistical_unit':'independent randomization/replicate, never a shard or chunk','allocation':'frozen before production; LPT scheduling does not change sample counts'}
        if nettmp:os.link(nettmp,out/'sobol.net') # Published only after every validation above.
        dump(out/'manifest.json',manifest)
    finally:
        if nettmp and nettmp.exists():nettmp.unlink()
    print(json.dumps({'directory':str(out),'shards':nshards,'work_units':len(work),'samples_per_degree':manifest['samples_per_degree']},indent=2))

def work_rows(path:Path)->tuple[int,list[tuple[int,...]]]:
    with path.open() as f:
        magic,ng,n=f.readline().split()
        if magic!='C8TASKS1':raise ValueError('bad task header')
        w=[tuple(map(int,line.split())) for line in f if line.strip()]
    if len(w)!=int(n) or any(len(t)!=6 for t in w):raise ValueError('bad task rows')
    return int(ng),w

def identity(shard:int,part:int,N:int)->str:return f's{shard:06d}_p{part:06d}_N{N}'

def blocks(directory:Path,m:dict,only:int|None=None):
    """Yield (shard, part, work block, inventory count) after checking every task-plan hash."""
    for shard in m['shards'] if only is None else [m['shards'][only]]:
        task=directory/shard['file']
        if digest(task)!=shard['sha256']:raise ValueError('task plan checksum mismatch: '+shard['file'])
        ng,ws=work_rows(task)
        for part,st in enumerate(range(0,len(ws),m['checkpoint_tasks'])):yield shard,part,ws[st:st+m['checkpoint_tasks']],ng

def payload_digest(d:dict)->str:
    """SHA-256 of the scientific content of one worker output; timings, profiles and provenance are excluded."""
    rows=[[r['uid'],r['replicate'],r['graph'],r['begin'],r['end'],r['total'],r.get('quad_calls',0),r.get('mp_calls',0),[str(D(v)) for v in r['value']]] for r in d['rows']]
    core={'mode':d['mode'],'L':d['L'],'degree':d['degree'],'seed':d['seed'],'rate':str(D(d['rate'])),'inventory_count':d['inventory_count'],'rows':rows}
    return hashlib.sha256(json.dumps(core,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate_output(path:Path,m:dict,ws:list[tuple[int,...]],N:int,manifest_hash:str,ident:str,committed:bool=True)->dict:
    try:
        d=read(path)
        for k,v in [('mode',m['mode']),('L',m['L']),('degree',N),('seed',m['seed']),('inventory_count',m['inventory_count']),('slots',NW),('schema','c8-hpc-1')]:
            if d.get(k)!=v:raise ValueError(f'{path}: mismatched {k}')
        if abs(D(d['rate'])-D(m['rate'])) > D(2)**(-int(d['long_double_bits']))*max(D(1),abs(D(m['rate']))):raise ValueError('rate mismatch')
        if len(d.get('rows',[]))!=len(ws):raise ValueError('incomplete checkpoint')
        for w,r in zip(ws,d['rows']):
            got=tuple(r[k] for k in ['uid','replicate','graph','begin','end','total'])
            if got!=w or len(r['value'])!=NV or any(not D(v).is_finite() for v in r['value']):raise ValueError('invalid checkpoint row')
        p=d.get('provenance')
        if committed and m.get('schema')==SCHEMA and not p:raise ValueError('missing checkpoint provenance')
        if p and (p.get('manifest_sha256')!=manifest_hash or p.get('checkpoint')!=ident):raise ValueError('checkpoint belongs to another campaign')
        if p and m.get('schema')==SCHEMA and p.get('payload_sha256')!=payload_digest(d):raise ValueError('checkpoint content does not match its committed payload_sha256 (corrupted?); inspect it and use "campaign.py quarantine"')
    except (KeyError,TypeError,decimal.InvalidOperation,json.JSONDecodeError) as e:raise ValueError(f'{path}: malformed checkpoint ({e!r})') from e
    except ValueError as e:
        if str(path) in str(e):raise
        raise ValueError(f'{path}: {e}') from e
    return d

def affinity_count()->int|None:
    f=getattr(os,'sched_getaffinity',None)
    return len(f(0)) if f else None

def binding_policy(n:int|None,threads:int)->str:
    """unknown: no affinity API; oversubscribed: fewer allowed CPUs than threads; unconfined: more; confined: equal."""
    if n is None:return 'unknown'
    if n<threads:return 'oversubscribed'
    return 'unconfined' if n>threads else 'confined'

def runtime_libraries(exe:Path)->dict:
    try:out=subprocess.run(['ldd',str(exe)],capture_output=True,text=True,check=True).stdout
    except (OSError,subprocess.CalledProcessError):return {}
    libs={}
    for line in out.splitlines():
        t=line.split()
        if len(t)>2 and t[1]=='=>' and t[2].startswith('/') and t[0].startswith(('libquadmath','libgomp','libstdc++','libm.','libc.','libgcc_s')):
            p=Path(t[2]).resolve();libs[t[0]]={'path':str(p),'sha256':digest(p)}
    return libs

def check_frozen(m:dict,inputs:Path,exe:Path,net:Path)->str:
    """Verify the executable, every planned input and the net; return the executable digest actually checked."""
    h=digest(exe)
    if h!=m['executable_sha256']:raise ValueError('executable changed: make a new campaign, do not mix builds in one result')
    for file,sha in m['input_sha256'].items():
        if sha=='absent':
            if (inputs/file).exists():raise ValueError('input planned as absent now exists: '+file)
            continue
        if digest(inputs/file)!=sha:raise ValueError('input checksum mismatch: '+file)
        if file.endswith('.bin') and (inputs/Path(file).with_suffix('.txt')).exists():
            raise ValueError('Unplanned portable weights would override native weights: '+file+'; create a new campaign')
    if m['net'] and digest(net)!=m['net']['sha256']:raise ValueError('net checksum mismatch')
    return h

def run(a:argparse.Namespace)->None:
    directory=a.directory.resolve();mp=directory/'manifest.json';m=json.loads(mp.read_text());mh=digest(mp)
    if a.index is not None:index=a.index
    elif 'SLURM_ARRAY_TASK_ID' in os.environ:index=int(os.environ['SLURM_ARRAY_TASK_ID'])
    else:raise ValueError('give --index or run inside a Slurm array (no silent default shard)')
    if not 0<=index<len(m['shards']):raise ValueError('shard index out of range')
    threads=a.threads or m['threads']
    if not 1<=threads<=4096:raise ValueError('invalid thread count')
    shard=m['shards'][index]
    inputs=(a.inputs or campaign_inputs(directory,m)).resolve();exe=(a.executable or Path(m['executable'])).resolve();net=directory/'sobol.net'
    check_frozen(m,inputs,exe,net)
    env=dict(os.environ);policy=binding_policy(affinity_count(),threads)
    if policy=='oversubscribed' and not a.allow_oversubscribe:
        raise ValueError(f'CPU affinity {affinity_count()} < threads {threads}; launch srun with --cpus-per-task (or pass --allow-oversubscribe)')
    if policy=='unconfined':
        for k in ('OMP_PLACES','OMP_PROC_BIND'):env.pop(k,None)
        print(f'note: {affinity_count()} allowed CPUs for {threads} threads (unconfined node); OpenMP thread binding disabled',flush=True)
    elif policy=='unknown':print('note: CPU affinity not available on this platform; no oversubscription guard',flush=True)
    libs=runtime_libraries(exe);host=socket.gethostname();outdir=directory/'checkpoints';outdir.mkdir(exist_ok=True)
    signal.signal(signal.SIGTERM,lambda s,f:sys.exit(128+s)) # Wall-time kills unwind, so temporary block directories are removed.
    for shard,part,block,ng in blocks(directory,m,index):
        with tempfile.TemporaryDirectory(prefix='c8_task_',dir=a.scratch) as td:
            td=Path(td);tf=td/'tasks.txt';tf.write_text(f'C8TASKS1 {ng} {len(block)}\n'+''.join(' '.join(map(str,w))+'\n' for w in block))
            for N in m['degrees']:
                ident=identity(index,part,N);dest=outdir/(ident+'.json')
                if dest.exists():
                    validate_output(dest,m,block,N,mh,ident);continue
                temp=td/f'result_{N}.json'
                cmd=[str(exe),'--mode',m['mode'],'--inputs',str(inputs),'--L',str(m['L']),'--tasks',str(tf),'--seed',str(m['seed']),'--rate',m['rate'],'--output',str(temp),
                     '--threads',str(threads),'--tile',str(m['tile']),'--scratch-mib',str(m['scratch_mib'])]
                if m['mode']=='qmc':cmd+=['--net',str(net)]
                else:cmd+=['--degree',str(N)]
                ran=check_frozen(m,inputs,exe,net) # Re-checked before every invocation: a mid-run rebuild cannot slip in.
                subprocess.run(cmd,check=True,env=env)
                d=validate_output(temp,m,block,N,mh,ident,committed=False)
                text=temp.read_text().rstrip()
                if not text.endswith('}'):raise ValueError('unexpected worker output framing')
                provenance={'manifest_sha256':mh,'checkpoint':ident,'executable_sha256':ran,'task_plan_sha256':shard['sha256'],'command':cmd,
                            'payload_sha256':payload_digest(d),'host':host,'threads':threads,'binding':policy,'runtime_libraries':libs}
                text=text[:-1]+',"provenance":'+json.dumps(provenance,allow_nan=False)+'}\n'
                try:publish(dest,text);print('committed',ident,flush=True)
                except FileExistsError:validate_output(dest,m,block,N,mh,ident);print('verified concurrent duplicate',ident,flush=True) # never count twice

def quarantine(a:argparse.Namespace)->None:
    """Explicit operator recovery: move one committed checkpoint aside so the next run recomputes it."""
    directory=a.directory.resolve();src=directory/'checkpoints'/(a.identity+'.json')
    if not src.is_file():raise FileNotFoundError(str(src))
    q=directory/'checkpoints'/'quarantine';q.mkdir(exist_ok=True);n=0
    while (q/f'{src.name}.{n}').exists():n+=1
    dest=q/f'{src.name}.{n}';h=digest(src);os.rename(src,dest);ap=directory/'merged'/'audit.json';old=None
    if ap.exists(): # The audit names the quarantined file; merged scientific outputs stay and must be reproduced exactly.
        k=0
        while (ap.parent/f'audit.json.invalidated.{k}').exists():k+=1
        old=f'audit.json.invalidated.{k}';os.rename(ap,ap.parent/old)
    with (q/'log.jsonl').open('a') as f:f.write(json.dumps({'identity':a.identity,'moved_to':dest.name,'sha256':h,'invalidated_audit':old,'time':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'reason':a.reason})+'\n')
    print('quarantined',src,'->',dest,*(['; audit invalidated ->',old,'(rerun run, then merge)'] if old else []))

def num(v:Any)->str:
    v=D(v)
    if not v.is_finite():raise ValueError('nonfinite output')
    return str(v)

def check_coverage(conn:sqlite3.Connection,m:dict)->int:
    """Task rows (table expected) must be exactly replicates x active graphs at the manifest totals, contiguous from 0."""
    n=conn.execute('SELECT COUNT(*) FROM expected').fetchone()[0]
    if n!=m['total_work_units']:raise ValueError('planned coverage mismatch')
    want={(r,g):t for r in range(m['replicates']) for g,t in enumerate(m['counts']) if t}
    got={(rep,gi):t for rep,gi,t in conn.execute('SELECT rep,graph,MIN(total) FROM expected GROUP BY rep,graph')}
    if got!=want:raise ValueError('task files do not cover exactly the manifest streams (replicates x counts)')
    # Every graph/replicate must cover [0,total), no gaps/overlap, complete Sobol nets.
    last=None;end=0;total=0
    for rep,gi,lo,hi,t in conn.execute('SELECT rep,graph,lo,hi,total FROM expected ORDER BY rep,graph,lo'):
        if (rep,gi)!=last:
            if last is not None and end!=total:raise ValueError('missing tail')
            last=(rep,gi);end=0;total=t
        if lo!=end or total!=t:raise ValueError('overlap, gap or inconsistent total')
        end=hi
    if last is not None and end!=total:raise ValueError('missing final tail')
    return n

def insert_tasks(conn:sqlite3.Connection,block:list)->None:
    try:conn.executemany('INSERT INTO expected VALUES(?,?,?,?,?,?)',block)
    except sqlite3.IntegrityError as e:raise ValueError('duplicate work uid in task files') from e

def merge(a:argparse.Namespace)->None:
    directory=a.directory.resolve();mp=directory/'manifest.json';m=json.loads(mp.read_text());mh=digest(mp);out=directory/'merged';out.mkdir(exist_ok=True)
    # On-disk uniqueness/completeness joins and external sort: bounded RAM, deterministic order.
    with tempfile.TemporaryDirectory(prefix='c8_merge_',dir=a.scratch) as td:
        conn=sqlite3.connect(str(Path(td)/'rows.sqlite'));conn.execute('PRAGMA cache_size=-16384');conn.execute('PRAGMA temp_store=FILE')
        conn.execute('CREATE TABLE expected(uid INTEGER PRIMARY KEY, rep INTEGER, graph INTEGER, lo INTEGER, hi INTEGER, total INTEGER)')
        conn.execute('CREATE TABLE actual(N INTEGER, uid INTEGER, vals TEXT, PRIMARY KEY(N,uid))')
        sources=[]
        for shard,part,block,_ in blocks(directory,m):
            insert_tasks(conn,block)
            for N in m['degrees']:
                ident=identity(shard['id'],part,N);p=directory/'checkpoints'/(ident+'.json')
                if not p.is_file():raise FileNotFoundError('Incomplete campaign: '+str(p))
                d=validate_output(p,m,block,N,mh,ident)
                if not d.get('provenance'):raise ValueError('missing checkpoint provenance')
                for r in d['rows']:conn.execute('INSERT INTO actual VALUES(?,?,?)',(N,r['uid'],','.join(num(v) for v in r['value'])))
                sources.append({'file':str(p.relative_to(directory)),'sha256':digest(p)})
        conn.commit();n=check_coverage(conn,m)
        allbatches={};pending=[]
        try:
            with decimal.localcontext() as dc:
                dc.prec=50
                for N in m['degrees']:
                    if conn.execute('SELECT COUNT(*) FROM actual WHERE N=?',(N,)).fetchone()[0]!=n:raise ValueError('missing degree data')
                    dest=out/f'N{N}.json'
                    fd,tmp=tempfile.mkstemp(prefix=dest.name+'.tmp.',dir=out);os.fchmod(fd,0o666&~umask());pending.append((tmp,dest))
                    batches=[[D(0) for _ in range(NV)] for _ in range(m['replicates'])]
                    with os.fdopen(fd,'w') as f:
                        f.write('{"L":'+str(m['L'])+',"N":'+str(N)+',"replicates":'+str(m['replicates'])+',"seed":'+str(m['seed'])+',"rate":'+num(m['rate'])+',"counts":'+json.dumps(m['counts'])+',"method":"c8_hpc_complete_stream_merge","complete":true')
                        cursor=iter(conn.execute('SELECT e.rep,e.graph,e.lo,a.vals FROM actual a JOIN expected e USING(uid) WHERE a.N=? ORDER BY e.rep,e.graph,e.lo',(N,)))
                        nxt=next(cursor,None)
                        if a.legacy:f.write(',"graph_batches":[')
                        for rep in range(m['replicates']):
                            if a.legacy:
                                if rep:f.write(',')
                                f.write('[')
                            for gi in range(m['inventory_count']):
                                vals=[D(0)]*NV
                                while nxt and nxt[:2]==(rep,gi):
                                    parts=list(map(D,nxt[3].split(',')));vals=[x+y for x,y in zip(vals,parts)];nxt=next(cursor,None)
                                batches[rep]=[x+y for x,y in zip(batches[rep],vals)]
                                if a.legacy:
                                    if gi:f.write(',')
                                    f.write('['+','.join(num(v) for v in vals)+']')
                            if a.legacy:f.write(']')
                        if a.legacy:f.write(']')
                        if nxt is not None:raise ValueError('out-of-range replicate')
                        f.write(',"batches":['+','.join('['+','.join(num(x) for x in row)+']' for row in batches)+'],"manifest_sha256":'+json.dumps(mh)+'}\n')
                        f.flush();os.fsync(f.fileno())
                    allbatches[N]=batches
            import numpy as np
            stats={}
            def stat(b):
                b=np.array(b,dtype=float)
                if len(b)<2:return {'mean':b.mean(0).tolist(),'covariance_of_mean':None,'independent_replicates':len(b),'note':'deterministic exact sum'}
                return {'mean':b.mean(0).tolist(),'covariance_of_mean':(np.cov(b,rowvar=False,ddof=1)/len(b)).tolist(),'independent_replicates':len(b)}
            for N,b in allbatches.items():stats[str(N)]=stat(b)
            if len(m['degrees'])==2:
                lo,hi=m['degrees'];paired=[[x-y for x,y in zip(h,l)] for h,l in zip(allbatches[hi],allbatches[lo])]
                stats['paired_difference']=stat(paired);stats['paired_difference']['degrees']=[lo,hi]
            # Statistics are complete before anything is published; reruns reuse identical outputs.
            files=[]
            while pending:
                tmp,dest=pending.pop(0);commit(tmp,dest);files.append({'file':str(dest.relative_to(directory)),'sha256':digest(dest)})
        finally:
            for tmp,_ in pending:os.unlink(tmp)
        publish_or_verify(out/'audit.json',json.dumps({'manifest_sha256':mh,'complete':True,'work_units_per_degree':n,'sources':sources,'outputs':files,'statistics':stats,
                              'precision':'50-digit decimal deterministic merging of extended-precision sums; chunks are not independent replicates'},indent=2,allow_nan=False)+'\n')
        conn.close();print('Merged complete campaign:',out)

def verify_campaign(directory:Path)->dict:
    """Re-validate a merged campaign: manifest, task plans, every checkpoint (with payload digest) and the audited outputs."""
    directory=directory.resolve();mp=directory/'manifest.json';m=json.loads(mp.read_text());mh=digest(mp);ap=directory/'merged'/'audit.json'
    if not ap.is_file():raise FileNotFoundError('campaign not merged: '+str(directory))
    audit=json.loads(ap.read_text())
    if audit.get('manifest_sha256')!=mh or audit.get('complete') is not True:raise ValueError('audit does not match the manifest or is incomplete: '+str(directory))
    if audit.get('work_units_per_degree')!=m['total_work_units']:raise ValueError('audit work-unit count mismatch: '+str(directory))
    expected=[]
    with tempfile.TemporaryDirectory(prefix='c8_verify_') as td: # Coverage is re-derived, not trusted from the audit.
        conn=sqlite3.connect(str(Path(td)/'tasks.sqlite'));conn.execute('CREATE TABLE expected(uid INTEGER PRIMARY KEY, rep INTEGER, graph INTEGER, lo INTEGER, hi INTEGER, total INTEGER)')
        for shard,part,block,_ in blocks(directory,m):
            insert_tasks(conn,block)
            for N in m['degrees']:
                ident=identity(shard['id'],part,N);p=directory/'checkpoints'/(ident+'.json')
                if not p.is_file():raise FileNotFoundError('audited checkpoint missing: '+str(p))
                validate_output(p,m,block,N,mh,ident);expected.append({'file':str(p.relative_to(directory)),'sha256':digest(p)})
        conn.commit()
        try:check_coverage(conn,m)
        except ValueError as e:raise ValueError(f'{directory}: {e}') from e
        finally:conn.close()
    if expected!=audit.get('sources'):raise ValueError('checkpoint set or content differs from the audit: '+str(directory))
    outs=[{'file':f'merged/N{N}.json','sha256':digest(directory/'merged'/f'N{N}.json')} for N in m['degrees']]
    if outs!=audit.get('outputs'):raise ValueError('merged outputs differ from the audit: '+str(directory))
    for N in m['degrees']: # the merged header must describe exactly the planned streams
        o=json.loads((directory/'merged'/f'N{N}.json').read_text())
        if (o.get('L'),o.get('N'),o.get('replicates'),o.get('seed'),o.get('counts'),o.get('manifest_sha256'),o.get('complete'),len(o.get('batches',[])))!=(m['L'],N,m['replicates'],m['seed'],m['counts'],mh,True,m['replicates']):
            raise ValueError(f'merged output N{N} does not match its manifest: '+str(directory))
    return {'manifest':m,'manifest_sha256':mh,'audit':audit}

def main()->None:
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='action',required=True)
    p=sub.add_parser('plan');p.add_argument('--mode',choices=['qmc','power','exact'],required=True);p.add_argument('--L',type=int,choices=range(2,9),required=True)
    p.add_argument('--inputs',type=Path,default=ROOT/'inputs8');p.add_argument('--executable',type=Path,default=ROOT/'bin/c8_integrate');p.add_argument('--out',type=Path,required=True)
    p.add_argument('--counts',type=Path);p.add_argument('--points',type=int,default=1);p.add_argument('--multiplier',type=int,default=1);p.add_argument('--replicates',type=int,default=16)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--matrix-seed',type=int,default=9183517);p.add_argument('--net',type=Path);p.add_argument('--rate',default='0.8')
    p.add_argument('--selection',choices=['all','free','power','nonprimitive','primitive'],default='all');p.add_argument('--degrees',type=int,nargs='+',default=[1,3])
    p.add_argument('--shards',type=int,default=16);p.add_argument('--threads',type=int,default=4);p.add_argument('--chunk-points',type=int,default=0)
    p.add_argument('--checkpoint-tasks',type=int,default=64);p.add_argument('--tile',type=int,default=128);p.add_argument('--scratch-mib',type=int,default=32)
    p=sub.add_parser('run');p.add_argument('directory',type=Path);p.add_argument('--index',type=int);p.add_argument('--threads',type=int);p.add_argument('--inputs',type=Path);p.add_argument('--executable',type=Path);p.add_argument('--scratch',type=Path)
    p.add_argument('--allow-oversubscribe',action='store_true',help='permit fewer allowed CPUs than threads')
    p=sub.add_parser('merge');p.add_argument('directory',type=Path);p.add_argument('--legacy',action='store_true',help='also stream the original graph_batches array to disk');p.add_argument('--scratch',type=Path)
    p=sub.add_parser('verify');p.add_argument('directory',type=Path)
    p=sub.add_parser('quarantine');p.add_argument('directory',type=Path);p.add_argument('identity');p.add_argument('--reason',default='')
    a=ap.parse_args()
    if a.action=='verify':r=verify_campaign(a.directory);print('Verified campaign:',a.directory.resolve(),'checkpoints:',len(r['audit']['sources']));return
    {'plan':plan,'run':run,'merge':merge,'quarantine':quarantine}[a.action](a)
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,ArithmeticError,subprocess.CalledProcessError,sqlite3.Error) as e:
        print('Campaign failed:',e,file=sys.stderr);sys.exit(2)
