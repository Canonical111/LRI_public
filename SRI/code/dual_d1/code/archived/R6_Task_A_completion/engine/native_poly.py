"""Optional exact GMP multiplication acceleration for immutable QQ polynomials.
Packing is used only if each exponent <=63 in the first eight variables and
all later exponents vanish. The sum therefore cannot carry between 7-bit slots.
All unsupported inputs use the unmodified SymPy multiplication.
"""
import ctypes
from pathlib import Path
from functools import lru_cache
from sympy.polys.rings import PolyElement
from sympy.polys.domains import QQ
LIB=ctypes.CDLL(str(Path(__file__).with_name('poly_multiply.so')))
LIB.multiply_qq.argtypes=[ctypes.c_char_p,ctypes.c_char_p];LIB.multiply_qq.restype=ctypes.c_void_p
LIB.free_result.argtypes=[ctypes.c_void_p]
ORIGINAL=PolyElement.__mul__
COUNTS={'native':0,'fallback':0}
NATIVE_PRODUCT_THRESHOLD=10000
@lru_cache(maxsize=40000)
def pack(mon):
 if any(mon[8:]) or any(n>63 or n<0 for n in mon[:8]):return None
 return sum(n<<(7*i) for i,n in enumerate(mon[:8]))
@lru_cache(maxsize=40000)
def unpack(key,ngens):return tuple((key>>(7*i))&127 if i<8 else 0 for i in range(ngens))
@lru_cache(maxsize=64)
def encoded(p):
 out=[]
 for mon,c in p.items():
  k=pack(mon)
  if k is None:return None
  out.append(f'{k} {c.numerator}/{c.denominator}\n')
 return ''.join(out).encode()
def multiply(a,b):
 if not isinstance(b,PolyElement) or a.ring is not b.ring or a.ring.domain!=QQ or min(len(a),len(b))<8 or len(a)*len(b)<NATIVE_PRODUCT_THRESHOLD:
  COUNTS['fallback']+=1;return ORIGINAL(a,b)
 aa=encoded(a);bb=encoded(b)
 if aa is None or bb is None:
  COUNTS['fallback']+=1;return ORIGINAL(a,b)
 ptr=LIB.multiply_qq(aa,bb)
 if not ptr:raise ArithmeticError('Native exact multiplication failed')
 try:data=ctypes.string_at(ptr)
 finally:LIB.free_result(ptr)
 terms={};ngens=a.ring.ngens
 for row in data.splitlines():
  k,c=row.split();parts=c.split(b'/');n=int(parts[0]);d=int(parts[1]) if len(parts)>1 else 1
  terms[unpack(int(k),ngens)]=QQ(n,d)
 COUNTS['native']+=1
 return a.ring.from_dict(terms)
def install():PolyElement.__mul__=multiply
if __name__=='__main__':
 import random,time,json
 from sympy.polys.rings import ring
 R,*_=ring('e,u,v,w,t,q,r,h,Z2,Z3,Z4,Z5,Z6',QQ);random.seed(43051)
 tests=300;st=time.time();NATIVE_PRODUCT_THRESHOLD=0
 for j in range(tests):
  def poly():
   d={}
   for k in range(random.randint(3,55)):
    mon=tuple(random.randrange(5) for _ in range(4))+(0,)*9
    d[mon]=QQ(random.randint(-50,50),random.randint(1,13))
   return R.from_dict(d)
  a,b=poly(),poly();p=ORIGINAL(a,b);q=multiply(a,b);assert p==q
 assert COUNTS['native']>200, 'Native test coverage was not exercised'
 report={'test':'GMP multiplication versus unmodified SymPy (native selection forced for test)','random_exact_equal':tests,'seconds':time.time()-st,'counts':COUNTS}
 Path(__file__).parent.parent.joinpath('native_poly_checks.json').write_text(json.dumps(report,indent=2));print(report)
