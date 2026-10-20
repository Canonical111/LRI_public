"""Evaluate the four fixed bivariate H-values through their proven beta pairing.

This is floating-point quadrature, not interval arithmetic. The beta pairing
contains standard univariate Meijer G functions. For stable numerical work,
we use their proven Gauss connection formulas and cross-check against
mpmath.meijerg at independent interior points.
"""
from __future__ import annotations
import argparse
from functools import lru_cache
import json
from pathlib import Path
import time
import mpmath as mp


def run(dps: int = 50) -> dict:
    if dps < 25:
        raise ValueError('Use at least 25 decimal working digits.')
    mp.mp.dps = dps
    q=mp.mpf(1)/4; half=mp.mpf(1)/2
    pi=mp.pi; rtpi=mp.sqrt(pi); Q=mp.gamma(q)**4/pi
    rootQ=mp.sqrt(Q); ell=mp.log(2)
    t0=time.monotonic()

    def reflected_h_scaled(x):
        # sqrt(Q)*h(1-x), evaluated WITHOUT forming 1-x.
        n=0; coeff=mp.mpf(1); bracket=-mp.log(x)+pi+6*ell
        total=coeff*bracket
        while True:
            coeff *= x*((n+q)/(n+1))**2
            bracket += 2/mp.mpf(n+1)-2/(n+q)
            n += 1
            term=coeff*bracket
            total += term
            if abs(term) < mp.eps*abs(total)/16:
                return total
            if n > 20*dps+200:
                raise ArithmeticError('Reflected Gauss expansion did not converge.')

    @lru_cache(maxsize=None)
    def kernels(x):
        # Return G_j(x), G_j(1-x), p_i(x), p_i(1-x); 0<x<=1/2.
        f=mp.hyp2f1(q,q,1,x)
        d=reflected_h_scaled(x)
        h=mp.hyp2f1(q,q,half,x)
        u=mp.hyp2f1(q+half,q+half,mp.mpf('1.5'),x)
        vstar=rootQ*h/(2*pi)-2*mp.sqrt(x)*u/rootQ
        dstar=rootQ*h
        ps=(f*f,f*d,d*d)
        pt=(vstar*vstar,vstar*dstar,dstar*dstar)
        left=(rtpi*ps[0],(ps[1]-pi*ps[0])/rtpi,
              (ps[2]-2*pi*ps[1])/(2*pi*rtpi))
        right=(rtpi*pt[0],vstar*(dstar-pi*vstar)/rtpi,
               2*mp.sqrt(x)*h*u/rtpi)
        return left,right,ps,pt

    def bivariate(j,k):
        def integrand(t):
            if t == 0: return mp.mpf(0)
            x=t**4/2
            left,right,_,_=kernels(x)
            jac=2*mp.sqrt(2)*t/mp.sqrt(1-x)
            return jac*(left[j-1]*right[k-1]+left[k-1]*right[j-1])
        return mp.quad(integrand,[0,mp.mpf('0.125'),mp.mpf('0.5'),1])

    vals={}
    for j,k in [(1,1),(1,2),(2,2),(2,3),(1,3),(3,3)]:
        vals[f'{j}{k}']=bivariate(j,k)
    pa_new=8*pi**3*(10*vals['11']+21*vals['12']+18*vals['22']+15*vals['23'])
    def original_integrand(t):
        if t == 0: return mp.mpf(0)
        x=t**4/2
        _,_,p,r=kernels(x)
        num=15*p[2]*r[2]+24*pi*pi*p[1]*r[1]-4*pi**4*p[0]*r[0]
        return 4*mp.sqrt(2)*t/mp.sqrt(1-x)*num
    pa_old=mp.quad(original_integrand,[0,mp.mpf('0.125'),mp.mpf('0.5'),1])
    # Inherited rational midpoint, used ONLY after evaluating the new values.
    cert=json.loads((Path(__file__).parent/'inputs'/'complete_interval_certificate.json').read_text())
    ref=cert['weighted_parts_in_C6_units']['primitive']
    with mp.workdps(dps+30):
        inherited=(mp.mpf(ref['lower_numerator'])+mp.mpf(ref['upper_numerator']))/2**(ref['denominator_power_of_two']+1)*mp.mpf(2187)/96

    point_errors=[]
    for x in [mp.mpf('0.01'),mp.mpf('0.1'),mp.mpf('0.25'),mp.mpf('0.5')]:
        left,right,_,_=kernels(x)
        for xx,expected in [(x,left),(1-x,right)]:
            for j in [1,2,3]:
                got=mp.meijerg([[half]*(3-j),[half]*j],[[0]*j,[0]*(3-j)],xx)
                point_errors.append(abs(got-expected[j-1]))
    fmt=lambda a:mp.nstr(a,dps)
    report={
        'working_decimal_digits':dps,
        'method':'Beta pairing of univariate Meijer G; stable Gauss connection implementation. Floating-point, not certified.',
        'values':{k:fmt(v) for k,v in vals.items()},
        'primitive_new':fmt(pa_new),
        'primitive_original_symmetric_integral':fmt(pa_old),
        'primitive_replacement_absolute_residual':fmt(abs(pa_new-pa_old)),
        'primitive_vs_inherited_rational_midpoint_absolute_difference':fmt(abs(pa_new-inherited)),
        'inherited_comparison':'Rational midpoint from complete certificate; used only for comparison, not quadrature.',
        'pairing_identity_absolute_residual':fmt(abs(vals['33']+2*vals['13']-vals['22'])),
        'new_C6_minus_old_C6_from_primitive':fmt(96*(pa_new-pa_old)/2187),
        'meijerg_point_checks':len(point_errors),
        'maximum_meijerg_point_absolute_difference':fmt(max(point_errors)),
        'seconds':time.monotonic()-t0,
        'new_interval_certificate':False,
        'new_full_C6_numerical_evaluation':False
    }
    out=Path(__file__).parent/'results'/f'numerical_{dps}.json'
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--digits',type=int,default=50)
    run(parser.parse_args().digits)
