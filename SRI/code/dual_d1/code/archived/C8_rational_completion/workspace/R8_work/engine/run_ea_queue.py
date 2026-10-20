from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import subprocess,os,sys,json,time
n=int(sys.argv[1]);jobs=int(sys.argv[2]) if len(sys.argv)>2 else 1
root=Path(__file__).resolve().parent.parent;out=root/'endpoint_odd';logs=root/'endpoint_logs';logs.mkdir(exist_ok=True)
script=root/'engine/endpoint_odd.py';env=dict(os.environ,OPENBLAS_NUM_THREADS='1')
with (logs/f'EA{n}_source.log').open('w') as f:subprocess.run([sys.executable,str(script),'--n',str(n),'--sources'],stdout=f,stderr=subprocess.STDOUT,check=True,env=env)
names=[a['id'] for a in json.loads((out/f'EA{n}_manifest.json').read_text())['blocks']]
def run(name):
 with (logs/f'{name}.log').open('w') as f:
  start=time.time();r=subprocess.run([sys.executable,str(script),'--block',name],stdout=f,stderr=subprocess.STDOUT,env=env)
 return name,r.returncode,time.time()-start
with ThreadPoolExecutor(max_workers=jobs) as pool:
 for f in as_completed([pool.submit(run,name) for name in names]):print(f.result(),flush=True)
assert all((out/name/'result.json').exists() for name in names)
print('EA_ALL_DONE',n,flush=True)
