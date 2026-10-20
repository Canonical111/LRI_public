"""Exact modular images accelerate divisor rejection, never acceptance."""
from pathlib import Path
from functools import lru_cache
import ctypes
import factored_field as ff
import exact_acceleration as ex
import native_poly as np
ORIGINAL=ex.modular_coeffs
LIB=ctypes.CDLL(str(Path(__file__).with_name('poly_mod.so')))
LIB.spec_qq.argtypes=[ctypes.c_char_p,ctypes.c_int];LIB.spec_qq.restype=ctypes.c_void_p
LIB.free_result.argtypes=[ctypes.c_void_p]
@lru_cache(maxsize=200)
def modular_coeffs(p,idx):
    text=np.encoded(p)
    if text is None or idx>=8:return ORIGINAL(p,idx)
    ptr=LIB.spec_qq(text,idx)
    if not ptr:return None
    try:out=ctypes.string_at(ptr)
    finally:LIB.free_result(ptr)
    return list(map(int,out.split())),ex.VALUES,ex.PRIME

def install():ff.modular_coeffs=modular_coeffs
if __name__=='__main__':
    import random,json,time
    from sympy.polys.domains import QQ
    from sympy.polys.rings import ring
    random.seed(8645);R,*x=ring('e,u,v,w,t,q,r,h,Z2,Z3,Z4,Z5,Z6',QQ);st=time.time()
    for i in range(300):
        p=R.from_dict({tuple(random.randrange(5) if j<6 else 0 for j in range(13)):QQ(random.randint(-10000,10000),random.randint(1,1000000)) for _ in range(150)})
        for idx in range(6):assert modular_coeffs(p,idx)==ORIGINAL(p,idx),(i,idx)
    out={'test':'Native modular images versus original exact rational reduction modulo prime','polynomials':300,'coefficient_vector_comparisons':1800,'all_equal':True,'seconds':time.time()-st}
    Path(__file__).parent.parent.joinpath('native_mod_checks.json').write_text(json.dumps(out,indent=2));print(out)
