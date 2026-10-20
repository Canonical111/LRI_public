#!/usr/bin/env python3
"""Reconstruct diagrams and check the compact a5 formula.
Run in this directory. Requires mpmath; no browser, fitting, or bootstrap data.
The only interpolant below is a labelled numerical limit of an exact Selberg
integral, not a fit used to obtain any perturbative coefficient.
"""
import json
import os
from pathlib import Path
import mpmath as mp
from assemble import compute,stringify
from calculate_a5 import coefficients
from enumerate_graphs import enumerate_graphs


def main():
    os.chdir(Path(__file__).resolve().parent)
    mp.mp.dps=65
    report={'precision_decimal_digits':mp.mp.dps,'dimensions':[]}
    counts={n:len(enumerate_graphs(n)) for n in (2,3,4,5)}
    assert counts=={2:1,3:1,4:5,5:14}
    report['enumerated_graph_counts']=counts
    for d in (1,2,3):
        base=compute(d)
        alt=compute(d,seed=4,star_choice=1)
        formula=coefficients(d)
        residuals={f'a{k}':base['coefficients'][k]-formula[f'a{k}'] for k in (2,3,4,5)}
        changed=alt['coefficients'][5]-base['coefficients'][5]
        pole=max(abs(base['fs'][n].get(k,0)) for n in (3,4,5) for k in (-3,-2,-1))
        A,R,U,V,T,P=(formula[k] for k in ('A','R','U','V','T','P4'))
        q=mp.mpf(d)/4
        M=mp.gamma(-q)*mp.gamma(2*q)**2/mp.gamma(3*q)
        N=mp.digamma(-q)+mp.digamma(3*q)-mp.digamma(1)-mp.digamma(2*q)
        s41=M*(A+N)/18+A*R+U/8-9*V/4
        s50=mp.mpf(7)/8*A**3+M*(A+N)+mp.mpf(145)/8*A*R+mp.mpf(43)/16*U-mp.mpf(181)/8*V
        kernel_residuals={'S4_linear':base['S4'][1]-s41,'S5_finite':base['S5'][0]-s50}
        assert max([abs(x) for x in residuals.values()]+[abs(changed),pole]+[abs(x) for x in kernel_residuals.values()])<mp.mpf('1e-45')
        row={'d':d,'diagram_minus_closed_formula':residuals,
             'changed_deformation_and_reference_a5_difference':changed,
             'largest_uncancelled_pole':pole,'kernel_jet_residuals':kernel_residuals}
        report['dimensions'].append(row)
        Path(f'assembled_d{d}.json').write_text(json.dumps(stringify(base),indent=2)+'\n')
        print('d=',d,'a5=',mp.nstr(base['coefficients'][5],25), 'max formula residual=',mp.nstr(max(map(abs,residuals.values())),8),flush=True)
    def gamma_ratio(x):return mp.gamma(x)/mp.gamma(1-x)
    def selberg(e):
        u=(2-e)/4;a=1-u;r=-u/2
        return mp.factorial(3)*mp.fprod(gamma_ratio(a+j*r)**2*gamma_ratio((j+1)*r)/(gamma_ratio(2*a+(2+j)*r)*gamma_ratio(r)) for j in range(3))
    T=coefficients(2)['T'];steps=[mp.mpf('.0001')/2**j for j in range(8)]
    remainders=[selberg(e)-2*T/(3*e) for e in steps]
    # Polynomial extrapolation solely checks the finite part of the independent exact integral.
    mat=mp.matrix([[e**k for k in range(len(steps))] for e in steps])
    finite=(mp.lu_solve(mat,mp.matrix(remainders)))[0]
    assert abs(finite)<mp.mpf('1e-28')
    report['independent_d2_three_variable_Selberg_check']={'epsilon':steps,
        'K7_minus_pole':remainders,'extrapolated_finite_part':finite,'expected_finite_part':'0',
        'warning':'Limit-extrapolation residual, not a physical uncertainty bound.'}
    report['scope']='Internal graph reduction, symbolic/numerical consistency and one independent exact special-dimensional integral; no direct numerical integration of every five-vertex graph and no independent four-loop beta-function computation.'
    Path('verification_results.json').write_text(json.dumps(stringify(report),indent=2)+'\n')
    print('Selberg finite-part limit:',mp.nstr(finite,15))
    print('All assertions passed.')

if __name__=='__main__':main()
