#!/usr/bin/env python3
"""One independent process per benchmark. Warm compilation on cutoff 4."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('MKL_NUM_THREADS','1')
import argparse,json,sys,time,resource,cProfile,pstats,platform
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'reference/original_code')]
import numpy as np
import numba
import contextlib
def threadpool_limits(limits):
 # threadpoolctl 2.2 raises on some BLAS builds; BLAS threads are also capped by env.
 try:
  from threadpoolctl import threadpool_limits as tl
  return tl(limits=limits)
 except Exception:return contextlib.nullcontext()
p=argparse.ArgumentParser();p.add_argument('--solver',choices=['old','new'],required=True)
p.add_argument('--cutoff',type=int,required=True);p.add_argument('--threads',type=int,default=4)
p.add_argument('--scheme',default='raw',choices=['raw','vacuum_only']);p.add_argument('--backend',default='stored',choices=['stored','ranked'])
p.add_argument('--output',type=Path,required=True);p.add_argument('--profile',action='store_true');a=p.parse_args()
numba.set_num_threads(a.threads)
if a.solver=='old':
 from c8_solver import compute
 fn=lambda L:compute(L,8,a.scheme)
else:
 from lri_c8.engine import compute
 fn=lambda L:compute(L,a.scheme,a.backend)
with threadpool_limits(limits=1):
 wt=time.perf_counter();fn(4);warm=time.perf_counter()-wt
 prof=cProfile.Profile();
 if a.profile:prof.enable()
 start=time.perf_counter();r=fn(a.cutoff);elapsed=time.perf_counter()-start
 if a.profile:prof.disable()
ref=json.loads((ROOT/f'inputs/{a.scheme}/{a.scheme}_L{a.cutoff}_d8.json').read_text()) if (ROOT/f'inputs/{a.scheme}/{a.scheme}_L{a.cutoff}_d8.json').exists() else None
residuals=None
if ref is not None:
 residuals={k:float(np.max(abs(np.array(r[k])-ref[k]))) for k in ('C','r','g','energies')}
 for k in residuals:np.testing.assert_allclose(r[k],ref[k],atol=1e-7,rtol=2e-11)
out={'config':{k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()},'seconds':elapsed,'warmup_seconds':warm,
     'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'reference_max_abs':residuals,
     'environment':{'python':platform.python_version(),'numpy':np.__version__,'numba':numba.__version__,
      'platform':platform.platform(),'cpu_quota':Path('/sys/fs/cgroup/cpu.max').read_text().strip() if Path('/sys/fs/cgroup/cpu.max').exists() else 'unknown'},
     'result':r}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
if a.profile:
 with a.output.with_suffix('.profile.txt').open('w') as f:pstats.Stats(prof,stream=f).sort_stats('cumtime').print_stats(35)
print(a.solver,a.cutoff,a.scheme,a.backend,a.threads,round(elapsed,4),round(out['peak_rss_mib'],1),flush=True)
