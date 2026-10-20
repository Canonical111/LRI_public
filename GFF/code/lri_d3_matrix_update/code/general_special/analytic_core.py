"""Exact d-dimensional conformal graph reductions.
A critical affine base r represents r*D; regulator slopes are not rescaled.
All graph exponents use |x-y|^{-p}, not squared-distance powers.
The historical internal FullLineBeta/Selberg heads are symbolic labels only;
the Gamma evaluation is the d-dimensional implementation in series_engine.py.
"""
from __future__ import annotations
import itertools,json,functools
from pathlib import Path
from collections import defaultdict
import sympy as s
ROOT=Path(__file__).parent
CC=json.load(open(ROOT/'C5_wheel_nonprimitive/reduced_classes.json'))
CC['1']=[dict(word='2',aut=2,subgraphs=[],w4=[3,2],w2=[1,2])]
z,d=s.symbols('z d');BB=s.Function('FullLineBeta');JJ=s.Function('TwoPointMaster');MS=s.Function('FullLineSelberg')

def graph(L,i,shift=None):
 pairs=list(itertools.combinations(range(L+1),2));shift=shift or{}
 return {e:s.Rational(int(q),2)*(1-z)+d*shift.get(e,0) for e,q in zip(pairs,CC[str(L)][i]['word'])if q!='0'}
def vertices(m):return sorted(set(itertools.chain.from_iterable(m)))
def simplify_m(m):return {e:s.expand(a)for e,a in m.items()if s.expand(a)!=0}
def norm(m,roots=None):
 vs=vertices(m);perm={v:i for i,v in enumerate(vs)}
 out={(perm[a],perm[b]):p for(a,b),p in m.items()}
 return(out,tuple(perm[r]for r in roots))if roots is not None else out

def integer_m(m):
 out={e:int(2*p.subs({z:0,d:0}))for e,p in m.items()}
 assert all(p>0 for p in out.values())
 return out

def uvsubs(m):
 vs=vertices(m);n=len(vs);M=integer_m(m);ret=[]
 for k in range(2,n):
  for ss in itertools.combinations(vs,k):
   S=set(ss);sub={e:p for e,p in M.items()if set(e)<=S}
   if sum(sub.values())!=2*(k-1):continue
   good=True
   for mask in range(1,1<<(k-1)):
    cut={ss[j]for j in range(k)if mask>>j&1}
    if sum(p for(a,b),p in sub.items()if(a in cut)!=(b in cut))<2:good=False;break
   if good:ret.append(ss)
 return ret

def forests(m):
 subs=uvsubs(m);ret=[]
 for k in range(1,len(subs)+1):
  for fs in itertools.combinations(subs,k):
   if sum(map(len,fs))==len(set(itertools.chain.from_iterable(fs))):ret.append(fs)
 return ret

def contracted(m,fs,roots=None):
 repl={v:min(ss)for ss in fs for v in ss};ret={}
 for(a,b),p in m.items():
  aa=repl.get(a,a);bb=repl.get(b,b)
  if aa==bb:continue
  e=tuple(sorted((aa,bb)));ret[e]=ret.get(e,0)+p
 rr=tuple(repl.get(v,v)for v in roots)if roots is not None else None
 return norm(simplify_m(ret),rr)if rr is not None else norm(simplify_m(ret))

def subgraph(m,ss):return norm({e:p for e,p in m.items()if set(e)<=set(ss)})
def graph_key(m):return tuple((a,b,s.expand(p))for(a,b),p in sorted(norm(m).items()))
def from_key(key):return {(a,b):p for a,b,p in key}

def beta(u,v):
 if u==0 or v==0:return s.S(0)
 # Full-line integral is symmetric in its two exponents.
 return BB(*sorted([s.expand(u),s.expand(v)],key=s.default_sort_key))

def complete(args):
 a,b,c,dd,e=args
 return [3-a-b-c-dd-e,a,c,b+dd+e-1,b,dd,a+c+e-1,e,2-a-b-e,2-c-dd-e]
P5=list(itertools.combinations(range(5),2));IDX5={e:i for i,e in enumerate(P5)}
PERMS5=[tuple(IDX5[tuple(sorted((p[i],p[j])))]for i,j in P5)for p in itertools.permutations(range(5))]

@functools.lru_cache(None)
def canonical_master(args):
 # Exact completed-graph (S5) covariance of the full-line period.
 lam=[s.expand(x)for x in complete(args)]
 def key(v):
  return tuple(tuple(vv.coeff(var)if var is not None else vv.subs({z:0,d:0})for var in [None,z,d])for vv in v)
 reps=[tuple(lam[i]for i in p)for p in PERMS5]
 # Prefer a connected, reflection-symmetric two-point representation and no zero powers.
 def score(v):
  a,b,c,dd,e=[v[i]for i in [1,4,2,5,7]]
  aa=[a,b,c,dd,e]
  half=sum(q.subs({z:0,d:0})==s.Rational(1,2)for q in aa)
  sym=(a==c)+(b==dd)
  return (-sym,-half,sum(q==0 for q in aa),s.default_sort_key(aa))
 best=min(reps,key=score)
 return tuple(best[i]for i in [1,4,2,5,7])

