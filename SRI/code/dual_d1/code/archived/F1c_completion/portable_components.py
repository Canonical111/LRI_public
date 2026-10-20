import subprocess,sys
from pathlib import Path
p=Path(__file__).resolve().parent
for cmd in [('assemble_F1c.py',),('check_Leibniz.py',),('check_full_derivative.py',),('check_two_kink.py',),('extract_finite_exact.py','Q4_vvd','EQ4_vd')]:
 print('RUN',cmd,flush=True);subprocess.run([sys.executable,'-u',*cmd],cwd=p/'engine',check=True)
print('PORTABLE_COMPONENT_CHECKS_PASS',flush=True)
