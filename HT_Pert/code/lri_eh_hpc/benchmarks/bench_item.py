#!/usr/bin/env python3
"""Fresh-process comparison; warm compilation before timed solver work."""
import argparse,json,os,sys,time,resource,cProfile,pstats
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--backend',choices=['old','new'],required=True);ap.add_argument('--cutoff',type=int,required=True)
ap.add_argument('--degree',type=int,default=7);ap.add_argument('--threads',type=int,default=4);ap.add_argument('--output',type=Path,required=True)
ap.add_argument('--profile',action='store_true');ap.add_argument('--memory-limit-gib',type=float,default=3.9);a=ap.parse_args()
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1';os.environ['NUMBA_NUM_THREADS']=str(a.threads)
sys.path.insert(0,str(ROOT))
if a.backend=='old':
 sys.path.insert(0,str(ROOT/'reference/original/code'));from run_correction_only import correction as run
else:
 from lri_eh.numerics import compute as run
from numba import set_num_threads
from lri_eh.runtime import environment,fingerprint,atomic_json
set_num_threads(a.threads)
t=time.perf_counter();run(4,a.degree,a.memory_limit_gib);warm=time.perf_counter()-t
pr=cProfile.Profile();t=time.perf_counter()
if a.profile:pr.enable()
r=run(a.cutoff,a.degree,a.memory_limit_gib)
if a.profile:
 pr.disable();a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.with_suffix('.profile.txt').open('w') as f:pstats.Stats(pr,stream=f).sort_stats('cumtime').print_stats(40)
r.update(wall_seconds=time.perf_counter()-t,warmup_seconds=warm,peakrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
         backend=a.backend,threads=a.threads,environment=environment(),optimized_source_sha256=fingerprint(),
         timing_scope='Independent process; numerical work after cutoff-4 warmup. Peak RSS includes runtime/JIT.')
atomic_json(a.output,r)
print(json.dumps(dict(backend=a.backend,degree=a.degree,cutoff=a.cutoff,threads=a.threads,wall=r['wall_seconds'],rss=r['peakrss_kib'])))
