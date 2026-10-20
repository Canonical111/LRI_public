from pathlib import Path
import json
import sympy as s
import mpmath as mp
from asymptotic_gpl import extract_rows,ell
from evaluate_periods import evaluate
ROOT=Path(__file__).resolve().parent
rows=json.loads((ROOT/'Adelta23_negative.json').read_text())
raw=extract_rows(rows,2,0,None)
raw=s.Poly(raw,ell)
# Only higher logarithms are a lower-order test; do not use V.
higher={str(j):raw.coeff_monomial(ell**j) for j in range(2,7)}
registry={a:tuple(int(t[1:]) for t in str(a).split('_')[1:]) for ex in higher.values() for a in ex.free_symbols if str(a).startswith('R_')}
vals=evaluate(set(registry.values()),dps=80,R=100,ntaylor=260,nasym=115)
subs={a:s.Float(mp.nstr(vals[w],80),80) for a,w in registry.items()}
Z2=s.zeta(2);Z3=s.zeta(3);Z4=s.zeta(4);L=s.log(2)
a=-4*Z2
A=-8-4*Z2-2*Z3+16*L
p=8-2*Z2-7*Z3-8*L
E=-16+14*Z2-22*Z3+12*Z4+8*L-8*L**2-16*s.polylog(4,s.Rational(1,2))-14*Z3*L+4*Z2*L**2-2*L**4/3
expected={'6':s.Rational(1,3),'5':-s.Rational(1,15),'4':-s.Rational(1,3)-a/4,'3':s.Rational(4,3)+a/6+A/3-p/3,'2':E/2}
out={}
for j,ex in higher.items():
    residual=s.N((ex-expected[j]).subs(subs),70)
    print('ell power',j,'raw=',s.N(ex.subs(subs),30),'residual=',residual,flush=True)
    assert abs(mp.mpf(str(residual)))<mp.mpf('1e-60')
    out[j]={'raw_exact':str(ex),'expected':str(expected[j]),'residual':str(residual)}
(ROOT/'V_higher_log_checks.json').write_text(json.dumps(out,indent=2)+'\n')
(ROOT/'Adelta2_full_poly.expr').write_text(str(raw.as_expr())+'\n')
print('PASS: all five higher logarithms, without using V.')
