"""Optional C++ acceleration, content-addressed atomic build outside the source tree."""
from pathlib import Path
import ctypes, functools, hashlib, os, platform, subprocess, tempfile
import numpy as np
from numba import get_num_threads

@functools.lru_cache(None)
def library():
    src=Path(__file__).with_name('native.cpp');compiler=os.environ.get('CXX','c++')
    version=subprocess.check_output([compiler,'--version'],text=True).splitlines()[0]
    flags=['-O3','-std=c++17','-fPIC','-shared','-fopenmp','-fno-fast-math','-ffp-contract=off']
    digest=hashlib.sha256(src.read_bytes()+(' '.join(flags)+version+platform.machine()).encode()).hexdigest()[:24]
    cache=Path(os.environ.get('LRI_COEFF_NATIVE_CACHE',str(Path.home()/'.cache/lri_coeff')));cache.mkdir(parents=True,exist_ok=True)
    dest=cache/f'native_{digest}.so'
    if not dest.exists():
        fd,tmp=tempfile.mkstemp(prefix='build_',suffix='.so',dir=cache);os.close(fd)
        try:
            subprocess.run([compiler,*flags,str(src),'-o',tmp],check=True)
            os.replace(tmp,dest)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    lib=ctypes.CDLL(str(dest))
    lib.lri_ld_bits.restype=ctypes.c_int;lib.lri_ld_size.restype=ctypes.c_int
    if lib.lri_ld_bits()<64 or lib.lri_ld_size()!=np.dtype(np.longdouble).itemsize:
        raise RuntimeError('Native/NumPy extended accumulator ABI mismatch; use --backend numba.')
    ip=ctypes.c_int;vp=ctypes.c_void_p;ll=ctypes.c_int64
    lib.lri_apply.argtypes=[ip,ip,ip,ip,vp,vp,vp,vp,vp,vp,ip,vp,vp,ll,ip,vp,ctypes.c_double];lib.lri_apply.restype=ip
    lib.lri_dot.argtypes=[vp,ip,vp,ip,ip,ll,ip,vp];lib.lri_dot.restype=ip
    lib.lri_project.argtypes=[vp,vp,ip,vp,ll,ip];lib.lri_project.restype=None
    return lib

def apply(g,x,d,n,creation,add=None,scale=1.):
    if x.dtype!=np.float64 or not x.flags.c_contiguous:raise ValueError('Expected contiguous float64 input')
    if g.mode.dtype!=np.uint16:raise ValueError('Native mode indices exceed uint16; use numba backend')
    y=np.empty((n,d+1));p,neighbor=(g.cptr,g.child) if creation else (g.bptr,g.parent)
    err=library().lri_apply(int(creation),neighbor.dtype.itemsize,d+1,x.shape[1],p.ctypes.data,neighbor.ctypes.data,g.edge.ctypes.data,g.mode.ctypes.data,g.amp.ctypes.data,g.u.ctypes.data,g.u.shape[1],x.ctypes.data,y.ctypes.data,n,get_num_threads(),add.ctypes.data if add is not None else None,scale)
    if err:raise RuntimeError(f'Native contraction rejected arguments: {err}')
    return y

def poly_dot(x,y,d):
    x=np.ascontiguousarray(x);y=np.ascontiguousarray(y)
    if x.dtype!=np.float64 or y.dtype!=np.float64:raise ValueError('Expected float64 input')
    out=np.zeros(d+1,dtype=np.longdouble)
    err=library().lri_dot(x.ctypes.data,x.shape[1],y.ctypes.data,y.shape[1],d+1,len(x),get_num_threads(),out.ctypes.data)
    if err:raise RuntimeError(f'Native dot arguments: {err}')
    return out

def project(g,m,v,n):
    library().lri_project(m.ctypes.data,v.ctypes.data,m.shape[1],g.Jabs.ctypes.data,n,get_num_threads())
