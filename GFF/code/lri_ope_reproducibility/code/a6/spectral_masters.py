"""Numerical evaluation of K_d,L_d,Z_d from the note's convergent spectral kernels.
For d=2,3 the omitted spin tail is integrated analytically term by term in
its large-spin Gamma-ratio expansion and summed with Hurwitz zeta.
No fit in d, to bootstrap points, or to thermal coefficients is used.
"""
from __future__ import annotations
from functools import lru_cache
import numpy as np
from scipy.special import loggamma,digamma,gamma,roots_legendre
import mpmath as mp
from pathlib import Path
import json,time

BERN=np.array([1/6,-1/30,1/42,-1/30,5/66,-691/2730,7/6,-3617/510,43867/798,-174611/330],float)

def complex_psi12(z):
    """Trigamma and second polygamma, using recurrence and Bernoulli asymptotics."""
    z=np.asarray(z,dtype=complex);shift=max(0,int(np.ceil(14-float(z.real.flat[0]))));w=z+shift
    p1=1/w+1/(2*w*w);p2=-1/(w*w)-1/(w*w*w)
    iw=1/w;u=iw**3
    for k,B in enumerate(BERN,start=1):
        p1+=B*u;p2-=(2*k+1)*B*u*iw;u*=iw*iw
    for j in range(shift):
        v=1/(z+j);p1+=v*v;p2-=2*v*v*v
    return p1,p2

@lru_cache(None)
def nodes(n):
    x,w=roots_legendre(n);return (x+1)/2,w/2

def spin_integrals(d,ell,nu_nodes):
    q=d/4;a=ell/2+q/2;b=a+q;t,w=nodes(nu_nodes);nu=a*t/(1-t);jac=a/(1-t)**2
    za=a+1j*nu;zb=b+1j*nu
    tl=gamma(2*q)*np.exp(2*(loggamma(za)-loggamma(zb)).real)
    pa=digamma(za);pb=digamma(zb);ta,ua=complex_psi12(za);tb,ub=complex_psi12(zb)
    w1=-digamma(q)+(pa+pb).real/2;w2=(ta-tb).real/8
    p=(pa+pb).real;h=(pa-pb).imag;j=(ta-tb).real;k=(ta+tb).imag;r=(ua+ub).real
    e2=-h*h/2-5*j/8;cstar=digamma(1)+digamma(2*q)
    kval=tl**2*((cstar-p)*e2-h*k/2-5*r/32)/4
    arr=np.array([tl**3,tl**4,4*tl**4*w1,tl**3*(w1*w1+w2/3),kval,3*tl**3*w1])
    mult=1 if ell==0 else (2 if d==2 else 2*ell+1)
    return arr@(w*jac)*(mult/np.pi)

@lru_cache(None)
def bernpoly_coeffs(n):return tuple(mp.mpf(mp.binomial(n,k))*mp.bernoulli(n-k) for k in range(n+1))
def bernpoly(n,x):
    # Recompute Bernoulli values at the caller's precision (mp.diff may raise it).
    return sum(mp.binomial(n,k)*mp.bernoulli(n-k)*x**k for k in range(n+1))
def c_even(k,g):return bernpoly(2*k+1,(1+g)/2)/(k*(2*k+1))
def exp_coeff(es):
    u=[mp.mpf(1)]
    for n in range(1,len(es)+1):u.append(sum(k*es[k-1]*u[n-k] for k in range(1,n+1))/n)
    return u

def wheel_tail(d,r,g,N,J):
    q=mp.mpf(d)/4;g=mp.mpf(g);n0=mp.mpf(N)+(mp.mpf(d)-2)/2
    C=mp.gamma(2*q)*mp.gamma(g)/mp.gamma(2*q-g)
    uu=exp_coeff([r*c_even(k,g) for k in range(1,J+1)])
    out=mp.mpf(0);p=g*r
    for j in range(J+1):
        H=mp.gamma(2*p+2*j-1)*sum(uu[a]*uu[j-a]/(mp.gamma(p+2*a)*mp.gamma(p+2*(j-a))) for a in range(j+1))
        out+=H*mp.zeta(2*p+2*j-d+1,n0)
    return 2*C**r*out

def mixed_tail(d,tau,N,J):
    q=mp.mpf(d)/4;tau=mp.mpf(tau);n0=mp.mpf(N)+(mp.mpf(d)-2)/2
    alpha=(1-q)/2;beta=(1+q)/2;p=2*q+tau
    er=[(-1)**(k+1)*(3*bernpoly(k+1,alpha)-2*bernpoly(k+1,beta)-bernpoly(k+1,alpha+tau))/(k*(k+1)) for k in range(1,2*J+1)]
    ur=exp_coeff(er);us=exp_coeff([2*c_even(k,q+tau/2) for k in range(1,J+1)])
    out=mp.mpf(0)
    # j=0 cancels identically before summation, removing the individual UV pole.
    for j in range(1,J+1):
        hr=sum((-1)**a*ur[a]*ur[2*j-a]/(mp.gamma(p+a)*mp.gamma(p+2*j-a)) for a in range(2*j+1))
        hs=sum(us[a]*us[j-a]/(mp.gamma(p+2*a)*mp.gamma(p+2*j-2*a)) for a in range(j+1))
        out+=mp.gamma(2*p+2*j-1)*(hr-hs)*mp.zeta(1+2*tau+2*j,n0)
    return 2*mp.gamma(2*q)**2*out

def tails(d,N,J,dps=55):
    if d not in (2,3):raise ValueError('This spin-tail implementation is for d=2,3.')
    with mp.workdps(dps):
        q=mp.mpf(d)/4
        W3=wheel_tail(d,3,q,N,J);W4=wheel_tail(d,4,q,N,J)
        L=-mp.diff(lambda g:wheel_tail(d,4,g,N,J),q)/2
        Z=mp.diff(lambda g:wheel_tail(d,3,g,N,J),q,2)/36
        first=-mp.diff(lambda g:wheel_tail(d,3,g,N,J),q)/2
        f2=mp.diff(lambda t:mixed_tail(d,t,N,J),mp.mpf(0),2)/2
        f3=mp.diff(lambda t:mixed_tail(d,t,N,J),mp.mpf(0),3)/6
        K=((mp.digamma(1)+mp.digamma(2*q))*f2+f3)/4
        return np.array([float(x) for x in (W3,W4,L,Z,K,first)]),[mp.nstr(x,45) for x in (W3,W4,L,Z,K,first)]

def evaluate(d,N=32,nu_nodes=512,J=6,dps=55):
    start=time.time();ss=np.stack([spin_integrals(d,l,nu_nodes) for l in range(N)]);low=ss.sum(axis=0)
    tail,tailtext=tails(d,N,J,dps);total=low+tail
    q=d/4;A=digamma(2*q)-2*digamma(q)+digamma(1);U=float(mp.polygamma(2,q));total[4]-=A*U/4
    result=dict(d=d,N=N,nu_nodes=nu_nodes,J=J,seconds=time.time()-start,
                Q=total[0]/3,P4=total[1],L=total[2],Z=total[3],K=total[4],W3_first_derivative=total[5],
                low_spin_sum=low.tolist(),tail=tailtext)
    return result

if __name__=='__main__':
    mp.mp.dps=60;out=[]
    for d in (2,3):
        for N,nu,J in [(24,384,5),(32,768,6),(48,1024,7)]:
            print('BEGIN',d,N,nu,J,flush=True);r=evaluate(d,N,nu,J);out.append(r);print(json.dumps(r,indent=2),flush=True)
            Path('spectral_results.json').write_text(json.dumps(out,indent=2))
