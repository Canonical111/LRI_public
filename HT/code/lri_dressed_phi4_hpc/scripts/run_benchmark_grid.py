from pathlib import Path
import subprocess,sys,os
root=Path(__file__).resolve().parents[1]
env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMBA_NUM_THREADS='4')
for N,z,o in [(12,20,160),(16,24,192)]:
 for impl,threads in [('reference',1),('tensor',1),('tensor',2),('tensor',4),('ladder',1),('ladder',4)]:
  for rep in range(3):
   out=root/f'benchmarks/runs/N{N}_{impl}_t{threads}_r{rep}.json'
   if out.exists():continue
   cmd=[sys.executable,str(root/'scripts/bench_once.py'),'--impl',impl,'--threads',str(threads),'--N',str(N),'--nz',str(z),'--osc',str(o),'--seed',str(root/f'inputs/N{N}_z{z}_o{o}_d0.10000000.json'),'--out',str(out)]
   subprocess.run(cmd,env=env,check=True,timeout=240)
