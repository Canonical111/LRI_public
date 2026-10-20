"""Atomic, fingerprinted state and acceptance checks for cluster execution."""
from __future__ import annotations
import contextlib
import fcntl
import hashlib
import json
import math
import os
import platform
import signal
import socket
import sys
import time
import tempfile
from pathlib import Path
from . import __version__

SCHEMA=2
PRESCRIPTION='isolated-vacuum-delta-response-v2'

class BusyError(RuntimeError):pass
class AcceptanceError(RuntimeError):pass
class Preempted(RuntimeError):pass


def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()


def fingerprint():
    h=hashlib.sha256();root=Path(__file__).parent
    for p in sorted(root.rglob('*.py')):
        h.update(p.relative_to(root).as_posix().encode());h.update(b'\0');h.update(p.read_bytes());h.update(b'\0')
    return h.hexdigest()


def environment():
    import numpy,numba,llvmlite
    return dict(python=platform.python_version(),numpy=numpy.__version__,numba=numba.__version__,llvmlite=llvmlite.__version__,
                host=socket.gethostname(),platform=platform.platform(),pid=os.getpid(),
                threads=numba.get_num_threads(),cpu_affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
                slurm={k:os.environ[k] for k in ('SLURM_JOB_ID','SLURM_ARRAY_TASK_ID','SLURM_CPUS_PER_TASK','SLURM_MEM_PER_NODE') if k in os.environ})


def config(cutoff,degree):
    import numpy,numba,llvmlite
    return dict(schema=SCHEMA,prescription=PRESCRIPTION,cutoff=cutoff,degree=degree,
                source_sha256=fingerprint(),dtype='float64',fastmath=False,
                dependencies=dict(python=platform.python_version(),numpy=numpy.__version__,numba=numba.__version__,llvmlite=llvmlite.__version__))


