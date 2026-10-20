"""Convergent/regularized double-shuffle reduction at weight six."""
import sympy as s,json
from functools import lru_cache
from collections import Counter
from pathlib import Path
from hyperlog_core import shuffle

def comps(n):
 if not n:return [()]
 return [(k,)+r for k in range(1,n+1) for r in comps(n-k)]
def conv(n):return [a for a in comps(n) if a[0]>=2]
def word(a):return tuple(j for k in a for j in ([0]*(k-1)+[1]))
def idx(w):
 out=[];n=0
 for b in w:
  n+=1
  if b:out.append(n);n=0
 assert n==0
 return tuple(out)
@lru_cache(None)
def stuff(a,b):
 if not a:return {b:1}
 if not b:return {a:1}
 out=Counter()
 for w,c in stuff(a[1:],b).items():out[(a[0],)+w]+=c
 for w,c in stuff(a,b[1:]).items():out[(b[0],)+w]+=c
 for w,c in stuff(a[1:],b[1:]).items():out[(a[0]+b[0],)+w]+=c
 return dict(out)
z2,z3,z4,z5,z6=s.symbols('Z2 Z3 Z4 Z5 Z6')
val={(2,):z2,(3,):z3,(2,1):z3,(4,):z4,(3,1):z4/4,(2,2):3*z4/4,(2,1,1):z4}
keys=conv(6);vs={k:s.Symbol('m'+'_'.join(map(str,k))) for k in keys}
def ex(d):return sum(c*vs[k] for k,c in d.items())
def prod(a,b):return s.expand(val[a]*val[b]).subs(z2*z4,s.Rational(7,4)*z6)
eq=[vs[(6,)]-z6]
for i in (2,3,4):
 for a in conv(i):
  for b in conv(6-i):
   eq.append(ex(stuff(a,b))-prod(a,b))
   eq.append(ex({idx(w):c for w,c in shuffle(word(a),word(b)).items()})-prod(a,b))
for a in keys:
 eq.append(vs[a]-vs[idx(tuple(1-b for b in word(a)[::-1]))])
for a in conv(5):
 ds=Counter(stuff((1,),a))
 for w,c in shuffle((1,),word(a)).items():ds[idx(w)]-=c
 ds={k:v for k,v in ds.items() if v}
 assert all(k[0]>=2 for k in ds)
 eq.append(ex(ds))
sol=s.solve(eq,list(vs.values()))
assert len(sol)==len(vs),(len(sol),len(vs))
assert all(not (ex.free_symbols&set(vs.values())) for ex in sol.values())
assert all(s.expand(e.subs(sol))==0 for e in eq)
print('Exact weight-six reductions:')
for k in keys:print(k,'=',sol[vs[k]])
Path(__file__).with_name('weight6_reductions.json').write_text(json.dumps({','.join(map(str,k)):str(sol[vs[k]]) for k in keys},indent=2))
print('PASS',len(eq),'equations;',len(sol),'MZVs')
