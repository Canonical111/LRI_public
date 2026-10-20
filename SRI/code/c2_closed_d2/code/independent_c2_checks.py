#!/usr/bin/env python3
"""Independent numerical/algebraic audit of the supplied 2D LRI expressions.

Adapted from stage 01 independent_checks.py; the cubic-order RG check was
omitted, and only the CLI/output routing changed otherwise.
No project module is imported. Dependencies: Python 3.10+, mpmath, numpy,
scipy and sympy. This checks formulas and local limits, NOT the complete
renormalized six-point integral. Floating-point results are not interval
certificates, even where an exact analytic series-tail inequality is proved.
"""
from __future__ import annotations
import itertools
import argparse
import json
from pathlib import Path
import time
import platform
import sys
import scipy
import mpmath as mp
import numpy as np
from scipy.special import roots_legendre
import sympy as sp

OUT = Path(__file__).resolve().parents[1]/"outputs"/"raw"
mp.mp.dps = 75


def encode(x):
    if isinstance(x, dict): return {str(k): encode(v) for k,v in x.items()}
    if isinstance(x, (list,tuple)): return [encode(v) for v in x]
    if isinstance(x, (mp.mpf,mp.mpc)): return mp.nstr(x,65)
    if isinstance(x, np.generic): return x.item()
    return x


def constants():
    q=mp.mpf(1)/4
    R=mp.gamma(q)/mp.gamma(3*q)
    P=mp.hyper([-2*q,-2*q,6*q,3*q],[1,2,q],1)
    Q=mp.hyper([2*q,6*q,6*q,9*q],[3,3,7*q],1)
    T=mp.hyper([6*q,-q,3*q,3*q],[q,9*q,9*q],1)
    b=9*mp.pi**2/(8*R**2)
    C=16/R**2-R**2/9-mp.pi**2*R**2/16*(P-5*R**2*Q/384)*(P-5*R**2*Q/128-512*T/(25*mp.pi*R**2))
    B=mp.pi**2*(12-mp.pi*mp.sqrt(3)-9*mp.log(3))/96
    return dict(R=R,P=P,Q=Q,T=T,b0=b,B31=B,C2_expression=C,
                C2_in_s_convention=C/4,contact_contribution=-mp.pi**2/(4*b))


def direct_period(a,cutoff=200):
    """Carlson quadrature after subtracting just the leading endpoint terms.
    This is not a coefficient/Frobenius-series evaluation.
    The upper u cutoff removes a convergent tail not rigorously bounded here.
    """
    a=mp.mpf(a)
    with mp.workdps(100):
        L=mp.log(32); scale=mp.power(2,-a)
        j0=scale/a
        j1=scale*(L/a+1/a**2)
        j2=scale*(L*L/a+2*L/a**2+2/a**3)
        def integrand(u,which):
            t=mp.exp(-u); ell=mp.log(16)+u
            k=mp.elliprf(0,1-t,1); kc=mp.elliprf(0,t,1)
            w=(1-t)**(a-1)
            rem=(w*(k*k+kc*kc)-(mp.pi**2+ell**2)/4 if which==0
                 else w*k*kc-mp.pi*ell/4)
            return mp.exp(-a*u)*rem
        pts=[mp.log(2),2,5,10,20,40,80,120,mp.mpf(cutoff)]
        # Gauss-Legendre integration, not the archived half-interval summation.
        urem=mp.quad(lambda x: integrand(x,0),pts,method='gauss-legendre')
        vrem=mp.quad(lambda x: integrand(x,1),pts,method='gauss-legendre')
        U=4/mp.pi**2*(urem+(mp.pi**2*j0+j2)/4)
        V=8/mp.pi**2*(vrem+mp.pi*j1/4)
        return U,V


