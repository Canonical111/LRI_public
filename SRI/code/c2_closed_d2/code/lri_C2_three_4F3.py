#!/usr/bin/env python3
"""Three ordinary 4F3(1) constants for the candidate 2d LRI C2.

The reduction from six 4F3 constants is proved by three explicit rational
summation certificates and their nonzero Gamma boundary terms. All new
series have excess 2, so no analytic continuation is used in evaluating
this closed form. This simplifies the existing candidate; it does not
independently validate the physical regulator/contact matching.

Requires mpmath. SymPy is needed only for --symbolic.
Examples:
  python lri_C2_three_4F3.py --dps 80
  python lri_C2_three_4F3.py --dps 120 --check --symbolic --json checks.json
"""
from __future__ import annotations
import argparse
import json
from functools import lru_cache
from pathlib import Path
from typing import Sequence
import mpmath as mp


def coefficient(dps: int = 80) -> dict:
    if dps < 25:
        raise ValueError('Use at least 25 working decimal digits.')
    with mp.workdps(dps):
        q = mp.mpf(1)/4
        h = 2*q
        R = mp.gamma(q)/mp.gamma(3*q)
        P = mp.hyper([-h,-h,3*h,3*q], [1,2,q], 1)
        Q = mp.hyper([h,3*h,3*h,9*q], [3,3,7*q], 1)
        T = mp.hyper([3*h,-q,3*q,3*q], [q,9*q,9*q], 1)
        left = P-5*R**2*Q/384
        right = P-5*R**2*Q/128-512*T/(25*mp.pi*R**2)
        c2 = 16/R**2-R**2/9-mp.pi**2*R**2*left*right/16
        return dict(R=R,P=P,Q=Q,T=T,left=left,right=right,C2=c2)


def symbolic_certificates() -> dict:
    """Check all three rational summation identities exactly, not numerically."""
    try:
        import sympy as sp
    except ImportError as exc:
        raise RuntimeError('--symbolic requires SymPy.') from exc
    n=sp.symbols('n'); h=sp.Rational(1,2); q=sp.Rational(1,4)
    ratios = (
        (n+h)**3*(n+3*q)/((n+1)**3*(n+5*q)),
        (n+h)**3*(n+q)/((n+1)**3*(n+3*q)),
        (n+h)*(n+3*q)**3/((n+1)*(n+5*q)**3),
    )
    old_factors = (
        -(12*n+7)/(4*n-1),
        3*(12*n-1)/(4*n+3),
        2-5*((4*n+1)/(4*n-1))**3,
    )
    new_ratios = (
        (2*n+1)*(4*n+1)/((2*n-1)**2*(n+1)),
        sp.Rational(12,5)*(2*n+1)**2*(4*n+1)*(4*n+5)
            /((n+1)**2*(n+2)**2*(4*n+3)),
        -25*(2*n+1)*(4*n+1)/((4*n-1)*(4*n+5)**2),
    )
    certificates = (
        -4*n**2*(2*n-3)*(4*n+1)**2/((2*n-1)**2*(4*n-1)),
        -3*n*(16*n**3+44*n**2+34*n+15)/(2*(n+1)**2),
        2*n*(4*n+1)*(64*n**3+16*n**2-20*n+43)/(4*n-1)**3,
    )
    prefactors = (sp.Rational(9,2),sp.Rational(45,64),sp.Rational(72,25))
    result = {}
    for name,rat,old,new,H,c in zip('XYZ',ratios,old_factors,new_ratios,certificates,prefactors):
        residual = sp.factor(rat*H.subs(n,n+1)-H-old+c*new)
        if residual != 0:
            raise AssertionError(f'Certificate {name} failed: {residual}')
        result[name] = dict(residual=str(residual),H_at_zero=str(H.subs(n,0)),
                           quadratic_coefficient=str(sp.limit(H/n**2,n,sp.oo)))
    return result


def _convolve(a: Sequence, b: Sequence, n: int) -> tuple:
    return tuple(mp.fsum(a[k]*b[j-k] for k in range(j+1)) for j in range(n))


@lru_cache(maxsize=4)
def _base_series(n: int,dps: int) -> tuple:
    with mp.workdps(dps):
        f,g,H = [mp.mpf(1)],[mp.mpf(0)],mp.mpf(0)
        for k in range(1,n):
            f.append(f[-1]*((mp.mpf(k)-mp.mpf('0.5'))/k)**2)
            H += 1/mp.mpf(2*k-1)+1/mp.mpf(2*k)-1/mp.mpf(k)
            g.append(4*f[-1]*H)
        return _convolve(f,f,n),_convolve(f,g,n),_convolve(g,g,n)


