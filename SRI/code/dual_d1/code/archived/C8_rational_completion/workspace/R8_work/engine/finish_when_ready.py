from pathlib import Path
import json,time,subprocess,sys
root=Path(__file__).resolve().parent.parent;eng=root/'engine';start=time.time()
def ready():
 for k,n in [('A',9),('Z',8)]:
  p=root/'tail_blocks'/f'{k}_base'
  for f in range(1,n//2+1):
   q=p/f'n{n}_face{f}_manifest.json'
   if not q.exists():return False
   for b in json.loads(q.read_text())['blocks']:
    if not all((p/b['id']/x).exists() for x in ['result.json','full_boundary_jets.json']):return False
 for tag in ['EA5_d','EZ4_d','EZ6_base','EQ4_vd','Q4_vvd','Q6_vv','EQ6_v']:
  p=root/'finite_lower'/tag;q=p/'manifest.json'
  if not q.exists():return False
  for b in json.loads(q.read_text())['blocks']:
   if not (p/b['id']/'result.json').exists():return False
 return True
while not ready():
 if time.time()-start>7200:raise SystemExit('Complete inputs not obtained; no final result generated.')
 time.sleep(10)
print('ALL_MAIN_INPUTS_PRESENT',flush=True)
for name in ['check_lower_tables_stdlib.py','finalize_tail.py','finalize_ninth.py','assemble_C8_full_beta.py','verify_direct_Z6.py','check_trial_rational_parts.py']:
 p=subprocess.run([sys.executable,str(eng/name)],cwd=eng,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (root/(name.replace('.py','')+'_acceptance.log')).write_text(p.stdout)
 print(name,p.returncode,flush=True)
 if p.returncode:print(p.stdout,flush=True);raise SystemExit(p.returncode)
print((root/'Task_D_result.json').read_text(),flush=True)
print((root/'full_beta_C8_check.json').read_text(),flush=True)
