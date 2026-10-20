#!/usr/bin/env python3
"""Numerical continuation of two fitted trial branches, not an LRI calculation.

Requires verification/results.json and the companion modules. Root residuals
are numerical consistency checks, not certified error bounds or a rigorous
global branch proof.
"""
from pathlib import Path
import json
from formal_series import s, mp
from endpoint_model import numeric_function

root=Path(__file__).resolve().parents[1]
data=json.loads((root/'verification/results.json').read_text())
coeffs={tuple(k):s.Rational(v) for k,v in data['trial_polynomials']}
mp.mp.dps=60
report={'scope':__doc__.strip(),'branches':{}}
for complete in (False, True):
    fn=numeric_function(coeffs,complete,0)
    y=mp.mpf(0);old_t=mp.mpf(0);rows=[]
    for k in range(1,51):
        t=mp.mpf(k)/100
        guess=2*t if k==1 else y+2*(t-old_t)
        y=mp.findroot(lambda yy:fn(yy,t),(guess-mp.mpf('.002'),guess+mp.mpf('.002')),tol=mp.mpf('1e-52'))
        assert abs(fn(y,t))<mp.mpf('1e-48')
        fy=mp.diff(lambda yy:fn(yy,t),y)
        assert fy>0
        old_t=t
        if k%5==0:
            rows.append({'t':mp.nstr(t,5),'Delta':mp.nstr(1-y,40),'Fy':mp.nstr(fy,30)})
    report['branches']['completed_tau0' if complete else 'unmodified']=rows
    print('completed=',complete,' trial endpoint=',mp.nstr(1-y,35),flush=True)
(root/'verification/branch_continuation.json').write_text(json.dumps(report,indent=2)+'\n')
