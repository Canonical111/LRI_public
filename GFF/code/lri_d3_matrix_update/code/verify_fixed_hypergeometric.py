#!/usr/bin/env python3
"""Verify the finite fixed-parameter P5 formula, without parameter differentiation.

The reference is fresh positive gamma quadrature, never a stored period value.
All numerical residuals are consistency checks, not interval error bounds.
Requires mpmath and sympy.  From the revision root:
    python code/verify_fixed_hypergeometric.py --digits 100 \
        --output verification/fixed_hypergeometric_checks.json
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
import mpmath as mp


def hyper_y(r: int):
    """Gamma-normalized fixed 9F8(-1); r=2 simplifies to an 8F7."""
    v = mp.mpf(r)/8
    a = v + mp.mpf(1)/4
    b = v + mp.mpf(3)/4
    return v*(mp.gamma(a)/mp.gamma(b))**7*mp.hyper(
        [1, 1+v]+[a]*7, [v]+[b]*7, -1)


def unilateral(t):
    """Only used at explicitly fixed nonsingular complex test points."""
    a=t+mp.mpf(1)/2; b=t+1; v=t+mp.mpf(1)/4
    return v*(mp.gamma(a)/mp.gamma(b))**7*mp.hyper(
        [1,1+v]+[a]*7,[v]+[b]*7,-1)


def regularized_bilateral(t):
    return mp.cos(mp.pi*t)**7*unilateral(t)-mp.sin(mp.pi*t)**7*unilateral(mp.mpf(1)/2-t)


def fixed_formula():
    y={r:hyper_y(r) for r in (1,2,3,5,7)}
    c=mp.cos(mp.pi/8); s=mp.sin(mp.pi/8)
    e0=y[2]; ep=c**7*y[3]-s**7*y[5]; em=c**7*y[1]+s**7*y[7]
    p=16*mp.pi**mp.mpf('1.5')*(-35*e0+(22*mp.sqrt(2)-13)*ep+(22*mp.sqrt(2)+13)*em)
    return p,y,(e0,ep,em)


def gamma_integrand(y):
    if not y: return mp.mpf(0)
    p=mp.pi*y
    # Stable evaluation of exp(14 Re log Gamma)*[sinh(6p)+13sinh(4p)+29sinh(2p)].
    bracket=(-mp.expm1(-12*p)+13*mp.exp(-2*p)*(-mp.expm1(-8*p))
             +29*mp.exp(-4*p)*(-mp.expm1(-4*p)))/2
    return y*mp.exp(14*mp.re(mp.loggamma(mp.mpf(1)/4+1j*y))+6*p)*bracket/mp.pi**mp.mpf('5.5')


def gamma_reference(breaks):
    return mp.quad(gamma_integrand, breaks+[mp.inf])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--digits',type=int,default=100)
    parser.add_argument('--output',type=Path,default=Path('verification/fixed_hypergeometric_checks.json'))
    args=parser.parse_args()
    if args.digits<40: parser.error('--digits must be at least 40')
    mp.mp.dps=args.digits
    started=time.time()
    enc=lambda z: mp.nstr(z,args.digits)
    p,y,(e0,ep,em)=fixed_formula()
    alpha=(e0+(ep+em)/mp.sqrt(2))/2
    beta=(ep-em)/2
    gamma=(e0-(ep+em)/mp.sqrt(2))/2
    # Five entirely different frozen-parameter values, at t=0,+/-1/6,1/3,2/3.
    sixthp=regularized_bilateral(mp.mpf(1)/6)
    sixthm=regularized_bilateral(-mp.mpf(1)/6)
    psixth=16*mp.pi**mp.mpf('1.5')*(-mp.mpf(61)/3*e0
        +(mp.mpf(88)/3-26/mp.sqrt(3))*sixthp
        +(mp.mpf(88)/3+26/mp.sqrt(3))*sixthm)
    tests=[]
    for t in [mp.mpf('0.07'),mp.mpf('-0.2'),mp.mpf('0.31'),mp.mpc('0.13','0.09'),mp.mpc('0.2','0.7')]:
        direct=regularized_bilateral(t)
        trig=alpha*mp.cos(2*mp.pi*t)+beta*mp.sin(4*mp.pi*t)+gamma*mp.cos(6*mp.pi*t)
        tests.append({'point':enc(t),'residual':enc(direct-trig),'absolute_residual':enc(abs(direct-trig))})
    excesses={}
    for r in (1,2,3,5,7):
        v=mp.mpf(r)/8
        excesses[str(r)]=enc(v+7*(v+mp.mpf(3)/4)-(2+v+7*(v+mp.mpf(1)/4)))
    gvals={'G_1_8':e0, 'G_2_7':2*(em-ep), 'G_3_8':mp.pi**2*(-6*e0+4*mp.sqrt(2)*(ep+em))}
    meijer_combination=8/mp.sqrt(mp.pi)*(11*gvals['G_3_8']+13*mp.pi**2*gvals['G_2_7']-4*mp.pi**2*gvals['G_1_8'])
    print('Fixed hypergeometric P5:',enc(p),flush=True)
    print('Starting independent positive gamma quadrature...',flush=True)
    breaks=[mp.mpf(0),mp.mpf(1)/32,mp.mpf(1)/8,mp.mpf(1)/2,1,2,4,8,16,32]
    pgamma=gamma_reference(breaks)
    print('Gamma minus frozen:',enc(pgamma-p),flush=True)
    # A higher-working-precision control changes the quadrature segmentation as well.
    with mp.workdps(args.digits+25):
        p_hi,_,_=fixed_formula()
        breaks_hi=[mp.mpf(0),mp.mpf(1)/20,mp.mpf(1)/5,mp.mpf(3)/5,mp.mpf(3)/2,3,6,12,24,48]
        pgamma_hi=gamma_reference(breaks_hi)
        hi={'working_digits':mp.mp.dps, 'P5_frozen':mp.nstr(p_hi,mp.mp.dps),
            'P5_gamma':mp.nstr(pgamma_hi,mp.mp.dps),
            'gamma_minus_frozen':mp.nstr(pgamma_hi-p_hi,mp.mp.dps),
            'frozen_high_minus_base':mp.nstr(p_hi-p,mp.mp.dps),
            'gamma_high_minus_base':mp.nstr(pgamma_hi-pgamma,mp.mp.dps),
            'quadrature_breakpoints':[mp.nstr(x,20) for x in breaks_hi]+['+inf']}
    import sympy as sp
    X,Y,Z,pi=sp.symbols('X Y Z pi'); rt=sp.sqrt(2)
    # Exact substitution from the original three-G formula.
    g1=X;g2=2*(Z-Y);g3=pi**2*(-6*X+4*rt*(Y+Z))
    # Cancel the shared 8*pi^(3/2) factor before checking, to avoid branch issues.
    exact=sp.simplify(11*g3/pi**2+13*g2-4*g1-2*(-35*X+(22*rt-13)*Y+(22*rt+13)*Z))
    assert exact==0
    # Exact symbolic sampling identity, and the coefficient combination for +/-1/6.
    A,B,C=sp.symbols('alpha beta gamma')
    e_0=A+C;e_p=(A-C)/rt+B;e_m=(A-C)/rt-B
    sample=sp.expand(-35*e_0+(22*rt-13)*e_p+(22*rt+13)*e_m-(9*A-26*B-79*C))
    assert sp.simplify(sample)==0
    sxp=A/2-C+sp.sqrt(3)*B/2;sxm=A/2-C-sp.sqrt(3)*B/2
    sixexpr=-sp.Rational(61,3)*e_0+(sp.Rational(88,3)-26/sp.sqrt(3))*sxp+(sp.Rational(88,3)+26/sp.sqrt(3))*sxm
    assert sp.simplify(sixexpr-(9*A-26*B-79*C))==0
    result={
        'working_digits':args.digits,'mpmath_version':mp.__version__,
        'scope':'New fixed-parameter special-function identity only; no graph or counterterm computations rerun.',
        'saved_period_values_used':False,'parameter_derivatives_used':False,
        'parameter_limits_used':False,'Cauchy_coefficients_used':False,
        'rigorous_interval_enclosure':False,
        'formula':'16*pi^(3/2)*[-35*Y2+(22*sqrt(2)-13)*(cos(pi/8)^7*Y3-sin(pi/8)^7*Y5)+(22*sqrt(2)+13)*(cos(pi/8)^7*Y1+sin(pi/8)^7*Y7)]',
        'P5_frozen':enc(p),'P5_gamma':enc(pgamma),'gamma_minus_frozen':enc(pgamma-p),
        'Y_values':{str(r):enc(v) for r,v in y.items()},
        'E_samples':{'0':enc(e0),'1/8':enc(ep),'-1/8':enc(em)},
        'fourier_coefficients':{'alpha':enc(alpha),'beta':enc(beta),'gamma':enc(gamma)},
        'parametric_excesses':excesses,
        'G_values_reconstructed_from_frozen_pFq':{k:enc(v) for k,v in gvals.items()},
        'three_G_combination_minus_frozen':enc(meijer_combination-p),
        'trigonometric_identity_checks':tests,
        'alternative_sixth_grid_minus_eighth_grid':enc(psixth-p),
        'higher_precision_control':hi,
        'exact_symbolic_checks':{'original_G_combination':True,'eighth_grid':True,'sixth_grid':True},
        'elapsed_seconds':time.time()-started
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Higher precision residual:',hi['gamma_minus_frozen'],flush=True)
    print('Wrote',args.output,'elapsed',time.time()-started,flush=True)

if __name__=='__main__':
    main()
