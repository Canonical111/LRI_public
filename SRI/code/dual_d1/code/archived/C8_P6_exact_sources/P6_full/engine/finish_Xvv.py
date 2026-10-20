from pathlib import Path
import json,time,subprocess,sys,os
ROOT=Path(__file__).resolve().parent.parent
mm=json.loads((ROOT/'Q6_vv/manifest.json').read_text())
while not all((ROOT/'Q6_vv'/r['block']/'result.json').is_file() for r in mm['blocks']):time.sleep(2)
subprocess.run([sys.executable,str(ROOT/'engine/assemble_new_finite.py'),'Xvv'],check=True)
manifest=ROOT/'data/Xvv_evaluation_manifest.json'
manifest.write_text(json.dumps({'Xvv':str(ROOT/'data/Xvv.expr'),'F3_lower_shift':str(ROOT/'inherited/F3_lower_shift.expr')},indent=2))
env=os.environ.copy();env['OMP_NUM_THREADS']='1';env['OPENBLAS_NUM_THREADS']='1'
for label,dps,R,nt,na,step in [('first60',60,90,210,130,'.3'),('second90',90,130,280,175,'.25')]:
 cmd=[sys.executable,str(ROOT/'numerical/evaluate_set.py'),'--manifest',str(manifest),'--out',str(ROOT/'data'/f'Xvv_{label}.json'),'--dps',str(dps),'--radius',str(R),'--taylor',str(nt),'--asymptotic',str(na),'--step',step,'--backend','gmp']
 with (ROOT/'logs'/f'Xvv_{label}.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,check=True)
 print('EVALUATED',label,flush=True)
with (ROOT/'logs/Xvv_finite_check.log').open('w') as f:
 subprocess.run([sys.executable,str(ROOT/'numerical/check_complete_finite.py'),'Xvv'],stdout=f,stderr=subprocess.STDOUT,env=env,check=True)
print('XVV_FULL_CHECKS_FINISHED',flush=True)
