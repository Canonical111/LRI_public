from pathlib import Path
import json,subprocess,sys,os,concurrent.futures
ROOT=Path(__file__).resolve().parent.parent
m=json.loads((ROOT/'XE_terminal/manifest.json').read_text())
def work(r):
 p=ROOT/'XE_terminal'/r['block'];env=os.environ.copy();env['OPENBLAS_NUM_THREADS']='1'
 with (ROOT/'logs'/f'XE_growth_stage_{r["block"]}.log').open('a') as log:
  subprocess.run([sys.executable,'-u',str(ROOT/'engine/endpoint_projected_stage.py'),str(p)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 return r['block']
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for f in concurrent.futures.as_completed([pool.submit(work,r) for r in m['blocks']]):print('GROWTH_SOURCE_COMPLETE',f.result(),flush=True)
print('ALL_GROWTH_SOURCES_COMPLETE',flush=True)
