import os,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'reference')]
import numba,numpy as np
numba.set_num_threads(2)
from lri_hpc.solver import compute
from check_lri_C7 import compute as c7
from compute_phi6 import compute as phi6
rows=[]
for task,degree in [('thermal',7),('phi6',5)]:
 for L in [4,8]:
  a=compute(L,task,degree)
  b=c7(L,True) if task=='thermal' else phi6(L,True,degree)
  for p in ([None] if task=='thermal' else ['raw','vacuum_subtracted']):
   x=a[p] if p else a;y=b[p] if p else b
   for k in ['C','r','g']+(['D6'] if task=='phi6' else []):np.testing.assert_allclose(x[k],y[k],rtol=2e-11,atol=1e-7)
  r={'task':task,'cutoff':L,'original_full_recursion':b.get('full_recursion_max_abs_residual') if task=='thermal' else {p:b[p]['full_recursion_residual'] for p in ['raw','vacuum_subtracted']}}
  # The independent full recursion must agree with the Rayleigh-quotient results (review LRI-002).
  res=[r['original_full_recursion']] if task=='thermal' else list(r['original_full_recursion'].values())
  assert all(x is not None and x<=1e-8 for x in res),('full recursion disagrees',task,L,res)
  rows.append(r);print(r,flush=True)
(ROOT/'benchmarks/full_recursion_validation.json').write_text(json.dumps(rows,indent=2)+'\n')
