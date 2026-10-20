from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import subprocess,os,json,time
root=Path('/mnt/data/P8_final_run/F3_six_kink_completion');logs=root/'P8_collapse_logs';logs.mkdir(exist_ok=True)
env=os.environ.copy();env['OPENBLAS_NUM_THREADS']='1'
def run(i):
 with (logs/f'b{i:03d}.log').open('w') as f:
  p=subprocess.run(['python','-u',str(root/'engine/collapse_fixed_bucket.py'),str(i)],cwd=root/'engine',env=env,stdout=f,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError((i,p.returncode))
 return json.loads((root/'P8_fixed4'/f'b{i:03d}.report.json').read_text())
st=time.time()
with ThreadPoolExecutor(max_workers=3) as ex:
 fs=[ex.submit(run,i) for i in range(256)]
 for f in as_completed(fs):
  r=f.result();print('COMPLETE',r['bucket'],r['input_rows'],r['output_rows'],'elapsed',time.time()-st,flush=True)
