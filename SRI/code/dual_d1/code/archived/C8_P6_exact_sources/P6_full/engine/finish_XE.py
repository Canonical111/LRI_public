"""Accept only all 47 complete endpoint-growth blocks, then evaluate the full period expression."""
from pathlib import Path
import json,time,subprocess,sys,os,hashlib
ROOT=Path(__file__).resolve().parent.parent
m=json.loads((ROOT/'data/XE_final_plan.json').read_text())
while not all((ROOT/r/'growth_stage5_report.json').exists() for r in m['evaluation_folders']):time.sleep(3)
with (ROOT/'logs/XE_growth_sum.log').open('w') as f:subprocess.run([sys.executable,str(ROOT/'engine/sum_growth_sources.py')],stdout=f,stderr=subprocess.STDOUT,check=True)
print('ALL_GROWTH_SUMMED',flush=True)
subprocess.run([sys.executable,str(ROOT/'engine/check_XE_source_coverage.py')],check=True)
with (ROOT/'logs/XE_total_functional.log').open('w') as f:
 subprocess.run([sys.executable,str(ROOT/'engine/growth_linear_periods.py'),str(ROOT/'XE_growth_total')],stdout=f,stderr=subprocess.STDOUT,check=True)
record=json.loads((ROOT/'XE_growth_total/linear_growth_report.json').read_text());assert record['rational_projection']=='3729/2',record
out=ROOT/'data/XE.expr';out.write_bytes((ROOT/'XE_growth_total/linear_growth_finite.expr').read_bytes())
record['output_sha256']=hashlib.sha256(out.read_bytes()).hexdigest();record['original_47_source_chunks_covered']=True;record['retained_chunks']=27;record['jointly_integrated_remaining_chunks']=20
(ROOT/'data/XE_assembly.json').write_text(json.dumps(record,indent=2))
manifest=ROOT/'data/XE_evaluation_manifest.json';manifest.write_text(json.dumps({'XE':str(out),'Xvv':str(ROOT/'data/Xvv.expr'),'F3_lower_shift':str(ROOT/'inherited/F3_lower_shift.expr')},indent=2))
env=os.environ.copy();env['OMP_NUM_THREADS']='1';env['OPENBLAS_NUM_THREADS']='1'
for label,dps,R,nt,na,step in [('first60',60,90,210,130,'.3'),('second90',90,130,280,175,'.25')]:
 with (ROOT/'logs'/f'XE_{label}.log').open('w') as f:
  subprocess.run([sys.executable,str(ROOT/'numerical/evaluate_set.py'),'--manifest',str(manifest),'--out',str(ROOT/'data'/f'XE_{label}.json'),'--dps',str(dps),'--radius',str(R),'--taylor',str(nt),'--asymptotic',str(na),'--step',step,'--backend','gmp'],stdout=f,stderr=subprocess.STDOUT,check=True,env=env)
 print('XE_EVALUATED',label,flush=True)
print('XE_FULL_PERIOD_COMPLETE',flush=True)
