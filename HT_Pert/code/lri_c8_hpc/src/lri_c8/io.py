"""Process-owned POSIX locks, checksummed scalar checkpoints, atomic publication."""
from __future__ import annotations
import contextlib,errno,fcntl,hashlib,json,os,platform,signal,sys,time
from pathlib import Path
import numpy, numba, scipy

class StopRequested(Exception):pass
class ClaimBusy(RuntimeError):pass

class StopFlag:
    def __init__(self):self.signum=None;self.old={}
    def __enter__(self):
        from . import _signals
        for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGUSR1):
            self.old[sig]=signal.signal(sig,self._handler)
        # A signal delivered while the interpreter was still importing is not lost.
        if _signals.pending is not None:self.signum=_signals.pending
        return self
    def _handler(self,signum,frame):self.signum=signum
    def boundary(self):
        if self.signum is not None:raise StopRequested(f'Saved at safe boundary after signal {self.signum}')
    def __exit__(self,*args):
        for sig,handler in self.old.items():signal.signal(sig,handler)

def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(obj):return hashlib.sha256(canonical(obj)).hexdigest()
def source_digest():
    root=Path(__file__).parent;h=hashlib.sha256()
    for p in sorted(root.rglob('*.py')):
        h.update(str(p.relative_to(root)).encode());h.update(p.read_bytes())
    return h.hexdigest()

def blas_info():
    # threadpoolctl 2.2 cannot introspect some BLAS builds; never fail a run on metadata.
    try:
        import threadpoolctl
        return [{k:v for k,v in x.items() if k!='filepath'} for x in threadpoolctl.threadpool_info()]
    except Exception as e:return [{'unavailable':repr(e)}]

def runtime(threads):
    try:layer=numba.threading_layer()
    except ValueError:layer='not_initialized'
    return {'python':platform.python_version(),'numpy':numpy.__version__,'numba':numba.__version__,
            'scipy':scipy.__version__,'platform':platform.platform(),'machine':platform.machine(),
            'threads':threads,'threading_layer':layer,
            'blas':blas_info()}

def config(cutoff,scheme,backend,threads):
    return {'format':1,'solver':'c8-residual-packed-0.1','source_sha256':source_digest(),
            'cutoff':cutoff,'degree':8,'scheme':scheme,'outer_backend':backend,
            'caps':{'core':[15,12],'full':[19,16]},'dtype':'float64','fastmath':False,'runtime':runtime(threads)}

def tmp_name(path):
    # Unique across nodes sharing a file system, not only across local pids.
    return path.with_name(path.name+f'.tmp.{platform.node()}.{os.getpid()}.{os.urandom(4).hex()}')

def fsync_dir(directory):
    fd=os.open(directory,os.O_RDONLY)
    try:os.fsync(fd)
    except OSError as e:
        # Some network file systems reject fsync on a directory descriptor.
        if e.errno not in (errno.EINVAL,errno.ENOTSUP,errno.EOPNOTSUPP):raise
    finally:os.close(fd)

def atomic_save(path,payload):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    # Hash what read() will see: JSON turns int keys into strings and reorders them.
    payload=json.loads(json.dumps(payload,allow_nan=False))
    envelope={'format':'lri-c8-sha256-v1','sha256':digest(payload),'payload':payload}
    tmp=tmp_name(path)
    try:
        with tmp.open('w') as f:
            json.dump(envelope,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
        fsync_dir(path.parent)
    finally:
        if tmp.exists():tmp.unlink()

def read(path):
    envelope=json.loads(Path(path).read_text())
    if envelope.get('format')!='lri-c8-sha256-v1' or digest(envelope['payload'])!=envelope.get('sha256'):
        raise ValueError(f'Checksum/format failure: {path}')
    return envelope['payload']

@contextlib.contextmanager
def claim(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    f=path.open('a+')
    try:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ClaimBusy(f'Item is already owned by another solver: {path}')
        f.seek(0);f.truncate();f.write(json.dumps({'pid':os.getpid(),'host':platform.node(),'time':time.time()}));f.flush()
        yield
    finally:f.close()

# flock is node-local on BeeGFS unless tuneUseGlobalFileLocks=true (false on symmetry).
# Cross-node exclusivity therefore uses O_EXCL owner files held by every writer: the
# solver for its item (next to the flock file), the lane supervisor for its journal,
# and assemble/export/make_campaign for one-shot publications. An existing owner is
# never taken over, not even by the same Slurm job: a stale owner (hard kill, node
# failure) is moved aside only by scripts/clean_owners.py, which the submit wrapper
# runs under its mutex after checking that the job recorded in the owner is not live.
def owner_info():
    return {'host':platform.node(),'pid':os.getpid(),'time':time.time(),
            **{k.lower():os.environ[k] for k in ('SLURM_JOB_ID','SLURM_ARRAY_JOB_ID','SLURM_ARRAY_TASK_ID',
                                                 'SLURM_RESTART_COUNT') if k in os.environ}}

def acquire_owner(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    info={**owner_info(),'token':os.urandom(8).hex()}
    try:fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o644)
    except FileExistsError:
        try:old=path.read_text()
        except OSError as e:old=repr(e)
        raise ClaimBusy(f'Owned elsewhere: {path} {old}')
    try:os.write(fd,json.dumps(info).encode());os.fsync(fd)
    finally:os.close(fd)
    return info['token']

def release_owner(path,token):
    path=Path(path)
    try:
        if json.loads(path.read_text()).get('token')==token:path.unlink()
    except (OSError,ValueError):pass

def owner_path(dest):
    """The ONE owner file of a destination, shared by every writer of it (solver,
    assemble, export, make_campaign): <dir>/claims/<stem>.owner."""
    dest=Path(dest);return dest.parent/'claims'/(dest.stem+'.owner')

@contextlib.contextmanager
def owner(path):
    token=acquire_owner(path)
    try:yield token
    finally:release_owner(path,token)

@contextlib.contextmanager
def owners(*dests):
    """Own every destination's canonical owner (sorted, all or nothing)."""
    with contextlib.ExitStack() as stack:
        for o in sorted({owner_path(p) for p in dests}):stack.enter_context(owner(o))
        yield

@contextlib.contextmanager
def publication(*paths):
    """One-shot publication of NEW files, exclusive across nodes: owns EVERY destination,
    then refuses existing destinations. A crash leaves the owners behind, which makes
    later attempts refuse until they are inspected and removed."""
    with owners(*paths):
        for p in paths:
            if Path(p).exists():raise FileExistsError(f'Refusing to overwrite {p}')
        yield

def reject_multirank():
    for k in ('OMPI_COMM_WORLD_SIZE','PMI_SIZE','PMIX_SIZE','MV2_COMM_WORLD_SIZE','SLURM_NTASKS'):
        if int(os.environ.get(k,'1'))>1:raise RuntimeError('No single-item MPI backend. Use independent one-task jobs or reference shards.')