def period_check(vals):
    um,vm=direct_period('-.25'); up,vp=direct_period('.75')
    f=mp.mpf('2.5')*um-4*up; g=mp.mpf('2.5')*vm-4*vp
    R=vals['R']; b=vals['b0']
    c=16/R**2-R**2/9-mp.pi*R**4*(f+g)*(f+3*g)/10368
    diff=c-vals['C2_expression']
    assert abs(diff)<mp.mpf('1e-50'),diff
    return dict(method='Leading-term-subtracted Carlson quadrature, u=-log(t), u<=200',
                U_minus=um,V_minus=vm,U_plus=up,V_plus=vp,f=f,g=g,
                C2_from_periods=c,discrepancy=diff,
                I_from_independent_periods=-4*b*b*c/mp.pi-mp.pi*b,
                status='Numerical comparison; no rigorous quadrature or cutoff bound')


def direct_series_tail_checks(vals,N=20000):
    """Exact tail inequalities, evaluated with ordinary arbitrary precision.
    For n>=1, tails of |t_n| are between (n/2+c_lo)|t_n| and
    (n/2+c_hi)|t_n|. Positivity certificates are checked symbolically.
    """
    h=sp.Rational(1,2);q=sp.Rational(1,4)
    specs={'P':([-h,-h,3*h,3*q],[1,2,q],0,1),
           'Q':([h,3*h,3*h,9*q],[3,3,7*q],1,2),
           'T':([3*h,-q,3*q,3*q],[q,9*q,9*q],0,1)}
    n,m=sp.symbols('n m', nonnegative=True)
    out={}
    for name,(a,b,lo,hi) in specs.items():
        rat=sp.prod(n+x for x in a)/((n+1)*sp.prod(n+x for x in b))
        certs={}
        for lab,c,sign in [('lower',lo,-1),('upper',hi,1)]:
            res=sp.factor(n/2+c-1-((n+1)/2+c)*rat)
            num,den=sp.fraction(sign*res)
            # Shift n=m+1; all coefficients nonnegative proves sign on n>=1.
            assert all(x>=0 for x in sp.Poly(sp.expand(num.subs(n,m+1)),m).all_coeffs())
            assert all(x>=0 for x in sp.Poly(sp.expand(den.subs(n,m+1)),m).all_coeffs())
            certs[lab]=str(res)
        aa=[mp.mpf(str(x.p)) / int(x.q) if hasattr(x,'p') else mp.mpf(x) for x in a]
        bb=[mp.mpf(str(x.p)) / int(x.q) if hasattr(x,'p') else mp.mpf(x) for x in b]
        term=mp.mpf(1); partial=mp.mpf(0)
        for k in range(N):
            partial+=term
            term*=mp.fprod(k+x for x in aa)/((k+1)*mp.fprod(k+x for x in bb))
        lower_tail=(mp.mpf(N)/2+lo)*abs(term)
        upper_tail=(mp.mpf(N)/2+hi)*abs(term)
        if term>0: low,high=partial+lower_tail,partial+upper_tail
        else: low,high=partial-upper_tail,partial-lower_tail
        assert low<vals[name]<high
        out[name]=dict(N=N,partial_sum=partial,first_omitted=term,
                       analytic_envelope_lower=low,analytic_envelope_upper=high,
                       width=high-low,certificates=certs)
    return out


def contact(p,M,n=180):
    """Direct 2D polar quadrature of the contact, no root factorization.
    The known Fourier coefficient of log|1-r exp(i theta)|^2 is integrated
    analytically; the remaining smooth logarithm is quadratured directly.
    """
    nodes,weights=roots_legendre(n)
    r=(nodes+1)/2; wr=weights/2
    th=np.pi*(nodes+1); wt=np.pi*weights
    co=np.cos(th)[None,:]
    rr=r[:,None]
    ap=1+rr*rr+2*rr*co; am=1+rr*rr-2*rr*co
    logd=np.log(ap**(2*p)+M*am**(2*p))
    # Radial-only subtraction makes the small-r angular integration stable.
    logd-=np.log((1+M)*(1+rr*rr)**(2*p))
    angular=np.sum(wt[None,:]*np.cos(2*th)[None,:]*logd,axis=1)
    A=-np.pi**2/4-np.pi/(2*p)*np.dot(wr,angular/r)
    integ=np.dot(wr,(1/(1+M*r**(2*p))-r**(2*p)/(r**(2*p)+M))/(1+r)**2)
    B=np.pi**2/8-np.pi**2*integ/2
    return dict(p=p,M=M,order=n,A_direct=A,B_direct=B,residual=A-4*B+np.pi**2/4)


