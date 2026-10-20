from pathlib import Path
from fractions import Fraction as Q
from math import comb
import random,json
import numpy as np
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"LRI_C7_d2_progress"/"code"))
from analyze import coefficients
W=Path(__file__).resolve().parents[1];N=8
Z=[Q(0)]*N

def add(a,b):return [x+y for x,y in zip(a,b)]
def scale(a,t):return [x*t for x in a]
def mul(a,b):
 c=Z.copy()
 for i,x in enumerate(a):
  if x:
   for j,y in enumerate(b[:N-i]):
    if y:c[i+j]+=x*y
 return c

def fixed(b,c):
 g=Z.copy();eps=Z.copy();eps[1]=1
 for it in range(N):
  power=g;val=Z.copy()
  for L in range(2,N):power=mul(power,g);val=add(val,mul(b[L],power))
  g=scale(add(eps,scale(val,-1)),Q(1,3))
 out=Z.copy();power=Z.copy();power[0]=1
 for L in range(1,N):power=mul(power,g);out=add(out,mul(c[L],power))
 out[0]+=1;out[1]-=Q(1,2)
 return out

def lagrange(b,c):
 # Bivariate g/epsilon arrays, each entry is an epsilon polynomial.
 def bmul(a,b):
  out=[Z.copy()for i in range(N)]
  for i in range(N):
   for j in range(N-i):out[i+j]=add(out[i+j],mul(a[i],b[j]))
  return out
 X=[Z.copy()for i in range(N)]
 for L in range(2,N):X[L-1]=scale(b[L],Q(1,3))
 one=[Z.copy()for i in range(N)];one[0][0]=1
 powers=[one]
 for i in range(1,N):powers.append(bmul(powers[-1],X))
 out=Z.copy();out[0]=1;out[1]=-Q(1,2)
 for k in range(1,N):
  C=Z.copy()
  for ell in range(1,k+1):
   jg=k-ell;v=Z.copy()
   for j in range(k):v=add(v,scale(powers[j][jg],Q((-1)**j*comb(k+j-1,j),3**k)))
   C=add(C,mul(scale(c[ell],ell),v))
  for s in range(N-k):out[s+k]+=C[s]/k
 return out

def ms7(A,b,c):
 b3,b4,b5,b6,b7=[b[j][0]for j in range(3,8)];c3,c4,c5,c6,c7=[c[j][0]for j in range(3,8)]
 return (12672*A**6-3360*A**4*b3+4320*A**4*c3-672*A**3*b4+1152*A**3*c4+192*A*A*b3*b3-432*A*A*b3*c3-112*A*A*b5+240*A*A*c5+Q(128,3)*A*b3*b4-64*A*b3*c4-48*A*b4*c3-14*A*b6+36*A*c6-Q(4,3)*b3**3+4*b3*b3*c3+Q(8,3)*b3*b5-5*b3*c5+Q(4,3)*b4*b4-4*b4*c4-3*b5*c3-b7+3*c7)/6561
rng=random.Random(36985701);cases=[]
for t in range(24):
 b={1:[Q(3)]+Z[1:]};c={1:[Q(1)]+Z[1:]}
 for L in range(2,N):
  b[L]=[Q(rng.randrange(-10,11),rng.randrange(1,7))for j in range(N-L)]+[Q(0)]*L
  c[L]=[Q(rng.randrange(-10,11),rng.randrange(1,7))for j in range(N-L)]+[Q(0)]*L
 a=fixed(b,c);z=lagrange(b,c);assert a==z
 # Independent tests of the closed MS polynomial with constant jets.
 A=Q(rng.randrange(1,10),rng.randrange(1,7));b[2]=[-6*A]+Z[1:];c[2]=[-A]+Z[1:]
 for L in range(3,N):b[L]=b[L][:1]+Z[1:];c[L]=c[L][:1]+Z[1:]
 assert fixed(b,c)[7]==ms7(A,b,c)
 cases.append(dict(index=t,regulator_dependent_coefficients_equal=True,MS_C7_polynomial_equal=True))
res=dict(status='passed',random_seed=36985701,exact_regulator_dependent_cases=24,exact_constant_MS_cases=24,cases=cases,coefficients_compared=24*8,scope='independent exact-rational fixed-point iteration versus bivariate Lagrange inversion; not an integration check')
(W/'verification/assembly_checks.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
