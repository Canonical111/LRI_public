#!/usr/bin/env python3
"""Check compact and unity-argument P5 formulas with literal mpmath pFq calls.

No saved period, parameter derivative, limiting parameter or Cauchy extraction
is used. The reference is a fresh positive Gamma-moment quadrature. Reported
residuals are numerical consistency checks, NOT rigorous error enclosures.

    python code/verify_compact_unity.py --digits 80 --control-extra 20 \
        --output verification/compact_unity_checks.json

The two-value formulas count one complex pFq evaluation followed by its real
part as one value. Displaying that real part as an explicit conjugate sum
would show a third pFq occurrence, not an independent numerical evaluation.
Requires Python 3, mpmath, and sympy.
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
import mpmath as mp


def h_minus(z):
    q=mp.mpf(1)/4
    return mp.hyper([1,1+z]+[z+q]*7, [z]+[z+3*q]*7, -1)


def e_unity(z):
    """16F15(1); an upper/lower 1 cancels at z=1/4 or 5/4."""
    q=mp.mpf(1)/4
    return mp.hyper([1,1+z/2]+[(z+q)/2]*7+[(z+5*q)/2]*7,
                    [z/2]+[(z+3*q)/2]*7+[(z+7*q)/2]*7,1)


def d7(z):
    q=mp.mpf(1)/4
    return z*(z+3*q)**7-(z+1)*(z+q)**7


def d7_roots():
    """All seven roots, from a fixed cubic; square-root signs occur in pairs."""
    half=mp.mpf(1)/2
    u=mp.polyroots([20480,-1792,-784,-13],maxsteps=1000,extraprec=80)
    roots=[-half]
    for v in u:
        r=mp.sqrt(v)
        roots.extend([-half+r,-half-r])
    return u,roots


def u_unity(z,roots):
    """22F21(1); at z=1/4 a 1 cancels, giving a 21F20(1)."""
    q=mp.mpf(1)/4
    eta=[(z-r)/2 for r in roots]
    return mp.hyper([1]+[(z+q)/2]*7+[(z+5*q)/2]*7+[1+x for x in eta],
                    [(z+7*q)/2]*7+[(z+11*q)/2]*7+eta,1)


def h_from_e(z,e0,e1):
    q=mp.mpf(1)/4
    return e0-(z+1)/z*((z+q)/(z+3*q))**7*e1


def h_from_u(z,u):
    q=mp.mpf(1)/4
    return d7(z)/(z*(z+3*q)**7)*u


def p_from_h(h0,hr,rho):
    q=mp.mpf(1)/4
    rg=(mp.mpf(11)/(13*mp.pi))**7*abs(mp.gamma(q+1j*rho))**14
    return 8*mp.pi**mp.mpf('1.5')/11*(29*mp.pi**mp.mpf('3.5')/4*h0
        +mp.mpf(2197)*rho/(3*mp.sqrt(35))*rg*(2*mp.re(hr)-1))


def gamma_integrand(y):
    if not y: return mp.mpf(0)
    p=mp.pi*y
    bracket=(-mp.expm1(-12*p)+13*mp.exp(-2*p)*(-mp.expm1(-8*p))
             +29*mp.exp(-4*p)*(-mp.expm1(-4*p)))/2
    return y*mp.exp(14*mp.re(mp.loggamma(mp.mpf(1)/4+1j*y))+6*p)*bracket/mp.pi**mp.mpf('5.5')


def old_five_value():
    q=mp.mpf(1)/4
    def Y(r):
        z=mp.mpf(r)/8
        return z*(mp.gamma(z+q)/mp.gamma(z+3*q))**7*h_minus(z)
    ys={r:Y(r) for r in (1,2,3,5,7)}
    c=mp.cos(mp.pi/8);s=mp.sin(mp.pi/8)
    return 16*mp.pi**mp.mpf('1.5')*(-35*ys[2]
        +(22*mp.sqrt(2)-13)*(c**7*ys[3]-s**7*ys[5])
        +(22*mp.sqrt(2)+13)*(c**7*ys[1]+s**7*ys[7]))


def run(digits:int, alternate_breaks:bool=False):
    mp.mp.dps=digits
    enc=lambda x:mp.nstr(x,digits)
    started=time.time(); q=mp.mpf(1)/4
    rho=mp.acosh(mp.mpf(22)/13)/(2*mp.pi); z=1j*rho
    values={};times={}
    def compute(name,fn):
        st=time.time();v=fn();values[name]=v;times[name]=time.time()-st
        print(f'{digits} dps: {name} done in {times[name]:.2f}s',flush=True)
        return v
    h0=compute('h_quarter_minus',lambda:h_minus(q))
    hr=compute('h_i_rho_minus',lambda:h_minus(z))
    pminus=p_from_h(h0,hr,rho)
    es=[]
    for tag,w in [('quarter',q),('five_quarters',5*q),('i_rho',z),('one_plus_i_rho',1+z)]:
        es.append(compute('E_'+tag,lambda w=w:e_unity(w)))
    he0=h_from_e(q,es[0],es[1]);her=h_from_e(z,es[2],es[3])
    pe=p_from_h(he0,her,rho)
    cubic,roots=d7_roots()
    u0=compute('U_quarter',lambda:u_unity(q,roots))
    ur=compute('U_i_rho',lambda:u_unity(z,roots))
    hu0=h_from_u(q,u0);hur=h_from_u(z,ur)
    pu=p_from_h(hu0,hur,rho)
    if alternate_breaks:
        breaks=[mp.mpf(0),mp.mpf(1)/20,mp.mpf(1)/5,mp.mpf(3)/5,mp.mpf(3)/2,3,6,12,24,48,mp.inf]
    else:
        breaks=[mp.mpf(0),mp.mpf(1)/32,mp.mpf(1)/8,mp.mpf(1)/2,1,2,4,8,16,32,mp.inf]
    pg=compute('P5_gamma',lambda:mp.quad(gamma_integrand,breaks))
    old=compute('P5_old_five_values',old_five_value)
    rg=(mp.mpf(11)/(13*mp.pi))**7*abs(mp.gamma(q+z))**14
    def S(w):return w*(mp.gamma(w+q)/mp.gamma(w+3*q))**7*h_minus(w)
    t=-q+z
    xi_direct=mp.cos(mp.pi*t)**7*S(z)-mp.sin(mp.pi*t)**7*S(1-z)
    xi_reflected=1j*rho*rg*(2*mp.re(hr)-1)
    # The parameter root factors are checked without making them part of the reference.
    pair_checks=[]
    for w in (q,z):
        for n in (0,1,2,5,10):
            eta=[(w-r)/2 for r in roots]
            prod=mp.fprod(mp.rf(1+a,n)/mp.rf(a,n) for a in eta)
            pair_checks.append(abs(prod-d7(w+2*n)/d7(w)))
    result={
        'working_digits':digits,'rho':enc(rho),'rho_definition':'acosh(22/13)/(2*pi)',
        'P5_two_minus_one':enc(pminus),'P5_four_unity':enc(pe),'P5_two_unity':enc(pu),
        'P5_gamma':enc(pg),'P5_old_five_values':enc(old),
        'gamma_minus_two_minus_one':enc(pg-pminus),
        'gamma_minus_four_unity':enc(pg-pe),'gamma_minus_two_unity':enc(pg-pu),
        'old_five_minus_two_minus_one':enc(old-pminus),
        'four_unity_minus_two_minus_one':enc(pe-pminus),
        'two_unity_minus_two_minus_one':enc(pu-pminus),
        'individual_transform_residuals':{
          'E_quarter_to_h':enc(he0-h0),'E_i_rho_to_h':enc(her-hr),
          'U_quarter_to_h':enc(hu0-h0),'U_i_rho_to_h':enc(hur-hr),
          'Xi_complex_point':enc(xi_direct-xi_reflected)},
        'hypergeometric_values':{k:enc(v) for k,v in values.items() if k not in ('P5_gamma','P5_old_five_values')},
        'cubic_roots':list(map(enc,cubic)),'D7_roots':list(map(enc,roots)),
        'max_D7_root_residual':enc(max(abs(d7(r)) for r in roots)),
        'max_polynomial_Pochhammer_absolute_residual':enc(max(pair_checks)),
        'gamma_quadrature_breakpoints':list(map(enc,breaks)),
        'function_timings_seconds':times,'elapsed_seconds':time.time()-started
    }
    print(f'{digits} dps gamma - two at -1: {result["gamma_minus_two_minus_one"]}',flush=True)
    print(f'{digits} dps gamma - four at 1: {result["gamma_minus_four_unity"]}',flush=True)
    print(f'{digits} dps gamma - two at 1: {result["gamma_minus_two_unity"]}',flush=True)
    return result


def symbolic_checks():
    import sympy as sp
    a,b,c,s,x,w=sp.symbols('alpha beta gamma s x w')
    p=(a+c)+2*b*s-4*c*s**2
    assert sp.expand(sp.Rational(29,22)*p.subs(s,0)+sp.Rational(169,22)*p.subs(s,-sp.Rational(22,13))-(9*a-26*b-79*c))==0
    q=sp.Rational(1,4)
    poly=sp.expand(x*(x+3*q)**7-(x+1)*(x+q)**7)
    factor=w*(20480*w**6-1792*w**4-784*w**2-13)/8192
    assert sp.expand(poly.subs(x,w-sp.Rational(1,2))-factor)==0
    assert poly.subs(x,q)==sp.Rational(123,512)
    assert sp.simplify(poly.subs(x,q)/(q*(q+3*q)**7))==sp.Rational(123,128)
    assert sp.simplify((q+1)/q*((q+q)/(q+3*q))**7)==sp.Rational(5,128)
    return {'two_node_identity':True,'D7_shifted_factorization':True,
      'D7_quarter':'123/512','h_quarter_to_U_factor':'123/128',
      'h_quarter_odd_even_factor':'5/128',
      'excess_minus_one':'3/2','excess_four_unity':'3/2','excess_two_unity':'5/2',
      'all_degree_seven_roots_simple':sp.discriminant(poly,x)!=0}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--digits',type=int,default=80)
    ap.add_argument('--control-extra',type=int,default=20)
    ap.add_argument('--output',type=Path,default=Path('verification/compact_unity_checks.json'))
    args=ap.parse_args()
    if args.digits<30 or args.control_extra<0:ap.error('use digits >= 30 and control-extra >= 0')
    result={'mpmath_version':mp.__version__,
      'scope':'P5 special-function identities only. No graph integrals or RG counterterms rerun.',
      'saved_period_values_used':False,'parameter_derivatives_used':False,
      'parameter_limits_used':False,'Cauchy_coefficients_used':False,
      'rigorous_interval_enclosure':False,
      'two_value_count':'one real value and one complex value followed by Re; a conjugate need not be independently evaluated',
      'symbolic_checks':symbolic_checks()}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    result['base']=run(args.digits)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    if args.control_extra:
        result['higher_precision_control']=run(args.digits+args.control_extra,True)
        args.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Wrote',args.output,flush=True)

if __name__=='__main__':main()
