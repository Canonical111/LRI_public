#!/usr/bin/env python3
import argparse,json,os,sys,time,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--backend',choices=['dense','matrixfree'],required=True)
ap.add_argument('--low',type=int,default=8);ap.add_argument('--parent',type=int,default=16);ap.add_argument('--output',type=Path,required=True)
a=ap.parse_args();os.environ['NUMBA_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
sys.path.insert(0,str(ROOT))
from numba import set_num_threads
set_num_threads(4)
if a.backend=='dense':
 sys.path.insert(0,str(ROOT/'reference/original/code'));from finite_shell_match import compare
else:from lri_eh.finite_shell import compare
from lri_eh.runtime import atomic_json,environment,fingerprint
compare(2,4,7)
t=time.perf_counter();r=compare(a.low,a.parent,7);wall=time.perf_counter()-t
r.update(backend=a.backend,wall_seconds=wall,peakrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,environment=environment(),source_sha256=fingerprint())
atomic_json(a.output,r);print(a.backend,a.low,a.parent,wall,r['peakrss_kib'])
