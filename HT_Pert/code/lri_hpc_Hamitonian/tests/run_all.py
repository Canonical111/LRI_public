#!/usr/bin/env python3
"""Portable regression suite; actual MPI smoke tests are run separately."""
import os,sys,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
for name in ['test_ranking.py','test_operators.py','test_solver.py','test_full_recursion.py','test_restart.py','test_distributed_simulated.py','test_int64.py','test_validate.py','test_campaign.py','test_lane_claims.py','test_extended_merge.py']:
 print('RUN',name,flush=True)
 env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMBA_NUM_THREADS='4',OMP_NUM_THREADS='1')
 subprocess.run([sys.executable,str(root/name)],env=env,check=True)
print('PASS all local tests. Real MPI performance/ABI remain untested until mpi_smoke.py is run.',flush=True)
