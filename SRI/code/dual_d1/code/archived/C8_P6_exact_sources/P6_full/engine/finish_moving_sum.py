from pathlib import Path
import json,subprocess,sys,os,time,hashlib,concurrent.futures
r=Path(__file__).resolve().parent.parent
env=dict(os.environ,OPENBLAS_NUM_THREADS='1',R6_NATIVE='1',R6_ACCEL='1',R6_LINEAR='1',R6_MOD='1')
while not all((r/'moving_s3'/f'b{i:03}.report.json').exists() for i in range(32)):time.sleep(2)
flat=r/'moving_flat';flat.mkdir(exist_ok=True);inputs=[]
for i in range(32):
 source=r/'moving_s3'/f'b{i:03}.jsonl';p=flat/source.name
 with p.open('w') as f:
  for line in source.open():
   w,tail,ll,c=json.loads(line);f.write(json.dumps([[w]+tail,ll,c],separators=(',',':'))+'\n')
 inputs.append({'path':str(p.relative_to(r)),'weight':1})
spec=r/'moving_sum_spec.json';spec.write_text(json.dumps({'inputs':inputs},indent=2));out=r/'moving_sum';out.mkdir(exist_ok=True)
if not (out/'partition.json').exists():subprocess.run([sys.executable,'-u','bucket_source_sum.py','split',str(spec),str(out),'32'],cwd=r/'engine',env=env,check=True)
def red(i):
 with (r/'logs'/f'moving_reduce_{i:03}.log').open('w') as fp:
  if not (out/f'bucket{i:03}.report.json').exists():subprocess.run([sys.executable,'-u','bucket_source_sum.py','reduce',str(out),str(i)],cwd=r/'engine',env=env,stdout=fp,stderr=subprocess.STDOUT,check=True)
 return i
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for i in pool.map(red,range(32)):print('MOVING_REDUCED',i,flush=True)
source=r/'moving_total.jsonl';n=0
with source.open('w') as f:
 for i in range(32):
  for line in (out/f'bucket{i:03}.jsonl').open():
   ww,ll,c=json.loads(line);w,*tail=ww;f.write(json.dumps([w,tail,ll,c],separators=(',',':'))+'\n');n+=1
print('TOTAL_MOVING_ROWS',n,flush=True)
terminal=r/'terminal';terminal.mkdir(exist_ok=True)
if not (terminal/'report.json').exists():subprocess.run([sys.executable,'-u','final_fibration.py',str(source),str(terminal),'64'],cwd=r/'engine',env=env,check=True)
subprocess.run([sys.executable,'-u','precompute_terminal_apart.py',str(terminal)],cwd=r/'engine',env=env,check=True)
def fin(i):
 with (r/'logs'/f'terminal_b{i:03}.log').open('w') as fp:
  subprocess.run([sys.executable,'-u','evaluate_terminal_bucket.py',str(terminal),str(i),'5','0','1'],cwd=r/'engine',env=env,stdout=fp,stderr=subprocess.STDOUT,check=True)
 return i
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for i in pool.map(fin,range(64)):print('FINAL_BUCKET',i,flush=True)
print('INTEGRATIONS_COMPLETE',flush=True)
