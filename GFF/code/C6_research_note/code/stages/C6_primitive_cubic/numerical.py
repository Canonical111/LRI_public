"""Independent floating-point checks of the contour and cubic reduction.

No numerical relation search is used here. The coefficients are fixed by the
analytic proof and exact algebra in DERIVATION.md / verify.py.
"""
from __future__ import annotations
import argparse
from functools import lru_cache
import json
from pathlib import Path
import time
import mpmath as mp
from series import harmonic_data, cubic_polynomial

ROOT=Path(__file__).resolve().parent

def run(working_digits: int) -> dict:
    if working_digits < 35:
        raise ValueError('At least 35 working digits are required for these checks.')
    with mp.workdps(working_digits):
        q=mp.mpf('0.25');half=mp.mpf('0.5');p=mp.pi
        ell=mp.log(2);Q=mp.gamma(q)**4/p;sqrtQ=mp.sqrt(Q)

        @lru_cache(None)
        def kernels(y):
            # Values of q_i=p_i/pi^i at t=y^2 and 1-t.
            if not y:
                return [mp.mpf(0)]*3,[mp.mpf(0)]*3
            t=y*y
            h=mp.hyp2f1(q,q,half,t)
            v=mp.hyp2f1(q,q,1,t)
            g0=mp.hyp2f1(3*q,3*q,3*half,t)
            vb=sqrtQ*h/(2*p)-2*y*g0/sqrtQ
            if t > mp.mpf('1e-10'):
                hb=mp.hyp2f1(q,q,half,1-t)
            else:
                # Zero-balanced connection: avoids rounding 1-t to 1.
                coeff=power=mp.mpf(1)
                d=p+6*ell;hb=mp.mpf(0);lt=mp.log(t)
                for n in range((working_digits+30)//10+5):
                    hb+=coeff*power*(d-lt)
                    coeff*=(n+q)**2/(n+1)**2
                    d+=mp.mpf(2)/(n+1)-2/(n+q)
                    power*=t
                hb/=sqrtQ
            return ([v*v,sqrtQ/p*v*hb,Q/p**2*hb*hb],
                    [vb*vb,sqrtQ/p*vb*h,Q/p**2*h*h])

        endpoint=1/mp.sqrt(2)
        cuts=[0,endpoint/4,endpoint/2,endpoint]
        I={}
        start=time.time()
        for i in range(3):
            for j in range(i,3):
                def integrand(y):
                    f,g=kernels(y)
                    return 2*(f[i]*g[j]+f[j]*g[i])/mp.sqrt(1-y*y)
                I[f'{i}{j}']=mp.quad(integrand,cuts)
        relation=I['22']-4*I['12']+4*I['02']-4*I['00']
        pa_old=p**4*(15*I['22']+24*I['11']-4*I['00'])
        pa_new=p**4*(60*I['12']-60*I['02']+24*I['11']+56*I['00'])
        ref=json.loads((ROOT/'inputs/primitive_reference.json').read_text())['Pa']
        midpoint=(mp.mpf(ref['lower_numerator'])+mp.mpf(ref['upper_numerator']))/mp.power(
            2,ref['denominator_power_of_two']+1)

        # Direct beta integration of the cubic logarithmic polynomial,
        # without using the Gauss pairing quadrature.
        pairs=[(0,0),(0,2),(1,1),(2,5),(6,9)]
        data=harmonic_data(max(m+n for m,n in pairs))
        _,h,delta,_=data
        beta_checks=[]
        for m,n in pairs:
            def poly(L,K):
                bm=L+p+6*h[m];bn=K+p+6*h[n]
                qm=bm*bm+3*delta[m]-p*p
                qn=bn*bn+3*delta[n]-p*p
                return (30*p*((bm-p)*qn+(bn-p)*qm)
                        +24*p*p*bm*bn+56*p**4)
            def integrand(y):
                if not y:return mp.mpf(0)
                t=y*y;L=-mp.log(t);K=-mp.log1p(-t)
                return 2*(t**m*(1-t)**(n-half)*poly(L,K)
                          +t**n*(1-t)**(m-half)*poly(K,L))
            expectation=mp.quad(integrand,cuts)/mp.beta(m+half,n+half)
            target=2*p*cubic_polynomial(m,n,data)
            beta_checks.append({'m':m,'n':n,'absolute_difference':mp.nstr(abs(expectation-target),10)})

        # Check the sign of the limiting branch behavior on both exterior
        # intervals; finite epsilon means this is not a zero-residual proof.
        eps=mp.power(10,-working_digits//2)
        def fg(z):
            f=mp.hyp2f1(q,q,1,z)
            g=sqrtQ/p*mp.hyp2f1(q,q,half,1-z)-f
            return f,g
        boundary=[]
        for x in [mp.mpf('-10'),mp.mpf('-2'),mp.mpf('-0.125'),
                  mp.mpf('1.125'),mp.mpf('3'),mp.mpf('12')]:
            z=mp.mpc(x,eps)
            f,g=fg(z);F,G=fg(1-z)
            numerator=(g*g*G*G+g*g*F*F+f*f*G*G-4*f*g*F*G-3*f*f*F*F
                       +4j*(f*g*F*F-f*f*F*G))
            kernel=numerator/(mp.sqrt(z)*mp.sqrt(1-z))
            boundary.append({'x':str(x),'epsilon':mp.nstr(eps,5),
                             'abs_real_kernel':mp.nstr(abs(mp.re(kernel)),10),
                             'abs_real_kernel_over_epsilon':mp.nstr(abs(mp.re(kernel))/eps,10)})

        # A low-order coefficient check may lose some digits to endpoint
        # logarithms; these tolerances test implementation, not certify errors.
        tolerance=mp.power(10,-working_digits+12)
        if abs(pa_new-midpoint)>tolerance:
            raise ArithmeticError('Cubic pairing quadrature failed the reference check.')
        if abs(relation)>tolerance:
            raise ArithmeticError('Pairing relation failed the numerical check.')
        if any(mp.mpf(r['absolute_difference'])>tolerance for r in beta_checks):
            raise ArithmeticError('A cubic beta coefficient failed its check.')
        return {
            'working_digits':working_digits,
            'method':'mpmath tanh-sinh quadrature, folded at 1/2 with a stable Gauss connection at the logarithmic endpoint',
            'scope':'Floating-point cross-checks, not new rational interval certificates.',
            'pairings':{k:mp.nstr(v,working_digits) for k,v in I.items()},
            'relation_absolute_residual':mp.nstr(abs(relation),15),
            'Pa_old_pairings':mp.nstr(pa_old,working_digits),
            'Pa_cubic_pairings':mp.nstr(pa_new,working_digits),
            'PaCubic':mp.nstr(pa_new/(2*p*p),working_digits),
            'old_minus_new_absolute':mp.nstr(abs(pa_old-pa_new),15),
            'old_vs_inherited_midpoint_absolute':mp.nstr(abs(pa_old-midpoint),15),
            'cubic_vs_inherited_midpoint_absolute':mp.nstr(abs(pa_new-midpoint),15),
            'changed_C6_contribution_vs_reference_absolute':mp.nstr(96*abs(pa_new-midpoint)/2187,15),
            'beta_moment_checks':beta_checks,
            'exterior_boundary_checks':boundary,
            'elapsed_seconds':time.time()-start,
        }

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--digits',type=int,default=70)
    args=parser.parse_args()
    result=run(args.digits)
    destination=ROOT/f'results/numerical_{args.digits}.json'
    destination.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['pairings','exterior_boundary_checks']},indent=2))
