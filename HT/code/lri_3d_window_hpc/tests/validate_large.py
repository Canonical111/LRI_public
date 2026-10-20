"""Independent latest-reference operators and fully retuned angular spectra."""
from pathlib import Path
import os,sys,json,importlib.util,time
R=Path(__file__).resolve().parents[1]
for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):os.environ[key]='1'
os.environ.setdefault('NUMBA_NUM_THREADS','4');sys.path.insert(0,str(R/'code'))
import numpy as np
from threadpoolctl import threadpool_limits
from numba import set_num_threads
spec=importlib.util.spec_from_file_location('baseline_ht3d',R/'reference/baseline/code/ht3d/__init__.py',submodule_search_locations=[str(R/'reference/baseline/code/ht3d')])
m=importlib.util.module_from_spec(spec);sys.modules['baseline_ht3d']=m;spec.loader.exec_module(m)
from baseline_ht3d.basis import SphereBathBasis as RefBasis
from baseline_ht3d.operators import ProductOperator as RefOp
from baseline_ht3d.density import DensitySolver as RefSolver
from baseline_ht3d.diagnostics import diagnose as ref_diag
from ht3d.basis import SphereBathBasis
from ht3d.operators import ProductOperator
from ht3d.local import LocalProblem
from ht3d.density import DensitySolver
from ht3d.diagnostics import diagnose
records=[];spectra=[];t=time.perf_counter()
with threadpool_limits(limits=1,user_api='blas'):
 set_num_threads(1)
 for L,J in [(10,3),(12,0),(12,1),(12,2),(14,0)]:
  print('action check',L,J,flush=True);set_num_threads(1)
  b=SphereBathBasis.build(L);br=RefBasis.build(L)
  p=ProductOperator(b,.6,16,J);r=RefOp(br,.6,16,J)
  pd=(p.S-r.S).data
  assert np.max(abs(pd),initial=0)<1e-12
  w,V,_,_=LocalProblem(16,128).evaluate(.6,[.3,-2.15])
  for f in (0,1):
   v=np.random.default_rng(500+f).normal(size=p.dim)
   set_num_threads(1);a=p.apply(v,w,V,f);c=r.apply(v,w,V,f)
   err=float(np.max(abs(a-c)));rel=float(np.linalg.norm(a-c)/np.linalg.norm(c))
   set_num_threads(4);aa=p.apply(v,w,V,f);th=float(np.max(abs(aa-a)))
   assert err<2e-9 and rel<1e-12 and th<2e-9
   records.append(dict(L=L,J=J,field=f,dimension=p.dim,maximum_abs=err,relative_norm=rel,thread_difference=th))
  del p,r,b,br
 set_num_threads(1)
 for x in [.6,.5182]:
  print('retuned diagnostic replay',x,flush=True)
  td=json.loads((R/f'reference/baseline/results/curve/teacher_L6_x{x:g}.json').read_text());art=td['basis_artifact'];u=np.asarray(art['isometry']);cap=u.shape[1]//2;u=u[:,[*range(16),*range(cap,cap+16)]]
  out=[]
  for cls,diag in [(RefSolver,ref_diag),(DensitySolver,diagnose)]:
   s=cls(8,u,art['scale'],window='vacuum',backend='tensor',eig_tol=1e-12,ncv=40,residual_tol=1e-8)
   s.set_delta(x);row=s.solve(np.asarray(td['theta']),tol=3e-11,maxiter=50)
   d=diag(s,row['theta'],k=6,second=True)
   out.append({'scalar':row,'diagnostics':d})
  # Store full outputs to preserve candidate labels and ambiguity information.
  a,c=[np.r_[o['scalar']['even_gaps'],o['scalar']['odd_gaps']] for o in out]
  assert np.max(abs(a-c))<1e-9
  angular_max=0.
  for J,fields in out[0]['diagnostics']['angular_spectra'].items():
   for field,values in fields.items():
    aa=np.asarray(values);bb=np.asarray(out[1]['diagnostics']['angular_spectra'][J][field])
    angular_max=max(angular_max,float(np.max(abs(aa-bb))))
  assert angular_max<2e-9
  spectra.append({'x':x,'L':8,'scalar_max_abs':float(np.max(abs(a-c))),'angular_max_abs':angular_max,'baseline':out[0],'optimized':out[1]})
result={'passed':True,'action_checks':records,'spectral_replays':spectra,'elapsed_seconds':time.perf_counter()-t}
(R/'validation/large_independent_checks.json').write_text(json.dumps(result,indent=2,allow_nan=False))
print(json.dumps({'passed':True,'actions':len(records),'maximum_action_abs':max(r['maximum_abs'] for r in records),'maximum_action_relative':max(r['relative_norm'] for r in records),'maximum_scalar_gap_difference':max(r['scalar_max_abs'] for r in spectra),'seconds':result['elapsed_seconds']}))
