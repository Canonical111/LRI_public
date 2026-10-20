from __future__ import annotations
import json,itertools,time,functools,pickle,sys
from pathlib import Path
import sympy as s
import analytic_core as ac
import series_engine as se
z,d=ac.z,ac.d;q=se.q
ROOT=Path(__file__).parent

@functools.lru_cache(None)
def canonkey(key):
 m=ac.from_key(key);n=len(ac.vertices(m));pairs=list(itertools.combinations(range(n),2))
 rep=[]
 for pp in itertools.permutations(range(n)):
  vals=tuple((int(2*m.get(tuple(sorted((pp[i],pp[j]))),s.S(0)).subs({z:0,d:0})),m.get(tuple(sorted((pp[i],pp[j]))),s.S(0)).coeff(d))for i,j in pairs)
  rep.append(vals)
 best=min(rep,key=lambda vv:(tuple(v[0]for v in vv),tuple(v[1]for v in vv)))
 return tuple((i,j,s.Rational(v,2)*(1-z)+w*d)for(i,j),(v,w)in zip(pairs,best)if v)

def class_id(m):
 kk=canonkey(ac.graph_key(m));word=''.join(str(int(2*x.subs({z:0,d:0})))for _,_,x in kk)
 n=len(ac.vertices(m));pairs=list(itertools.combinations(range(n),2));mm=ac.from_key(kk)
 word=''.join(str(int(2*mm.get(e,s.S(0)).subs({z:0,d:0})))for e in pairs)
 return next((i for i,c in enumerate(ac.CC[str(n-1)])if c['word']==word),None)

def polynomial(a):
 a=se.clean(a)
 try:return s.Poly(a,q)
 except Exception:
  a=s.cancel(a);return s.Poly(a,q)
def pole(a,onlysimple=False):
 out={}
 for n,v in a.items():
  po=polynomial(v)
  keep=sum(c*q**j[0]for j,c in po.terms()if(n-j[0]==-1 if onlysimple else n-j[0]<0))
  if keep!=0:out[n]=se.clean(keep)
 return out

def ct(m):return ct_cached(canonkey(ac.graph_key(m)))

def higher(m):
 L=len(ac.vertices(m))-1;out={}
 for ss in ac.uvsubs(m):
  cg=ct(ac.subgraph(m,ss));quot=ct(ac.contracted(m,[ss]))
  out=se.add(out,se.scale(se.mul(pole(cg,True),quot,4-L),s.Rational(len(ss)-1,L)))
 return se.trim(out,4-L)

@functools.lru_cache(None)
def barejet(key,roots=None,diagonal=False):
 m=ac.from_key(key);L=len(ac.vertices(m))-1
 if diagonal:
  mm={e:s.expand(p.subs(d,z))for e,p in m.items()}
  expr=diagbare(mm,roots)
 else:expr=ac.bare(m,roots)
 return se.evaluate_expr(expr,4-L)

def bare(m,roots=None,diagonal=False):
 mm,rr=ac.norm(m,roots)if roots is not None else(ac.norm(m),None)
 return barejet(ac.graph_key(mm),rr,diagonal)

def starblock(m,inside):
 bd=set()
 for e in m:
  if set(e)&set(inside):bd.update(set(e)-set(inside))
 if len(inside)!=2 or len(bd)!=3:return None
 if any(s.expand(sum(p for e,p in m.items()if v in e)-2)!=0 for v in inside):return None
 a,b,c=sorted(bd);x,y=inside
 def ed(u,v):return m.get(tuple(sorted((u,v))),s.S(0))
 factor=ac.master(ed(a,x),ed(b,x),ed(a,y),ed(b,y),ed(x,y))
 weights={v:ed(v,x)+ed(v,y)for v in bd}
 ret={e:p for e,p in m.items()if not set(e)&set(inside)}
 for i,j in itertools.combinations(sorted(bd),2):
  k=next(v for v in bd if v not in(i,j));ee=(i,j);ret[ee]=ret.get(ee,0)+(weights[i]+weights[j]-weights[k])/2
 return factor,ac.simplify_m(ret)