def spin_energy(z,x=None,y=None):
    """Neutral-charge bosonization, with finite energy coordinates."""
    z=[mp.mpc(t) for t in z]; k=len(z)//2
    sw=mp.mpf(0); hw=mp.mpf(0)
    for plus in itertools.combinations(range(len(z)),k):
        charges=[mp.mpf(1) if j in plus else mp.mpf(-1) for j in range(len(z))]
        wt=mp.fprod(abs(z[i]-z[j])**(charges[i]*charges[j]/2)
                    for i in range(len(z)) for j in range(i))
        sw+=wt
        if x is None:
            factor=1-mp.fsum(e*t for e,t in zip(charges,z))*mp.fsum(e/t for e,t in zip(charges,z))/4
        else:
            factor=1/(x-y)**2+mp.fsum(e/(x-t) for e,t in zip(charges,z))*mp.fsum(e/(y-t) for e,t in zip(charges,z))/4
        hw+=wt*abs(factor)**2
    return mp.sqrt(sw/(2**k)),mp.sqrt(hw/(2**k))


def connected(z):
    s,h=spin_energy(z)
    s12,h12=spin_energy(z[:2]);s34,h34=spin_energy(z[2:])
    return h-s-h12*h34+s12*s34


def canonical_G(z,x,y):
    # Take the fourth spin to infinity analytically in the charge sum.
    v=[mp.mpc(0),z,mp.mpc(1)];sw=mp.mpf(0);hw=mp.mpf(0)
    for plus in itertools.combinations(range(4),2):
        charges=[mp.mpf(1) if j in plus else mp.mpf(-1) for j in range(4)]
        wt=mp.fprod(abs(v[i]-v[j])**(charges[i]*charges[j]/2)
                    for i in range(3) for j in range(i))
        qx=mp.fsum(charges[i]/(x-v[i]) for i in range(3))
        qy=mp.fsum(charges[i]/(y-v[i]) for i in range(3))
        sw+=wt;hw+=wt*abs(1/(x-y)**2+qx*qy/4)**2
    S=mp.sqrt(sw/4);H=mp.sqrt(hw/4)
    S12,H12=spin_energy([mp.mpc(0),z],x,y)
    H34=abs(1/(x-y)**2+1/(4*(x-1)*(y-1)))
    return H/abs(x-y)**2-(S-S12)/abs(x-y)**4-H12*H34


def coordinate_and_OPE_checks():
    params=[(mp.mpc('.7','.2'),mp.mpc('.23','.41'),mp.mpc('-.6','.3'),mp.mpc('1.2','-.5')),
            (mp.mpc('-.8','.4'),mp.mpc('-.43','.19'),mp.mpc('.2','1.1'),mp.mpc('1.5','.6'))]
    errors=[]
    for a,z,x,y in params:
        w=[a*x/y,a*(z-x)/(z-y),a*(1-x)/(1-y),a]
        F=connected(w);G=canonical_G(z,x,y)
        Y=abs(y*(y-z)*(y-1))
        R=abs(x/y)**2+abs((z-x)/(z-y))**2+abs((1-x)/(1-y))**2+1
        jac=abs(a)**6*abs(x-y)**4/Y**4
        for d in map(mp.mpf,['-.1','0','.17','.6']):
            k=-mp.mpf(15)/4+2*d
            original=jac*mp.exp(-mp.fsum(abs(t)**2 for t in w))*(abs(w[0]-w[1])*abs(w[2]-w[3]))**k*F
            changed=abs(a)**(-2+4*d)*mp.exp(-abs(a)**2*R)*abs(z)**k*(abs(x-y)**2/Y)**(2*d)*G
            err=abs(original-changed)/max(abs(original),abs(changed))
            assert err<mp.mpf('1e-65')
            errors.append(dict(delta=d,relative_error=err))
    a,b,c,d=(mp.mpc('.3','.5'),mp.mpc('-.7','.2'),
               mp.mpc('1.1','.3'),mp.mpc('-.4','1.3'))
    lead=abs(a-b)**mp.mpf('.75')*abs(c-d)**mp.mpf('.75')/(4*abs(a*b))
    rows=[]
    for k in [2,3,4,5,6]:
        lam=mp.power(10,-k)
        projected=lam**mp.mpf('.25')*connected([lam*a,lam*b,c,d])-lead/lam
        rows.append(dict(lam=lam,putative_log_projection=projected,projection_over_lam=projected/lam))
    assert all(mp.mpf('.09')<abs(rows[i+1]['putative_log_projection']/rows[i]['putative_log_projection'])<mp.mpf('.11') for i in range(4))
    return dict(full_regulated_density_change_of_variables=errors,external_OPE=rows)


