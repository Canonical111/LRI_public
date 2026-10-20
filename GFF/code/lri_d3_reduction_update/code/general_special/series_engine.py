"""Exact homogeneous Laurent jets along d=q*z.
Coefficients are polynomials/rational functions in q and named constants.
"""
from functools import lru_cache
import math,itertools
import sympy as s
import analytic_core as ac
z,d=ac.z,ac.d
q=s.Symbol('q');p,l,E,C,B4,Z3,Z5,g,Q,K=s.symbols('pi log2 Euler Catalan beta4 zeta3 zeta5 GammaQuarter Q K')
# Base r in an affine exponent denotes r*D (physical dimension).
# The regulator slopes, and the dummy index shift q*z, are not rescaled.
DIM=s.Symbol('DIM',positive=True)
Q,Z,K,M=s.symbols('Q Z K M')
A=s.Symbol('A')
HH=Z/Q
RR=-s.Symbol('u2')/2
MAXREL=4

def clean(x):
 x=s.expand(x)
 # Gamma factors that survive power-divergent bubbles.
 gm,g2,g3=s.symbols('gm g2 g3')
 if x.has(gm,g2,g3):
  x=s.expand(x.subs(gm,M*g3/g2**2))
 if x.has(q) and s.denom(x)!=1:x=s.cancel(x)
 return x

def trim(a,hi=None,lo=None):return{k:clean(v)for k,v in a.items()if v!=0 and(hi is None or k<=hi)and(lo is None or k>=lo)}
def add(*args):
 out={}
 for a in args:
  for k,v in a.items():out[k]=out.get(k,0)+v
 return trim(out)
def scale(a,c):return trim({k:v*c for k,v in a.items()})
def shift(a,k):return{i+k:v for i,v in a.items()}
def mul(a,b,hi=None):
 out={}
 for i,x in a.items():
  for j,y in b.items():
   if hi is None or i+j<=hi:out[i+j]=out.get(i+j,0)+x*y
 return trim(out)
def prod(arr,hi):
 if any(not a for a in arr):return{}
 vals=[min(a)for a in arr];out={0:s.S(1)}
 for i,a in enumerate(arr):out=mul(out,a,hi-sum(vals[i+1:]))
 return trim(out,hi)
def inv(a,hi):
 a=trim(a)
 if not a:raise ZeroDivisionError
 k=min(a);c=a[k];out={-k:1/c}
 for n in range(1,hi+k+1):
  out[n-k]=-sum(a.get(k+j,0)*out.get(n-j-k,0)for j in range(1,n+1))/c
 return trim(out)
def div(a,b,hi):
 return mul(a,inv(b,hi-min(a)),hi)if a else{}
def evaluate(a,**vals):
 sub={globals()[k]:v for k,v in vals.items()};return trim({i:v.subs(sub)for i,v in a.items()})

def affine(x):
 x=s.expand(x.subs(d,q*z));r=x.subs(z,0);v=x.coeff(z)
 assert s.expand(x-r-v*z)==0,(x,r,v)
 return r,v

def zet(k):
 return {2:p**2/6,3:Z3,4:p**4/90,5:Z5}[k]
def bet(k):return{2:C,3:p**3/32,4:B4,5:5*p**5/1536}[k]
@lru_cache(None)
def gamma_const(r):
 if r==0:raise ValueError(('pole',r))
 names={s.Rational(1,4):'g1',s.Rational(1,2):'g2',s.Rational(3,4):'g3',s.Rational(-1,4):'gm',s.S(1):'g4'}
 return s.Symbol(names.get(r,'GammaD_'+str(r).replace('/','_').replace('-','m')))
@lru_cache(None)
def psi(n,r):
 # r=0 encodes the shifted Gamma(1+v*z) at an originally zero base.
 names={s.S(0):'j',s.Rational(1,4):'u',s.Rational(1,2):'v',s.Rational(3,4):'w',s.Rational(-1,4):'m',s.S(1):'x'}
 if n==0 and r==s.Rational(1,4):
  return (s.Symbol('v0')+s.Symbol('j0')-A)/2
 return s.Symbol(names.get(r,'psiD_'+str(r).replace('/','_').replace('-','m')+'_')+str(n))

@lru_cache(None)
def gprod(nums,dens,pref=s.S(1),rel=MAXREL):
 # args are tuples (rational base, affine slope in q)
 pref=s.sympify(pref);valuation=0;log=[s.S(0)]*(rel+1)
 for args,sign in [(nums,1),(dens,-1)]:
  for r,v in args:
   if r==0:
    # Gamma(v*z)=Gamma(1+v*z)/(v*z).
    m=0;valuation-=sign
    pref*=((-1)**m/(s.factorial(m)*v))**sign
    for n in range(1,rel+1):
     log[n]+=sign*(psi(n-1,s.S(0))*v**n/s.factorial(n)+sum((v/j)**n/n for j in range(1,m+1)))
   else:
    pref*=gamma_const(r)**sign
    for n in range(1,rel+1):log[n]+=sign*psi(n-1,r)*v**n/s.factorial(n)
 pref=clean(pref);log=list(map(clean,log));ex=[s.S(1)]
 for n in range(1,rel+1):ex.append(clean(sum(k*log[k]*ex[n-k]for k in range(1,n+1))/n))
 return trim({valuation+n:pref*ex[n]for n in range(rel+1)})

