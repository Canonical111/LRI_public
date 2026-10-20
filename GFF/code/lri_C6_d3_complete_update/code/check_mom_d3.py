"""Two independent exact coefficient extractions for epsilon-dependent RG functions."""
from fractions import Fraction as F
from math import comb
from pathlib import Path
import json,random
W=Path(__file__).resolve().parents[1]/'records';N=6

def mul(a,b):
 c=[F(0)]*(N+1)
 for i,x in enumerate(a):
  for j,y in enumerate(b):
   if i+j<=N:c[i+j]+=x*y
 return c

def compose(b,c):
 g=[F(0)]*(N+1);e=g.copy();e[1]=1
 for _ in range(N+1):
  p=g.copy();tmp=[F(0)]*(N+1)
  for L in range(2,N+1):
   p=mul(p,g);z=mul(b[L],p);tmp=[x+y for x,y in zip(tmp,z)]
  g=[(x-y)/3 for x,y in zip(e,tmp)]
 ans=[F(0)]*(N+1);p=[F(1)]+[F(0)]*N
 for L in range(1,N+1):
  p=mul(p,g);z=mul(c[L],p);ans=[x+y for x,y in zip(ans,z)]
 ans[0]+=F(3,2);ans[1]-=F(1,2);return ans

def bm(a,b):
 c={}
 for (g,e),v in a.items():
  for (h,f),w in b.items():
   if g+h<=5 and e+f<=5:c[g+h,e+f]=c.get((g+h,e+f),F(0))+v*w
 return {k:v for k,v in c.items()if v}

def lagrange(b,c):
 w={(L-1,j):v/3 for L in range(2,7)for j,v in enumerate(b[L])if v};der={(L-1,j):L*v for L in range(1,7)for j,v in enumerate(c[L])if v}
 wp=[{(0,0):F(1)}]
 for r in range(1,6):wp.append(bm(wp[-1],w))
 out=[F(3,2),F(-1,2)]+[F(0)]*5
 for k in range(1,7):
  inv={}
  for r in range(k):
   pref=F((-1)**r*comb(k+r-1,r),3**k)
   for key,v in wp[r].items():inv[key]=inv.get(key,F(0))+pref*v
  tmp=bm(der,inv)
  for n in range(k,7):out[n]+=tmp.get((k-1,n-k),F(0))/k
 return out
r=random.Random(319991);checks=0
for test in range(32):
 b={1:[F(3)]};c={1:[F(1)]}
 for L in range(2,7):
  b[L]=[F(r.randint(-20,20),r.randint(1,9))for _ in range(7-L)];c[L]=[F(r.randint(-15,15),r.randint(1,9))for _ in range(7-L)]
 x=compose(b,c);y=lagrange(b,c);assert x==y,(test,x,y);checks+=7
# Check the full published constant-coefficient MS assembly independently.
for test in range(32):
 A=F(r.randint(1,20),r.randint(1,7));b={1:[F(3)],2:[-6*A]};c={1:[F(1)],2:[-A]}
 for L in range(3,7):b[L]=[F(r.randint(-30,30),r.randint(1,9))];c[L]=[F(r.randint(-20,20),r.randint(1,9))]
 b3,b4,b5,b6=[b[L][0]for L in range(3,7)];c3,c4,c5,c6=[c[L][0]for L in range(3,7)]
 z=(3*c6-b6+2016*A**5-448*A**3*b3+672*A**3*c3-84*A*A*b4+168*A*A*c4+F(49,3)*A*b3*b3-42*A*b3*c3-12*A*b5+30*A*c5+F(7,3)*b3*b4-4*b3*c4-3*b4*c3)/2187
 assert compose(b,c)[6]==z;checks+=1
(W/'mom_lagrange_d3_checks.json').write_text(json.dumps({'exact_rational_checks':checks,'epsilon_dependent_inputs':32,'independent_routes':['implicit fixed-point substitution','bivariate Lagrange inversion'],'constant_MS_sixth_assembly_checks':32,'all_passed':True},indent=2));print(checks,'passed')
