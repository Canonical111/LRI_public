#!/usr/bin/env python3
"""C2 source-contact identity and numerical checks.

Adapted from stage 00 code/two_d/lri_C2_regulator_audit.py.
The exploratory rational-order obstruction was omitted; contact formulas are unchanged.

The identity A_p(M) = 4 B_p(M) - pi^2/4 is proved in the companion
TeX addendum. This program evaluates its two sides by different
one-dimensional integrals: a rational integral for B, and a Fourier
coefficient/root representation for A. No value of C2 is used in that check.

This is NOT a computation of the full six-point renormalized residue,
and does NOT remove the candidate qualification of the previous C2.
Requires Python 3.10+ and mpmath.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import mpmath as mp


def _validate(p: int, M) -> mp.mpf:
    if not isinstance(p, int) or isinstance(p, bool) or p < 1:
        raise ValueError('p must be a positive integer (a smooth source).')
    M = mp.mpf(M)
    if M < 0:
        raise ValueError('M must be nonnegative.')
    return M


def lower_order_constant(p: int, M=3) -> mp.mpf:
    """B_p(M), evaluated by an ordinary, nonsingular rational integral."""
    M = _validate(p, M)
    if M == 0:
        return mp.pi**2/8
    def integrand(r):
        y = r**(2*p)
        return (1/(1+M*y)-y/(y+M))/(1+r)**2
    integral = mp.quad(integrand, [0, mp.mpf('.25'), mp.mpf('.5'), 1])
    return mp.pi**2/8-mp.pi**2*integral/2


def branch_contact(p: int, M=3) -> mp.mpf:
    """A_p(M), via an independent angular Fourier coefficient.

    Factor (1+r^2+2r cos t)^(2p)+M(1+r^2-2r cos t)^(2p).
    Each factor is a+b cos(t). Its second logarithmic Fourier coefficient
    is -pi*s^2, where |s|<1 and s+1/s=-2a/b.
    The reciprocal of the LARGE root is used to avoid catastrophic
    cancellation as r tends to zero.
    """
    M = _validate(p, M)
    if M == 0:
        return mp.pi**2/4
    roots = [M**(mp.mpf(1)/(2*p))*mp.exp(mp.j*mp.pi*(2*k+1)/(2*p))
             for k in range(2*p)]
    def integrand(r):
        if not r:
            return mp.mpf(0)
        values = []
        for q in roots:
            a = (1-q)*(1+r*r)
            b = 2*r*(1+q)
            disc = mp.sqrt(a*a-b*b)
            large = max(((-a+disc)/b, (-a-disc)/b), key=abs)
            small = 1/large
            values.append(small*small)
        return mp.re(mp.fsum(values))/r
    integral = mp.quad(integrand, [0, mp.mpf('.25'), mp.mpf('.5'),
                                   mp.mpf('.75'), 1])
    return -mp.pi**2/4+mp.pi**2*integral/(2*p)


def run(dps: int = 50) -> dict:
    if dps < 25:
        raise ValueError('Use at least 25 digits.')
    with mp.workdps(dps):
        records = []
        for p,M in [(1,3),(2,3),(3,3),(5,3),(2,mp.mpf('.5')),(3,5)]:
            B=lower_order_constant(p,M)
            A=branch_contact(p,M)
            error=A-4*B+mp.pi**2/4
            records.append({'p':p,'M':mp.nstr(M,15),
                            'B':mp.nstr(B,dps-8),'A':mp.nstr(A,dps-8),
                            'error':mp.nstr(error,10)})
        b_exact=mp.pi**2*(12-mp.pi*mp.sqrt(3)-9*mp.log(3))/96
        b_error=lower_order_constant(1,3)-b_exact
        return {'status':'Local contact identity checked; full physical C2 unproved here.',
                'working_dps':dps,'profiles':records,
                'gaussian_closed_form_error':mp.nstr(b_error,10)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dps',type=int,default=50)
    parser.add_argument('--json',type=Path)
    args=parser.parse_args()
    result=run(args.dps)
    text=json.dumps(result,indent=2)
    print(text)
    if args.json:
        args.json.parent.mkdir(parents=True,exist_ok=True)
        args.json.write_text(text+'\n')

if __name__=='__main__':
    main()
