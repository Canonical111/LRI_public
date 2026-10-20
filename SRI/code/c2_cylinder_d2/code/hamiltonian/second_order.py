"""Independent second-order spectral sums and analytic-continuation checks."""
import numpy as np
from scipy.signal import fftconvolve
from math import pi
import mpmath as mp

def coeff(p,n):
    out=np.ones(n)
    for k in range(1,n):out[k]=out[k-1]*(p+k-1)/k
    return out

def smooth_chi(a,n=10000):
    q=np.exp(-a);k=np.arange(n,dtype=float)
    chi=coeff(15/8,n)*np.exp(-a*k)
    # A long output with a short exponentially convergent chi input is more stable.
    m=min(n,max(100,int(50/a)+1));chi=chi[:m]
    d=fftconvolve(coeff(1/8,n),chi)[:n]
    c=fftconvolve(coeff(-3/8,n),chi)[:n]
    dm=np.r_[0,d[:-1]];dm2=np.r_[0,0,d[:-2]]
    B=d+dm
    A=np.r_[d[1:],0]+3*d+3*dm+dm2
    k=k[:-1];d=d[:-1];B=B[:-1];A=A[:-1];c=c[:-1]
    pref=pi*pi*q**(15/8)
    e0=-4*pref*np.sum(d*d/(2*k+2))
    ee=-pref*np.sum(B*B/(2*k+1))
    ed=-pref/4*np.sum(A*B/(2*k+1))
    mix=-pref*np.sum(c*c*(1/(2*k+1)+1/(2*k+2)))
    return dict(a=a,n=n,E0=e0,Eepsilon=ee,Edescendant=ed,gap2=ee-e0,
                X2=2*ee-ed-e0,t2=-mix/(2*pi),k2=-(ee-e0))

def analytic_gap(delta):
    if delta==0:return mp.mpf(0)
    p=2-delta
    return mp.pi**2*mp.gamma(p/2)**2*mp.gamma(1-p)/(mp.gamma(1-p/2)**2*mp.gamma(p))

if __name__=='__main__':
    import json
    mp.mp.dps=60
    out={'analytic_gap_slope':str(mp.diff(analytic_gap,0)),
         'analytic_formula':'pi^2 Gamma(1-delta/2)^2 Gamma(delta-1) / [Gamma(delta/2)^2 Gamma(2-delta)]',
         'time_cutoff_gap_endpoint':'-pi^2 / (4 cosh(a/2)^2)',
         'time_cutoff_finite_artifact':str(-mp.pi**2/4),
         'smooth_chi':[smooth_chi(a) for a in [.25,.35,.5,.75,1.0]]}
    print(json.dumps(out,indent=2))
