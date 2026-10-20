"""Exact highest-log checks independent of the unknown Omega."""
from pathlib import Path
import sympy as s,json,time
from read_expression import load
ROOT=Path(__file__).resolve().parent;l=s.Symbol('ell');Z2=s.Symbol('Z2')
def reduce2(ex):
 repl={}
 for sy in ex.free_symbols:
  if not str(sy).startswith('R_'):continue
  w=tuple(int(a[1:]) if a.startswith('m') else int(a) for a in str(sy).split('_')[1:])
  if len(w)==1:repl[sy]=-s.log(w[0]) if w[0] else s.S.Zero
  elif len(w)==2:
   a,b=w
   if b:repl[sy]=s.log(b)**2/2+s.polylog(2,1-s.Rational(a,b))
   elif a:repl[sy]=-Z2-s.log(a)**2/2
   else:repl[sy]=s.S.Zero
 ex=s.expand(ex.xreplace(repl))
 for q in list(ex.atoms(s.polylog)):
  if q.args[0]!=2 or not q.args[1].is_Rational:continue
  x=q.args[1]
  if x<0:ex=ex.subs(q,-s.polylog(2,x/(x-1))-s.log(1-x)**2/2)
 for q in list(ex.atoms(s.polylog)):
  if q.args[0]!=2 or not q.args[1].is_Rational:continue
  x=q.args[1]
  if x==0:ex=ex.subs(q,0)
  elif x==1:ex=ex.subs(q,Z2)
  elif x==s.Rational(1,2):ex=ex.subs(q,Z2/2-s.log(2)**2/2)
  elif s.Rational(1,2)<x<1:ex=ex.subs(q,Z2-s.polylog(2,1-x)-s.log(x)*s.log(1-x))
 ex=s.expand(s.expand_log(ex,force=True)).subs(s.pi**2,6*Z2)
 for q in list(ex.atoms(s.log)):
  x=q.args[0]
  if x.is_Rational and x>0:
   a,b=x.as_numer_denom();re=s.S.Zero
   for prime,m in s.factorint(a).items():re+=m*s.log(prime)
   for prime,m in s.factorint(b).items():re-=m*s.log(prime)
   ex=ex.subs(q,re)
 return s.expand(ex)
if __name__=='__main__':
 start=time.time();raw=load(ROOT/'series'/'norm_C7_1_0.expr');checks={}
 for n in [5,6,7,8]:
  pred=load(ROOT/f'A7v_log{n}_predicted.expr');assert not any('Omega' in str(x) for x in pred.free_symbols)
  diff=s.expand(raw.coeff(l,n)-pred);(ROOT/f'A7v_fresh_log{n}_residual.expr').write_text(str(diff))
  red=reduce2(diff);(ROOT/f'A7v_fresh_log{n}_residual_reduced.expr').write_text(str(red))
  checks[str(n)]={'prediction':str(pred),'exact_zero':red==0,'residual_terms':0 if red==0 else len(s.Add.make_args(red)),'new_Omega_used':False}
  print('LOG',n,checks[str(n)],flush=True)
 (ROOT/'A7v_fresh_higher_log_checks.json').write_text(json.dumps({'checks':checks,'seconds':time.time()-start,'identities':'weight-two primitive; Euler reflection; Landen; logarithm multiplicativity'},indent=2))
 if not all(q['exact_zero'] for q in checks.values()):raise SystemExit(2)