def corner_check():
    """A local check of the double-energy shrinking-pair corner, not a
    uniform/nested-sector proof. Angular mean has no order-r scalar term."""
    xi=mp.mpc('.24','.51'); eta=mp.mpc('-.61','.27'); delta=mp.mpf('.073')
    def angular_mean(r):
        vals=[]
        for j in range(24):
            z=r*mp.exp(2j*mp.pi*j/24);x=z*xi;y=z*eta
            R=abs(x/y)**2+abs((z-x)/(z-y))**2+abs((1-x)/(1-y))**2+1
            W=abs(x-y)**2/(abs(y*(y-z)*(y-1))*R)
            vals.append(r**mp.mpf('3.25')*canonical_G(z,x,y)*W**(2*delta))
        return mp.fsum(vals)/len(vals)
    rs=[mp.mpf('0.001'),mp.mpf('0.0005'),mp.mpf('0.00025'),mp.mpf('0.000125')]
    means=[angular_mean(r) for r in rs]
    slopes=[(means[i]-means[i+1])/(rs[i]-rs[i+1]) for i in range(3)]
    ratios=[slopes[i+1]/slopes[i] for i in range(2)]
    assert all(mp.mpf('.49')<v<mp.mpf('.51') for v in ratios)
    return dict(delta=delta,radii=rs,angular_means=means,putative_scalar_log_slopes=slopes,
                slope_ratios=ratios,status='Local two-energy corner check only')


def symbolic_RG():
    d,g,u=sp.symbols('delta g u'); b,b1,c,a,a1,h=sp.symbols('b b1 c a a1 h',nonzero=True)
    p,q=sp.symbols('p q'); ans=sp.solve([b*p-1,b*q+b1*p+c*p**2],[p,q],dict=True)[0]
    us=ans[p]*d+ans[q]*d*d
    shift=sp.expand((a+a1*d)*us+h*us**2)
    C1=sp.simplify(shift.coeff(d,1)); C2=sp.simplify(shift.coeff(d,2))
    assert sp.simplify(C2-(a1/b+h/b**2-a*b1/b**2-a*c/b**3))==0
    f=sp.symbols('f'); c2two=C2.subs(a,0)
    assert sp.simplify(c2two.subs({a1:a1+2*f,h:h-2*f*b},simultaneous=True)-c2two)==0
    return dict(C1=str(C1),C2=str(C2),C2_2d=str(c2two),finite_operator_redefinition='PASS')



