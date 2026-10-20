#!/usr/bin/env python3
"""Allocation-free counts by default; explicit --execute runs staged setup only.

No eigensolve, coupling retuning, or physical spectrum is run here. One output and
JSONL path per process; use separate Slurm jobs/resources for each L and spin.
"""
from pathlib import Path
import argparse,json,os,sys,time,resource,traceback
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--L',type=int,required=True)
p.add_argument('--x',type=float,default=.6)
p.add_argument('--spins',nargs='+',type=int,default=[0,1,2])
p.add_argument('--nz',type=int,default=16)
p.add_argument('--execute',action='store_true',help='Allocate the graph and requested setup stages')
p.add_argument('--stop-after',choices=['graph','projector','vertices'],default='vertices')
p.add_argument('--max-bath-states',type=int,default=2_000_000)
p.add_argument('--memory-limit-gib',type=float,default=8.)
p.add_argument('--max-basis-gib',type=float,help='Default memory-limit-gib/4, matching production driver')
p.add_argument('--threads',type=int,default=1)
p.add_argument('--cache-dir',type=Path)
p.add_argument('--dump-dir',type=Path,help='Replay matrices if both SVD drivers fail')
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
if a.threads<1 or not 0<a.memory_limit_gib or a.nz<1:raise ValueError('Invalid resources')
if a.max_basis_gib is not None and not 0<a.max_basis_gib<=a.memory_limit_gib:
    raise ValueError('max-basis-gib must be positive and no greater than memory-limit-gib')
for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS','BLIS_NUM_THREADS'):
    os.environ[key]='1'
os.environ.setdefault('NUMBA_NUM_THREADS',str(a.threads))
sys.path.insert(0,str(ROOT/'code'))
import numpy as np,scipy,numba
from threadpoolctl import threadpool_limits,threadpool_info
from ht3d.projector_preflight import census
from ht3d.basis import SphereBathBasis
from ht3d.operators import ProductOperator
from ht3d.hpc import atomic_json,source_hash
from ht3d.cache import COUNTERS
numba.set_num_threads(a.threads)
if a.output.exists():raise FileExistsError('Use a fresh probe output, not an old result path')
a.output.parent.mkdir(parents=True,exist_ok=True)
log=Path(str(a.output)+'.projector.jsonl')
with log.open('x'):pass
os.environ['HT3D_PROJECTOR_LOG']=str(log)
if a.dump_dir:os.environ['HT3D_PROJECTOR_DUMP_DIR']=str(a.dump_dir)
report={'schema':'ht3d-setup-probe-v1','status':'started','passed':False,
        'configuration':{k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()},
        'source_sha256':source_hash(),'runtime':{'numpy':np.__version__,'scipy':scipy.__version__,
        'numba':numba.__version__,'python':sys.version,'blas':threadpool_info()},'stages':[],
        'scope':'setup only; passed does not imply an eigensolve or cluster deployment'}
atomic_json(a.output,report)
t0=time.perf_counter()
def mark(stage,status,**details):
    rss=None
    try:
        for line in Path('/proc/self/status').read_text().splitlines():
            if line.startswith('VmRSS:'):rss=int(line.split()[1]);break
    except OSError:pass
    report['stages'].append(dict(stage=stage,status=status,elapsed_seconds=time.perf_counter()-t0,
        current_rss_kib=rss,process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,**details))
    atomic_json(a.output,report)
    print(json.dumps(report['stages'][-1],sort_keys=True,allow_nan=False),flush=True)
try:
 with threadpool_limits(limits=1,user_api='blas'):
    report['preflight']=census(a.L,spins=a.spins,nz=a.nz)
    mark('preflight','complete')
    if a.execute:
        if not .5<a.x<.75:raise ValueError('Require 1/2<x<3/4')
        graph_budget=int((a.max_basis_gib if a.max_basis_gib is not None else a.memory_limit_gib/4)*2**30)
        mark('graph','started',max_array_bytes=graph_budget)
        b=SphereBathBasis.build(a.L,max_states=a.max_bath_states,max_bytes=graph_budget,cache_dir=a.cache_dir)
        assert len(b.N)==report['preflight']['graph']['states']
        assert len(b.parents)==report['preflight']['graph']['edges']
        assert b.nbytes==report['preflight']['graph']['graph_array_bytes']
        mark('graph','complete',states=len(b.N),edges=len(b.parents),array_bytes=b.nbytes,
             arrays={k:{'dtype':getattr(b,k).dtype.str,'bytes':getattr(b,k).nbytes} for k in
                     ('N','P','M','ptr','parents','modes','sqocc','tree','last','counts','mode_levels')})
        if a.stop_after!='graph':
            for J in a.spins:
                mark('projector','started',spin=J)
                S,N,P,keep,meta=b.highest_weight(J,J%2)
                expected=report['preflight']['sectors'][str(J)]['highest_weights']
                if S.shape[1]!=expected:raise AssertionError('Complete character/projector dimension mismatch')
                mark('projector','complete',spin=J,sector_bath_states=S.shape[1],nnz=int(S.nnz),
                     pointer_dtype=S.indptr.dtype.str,index_dtype=S.indices.dtype.str,
                     projection_tests=meta)
                if a.stop_after=='vertices':
                    mark('vertices','started',spin=J)
                    op=ProductOperator(b,a.x,a.nz,J,'tensor')
                    mark('vertices','complete',spin=J,dimension_per_field_parity=op.dim,
                         operator_array_bytes=op.nbytes,vertices=[dict(shape=list(v.shape),nnz=int(v.nnz),
                         pointer_dtype=v.indptr.dtype.str,index_dtype=v.indices.dtype.str,
                         bytes=v.data.nbytes+v.indices.nbytes+v.indptr.nbytes) for v in op.W])
                    del op
                del S,N,P,keep
                b._projectors.clear()
        report['status']='complete_setup'
    else:report['status']='complete_preflight_only'
    report['passed']=True
except Exception as exc:
    report.update(status='failed',error=f'{type(exc).__name__}: {exc}',traceback=traceback.format_exc())
    raise
finally:
    report['static_cache_counters']=dict(COUNTERS)
    report['elapsed_total_seconds']=time.perf_counter()-t0
    report['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    atomic_json(a.output,report)
