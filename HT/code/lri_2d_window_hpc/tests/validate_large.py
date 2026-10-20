"""Independent large-space actions and fresh all-sector spectral regression."""
from pathlib import Path
import sys,importlib.util,importlib,json,time,platform
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
import numpy as np
from numba import set_num_threads
from ht2d.basis import CircleBathBasis
from ht2d.operators import ProductOperator
from ht2d.solver import DressedSolver
from ht2d.density import DensitySolver
from ht2d.diagnostics import diagnose
spec=importlib.util.spec_from_file_location('original_ht2d',ROOT/'reference/code/ht2d/__init__.py',submodule_search_locations=[str(ROOT/'reference/code/ht2d')])
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
old=importlib.import_module('original_ht2d.operators')
results=[]
for L in [12,16]:
 b=CircleBathBasis.build(L)
 s=DressedSolver(L,16,192,basis=b);s.set_delta(.25);w,V,_,_=s.local_problem.evaluate(.25,s.initial(1.))
 for J in ([0,1,2] if L==12 else [0,1]):
  original=old.ProductOperator(b,.25,16,J,'tensor');opt=ProductOperator(b,.25,16,J,'gram')
  rng=np.random.default_rng(106+J);v=rng.normal(size=opt.dim)
  for f in [0,1]:
   set_num_threads(1);ref=original.apply(v,w,V,f);single=opt.apply(v,w,V,f)
   set_num_threads(4);parallel=opt.apply(v,w,V,f)
   err=float(np.max(abs(parallel-ref)));relative=float(np.linalg.norm(parallel-ref)/np.linalg.norm(ref))
   assert err<1e-9 and relative<3e-14
   assert np.max(abs(single-parallel))<1e-10
   results.append({'type':'operator','L':L,'J':J,'field':f,'size':opt.dim,'max_difference':err,'relative_norm_difference':relative,
                   'thread_difference':float(np.max(abs(single-parallel)))})
# Independent saved reference generated before this optimization. All diagnostic
# poles, not merely the tuned gaps, are compared; ambiguity flags stay explicit.
set_num_threads(1)
for x in [.3,.126]:
 d=json.loads((ROOT/'reference/results'/f'teacher_L6_x{x:.3f}.json').read_text());a=d['basis_artifact']
 u=np.array(a['isometry']);k=u.shape[1]//2;u=u[:,list(range(16))+list(range(k,k+16))]
 s=DensitySolver(8,u,a['scale'],window='vacuum',backend='gram',eig_tol=1e-12,residual_tol=1e-8,ncv=40);s.set_delta(x)
 row=s.solve(d['theta'],tol=3e-11,maxiter=50);diag=diagnose(s,row['theta'],k=6,second=True)
 ref=json.loads((ROOT/'reference/results'/f'window_L8_z16_x{x:.3f}.json').read_text())
 scalar=max(np.max(abs(np.array(row[key])-ref[key])) for key in ['even_gaps','odd_gaps'])
 angular=max(np.max(abs(np.array(vals)-ref['diagnostics']['angular_spectra'][J][f])) for J,data in diag['angular_spectra'].items() for f,vals in data.items())
 assert scalar<1e-9 and angular<2e-8
 results.append({'type':'spectrum','x':x,'L':8,'thermal_difference':abs(row['Delta_thermal']-ref['Delta_thermal']),
                 'max_scalar_difference':float(scalar),'max_angular_difference':float(angular),'diagnostics':diag,
                 'max_residual':row['max_eigenvector_residual']})
(ROOT/'validation/large_numerical_checks.json').write_text(json.dumps(results,indent=2)+'\n')
print('Large actions and independent full-spectrum comparisons passed',len(results))
