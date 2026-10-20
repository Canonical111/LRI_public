#!/usr/bin/env python3
"""Coefficient-level logic checked by small-epsilon values, NOT epsilon fitting.
The consistent window starts at O(eps^2) and annihilates the zero-bath primary
seeds. It leaves primary energies/tuning unchanged through cubic order. This
script tests the expected O(eps^4) difference, without fitting its coefficient.
"""
import sys,json,math
from pathlib import Path
from fractions import Fraction
from ht2d.solver import DressedSolver
from run import atomic_json
ROOT=Path(__file__).resolve().parents[1]

def c2(L):
    out=Fraction(17,81);c=Fraction(1)
    for n in range(1,L//2+1):
        c*=Fraction(2*n-1,2*n)
        out+=c*c*(Fraction(2,81*(2*n-1))+Fraction(2,9*2*n)+Fraction(2,9*(2*n+1))+Fraction(2,81*(2*n+2)))
    return out

def main():
    old=json.loads((ROOT/'inputs/prior_2d_points.json').read_text())
    rows=[]
    for eps in [.04,.02,.01,.005]:
        x=(2-eps)/4;values={}
        for mode in ['none','vacuum']:
            s=DressedSolver(4,16,128,window=mode,eig_tol=1e-13,ncv=40)
            s.set_delta(x);r=s.solve(tol=1e-13,maxiter=40);values[mode]=r['Delta_thermal']
        d=values['vacuum']-values['none'];rows.append(dict(epsilon=eps,raw=values['none'],window=values['vacuum'],difference=d,difference_over_epsilon4=d/eps**4))
    for a,b in zip(rows,rows[1:]):a['halving_difference_ratio']=a['difference']/b['difference']
    record={'scope':'Direct finite-epsilon validation only; no coefficient extracted by fitting','L':4,
            'C2_finite_exact':str(c2(4)),'C2_infinite':4*math.log(2)/9,'rows':rows}
    atomic_json(ROOT/'validation/weak_window.json',record);print(json.dumps(record,indent=2))
if __name__=='__main__':main()
