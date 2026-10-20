"""Regenerate missing raw moments one job at a time; record explicit exits."""
from pathlib import Path
import subprocess,sys,re,json,time,os
ROOT=Path(__file__).resolve().parent;LOG=ROOT.parent/'logs'
req=json.loads((ROOT/'C7_raw_requirements.json').read_text())
selected=sys.argv[1:] or [x for x in req['missing'] if x not in ['A7_v','Q8_base']]
records=[]
for tag in selected:
 if (ROOT/(tag+'_negative.json')).exists():continue
 m=re.fullmatch(r'(EA|EQ|EZ|A|Q|Z)(\d+)_(\w+)',tag)
 assert m,tag
 kind,n,der=m.groups()
 start=time.time()
 print('START',tag,flush=True)
 with (LOG/(tag+'_fresh.log')).open('w') as f:
  cp=subprocess.run([sys.executable,'run_moment.py',n,kind,der],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
 rec={'tag':tag,'returncode':cp.returncode,'seconds':time.time()-start,'exists':(ROOT/(tag+'_negative.json')).is_file()}
 records.append(rec);(ROOT/'fresh_raw_job_status.json').write_text(json.dumps(records,indent=2))
 print('DONE',rec,flush=True)
 if cp.returncode:print('CONTINUING OTHER INDEPENDENT JOBS',flush=True)
