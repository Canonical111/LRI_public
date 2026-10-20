import subprocess,os,sys,json,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
root=Path(__file__).resolve().parent.parent;script=root/'engine/check_Z6_direct.py';logs=root/'direct_Z6_d';logs.mkdir(exist_ok=True)
env=dict(os.environ,OPENBLAS_NUM_THREADS='1')
subprocess.run([sys.executable,str(script),'--sources'],stdout=open(logs/'sources.log','w'),stderr=subprocess.STDOUT,check=True,env=env)
names=[a['id'] for a in json.loads((logs/'manifest.json').read_text())]
def run(name):
 with (logs/f'{name}.log').open('w') as f:
  st=time.time();p=subprocess.run([sys.executable,str(script),'--block',name],stdout=f,stderr=subprocess.STDOUT,env=env)
 return name,p.returncode,time.time()-st
with ThreadPoolExecutor(max_workers=1) as pool:
 for f in as_completed([pool.submit(run,name) for name in names]):print(f.result(),flush=True)
