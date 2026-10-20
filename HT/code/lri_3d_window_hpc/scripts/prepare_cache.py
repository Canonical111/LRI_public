#!/usr/bin/env python3
"""Build immutable bare graph/projector/vertex arrays, without solving a spectrum."""
from __future__ import annotations
import argparse,json,os,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--L',type=int,nargs='+',required=True)
p.add_argument('--x',type=float,nargs='+',required=True)
p.add_argument('--spins',type=int,nargs='+',default=[0,1,2])
p.add_argument('--cache-dir',type=Path,required=True)
p.add_argument('--threads',type=int,default=1)
p.add_argument('--max-bath-states',type=int,default=2_000_000)
p.add_argument('--max-basis-gib',type=float,default=2.)
p.add_argument('--output',type=Path)
a=p.parse_args()
if a.threads<1 or a.max_basis_gib<=0: p.error('Resource bounds must be positive')
if any(L<2 for L in a.L) or any(J<0 for J in a.spins):p.error('Require L>=2, J>=0')
if any(not .5<x<.75 for x in a.x):p.error('Require 1/2<x<3/4')
for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS','BLIS_NUM_THREADS'):os.environ[key]='1'
os.environ.setdefault('NUMBA_NUM_THREADS',str(a.threads));sys.path.insert(0,str(R/'code'))
import numba
from threadpoolctl import threadpool_limits
from ht3d.basis import SphereBathBasis
from ht3d.operators import ProductOperator
from ht3d.cache import COUNTERS,implementation
from ht3d.hpc import atomic_json
numba.set_num_threads(a.threads)
records=[]
with threadpool_limits(limits=1,user_api='blas'):
    for L in a.L:
        start=time.perf_counter()
        b=SphereBathBasis.build(L,max_states=a.max_bath_states,max_bytes=int(a.max_basis_gib*1024**3),cache_dir=a.cache_dir)
        for J in a.spins:
            # Empty angular sectors are invalid, not silently replaced by scalars.
            for x in a.x:
                t=time.perf_counter();op=ProductOperator(b,x,1,J,'tensor')
                rec={'L':L,'J':J,'x':x,'bath_states':len(b.N),'sector_states':op.nB,
                     'operator_array_bytes':op.nbytes,'seconds':time.perf_counter()-t}
                records.append(rec);print(json.dumps(rec),flush=True)
                del op
        del b
report={'purpose':'bare array cache only; no window, coupling, or energy solution',
        'implementation':implementation(),'cache_counters':dict(COUNTERS),'records':records}
if a.output:atomic_json(a.output,report)
