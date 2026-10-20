"""Conformal wheel moments with a general balanced spoke/rim exponent.
T_b eigenvalues: normalization d^d x Gamma(d/2)/pi^(d/2).
Independent of conformal-triangle/zigzag kernel used in original work.
"""
import numpy as np
from scipy.special import loggamma,gammaln,gammasgn,digamma,roots_legendre
from kappa_mb import trigamma
import mpmath as mp
import json
from pathlib import Path

def degeneracy(d,l):
    l=np.asarray(l,dtype=float)
    if d==1:return np.where(l<=1,1.,0.)
    if d==2:return np.where(l==0,1.,2.)
    if d==3:return 2*l+1
    if d==4:return (l+1)**2
    out=np.zeros_like(l); nz=l>0
    out[~nz]=1
    out[nz]=(2*l[nz]+d-2)*np.exp(gammaln(l[nz]+d-2)-gammaln(d-1)-gammaln(l[nz]+1))
    if d<1:out[nz]*=gammasgn(l[nz]+d-2)*gammasgn(d-1)
    return out

def terms(d,ls,nodes=256):
    ls=np.asarray(ls,dtype=float)
    q=d/4; a=ls[:,None]/2+q/2; b=a+q
    # tan transform with spin-dependent scale.
    xx,ww=roots_legendre(nodes);x=(xx+1)/2;w=ww/2
    scale=(a+b)/2
    angle=np.pi*x/2
    nu=scale*np.tan(angle)
    wt=scale*(np.pi/2)/np.cos(angle)**2*w
    za=a+1j*nu;zb=b+1j*nu
    t=np.exp(gammaln(2*q)+2*(loggamma(za)-loggamma(zb)).real)
    w1=-digamma(q)+.5*(digamma(za)+digamma(zb)).real
    w2=.125*(trigamma(za)-trigamma(zb)).real
    deg=degeneracy(d,ls)/np.pi
    return np.array([deg*np.sum(wt*t**3,axis=1),
                     deg*np.sum(wt*t**4,axis=1),
                     deg*np.sum(wt*t**4*4*w1,axis=1),
                     deg*np.sum(wt*t**3*(w1*w1+w2/3),axis=1),
                     deg*np.sum(wt*t**3*3*w1,axis=1)])

def direct1():
    mp.mp.dps=35;d=mp.mpf(1);q=d/4
    vals=[mp.mpf(0)]*5
    for l in [0,1]:
        a=mp.mpf(l)/2+q/2;b=a+q
        def integrand(nu,which):
            t=mp.gamma(2*q)*abs(mp.gamma(a+1j*nu)/mp.gamma(b+1j*nu))**2
            w1=-mp.digamma(q)+(mp.digamma(a+1j*nu)+mp.digamma(b+1j*nu)).real/2
            w2=(mp.polygamma(1,a+1j*nu)-mp.polygamma(1,b+1j*nu)).real/8
            return [t**3,t**4,4*t**4*w1,t**3*(w1*w1+w2/3),3*t**3*w1][which]/mp.pi
        for i in range(5):vals[i]+=mp.quad(lambda x:integrand(x,i),[0,.1,.3,1,4,12,mp.inf])
    return [str(x) for x in vals]

if __name__=='__main__':
    rows=[]
    for d in [1,2,3,4]:
        for nodes in [192,384]:
            L=2 if d==1 else 512
            v=terms(d,np.arange(L),nodes)
            row=dict(d=d,nodes=nodes,spins=L,labels=['W3','P4','L','Z','W3prime'],values=v.sum(axis=1).tolist())
            rows.append(row);print(row,flush=True)
    Path(__file__).with_name('wheel_spectral_raw.json').write_text(json.dumps(rows,indent=2))

def tetragamma(z):
    from scipy.special import bernoulli
    z=np.asarray(z,dtype=complex);w=z+24
    val=-1/w**2-1/w**3
    B=bernoulli(20)
    for k in range(1,11):val-=B[2*k]*(2*k+1)/w**(2*k+2)
    for k in range(24):val-=2/(z+k)**3
    return val

def kterms(d,ls,nodes=256):
    ls=np.asarray(ls,dtype=float);q=d/4
    a=ls[:,None]/2+q/2;b=a+q
    xx,ww=roots_legendre(nodes);x=(xx+1)/2;w=ww/2
    scale=(a+b)/2;angle=np.pi*x/2
    nu=scale*np.tan(angle);wt=scale*(np.pi/2)/np.cos(angle)**2*w
    za=a+1j*nu;zb=b+1j*nu
    t=np.exp(gammaln(2*q)+2*(loggamma(za)-loggamma(zb)).real)
    pa,pb=digamma(za),digamma(zb);ta,tb=trigamma(za),trigamma(zb)
    p=(pa+pb).real;h=(pa-pb).imag;j=(ta-tb).real;k=(ta+tb).imag
    r=(tetragamma(za)+tetragamma(zb)).real
    D2=-h*h/2-5*j/8
    weight=((digamma(1)+digamma(2*q)-p)*D2-h*k/2-5*r/32)/4
    return degeneracy(d,ls)*np.sum(wt*t*t*weight,axis=1)/np.pi
