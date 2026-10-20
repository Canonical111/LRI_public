import sys,json,time
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'reference')]
import numba,numpy as np
numba.set_num_threads(2)
from lri_hpc.solver import compute
from check_lri_C7 import compute as old7
from compute_phi6 import compute as old6
results=[]
for task,degree in [('thermal',7),('thermal',6),('phi6',5),('phi6',3)]:
 for L in [4,8,12,24,32]:
  t=time.perf_counter();a=compute(L,task,degree)
  b=old7(L) if task=='thermal' else old6(L,degree=degree)
  errors={}
  for pres in (['raw','vacuum_subtracted'] if task=='phi6' else [None]):
   x=a[pres] if pres else a;y=b[pres] if pres else b
   for k in ['C','r','g']+(['D6'] if task=='phi6' else []):
    delta=np.abs(np.array(x[k])-np.array(y[k][:degree+1]));errors[f'{pres}:{k}']=delta.max().item()
    np.testing.assert_allclose(x[k],y[k][:degree+1],atol=1e-7,rtol=2e-11)
  row={'task':task,'degree':degree,'cutoff':L,'errors':errors,'seconds_combined':time.perf_counter()-t}
  results.append(row);print(row,flush=True)
(Path(__file__).resolve().parents[1]/'benchmarks/regression.json').write_text(json.dumps(results,indent=2))
