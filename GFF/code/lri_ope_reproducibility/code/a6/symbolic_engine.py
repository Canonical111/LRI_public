"""Exact sparse polynomial shadow of the order-four regulator jets.
No interpolation in dimension or fit to numerical master values is used.
Gamma constants are symbolic; all coefficients are rational.
"""
from __future__ import annotations
from fractions import Fraction as F
from collections import Counter
from functools import lru_cache
import mpmath as mp
import sympy as sp
from reconstruct import ReconstructionEngine
from jet_engine import X

class LP:
 __slots__=('t',)
 def __init__(self,t):self.t={k:F(v) for k,v in t.items() if v}
 @staticmethod
 def cast(x):
  if isinstance(x,LP):return x
  if isinstance(x,mp.mpf):x=F(str(x))
  return LP({():F(x)})
 @staticmethod
 def var(name):return LP({((name,1),):F(1)})
 def __bool__(self):return bool(self.t)
 def __add__(self,x):
  x=self.cast(x);o=self.t.copy()
  for k,v in x.t.items():o[k]=o.get(k,F(0))+v
  return LP(o)
 __radd__=__add__
 def __neg__(self):return LP({k:-v for k,v in self.t.items()})
 def __sub__(self,x):return self+-self.cast(x)
 def __rsub__(self,x):return self.cast(x)+-self
 def __mul__(self,x):
  x=self.cast(x)
  if not self or not x:return LP({})
  o={}
  for k,v in self.t.items():
   for l,w in x.t.items():
    if not k:mon=l
    elif not l:mon=k
    else:
     p=dict(k)
     for a,b in l:p[a]=p.get(a,0)+b
     mon=tuple(sorted((a,b) for a,b in p.items() if b))
    o[mon]=o.get(mon,F(0))+v*w
  return LP(o)
 __rmul__=__mul__
 def __truediv__(self,x):
  x=self.cast(x)
  if len(x.t)!=1:raise ValueError('polynomial divisor')
  (mon,c),=x.t.items()
  return self*LP({tuple((a,-b) for a,b in mon):1/c})
 def __rtruediv__(self,x):return self.cast(x)/self
 def __pow__(self,n):
  if n<0:return LP.cast(1)/(self**(-n))
  if n==0:return LP.cast(1)
  if n==1:return self
  y=self**(n//2);return y*y*(self if n%2 else LP.cast(1))
 def sympy(self):
  return sp.Add(*(sp.Rational(c.numerator,c.denominator)*sp.Mul(*(sp.Symbol(x)**p for x,p in mon)) for mon,c in self.t.items()))
 def __repr__(self):return str(self.sympy())
 def serialize(self):return str(self)
 def evaluate(self,values):
  o=mp.mpf(0)
  for mon,c in self.t.items():
   v=mp.mpf(c.numerator)/c.denominator
   for x,p in mon:v*=values[x]**p
   o+=v
  return o

@lru_cache(None)
def pfun(k,n):
 p=lambda i,j:LP.var(f'p{i}_{"m"+str(-j) if j<0 else j}')
 A,R,U,V,X,N=[LP.var(x) for x in ('A','R','U','V','X','N')]
 if k==0 and n==2:return A-p(0,0)+2*p(0,1)
 if k==0 and n==-1:return N-p(0,3)+p(0,0)+pfun(0,2)
 if k==1 and n==2:return R+p(1,0)
 if k==2 and n==1:return U
 if k==2 and n==2:return V-p(2,0)
 if k==3 and n==2:return X+pfun(3,0)
 if k==3 and n==0:return F(12,5)*p(1,0)**2
 return p(k,n)

class SymbolicEngine(ReconstructionEngine):
 def __init__(self,verbose=True):
  super().__init__(mp.mpf('1.31'),1,P4=1,N=4,verbose=verbose)
  for x in ('A','R','U','V','M','N','T','K','Z','L','Ccross'):setattr(self,x,LP.var(x))
  self.P4=LP.var('P');self.gamma_prefactors=set()
 def m(self,x):return LP.cast(x)
 def add(self,*js):
  o={}
  for j in js:
   for k,v in j.items():o[k]=o.get(k,LP.cast(0))+LP.cast(v)
  return {k:v for k,v in o.items() if v}
 def scale(self,j,c):
  c=LP.cast(c);return {k:v*c for k,v in j.items() if v*c}
 def shift(self,j,k,c=1):return {n+k:LP.cast(v)*c for n,v in j.items() if LP.cast(v)*c}
 def mul(self,*js):
  out={0:LP.cast(1)}
  for j in js:
   j={k:LP.cast(v) for k,v in j.items() if LP.cast(v)}
   if not j or not out:return {}
   p=min(out)+min(j);o={}
   for k,v in out.items():
    for l,w in j.items():
     if k+l<=p+4:o[k+l]=o.get(k+l,LP.cast(0))+v*w
   out={k:v for k,v in o.items() if v}
  return out
 @lru_cache(None)
 def gr_cached(self,nums,dens):
  counts=Counter(nums);counts.subtract(dens);counts={x:c for x,c in counts.items() if c}
  zeros=[c for x,c in counts.items() if x.a==0 and x.b==0]
  if any(c>0 for c in zeros):raise ZeroDivisionError('identical symbolic Gamma pole')
  if zeros:return {}
  pref=LP.cast(1);pole=0;lg=[LP.cast(0) for _ in range(5)];gb=Counter()
  for x,c in counts.items():
   n=int(x.a)
   if x.a!=n:raise ValueError(('noninteger critical multiple',x))
   slope=x.b
   if n==0:
    pole-=c;pref*=slope**(-c)
   else:gb[n]+=c
   for k in range(1,5):lg[k]+=c*pfun(k-1,n)*slope**k/F(__import__('math').factorial(k))
  gb={k:c for k,c in gb.items() if c};self.gamma_prefactors.add(tuple(sorted(gb.items())))
  if -1 in gb:
   power=gb.pop(-1);pref*=LP.var('M')**power;gb[3]=gb.get(3,0)+power;gb[2]=gb.get(2,0)-2*power
  for n,c in gb.items():
   if c:pref*=LP.var('G'+('m'+str(-n) if n<0 else str(n)))**c
  val=[LP.cast(1)]
  for k in range(1,5):val.append(sum((i*lg[i]*val[k-i] for i in range(1,k+1)),LP.cast(0))/k)
  return {pole+k:pref*x for k,x in enumerate(val) if pref*x}
 def gr(self,nums,dens=()):return self.gr_cached(tuple(nums),tuple(dens))

if __name__=='__main__':
 import json,time
 from itertools import combinations
 E=SymbolicEngine();u=X(1,-F(1,4));out={}
 for n in (4,5,6):
  S={};rows=[]
  for r in json.load(open(f'graphs_n{n}.json')):
   print('SYMBOLIC BEGIN',n,r['index'],flush=True);tm=time.time()
   g={p:m*u for p,m in zip(combinations(range(n),2),r['edges']) if m}
   j=E.kernel(g,range(n),(0,1));j={k:j.get(k,LP.cast(0)) for k in range(2-n,7-n)}
   S=E.add(S,E.scale(j,F(r['weight'])))
   rows.append({'index':r['index'],'new':str(LP.cast(j[6-n]))})
   print('SYMBOLIC END',n,r['index'],'new=',LP.cast(j[6-n]),'sec',time.time()-tm,flush=True)
   out[f'graphs{n}']=rows
   with open('symbolic_progress.json','w') as f:json.dump(out,f,indent=2)
  out[f'S{n}']={str(k):str(v) for k,v in S.items()}
  print('SYMBOLIC SUM',n,out[f'S{n}'],flush=True)
  with open('symbolic_kernel_results.json','w') as f:json.dump(out,f,indent=2)
 # Same engine/cache for the RG forest audit.
 from vertex_counterterms import Forests
 forests=Forests(E,P5=LP.var('P5'));b=LP.cast(0);c=LP.cast(0);rows=[]
 for r in json.load(open('vertex_n6.json')):
  print('SYMBOLIC VERTEX BEGIN',r['index'],flush=True);tm=time.time()
  ct=forests.counterterm(6,tuple(r['edges']));v=LP.cast(ct.get(-1,0))
  b+=E.m(F(r['weight4']))*v;c+=E.m(F(r['weight2']))*v
  rows.append({'index':r['index'],'simple_pole':str(v)})
  print('SYMBOLIC VERTEX END',r['index'],'sec',time.time()-tm,flush=True)
  out['vertex_graphs']=rows
  with open('symbolic_progress.json','w') as f:json.dump(out,f,indent=2)
 b=-5*b;c=-5*c;out['b5']=str(b);out['c5']=str(c);out['D5']=str(3*c-b)
 out['gamma_prefactors']=[str(x) for x in sorted(E.gamma_prefactors)]
 for k in ('b5','c5','D5'):print('SYMBOLIC',k,out[k],flush=True)
 with open('symbolic_results.json','w') as f:json.dump(out,f,indent=2)
