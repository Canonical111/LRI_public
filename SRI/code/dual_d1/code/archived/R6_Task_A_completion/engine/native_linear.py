"""Optional exact GMP synthetic division by affine factors.
Only total numerator degree <=60 in the first eight variables is packed;
all other cases retain the original exact implementation. A native result
includes its full remainder. The modular rejection test never accepts a
cancellation, and successful cancellation always has exactly zero remainder.
"""
from pathlib import Path
from functools import lru_cache
import ctypes
from sympy.polys.domains import QQ
import factored_field as ff
import native_poly as np
LIB=ctypes.CDLL(str(Path(__file__).with_name('poly_divide.so')))
LIB.divide_linear_qq.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int];LIB.divide_linear_qq.restype=ctypes.c_void_p
LIB.free_result.argtypes=[ctypes.c_void_p]
ORIGINAL=ff.divide_linear_cached
COUNTS={'native':0,'rejected':0,'fallback':0}

def divide_raw(p,f,idx):
    a=np.encoded(p);b=np.encoded(f)
    if a is None or b is None:return None
    ptr=LIB.divide_linear_qq(a,b,idx)
    if not ptr:raise ArithmeticError('Native linear division failed')
    try:data=ctypes.string_at(ptr)
    finally:LIB.free_result(ptr)
    def poly(txt):
        out={}
        for line in txt.splitlines():
            k,c=line.split();co=c.split(b'/');out[np.unpack(int(k),p.ring.ngens)]=QQ(int(co[0]),int(co[1]) if len(co)>1 else 1)
        return p.ring.from_dict(out)
    q,r=data.split(b'#\n');return poly(q),poly(r)

@lru_cache(maxsize=500)
def divide(p,f):
    info=ff.lininfo(f)
    if info is None or len(p)<12 or any(any(m[8:]) or sum(m[:8])>60 for m in p):
        COUNTS['fallback']+=1;return ORIGINAL(p,f)
    if ff.cannot_divide(p,f,info):
        COUNTS['rejected']+=1;return p.ring.zero,p
    ans=divide_raw(p,f,info[0])
    if ans is None:
        COUNTS['fallback']+=1;return ORIGINAL(p,f)
    COUNTS['native']+=1;return ans

def install():ff.divide_linear_cached=divide
if __name__=='__main__':
    import random,json,time
    from sympy.polys.rings import ring
    random.seed(14623);R,*x=ring('e,u,v,w,t,q,r,h,Z2,Z3,Z4,Z5,Z6',QQ);st=time.time()
    cases=300
    for i in range(cases):
        idx=random.randrange(4);f=R.zero
        for j in range(idx,5):f+=x[j]*random.choice([-3,-2,1,2,3])
        f+=random.randint(-3,3)
        q=R.from_dict({tuple(random.randrange(4) if j<5 else 0 for j in range(13)):QQ(random.randint(-10,10),random.randint(1,7)) for _ in range(35)})
        r=R.from_dict({tuple(random.randrange(3) if j<5 and j!=idx else 0 for j in range(13)):QQ(random.randint(-8,8),random.randint(1,5)) for _ in range(8)}) if i%2 else R.zero
        p=f*q+r;actual=divide_raw(p,f,idx);assert actual==(q,r),(i,actual,(q,r))
    out={'test':'GMP linear division versus constructed exact quotient and remainder','cases':cases,'divisible_cases':150,'nonzero_remainder_cases':150,'all_equal':True,'seconds':time.time()-st}
    Path(__file__).parent.parent.joinpath('native_linear_checks.json').write_text(json.dumps(out,indent=2));print(out)
