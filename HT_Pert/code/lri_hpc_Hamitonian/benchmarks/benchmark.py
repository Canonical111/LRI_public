#!/usr/bin/env python3
"""Run one implementation in its own process; warming and imports are separate.

Use repeated independent processes for runtime/RSS comparisons. The reference
profile is NOT an unprofiled baseline. Peak RSS includes imports and warmup.
"""
import os
for name in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS','BLIS_NUM_THREADS']:
    os.environ[name]='1'
import sys,json,time,argparse,resource,platform
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'reference')]
p=argparse.ArgumentParser();p.add_argument('--impl',choices=['original','optimized'],required=True)
p.add_argument('--cutoff',type=int,default=40);p.add_argument('--task',choices=['thermal','phi6'],default='thermal')
p.add_argument('--degree',type=int);p.add_argument('--threads',type=int,default=1);p.add_argument('--output',required=True)
a=p.parse_args();start=time.perf_counter()
if a.impl=='optimized':
 import numba;numba.set_num_threads(a.threads)
 from lri_hpc.solver import compute
 f=lambda L:compute(L,a.task,a.degree)
else:
 if a.task=='thermal':
  from check_lri_C7 import compute
  f=lambda L:compute(L)
 else:
  from compute_phi6 import compute
  f=lambda L:compute(L,degree=a.degree or 5)
import_seconds=time.perf_counter()-start
warm=time.perf_counter();f(4);warm_seconds=time.perf_counter()-warm
start=time.perf_counter();r=f(a.cutoff);elapsed=time.perf_counter()-start
out={'implementation':a.impl,'task':a.task,'cutoff':a.cutoff,'threads':a.threads,
     'import_seconds':import_seconds,'warmup_seconds':warm_seconds,'wall_seconds':elapsed,
     'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'result':r,
     'python':sys.version,'platform':platform.platform(),'cpu_affinity':list(os.sched_getaffinity(0))}
Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ('result','python','platform','cpu_affinity')}),flush=True)
