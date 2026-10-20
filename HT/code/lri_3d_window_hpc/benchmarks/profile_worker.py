"""Reproducible baseline/new complete scalar workflow profile (no physics change)."""
from pathlib import Path
import sys,os,argparse,time,cProfile,pstats,io,json,resource
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--impl',choices=['baseline','optimized'],default='baseline');p.add_argument('--L',type=int,default=10);p.add_argument('--x',type=float,default=.6);p.add_argument('--threads',type=int,default=1);p.add_argument('--profile',action='store_true');p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
for k in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):os.environ[k]='1'
os.environ['NUMBA_NUM_THREADS']=str(max(a.threads,4))
base=R/'reference/baseline';code=base/'code' if a.impl=='baseline' else R/'code'
sys.path.insert(0,str(code))
import numpy as np
from numba import set_num_threads
set_num_threads(a.threads)
from threadpoolctl import threadpool_limits,threadpool_info
_pool=threadpool_limits(limits=1,user_api='blas')
from ht3d.density import DensitySolver
from ht3d.solver import DressedSolver
s0=DressedSolver(4,6,48,window='vacuum',backend='tensor',eig_tol=1e-12,ncv=40,residual_tol=1e-8)
s0.set_delta(.6);s0.spectrum([.2,-2.2],k=3,diagnostics=True)
w0,V0,_,_=s0.local_problem.evaluate(.6,[.2,-2.2]);s0.op.apply(np.ones(s0.op.dim),w0,V0,0)
td=json.loads((base/f'results/curve/teacher_L6_x{a.x:g}.json').read_text())
art=td['basis_artifact'];u=np.array(art['isometry']);cap=u.shape[1]//2;nz=16
u=u[:,[*range(nz),*range(cap,cap+nz)]]
seedpath=base/f'results/curve/window_L{max(8,a.L-2)}_x{a.x:g}.json'
seed=json.loads(seedpath.read_text())['theta']
seed=np.array(seed)+np.array([.0001,-.0001])
pr=cProfile.Profile();t=time.perf_counter()
print('START',a.impl,a.L,a.x,threadpool_info(),flush=True)
if a.profile:pr.enable()
s=DensitySolver(a.L,u,art['scale'],window='vacuum',backend='tensor',eig_tol=1e-12,ncv=40,residual_tol=1e-8)
s.set_delta(a.x);t_setup=time.perf_counter()-t
print('SETUP',t_setup,flush=True)
s.checkpoint=lambda theta,history:print('NEWTON',history[-1]['iteration'],history[-1]['residual'],time.perf_counter()-t,flush=True)
row=s.solve(seed,tol=3e-11,maxiter=50)
total=time.perf_counter()-t
if a.profile:pr.disable()
r={'implementation':a.impl,'L':a.L,'x':a.x,'threads':a.threads,'setup_seconds':t_setup,'total_seconds':total,'solve':row,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
a.output.parent.mkdir(parents=True,exist_ok=True)
if a.profile:
 stream=io.StringIO();pstats.Stats(pr,stream=stream).strip_dirs().sort_stats('cumulative').print_stats(70)
 a.output.with_suffix('.profile.txt').write_text(stream.getvalue());pr.dump_stats(str(a.output.with_suffix('.pstats')))
 r['profile']=stream.getvalue()
a.output.write_text(json.dumps(r,indent=2));print(a.impl,a.L,a.x,'setup',t_setup,'total',total,'gap',row['Delta_thermal'],flush=True)
