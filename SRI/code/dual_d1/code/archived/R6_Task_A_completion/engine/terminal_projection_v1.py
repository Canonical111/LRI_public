"""Exact rational cutoff functionals for the final one-dimensional integral.

The variable q is scaled to q=e*z. Rational coefficients are homogeneous of
scaled degrees kappa=0 or 1. The final constant at infinity is computed by
integration by parts, with nonempty pure-GPL constants projected to zero.
The lower-endpoint scaling anomaly is included explicitly. No period values
or guessed RG coefficients are used.
"""
from fractions import Fraction as F
from functools import lru_cache
from math import comb,factorial
from collections import defaultdict

def trim(p):
 p=list(p)
 while p and not p[-1]:p.pop()
 return tuple(p)
def padd(p,q):
 r=list(p)+[F(0)]*max(0,len(q)-len(p))
 for i,c in enumerate(q):r[i]+=c
 return trim(r)
def pmul(p,q):
 if not p or not q:return ()
 r=[F(0)]*(len(p)+len(q)-1)
 for i,c in enumerate(p):
  for j,d in enumerate(q):r[i+j]+=c*d
 return trim(r)
def pscale(p,c):return trim([c*v for v in p])
def deriv(p):return tuple(i*p[i] for i in range(1,len(p)))
def integrate_exp(p,a):
 # Unique polynomial P with P'+a*P=p, a != 0.
 out=();q=p;j=0
 while q:
  out=padd(out,pscale(q,F((-1)**j,a**(j+1))));q=deriv(q);j+=1
 return out

@lru_cache(maxsize=24000)
def large(word,n):
 if not word:return (F(1),) if n==0 else ()
 if n==0:return (F(0),)*len(word)+(F(1,factorial(len(word))),)
 rhs=()
 for j in range(n+1):rhs=padd(rhs,pscale(large(word[1:],n-j),word[0]**j))
 return integrate_exp(rhs,-n)

@lru_cache(maxsize=24000)
def small(word,n):
 if not word:return (F(1),) if n==0 else ()
 if n==0:
  return (F(0),)*len(word)+(F(1,factorial(len(word))),) if all(a==0 for a in word) else ()
 a=word[0]
 if a==0:rhs=small(word[1:],n)
 else:
  rhs=()
  for j in range(n):rhs=padd(rhs,pscale(small(word[1:],n-1-j),-a**(-j-1)))
 return integrate_exp(rhs,n)

def c0(p):return p[0] if p else F(0)

@lru_cache(maxsize=24000)
def constant_poly(k,word):
 if not word:return F(0)
 a=word[0]
 return (c0(large(word,k+1))-sum(a**j*constant_poly(k-j,word[1:]) for j in range(k+1)))/(k+1)

@lru_cache(maxsize=24000)
def constant_pole(a,p,word):
 if p==1:return F(0)
 if not word:return (-a)**(1-p)/(p-1) if a else F(0)
 boundary=c0(small(word,p-1))/(p-1) if a==0 else F(0)
 b=word[0]
 if b==a:return boundary+constant_pole(a,p,word[1:])/(p-1)
 # Simple poles in the product have zero projected constant at infinity.
 subtotal=F(0)
 for j in range(p-2):
  subtotal+=F((-1)**j)*(a-b)**(-j-1)*constant_pole(a,p-1-j,word[1:])
 return boundary+subtotal/(p-1)

@lru_cache(maxsize=20000)
def apart(num,den):
 # den = sorted (root, multiplicity), all factors monic.
 dpoly=(F(1),)
 for a,p in den:dpoly=pmul(dpoly,tuple(F(comb(p,j))*(-a)**(p-j) for j in range(p+1)))
 rem=list(num);quo=[F(0)]*max(0,len(rem)-len(dpoly)+1)
 while rem and len(rem)>=len(dpoly):
  k=len(rem)-len(dpoly);c=rem[-1]/dpoly[-1];quo[k]+=c
  for j,b in enumerate(dpoly):rem[j+k]-=c*b
  while rem and not rem[-1]:rem.pop()
 poles=[]
 for a,p in den:
  local=[sum(rem[j]*comb(j,k)*a**(j-k) for j in range(k,len(rem))) for k in range(p)]
  inverse=[F(1)]+[F(0)]*(p-1)
  for b,m in den:
   if b==a:continue
   fac=[F((-1)**j*comb(m+j-1,j))*(a-b)**(-m-j) for j in range(p)]
   inverse=[sum(inverse[k]*fac[j-k] for k in range(j+1)) for j in range(p)]
  for j in range(p):
   c=sum(local[k]*inverse[j-k] for k in range(j+1))
   if c:poles.append((a,p-j,c))
 return trim(quo),tuple(poles)

