"""Root-distance IR rearrangement and disjoint-vertex UV forests.
The chosen root pair is never contained in a proper divergent subgraph.
All exponent jets and local counterterms use normalized coordinate measure.
"""
from fractions import Fraction as F
from functools import lru_cache
import json,time,sys
from pathlib import Path
import mpmath as mp
from jet_engine import X
from reconstruct import ReconstructionEngine
from vertex_graphs import ps,canon,logs,choose_roots,spinnies,contract,enumerate_vertices

class Forests:
 def __init__(self,E,P5=0):self.E=E;self.P5=P5;self.cache={};self.ampcache={}
 def amplitude(self,n,word,roots):
  key=(n,word,roots)
  if key not in self.ampcache:
   u=X(1,-F(1,4));g={p:m*u for p,m in zip(ps(n),word) if m}
   z=self.E.kernel(g,range(n),roots)
   self.ampcache[key]=self.E.shift(z,-1,F(2,n-1))
  return self.ampcache[key]
 def counterterm(self,n,word):
  word,_,_=canon(n,word);key=n,word
  if key in self.cache:return self.cache[key]
  if n==6 and not logs(n,word) and max(word)==1:
   au=canon(n,word)[2]
   if au in (12,16):period=self.E.T**2/4
   elif au==2:period=self.P5
   else:raise ValueError(('unrecognized primitive',word,au))
   Z={-1:-self.E.m(F(2,5))*period};self.cache[key]=Z;return Z
  roots=choose_roots(n,word)
  result=self.amplitude(n,word,roots).copy()
  for forest in spinnies(n,word):
   cn,cw,cr=contract(n,word,forest,roots)
   factors=[self.counterterm(len(S),wg) for S,wg in forest]
   factors.append(self.amplitude(cn,cw,cr))
   result=self.E.add(result,self.E.mul(*factors))
  Z={k:-x for k,x in result.items() if k<0}
  self.cache[key]=Z;return Z

def go(d,order=5,verbose=True):
 from calculate_a5 import fixed_periods
 d=mp.mpf(d);q=d/4;T,P,_=fixed_periods(d)
 Z=4*mp.catalan*T/6 if d==2 else 0
 E=ReconstructionEngine(d,T,P4=P,Z=Z,N=7,verbose=verbose)
 FST=Forests(E);out={}
 for L in range(1,order+1):
  n=L+1;rfile=Path(f'vertex_n{n}.json');rows=json.loads(rfile.read_text()) if rfile.exists() else enumerate_vertices(n)
  sum4=mp.mpf(0);sum2=mp.mpf(0);report=[]
  for r in rows:
   print('BEGIN VERTEX',L,r['index'],flush=True);tm=time.time()
   try:z=FST.counterterm(n,tuple(r['edges']))
   except Exception as err:
    print('FAIL VERTEX',L,r,flush=True);raise
   v=z.get(-1,0);sum4+=E.m(F(r['weight4']))*v;sum2+=E.m(F(r['weight2']))*v
   report.append({'index':r['index'],'counterterm':{str(k):mp.nstr(v,50) for k,v in z.items()}})
   print('END VERTEX',L,r['index'],mp.nstr(v,25),'time',time.time()-tm,flush=True)
   Path(f'vertex_progress_{L}.json').write_text(json.dumps(report,indent=2))
  b=L*(-1)**L*sum4;c=L*(-1)**L*sum2
  print('RG',L,'b=',mp.nstr(b,45),'c=',mp.nstr(c,45),flush=True)
  out[L]={'b':mp.nstr(b,50),'c':mp.nstr(c,50),'graphs':report}
  Path('vertex_results.json').write_text(json.dumps(out,indent=2))
 return out
if __name__=='__main__':
 mp.mp.dps=55;go(2,int(sys.argv[1]) if len(sys.argv)>1 else 5)
