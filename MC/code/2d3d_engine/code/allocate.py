#!/usr/bin/env python3
"""Pilot-based optimal size-pair effort, for STATISTICAL error only.

Resample one size at a time, including refitted multi-temperature free energies
and crossing. Estimate A_L = Var_L(Delta_eff)*M_L and use Var ~= sum A_L/M_L.
Given compute-node costs c_L seconds/sweep, the unconstrained minimum-cost plan is
M_L = sum_j sqrt(A_j*c_j)/target^2 * sqrt(A_L/c_L).
This does not budget finite-size bias, unknown autocorrelation tails, or warm-up.
"""
from pathlib import Path
import argparse,json
import numpy as np
from precision_analysis import Group,crossing

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('index',type=Path)
 p.add_argument('--dim',type=int,required=True);p.add_argument('--s',type=float,required=True);p.add_argument('--nn-extra',type=float,default=0)
 p.add_argument('--L',type=int,required=True);p.add_argument('--target-stat',type=float,default=.001)
 p.add_argument('--seconds-per-sweep',type=float,nargs=2,required=True,metavar=('COST_L','COST_2L'))
 p.add_argument('--bootstrap',type=int,default=200);p.add_argument('--seed',type=int,default=794233)
 p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.target_stat<=0 or min(a.seconds_per_sweep)<=0:p.error('target and costs must be positive')
 mf=json.loads(a.index.read_text());ts=[t for t in mf['tasks'] if t['d']==a.dim and abs(t['s']-a.s)<1e-10 and abs(t.get('nn_extra',0)-a.nn_extra)<1e-12]
 gs=[Group([t for t in ts if t['L']==L],a.index.parent) for L in [a.L,2*a.L]]
 rng=np.random.default_rng(a.seed);vars=[];fail=[]
 for i in range(2):
  samples=[]
  for b in range(a.bootstrap):
   curves=[g.central for g in gs]
   try:curves[i]=gs[i].curve(rng);samples.append(crossing(*curves)[0][2])
   except (ValueError,np.linalg.LinAlgError):pass
  if len(samples)<max(50,.95*a.bootstrap):raise ValueError('too many failed bootstrap roots for reliable effort planning')
  vars.append(float(np.var(samples,ddof=1)));fail.append(a.bootstrap-len(samples))
 M=np.array([sum(t['diagnostics']['used'] for t in g.tasks) for g in gs],dtype=float)
 A=M*np.array(vars);cost=np.array(a.seconds_per_sweep);scale=np.sqrt(A*cost).sum()/a.target_stat**2
 target=np.maximum(M,np.ceil(scale*np.sqrt(A/cost)));achieved=float(np.sqrt(np.sum(A/target)))
 r=dict(d=a.dim,s=a.s,Delta_sigma=(a.dim-a.s)/2,L=[a.L,2*a.L],current_measurements=M.tolist(),
        variance_contributions=vars,A=A.tolist(),bootstrap_failed=fail,seconds_per_sweep=cost.tolist(),
        target_statistical_stderr=a.target_stat,recommended_total_measurements=target.astype(np.int64).tolist(),
        approximate_additional_core_hours=float(np.sum((target-M)*cost)/3600),predicted_statistical_stderr=achieved,
        qualification='Asymptotic statistical planning at these SAME sizes and temperature proportions. No guarantee on continuum error, thermalization, new sizes, or new machines.')
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
