#!/usr/bin/env python3
"""Compare the newly integrated lower loops to the retained analytic coefficients."""
from pathlib import Path
import json
import mpmath as mp
import laurent_assembly as a
R=Path(__file__).resolve().parent;mp.mp.dps=80
ref={k:mp.mpf(v)for k,v in json.loads((R/'records/reference.json').read_text()).items()}
A,Q,P4=ref['A'],ref['Q'],ref['P4']
cs=[mp.mpf('.5'),-mp.mpf(1)/6,A/9,(A*A+mp.pi**2/3-8*Q)/108,(16*P4-A**3-A*mp.pi**2-53*mp.pi**3-1436*mp.zeta(3)-8*A*Q)/648]
out={}
for cut in ['span','maxgap']:
    raw=json.loads((R/f'records/lower_{cut}_32.json').read_text(),parse_float=str);raw['5']=[{},{}]
    v=a.assemble(raw)
    out[cut]={'new_lower_coefficients':v['C'][:5],'analytic_lower_coefficients':cs,
              'new_minus_analytic':[x-y for x,y in zip(v['C'][:5],cs)],
              'b3_error':v['beta'][2]-ref['b3'],'c3_error':v['gamma'][2]-ref['c3'],
              'b4_error':v['beta'][3]-ref['b4'],'c4_error':v['gamma'][3]-ref['c4']}
(R/'records/lower_controls.json').write_text(json.dumps(a.serial(out),indent=2))
for c,v in out.items():print(c,[mp.nstr(x,8)for x in v['new_minus_analytic']])
