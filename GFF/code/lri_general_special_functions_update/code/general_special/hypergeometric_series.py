"""Explicit, derivative-free polygamma-weighted double hypergeometric sums.
No graph integral, Barnes integral, or parameter differentiation is used.
Raw rectangular partial sums are intended as structural checks, not error estimates.
"""
import numpy as np
from scipy.special import digamma,polygamma,gammaln
from wheel_spectrum import degeneracy

def psi(m,x):return digamma(x) if m==0 else polygamma(m,x)
def arrays(d,ls,ns):
    q=d/4.;l=np.asarray(ls,dtype=float)[:,None];n=np.asarray(ns,dtype=float)[None,:]
    a=l+q+n;b=l+2*q+n;c=n+1-q;nn=n+1
    # Reflection evaluated only with positive-argument polygamma functions.
    C=[(-1)**m*psi(m,c)+psi(m,q)-(-1)**m*psi(m,1-q) for m in range(4)]
    lam=[];eta=[];theta=[];pp=[]
    for m in range(4):
        pole=(1+(-1)**(m+1))*psi(m,1)-psi(m,nn)
        lam.append(psi(m,a)-psi(m,b)-(-1)**(m+1)*C[m]+pole)
        pp.append((psi(m,a)+psi(m,b)+(-1)**m*C[m]-pole)/2)
        if m<3:eta.append((psi(m+1,a)+(-1)**(m+1)*C[m+1])/2)
        if m<2:theta.append((psi(m+2,a)-(-1)**(m+1)*C[m+2])/4)
    mu1=(psi(0,a)-psi(0,q)+psi(0,c)-psi(0,1-q))/2
    mu2=(psi(1,a)-psi(1,q)+psi(1,c)-psi(1,1-q))/4
    logt=(gammaln(a)-gammaln(q)+gammaln(2*q)-gammaln(b)
        +gammaln(c)-gammaln(1-q)-gammaln(nn))
    logs=(gammaln(l+2*q+n)-gammaln(2*q)+gammaln(3*q)-gammaln(l+3*q+n)
          +gammaln(nn)+gammaln(1+q)-gammaln(nn+q))
    return logt,logs,lam,eta,theta,pp,mu1,mu2

def series_terms(d,ls,ns):
    q=d/4.;l=np.asarray(ls,dtype=float)
    lt,ls2,ll,et,th,pp,mu1,mu2=arrays(d,ls,ns)
    l1,l2,l3,l4=ll;e1,e2,e3=et;t1,t2=th;p0,p1,p2,p3=pp
    deg=degeneracy(d,l)[:,None]
    f3=(9*l1*l1+3*l2)/2
    f3p=9*l1*e1+1.5*e2
    f3pp=9*e1*e1+9*l1*t1+1.5*t2
    f4=32/3*l1**3+8*l1*l2+2/3*l3
    f4p=32*l1*l1*e1+8*e1*l2+8*l1*e2+2/3*e3
    w3=deg*np.exp(3*lt)*f3
    w4=-deg*np.exp(4*lt)*f4
    L=-deg*np.exp(4*lt)*(4*mu1*f4+f4p)
    Z=deg*np.exp(3*lt)*(((9*mu1*mu1+3*mu2)*f3+6*mu1*f3p+f3pp)/9)
    c1=digamma(1)+digamma(2*q)
    rr=((p0-c1)/2*(l1**3+3*l1*l2+l3)+.75*p1*(l1*l1+l2)
        -(l1*p2+p3)/4-l1**4/12+l1*l1*l2/8+7*l1*l3/24+l2*l2/8+l4/12)
    logM=gammaln(-q)+2*gammaln(2*q)-gammaln(3*q)
    K=deg*(np.exp(2*logM+2*ls2)/8-np.exp(2*lt)*rr/4)
    return np.array([w3,w4,L,Z,K])

if __name__=='__main__':
    for d in [1,2,3]:
        q=d/4;A=digamma(2*q)+digamma(1)-2*digamma(q);kg=-A*polygamma(2,q)/4
        for n in [64,256,1024]:
            val=np.zeros(5)
            limit=2 if d==1 else n
            for i in range(0,limit,16):
                val+=series_terms(d,np.arange(i,min(i+16,limit)),np.arange(n)).sum(axis=(1,2))
            val[-1]+=kg
            print(d,n,val,flush=True)
