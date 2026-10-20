from pathlib import Path
import json
import mpmath as mp
import sympy as s
from evaluate_periods import evaluate
ROOT=Path(__file__).resolve().parent
ex=s.sympify((ROOT/'V_symbolic.expr').read_text())
registry={x:tuple(int(t[1:]) for t in str(x).split('_')[1:]) for x in ex.free_symbols if str(x).startswith('R_')}
vals=evaluate(set(registry.values()),dps=75,R=100,ntaylor=240,nasym=100)
subs={x:s.Float(mp.nstr(vals[w],75),75) for x,w in registry.items()}
V=s.N(ex.subs(subs),65)
expected=json.loads((ROOT/'three_tail_second.json').read_text())[-1]['V']
residual=mp.mpf(str(V))-mp.mpf(expected)
print('V from exact regulated hyperlogs:',V)
print('V from convergent integral:',expected)
print('Difference:',mp.nstr(residual,12))
assert abs(residual)<mp.mpf('1e-55')
out={'V_hyperlogs':str(V),'V_integral':expected,'residual':mp.nstr(residual,30),'status':'PASS','note':'Independent numerical check, not an interval bound.'}
(ROOT/'V_independent_check.json').write_text(json.dumps(out,indent=2)+'\n')
(ROOT/'V_period_values.json').write_text(json.dumps({','.join(map(str,w)):mp.nstr(v,75) for w,v in vals.items()},indent=2)+'\n')