@lru_cache(maxsize=10000)
def shift_positive(N,a,hp,d):
 if d<0:return F(0)
 h=tuple([F(0)]+[F(-N**k,k) for k in range(1,d+1)])
 v=(F(1),)
 for _ in range(hp):v=pmul(v,h)[:d+1]
 return sum(v[k]*comb(a,d-k)*(-N)**(d-k) for k in range(len(v)) if 0<=d-k<=a)

@lru_cache(maxsize=80000)
def poly_functional(k,word,kappa,N,p,m):
 if m<0:return F(0)
 out=F(0)
 # Integration constant at infinity.
 if kappa==p and m==0:out+=constant_poly(k,word)
 for n in range(k+2):
  a=k-n+1;d=a+p-kappa
  if d<0:continue
  b=large(word,n)
  if a==0:
   integ=(F(0),)+tuple(c/F(j+1) for j,c in enumerate(b))
  else:integ=integrate_exp(b,a)
  for j,c in enumerate(integ):
   if j>=m and c:out+=c*comb(j,m)*(-1)**m*shift_positive(N,a,j-m,d)
 return out

@lru_cache(maxsize=80000)
def pole_functional(a,order,word,kappa,p,m):
 if kappa!=p or m<0:return F(0)
 if m==0:return constant_pole(a,order,word)
 if m!=1:raise ValueError('This implementation requests only log degree 0 or 1')
 # Integral at infinity contributes a single log only for a simple pole
 # and an empty word. The second term restores the original-q lower Reg.
 infinity=-F(1) if order==1 and not word else F(0)
 lower=c0(small(word,order-1)) if a==0 else F(0)
 return infinity+lower

@lru_cache(maxsize=100000)
def normalized_functional(num,den,word,kappa,N,p,m):
 if p>0 or kappa not in (0,1) or m not in (0,1):raise ValueError((kappa,p,m))
 pol,poles=apart(num,den)
 val=sum(c*poly_functional(k,word,kappa,N,p,m) for k,c in enumerate(pol) if c)
 for a,o,c in poles:val+=c*pole_functional(a,o,word,kappa,p,m)
 return val

def rational_field_fraction(c):return F(int(c.numerator),int(c.denominator))

@lru_cache(maxsize=12000)
def scale_field(coef,qindex):
 # Adapter for archived exact field coefficients. No numerical substitutions.
 numerator=coef.numer;D=0;constant=F(1);roots={}
 for f,m in coef.denf.items():
  aa=bb=F(0)
  for mon,c in f.items():
   if any(v for i,v in enumerate(mon) if i not in (0,qindex)):raise ValueError(('spectator denominator',mon))
   if mon[0]==1 and mon[qindex]==0:aa+=rational_field_fraction(c)
   elif mon[0]==0 and mon[qindex]==1:bb+=rational_field_fraction(c)
   else:raise ValueError(('nonhomogeneous denominator',mon))
  D+=m
  if bb:
   constant*=bb**m;a=-aa/bb;roots[a]=roots.get(a,0)+m
  else:constant*=aa**m
 groups={}
 for mon,c in numerator.items():
  if any(v for i,v in enumerate(mon) if i not in (0,qindex)):raise ValueError(('spectator numerator',mon))
  kappa=mon[0]+mon[qindex]-D+1
  if kappa not in (0,1):raise ValueError(('unexpected homogeneity',kappa,str(coef)))
  d=groups.setdefault(kappa,{})
  d[mon[qindex]]=d.get(mon[qindex],F(0))+rational_field_fraction(c)/constant
 out=[]
 for kappa,d in groups.items():
  if not any(d.values()):continue
  num=trim([d.get(j,F(0)) for j in range(max(d)+1)])
  scalar=next(c for c in num if c);num=tuple(c/scalar for c in num)
  out.append((kappa,scalar,num,tuple(sorted(roots.items()))))
 return tuple(out)

def field_letter(a,qindex,e):
 r=a/e
 if r.denf or any(any(mon) for mon in r.numer):
  # General constant fraction, normally the denominator is already scalar.
  expr=r.as_expr()
  if not getattr(expr,'is_Rational',False):raise ValueError(('nonconstant letter',str(a)))
  return F(int(expr.p),int(expr.q))
 return sum((rational_field_fraction(c) for c in r.numer.values()),F(0))

def apply_field(coef,word,explicit,N,demands=((0,1),(-2,0),(-2,1),(-1,0),(-1,1))):
 tail=0
 for a in reversed(word):
  if a:break
  tail+=1
 ans=[F(0)]*len(demands)
 for kappa,scalar,num,den in scale_field(coef,N):
  for d,(p,m) in enumerate(demands):
   for j in range(min(tail,m-explicit)+1):
    w=word[:-j] if j else word
    ans[d]+=scalar*normalized_functional(num,den,w,kappa,N,p,m-explicit-j)/factorial(j)
 return ans

def clear_caches():
 for f in (large,small,constant_poly,constant_pole,apart,shift_positive,poly_functional,pole_functional,normalized_functional,scale_field):f.cache_clear()
