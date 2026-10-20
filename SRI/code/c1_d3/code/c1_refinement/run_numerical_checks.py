#!/usr/bin/env python3
"""Recompute descendant, tail-quadrature, angular-exponent and LP checks."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json,numpy as np
from scipy.optimize import linprog
from crossing_envelope import BASE,Envelope
from angular_tail import moment_bound

def main():
 out={}
 for a,b in [(32,40),(40,48)]:
  x=np.load(BASE/f'basis_L{a}.npz');y=np.load(BASE/f'basis_L{b}.npz')
  out[f'descendant{a}_{b}']={k:float(np.max(abs(x[k]-y[k]))) for k in ['d0','J','pad']}
 env=Envelope(8,7,40);lp=np.load(BASE/'final_8_7_pad1_lp.npz')
 for k in ['A','B','Beven','Bodd']:setattr(env,k,lp[k])
 out['tail_quadrature']=[dict(nodes=n,values=env.integral(n).tolist()) for n in [80,140,220]]
 for n,j,step in [(100,64,.1),(160,96,.05)]:out[f'angular{n}']=moment_bound(env,n=n,J=j,step=step)['best_upper']
 out['angular_upper_change']=out['angular160']['odd_integral_upper']-out['angular100']['odd_integral_upper']
 (BASE/'final_numerical_checks.json').write_text(json.dumps(out,indent=2)+'\n')
 checks=[]
 for sign in [1,-1]:
  c=sign*env.obj;r=linprog(c,A_ub=env.A,b_ub=env.B,bounds=env.bnds,method='highs',options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
  if not r.success:raise RuntimeError(r.message)
  lo=np.array([x[0] for x in env.bnds]);hi=np.array([x[1] for x in env.bnds]);dual=float(env.B@r.ineqlin.marginals+lo@r.lower.marginals+hi@r.upper.marginals)
  checks.append(dict(objective_sign=sign,primal_value=float(r.fun),dual_value=dual,primal_dual_gap=abs(float(r.fun)-dual),max_constraint_violation=float(max(0,np.max(env.A@r.x-env.B)))))
 (BASE/'lp_optimality_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
 print('numerical checks saved',out['descendant40_48'],checks)
if __name__=='__main__':main()
