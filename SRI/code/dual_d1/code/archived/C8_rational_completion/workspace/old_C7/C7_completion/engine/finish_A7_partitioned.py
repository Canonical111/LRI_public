"""Partition one linear integration stage; combine exactly before continuing."""
from pathlib import Path
import json,subprocess,sys,os,time,hashlib
from hyperlog_core import K
ROOT=Path(__file__).resolve().parent;LOG=ROOT.parent/'logs'
rows=json.loads((ROOT/'A7_v_stage3.json').read_text());parts=2;children=[];records=[]
for i in range(parts):
 part=rows[i::parts];tag=f'A7_v_part{i}'
 p=ROOT/f'{tag}_stage3.json';p.write_text(json.dumps(part));f=(LOG/f'{tag}_stage4.log').open('w')
 proc=subprocess.Popen([sys.executable,'run_moment.py','7','A','v','--resume','3'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'LRI_TAG_SUFFIX':f'_part{i}','LRI_STOP_AFTER':'4','OPENBLAS_NUM_THREADS':'1'})
 children.append((i,proc,f));print('START',i,'pid',proc.pid,'rows',len(part),flush=True)
for i,p,f in children:
 rc=p.wait();f.close();assert rc==0,(i,rc)
 records.append({'part':i,'returncode':rc});print('COMPLETE PART',i,flush=True)
merged={};start=time.time()
for i in range(parts):
 p=ROOT/f'A7_v_part{i}_stage4.json';rr=json.loads(p.read_text())
 for j,(ww,logs,c) in enumerate(rr):
  key=tuple(tuple(w) for w in ww),tuple(logs)
  merged[key]=merged.get(key,K.zero)+K.from_expr(c)
  if j%500==0:print('merge',i,j,len(merged),time.time()-start,flush=True)
 merged={k:c for k,c in merged.items() if c}
 records[i]['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
rr=[([list(w) for w in ww],list(logs),str(c)) for (ww,logs),c in merged.items()]
(ROOT/'A7_v_stage4.json').write_text(json.dumps(rr));(ROOT/'A7_v_stage4_partition_audit.json').write_text(json.dumps({'input_partition':'even/odd row numbers of exact stage3 sum','records':records,'merged_rows':len(rr),'exact_arithmetic':True},indent=2))
print('STAGE4 MERGED',len(rr),flush=True)
if '--stop-after-four' in sys.argv: raise SystemExit(0)
with (LOG/'A7_v_global_finish.log').open('w') as f:
 subprocess.run([sys.executable,'run_moment.py','7','A','v','--resume','4'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
print('A7_v RAW COMPLETE',flush=True)
