"""Item claims (node-local flock plus a cross-node lease), atomic records and strict provenance validation."""
from __future__ import annotations
import hashlib,json,os,sys,platform,math,fcntl,tempfile
from pathlib import Path
from contextlib import contextmanager

SCHEMA='lri-dressed-phi4-v1'

def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(obj):return hashlib.sha256(canonical(obj)).hexdigest()

def source_fingerprint():
    """Numerical fingerprint: the package modules. Bound into every result configuration."""
    root=Path(__file__).parent;h=hashlib.sha256()
    for p in sorted(root.glob('*.py')):h.update(p.name.encode());h.update(p.read_bytes())
    return h.hexdigest()

RELEASE_GLOBS=('src/lri_dressed/*.py','scripts/*.py','cluster/symmetry/*','tests/*.py','reference/*.py',
    'inputs/*.json','pyproject.toml','requirements-tested.txt')

def release_root():return Path(__file__).resolve().parents[2]

def release_fingerprint(root=None):
    """Release fingerprint: everything that executes or validates a campaign. Bound into receipts and manifests."""
    root=Path(root or release_root());h=hashlib.sha256();files=set()
    for pattern in RELEASE_GLOBS:files.update(p for p in root.glob(pattern) if p.is_file())
    if not files:raise RuntimeError(f'No release files under {root}')
    for p in sorted(files,key=lambda q:q.relative_to(root).as_posix()):
        h.update(p.relative_to(root).as_posix().encode()+b'\0');h.update(p.read_bytes())
    return h.hexdigest()

def runtime():
    import numpy,scipy,numba
    return {'python':platform.python_version(),'numpy':numpy.__version__,'scipy':scipy.__version__,'numba':numba.__version__}

def atomic_json(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    blob=canonical(obj)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
        dfd=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(dfd)
        finally:os.close(dfd)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def envelope(kind,config,payload):
    record={'schema':SCHEMA,'kind':kind,'config':config,'payload':payload}
    record['sha256']=digest(record);return record

def read_envelope(path,kind=None,config=None):
    row=json.loads(Path(path).read_text());saved=row.pop('sha256',None)
    if saved!=digest(row):raise ValueError(f'Checksum failure: {path}')
    if row.get('schema')!=SCHEMA or (kind and row.get('kind')!=kind):raise ValueError('Schema/kind mismatch')
    if config is not None and row.get('config')!=config:raise ValueError('Configuration/source/dependency mismatch')
    row['sha256']=saved;return row

MAINTENANCE_ENV='LRI_MAINTENANCE_MARKER'

@contextmanager
def claim(path):
    """Held by the solver process itself, not by an external supervisor.

    flock excludes processes on this node; the generation lease excludes other nodes
    (BeeGFS without global locks makes flock node-local). Raises lease.Claimed when owned.
    """
    from .lease import Lease,Claimed
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    marker=os.environ.get(MAINTENANCE_ENV)
    if marker and Path(marker).exists():raise Claimed(f'Campaign is in maintenance: {marker}')
    with path.open('a+') as f:
        try:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise Claimed(f'Item is already claimed: {path}') from None
        f.seek(0);f.truncate();f.write(str(os.getpid())+'\n');f.flush()
        try:
            lease=Lease(path);lease.acquire()
            try:yield
            finally:lease.release()
        finally:fcntl.flock(f.fileno(),fcntl.LOCK_UN)

def validate_result(row,config):
    def finite(x):
        if isinstance(x,float) and not math.isfinite(x):raise ValueError('Non-finite result')
        if isinstance(x,dict):
            for y in x.values():finite(y)
        if isinstance(x,list):
            for y in x:finite(y)
    finite(row)
    for key,value in [('bath_cut',config['bath_cut']),('nz_per_parity',config['nz']),('auxiliary_oscillator_size',config['osc']),('delta',config['delta']),('backend',config['resolved_backend'])]:
        if row.get(key)!=value:raise ValueError(f'Result metadata mismatch: {key}')
    tune=max(1e-8,5*config['tuning_tol'])
    if row.get('tuning_residual',float('inf'))>tune:raise ValueError('Tuning gate')
    if row.get('max_eigenvector_residual',float('inf'))>config['residual_tol']:raise ValueError('Eigenvector gate')
    if row.get('max_orthogonality_residual',float('inf'))>1e-9:raise ValueError('Orthogonality gate')
    if abs(row['Delta_sigma_measured']-config['delta'])>tune:raise ValueError('Spin gap gate')
    if abs(row['Delta_shadow_measured']-(1-config['delta']))>tune:raise ValueError('Shadow gap gate')
    if not isinstance(row.get('theta'),list) or len(row['theta'])!=2:raise ValueError('Missing coupling state')
    if row.get('g',0)<=0:raise ValueError('Nonpositive quartic coupling')
    for key in ('even_gaps','odd_gaps'):
        v=row.get(key,[])
        if len(v)<3 or any(v[i+1]<v[i]-1e-10 for i in range(len(v)-1)):raise ValueError('Spectrum ordering gate')
    if abs(row['Delta_thermal']-row['even_gaps'][1])>1e-12:raise ValueError('Thermal gap metadata gate')
    window=config.get('window','none')
    if row.get('window','none')!=window:raise ValueError('Result metadata mismatch: window')
    if window!='none':
        wc=row.get('window_correction')
        if not isinstance(wc,dict) or wc.get('mode')!=config.get('window_mode'):raise ValueError('Missing window record')
        D=wc.get('D_by_N',{});Ev=wc.get('Ev',{});tol=config['window_tol']
        if sorted(map(int,D))!=list(range(config['bath_cut']+1)) or D.get('0')!=0.:raise ValueError('Window table gate')
        top=Ev.get(str(config['bath_cut']-(config['bath_cut']&1)))
        # Absolute ceiling (PLAN G2), independent of the configurable iteration tolerance.
        if top is None or not wc.get('top_fixed_point_residual',float('inf'))<=1e-11:raise ValueError('Window fixed-point gate')
        for lev,r in wc.get('sublevel_fixed_point_residuals',{}).items():
            if not r<=1e-11 or lev not in Ev:raise ValueError('Window sublevel fixed-point gate')
