"""Exact quartic/mass vertex graph enumeration and critical logarithmic forests."""
from fractions import Fraction as F
from itertools import combinations,permutations,product
from functools import lru_cache
from math import factorial,prod
import json

@lru_cache(None)
def ps(n):return tuple(combinations(range(n),2))
def mat(n,word):return dict(zip(ps(n),word))
def degrees(n,word):return tuple(sum(m for (i,j),m in zip(ps(n),word) if v in (i,j)) for v in range(n))
def transform(n,word,p):
 g=mat(n,word);return tuple(g[tuple(sorted((p[i],p[j])))] for i,j in ps(n))
@lru_cache(None)
def canon(n,word):
 deg=degrees(n,word);dd=sorted(set(deg));groups=[[i for i,x in enumerate(deg) if x==d] for d in dd]
 best=None;bp=None;au=0
 for groupsp in product(*(permutations(g) for g in groups)):
  p=sum((tuple(z) for z in groupsp),());w=transform(n,word,p)
  if best is None or w<best:best,bp,au=w,p,1
  elif w==best:au+=1
 return best,bp,au

def onepi(n,word):
 for k in range(1,n):
  for S in combinations(range(1,n),k):
   S=set(S)
   if sum(m for (i,j),m in zip(ps(n),word) if (i in S)!=(j in S))<2:return False
 return True

def enumerate_vertices(n):
 types=[(2,2)+(4,)*(n-2)]
 if n>=3:types.append((2,3,3)+(4,)*(n-3))
 if n>=4:types.append((3,3,3,3)+(4,)*(n-4))
 allc={}
 for dd in types:
  deg=list(dd);word=[0]*len(ps(n));pp=ps(n)
  future=[[sum(v in p for p in pp[k:]) for v in range(n)] for k in range(len(pp)+1)]
  def rec(k):
   if k==len(pp):
    if any(deg):return
    w=tuple(word)
    if not onepi(n,w):return
    c,p,au=canon(n,w);allc[c]=au;return
   i,j=pp[k]
   for m in range(min(3,deg[i],deg[j])+1):
    deg[i]-=m;deg[j]-=m;word[k]=m
    if all(deg[v]<=3*future[k+1][v] for v in range(n)):rec(k+1)
    deg[i]+=m;deg[j]+=m
  rec(0)
 result=[]
 for i,(w,au) in enumerate(sorted(allc.items())):
  deg=degrees(n,w);ext=[4-d for d in deg]
  w4=F(24,prod(factorial(e) for e in ext)*prod(factorial(m) for m in w)*au)
  w2=w4*F(sum(e*(e-1) for e in ext),12)
  result.append({'index':i+1,'edges':w,'weight4':str(w4),'weight2':str(w2),'automorphisms':au,'degrees':deg})
 return result

@lru_cache(None)
def logs(n,word):
 out=[]
 for k in range(2,n):
  for vs in combinations(range(n),k):
   wg=tuple(mat(n,word)[(vs[i],vs[j])] for i,j in ps(k))
   if sum(wg)==2*(k-1) and onepi(k,wg):out.append((frozenset(vs),wg))
 return tuple(out)

def choose_roots(n,word):
 ls=logs(n,word);deg=degrees(n,word)
 for r in sorted(ps(n),key=lambda r:(deg[r[0]]+deg[r[1]],r)):
  if not any(set(r)<=S for S,w in ls):return r
 raise ValueError(('no UV-safe roots',n,word))

def spinnies(n,word):
 subs=logs(n,word);out=[]
 def rec(j,used,seq):
  if seq:out.append(tuple(seq))
  for i in range(j,len(subs)):
   S,w=subs[i]
   if not used&S:rec(i+1,used|S,seq+[(S,w)])
 rec(0,set(),[]);return out

def contract(n,word,forest,roots):
 representative={i:i for i in range(n)}
 for S,w in forest:
  anchor=next((r for r in roots if r in S),min(S))
  representative.update({i:anchor for i in S})
 vs=sorted(set(representative.values()));ren={v:i for i,v in enumerate(vs)};mapping={i:ren[representative[i]] for i in range(n)}
 cg={p:0 for p in ps(len(vs))}
 for (i,j),m in zip(ps(n),word):
  a,b=mapping[i],mapping[j]
  if a!=b:cg[tuple(sorted((a,b)))]+=m
 return len(vs),tuple(cg[p] for p in ps(len(vs))),tuple(mapping[r] for r in roots)

if __name__=='__main__':
 import time
 for n in range(2,7):
  t=time.time();r=enumerate_vertices(n);json.dump(r,open(f'vertex_n{n}.json','w'),indent=2)
  print(n,len(r),'mass',sum(F(x['weight2'])!=0 for x in r),'secs',time.time()-t,flush=True)
  bad=[]
  for x in r:
   try:choose_roots(n,tuple(x['edges']))
   except ValueError:bad.append(x['index'])
  print('unsafe',bad,flush=True)
