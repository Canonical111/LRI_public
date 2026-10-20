from pathlib import Path
from fractions import Fraction as F
import concurrent.futures,subprocess,json,time,os,sys,hashlib
r=Path(__file__).resolve().parent.parent;folder=r/'terminal'
while not (folder/'prefactor_apart_report.json').exists():time.sleep(3)
# Delay to avoid oversubscribing the final scalar queue.
while not all((folder/'terminal'/f'b{i:03}.report.json').exists() for i in range(64)):time.sleep(3)
env=dict(os.environ,OPENBLAS_NUM_THREADS='1')
def run(job):
 p,i=job
 with (r/'logs'/f'control_p{p}_b{i:03}.log').open('w') as fp:
  subprocess.run([sys.executable,'-u','evaluate_terminal_control.py',str(folder),str(i),'5','0','1',str(p)],cwd=r/'engine',env=env,stdout=fp,stderr=subprocess.STDOUT,check=True)
 return job
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for x in pool.map(run,[(p,i) for p in (-2,-1) for i in range(64)]):print('CTRL_BUCKET',x,flush=True)
sys.path.insert(0,str(r.parent/'C8_full_numerical_completion/code'));import period_algebra as pa
manifest={}
for p in (-2,-1):
 poly={}
 for i in range(64):
  for line in (folder/f'terminal_p{p}'/f'b{i:03}.jsonl').open():
   w,ll,zm,c=json.loads(line);v=pa.R(tuple(map(F,w)))
   for k in ll:v=pa.mul(v,pa.log(k))
   mon=tuple((z,k) for z,k in zip(['Z2','Z3','Z5','Z7'],zm) if k)
   if mon:v=pa.mul(v,{mon:F(1)})
   pa.add(poly,v,F(c))
 assert poly.get(())==F(18 if p==-2 else 1638),(p,poly.get(()))
 dest=r/'control'/f'B_p{p}_actual.expr';dest.write_text(pa.dump(poly));manifest[f'actual_p{p}']=str(dest)
 pred=pa.parse_expr((r/'control'/f'B_p{p}_predicted.expr').read_text());diff=poly.copy();pa.add(diff,pred,-1)
 dest=r/'control'/f'B_p{p}_difference.expr';dest.write_text(pa.dump(diff));manifest[f'diff_p{p}']=str(dest)
 print('CONTROL_EXPRESSION',p,len(poly),len(diff),flush=True)
(r/'control/completed_manifest.json').write_text(json.dumps(manifest,indent=2))
