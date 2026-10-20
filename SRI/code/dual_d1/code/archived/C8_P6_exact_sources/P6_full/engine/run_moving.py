from pathlib import Path
import json,subprocess,sys,concurrent.futures,os
r=Path(__file__).resolve().parent.parent
env=dict(os.environ,OPENBLAS_NUM_THREADS='1',R6_NATIVE='1',R6_ACCEL='1',R6_LINEAR='1',R6_MOD='1')
def run(i):
 folder=r/'weighted_s2'
 with (r/'logs'/f'moving_b{i:03}.log').open('w') as fp:
  if not (folder/f'bucket{i:03}.report.json').exists():subprocess.run([sys.executable,'-u','bucket_source_sum.py','reduce',str(folder),str(i)],cwd=r/'engine',env=env,stdout=fp,stderr=subprocess.STDOUT,check=True)
  subprocess.run([sys.executable,'-u','make_moving_bucket.py',str(i)],cwd=r/'engine',env=env,stdout=fp,stderr=subprocess.STDOUT,check=True)
 return i
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 fs=[pool.submit(run,i) for i in range(32)]
 for f in concurrent.futures.as_completed(fs):print('MOVING_COMPLETE',f.result(),flush=True)
print('ALL_MOVING_COMPLETE',flush=True)
