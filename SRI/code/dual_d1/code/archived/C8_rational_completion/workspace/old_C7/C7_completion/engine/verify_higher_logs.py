"""Numerical check of exact higher-log differences, independent of new singles."""
from pathlib import Path
import json,sympy as s,mpmath as mp
from evaluate_periods import evaluate
ROOT=Path(__file__).resolve().parent
patterns=['C7_log*_residual.expr','C5_tail_log*_residual_symbolic.expr','aux_g*_residual_symbolic.expr']
exs={p.stem:s.sympify(p.read_text()) for pat in patterns for p in ROOT.glob(pat)}
assert exs,'Generate higher-log expressions first.'
syms=set().union(*(x.free_symbols for x in exs.values()))
reg={x:tuple(int(t[1:]) if t.startswith('m') else int(t) for t in str(x).split('_')[1:]) for x in syms if str(x).startswith('R_')}
mp.mp.dps=100
vals={tuple(map(int,k.split(','))):mp.mpf(v) for k,v in json.loads((ROOT/'final_periods_run2.json').read_text()).items()}
missing=set(reg.values())-vals.keys()
if missing:vals.update(evaluate(missing,dps=100,R=120,ntaylor=290,nasym=150,stepfrac='.35'))
sub={x:s.Float(mp.nstr(vals[w],100),100) for x,w in reg.items()};sub.update({s.Symbol(f'Z{k}'):s.zeta(k) for k in range(2,7)})
out={}
for name,ex in sorted(exs.items()):
 val=s.N(ex.xreplace(sub),85);assert not val.free_symbols
 err=abs(mp.mpf(str(val)));assert err<mp.mpf('1e-75'),(name,val)
 out[name]={'residual':str(val),'rational_or_elementary_zero':bool(s.simplify(ex)==0)}
 print('PASS',name,str(val),flush=True)
(ROOT/'higher_log_verification.json').write_text(json.dumps({'status':'pass','maximum_residual':str(max(abs(mp.mpf(q['residual'])) for q in out.values())),'checks':out,'qualification':'Nonrational period identities are verified numerically, not certified symbolically.'},indent=2))
