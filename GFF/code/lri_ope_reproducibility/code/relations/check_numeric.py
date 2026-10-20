#!/usr/bin/env python3
"""Numerical regression for the algebraic map, using saved master inputs."""
import json
from pathlib import Path
import mpmath as mp
from relations import from_thermal, serial, omega_two

root=Path(__file__).resolve().parent
mp.mp.dps=70
inputs=json.loads((root/'regression_inputs.json').read_text())
report={}
for ds,row in inputs.items():
    d=mp.mpf(ds);q=d/4
    A=mp.digamma(2*q)-2*mp.digamma(q)+mp.digamma(1)
    R=mp.polygamma(1,2*q)-mp.polygamma(1,1)
    U=mp.polygamma(2,q);V=mp.polygamma(2,1)+mp.polygamma(2,2*q)
    X=mp.polygamma(3,2*q)-mp.polygamma(3,1)
    T,P4,P5,K,L,Z=[mp.mpf(row[k]) for k in ['T','P4','P5','K','L','Z']]
    C3=(A*A+R)/108-T/81
    C4=(16*P4-A**3-mp.mpf(4)/3*A*T-3*A*R+mp.mpf(53)/2*U-3*V)/648
    C5=(-1536*(P5+K)+384*A*P4-576*L-48*T*T+120*A*A*T+168*T*R+7152*Z
         -15*A**4-90*A*A*R+414*A*U-108*A*V-117*R*R-75*X)/46656
    omega=13*Z-L-12*K
    out=from_thermal(d,C3,C4,C5,omega)
    diffs={k:out['a_coefficients'][int(k)]-mp.mpf(v) for k,v in row['coefficients'].items()}
    if max(abs(v) for v in diffs.values())>mp.mpf('1e-55'):
        raise AssertionError((ds,diffs))
    report[ds]={'maximum_absolute_difference_from_saved_coefficients':max(abs(v) for v in diffs.values()),
                'C3':C3,'C4':C4,'C5':C5,'omega':omega,
                'a_coefficients':out['a_coefficients']}
report['qualification']='Regression against the earlier one-point coefficient file; not independent physical validation.'
text=json.dumps(serial(report),indent=2)
(root/'numeric_checks.json').write_text(text+'\n')
print(text)
