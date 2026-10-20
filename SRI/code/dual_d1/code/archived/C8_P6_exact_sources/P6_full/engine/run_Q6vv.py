import concurrent.futures,subprocess,sys,json,os
from pathlib import Path
root=Path(__file__).resolve().parent.parent
manifest=json.loads((root/'Q6_vv/manifest.json').read_text())
def run(rec):
 name=rec['block'];env=os.environ.copy();env['OPENBLAS_NUM_THREADS']='1'
 with (root/'logs'/f'Q6_vv_{name}.log').open('a') as f:
  subprocess.run([sys.executable,'-u',str(root/'engine/full_runner.py'),'--tag','Q6_vv','--block',name],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 return name
with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
 for name in pool.map(run,manifest['blocks']):print('BLOCK_COMPLETE',name,flush=True)
