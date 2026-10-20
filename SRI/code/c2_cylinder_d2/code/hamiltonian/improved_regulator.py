"""Polynomial-improved positive chi oscillator cutoffs; same Hamiltonian sums.
No fitting in the physical parameter delta, and no target fourth-order input.
"""
from pathlib import Path
import numpy as np
from numpy.polynomial.legendre import leggauss
from math import pi
from scipy.special import gammaln

def trunc_exp(x,order):
    out=np.ones_like(x);term=out.copy()
    for j in range(1,order+1):term=term*x/j;out+=term
    return out

def planar_constants(order,n=512):
    """Planar thermal and spin-two counterterms by compact 2D quadrature.
    Returns positive kappa = uncorrected epsilon gap, so k2=-kappa.
    """
    chi=15/8
    zz,ww=leggauss(n);u=(zz[:,None]+1)/2;y=(zz[None,:]+1)/2
    wt=ww[:,None]*ww[None,:]/4
    z=(1-u)*((1-y*y)+1j*y*np.sqrt(1-y*y))
    P=np.ones_like(z);term=P.copy()
    for j in range(1,order+1):term=term*z*(chi+j-1)/j;P+=term
    ct=np.sum(wt*(u*u+y*y-u*u*y*y)**(3/8)*abs(P)**2)
    t=(zz[:,None]+1)/2;ph=(zz[None,:]+1)*pi/4;c=np.cos(ph)
    den=t*t+2*c*t*(1-t)+(1-t)**2
    z=(1-t)/(1-t+t*np.exp(1j*ph))
    P=np.ones_like(z);term=P.copy()
    for j in range(1,order+1):term=term*z*(chi+j-1)/j;P+=term
    delta=-pi*np.sum(ww[:,None]*ww[None,:]*pi/8*np.cos(2*ph)*t**(11/4)/((1-t)*den**chi)*(abs(P)**2-1))
    r=np.exp(gammaln(chi+.5)-gammaln(1.5)-gammaln(chi))
    kap0=pi*pi/4*(chi-r)/(chi-1)
    return dict(order=order,n=n,ct=float(ct),kappa=float(kap0+delta),kappa_delta=float(delta))

if __name__=='__main__':
    import json
    out=[]
    for k in range(4):
        for n in [128,256,512]:
            a=planar_constants(k,n);out.append(a);print(a,flush=True)
    Path(__file__).with_name('improved_constants.json').write_text(json.dumps(out,indent=2))

def leading_moments(order,n=512):
    """Convergent dimension-three UV moments for order >=1.
    M_l = int_{tau>0} d^2r |r|^(11/4) cos(l phi) (K_reg-K_0).
    These scale as lambda; l=0,2. This is a regulator calculation only.
    """
    if order<1:raise ValueError('The unimproved first moment is logarithmically divergent')
    chi=15/8;zz,ww=leggauss(n);t=(zz[:,None]+1)/2;ph=(zz[None,:]+1)*pi/4
    e=(1-t)/t;z=e/(e+np.exp(1j*ph));term=np.ones_like(z);pm=np.zeros_like(z)
    for j in range(1,order+1):term*=z*(chi+j-1)/j;pm+=term
    logf=-chi*np.log1p(2*np.cos(ph)*e+e*e)+2*np.log1p(pm).real
    base=np.expm1(logf)/(1-t)**2
    weights=ww[:,None]*ww[None,:]*pi/4
    return dict(order=order,n=n,M0=float(np.sum(weights*base)),M2=float(np.sum(weights*base*np.cos(2*ph))))

def curvature_thermal(order,n=512):
    """Order-lambda thermal counterterm from the cylinder chi kernel.
    Uses (2sinh(z/2))^-chi = z^-chi - chi*z^(2-chi)/24 + ... .
    For order>=1 the subtracted planar moment is convergent.
    """
    if order<1:raise ValueError('Unimproved curvature moment has a logarithm')
    chi=15/8;zz,ww=leggauss(n);t=(zz[:,None]+1)/2;ph=(zz[None,:]+1)*pi/4;e=(1-t)/t
    z=e/(e+np.exp(1j*ph));ps=[]
    for aa in [chi-2,chi]:
        P=np.ones_like(z);term=P.copy()
        for j in range(1,order+1):term*=z*(aa+j-1)/j;P+=term
        ps.append(P)
    F=np.real((np.exp(1j*ph)+e)**2*ps[0]*np.conj(ps[1]))/(1+2*np.cos(ph)*e+e*e)**chi
    w=ww[:,None]*ww[None,:]*pi/4
    integral=np.sum(w*(F-np.cos(2*ph))/(1-t)**2)
    return dict(order=order,n=n,thermal_lambda_coefficient=float(-chi*integral/24),integral=float(integral))
