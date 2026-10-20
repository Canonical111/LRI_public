from read_expression import load as load_expr
"""Cutoff series of the exact raw moments; products precede finite parts."""
import sympy as s,json,time
from pathlib import Path
from functools import lru_cache
from asymptotic_gpl import extract_rows,E as eps,ell
ROOT=Path(__file__).resolve().parent
CACHE=ROOT/'series';CACHE.mkdir(exist_ok=True)
@lru_cache(maxsize=None)
def rows(tag):return json.loads((ROOT/(tag+'_negative.json')).read_text())
@lru_cache(maxsize=None)
def pol(n,kind,deriv='base',p=0):
 tag=f'{kind}{n}_{deriv}';f=CACHE/(tag+f'_p{p}.expr')
 if f.exists():return load_expr(f)
 start=time.time();out=extract_rows(rows(tag),n-1,p,None)
 f.write_text(s.sstr(out, order="none"))
 print('EXTRACT',tag,'p',p,'terms',len(s.Add.make_args(out)),'seconds',time.time()-start,flush=True)
 return out

def val(n,kind,deriv='base',p=0,m=0):return s.expand(pol(n,kind,deriv,p)).coeff(ell,m)

def product0(*args):
 """args are dictionaries {cutoff degree: logarithm polynomial}."""
 out={0:s.S.One}
 for a in args:
  nxt={}
  for i,c in out.items():
   for j,d in a.items():nxt[i+j]=nxt.get(i+j,0)+c*d
  out=nxt
 return s.expand(out.get(0,s.S.Zero))

@lru_cache(maxsize=None)
def raw(n,kind,deriv='base',pmin=None,pmax=None):
 if pmin is None:pmin=-(n//2)
 if pmax is None:pmax=2 if n<=3 else 1
 return {p:pol(n,kind,deriv,p) for p in range(pmin,pmax+1)}

if __name__=='__main__':
 from evaluate_periods import evaluate
 tests={
 'EA3finite':val(3,'EA'),
 'EQ2finite':val(2,'EQ'),
 'EZ2finite':val(2,'EZ'),
 'EQ4finite':val(4,'EQ'),
 'EA3vfinite':val(3,'EA','v'),
 'EQ4vfinite':val(4,'EQ','v'),
 'EA3dfinite':val(3,'EA','d')}
 z2,z3,z4=s.symbols('Z2 Z3 Z4')
 exact={'EA3finite':-26+10*z2,'EQ2finite':-2*z2,
 'EZ2finite':2*z2-2,'EQ4finite':6-12*z2-54*z3-25*z4,
 'EA3vfinite':-108+60*z2+22*z3-34*z4+16*s.log(2)}
 print('TEST EXPRESSIONS',tests,flush=True)
 words={x:tuple(int(t[1:]) if t.startswith('m') else int(t) for t in str(x).split('_')[1:]) for ex in tests.values() for x in ex.free_symbols if str(x).startswith('R_')}
 vv=evaluate(set(words.values()),dps=65,ntaylor=190,nasym=85)
 subs={x:s.Float(str(vv[w]),65) for x,w in words.items()}
 subs.update({s.Symbol(f'Z{k}'):s.zeta(k) for k in range(2,7)})
 out={}
 for tag,ex in tests.items():
  nu=s.N(ex.subs(subs),50);diff=s.N((ex-exact.get(tag,ex)).subs(subs),40)
  out[tag]={'value':str(nu),'known_residual':str(diff)};print(tag,nu,'residual',diff,flush=True)
 (ROOT/'endpoint_validation.json').write_text(json.dumps(out,indent=2))
 (ROOT/'endpoint_validation_periods.json').write_text(json.dumps({','.join(map(str,w)):str(v) for w,v in vv.items()},indent=2))
