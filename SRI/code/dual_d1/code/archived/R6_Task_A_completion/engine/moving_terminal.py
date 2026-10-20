"""Exact final rational functional without expanding moving-letter GPLs.
H is a product of GPLs G(a_i*z+b_i; z), encoded as a tuple of words.
Projected constants at zero/infinity of nonempty homogeneous GPLs vanish.
Full derivative uses the same regularized total differential as the archive.
"""
from fractions import Fraction as F
from functools import lru_cache
from collections import defaultdict
from math import comb
import terminal_projection as tp

def canon(H):return tuple(sorted(w for w in H if w))
@lru_cache(maxsize=50000)
def edges(H):
 out=defaultdict(F)
 for k,w in enumerate(H):
  ext=((F(1),F(0)),)+w+((F(0),F(0)),)
  for i,(ai,bi) in enumerate(w):
   low=canon(H[:k]+(w[:i]+w[i+1:],)+H[k+1:])
   for side,sign,other in [('prev',1,ext[i]),('next',-1,ext[i+2])]:
    a=other[0]-ai;b=other[1]-bi
    if a:root=-b/a
    elif b:continue
    elif side=='prev' and i==0 and (ai,bi)==(1,0):root=F(0)
    else:continue
    out[root,low]+=sign
 return tuple((root,low,c) for (root,low),c in out.items() if c)

def intlog(p):return (F(0),)+tuple(c/F(i+1) for i,c in enumerate(p)) if p else ()
@lru_cache(maxsize=100000)
def large(H,n):
 if not H:return (F(1),) if n==0 else ()
 rhs=()
 for a,low,c in edges(H):
  for j in range(n+1):rhs=tp.padd(rhs,tp.pscale(large(low,n-j),c*a**j))
 return intlog(rhs) if n==0 else tp.integrate_exp(rhs,-n)
@lru_cache(maxsize=100000)
def small(H,n):
 if not H:return (F(1),) if n==0 else ()
 rhs=()
 for a,low,c in edges(H):
  if a==0:rhs=tp.padd(rhs,tp.pscale(small(low,n),c))
  else:
   for j in range(n):rhs=tp.padd(rhs,tp.pscale(small(low,n-1-j),-c*a**(-j-1)))
 return intlog(rhs) if n==0 else tp.integrate_exp(rhs,n)
@lru_cache(maxsize=100000)
def const_poly(k,H):
 if not H:return F(0)
 rhs=tp.c0(large(H,k+1))
 for a,low,c in edges(H):
  for j in range(k+1):rhs-=c*a**j*const_poly(k-j,low)
 return rhs/(k+1)
@lru_cache(maxsize=100000)
def const_pole(a,p,H):
 if p==1:return F(0)
 if not H:return (-a)**(1-p)/(p-1) if a else F(0)
 out=tp.c0(small(H,p-1))/(p-1) if not a else F(0)
 for b,low,c in edges(H):
  if b==a:out+=c*const_pole(a,p,low)/(p-1)
  else:
   for j in range(p-2):out+=c*F((-1)**j)*(a-b)**(-j-1)*const_pole(a,p-1-j,low)/(p-1)
 return out
@lru_cache(maxsize=100000)
def poly_functional(k,H,kappa,N,p=0,m=0):
 out=F(0)
 if kappa==p and m==0:out+=const_poly(k,H)
 for n in range(k+2):
  a=k-n+1;d=a+p-kappa
  if d<0:continue
  b=large(H,n)
  integ=intlog(b) if a==0 else tp.integrate_exp(b,a)
  for j,c in enumerate(integ):
   if j>=m and c:out+=c*comb(j,m)*(-1)**m*tp.shift_positive(N,a,j-m,d)
 return out
@lru_cache(maxsize=100000)
def functional(num,den,H,kappa,N,p=0,m=0):
 if p>0 or kappa not in (0,1):raise ValueError((kappa,p))
 pol,rem=tp.quotient(num,den)
 out=sum(c*poly_functional(k,H,kappa,N,p,m) for k,c in enumerate(pol) if c)
 if kappa==p:
  assert m==0
  _,poles=tp.apart(rem,den)
  out+=sum(c*const_pole(a,o,H) for a,o,c in poles)
 return out

def apply_field(coef,H,N,qindex,demands=((0,0),(-2,0),(-1,0))):
 out=[F(0)]*len(demands)
 for kappa,c,num,den in tp.scale_field(coef,qindex):
  for i,(p,m) in enumerate(demands):out[i]+=c*functional(num,den,H,kappa,N,p,m)
 return out

def affine_letter(a,idx,e,GEN):
 from hyperlog_core import K,sub
 slope=a.diff(GEN[idx]);inter=sub(a,idx,K.zero)/e
 if slope.denf or inter.denf:raise ValueError(('nonpolynomial affine letter',a))
 ss=sum((tp.rational_field_fraction(v) for m,v in slope.numer.items() if not any(m)),F(0))
 bb=sum((tp.rational_field_fraction(v) for m,v in inter.numer.items() if not any(m)),F(0))
 assert slope==K(ss.numerator)/ss.denominator and inter==K(bb.numerator)/bb.denominator
 return (ss,bb)

def clear():
 for f in [edges,large,small,const_poly,const_pole,poly_functional,functional]:f.cache_clear()
 tp.clear_caches()

if __name__=='__main__':
 import random,json,time
 from pathlib import Path
 import rebuild_rational
 from hyperlog_core import K,e,GEN,endpoint_fibrate,shuffle
 random.seed(7491);st=time.time();done=0
 for z in range(150):
  choices=[(F(0),F(-1)),(F(0),F(-2)),(F(0),F(0)),(F(1),F(1)),(F(1),F(2)),(F(1),F(0))]
  wa=tuple(random.choice(choices) for _ in range(random.randrange(1,4)))
  wb=tuple((F(0),F(random.choice([-1,-2,0]))) for _ in range(random.randrange(0,3)))
  H=canon((wa,wb));kappa=random.randrange(2)
  den=((F(random.choice([-2,-1,0])),random.randrange(1,4)),)
  num=tuple(F(random.randrange(-2,3)) for _ in range(random.randrange(1,4)))
  ref=[F(0)]*3
  for ww,c in endpoint_fibrate(tuple(K(a.numerator)/a.denominator*GEN[4]+K(b.numerator)/b.denominator*e for a,b in wa),4).items():
   fixed=tuple(tp.field_letter(a,4,e) for a in ww)
   for w,mu in shuffle(fixed,tuple(b for a,b in wb)).items():
    cc=tp.rational_field_fraction(next(iter(c.numer.values()))) if c else F(0)
    for i,(p,m) in enumerate(((0,0),(-2,0),(-1,0))):ref[i]+=cc*mu*tp.normalized_functional(num,den,w,kappa,5,p,m)
  actual=[functional(num,den,H,kappa,5,p,m) for p,m in ((0,0),(-2,0),(-1,0))]
  assert actual==ref,(H,num,den,kappa,actual,ref)
  done+=1
 out={'random_tests':done,'comparison':'moving-letter direct functional versus full fibration and ordinary shuffle words','exact_equal':True,'seconds':time.time()-st}
 Path(__file__).parent.parent.joinpath('moving_terminal_checks.json').write_text(json.dumps(out,indent=2));print(out)
