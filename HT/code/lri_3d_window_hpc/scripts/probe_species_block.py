#!/usr/bin/env python3
"""Replay a real largest species J+ block without allocating the full Fock graph.

--force-fallback is an explicit fault-injection test, NOT a production solver
setting. This verifies the retry using a real physical matrix but does not claim
that gesdd naturally failed on this runtime or that a full L18/L20 setup ran.
"""
from pathlib import Path
import argparse,json,os,sys,time,resource
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--L',type=int,required=True)
p.add_argument('--spin',type=int,default=0)
p.add_argument('--block-rank',type=int,default=0)
p.add_argument('--force-fallback',action='store_true')
p.add_argument('--assemble-only',action='store_true',help='Sparse assembly and exact character moments only; no dense SVD')
p.add_argument('--memory-limit-gib',type=float,default=2.)
p.add_argument('--blas-threads',type=int,default=1)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
for k in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS','BLIS_NUM_THREADS'):
    os.environ[k]=str(a.blas_threads)
sys.path.insert(0,str(ROOT/'code'))
import numpy as np,scipy
from threadpoolctl import threadpool_limits,threadpool_info
from unittest.mock import patch
from contextlib import nullcontext
from ht3d.projector_preflight import census,species_jplus,symmetric_character
from ht3d import basis
from ht3d.hpc import atomic_json,source_hash
if a.blas_threads<1 or a.memory_limit_gib<=0 or a.block_rank<0:raise ValueError('Invalid limits')
if a.assemble_only and a.force_fallback:raise ValueError('Assembly-only cannot test an SVD fallback')
r={'purpose':'isolated physical J+ block; no full Fock graph or spectrum',
   'L':a.L,'spin':a.spin,'block_rank':a.block_rank,'fault_injection':a.force_fallback,
   'assemble_only':a.assemble_only,'source_sha256':source_hash(),'runtime':{'numpy':np.__version__,'scipy':scipy.__version__,
   'blas':threadpool_info()},'status':'started','passed':False}
atomic_json(a.output,r)
t=time.perf_counter()
try:
 with threadpool_limits(limits=a.blas_threads,user_api='blas'):
    d=census(a.L,spins=(a.spin,),largest=a.block_rank+1)
    rec=d['sectors'][str(a.spin)]['largest_blocks'][a.block_rank]
    nt,ns=rec['targets'],rec['sources']
    # Conservative planning allowance, not a certified LAPACK bound: full input,
    # input copy, full U/V, extra SVD temporaries and a 256MiB process allowance.
    estimate=8*(2*nt*ns+nt*nt+ns*ns+4*min(nt,ns)**2)+256*2**20
    r.update(block=rec,memory_estimate_bytes=estimate)
    atomic_json(a.output,r)
    if not a.assemble_only and estimate>a.memory_limit_gib*2**30:
        raise MemoryError(f'Isolated dense SVD estimate {estimate/2**30:.3f} GiB exceeds budget')
    A,src,dst=species_jplus(rec['species'],a.spin)
    assert A.shape==(nt,ns)
    r.update(sparse_nnz=int(A.nnz),assembly_seconds=time.perf_counter()-t)
    atomic_json(a.output,r)
    if a.assemble_only:
        chars=np.array([1],np.int64)
        for n,l,q in rec['species']:chars=np.convolve(chars,symmetric_character(l,q))
        mid=len(chars)//2
        expected=[]
        for power in (1,2):
            val=0
            for j in range(a.spin+1,mid+1):
                multiplicity=int(chars[mid+j])-(int(chars[mid+j+1]) if j<mid else 0)
                val+=multiplicity*(j*(j+1)-a.spin*(a.spin+1))**power
            expected.append(val)
        gram=A@A.T
        measured=[float(A.data@A.data),float(gram.data@gram.data)]
        relative=[abs(v-w)/max(1,abs(w)) for v,w in zip(measured,expected)]
        assert max(relative)<2e-13
        r.update(status='complete_assembly_only',passed=True,
                 character_moment_expected=expected,character_moment_measured=measured,
                 maximum_moment_relative_error=max(relative),
                 scope='Sparse physical block and character moments checked; NO SVD or projector computed')
    else:
        stats=basis._new_projector_stats(a.spin,a.spin%2)
        with (patch.object(basis,'null_space',side_effect=np.linalg.LinAlgError('INJECTED gesdd failure for retry validation'))
              if a.force_fallback else nullcontext()):
            Q=basis._highest_weight_kernel(A.toarray(),dict(L=a.L,spin=a.spin,
                                          inversion=a.spin%2,species=rec['species']),stats)
        # Sparse action is independent of the helper's dense residual calculation.
        res=float(np.max(abs(A@Q),initial=0.))
        orth=float(np.max(abs(Q.T@Q-np.eye(Q.shape[1])),initial=0.))
        assert Q.shape[1]==rec['nullity'] and max(res,orth)<=1e-10
        r.update(status='complete',passed=True,Jplus_residual=res,orthogonality=orth,
                 actual_nullity=Q.shape[1],svd_statistics=stats)
except Exception as exc:
    r.update(status='failed',error=f'{type(exc).__name__}: {exc}')
    raise
finally:
    r.update(elapsed_seconds=time.perf_counter()-t,
             peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    atomic_json(a.output,r)
    print(json.dumps(r,sort_keys=True,allow_nan=False),flush=True)
