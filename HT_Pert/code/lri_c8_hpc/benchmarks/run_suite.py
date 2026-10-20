#!/usr/bin/env python3
"""Serial independent subprocesses; never benchmark competing solvers concurrently."""
from pathlib import Path
import argparse,os,sys,subprocess,itertools
ROOT=Path(__file__).resolve().parents[1]
# benchmarks/results/ holds the bundled, manifest-listed measurements; fresh runs go
# elsewhere so existing files are never mistaken for a new measurement.
ap=argparse.ArgumentParser();ap.add_argument('--output-dir',type=Path,default=ROOT/'validation/benchmarks')
dest=ap.parse_args().output_dir;dest.mkdir(parents=True,exist_ok=True)
# Paired comparisons and memory/speed tradeoffs. Set OMP/BLAS to one; Numba team
# is selected explicitly by bench_item. Compilation is warmed and excluded.
env={**os.environ,'OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OMP_NUM_THREADS':'1','NUMBA_NUM_THREADS':'4'}
cases=[(40,4,'raw','stored'),(50,4,'raw','stored'),(40,1,'raw','stored'),(50,4,'vacuum_only','stored')]
for L,t,s,b in cases:
 for repeat in range(3):
  for solver in ('old','new') if repeat%2==0 else ('new','old'):
   out=dest/f'{solver}_L{L}_{s}_{b}_t{t}_{repeat}.json'
   if out.exists():continue
   subprocess.run([sys.executable,str(ROOT/'benchmarks/bench_item.py'),'--solver',solver,'--cutoff',str(L),'--threads',str(t),
    '--scheme',s,'--backend',b,'--output',str(out)],env=env,check=True)
for L,t in [(50,4),(50,1)]:
 for repeat in range(3):
  out=dest/f'new_L{L}_raw_ranked_t{t}_{repeat}.json'
  if out.exists():continue
  subprocess.run([sys.executable,str(ROOT/'benchmarks/bench_item.py'),'--solver','new','--cutoff',str(L),'--threads',str(t),
   '--backend','ranked','--output',str(out)],env=env,check=True)
