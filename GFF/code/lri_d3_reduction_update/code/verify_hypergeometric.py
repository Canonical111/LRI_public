#!/usr/bin/env python3
"""Verify the hypergeometric presentation of P5 without stored period inputs.

The principal checks are Cauchy coefficients of the literal 9F8(-1) family,
direct Barnes integrals defining the Meijer G values, independent positive gamma quadrature, and the
Euler-accelerated harmonic series. Only mpmath is required.

Usage: python code/verify_hypergeometric.py --digits 60 \
           --output verification/hypergeometric_checks.json
This is a numerical consistency check, not an interval enclosure or a new
full five-loop calculation. Mathematica execution is not tested here.
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
import mpmath as mp
from evaluate_P5_further import h, phi, _cauchy_coefficients, p5_gamma, p5_euler_series


def run(digits: int) -> dict:
    if digits < 20:
        raise ValueError('digits must be at least 20')
    started = time.perf_counter()
    out = {'requested_digits': digits, 'working_digits': digits+25,
           'saved_period_values_used': False, 'rigorous_error_enclosure': False,
           'scope': 'Special-function equivalence of P5 only; no graph integrals rerun.',
           'mpmath_version': mp.__version__}
    # The nearest poles of the literal h family are safely outside both circles.
    nodes = max(48, 2*((digits+15)//2))
    with mp.workdps(digits+25):
        def s(x): return mp.nstr(x, digits+10)
        jets=[]
        for radius in ('0.01','0.007'):
            c = _cauchy_coefficients(phi, (0,1,2), radius, nodes)
            jets.append(c)
            print(f'9F8 Cauchy coefficients complete: radius={radius}, nodes={nodes}',flush=True)
        c=jets[0]
        value=mp.pi**3*(22*c[2]-26*mp.pi*c[1]+3*mp.pi**2*c[0])
        out['Cauchy']={'nodes':nodes,'radii':['0.01','0.007'],
          'Phi_Taylor_coefficients':{str(k):s(c[k]) for k in c},
          'coefficient_differences':{str(k):s(jets[1][k]-c[k]) for k in c}}
        out['P5_hypergeometric']=s(value)
        # Independent Cauchy coefficients of h, not of the Gamma-prefactored Phi.
        hc=_cauchy_coefficients(h,(0,1,2),'0.008',nodes)
        alpha=4+7*(mp.digamma(mp.mpf(1)/2)-mp.digamma(1))
        beta=-16+7*(mp.polygamma(1,mp.mpf(1)/2)-mp.polygamma(1,1))
        D=mp.digamma(mp.mpf(3)/4)-mp.digamma(mp.mpf(1)/4)
        R=mp.polygamma(1,mp.mpf(1)/2)-mp.polygamma(1,1)
        expanded=mp.pi**3*(22*hc[2]+(22*alpha-26*mp.pi)*hc[1]
                    +(11*(alpha**2+beta)-26*mp.pi*alpha+3*mp.pi**2)*hc[0])
        psi=D**3*(22*hc[2]+(22*alpha-26*D)*hc[1]
                    +(11*alpha**2-26*D*alpha-176+86*R)*hc[0])
        out['h_Taylor_coefficients']={str(k):s(hc[k]) for k in hc}
        out['expanded_minus_hypergeometric']=s(expanded-value)
        out['polygamma_minus_hypergeometric']=s(psi-value)
        print('Expanded and polygamma checks complete',flush=True)
        # Evaluate the literal Barnes contours, not mpmath's repeated-pole
        # hypergeometric continuation algorithm. Conjugate halves reduce each
        # upward contour s=-1/4+i*y to Re(integrand)/pi over y>0.
        def barnes_value(which):
            def integrand(y):
                if not y: return mp.mpf(0)
                z=mp.j*y
                lp=mp.loggamma(mp.mpf(1)/4+z)
                lm=mp.conj(lp)
                rp=mp.loggamma(mp.mpf(3)/4+z)
                rm=mp.conj(rp)
                if which == 1: lg=lm+7*lp-6*rp
                elif which == 2: lg=2*lm+6*lp-5*rp-rm
                else: lg=3*lm+7*lp-4*rp
                return mp.re(z*mp.exp(lg))/mp.pi
            return mp.quad(integrand,[0,mp.mpf(1)/4,1,3,10,mp.inf])
        gs={'G_1_8':barnes_value(1),'G_2_7':barnes_value(2),
            'G_3_8':barnes_value(3)}
        mg=8/mp.sqrt(mp.pi)*(11*gs['G_3_8']+13*mp.pi**2*gs['G_2_7']-4*mp.pi**2*gs['G_1_8'])
        out['P5_Barnes_contours']=s(mg)
        out['Barnes_G_values']={k:s(v) for k,v in gs.items()}
        out['Barnes_minus_hypergeometric']=s(mg-value)
        out['native_MeijerG_function_evaluated_in_this_record']=False
        expected={'G_1_8':mp.pi**(mp.mpf(7)/2)/4*c[0],
                  'G_2_7':-mp.pi**(mp.mpf(5)/2)/4*c[1],
                  'G_3_8':mp.pi**(mp.mpf(7)/2)/8*(2*c[2]+mp.pi**2*c[0])}
        out['individual_Barnes_G_minus_jet']={k:s(gs[k]-expected[k]) for k in gs}
        print('All three direct Barnes-contour conversion checks complete',flush=True)
        ga=p5_gamma(digits,guard=25)
        eu=p5_euler_series(digits)
        out['P5_gamma_integral']=s(ga)
        out['gamma_minus_hypergeometric']=s(ga-value)
        out['Euler_series_minus_gamma']=s(eu-ga)
        print('Independent gamma quadrature and harmonic-series checks complete',flush=True)
        # Record convergence and the upper/lower parameter cancellation issue.
        t=mp.mpf('0.02')
        excess=sum([mp.mpf(1)/4+t]+[1+t]*7)-sum([1,mp.mpf(5)/4+t]+[mp.mpf(1)/2+t]*7)
        out['parametric_excess_at_t_0p02']=s(excess)
    out['elapsed_seconds']=time.perf_counter()-started
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--digits',type=int,default=60)
    p.add_argument('--output',type=Path,default=Path('verification/hypergeometric_checks.json'))
    args=p.parse_args()
    try: out=run(args.digits)
    except ValueError as exc: p.error(str(exc))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2),flush=True)

if __name__=='__main__': main()
