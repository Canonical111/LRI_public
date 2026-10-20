"""Independent highest Mellin pole of A7 tail vs lowest-flow leading logarithm."""
from itertools import permutations
from fractions import Fraction as Q
from math import factorial
from collections import Counter
from functools import lru_cache
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def pmul(a,b,target):
 o={}
 for i,c in a.items():
  for j,d in b.items():
   k=tuple(x+y for x,y in zip(i,j))
   if any(x>y for x,y in zip(k,target)):continue
   o[k]=o.get(k,0)+c*d
 return {k:v for k,v in o.items() if v}
def binom(e,k):
 b=Q(1)
 for j in range(k):b*=Q(e-j,j+1)
 assert b.denominator==1
 return int(b)
@lru_cache(None)
def smooth_coefficient(target,fac):
 zero=(0,)*len(target);f={zero:1}
 for masks,e in fac:
  if not e:continue
  h=Counter()
  for mask in masks:
   z=tuple((mask>>j)&1 for j in range(len(target)))
   if all(x<=y for x,y in zip(z,target)):h[z]+=1
  if not h:continue
  pe={zero:1};power={zero:1}
  for k in range(1,sum(target)+1):
   power=pmul(power,h,target)
   cc=binom(e,k)
   if cc:
    for z,c in power.items():pe[z]=pe.get(z,0)+cc*c
  f=pmul(f,pe,target)
 return f.get(target,0)

def pole(n):
 m=n-1;d=m-1;a=Q(1-n,2) if n%2 else Q(-n,2)
 total=Q(0);count=0;details=[]
 for perm in permutations(range(m)):
  rank={v:i for i,v in enumerate(perm)};ex=[0]*d;fac=Counter();cs=[0]*d
  for i in range(n):
   for j in range(i+1,n):
    sign=(-1)**(i+j);ks=sorted(rank[h] for h in range(i,j));k=ks[0]
    for t in range(k):ex[t]+=2*sign;cs[t]+=sign
    masks=tuple(sum(1<<t for t in range(k,r)) for r in ks[1:])
    if masks:fac[masks]+=2*sign
  ps=[m-2-j+ex[j] for j in range(d)]
  if any(p>=0 for p in ps):continue
  target=tuple(-p-1 for p in ps)
  residue=smooth_coefficient(target,tuple(sorted(fac.items())))
  leading=2*residue*(a+sum(Q(j+2)*c for j,c in enumerate(cs)))
  total+=leading;count+=1
 return {'n':n,'coefficient_qminus':str(total),'pole_order':d+4,'coefficient_highest_log':str((-1)**(d+3)*total/factorial(d+3)),'all_gap_sectors':factorial(m),'maximally_singular_sectors':count}

def leading_flow(n):
 # h rescaled as h/sqrt(2): bg=-4 g h; bh=-g^2.
 import sympy as s
 g,h,d,l=s.symbols('g h d l')
 bg=-4*g*h;bh=-g*g*(1-d*l*l)
 def tr(ex):
  return s.Add(*(c*g**ig*h**ih*d**idd for (ig,ih,idd),c in s.Poly(s.expand(ex),g,h,d).terms() if ig+2*ih<=n and idd<=1))
 cc=[g]
 for k in range(n+1):
  rhs=0
  for j in range(k+1):rhs+=bg.coeff(l,j)*s.diff(cc[k-j],g)+s.expand(bh).coeff(l,j)*s.diff(cc[k-j],h)
  cc.append(tr(rhs)/(k+1))
 return str(s.expand(cc[n+1].subs(h,0)).coeff(g,n).coeff(d,1))
def main():
 rows=[]
 for n in [3,5,7]:
  r=pole(n);r['leading_flow_coefficient']=leading_flow(n);r['exact_agreement']=Q(r['coefficient_highest_log'])==Q(r['leading_flow_coefficient']);rows.append(r);print(r,flush=True)
 (ROOT/'verification/leading_log_independent.json').write_text(json.dumps(rows,indent=2))
 assert all(r['exact_agreement'] for r in rows)
if __name__=='__main__':main()
