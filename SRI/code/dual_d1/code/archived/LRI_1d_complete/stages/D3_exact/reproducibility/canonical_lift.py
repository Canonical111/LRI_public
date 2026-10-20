"""Deterministic, exact lift of the computed D3 difference to period words.
The only identities used are proved in the note: shuffle, logarithms,
and R_{a,b,...,b} = (-log b)^n/n! + Li_n(1-a/b).
"""
import sympy as s,json
from fractions import Fraction as Q
from collections import Counter
from functools import lru_cache
from pathlib import Path
from confluence_relations import sh
ROOT=Path(__file__).resolve().parent

def mul(A,B):
 out=Counter()
 for a,c in A.items():
  for b,d in B.items():
   for w,m in sh(a,b).items():out[w]+=c*d*m
 return {w:c for w,c in out.items() if c}
@lru_cache(None)
def lift(ex):
 if ex.is_Rational:return {():Q(int(ex.p),int(ex.q))} if ex else {}
 if ex.is_Add:
  out=Counter()
  for e in ex.args:
   for w,c in lift(e).items():out[w]+=c
  return {w:c for w,c in out.items() if c}
 if ex.is_Mul:
  out={():Q(1)}
  for e in ex.args:out=mul(out,lift(e))
  return out
 if ex.is_Pow and ex.exp.is_Integer and ex.exp>=0:
  out={():Q(1)}
  for _ in range(int(ex.exp)):out=mul(out,lift(ex.base))
  return out
 if ex.is_Symbol:
  name=str(ex)
  if name.startswith('R_'):
   w=tuple(int(z[1:]) for z in name.split('_')[1:]);return {w:Q(1)}
  if name in ['Z2','Z3','Z4']:
   n=int(name[1:]);return {(2,)+(1,)*(n-1):{2:Q(-2),3:Q(-4,3),4:Q(-8,7)}[n]}
 if ex.func==s.log and ex.args[0].is_Rational and ex.args[0]>0:
  z=ex.args[0];out=Counter()
  for p,k in s.factorint(int(z.p)).items():out[(p,)]-=Q(k)
  for p,k in s.factorint(int(z.q)).items():out[(p,)]+=Q(k)
  return {w:c for w,c in out.items() if c}
 if ex.func==s.polylog:
  n,c=ex.args;r=1-c
  if n.is_Integer and r.is_Rational and r>0:
   a,b=int(r.p),int(r.q);ww=(a,)+(b,)*(int(n)-1);zz=(b,)*int(n)
   out=Counter({ww:Q(1)});out[zz]-=Q(1)
   return {w:v for w,v in out.items() if v}
 raise ValueError(('UNSUPPORTED exact expression',ex))

def build():
 ex=s.sympify((ROOT/'D3_difference_symbolic.expr').read_text())
 out=lift(ex)
 assert all(len(w) in (2,3,4) and all(1<=a<=7 for a in w) for w in out)
 data=[[list(w),str(c)] for w,c in sorted(out.items())]
 (ROOT/'D3_linear_words.json').write_text(json.dumps(data,indent=2))
 print('Canonical lift:',len(out),'words;',dict(Counter(map(len,out))))
 return out
if __name__=='__main__':build()
