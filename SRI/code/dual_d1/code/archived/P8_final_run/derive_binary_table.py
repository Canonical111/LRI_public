"""Derive convergent MZVs through weight seven from products, duality,
height-one beta integral, and one-zeta(1) regularized double shuffle.
All arithmetic exact; no fitted period values are used.
"""
import sympy as s,json
from functools import lru_cache
from collections import Counter
from pathlib import Path
z={k:s.Symbol('Z'+str(k)) for k in [2,3,5,7]}
z[4]=s.Rational(2,5)*z[2]**2;z[6]=s.Rational(8,35)*z[2]**3
@lru_cache(None)
def comps(w):
 if not w:return ((),)
 return tuple((i,)+c for i in range(1,w+1) for c in comps(w-i))
def word(a):return sum(((0,)*(n-1)+(1,) for n in a),())
def index(w):
 assert w[-1]==1
 out=[];n=0
 for b in w:
  n+=1
  if b:out.append(n);n=0
 return tuple(out)
@lru_cache(None)
def sh(a,b):
 if not a:return {b:1}
 if not b:return {a:1}
 c=Counter()
 for w,n in sh(a[1:],b).items():c[(a[0],)+w]+=n
 for w,n in sh(a,b[1:]).items():c[(b[0],)+w]+=n
 return dict(c)
@lru_cache(None)
def st(a,b):
 if not a:return {b:1}
 if not b:return {a:1}
 c=Counter()
 for w,n in st(a[1:],b).items():c[(a[0],)+w]+=n
 for w,n in st(a,b[1:]).items():c[(b[0],)+w]+=n
 for w,n in st(a[1:],b[1:]).items():c[(a[0]+b[0],)+w]+=n
 return dict(c)
# Truncated bivariate exponential of log Gamma ratio.
u,v=s.symbols('u v');E={}
for k in range(2,8):
 for j in range(1,k):E[j,k-j]=-z[k]*s.binomial(k,j)/k
B={};power={(0,0):s.S.One}
for a in range(1,5):
 nxt={}
 for (i,j),c in power.items():
  for (k,l),d in E.items():
   if i+j+k+l<=7:nxt[i+k,j+l]=nxt.get((i+k,j+l),0)+c*d
 power=nxt
 for key,c in power.items():B[key]=s.expand(B.get(key,0)-c/s.factorial(a))
table={};reports=[]
for w in range(2,8):
 inds=[a for a in comps(w) if a[0]>=2];xx=s.symbols('X:'+str(len(inds)));unk=dict(zip(inds,xx));eq=[]
 eq.append(unk[(w,)]-z[w])
 for a in inds:
  dual=index(tuple(1-b for b in word(a)[::-1]));eq.append(unk[a]-unk[dual])
 for k in range(2,w-1):
  for a in [x for x in comps(k) if x[0]>=2]:
   for b in [x for x in comps(w-k) if x[0]>=2]:
    prod=table[a]*table[b]
    eq.append(sum(n*unk[c] for c,n in st(a,b).items())-prod)
    eq.append(sum(n*unk[index(c)] for c,n in sh(word(a),word(b)).items())-prod)
 for a in [x for x in comps(w-1) if x[0]>=2]:
  rhs=Counter(st((1,),a))
  for ww,n in sh((1,),word(a)).items():rhs[index(ww)]-=n
  assert not any(c[0]==1 and n for c,n in rhs.items())
  eq.append(sum(n*unk[c] for c,n in rhs.items() if n))
 for m in range(1,w):
  n=w-m;idx=(m+1,)+(1,)*(n-1)
  if idx in unk:eq.append(unk[idx]-B.get((m,n),0))
 A,b=s.linear_eq_to_matrix(eq,xx);rank=A.rank();sol=s.linsolve((A,b),xx);sol=next(iter(sol));assert not any(ex.has(*xx) for ex in sol),(w,rank,len(xx))
 solved={a:s.factor(ex) for a,ex in zip(inds,sol)}
 assert all(s.expand(ex.subs(dict(zip(xx,sol))))==0 for ex in eq)
 table.update(solved);reports.append({'weight':w,'unknowns':len(xx),'rank':rank,'equations':len(eq),'exact_residual_zero':True});print(reports[-1],flush=True)
out={'table':{','.join(map(str,a)):str(v) for a,v in table.items()},'checks':reports,'constants':'Z4=2Z2^2/5; Z6=8Z2^3/35; weight-seven spanned by Z7,Z2*Z5,Z2^2*Z3'}
Path('/mnt/data/P8_final_run/binary_table7.json').write_text(json.dumps(out,indent=2))
