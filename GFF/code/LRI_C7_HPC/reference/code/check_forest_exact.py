"""Coefficientwise exact check of all full-graph forest polynomials through seven loops."""
import json,collections,time
from pathlib import Path
from fractions import Fraction as F
R=Path(__file__).resolve().parents[1]/"verification"; data=json.load(open(R/"forest_polynomials.json"));N=7

def clean(a):return {k:v for k,v in a.items()if v}
def add(a,b,c=F(1)):
 out=dict(a)
 for k,v in b.items():out[k]=out.get(k,F(0))+c*v
 return clean(out)
def scale(a,c):return clean({k:v*c for k,v in a.items()})
def mul(a,b):
 c=collections.defaultdict(F)
 for m,x in a.items():
  for n,y in b.items():c[tuple(sorted(m+n))]+=x*y
 return clean(c)
def gm(a,b):
 c=[{}for _ in range(N+1)]
 for i,x in enumerate(a):
  for j,y in enumerate(b[:N+1-i]):
   if x and y:c[i+j]=add(c[i+j],mul(x,y))
 return c
one=[{():F(1)}]+[{}for _ in range(N)]
def gp(a,k):
 if k<0:
  out=[{():F(1)}]
  for n in range(1,N+1):
   v={}
   for j in range(1,n+1):v=add(v,mul(a[j],out[n-j]),F(-1))
   out.append(v)
  a=out;k=-k
 out=one
 for _ in range(k):out=gm(out,a)
 return out

def pol(rows):return {tuple(r['monomial']):F(r['coefficient'])for r in rows}
A=[{():F(1)}]+[scale(pol(data[str(L)]['bareA']),(-1)**L)for L in range(1,N+1)]
B=[{():F(1)}]+[scale(pol(data[str(L)]['bareB']),(-1)**L)for L in range(1,N+1)]
checks=[];start=time.time()
for L in range(1,N+1):
 dd=[scale(A[i],i*(i+1))for i in range(N+1)];bb=scale(gm(dd,gp(A,-L-1))[L],-F(1,L+1))
 lg=gm([scale(B[i],i)for i in range(N+1)],gp(B,-1));dd=[scale(lg[i+1],i+1)for i in range(N)]+[{}]
 cc=scale(gm(dd,gp(A,-L))[L-1],-F(1,L))
 db=add(bb,pol(data[str(L)]['beta']),-1);dc=add(cc,pol(data[str(L)]['gamma']),-1)
 r={'L':L,'beta_monomials':len(bb),'gamma_monomials':len(cc),'beta_difference_zero':not db,'gamma_difference_zero':not dc};checks.append(r);print(r,flush=True)
 assert not db and not dc
(R/'forest_exact_checks_new.json').write_text(json.dumps({'description':'Full rational polynomial identities, not evaluations at sample points','checks':checks,'seconds':time.time()-start},indent=2))
