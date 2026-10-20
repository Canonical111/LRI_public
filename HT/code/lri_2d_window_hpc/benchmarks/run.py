"""Serial alternating independent-process benchmarks. Nothing is submitted to Slurm."""
import os,subprocess,sys,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--quick',action='store_true');p.add_argument('--group',choices=['solve','operator','basis','all'],default='all');a=p.parse_args()
ROOT=Path(__file__).resolve().parents[1];dest=ROOT/'results'/'benchmarks';dest.mkdir(exist_ok=True,parents=True)
env={**os.environ,'OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OMP_NUM_THREADS':'1','NUMBA_NUM_THREADS':'4'}
calls=[]
if a.group in ('solve','all'):
 for L,x in ([(10,.25)] if a.quick else [(10,.25),(12,.25),(10,.126)]):
  for rep in range(1 if a.quick else 3):
   for impl in (['original','optimized'] if rep%2==0 else ['optimized','original']):
    calls.append((f'solve_L{L}_x{x}_{impl}_{rep}', ['--task','solve','--L',str(L),'--x',str(x),'--implementation',impl]))
if a.group in ('operator','all'):
 for L in ([12] if a.quick else [12,14,16]):
  for threads in ([1] if a.quick else [1,2,4]):
   for impl,backend in [('original','tensor'),('original','ladder'),('optimized','tensor'),('optimized','gram')]:
    calls.append((f'op_L{L}_t{threads}_{impl}_{backend}', ['--task','operator','--L',str(L),'--threads',str(threads),'--implementation',impl,'--backend',backend]))
if a.group in ('basis','all'):
 for L in ([12] if a.quick else [12,16,18,20]):
  for impl in ('original','optimized'):
   calls.append((f'basis_L{L}_{impl}', ['--task','basis','--L',str(L),'--implementation',impl]))
for name,args in calls:
 out=dest/(name+'.json')
 if out.exists():continue
 with out.with_suffix('.log').open('w') as f:
  subprocess.run([sys.executable,str(ROOT/'benchmarks/worker.py'),*args,'--output',str(out)],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 print(name,flush=True)
