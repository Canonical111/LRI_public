#!/usr/bin/env python3
import argparse,sys,json,resource
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ap=argparse.ArgumentParser(description='Matrix-free finite-parent matching oracle, NOT infinite-shell production')
ap.add_argument('--low',type=int,required=True);ap.add_argument('--parent',type=int,required=True);ap.add_argument('--degree',type=int,default=7)
ap.add_argument('--threads',type=int,default=4);ap.add_argument('--memory-limit-gib',type=float,required=True);ap.add_argument('--output',type=Path,required=True)
a=ap.parse_args()
from numba import set_num_threads
from lri_eh.finite_shell import compare
from lri_eh.runtime import claim,atomic_json,seal,fingerprint,environment
set_num_threads(a.threads)
with claim(a.output.with_suffix('.lock')):
 if a.output.exists():raise FileExistsError(a.output)
 r=compare(a.low,a.parent,a.degree,a.memory_limit_gib)
 r.update(source_sha256=fingerprint(),environment=environment(),peakrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
 atomic_json(a.output,seal(r));print(json.dumps(r))
