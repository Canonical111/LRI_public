#!/usr/bin/env python3
"""Reassemble the saved-data analyses; does not rerun large Fock-space jobs."""
import os,sys,subprocess
from pathlib import Path
D=Path(__file__).resolve().parent
env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
for name in ['verify_boundary_identities.py','analyze_joint.py','fit_omega3.py','final_joint.py','stress_joint.py','combined_stress.py']:
    print('Running',name,flush=True)
    with (D/(name+'.log')).open('w') as f:
        subprocess.run([sys.executable,str(D/name)],cwd=D,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
print('See final_summary.json, stress_summary.json, and boundary_identity_checks.json.')
