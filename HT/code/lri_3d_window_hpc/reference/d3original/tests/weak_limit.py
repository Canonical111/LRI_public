#!/usr/bin/env python3
"""Weak-coupling scaling check against independently calculated shell C2(L).

No coefficients from the analytic note enter the nonlinear solve or this
finite-cutoff consistency test. The residual must start at order epsilon^3.
"""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
from d3dressed.solver import DressedSolver
from check_second_order import C2

def main():
    out=[]
    for L in (4,6,8):
        solver=DressedSolver(L,12,96,eig_tol=2e-13,ncv=40)
        c2=C2(L)
        for eps in (.02,.01,.005,.002):
            solver.set_delta((3-eps)/4);r=solver.solve(tol=4e-13,maxiter=40)
            approx=1.5-eps/6+c2*eps**2
            err=r['Delta_thermal']-approx
            row={'L':L,'epsilon':eps,'direct':r['Delta_thermal'],'second_order_polynomial':approx,'C2_rational_shell':c2,'residual':err,'residual_over_epsilon_cubed':err/eps**3,'tuning':r['tuning_residual']}
            out.append(row);print(row,flush=True)
        rs=[a for a in out if a['L']==L]
        assert max(abs(a['residual_over_epsilon_cubed']) for a in rs)<.5
        assert abs(rs[-1]['residual'])<abs(rs[0]['residual'])/300
    (ROOT/'reproduced').mkdir(exist_ok=True)
    (ROOT/'reproduced/weak_limit.json').write_text(json.dumps(out,indent=2))
if __name__=='__main__':main()