def diagbare(m,roots):
 L=len(ac.vertices(m))-1
 def rec(mm):
  fac,rem,_=ac.reduce(mm,roots)
  if len(ac.vertices(rem))==2:return fac
  inner=set(ac.vertices(rem))-set(roots)
  opts=[]
  for v in sorted(inner):
   es=[p for e,p in rem.items()if v in e]
   if len(es)==3 and s.expand(sum(es)-2)==0:
    ff,rr=ac.star(rem,v);opts.append((ff,rr))
  for vs in itertools.combinations(sorted(inner),2):
   ss=starblock(rem,vs)
   if ss:opts.append(ss)
  for ff,rr in opts:
   try:return fac*ff*rec(rr)
   except ValueError:pass
  raise ValueError(('not diagonally reducible',roots,rem))
 return s.Rational(2,L)*rec(m)/z

SHIFTS={
  (4,8):({(2,4):2,(3,4):-2},(0,1)),
  (5,52):({(1,3):-2,(2,3):2},(0,4)),
  (5,56):({(1,4):-2,(2,4):2},(0,4)),
  (5,60):({(1,4):-2,(4,5):2},(0,2)),
  (5,79):({(2,3):2,(1,5):-2},(0,4)),
  (5,80):({(1,2):-2,(1,3):2},(0,4)),
  (5,91):({(1,4):2,(1,5):-2,(2,5):2,(3,4):-2},(0,4)),
  (5,127):({(0,5):-4,(1,4):2,(2,3):2},(1,2))}

@functools.lru_cache(None)
def shifted_residue(L,i):
 v,roots=SHIFTS[L,i];m=ac.graph(L,i,v)
 for ss in[ac.vertices(m)]+ac.uvsubs(m):
  assert s.expand(sum(p.coeff(d)for e,p in m.items()if set(e)<=set(ss)))==0
 raw=bare(m,roots,True)
 for fs in ac.forests(m):
  arr=[se.evaluate(ct(ac.subgraph(m,ss)),q=1)for ss in fs]
  quot,rr=ac.contracted(m,fs,roots)
  arr.append(bare(quot,rr,True))
  raw=se.add(raw,se.prod(arr,4-L))
 hh=se.evaluate(higher(m),q=1)
 r=se.clean(-raw.get(-1,0)-hh.get(-1,0))
 print('SHIFTED RESIDUE',L,i,r,flush=True)
 return r

@functools.lru_cache(None)
def ct_cached(key):
 m=ac.from_key(key);L=len(ac.vertices(m))-1
 if L==1:return{-1:s.S(-2)}
 ix=class_id(m)
 if L==4 and ix==8:
  # This exceptional shape is only needed along graph-antisymmetric index shifts.
  neg={e:s.expand(p.subs(d,-d))for e,p in m.items()}
  assert canonkey(ac.graph_key(neg))==key,('Non-even class8 deformation',m)
  return se.add(higher(m),{-1:shifted_residue(4,8)})
 roots=ac.optimal_roots(m)[2]
 raw=bare(m,roots)
 for fs in ac.forests(m):
  arr=[ct(ac.subgraph(m,ss))for ss in fs]
  quot,rr=ac.contracted(m,fs,roots);arr.append(bare(quot,rr))
  raw=se.add(raw,se.prod(arr,4-L))
 return se.scale(pole(raw),-1)


def residue(L,i):
 if(L,i)in SHIFTS:return shifted_residue(L,i)
 return se.clean(s.sympify(ct(ac.graph(L,i)).get(-1,0)).subs(q,0))

if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--classes',nargs='+',type=int,default=[79]);ap.add_argument('--loop',type=int,default=5);ar=ap.parse_args()
 out={};t=time.time()
 for i in ar.classes:
  try:
   r=residue(ar.loop,i);out[str(i)]=str(r);print('RESULT',ar.loop,i,r,'time',time.time()-t,flush=True)
  except Exception as e:
   import traceback;traceback.print_exc();out[str(i)]={'error':str(e)};break
 (ROOT/f'residues_{ar.loop}_{"_".join(map(str,ar.classes))}.json').write_text(json.dumps(out,indent=2))
 with open(ROOT/'ct_cache.pkl','wb')as f:pickle.dump(dict(shifted=[(k,shifted_residue(*k))for k in SHIFTS if k==(ar.loop,ar.classes[0])]),f)
