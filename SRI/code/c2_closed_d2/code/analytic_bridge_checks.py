#!/usr/bin/env python3
"""Exact and high-precision checks for analytic bridges in the C2-only note.

Requires mpmath and SymPy.  These checks do not integrate the regulated
quartic correlator and do not prove the global distributional matching.
No source archive, network access, or data file is needed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import mpmath as mp
import sympy as sp


def exact_checks():
    t = sp.symbols('t', positive=True)
    p = (1-2*t)/(t*(1-t))
    q = -1/(4*t*(1-t))
    ode1 = sp.diff(p,t)+2*p*p+4*q
    ode0 = 2*sp.diff(q,t)+4*p*q
    a = -8*t**sp.Rational(3,2)*(1-t)**2
    b = 4*sp.sqrt(t)*(1-t)*(5*t-3)
    c = 2*(1-t)*(3*t-1)/sp.sqrt(t)
    certificate = [sp.factor(sp.diff(a,t)-3*p*a+b),
                   sp.factor(sp.diff(b,t)-ode1*a+c),
                   sp.factor(sp.diff(c,t)-ode0*a-t**sp.Rational(-3,2)*(1-t*t))]
    assert certificate == [0,0,0]

    beta = sp.symbols('beta', real=True)
    J = sp.Matrix([[0,0,1],[0,2,0],[1,0,0]])
    Cp = sp.Matrix([[1,2*sp.I,-1],[0,1,sp.I],[0,0,1]])
    Cm = sp.conjugate(Cp)
    L = sp.Matrix([[0,0,sp.sin(beta)],
                   [0,2*sp.sin(beta),-2*sp.cos(beta)],
                   [sp.sin(beta),-2*sp.cos(beta),-sp.sin(beta)]])
    jump = sp.simplify(sp.expand_complex((sp.exp(sp.I*beta)*J*Cm
                                         -sp.exp(-sp.I*beta)*J*Cp)/(2*sp.I))-L)
    assert jump == sp.zeros(3)

    Bm = sp.Matrix([[1,0,0],[-sp.I,1,0],[-1,-2*sp.I,1]])
    expected_D = sp.Matrix([[1,-2,-1],[-1,-1,0],[0,-2,-1]])/sp.sqrt(2)
    for sign in (-1,1):
        Ac = sign*sp.I*Bm
        Ec = (1+sp.I)*Cp/sp.sqrt(2)
        D = sp.simplify(sp.re(Ec)-sp.re(Ac)*sp.im(Ac).inv()*sp.im(Ec))
        assert sp.simplify(D-expected_D) == sp.zeros(3)

    f,g,d = sp.symbols('f g d')
    H = sp.Matrix([[0,0,1],[0,2,2],[1,2,-1]])
    B = sp.Matrix([f+d/2,g,f-d/2])
    residual = sp.factor((B.T*expected_D.T*H*B)[0]/sp.sqrt(2)
                         -(d*d/4-(f+g)*(f+3*g)))
    assert residual == 0

    # Verify the complete Landen numerator change and both IBP polynomials.
    w, wb, area, area_t = sp.symbols('w wb area area_t')
    z = 4*w/(1+w)**2
    area_z_value = (1+w)*(1+wb)*area/2
    area_z_derivative = (1+w)**3/(4*(1-w))*((1+wb)*area/2
                            +w*(1+w)*(1+wb)*area_t)
    root = (1-w)/(1+w)
    alphas = ((z-1+root)/2,(z-1-root)/2,z/4)
    targets = (-w*w*(1-w)*(1+wb)*area_t,
               -(1-w)*(1+wb)*(area/2+w*w*area_t),
               w*w*(1+wb)/(1+w)*(area/2-(1-w*w)*area_t))
    landen_residuals = [sp.factor(alpha*area_z_value-z*(1-z)*area_z_derivative-target)
                       for alpha,target in zip(alphas,targets)]
    assert landen_residuals == [0,0,0]
    u = sp.symbols('u',positive=True)
    d1 = sp.expand((2+5*t)*(2+5*u)
                   -(14+35*t*u-10*(1-t)*(1-u)))
    assert d1 == 0
    W = (t*u)**sp.Rational(-1,2)*(1-t)*(1-u)
    d0 = sp.factor(W/4+(sp.diff(W*(1-t),t)+sp.diff(W*(1-u),u))/4
                   +sp.diff(W*(1-t)*(1-u),t,u)/4
                   -(t*u)**sp.Rational(-3,2)*(1-t)*(1-u)*(1+t)*(1+u)/16)
    assert d0 == 0
    return {'boundary_differential_certificate_residuals':[str(x) for x in certificate],
            'cut_jump_matrix_residual':str(jump),
            'contour_reflection_matrix':str(expected_D),
            'symmetric_period_factorization_residual':str(residual),
            'Landen_numerator_residuals':[str(x) for x in landen_residuals],
            'D1_polynomial_residual':str(d1),'D0_IBP_residual':str(d0)}


def numerical_checks(dps):
    mp.mp.dps = dps
    epsilon = mp.power(10, -(dps-10))
    plus_errors, minus_errors = [], []
    for t in map(mp.mpf, ('1.2','2','5')):
        k, kc = mp.ellipk(1/t), mp.ellipk(1-1/t)
        for sign, bucket in ((1,plus_errors),(-1,minus_errors)):
            bucket.append(abs(mp.ellipk(t+sign*mp.j*epsilon)
                              -(k+sign*mp.j*kc)/mp.sqrt(t)))
    negative_errors = []
    for u in map(mp.mpf, ('.2','.4','.7')):
        t = -u/(1-u)
        negative_errors.append(abs(mp.ellipk(1-(t+mp.j*epsilon))
                                   -mp.sqrt(1-u)*(mp.ellipk(1-u)-mp.j*mp.ellipk(u))))
    area_errors, wronskian_errors, transformed_errors = [], [], []
    def area(z):
        return 16*mp.re(mp.conj(mp.ellipk(z))*mp.ellipk(1-z))
    def kp(z):
        return (mp.ellipe(z)-(1-z)*mp.ellipk(z))/(2*z*(1-z))
    for z in (mp.mpc('.2','.1'),mp.mpc('-.3','.2'),mp.mpc('.1','-.25')):
        lhs = area(4*z/(1+z)**2)
        rhs = abs(1+z)**2*area(z*z)/2
        area_errors.append(abs(lhs-rhs)/max(1,abs(lhs),abs(rhs)))
        k,kc = mp.ellipk(z),mp.ellipk(1-z)
        dk,dkc = kp(z),-kp(1-z)
        at = 8*(dk*mp.conj(kc)+dkc*mp.conj(k))
        attbar = 8*(dk*mp.conj(dkc)+dkc*mp.conj(dk))
        lhs = abs(at)**2-area(z)*attbar
        rhs = 4*mp.pi**2/abs(z*(1-z))**2
        wronskian_errors.append(abs(lhs-rhs)/max(1,abs(lhs),abs(rhs)))
        # Here z plays the role of w in the Landen transformation.
        w = z
        zz, tt = 4*w/(1+w)**2,w*w
        az, atval = area(zz),area(tt)
        akt = 8*(kp(tt)*mp.conj(mp.ellipk(1-tt))-kp(1-tt)*mp.conj(mp.ellipk(tt)))
        kk = mp.ellipk(zz)
        qq = mp.ellipe(zz)/(4*kk)-(2-zz)/12-mp.pi*mp.conj(kk)/(kk*az)
        rt = mp.sqrt(1-zz)
        wp = abs(1+rt)/(2*abs(zz)**mp.mpf('.25')*abs(1-zz)**mp.mpf('.25'))
        wm = abs(1-rt)/(2*abs(zz)**mp.mpf('.25')*abs(1-zz)**mp.mpf('.25'))
        w0 = abs(zz)**mp.mpf('-.25')
        cp,cm,c0 = (zz-2+3*rt)/6,(zz-2-3*rt)/6,(2-zz)/12
        original = abs(zz)**mp.mpf('-3.75')*az*az/4*(wp*abs(cp-2*qq)**2
                                    +wm*abs(cm-2*qq)**2-w0*abs(c0-2*qq)**2)
        jacobian = 16*abs(1-w)**2/abs(1+w)**6
        original_t_density = original*jacobian/(4*abs(tt))
        transformed = (abs(tt)**-1*abs(1-tt)**mp.mpf('3.5')*abs(akt)**2
          +abs(tt)**mp.mpf('-2.5')*abs(1-tt)**mp.mpf('3.5')*abs(atval/2+tt*akt)**2
          -abs(tt)**-1*abs(1-tt)**2*abs(atval/2-(1-tt)*akt)**2)/256
        transformed_errors.append(abs(original_t_density-transformed)
                    /max(1,abs(original_t_density),abs(transformed)))
    assert max(plus_errors+minus_errors+negative_errors)<100*epsilon
    assert max(area_errors+wronskian_errors+transformed_errors)<mp.power(10,-dps+8)
    return {'working_digits':dps,'boundary_displacement':mp.nstr(epsilon,dps),
            'upper_boundary_max_absolute_difference':mp.nstr(max(plus_errors),12),
            'lower_boundary_max_absolute_difference':mp.nstr(max(minus_errors),12),
            'negative_cut_max_absolute_difference':mp.nstr(max(negative_errors),12),
            'Landen_area_max_relative_difference':mp.nstr(max(area_errors),12),
            'area_Wronskian_max_relative_difference':mp.nstr(max(wronskian_errors),12),
            'full_Landen_integrand_max_relative_difference':mp.nstr(max(transformed_errors),12)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dps',type=int,default=50)
    parser.add_argument('--json',type=Path)
    args=parser.parse_args()
    if args.dps<30:
        parser.error('Use at least 30 working digits.')
    result={'scope':'Exact algebra and pointwise elliptic checks; not global quartic integration.',
            'exact':exact_checks(),'numerical':numerical_checks(args.dps)}
    output=json.dumps(result,indent=2)
    print(output)
    if args.json:
        args.json.parent.mkdir(parents=True,exist_ok=True)
        args.json.write_text(output+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
