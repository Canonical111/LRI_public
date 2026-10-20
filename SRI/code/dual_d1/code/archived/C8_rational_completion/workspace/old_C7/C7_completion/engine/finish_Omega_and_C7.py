"""Run the remaining exact and numerical assembly after the checked raw
seven-kink charge derivative has been written. No extrapolation is used.
"""
from pathlib import Path
import subprocess,sys,time,json
ROOT=Path(__file__).resolve().parent
while not (ROOT/'A7_v_audit.json').exists():time.sleep(3)
commands=[
 [sys.executable,'assemble_C7.py','Omega'],
 [sys.executable,'assemble_C7_invariants.py'],
 [sys.executable,'evaluate_final_decimal.py','--label','C7_first','--dps','95','--radius','110','--taylor','280','--asymptotic','140','--step','.35','C7','D4_value','Omega','C7_without_Omega','D4_without_Omega','alpha','beta','gamma','Phi','Psi','Qnew','Pnew','Knew'],
]
log=[]
for cmd in commands:
 print('COMMAND',' '.join(cmd),flush=True);st=time.time()
 p=subprocess.run(cmd,cwd=ROOT);log.append({'command':cmd,'returncode':p.returncode,'seconds':time.time()-st})
 (ROOT/'C7_completion_commands.json').write_text(json.dumps(log,indent=2))
 if p.returncode:raise SystemExit(p.returncode)
print('NUMERICAL ASSEMBLY COMPLETED',flush=True)
