"""Independent exact Gamma-series arithmetic for the closed MS graph sector.
Expansions use Q[log(2), zeta(2), zeta(3), zeta(5)] with exact coefficients.
No PSLQ or fitted integer relation is involved.
"""
import sp_ms as M
import sympy as S
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import json,time,math
ell,eg,z2,z3,z5=S.symbols('ell EulerGamma zeta2 zeta3 zeta5')
zet={2:z2,3:z3,4:S.Rational(2,5)*z2**2,5:z5}
class Exact:
 @staticmethod
 def mpf(x):return S.Rational(str(x))
 factorial=staticmethod(S.factorial)
 nstr=staticmethod(lambda x,n=30:str(x))
M.mp=Exact;M.C.clear();M.solved_meta.clear();M.active.clear();M.mpf=lambda x:S.Rational(x.numerator,x.denominator)

def add(*xs):
 out={}
 for x in xs:
  for k,v in x.items():out[k]=out.get(k,S.Integer(0))+v
 return{k:S.expand(v)for k,v in out.items()}
def mul(x,y):
 out={}
 for k,v in x.items():
  for j,w in y.items():
   if -6<=k+j<=5:out[k+j]=out.get(k+j,S.Integer(0))+v*w
 return{k:S.expand(v)for k,v in out.items()}
M.add=add;M.mul=mul

def psi(m,a):
 a=S.Rational(a.numerator,a.denominator)if isinstance(a,F)else S.Rational(a)
 base=S.Integer(1)if a.q==1 else S.Rational(1,2);n=int(a-base)
 val=(-eg if base==1 else -eg-2*ell)if m==0 else (-1)**(m+1)*S.factorial(m)*zet[m+1]*(1 if base==1 else 2**(m+1)-1)
 if n>=0:val+=sum((-1)**m*S.factorial(m)/(base+j)**(m+1)for j in range(n))
 else:val-=sum((-1)**m*S.factorial(m)/(base+j)**(m+1)for j in range(n,0))
 return S.expand(val)

@lru_cache(None)
def gamma_series(ga):
 lead=S.Integer(1);power=0;logs=[S.Integer(0)]*M.K
 for a,b,v in ga:
  B=S.Rational(b.numerator,b.denominator)
  if a.denominator==1 and a<=0:
   m=int(-a);power-=v;lead*=((-1)**m/(B*S.factorial(m)))**v
   for k in range(1,M.K):logs[k]+=v*B**k*(psi(k-1,F(1))/S.factorial(k)+sum(S.Rational(1,j**k)for j in range(1,m+1))/k)
  else:
   A=S.Rational(a.numerator,a.denominator);lead*=S.gamma(A)**v
   for k in range(1,M.K):logs[k]+=v*B**k*psi(k-1,a)/S.factorial(k)
 lead=S.simplify(lead);logs=[S.expand(v)for v in logs]
 assert all(not x.has(eg)for x in logs),('Euler gamma did not cancel',ga,logs)
 cs=[lead]
 for k in range(1,M.K):cs.append(S.expand(sum(j*logs[j]*cs[k-j]for j in range(1,k+1))/k))
 return{power+k:v for k,v in enumerate(cs)}
M.gamma_series=gamma_series
out=[];t=time.time()
for row in M.inv['loops']:
 L=row['loop'];ok=[];b=S.Integer(0);c=S.Integer(0)
 for g in row['graphs']:
  try:
   cp=M.ct([tuple(e)for e in g['edges']]);r=-cp.get(-1,0);bb=(-1)**(L+1)*L*S.Rational(g['weight4'])*r;cc=(-1)**(L+1)*L*S.Rational(g['weight2'])*r;b+=bb;c+=cc
   ok.append({'id':g['id'],'counterterm':{str(k):str(S.expand(v))for k,v in cp.items()}})
  except M.Unsolved:pass
 b=S.expand(b);c=S.expand(c);out.append({'loop':L,'count':len(ok),'b':str(b),'c':str(c),'graphs':ok});print(L,len(ok),'b',b,'c',c,'time',time.time()-t,flush=True)
 (Path(__file__).resolve().parents[1]/'verification/sp_exact.json').write_text(json.dumps({'dictionary':{'ell':'log(2)','zeta2':'zeta(2)','zeta3':'zeta(3)','zeta5':'zeta(5)'},'loops':out,'seconds':time.time()-t},indent=2))
