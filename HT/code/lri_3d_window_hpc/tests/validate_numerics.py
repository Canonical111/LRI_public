"""Larger tensor/Gram/original actions and weak-coupling spectral controls."""
import sys,json,importlib.util
from pathlib import Path
import numpy as np
from numba import set_num_threads
from threadpoolctl import threadpool_limits
_pool=threadpool_limits(limits=1,user_api='blas')
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'code'),str(R/'reference/d3original/code'),str(R/'tests')]
from ht3d.basis import SphereBathBasis
from ht3d.operators import ProductOperator
from ht3d.local import LocalProblem
from ht3d.solver import DressedSolver
from d3dressed.basis import SphereBathBasis as OB
from d3dressed.operators import ProductOperator as OP
from second_order_oracle import C2
res={};maxrel=0.;maxabs=0.;thread=0.
for L,J in [(8,1),(10,0),(12,0)]:
 print('original/Gram/action',L,J,flush=True)
 b=SphereBathBasis.build(L);a=ProductOperator(b,.6,8,J,'tensor');g=ProductOperator(b,.6,8,J,'gram');o=OP(OB.build(L),.6,8,J)
 w,V,_,_=LocalProblem(8,96).evaluate(.6,[.3,-2.15])
 # These highest-weight nullspace gauges coincide; verify rather than assume.
 diff=(a.S-o.S).data;assert np.max(abs(diff),initial=0)<1e-12
 for f in [0,1]:
  v=np.random.default_rng(808+f).normal(size=a.dim)
  set_num_threads(1);aa=a.apply(v,w,V,f);gg=g.apply(v,w,V,f);oo=o.apply(v,w,V,f)
  for v1 in [gg,oo]:maxabs=max(maxabs,float(np.max(abs(aa-v1))));maxrel=max(maxrel,float(np.linalg.norm(aa-v1)/np.linalg.norm(aa)))
  set_num_threads(4);ab=a.apply(v,w,V,f);gb=g.apply(v,w,V,f);thread=max(thread,float(np.max(abs(aa-ab))),float(np.max(abs(gg-gb))))
set_num_threads(1)
weak=[]
for eps in [.04,.02,.01]:
 print('weak check',eps,flush=True)
 x=(3-eps)/4;values={}
 for mode in ['none','vacuum']:
  s=DressedSolver(6,20,160,window=mode,eig_tol=1e-12,residual_tol=1e-8,ncv=40);s.set_delta(x)
  d=s.solve(tol=3e-11);values[mode]=d['Delta_thermal']
 weak.append(dict(epsilon=eps,**values,window_minus_raw=values['vacuum']-values['none'],quadratic_remainder=values['none']-(1.5-eps/6+C2(6)*eps**2)))
assert maxrel<3e-13 and maxabs<1e-9 and thread<1e-9
ratios=[weak[i]['window_minus_raw']/weak[i+1]['window_minus_raw'] for i in range(2)]
assert all(10<r<24 for r in ratios)
res.update(larger_action_max_abs=maxabs,larger_action_max_relative=maxrel,one_four_thread_max_abs=thread,weak_controls=weak,window_difference_halving_ratios=ratios,passed=True)
(R/'validation/numerical_checks.json').write_text(json.dumps(res,indent=2));print(res)
