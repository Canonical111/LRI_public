#!/usr/bin/env python3
"""Audit the saved nominal LP without refitting its reference bounds.
Writes a separate report; does not overwrite the numerical run receipt.
"""
from __future__ import annotations
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import argparse, json, math, hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
ROOT=Path(__file__).resolve().parents[2]
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,default=ROOT/'outputs/reproduced')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/review_validation/fixed_lp_diagnostics.json')
    a=parser.parse_args();res=a.results.resolve()
    bpath=res/'refinement/basis_L40.npz';lpath=res/'refinement/final_8_7_pad1_lp.npz'
    basis=np.load(bpath);lp=np.load(lpath)
    meta=json.loads((res/'refinement/basis_L40.json').read_text())
    A,B=lp['A'],lp['B'];n=A.shape[1];nz=len(basis['z'])
    if A.shape!=(6*nz,len(meta['names'])):raise ValueError('Unexpected saved row ordering')
    bad=np.where(B < -1e-9)[0]
    # Minimize t with Ax <= B, -t <= x_i <= t and the published epsilon-prime window.
    augmented=np.vstack([np.c_[A,np.zeros(len(B))],np.c_[np.eye(n),-np.ones(n)],np.c_[-np.eye(n),-np.ones(n)]])
    rhs=np.r_[B,np.zeros(2*n)];bounds=[(None,None)]*n+[(0,None)]
    k=meta['names'].index('even_ss1_l0_d3.82968:h');scale=meta['parameters'][k]['scale']
    rows=json.loads((ROOT/'data/inputs/retained_spectrum.json').read_text());h0=rows[meta['parameters'][k]['row']]['h']
    bounds[k]=((1.5349-h0)/scale,(1.5375-h0)/scale)
    fit=linprog(np.r_[np.zeros(n),1.],A_ub=augmented,b_ub=rhs,bounds=bounds,method='highs',options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
    if not fit.success:raise RuntimeError(fit.message)
    z=basis['z'];real=(np.abs(z.imag)<1e-14)&(np.abs(z.real-.5)>1e-12);x=np.minimum(z.real[real],1-z.real[real]);rho=lambda x:x/(1+np.sqrt(1-x))**2
    low=json.loads((ROOT/'data/inputs/low_inputs.json').read_text())['values']
    sign={}
    for key in ['S','E']:
        D=low[key]['value'];sign[key]=float(np.max((rho(x)/rho(1-x))**8*((1-x)/x)**(2*D)))
    central=json.loads((res/'precision/analysis_results.json').read_text())['central']
    box=json.loads((res/'precision/input_box_results.json').read_text())['two_error_box']
    db=math.ceil(max(abs(box['delta_b_min']),abs(box['delta_b_max']))*1e6)/1e6
    nominal=json.loads((res/'refinement/final_8_7_pad1_summary.json').read_text())
    bs,ae=nominal['tail_b'],nominal['tail_a_even'];alo,ahi=nominal['tail_a_odd'];C,b=central['C1'],central['b'];q=nominal['objective_nonlinear_allowance']
    F=[nominal['input_linear_shift'][0]-q+(-ae+alo-C*bs)/b,nominal['input_linear_shift'][1]+q+(ae+ahi+C*bs)/b]
    report=dict(scope='Saved fixed-LP consistency diagnostics, not a physical confidence calculation',
      arrays_shape=list(A.shape),central_input_feasible=bool(len(bad)==0),central_violated_rows=len(bad),
      violations_by_correlator={s:int(np.sum((bad//(2*nz))==i)) for i,s in enumerate(['sigma4','epsilon4','mixed'])},
      violating_row_indices=bad.tolist(),min_scaled_rhs=float(B.min()),
      min_fixed_LP_maxnorm=float(fit.fun),min_maxnorm_in_quoted_error_units=2*float(fit.fun),
      witness=fit.x[:-1].tolist(),witness_max_constraint_violation=float(np.max(A@fit.x[:-1]-B)),
      interpretation='The minimum concerns fixed nominal LP rows. It is not the threshold for a rebuilt smaller-error-box problem. It is a maximum displacement, not a common displacement or a Gaussian significance.',
      real_axis_sign_factor_max=sign,reference=dict(a=central['a'],b=b,C1=C),derived_denominator_box=db,
      final_numerator_interval=F,ratio_sign_condition=bool(F[0]<=0<=F[1]),positive_denominator=bool(b>db+bs),
      source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [bpath,lpath]})
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['witness','violating_row_indices','source_sha256']},indent=2))
if __name__=='__main__':main()
