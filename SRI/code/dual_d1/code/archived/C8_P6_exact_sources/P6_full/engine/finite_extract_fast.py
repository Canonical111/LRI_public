"""Exact selected finite cutoff coefficient. No symbolic series solver or root finding.
Laurent expansion is finite rational long division. Constant periods are kept.
"""
import sympy as s
from functools import lru_cache
from math import factorial
import asymptotic_gpl as ag
from read_expression import parse

@lru_cache(maxsize=50000)
def rational_laurent(text,pmax=0):
 ex=parse(text);num,den=ex.as_numer_denom()
 np=s.Poly(num,ag.E).as_dict();dp=s.Poly(den,ag.E).as_dict()
 if not np:return {}
 a=min(k[0] for k in np);b=min(k[0] for k in dp);start=a-b;count=pmax-start
 if count<0:return {}
 nn={k[0]-a:c for k,c in np.items()};dd={k[0]-b:c for k,c in dp.items()};out=[]
 assert dd[0]!=0
 for k in range(count+1):out.append(s.expand((nn.get(k,0)-sum(c*out[k-j] for j,c in dd.items() if 1<=j<=k))/dd[0]))
 return {start+k:c for k,c in enumerate(out) if c}

@lru_cache(maxsize=200000)
def big_coefficient(word,n,k):
 if k<0:return s.S.Zero
 if not word:return s.S.One if n==0 and k==0 else s.S.Zero
 if n==0:return ag.Z(word[k:])/factorial(k) if k<=len(word) else s.S.Zero
 if k>len(word)-1:return s.S.Zero
 result=0
 for h in range(len(word)-k):
  rhs=sum(word[0]**r*big_coefficient(word[1:],n-r,k+h) for r in range(n+1))
  result-=s.Rational(factorial(k+h),factorial(k)*n**(h+1))*rhs
 return s.expand(result)

@lru_cache(maxsize=200000)
def upper_constant(word,N,d):
 out=0
 for j in range(d+1):
  for k in range(d-j+1):
   sh=ag.shiftcoef(N,j,k,d)
   if sh:out+=sh*factorial(k)*big_coefficient(word,j,k)
 return s.expand(out)

def extract_finite(rows,N):
 import time
 start=time.time();out={}
 for i,(word,logs,text) in enumerate(rows):
  if 1 in logs:continue # Both log(e*k) and log(k) give log(k) at the requested ell^0.
  scalar=s.prod(s.log(k) for k in logs);parts=[]
  for p,co in rational_laurent(text,0).items():parts.append(co*upper_constant(tuple(word),N,-p))
  val=s.expand(scalar*s.Add(*parts))
  for term in s.Add.make_args(val):
   c,m=term.as_coeff_Mul(rational=True);out[m]=out.get(m,s.S.Zero)+c
  if i%1000==0:print('FAST_EXTRACT',i+1,len(rows),len(out),time.time()-start,flush=True)
 return s.Add(*(m*c for m,c in out.items() if c))