def atomic_json(path,obj):
    """Same-directory rename; directory fsync after publication. No NaN JSON."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd_tmp,name=tempfile.mkstemp(prefix=path.name+'.tmp.',dir=path.parent)
    tmp=Path(name)
    try:
        with os.fdopen(fd_tmp,'wb') as f:
            f.write(json.dumps(obj,indent=2,allow_nan=False).encode()+b'\n');f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
        fd=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if tmp.exists():tmp.unlink()


def seal(obj):
    out=dict(obj);out.pop('payload_sha256',None);out['payload_sha256']=digest(out);return out


def verify_seal(obj):
    if not isinstance(obj,dict):raise AcceptanceError('Expected JSON object')
    body=dict(obj);got=body.pop('payload_sha256',None)
    if got!=digest(body):raise AcceptanceError('Missing or invalid payload SHA-256')


def load_checkpoint(path,cfg):
    path=Path(path)
    if not path.exists():return {}
    obj=json.loads(path.read_text());verify_seal(obj)
    if obj.get('config')!=cfg:raise AcceptanceError('Checkpoint source, dependencies, or configuration differ')
    cp=obj.get('state')
    if not isinstance(cp,dict):raise AcceptanceError('Malformed checkpoint')
    # Content checksum detects accidental writes; explicit dimensions avoid relying
    # on the checksum alone when validating checkpoint structure.
    degree=cfg['degree'];order=degree//2;base=max(order,degree-3)
    if 'low' in cp:
        for k in ('r','g'):check_vector(cp['low'].get(k),order+1,'checkpoint '+k)
        for p in ('0','1','3'):check_vector(cp['low'].get('E',{}).get(p),order+1,'checkpoint E'+p)
    for p,c in cp.get('components',{}).items():
        if p not in ('0','1','2','3'):raise AcceptanceError('Unexpected reference')
        lengths={'F':base+1,'M':base+1,'V':base+1,'dF':degree+1,
                 'dM':degree if degree>=6 else degree+1,'dV':degree if degree>=6 else degree+1,'K':degree-1}
        for k,n in lengths.items():check_vector(c.get(k),n,'component '+p+k)
    return cp


def check_vector(x,n,name):
    if not isinstance(x,list) or len(x)!=n:raise AcceptanceError(name+': invalid coefficient count')
    if not all(isinstance(y,(int,float)) and not isinstance(y,bool) and math.isfinite(y) for y in x):raise AcceptanceError(name+': nonfinite or nonnumeric coefficients')


def validate_result(obj,expected_config=None):
    verify_seal(obj)
    cfg=obj.get('config',{})
    if expected_config is not None and cfg!=expected_config:raise AcceptanceError('Result configuration/source/dependency mismatch')
    if cfg.get('schema')!=SCHEMA or cfg.get('prescription')!=PRESCRIPTION:raise AcceptanceError('Unsupported prescription/schema')
    if obj.get('source_sha256')!=cfg.get('source_sha256'):raise AcceptanceError('Inconsistent source fingerprint')
    d=obj.get('degree');L=obj.get('cutoff')
    if d not in (4,5,6,7) or not isinstance(L,int) or L<4 or L%2:raise AcceptanceError('Invalid degree/cutoff')
    if cfg.get('degree')!=d or cfg.get('cutoff')!=L:raise AcceptanceError('Result/config mismatch')
    if obj.get('dtype')!='float64' or obj.get('fastmath') is not False:raise AcceptanceError('Unexpected numerical precision')
    reach=(d-2)//2
    if obj.get('particle_cap')!=3+4*reach or obj.get('nonzero_particle_cap')!=4*reach:raise AcceptanceError('Wrong support caps')
    for k in ('delta_C','delta_r','delta_g'):check_vector(obj.get(k),d+1,k)
    if max(abs(x) for k in ('delta_C','delta_r','delta_g') for x in obj[k][:4])>1e-10:raise AcceptanceError('Lower-order invariance failed')
    v=obj.get('validation',{})
    for key,lim in [('max_raw_vacuum_shell_residual',1e-10),('max_tuning_residual',1e-6),('response_tuning_residual',1e-6),
                    ('exact_delta_C4_residual',1e-10),('lower_order_invariance_residual',1e-10)]:
        x=v.get(key)
        if not isinstance(x,(float,int)) or not math.isfinite(x) or x<0 or x>lim:raise AcceptanceError('Acceptance gate failed: '+key)
    from .exact import fast
    if abs(obj['delta_C'][4]-fast(L))>1e-10:raise AcceptanceError('Recomputed exact delta C4 gate failed')
    if obj.get('acceptance')!='passed':raise AcceptanceError('Unaccepted record')
    return obj


@contextlib.contextmanager
def claim(path):
    """Claim held by the solver process. Never delete/unlink the lock inode."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+') as f:
        try:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as e:raise BusyError(f'Live claim: {path}') from e
        f.seek(0);f.truncate();json.dump(dict(pid=os.getpid(),host=socket.gethostname(),started=time.time()),f);f.flush()
        try:yield
        finally:fcntl.flock(f.fileno(),fcntl.LOCK_UN)


class StopFlag:
    def __init__(self):self.requested=None;self.old={}
    def __enter__(self):
        for s in (signal.SIGTERM,signal.SIGINT,signal.SIGUSR1):
            self.old[s]=signal.signal(s,self.handle)
        return self
    def handle(self,signum,frame):self.requested=signum
    def check(self):
        if self.requested is not None:raise Preempted(f'Signal {self.requested}; stopped at scalar checkpoint boundary')
    def __exit__(self,*args):
        for s,h in self.old.items():signal.signal(s,h)


def event(path,**kwargs):
    """One solver writes this item journal while holding its claim."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as f:
        f.write(json.dumps(dict(time=time.time(),**kwargs),allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())


def require_receipt(path):
    obj=json.loads(Path(path).read_text());verify_seal(obj)
    if obj.get('kind')!='lri-eh-validation' or obj.get('passed') is not True:raise AcceptanceError('Validation receipt is not a pass')
    if obj.get('source_sha256')!=fingerprint():raise AcceptanceError('Validation receipt is for different source')
    if obj.get('dependencies')!=config(4,7)['dependencies']:raise AcceptanceError('Validation receipt dependency versions differ; rerun validation on this environment')
    return obj
