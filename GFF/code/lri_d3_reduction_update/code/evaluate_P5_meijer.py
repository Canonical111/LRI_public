#!/usr/bin/env python3
"""Derivative-free Meijer-G evaluation of the gamma moment P5.

P5 = 8/sqrt(pi) [11 G_(3,8) + 13*pi^2 G_(2,7) - 4*pi^2 G_(1,8)],
where G_(m,n) = G^(m,n)_(8,8)(1 | -1/4,(1/2)^7 ; 0^7,3/4).
The two lists of each mpmath argument explicitly retain the m/n split.

Usage:
    python evaluate_P5_meijer.py --digits 50 --verify --output checks.json

Only mpmath is required. Verification compares the named-function evaluation
with fresh quadrature of the positive gamma integral. No stored period values
are inputs. Numerical agreement is not an interval error certificate or a
verification of the full Ising C5 coefficient.
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
import mpmath as mp

ALLOWED = ((1,8), (2,7), (3,8))


def g_value(m: int, n: int):
    """One of the three standard Meijer-G constants, at current precision."""
    if (m, n) not in ALLOWED:
        raise ValueError('The supported pairs are (1,8), (2,7), (3,8).')
    quarter = mp.mpf(1)/4
    upper = [-quarter] + [2*quarter]*7
    lower = [mp.mpf(0)]*7 + [3*quarter]
    return mp.meijerg([upper[:n], upper[n:]],
                     [lower[:m], lower[m:]], mp.mpf(1), series=1)


def meijer_evaluation(digits: int = 50, guard: int = 15):
    with mp.workdps(digits+guard):
        values = {f'G_{m}_{n}': g_value(m,n) for m,n in ALLOWED}
        answer = 8/mp.sqrt(mp.pi)*(11*values['G_3_8']
                  +13*mp.pi**2*values['G_2_7']-4*mp.pi**2*values['G_1_8'])
        return answer, values


def gamma_evaluation(digits: int = 50, guard: int = 20):
    """Independent positive-real-axis quadrature of the given gamma moment."""
    with mp.workdps(digits+guard):
        def integrand(y):
            if not y:
                return mp.mpf(0)
            log_power = 14*mp.re(mp.loggamma(mp.mpf(1)/4+1j*y))
            return y*mp.fsum(
                weight*mp.exp(log_power+2*r*mp.pi*y)
                *(-mp.expm1(-4*r*mp.pi*y))/2
                for r,weight in ((1,29),(2,13),(3,1)))
        return mp.quad(integrand,[0,mp.mpf(1)/4,1,3,10,mp.inf])/mp.pi**(mp.mpf(11)/2)


def moment_evaluation(r: int, digits: int = 40, guard: int = 15):
    """M_r = integral y |Gamma(1/4+iy)|^14 sinh(2*pi*r*y) dy."""
    if r not in (1,2,3):
        raise ValueError('r must be 1, 2, or 3.')
    with mp.workdps(digits+guard):
        def f(y):
            if not y:
                return mp.mpf(0)
            log_power=14*mp.re(mp.loggamma(mp.mpf(1)/4+1j*y))
            return y*mp.exp(log_power+2*r*mp.pi*y)*(-mp.expm1(-4*r*mp.pi*y))/2
        return mp.quad(f,[0,mp.mpf(1)/4,1,3,10,mp.inf])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--digits',type=int,default=50)
    parser.add_argument('--verify',action='store_true')
    parser.add_argument('--individual-moments',action='store_true')
    parser.add_argument('--output',type=Path,default=Path('P5_meijer_checks.json'))
    args=parser.parse_args()
    if args.digits<15:
        parser.error('--digits must be at least 15')
    start=time.perf_counter()
    result,values=meijer_evaluation(args.digits)
    print('Meijer-G evaluation complete',flush=True)
    out={'requested_digits':args.digits,
         'P5_meijer':mp.nstr(result,args.digits),
         'G_values':{k:mp.nstr(v,args.digits) for k,v in values.items()}}
    if args.verify:
        direct=gamma_evaluation(args.digits)
        with mp.workdps(args.digits+25):
            out['P5_gamma_integral']=mp.nstr(direct,args.digits)
            out['meijer_minus_gamma']=mp.nstr(result-direct,20)
        print('Gamma-integral comparison complete',flush=True)
    if args.individual_moments:
        M={r:moment_evaluation(r,args.digits) for r in (1,2,3)}
        with mp.workdps(args.digits+25):
            expected={'G_3_8':M[1]/(2*mp.pi**5),
                      'G_2_7':M[2]/(8*mp.pi**7),
                      'G_1_8':(15*M[1]-M[3])/(32*mp.pi**7)}
            out['individual_moment_errors']={k:mp.nstr(values[k]-expected[k],20) for k in expected}
            out['gamma_moments']={f'M{r}':mp.nstr(v,args.digits) for r,v in M.items()}
    out.update(mpmath_version=mp.__version__,saved_period_values_used=False,
               rigorous_error_enclosure=False,
               scope='Special-function evaluation of the given P5 gamma integral, not full C5 validation.',
               elapsed_seconds=time.perf_counter()-start)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out,indent=2),flush=True)

if __name__=='__main__':
    main()
