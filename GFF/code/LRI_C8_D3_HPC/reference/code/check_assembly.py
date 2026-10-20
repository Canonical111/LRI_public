"""Exact rational fixed-point versus bivariate Lagrange inversion checks."""
from pathlib import Path
from fractions import Fraction as F
import json,random,numpy as np
from analyze import coefficients
W=Path(__file__).resolve().parents[1];N=8

def add(a,b):return [a[j]+b[j]for j in range(N)]
def mul(a,b):
 c=[F(0)]*N
 for i,x in enumerate(a):
  for j,y in enumerate(b[:N-i]):c[i+j]+=x*y
 return c

def fixed(b,c):
 g=[F(0)]*N;e=g.copy();e[1]=1
 for _ in range(N):
  gp=g.copy();z=[F(0)]*N
  for L in range(2,N):gp=mul(gp,g);z=add(z,mul(b[L],gp))
  g=[(e[i]-z[i])/3 for i in range(N)]
 v=[F(0)]*N;gp=[F(1)]+[F(0)]*7
 for L in range(1,N):gp=mul(gp,g);v=add(v,mul(c[L],gp))
 v[0]+=F(3,2);v[1]-=F(1,2);return v

def bm(a,b,K,J):
 c={}
 for (i,j),x in a.items():
  for (k,l),y in b.items():
   if i+k<=K and j+l<=J:c[i+k,j+l]=c.get((i+k,j+l),F(0))+x*y
 return c

def lagrange(b,c):
 out=[F(3,2),-F(1,2)]+[F(0)]*6
 for n in range(1,8):
  K=n-1;J=7-n;delta={(L-1,j):x/3 for L in range(2,8)for j,x in enumerate(b[L])if x and L-1<=K and j<=J};der={(L-1,j):L*x for L in range(1,8)for j,x in enumerate(c[L])if x and L-1<=K and j<=J}
  power={(0,0):F(1)};coef=F(1)
  for k in range(K+1):
   if k:power=bm(power,delta,K,J);coef=coef*F(-n-k+1,k)
   v=bm(power,der,K,J)
   for j in range(J+1):out[n+j]+=coef*v.get((K,j),F(0))/(n*3**n)
 return out
rng=random.Random(30703110);rows=[]
for test in range(64):
 b={1:[F(3)]+[F(0)]*7};c={1:[F(1)]+[F(0)]*7}
 for L in range(2,8):
  b[L]=[F(rng.randint(-12,12),rng.randint(1,7))for _ in range(8-L)]+[F(0)]*L;c[L]=[F(rng.randint(-12,12),rng.randint(1,7))for _ in range(8-L)]+[F(0)]*L
 x=fixed(b,c);y=lagrange(b,c);assert x==y
 rows.append(dict(case=test,exact_equal=True))
# Jacobian at top order is exact and independent of the lower coefficients.
b={L:[F(0)]*8 for L in range(1,8)};c={L:[F(0)]*8 for L in range(1,8)};b[1][0]=3;c[1][0]=1;x=fixed(b,c);b[7][0]=1;y=fixed(b,c);assert y[7]-x[7]==-F(1,6561);b[7][0]=0;c[7][0]=1;y=fixed(b,c);assert y[7]-x[7]==F(1,2187)
(W/'verification/assembly_checks.json').write_text(json.dumps(dict(status='passed',exact_cases=64,rows=rows,dC7_db7='-1/6561',dC7_dc7='1/2187'),indent=2));print('64 exact seventh-order comparisons and top-order sensitivities passed')
