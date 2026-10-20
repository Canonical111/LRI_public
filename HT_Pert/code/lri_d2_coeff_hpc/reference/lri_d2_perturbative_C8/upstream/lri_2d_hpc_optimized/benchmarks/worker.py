"""One isolated benchmark process; JSON includes exact settings and numerical data."""
import argparse,cProfile,pstats,json,time,resource,sys,platform
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--implementation',choices=['original','optimized'],required=True)
p.add_argument('--task',choices=['solve','operator','basis'],required=True);p.add_argument('--L',type=int,default=10)
p.add_argument('--x',type=float,default=.25);p.add_argument('--nz',type=int,default=16)
p.add_argument('--backend',choices=['tensor','ladder','gram','auto'],default='auto');p.add_argument('--threads',type=int,default=1)
p.add_argument('--repeat',type=int,default=5);p.add_argument('--output',type=Path,required=True);p.add_argument('--profile',action='store_true')
a=p.parse_args();ROOT=Path(__file__).resolve().parents[1]
src=ROOT/'code' if a.implementation=='optimized' else ROOT/'reference'/'code';sys.path.insert(0,str(src))
import numpy as np,scipy,numba
from numba import set_num_threads
from ht2d.basis import CircleBathBasis,dimension
from ht2d.operators import ProductOperator
from ht2d.solver import DressedSolver
from ht2d.density import DensitySolver
set_num_threads(a.threads)
actual_backend=a.backend
if actual_backend=='auto':
 actual_backend=('tensor' if a.L<=12 else 'ladder') if a.implementation=='original' else ('tensor' if a.L<=12 else 'gram')
res={'implementation':a.implementation,'task':a.task,'L':a.L,'x':a.x,'nz':a.nz,'backend':actual_backend,'threads':a.threads,
 'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'numba':numba.__version__,'platform':platform.platform(),'sparse_parallel_min_work':__import__('os').environ.get('HT2D_SPARSE_PARALLEL_MIN_WORK','250000'),
 'source_files':{str(p.relative_to(src)):__import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in sorted((src/'ht2d').glob('*.py'))}}
# Warm the same array/dtype signatures before starting performance measurements.
warm=DressedSolver(4,a.nz,192,window='vacuum',backend=actual_backend,eig_tol=1e-12,residual_tol=1e-8,ncv=40)
warm.set_delta(a.x);theta=warm.initial(2-4*a.x)
w,loc,_,_=warm.local_problem.evaluate(a.x,theta)
v=np.random.default_rng(29).normal(size=warm.op.dim)
for f in (0,1):
 warm.op.apply(v,w,loc,f);warm.op.apply_block(np.stack([v,v],axis=1),w,loc,f)
warm.spectrum(theta,k=3,diagnostics=True)
pr=cProfile.Profile();start=time.perf_counter()
if a.profile:pr.enable()
if a.task=='basis':
 b=CircleBathBasis.build(a.L,max_states=3_000_000)
 res.update(full_dimension=len(b.N),numeric_array_bytes=b.nbytes)
elif a.task=='operator':
 b=CircleBathBasis.build(a.L,max_states=3_000_000);bt=time.perf_counter()
 op=ProductOperator(b,a.x,a.nz,0,actual_backend);ot=time.perf_counter()
 v=np.random.default_rng(29).normal(size=op.dim)
 y=op.apply(v,w,loc,0)
 samples=[]
 for _ in range(a.repeat):
  t=time.perf_counter()
  for _ in range(15):y=op.apply(v,w,loc,0)
  samples.append((time.perf_counter()-t)/15)
 res.update(basis_seconds=bt-start,operator_setup_seconds=ot-bt,matvec_seconds=samples,
   full_dimension=len(b.N),scalar_bath_dimension=op.nB,operator_storage_bytes=op.nbytes,
   checksum=[float(y.sum()),float(y@y),float(y.min()),float(y.max())])
else:
 teacher=ROOT/'reference'/'results'/f'teacher_L6_x{a.x:.3f}.json'
 d=json.loads(teacher.read_text());B=d['basis_artifact'];u=np.array(B['isometry']);z=u.shape[1]//2
 u=u[:,list(range(a.nz))+list(range(z,z+a.nz))]
 s=DensitySolver(a.L,u,B['scale'],window='vacuum',backend=actual_backend,eig_tol=1e-12,residual_tol=1e-8,ncv=40)
 s.set_delta(a.x);r=s.solve(d['theta'],tol=3e-11,maxiter=50)
 res['result']=r;res['operators']=[{'L':op.basis.cutoff,'matvecs':op.matvec_count,'matvec_seconds':op.matvec_seconds,
   'operator_bytes':op.nbytes} for op in [*s.win.ops.values(),s.op]]
if a.profile:pr.disable()
res['elapsed_seconds']=time.perf_counter()-start
res['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
res['scope']='Finite implementation benchmark; setup included, imports and warmup excluded. No continuum accuracy claim.'
a.output.parent.mkdir(exist_ok=True,parents=True);a.output.write_text(json.dumps(res,indent=2)+'\n')
if a.profile:
 with a.output.with_suffix('.profile.txt').open('w') as f:pstats.Stats(pr,stream=f).sort_stats('cumulative').print_stats(55)
print(a.implementation,a.task,a.L,actual_backend,a.threads,res['elapsed_seconds'],res.get('result',{}).get('Delta_thermal'),flush=True)
