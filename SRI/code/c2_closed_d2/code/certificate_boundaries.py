#!/usr/bin/env python3
"""Exact endpoint terms required by the final three-4F3 reduction.

This small checker completes the endpoint bookkeeping of the unchanged stage-00
lri_C2_three_4F3.py certificates. It uses the same three base summands, but derives
their n^-2 constants by the gamma-ratio asymptotic formula. No numerical fitting
or value of C2 is used.
"""
from pathlib import Path
import argparse,json
import sympy as sp
from lri_C2_three_4F3 import symbolic_certificates


def check():
    n=sp.symbols('n',positive=True)
    q=sp.Rational(1,4);h=sp.Rational(1,2)
    R=sp.gamma(q)/sp.gamma(3*q)
    bases={
      'X':([h,h,h,3*q],[1,1,5*q]),
      'Y':([h,h,h,q],[1,1,3*q]),
      'Z':([h,3*q,3*q,3*q],[5*q,5*q,5*q]),
    }
    expected={'X':-2*R/sp.pi**sp.Rational(3,2),
              'Y':-24/(R*sp.pi**sp.Rational(3,2)),
              'Z':R**3/(8*sp.sqrt(sp.pi))}
    exact=symbolic_certificates();rows={}
    for name,(top,bottom) in bases.items():
        excess=sp.simplify(sum(bottom)-sum(top))
        assert excess==1
        term_constant=sp.prod(sp.gamma(b) for b in bottom)/sp.prod(sp.gamma(a) for a in top)
        leading=sp.Integer(exact[name]['quadratic_coefficient'])
        boundary=sp.simplify(sp.expand_func(leading*term_constant))
        residual=sp.simplify(sp.expand_func(boundary-expected[name]))
        assert residual==0 and exact[name]['H_at_zero']=='0'
        rows[name]={
          'base_numerator_parameters':[str(x) for x in top],
          'base_denominator_parameters':[str(x) for x in bottom],
          'base_series_excess':str(excess),
          'limit_n_squared_times_base_summand':str(sp.simplify(sp.expand_func(term_constant))),
          'limit_H_over_n_squared':str(leading),
          'finite_endpoint_H0':'0',
          'infinite_endpoint':str(boundary),
          'expected_infinite_endpoint':str(expected[name]),
          'exact_boundary_residual':str(residual),
          'rational_certificate_residual':exact[name]['residual'],
        }
    return {'scope':'Exact rational certificate and nonzero endpoint-term identities; no new physical matching proof.',
            'all_exact_residuals_zero':True,'certificates':rows,
            'identity_convention':'sum a_n old_factor(n) - c sum a_n new_ratio(n) = lim H(n)a_n - H(0)a_0'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--json',type=Path,default=Path(__file__).resolve().parents[1]/'outputs/raw/certificate_boundaries.json')
    a=p.parse_args();report=check();a.json.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(report,indent=2)+'\n';a.json.write_text(text);print(text,end='')
if __name__=='__main__':main()
