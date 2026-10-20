"""Coefficientwise exact check of all full-graph forest polynomials through N loops.

Generalization of reference/code/check_forest_exact.py (hard-wired to N=7 and to
verification/forest_polynomials.json) with N, the input JSON and the output JSON as parameters.
Algorithm unchanged: the forest polynomials beta_L, gamma_L produced by gen/forest_audit are
compared, as exact rational polynomials in the atom variables, with the Lagrange inversion of
the bare series (bareA, bareB) through N loops.

One necessary change: monomials read from the JSON are re-sorted as strings, the same order
`mul` uses. In the reference all atom keys had 18 decimal digits, so numeric and string order
coincided; 9-vertex atoms (L=8) have 23-digit keys and the orders would differ.
Usage: python check_forest_exact.py forest_polynomials.json N output.json
"""
import json,collections,time,sys
from fractions import Fraction as F
src,N,dst=sys.argv[1],int(sys.argv[2]),sys.argv[3]
data=json.load(open(src))

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

def pol(rows):
 out={}
 for r in rows:
  m=tuple(sorted(r['monomial']))
  assert m not in out,'duplicate monomial'
  out[m]=F(r['coefficient'])
 return out
A=[{():F(1)}]+[scale(pol(data[str(L)]['bareA']),(-1)**L)for L in range(1,N+1)]
B=[{():F(1)}]+[scale(pol(data[str(L)]['bareB']),(-1)**L)for L in range(1,N+1)]
checks=[];start=time.time()
for L in range(1,N+1):
 dd=[scale(A[i],i*(i+1))for i in range(N+1)];bb=scale(gm(dd,gp(A,-L-1))[L],-F(1,L+1))
 lg=gm([scale(B[i],i)for i in range(N+1)],gp(B,-1));dd=[scale(lg[i+1],i+1)for i in range(N)]+[{}]
 cc=scale(gm(dd,gp(A,-L))[L-1],-F(1,L))
 db=add(bb,pol(data[str(L)]['beta']),-1);dc=add(cc,pol(data[str(L)]['gamma']),-1)
 r={'L':L,'beta_monomials':len(bb),'gamma_monomials':len(cc),'beta_difference_zero':not db,'gamma_difference_zero':not dc,'elapsed_seconds':round(time.time()-start,3)};checks.append(r);print(r,flush=True)
 assert not db and not dc
open(dst,'w').write(json.dumps({'description':'Full rational polynomial identities, not evaluations at sample points','source':src,'N':N,'checks':checks,'seconds':time.time()-start},indent=2))
print('ALL PASS',N,time.time()-start)
