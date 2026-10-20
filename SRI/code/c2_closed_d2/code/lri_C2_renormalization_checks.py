#!/usr/bin/env python3
"""Checks supporting the analytic-MS renormalization proof for 2d LRI C2.

These are algebraic and numerical checks, NOT a numerical integration of the
full regulated six-point distribution. The completeness argument is in the
companion TeX/PDF. No network access or data files are needed.

Dependencies: mpmath; SymPy only with --symbolic.
Usage: python lri_C2_renormalization_checks.py --dps 50 --symbolic --json checks.json
"""
from __future__ import annotations
import argparse
from itertools import combinations
import json
from pathlib import Path
import mpmath as mp


def finite_spin_energy(points, x=None, y=None):
    """S_(2n), and H_(2n) with two finite energy positions when x,y supplied."""
    z = [mp.mpc(v) for v in points]
    if len(z) % 2 or len(set(z)) != len(z):
        raise ValueError('Require an even number of distinct spin positions.')
    if x is not None and (y is None or x == y or x in z or y in z):
        raise ValueError('Require distinct finite energy and spin positions.')
    ss, hh = [], []
    for plus in combinations(range(len(z)),len(z)//2):
        e = [1 if i in plus else -1 for i in range(len(z))]
        w = mp.fprod(abs(z[i]-z[j])**(mp.mpf(e[i]*e[j])/2)
                     for i in range(len(z)) for j in range(i))
        ss.append(w)
        if x is not None:
            p = 1/(x-y)**2+mp.fsum(e[i]/(x-z[i]) for i in range(len(z)))*mp.fsum(e[i]/(y-z[i]) for i in range(len(z)))/4
            hh.append(w*abs(p)**2)
    norm = 2**(len(z)//2)
    s = mp.sqrt(mp.fsum(ss)/norm)
    return (s,mp.sqrt(mp.fsum(hh)/norm)) if x is not None else s


def S2(a,b):
    return abs(a-b)**(-mp.mpf(1)/4)


def H2(a,b):
    return S2(a,b)*abs(a+b)**2/(4*abs(a*b))


def connected_F(points):
    """Exact two-block formula; energies at 0 and infinity."""
    a,b,c,d = points
    x=(a-b)*(c-d)/((a-d)*(c-b))
    A=(1-x)**(mp.mpf(1)/4); B=1/A
    U=a*c+b*d; V=a*d+b*c
    pref=abs((a-b)*(c-d))**(-mp.mpf(1)/4)
    s=pref/2*(abs(A+B)+abs(A-B))
    h=pref/(8*abs(a*b*c*d))*(abs(A*U+B*V)**2/abs(A+B)
                            +abs(A*U-B*V)**2/abs(A-B))
    return h-s-H2(a,b)*H2(c,d)+S2(a,b)*S2(c,d)


def canonical_SH(z,x,y):
    """Bosonization with spins exactly at 0,z,1,infinity: no large-R limit."""
    points=[mp.mpc(0),z,mp.mpc(1)]
    ss,hh=[],[]
    for plus in combinations(range(4),2):
        e=[1 if i in plus else -1 for i in range(4)]
        w=mp.fprod(abs(points[i]-points[j])**(mp.mpf(e[i]*e[j])/2)
                   for i in range(3) for j in range(i))
        qx=mp.fsum(e[i]/(x-points[i]) for i in range(3))
        qy=mp.fsum(e[i]/(y-points[i]) for i in range(3))
        p=1/(x-y)**2+qx*qy/4
        ss.append(w);hh.append(w*abs(p)**2)
    return mp.sqrt(mp.fsum(ss)/4),mp.sqrt(mp.fsum(hh)/4)


def canonical_G(z,x,y):
    s,h=canonical_SH(z,x,y)
    s12,h12=finite_spin_energy([mp.mpc(0),z],x,y)
    # For the second pair sigma(1),sigma(infinity), S34=1 exactly.
    h34=abs(1/(x-y)**2+1/(4*(x-1)*(y-1)))
    return h/abs(x-y)**2-s/abs(x-y)**4-h12*h34+s12/abs(x-y)**4


def elliptic_algebraic_G(z,x,y):
    """Independently use Weierstrass addition identities in algebraic coordinates."""
    t=mp.sqrt(1-z)
    wp=abs(1+t)/(2*abs(z)**mp.mpf('.25')*abs(1-z)**mp.mpf('.25'))
    wm=abs(1-t)/(2*abs(z)**mp.mpf('.25')*abs(1-z)**mp.mpf('.25'))
    w0=abs(z)**(-mp.mpf('.25'))
    cp=(z-2+3*t)/6; cm=(z-2-3*t)/6; c0=(2-z)/12
    shift=(1+z)/3
    px=x*(x-z)*(x-1);py=y*(y-z)*(y-1)
    summ=-(x+y-2*shift)/2+(px+py)/(2*(x-y)**2)
    diffsq=abs(px*py)/abs(x-y)**4
    return (wp*abs(summ+cp)**2+wm*abs(summ+cm)**2-w0*abs(summ+c0)**2
            -(wp+wm-w0)*diffsq)/abs(px*py)


def coefficient():
    q=mp.mpf(1)/4;h=2*q
    R=mp.gamma(q)/mp.gamma(3*q)
    P=mp.hyper([-h,-h,3*h,3*q],[1,2,q],1)
    Q=mp.hyper([h,3*h,3*h,9*q],[3,3,7*q],1)
    T=mp.hyper([3*h,-q,3*q,3*q],[q,9*q,9*q],1)
    C=16/R**2-R**2/9-mp.pi**2*R**2/16*(P-5*R**2*Q/384)*(P-5*R**2*Q/128-512*T/(25*mp.pi*R**2))
    b=9*mp.pi**2/(8*R**2)
    # Derived quantities; these do not constitute independent numerical checks.
    I=-4*b*b*C/mp.pi-mp.pi*b
    B=mp.pi**2/96*(12-mp.pi*mp.sqrt(3)-9*mp.log(3))
    z41=-C*b*b/4
    return dict(P=P,Q=Q,T=T,b0=b,C2=C,I=I,B31=B,Abr=4*B-mp.pi**2/4,
                J0=I-16*b*B/mp.pi+mp.pi*b,z41=z41,h0=-4*z41)


def symbolic_checks():
    import sympy as s
    a,x,y,z=s.symbols('a x y z')
    points=s.Matrix([a*x/y,a*(z-x)/(z-y),a*(1-x)/(1-y),a])
    jac=points.jacobian([a,x,y,z]).det(method='domain-ge')
    expect=-a**3*(x-y)**2/(y**2*(y-1)**2*(y-z)**2)
    residual=s.factor(jac-expect)
    assert residual==0
    u,v=s.symbols('u v')
    linear=s.Matrix([u-v,u+v]).jacobian([u,v]).det()
    assert linear==2
    return dict(Mobius_Jacobian_residual=str(residual),Abel_linear_complex_determinant=str(linear))


def checks(dps):
    mp.mp.dps=dps
    points=[
        (mp.mpc('.3','.4'),mp.mpc('-.7','.2'),mp.mpc('1.4','-.6')),
        (mp.mpc('-.6','.8'),mp.mpc('.8','.3'),mp.mpc('-1.2','-.5')),
        (mp.mpc('1.3','-.2'),mp.mpc('.1','1.1'),mp.mpc('-.9','.4')),
    ]
    errors=[]
    for z,x,y in points:
        direct=canonical_G(z,x,y);cover=elliptic_algebraic_G(z,x,y)
        errors.append(abs(direct-cover)/max(abs(direct),abs(cover),mp.mpf('1e-20')))
    assert max(errors)<mp.power(10,-dps+8)

    a=mp.mpc('.3','.5'); b=mp.mpc('-.7','.2')
    c=mp.mpc('1.1','.3'); d=mp.mpc('-.4','1.3')
    ident=abs(a-b)**mp.mpf('.75')*abs(c-d)**mp.mpf('.75')/(4*abs(a*b))
    projections=[]
    for k in [2,3,4,5,6]:
        l=mp.mpf(10)**(-k)
        remainder=connected_F([l*a,l*b,c,d])-ident*l**(-mp.mpf('1.25'))
        projections.append(dict(lambda_value=l,log_projection=remainder*l**mp.mpf('.25'),
                                first_integrable_projection=remainder/l**mp.mpf('.75')))
    # If the logarithmic term survived, log_projection would tend to a
    # nonzero constant. Here it falls by one power of lambda.
    ratios=[abs(projections[j+1]['log_projection']/projections[j]['log_projection']) for j in range(4)]
    assert all(mp.mpf('.09')<r<mp.mpf('.11') for r in ratios)

    Bdirect=mp.pi**2/8-mp.pi**2/2*mp.quad(lambda r:3/((1+r)**2*(r*r+3))
                                        -3*r*r/((1+r)**2*(1+3*r*r)),[0,1])
    Bclosed=mp.pi**2/96*(12-mp.pi*mp.sqrt(3)-9*mp.log(3))
    assert abs(Bdirect-Bclosed)<mp.power(10,-dps+8)
    return dict(working_digits=dps,pointwise_cover_relative_error=max(errors),
                B31_quadrature_residual=abs(Bdirect-Bclosed),external_OPE=projections,
                log_projection_ratios=ratios,coefficient_values=coefficient())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dps',type=int,default=50)
    parser.add_argument('--symbolic',action='store_true')
    parser.add_argument('--json',type=Path)
    args=parser.parse_args()
    if args.dps<35:parser.error('Use at least 35 digits for cancellation-sensitive OPE checks.')
    out=checks(args.dps)
    if args.symbolic:out['symbolic']=symbolic_checks()
    def convert(v):
        if isinstance(v,dict):return {k:convert(x) for k,x in v.items()}
        if isinstance(v,list):return [convert(x) for x in v]
        if isinstance(v,(mp.mpf,mp.mpc)):return mp.nstr(v,args.dps-8)
        return v
    out=convert(out)
    text=json.dumps(out,indent=2)
    print(text)
    if args.json:args.json.write_text(text+'\n',encoding='utf-8')

if __name__=='__main__':main()
