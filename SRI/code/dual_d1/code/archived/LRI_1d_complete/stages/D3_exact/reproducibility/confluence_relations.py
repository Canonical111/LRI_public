"""Exact confluence identities: G(-a_i,T+b_j;T) -> convergent MZVs.
Every identity is proved by exact differentiation and dominated convergence;
no numerical constants or integer-relation recognition are used.
"""
from collections import Counter
from functools import lru_cache
from itertools import product
from fractions import Fraction as Q
import json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
@lru_cache(None)
def fib(w):
 if not w:return {():1}
 out=Counter();ext=((1,0),)+w+((0,0),)
 for i,(ss,cc) in enumerate(w):
  lo=fib(w[:i]+w[i+1:])
  for si,(s,c) in [(1,ext[i]),(-1,ext[i+2])]:
   slope=s-ss;inter=c-cc
   if not slope:continue
   root=Q(-inter,slope)
   assert root.denominator==1 and root<0,(w,root)
   a=-root.numerator
   for v,n in lo.items():out[(a,)+v]+=si*n
 return {w:c for w,c in out.items() if c}
@lru_cache(None)
def sh(a,b):
 if not a:return {b:1}
 if not b:return {a:1}
 out=Counter()
 for w,c in sh(a[1:],b).items():out[(a[0],)+w]+=c
 for w,c in sh(a,b[1:]).items():out[(b[0],)+w]+=c
 return dict(out)
PHI={(0,1):Q(-1),(0,0,1):Q(-1),(0,1,1):Q(1),
 (0,0,0,1):Q(-1),(0,0,1,1):Q(1,4),(0,1,0,1):Q(3,4),(0,1,1,1):Q(-1)}
ZETAR={2:Q(-2),3:Q(-4,3),4:Q(-8,7)}
def confluence(n,M=7):
 for bits in [(0,)+mid+(1,) for mid in product((0,1),repeat=n-2)]:
  for aa in product(range(1,M),repeat=n):
   if max(a for a,b in zip(aa,bits) if not b)+max(a for a,b in zip(aa,bits) if b)>M:continue
   moving=tuple((b,a if b else -a) for a,b in zip(aa,bits))
   rr={w:Q(c) for w,c in fib(moving).items()}
   zz=(2,)+(1,)*(n-1);rr[zz]=rr.get(zz,Q(0))-PHI[bits]*ZETAR[n]
   rr={w:c for w,c in rr.items() if c}
   if rr:yield dict(kind='confluence',bits=bits,a=aa),rr

def multiply(row,w):
 out=Counter()
 for v,c in row.items():
  for u,k in sh(v,w).items():out[u]+=c*k
 return {w:c for w,c in out.items() if c}
def relations(n,M=7):
 # Weight-one logarithm identities, multiplied by any word.
 basic=[({'kind':'R1zero'},{(1,):Q(1)})]
 for a in range(2,M+1):
  for b in range(a,M+1):
   if a*b<=M:basic.append(({'kind':'logproduct','a':a,'b':b},{(a*b,):Q(1),(a,):Q(-1),**({(b,):Q(-1)} if a!=b else {})}))
 # Fix multiplicity when factors agree.
 for desc,rr in basic:
  if desc['kind']=='logproduct' and desc['a']==desc['b']:rr[(desc['a'],)]=Q(-2)
  for w in product(range(1,M+1),repeat=n-1):
   row=multiply(rr,w)
   if row:yield {**desc,'times':w},row
 for k in range(2,n+1):
  for desc,rr in confluence(k,M):
   for w in product(range(1,M+1),repeat=n-k):
    row=multiply(rr,w)
    if row:yield {**desc,'times':w},row

class ModularEchelon:
 def __init__(self,p=1000000007):self.p=p;self.rows={};self.count=0
 def add(self,row):
  p=self.p;r={w:(int(c.numerator)*pow(int(c.denominator),-1,p))%p for w,c in row.items()}
  r={w:c for w,c in r.items() if c}
  while r:
   lead=max(r)
   if lead not in self.rows:
    inv=pow(r[lead],-1,p);self.rows[lead]={w:c*inv%p for w,c in r.items()};return True
   fac=r[lead];b=self.rows[lead]
   for w,c in b.items():
    v=(r.get(w,0)-fac*c)%p
    if v:r[w]=v
    elif w in r:del r[w]
  return False
 def reduce(self,row):
  p=self.p;r={w:(int(c.numerator)*pow(int(c.denominator),-1,p))%p for w,c in row.items()};out={}
  while r:
   lead=max(r)
   if lead not in self.rows:out[lead]=r.pop(lead);continue
   fac=r[lead]
   for w,c in self.rows[lead].items():
    v=(r.get(w,0)-fac*c)%p
    if v:r[w]=v
    elif w in r:del r[w]
  return out

def main():
 targets=[(tuple(w),Q(c)) for w,c in json.loads((ROOT/'D3_linear_words.json').read_text())]
 for n in (2,3,4):
  t=time.time();A=ModularEchelon();count=0
  for desc,row in relations(n):
   A.add(row);count+=1
  tar={w:c for w,c in targets if len(w)==n};res=A.reduce(tar)
  print('weight',n,'relations',count,'rank',len(A.rows),'residual',len(res),'seconds',time.time()-t,flush=True)
  if res:print(res,flush=True)
if __name__=='__main__':main()

def scaling_relations(n,M=7):
 for k in range(2,n+1):
  for d in range(2,M+1):
   for w in product(range(1,M//d+1),repeat=k):
    rr=Counter({tuple(d*a for a in w):Q(1)})
    for j in range(k+1):
     for v,c in sh((d,)*j,w[j:]).items():rr[v]-=c
    rr={v:Q(c) for v,c in rr.items() if c}
    if not rr:continue
    for tail in product(range(1,M+1),repeat=n-k):
     row=multiply(rr,tail)
     if row:yield dict(kind='scaling',d=d,word=w,times=tail),row