def lower_order_gamma_checks():
    """Check the complex-beta reductions independently and symbolically.

    This verifies the algebra after meromorphic continuation. It is not
    direct quadrature of the original non-absolutely-convergent integrals.
    """
    t=sp.symbols('t'); rat=sp.Rational
    def J(a,b):
        return (sp.pi*sp.gamma(1+a)*sp.gamma(1+b)*sp.gamma(-1-a-b)
                /(sp.gamma(-a)*sp.gamma(-b)*sp.gamma(2+a+b)))
    from_beta=(J(-rat(1,2),t-2)/2+J(rat(1,2),t-2)/2
               -J(-rat(1,2),t-1)/4)
    target=(sp.pi*t**2/(4*(1-t)**2)*sp.gamma(t)*sp.gamma(rat(1,2)-t)
            /(sp.gamma(1-t)*sp.gamma(rat(1,2)+t)))
    assert sp.simplify(sp.gammasimp(from_beta/target))==1
    beta_from_integral=-sp.pi*J(-rat(3,2),rat(3,4))/32
    beta_exact=9*sp.pi**2/8*(sp.gamma(rat(3,4))/sp.gamma(rat(1,4)))**2
    assert sp.simplify(sp.expand_func(beta_from_integral/beta_exact))==1
    derivative=sp.limit(target/t,t,0)
    assert derivative==sp.pi/4
    return {'I2_gamma_reduction':'PASS', 'I2_at_zero':'0',
            'I2_derivative_at_zero':str(derivative),
            'b0_gamma_reduction':'PASS'}


def propagated_expression_envelope(vals,tails):
    """Propagate analytic series-tail envelopes using high-precision scalars.

    No claim of interval-certified rounding of gamma/pi or finite sums.
    """
    R=vals['R']
    low={k:v['analytic_envelope_lower'] for k,v in tails.items()}
    high={k:v['analytic_envelope_upper'] for k,v in tails.items()}
    A=(low['P']-5*R**2*high['Q']/384,
       high['P']-5*R**2*low['Q']/384)
    B=(low['P']-5*R**2*high['Q']/128-512*high['T']/(25*mp.pi*R**2),
       high['P']-5*R**2*low['Q']/128-512*low['T']/(25*mp.pi*R**2))
    prods=[a*b for a in A for b in B]
    offset=16/R**2-R**2/9; prefactor=mp.pi**2*R**2/16
    lower=offset-prefactor*max(prods);upper=offset-prefactor*min(prods)
    assert lower<vals['C2_expression']<upper
    return {'lower':lower,'upper':upper,'width':upper-lower,
            'status':'Analytic tail bounds with non-certified floating-point evaluation'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dps',type=int,default=80)
    parser.add_argument('--tail-terms',type=int,default=20000)
    parser.add_argument('--output',type=Path,default=OUT/'independent_c2.json')
    args=parser.parse_args()
    if args.dps<75:parser.error('The retained stringent local checks require at least 75 working digits.')
    if args.tail_terms<2:parser.error('Require at least two tail terms.')
    mp.mp.dps=args.dps
    args.output.parent.mkdir(parents=True,exist_ok=True)
    result={'scope':'Independent formula, quadrature and local-limit checks; NOT a global renormalization proof',
            'working_dps':mp.mp.dps,'environment':{'python':sys.version,'platform':platform.platform(),
                'mpmath':mp.__version__,'numpy':np.__version__,
                'sympy':sp.__version__,'scipy':scipy.__version__}}
    start=time.time()
    vals=constants(); result['constants']=vals
    for name,fn in [('lower_order_gamma',lower_order_gamma_checks),('symbolic_RG',symbolic_RG),('direct_series_tails',lambda:direct_series_tail_checks(vals,args.tail_terms)),
                    ('period_quadrature',lambda:period_check(vals)),
                    ('coordinate_and_OPE',coordinate_and_OPE_checks),('two_energy_corner',corner_check)]:
        print('RUN',name,flush=True)
        result[name]=fn()
        args.output.write_text(json.dumps(encode(result),indent=2)+'\n')
        print('PASS',name,flush=True)
    result['C2_series_envelope']=propagated_expression_envelope(vals,result['direct_series_tails'])
    result['direct_contacts']=[contact(p,M) for p,M in [(1,3),(2,3),(4,3),(2,.5),(3,5)]]
    assert max(abs(x['residual']) for x in result['direct_contacts'])<1e-10
    result['all_implemented_assertions_passed']=True
    result['elapsed_seconds']=time.time()-start
    args.output.write_text(json.dumps(encode(result),indent=2)+'\n')
    print('PASS direct_contacts; COMPLETE',flush=True)

if __name__=='__main__': main()
