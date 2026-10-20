from pathlib import Path
import sys,json,hashlib,time,subprocess
from fractions import Fraction as F
sys.path.insert(0,'/mnt/data/P8_final_run');import period_algebra as pa
R=Path('/mnt/data/P8_final_run/F3_six_kink_completion');a=R/'F4_A9'
while len(list((a/'terminal_fibration/terminal').glob('b*.report.json')))<64:time.sleep(2)
subprocess.run(['python','-u','/mnt/data/P8_final_run/finalize_terminal_target.py',str(a),'A9_log','-1'],check=True)
subs={'A9_log':(a/'A9_log.expr',1),'Z8_log':(R/'F4_Z8/Z8_log.expr',-1),'EA7_finite':(R/'F4_EA7/EA7_full.expr',2),'EZ6_finite':(R/'F4_EZ6/EZ6_full.expr',-2),'J9_lower_shift':(R/'F4_data/J9_lower_shift.expr',1)}
out={};records=[]
for name,(p,mu) in subs.items():
 pol=pa.parse_expr(p.read_text());pa.add(out,pol,F(mu));records.append({'name':name,'weight':mu,'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'rational_projection':str(pol.get((),F(0))),'terms':len(pol)})
assert out.get(())==F(-10192,3),out.get(())
fp=R/'F4_data/J9.expr';fp.write_text(pa.dump(out));(R/'F4_data/J9_assembly.json').write_text(json.dumps({'complete':True,'terms':len(out),'rational_projection':str(out.get(())),'inputs':records,'output_sha256':hashlib.sha256(fp.read_bytes()).hexdigest(),'no_guessed_coefficient_used':True},indent=2))
manifest={name:str(p) for name,(p,_) in subs.items()};manifest['J9']=str(fp);manifest['B_old_full']=str(R/'C8_assembly/B_old_full.expr');(R/'F4_data/full_manifest.json').write_text(json.dumps(manifest,indent=2));print('J9_COMPLETE',len(out),out.get(()),flush=True)
