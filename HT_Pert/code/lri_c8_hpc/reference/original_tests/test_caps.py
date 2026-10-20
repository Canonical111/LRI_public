#!/usr/bin/env python3
"""Show failure of the old seventh-order cap and sufficiency of the new one."""
import sys,json
from pathlib import Path
import numpy as np,numba
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
from c8_solver import compute
numba.set_num_threads(2)
rows=[]
for L in (8,16,24):
    a=compute(L,pmax=19,qmax=16)
    for P,Q in ((15,12),(23,20)):
        b=compute(L,pmax=P,qmax=Q)
        if P>19:np.testing.assert_allclose(a['C'],b['C'],rtol=5e-11,atol=1e-7)
        rows.append(dict(cutoff=L,pmax=P,qmax=Q,C8=b['C'][8],difference_vs_sufficient=b['C'][8]-a['C'][8]))
(ROOT/'results/cap_validation.json').write_text(json.dumps(rows,indent=2)+'\n')
print('Particle-cap comparisons passed.')