def master(a,b,c,dd,e):
 args=tuple(map(s.expand,[a,b,c,dd,e]))
 a,b,c,dd,e=args
 if e==0:return beta(a,b)*beta(c,dd)
 # A variable with only two attachments can be integrated directly.
 if a==0:return beta(b,e)*beta(c,dd+b+e-1)
 if b==0:return beta(a,e)*beta(c+a+e-1,dd)
 if c==0:return beta(dd,e)*beta(a,b+dd+e-1)
 if dd==0:return beta(c,e)*beta(a+c+e-1,b)
 aa=canonical_master(args)
 if aa[4]==0:return beta(aa[0],aa[1])*beta(aa[2],aa[3])
 if aa[0]==aa[2] and aa[1]==aa[3]:return MS(aa[0],aa[1],aa[4])
 return JJ(*aa)

def reduce(m,roots):
 m=simplify_m(m);remain=set(vertices(m));fac=s.S(1);steps=[]
 while True:
  opts=[]
  for k in [1,2]:
   for inside in itertools.combinations(sorted(remain-set(roots)),k):
    boundary=set();es=[]
    for e,p in m.items():
     if set(e)&set(inside):boundary.update(set(e)-set(inside));es.append((e,p))
    if len(boundary)==2:opts.append((k,inside,sorted(boundary),es))
  if not opts:break
  k,inside,boundary,es=min(opts,key=lambda q:(q[0],q[1]));a,b=boundary
  if k==1:
   fac*=beta(es[0][1],es[1][1])
  else:
   x,y=inside;mp=dict(es)
   powers=[mp.get(tuple(sorted(e)),s.S(0))for e in [(a,x),(b,x),(a,y),(b,y),(x,y)]]
   fac*=master(*powers)
  newp=sum(p for e,p in es)-k
  for e,p in es:del m[e]
  ne=tuple(boundary);m[ne]=m.get(ne,0)+newp;m=simplify_m(m);remain-=set(inside)
  steps.append((inside,boundary,es))
 return fac,m,steps

def unsafe_root_subsets(m):
 # All superficially divergent collision sets matter for IR safety, even
 # power-divergent and non-1PI sets. The counterterm forest remains 1PI.
 vs=vertices(m);mm=integer_m(m);bad=[]
 for k in range(2,len(vs)):
  for ss in itertools.combinations(vs,k):
   if sum(v for e,v in mm.items() if set(e)<=set(ss))>=2*(k-1):bad.append(ss)
 return bad

def optimal_roots(m):
 subs=unsafe_root_subsets(m);candidates=[]
 for rr in itertools.combinations(vertices(m),2):
  if any(set(rr)<=set(ss)for ss in subs):continue
  fac,rem,steps=reduce(m,rr);candidates.append((len(vertices(rem)),(len(fac.atoms(JJ)),len(fac.atoms(MS)),len(str(fac))),rr,fac,rem,steps))
 if not candidates:raise ValueError('No IR-safe roots')
 return min(candidates,key=lambda x:x[:2])

def bare(m,roots=None):
 n=len(vertices(m));L=n-1
 if roots is None:
  size,_,roots,fac,rem,steps=optimal_roots(m)
 else:fac,rem,steps=reduce(m,roots);size=len(vertices(rem))
 if size!=2:raise ValueError(('Nonreducible',n,roots,m,rem))
 return s.Rational(2,L)*fac/z

def star(m,v):
 nn=[(b if a==v else a,p)for(a,b),p in m.items()if v in(a,b)]
 if len(nn)!=3 or s.simplify(sum(p for _,p in nn)-2)!=0:raise ValueError(('Not unique',v,nn))
 ret={e:p for e,p in m.items()if v not in e}
 for i,j in itertools.combinations(range(3),2):
  k=3-i-j;ee=tuple(sorted((nn[i][0],nn[j][0])));ret[ee]=ret.get(ee,0)+1-nn[k][1]
 return beta(nn[0][1],nn[1][1]),simplify_m(ret)

def unique_bare(m,roots,stars):
 L=len(vertices(m))-1;fac=s.S(1);mm={e:s.expand(p.subs(d,z))for e,p in m.items()}
 # Reduce series vertices before each uniqueness move.
 for vv in stars:
  ff,mm,_=reduce(mm,roots);fac*=ff
  # A terminal reduction may consume a planned star: then it is unnecessary.
  if vv not in vertices(mm):continue
  ff,mm=star(mm,vv);fac*=ff
 ff,mm,_=reduce(mm,roots);fac*=ff
 if len(vertices(mm))!=2:raise ValueError(('Unique still nonreducible',mm))
 return s.Rational(2,L)*fac/z
