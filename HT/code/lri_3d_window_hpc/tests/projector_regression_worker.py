"""Separate-process graph/projector hashes against the pinned pre-fix code.

Failures are recorded; they are not counted as successful bitwise comparisons.
"""
from pathlib import Path
import argparse,os,sys,json,time,resource,hashlib,tempfile,traceback
_numba_cache=tempfile.TemporaryDirectory(prefix='ht3d-projector-regression-')
os.environ['NUMBA_CACHE_DIR']=_numba_cache.name
p=argparse.ArgumentParser();p.add_argument('--implementation',choices=['original','patched'],required=True)
p.add_argument('--L',type=int,required=True);p.add_argument('--spin',type=int,default=0)
p.add_argument('--output',type=Path,required=True);a=p.parse_args()
ROOT=Path(__file__).resolve().parents[1]
for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS','BLIS_NUM_THREADS'):os.environ[key]='1'
os.environ['NUMBA_NUM_THREADS']='4'
code=ROOT/'code' if a.implementation=='patched' else ROOT/'reference/performance_0_2_0/code'
sys.path.insert(0,str(code))
import numpy as np
from ht3d.basis import SphereBathBasis
from ht3d import basis as mod
from threadpoolctl import threadpool_limits

def ahash(x):
    h=hashlib.sha256();h.update(x.dtype.str.encode());h.update(repr(x.shape).encode())
    v=memoryview(np.ascontiguousarray(x)).cast('B')
    for i in range(0,len(v),4*2**20):h.update(v[i:i+4*2**20])
    return h.hexdigest()

out=dict(implementation=a.implementation,L=a.L,spin=a.spin,passed=False,status='started',
    source_file_sha256=hashlib.sha256((code/'ht3d/basis.py').read_bytes()).hexdigest(),
    scope='graph/projector only; no vertices/eigenvalues; timings single observations')
a.output.parent.mkdir(parents=True,exist_ok=True)
def save():a.output.write_text(json.dumps(out,indent=2,allow_nan=False))
save();start=time.perf_counter()
# Observes only a failed unmodified call; input and successful output unchanged.
old_null_space=mod.null_space

def observed(A,*args,**kwargs):
    try:return old_null_space(A,*args,**kwargs)
    except np.linalg.LinAlgError:
        out['svd_failure']={'shape':list(A.shape),'matrix_sha256':ahash(A)}
        raise
mod.null_space=observed
try:
 with threadpool_limits(limits=1,user_api='blas'):
    w=SphereBathBasis.build(4);w.highest_weight(a.spin,a.spin%2);del w
    start=time.perf_counter()
    b=SphereBathBasis.build(a.L,max_states=10_000_000,max_bytes=2*2**30)
    out.update(states=len(b.N),graph_seconds=time.perf_counter()-start,
        graph_hashes={name:ahash(getattr(b,name)) for name in
                      ('N','P','M','ptr','parents','modes','sqocc','tree','last','counts','mode_levels')})
    save();t=time.perf_counter()
    S,N,P,keep,meta=b.highest_weight(a.spin,a.spin%2)
    out.update(passed=True,status='complete',projector_seconds=time.perf_counter()-t,
        shape=list(S.shape),nnz=int(S.nnz),metadata=meta,
        hashes={name:ahash(x) for name,x in dict(data=S.data,indices=S.indices,indptr=S.indptr,N=N,P=P,keep=keep).items()})
except Exception as exc:
    out.update(status='failed',error=f'{type(exc).__name__}: {exc}',traceback=traceback.format_exc())
    raise
finally:
    out.update(peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               elapsed_seconds=time.perf_counter()-start)
    save()
    print(json.dumps({k:out[k] for k in ('implementation','L','spin','status','peak_rss_kib','elapsed_seconds')}))
