from pathlib import Path
import json,subprocess,sys,concurrent.futures,time,os
r=Path(__file__).resolve().parent.parent
# Wait only for already-running source stages within this computation.
while not all((r/f'B6_vd_f{f}'/j['block']/'stage2.jsonl').exists() for f in range(1,4) for j in json.loads((r/f'B6_vd_f{f}'/'manifest.json').read_text())['blocks']):time.sleep(2)
inputs=[{'path':f'B6_vd_f{f}/{j["block"]}/stage2.jsonl','weight':2 if f<3 else 1} for f in range(1,4) for j in json.loads((r/f'B6_vd_f{f}'/'manifest.json').read_text())['blocks']]
spec=r/'weighted_spec.json';spec.write_text(json.dumps({'inputs':inputs},indent=2));folder=r/'weighted_s2';folder.mkdir(exist_ok=True)
env=dict(os.environ,OPENBLAS_NUM_THREADS='1',R6_NATIVE='1',R6_ACCEL='1',R6_LINEAR='1',R6_MOD='1')
if not (folder/'partition.json').exists():subprocess.run([sys.executable,'-u','bucket_source_sum.py','split',str(spec),str(folder),'32'],cwd=r/'engine',env=env,check=True)
def run(i):
 with (r/'logs'/f'weighted_b{i:03}.log').open('a') as log:
  if not (folder/f'bucket{i:03}.report.json').exists():subprocess.run([sys.executable,'-u','bucket_source_sum.py','reduce',str(folder),str(i)],cwd=r/'engine',env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run([sys.executable,'-u','finish_mixed_bucket.py',str(i)],cwd=r/'engine',env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 return i
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 fs=[pool.submit(run,i) for i in range(32)]
 for f in concurrent.futures.as_completed(fs):print('COMPLETE_BUCKET',f.result(),flush=True)
print('ALL_32_COMPLETE',flush=True)
