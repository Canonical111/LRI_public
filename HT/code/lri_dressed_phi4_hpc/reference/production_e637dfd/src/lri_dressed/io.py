"""Single-process item claims, atomic records and strict provenance validation."""
from __future__ import annotations
import hashlib,json,os,sys,platform,math,fcntl,tempfile
from pathlib import Path
from contextlib import contextmanager

SCHEMA='lri-dressed-phi4-v1'

def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(obj):return hashlib.sha256(canonical(obj)).hexdigest()

def source_fingerprint():
    root=Path(__file__).parent;h=hashlib.sha256()
    for p in sorted(root.glob('*.py')):h.update(p.name.encode());h.update(p.read_bytes())
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

@contextmanager
def claim(path):
    """Lock remains held by the solver, not by an external supervisor."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+') as f:
        try:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError(f'Item is already claimed: {path}') from None
        f.seek(0);f.truncate();f.write(str(os.getpid())+'\n');f.flush()
        try:yield
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
