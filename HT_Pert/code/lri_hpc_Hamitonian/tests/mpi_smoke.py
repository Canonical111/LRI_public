#!/usr/bin/env python3
"""Run with 1,2,4 actual MPI ranks BEFORE production.

mpiexec -n 2 python tests/mpi_smoke.py
No local serial rerun is duplicated per rank. Rank zero compares with the
bundled original implementation while other ranks wait. Nonzero failure exit.
"""
import os,sys
from pathlib import Path
for k in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS','NUMBA_NUM_THREADS']:os.environ[k]='1'
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'reference')]
from mpi4py import MPI
import numpy as np
from lri_hpc.solver import compute
comm=MPI.COMM_WORLD
try:
 for task,degree in [('thermal',7),('phi6',5)]:
  result=compute(8,task,degree,comm=comm)
  if comm.rank==0:
   if task=='thermal':
    from check_lri_C7 import compute as original
    ref=original(8,validate=True)
   else:
    from compute_phi6 import compute as original
    ref=original(8,validate=True,degree=5)
   for p in ([None] if task=='thermal' else ['raw','vacuum_subtracted']):
    x=result[p] if p else result;y=ref[p] if p else ref
    for k in ['C','r','g']+(['D6'] if task=='phi6' else []):np.testing.assert_allclose(x[k],y[k],rtol=2e-11,atol=1e-7)
   print(f'PASS actual MPI ranks={comm.size} task={task}',flush=True)
  comm.Barrier()
except BaseException:
 import traceback;traceback.print_exc();comm.Abort(1)
