"""Exact fused numerator p*a+q*b. Reduces memory without altering cancellations."""
import ctypes
from pathlib import Path
from sympy.polys.domains import QQ
import native_poly as np
import factored_field as ff
LIB=ctypes.CDLL(str(Path(__file__).with_name('poly_fused.so')))
LIB.add_products_qq.argtypes=[ctypes.c_char_p]*4;LIB.add_products_qq.restype=ctypes.c_void_p;LIB.free_result.argtypes=[ctypes.c_void_p]
ORIGINAL=ff.Frac.__add__
COUNTS={'fused':0,'fallback':0}
def fused(p,a,q,b):
 strings=[np.encoded(v) for v in (p,a,q,b)]
 if any(v is None for v in strings):return p*a+q*b
 ptr=LIB.add_products_qq(*strings)
 if not ptr:raise ArithmeticError('exact fused multiplication failed')
 try:raw=ctypes.string_at(ptr)
 finally:LIB.free_result(ptr)
 terms={}
 for line in raw.splitlines():
  k,c=line.split();n,*d=c.split(b'/');terms[np.unpack(int(k),p.ring.ngens)]=QQ(int(n),int(d[0]) if d else 1)
 COUNTS['fused']+=1
 return p.ring.from_dict(terms)
def add(self,other):
 other=self.K(other)
 if not self:return other
 if not other:return self
 ds=self.denf.copy();mul1=self.K.ring.one;mul2=self.K.ring.one;common={}
 for f,m in other.denf.items():
  prev=ds.get(f,0)
  if m>prev:mul1*=f**(m-prev);ds[f]=m
  if prev:common[f]=min(m,prev)
 for f,m in self.denf.items():
  prev=other.denf.get(f,0)
  if m>prev:mul2*=f**(m-prev)
 if len(self.numer)*len(mul1)+len(other.numer)*len(mul2)>2000:
  n=fused(self.numer,mul1,other.numer,mul2)
 else:
  COUNTS['fallback']+=1;n=self.numer*mul1+other.numer*mul2
 if not n:return self.K.zero
 if common:
  n,rem=ff.cancel_factors(n,common)
  for f,m in common.items():
   ds[f]-=m-rem.get(f,0)
   if not ds[f]:del ds[f]
 return ff.Frac(self.K,n,ds)
def install():ff.Frac.__add__=add;ff.Frac.__radd__=add
if __name__=='__main__':
 import random,time,json
 from sympy.polys.rings import ring
 st=time.time();r=random.Random(230121);R,*x=ring('e,u,v,w,t,q,r,h,Z2,Z3,Z4,Z5,Z6',QQ)
 for i in range(200):
  def poly(n):return R.from_dict({tuple(r.randrange(5) for _ in range(4))+(0,)*9:QQ(r.randrange(-50,50),r.randrange(1,20)) for _ in range(n)})
  p,a,q,b=poly(150),poly(12),poly(160),poly(12)
  assert fused(p,a,q,b)==np.ORIGINAL(p,a)+np.ORIGINAL(q,b)
 print('FUSED_POLYNOMIAL_PASS',COUNTS,time.time()-st,flush=True)
 Path('../native_fused_checks.json').write_text(json.dumps({'random_exact_cases':200,'counts':COUNTS,'exact_equal':True,'seconds':time.time()-st},indent=2))
