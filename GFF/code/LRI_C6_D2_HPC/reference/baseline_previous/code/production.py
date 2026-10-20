from pathlib import Path
import json,subprocess,sys,time
W=Path(__file__).resolve().parents[1]
plan=json.load(open(W/'inputs/production_plan.json'));done=[]
for row in plan:
 d=row['d'];L=row['L'];out=W/f'records/{row["tag"]}_d{d}_L{L}.json'
 if out.exists():
  print('already complete',row['tag'],d,L,flush=True);continue
 cmd=[sys.executable,str(W/'code/run_precision.py'),row['tag'],'--d',str(d),'--loops',str(L)]
 for k in ['seed','replicates','budget','bits','encoding','allocation','rate']:cmd+=['--'+k,str(row[k])]
 t=time.time();subprocess.run(cmd,check=True);done.append({**row,'seconds':time.time()-t})
 (W/'records/production_executed.json').write_text(json.dumps(done,indent=2))