@lru_cache(None)
def beta(u,v):
 if u==0 or v==0:return{}
 u=s.sympify(u);v=s.sympify(v)
 nums=tuple(affine(x)for x in[(1-u)/2,(1-v)/2,(u+v-1)/2]);dens=tuple(affine(x)for x in[u/2,v/2,(2-u-v)/2])
 return gprod(nums,dens,gamma_const(s.Rational(1,2)))

TARGET_A=(s.Rational(1,2),)*4+(s.S(1),)
TARGET_B=(s.Rational(1,2),s.Rational(1,2),s.Rational(1,2),s.S(1),s.Rational(1,2))
TARGET_T=(s.Rational(1,2),)*5
@lru_cache(None)
def target_args(args):
 lam=[s.expand(x)for x in ac.complete(args)];crit=[x.subs({z:0,d:0})for x in lam]
 for target in[TARGET_T,TARGET_A,TARGET_B]:
  for per in ac.PERMS5:
   aa=tuple(lam[per[i]]for i in[1,4,2,5,7])
   if tuple(x.subs({z:0,d:0})for x in aa)==target:return target,aa
 raise ValueError(('Unknown critical master',args,crit))

def pole_A(args):
 a,b,c,dd,e=args
 t=s.expand(1-e);p0=s.expand(2-a-c-e);p1=s.expand(2-b-dd-e)
 ap=s.expand((a-c)/2);bp=s.expand((b-dd)/2)
 P=add(shift(scale(beta(s.expand((2-e)/2-ap),e),2/affine(p0)[1]),-1),
       shift(scale(beta(s.expand((2-e)/2-bp),e),2/affine(p1)[1]),-1),
       shift(scale(beta(s.expand(1-p0),s.expand(1-p1)),2/affine(t)[1]),-1),
       {-2:-4/affine(t)[1]*(1/affine(p0)[1]+1/affine(p1)[1])})
 return trim(P,2)

@lru_cache(None)
def a_regular_polynomial():
 import json
 dat=json.loads((__import__('pathlib').Path(__file__).parent/'A_regular.json').read_text())
 return {int(k):s.sympify(v,locals={'A':A}) for k,v in dat['polynomials'].items()}

def a_jet(args):
 slopes=[affine(x)[1] for x in args]
 poly=a_regular_polynomial()
 vv=s.symbols('da db dc dd de')
 return add(pole_A(args),{n:clean(v.subs(dict(zip(vv,slopes)),simultaneous=True)) for n,v in poly.items()})

@lru_cache(None)
def master(*args):
 args=tuple(map(s.expand,args));tag,(a,b,c,dd,e)=target_args(args)
 if tag==TARGET_T:
  lam=[s.expand(x-s.Rational(1,2))for x in ac.complete([a,b,c,dd,e])]
  quadratic=clean(sum(affine(x)[1]**2 for x in lam))
  return{0:3*Q,2:clean(Q*HH*quadratic/4)}
 if tag==TARGET_A:
  return trim(a_jet((a,b,c,dd,e)),2)
 if tag==TARGET_B:
  p1=s.expand(1-dd);p2=s.expand(2-b-dd-e);z1=s.expand(3-a-b-c-dd-e);z2=s.expand(2-c-dd-e)
  u2=prod([beta(1+p1-e,1-p1),beta(e+p2-z1,1-p2)],2)
  u1=prod([beta(e-p1+p2+z2,1+p1-e-z2),beta(1+p1-e-p2,1-p1)],2)
  u0=prod([beta(1+p1-e,1-p1),beta(e+p2,1-p2)],2)
  dif=add(beta(e+p2+z2-z1,1-p2),scale(beta(e+p2-z1,1-p2),-1),scale(beta(e+p2+z2,1-p2),-1),beta(e+p2,1-p2))
  correction=shift(scale(dif,2/affine(p1)[1]),-1)
  reg={2:clean(K*affine(z1)[1]*affine(z2)[1])}
  return trim(add(u2,u1,scale(u0,-1),correction,reg),2)

@lru_cache(None)
def evaluate_expr(ex,hi):
 ex=s.sympify(ex)
 if ex.func==ac.BB:return trim(beta(*ex.args),hi)
 if ex.func==ac.MS:return trim(master(ex.args[0],ex.args[1],ex.args[0],ex.args[1],ex.args[2]),hi)
 if ex.func==ac.JJ:return trim(master(*ex.args),hi)
 if ex.is_Add:return add(*(evaluate_expr(a,hi)for a in ex.args))
 if ex.is_Mul:
  # Compute factors to a safe maximum then truncate products according to valuations.
  arr=[evaluate_expr(a,5)for a in ex.args];return prod(arr,hi)
 if ex.is_Pow:
  base,pow=ex.args
  if base==z:return{int(pow):s.S(1)}
  if pow.is_Integer and pow>=0:return prod([evaluate_expr(base,5)]*int(pow),hi)
 if not ex.has(z,d):return{0:ex}
 # Polynomial prefactors (rare)
 aa=s.Poly(ex.subs(d,q*z),z)
 return trim({int(k[0]):v for k,v in aa.terms()},hi)

if __name__=='__main__':
 print('B(h,1-z)',beta((1-z)/2,1-z),flush=True)
 print('A jet polynomial',a_regular_polynomial(),flush=True)
 print('M critical',master(*TARGET_T),flush=True)
