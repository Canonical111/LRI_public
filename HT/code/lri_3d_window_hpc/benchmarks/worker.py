"""Fresh-process benchmarks; same physical problem and numerical tolerances."""
from pathlib import Path
import argparse,os,sys,time,json,resource,hashlib,platform,cProfile,pstats,io
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--impl',choices=['baseline','optimized'],required=True)
p.add_argument('--task',choices=['solve','operator','setup'],default='solve')
p.add_argument('--L',type=int,default=10);p.add_argument('--x',type=float,default=.6)
p.add_argument('--J',type=int,default=0);p.add_argument('--threads',type=int,default=1)
p.add_argument('--profile',action='store_true');p.add_argument('--cache-dir',type=Path)
p.add_argument('--output',type=Path,required=True);a=p.parse_args()
for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS','BLIS_NUM_THREADS'):os.environ[key]='1'
os.environ['NUMBA_NUM_THREADS']='4'
BASE=ROOT/'reference/baseline'
code=BASE/'code' if a.impl=='baseline' else ROOT/'code'
sys.path.insert(0,str(code))
import numpy as np,scipy,numba
from threadpoolctl import threadpool_limits,threadpool_info
pool=threadpool_limits(limits=1,user_api='blas');numba.set_num_threads(a.threads)
from ht3d.basis import SphereBathBasis
from ht3d.operators import ProductOperator
from ht3d.solver import DressedSolver
from ht3d.density import DensitySolver
from ht3d.local import LocalProblem
from ht3d import kernels as k

def warm():
    # Compile serial/parallel, vector/multi-vector paths outside timed interval.
    s=DressedSolver(4,6,48,window='vacuum',backend='tensor',eig_tol=1e-12,ncv=40,residual_tol=1e-8)
    s.set_delta(.6);s.spectrum([.2,-2.2],k=3,diagnostics=True)
    w,V,_,_=s.local_problem.evaluate(.6,[.2,-2.2]);X=np.ones((s.op.nB,6));s.op.apply(X.ravel(),w,V,0)
    ys=s.op.bath_powers(X)
    k.combine_serial(*ys,V,w,s.op.hbk,s.op.kpar,0,X)
    k.combine_parallel(*ys,V,w,s.op.hbk,s.op.kpar,0,X)
    if hasattr(k,'pack_local'):
        k.combine_contiguous_parallel(*ys,k.pack_local(V,6),V[3,0,0],w,s.op.hbk,s.op.kpar,0,X)
    for W in s.op.W:k.csr_batch(W.indptr,W.indices,W.data,X)

warm()
def file_hash(p):return hashlib.sha256(p.read_bytes()).hexdigest()
meta={'implementation':a.impl,'task':a.task,'L':a.L,'x':a.x,'J':a.J,'nz_per_parity':16,
      'threads':a.threads,'cache_dir':str(a.cache_dir) if a.cache_dir else None,
      'runtime':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'numba':numba.__version__,
      'blas':threadpool_info(),'affinity':sorted(os.sched_getaffinity(0)),'cpu_max':Path('/sys/fs/cgroup/cpu.max').read_text().strip()},
      'source_sha256':{str(f.relative_to(code)):file_hash(f) for f in sorted(code.rglob('*.py'))},
      'timing_scope':'fresh process; warmed JIT excluded; no fits or precision changes',
      'timestamp_unix':time.time()}
prof=cProfile.Profile();begin=time.perf_counter()
if a.profile:prof.enable()
if a.task=='solve':
    teacher=BASE/f'results/curve/teacher_L6_x{a.x:g}.json'
    td=json.loads(teacher.read_text());art=td['basis_artifact'];u=np.asarray(art['isometry']);cap=u.shape[1]//2
    u=u[:,[*range(16),*range(cap,cap+16)]]
    prev=BASE/f'results/curve/window_L{max(8,a.L-2)}_x{a.x:g}.json'
    guess=np.asarray(json.loads(prev.read_text())['theta'])+np.array([.0001,-.0001])
    kw=dict(window='vacuum',backend='tensor',eig_tol=1e-12,ncv=40,residual_tol=1e-8)
    if a.cache_dir:
        if a.impl!='optimized':raise ValueError('Cache belongs to optimized implementation')
        kw['cache_dir']=a.cache_dir
    # Input parsing is recorded separately; timed solve begins with local/bath construction.
    begin=time.perf_counter()
    s=DensitySolver(a.L,u,art['scale'],**kw);s.set_delta(a.x)
    setup=time.perf_counter()-begin
    row=s.solve(guess,tol=3e-11,maxiter=50)
    total=time.perf_counter()-begin
    meta.update(setup_seconds=setup,total_seconds=total,solve=row,
        seed=guess.tolist(),teacher_sha256=file_hash(teacher),seed_file_sha256=file_hash(prev),
        static_array_bytes=s.op.nbytes+(s.win.nbytes if s.win else 0))
else:
    kw={} if not a.cache_dir else {'cache_dir':a.cache_dir}
    b=SphereBathBasis.build(a.L,**kw);t1=time.perf_counter()
    b.highest_weight(a.J,a.J%2);t2=time.perf_counter()
    op=ProductOperator(b,a.x,16,a.J,'tensor');t3=time.perf_counter()
    meta.update(basis_seconds=t1-begin,projector_seconds=t2-t1,vertex_seconds=t3-t2,
        setup_seconds=t3-begin,full_bath_states=len(b.N),sector_bath_states=op.nB,
        sector_dimension=op.dim,static_array_bytes=op.nbytes,nnz=[W.nnz for W in op.W])
    if a.task=='operator':
        w,V,_,_=LocalProblem(16,128).evaluate(a.x,[.3,-2.15])
        v=np.random.default_rng(105).normal(size=op.dim);op.apply(v,w,V,0)
        trials=[]
        for i in range(7):
            t=time.perf_counter()
            for j in range(15):out=op.apply(v,w,V,0)
            trials.append((time.perf_counter()-t)/15)
        meta.update(apply_seconds=trials,median_apply_seconds=float(np.median(trials)),
                    norm=float(np.linalg.norm(out)),sample=out[:32].tolist())
        meta['timing_scope']+='; seven batches of 15 operator actions'
if a.profile:
    prof.disable();stream=io.StringIO()
    pstats.Stats(prof,stream=stream).strip_dirs().sort_stats('cumulative').print_stats(90)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.with_suffix('.profile.txt').write_text(stream.getvalue())
    # Portable text profiles are kept; interpreter-specific binary profiles are unnecessary.
    meta['profile_file']=a.output.with_suffix('.profile.txt').name
meta['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
if a.impl=='optimized':
    from ht3d.cache import COUNTERS
    meta['cache_counters']=dict(COUNTERS)
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(json.dumps(meta,indent=2,allow_nan=False))
print(a.impl,a.task,a.L,a.x,a.J,a.threads,meta.get('total_seconds',meta.get('setup_seconds')),meta.get('median_apply_seconds'),flush=True)
