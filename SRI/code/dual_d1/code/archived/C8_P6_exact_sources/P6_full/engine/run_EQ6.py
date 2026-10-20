import concurrent.futures,subprocess,sys,json,os
from pathlib import Path
root=Path(__file__).resolve().parent.parent
manifest=json.loads((root/'EQ6_v/manifest.json').read_text())
def run(rec):
 name=rec['block'];env=os.environ.copy();env['OPENBLAS_NUM_THREADS']='1'
 with (root/'logs'/f'EQ6_v_{name}.log').open('a') as f:
  subprocess.run([sys.executable,'-u',str(root/'engine/full_runner.py'),'--tag','EQ6_v','--block',name],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 return name
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for name in pool.map(run,manifest['blocks']):print('BLOCK_COMPLETE',name,flush=True)
