"""Independent normalization/rotation/C2 checks on the new sphere operators."""
from pathlib import Path
import sys,json,math,importlib.util
import numpy as np
from scipy.special import eval_gegenbauer,eval_legendre
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'code'),str(R/'reference/d3original/code')]
from ht3d.basis import SphereBathBasis
from ht3d.operators import ProductOperator
from ht3d.local import LocalProblem
from ht3d.diagnostics import zero_m_projector
from second_order_oracle import C2
spec=importlib.util.spec_from_file_location('original_validation',R/'reference/d3original/tests/validate.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
res={};cov=0.;coef=0.;rot=0.
for x in [.5182,.6,.749]:
 b=SphereBathBasis.build(8);u=b.weights(x)
 for k in range(9):
  for y in [-.77,-.1,.32,.9]:
   v=1. if k==0 else sum((2*l+1)*u[j]**2*eval_legendre(l,y) for j,(n,l,m) in enumerate(b.labels) if 2*n+l==k and m==0)
   cov=max(cov,abs(v-eval_gegenbauer(k,x,y)))
for L in [2,4,6,8,10]:
 b=SphereBathBasis.build(L);op=ProductOperator(b,.75,6);coef=max(coef,abs(old.direct_C2(op)-C2(L)))
for J in [1,2]:
 b=SphereBathBasis.build(4);op=ProductOperator(b,.6,6,J);S0=zero_m_projector(op)
 a=old.projected_vertices(b,op.S,.6,5);bb=old.projected_vertices(b,S0,.6,5)
 rot=max(rot,max(np.max(abs(aa-cc)) for aa,cc in zip(a,bb)))
x=.65;loc=LocalProblem(6,64);theta=np.array([1.2,-2.]);w,Lm,U,info=loc.evaluate(x,theta)
r,g,t=info['r'],info['g'],info['local_scale'];I=np.eye(64);q=[I]+[t**j*loc.q[j] for j in range(1,5)]
Q=[I,q[1],q[2]-I,q[3]-3*q[1],q[4]-6*q[2]+3*I]
H=x/4*(loc.pp/t**2+q[2]-2*I)+r*Q[2]+g*Q[4]/12
le=U.T@H@U;le-=np.eye(len(w))*le[0,0]
VV=np.array([U.T@a@U for a in [2*r*Q[1]+g*Q[3]/3,r*I+g*Q[2]/2,g*Q[1]/3,g*I/12]])
normal=max(np.max(abs(le-np.diag(w))),np.max(abs(VV-Lm)))
res.update(covariance_addition_max_abs=float(cov),C2_matrix_vs_exact_shell_max_abs=float(coef),rotational_M_equivalence_max_abs=float(rot),original_normal_ordering_max_abs=float(normal))
assert cov<1e-12 and coef<1e-12 and rot<1e-11 and normal<1e-10
res['passed']=True;(R/'validation/physics_checks.json').write_text(json.dumps(res,indent=2));print(res)
