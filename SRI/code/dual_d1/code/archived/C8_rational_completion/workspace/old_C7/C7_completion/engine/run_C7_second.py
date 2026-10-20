"""Independent numerical validation. The higher-precision run uses no
candidate. Recognition reads ONLY the first result and is fixed before
comparing with the second result. Runs may execute concurrently.
"""
from pathlib import Path
import subprocess,sys,time,json
ROOT=Path(__file__).resolve().parent
cmd=[sys.executable,'evaluate_final_decimal.py','--label','C7_second','--dps','115','--radius','140','--taylor','320','--asymptotic','170','--step','.30','C7','D4_value','Omega','C7_without_Omega','D4_without_Omega','alpha','beta','gamma','Phi','Psi','Qnew','Pnew','Knew']
start=time.time();print('COMMAND',' '.join(cmd),flush=True);p=subprocess.Popen(cmd,cwd=ROOT)
while not (ROOT/'final_evaluation_C7_first.json').exists():
 if p.poll() not in (None,0):raise SystemExit(p.returncode)
 time.sleep(4)
print('RECOGNITION USES FIRST RESULT ONLY',flush=True)
r=subprocess.run([sys.executable,'recognize_C7.py'],cwd=ROOT);assert r.returncode==0
recognition_time=time.time();ret=p.wait();assert ret==0,ret
q=subprocess.run([sys.executable,'check_eigenvalue_limit.py'],cwd=ROOT)
(ROOT/'C7_second_commands.json').write_text(json.dumps({'numerical_command':cmd,'numerical_returncode':ret,'recognition_source':'final_evaluation_C7_first.json only','candidate_used_by_evaluator':False,'candidate_fixed_before_second_comparison':True,'eigenvalue_check_returncode':q.returncode,'seconds':time.time()-start},indent=2))
assert q.returncode==0
print('SECOND ASSEMBLY AND DIRECT EIGENVALUE CHECK COMPLETE',flush=True)