def elliptic_moments(a,n: int,dps: int) -> tuple:
    """Independent U(a,a), V(a,a) from half-interval Frobenius series.

    Meromorphic continuation at negative a is implemented term by term.
    Neither the six- nor the three-4F3 formula is used in this evaluation.
    """
    with mp.workdps(dps):
        a=mp.mpf(a)
        ff,fg,gg=_base_series(n,dps)
        weight=[mp.mpf(1)]
        for k in range(1,n):
            weight.append(weight[-1]*(k-a)/k)
        x,y,z=(_convolve(weight,v,n) for v in (ff,fg,gg))
        sums=[[],[],[]]
        L=mp.log(32)
        for j in range(n):
            p=a+j
            if p==0:
                raise ValueError('Resonant Mellin exponent: a separate limit is required.')
            t=mp.power(2,-p)
            j0=t/p
            j1=t*(L/p+1/p**2)
            j2=t*(L**2/p+2*L/p**2+2/p**3)
            sums[0].append(mp.pi**2*x[j]*j0/4)
            sums[1].append(mp.pi*(x[j]*j1-y[j]*j0)/4)
            sums[2].append((x[j]*j2-2*y[j]*j1+z[j]*j0)/4)
        k0,k1,k2=(mp.fsum(v) for v in sums)
        return 4*(k0+k2)/mp.pi**2,8*k1/mp.pi**2


def checks(dps: int=80,n: int | None=None) -> dict:
    if n is None:
        n=4*dps+80
    with mp.workdps(dps):
        ans=coefficient(dps)
        R,P,Q,T=(ans[k] for k in ('R','P','Q','T'))
        q=mp.mpf(1)/4;h=2*q
        def A(a):return mp.hyper([h,h,h,a],[1,1,a+h],1)
        def D(a):return mp.hyper([h,a,a,a],[a+h,a+h,a+h],1)
        X0=5*A(-q)+2*A(3*q)
        Y0=5*A(5*q)-6*A(q)
        Z0=5*D(-q)+2*D(3*q)
        X=9*P/2-2*R/mp.pi**mp.mpf('1.5')
        Y=45*Q/64-24/(R*mp.pi**mp.mpf('1.5'))
        Z=72*T/25+R**3/(8*mp.sqrt(mp.pi))
        c_old=16/R**2-R**2/9-mp.pi**2/15552*(12*X0-R**2*Y0)*(R**2*(4*X0-R**2*Y0)-128*Z0/mp.pi)
        um,vm=elliptic_moments(-q,n,dps)
        up,vp=elliptic_moments(3*q,n,dps)
        f=mp.mpf(5)/2*um-4*up
        g=mp.mpf(5)/2*vm-4*vp
        c_period=16/R**2-R**2/9-mp.pi*R**4*(f+g)*(f+3*g)/10368
        errors=dict(X=X-X0,Y=Y-Y0,Z=Z-Z0,C2_vs_six=ans['C2']-c_old,
                    C2_vs_elliptic=ans['C2']-c_period)
        return dict(working_dps=dps,half_interval_terms=n,errors=errors,
                    max_absolute_discrepancy=max(abs(x) for x in errors.values()))


def _strings(obj,digits: int):
    if isinstance(obj,dict):return {k:_strings(v,digits) for k,v in obj.items()}
    if isinstance(obj,(str,int,bool)):return obj
    return mp.nstr(obj,digits)


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dps',type=int,default=80)
    parser.add_argument('--terms',type=int,default=None)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--symbolic',action='store_true')
    parser.add_argument('--json',type=Path,default=None)
    args=parser.parse_args()
    if args.dps<25 or (args.terms is not None and args.terms<20):
        parser.error('Require --dps>=25 and, if specified, --terms>=20.')
    mp.mp.dps=args.dps
    report=dict(status='Candidate physical coefficient; exact algebraic simplification.',
                working_dps=args.dps,values=coefficient(args.dps))
    if args.check:report['checks']=checks(args.dps,args.terms)
    if args.symbolic:report['symbolic_certificates']=symbolic_certificates()
    text=json.dumps(_strings(report,args.dps-8),indent=2)
    print(text)
    if args.json:
        args.json.parent.mkdir(parents=True,exist_ok=True)
        args.json.write_text(text+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
