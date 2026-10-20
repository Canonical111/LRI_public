"""Derivative-free primitive residues; independent of the spectral integration code."""
import math
import numpy as np
import mpmath as mp
from scipy.special import digamma, polygamma, gammaln, gammasgn

def psi(m,x): return digamma(x) if m==0 else polygamma(m,x)

def degeneracy(d,l):
    l=np.asarray(l,dtype=float)
    if d==1.: return np.where(l<=1,1.,0.)
    if d==2.: return np.where(l==0,1.,2.)
    out=np.ones_like(l); k=l>0; z=l[k]
    out[k]=(2*z+d-2)*np.exp(gammaln(z+d-2)-gammaln(d-1)-gammaln(z+1))*gammasgn(d-1)*gammasgn(z+d-2)
    return out

def Cpsi(m,N,alpha):
    """psi_m(alpha-N), with nonnegative integer N, by reflection."""
    c=float(mp.polygamma(m,alpha)-(-1)**m*mp.polygamma(m,1-alpha))
    return (-1)**m*psi(m,N+1-alpha)+c

def ecoeff(kappa,n):
    E=[np.ones_like(kappa[0])]
    for k in range(1,n+1):
        E.append(sum(kappa[j-1]*E[k-j]/math.factorial(j-1) for j in range(1,k+1))/k)
    return E[n]

def terms(d,ls,ns,r=7):
    if not 0 < d < 4:
        raise ValueError("Use 0<d<4. Endpoint dimensional continuation is not a direct float substitution.")
    if r != 7:
        raise ValueError("This evaluator is certified only for the P5 case r=7; lower powers need separate summation analysis.")
    if any(np.any(np.asarray(v)<0) or np.any(np.asarray(v)!=np.floor(np.asarray(v))) for v in (ls,ns)):
        raise ValueError("Spin and radial indices must be nonnegative integers.")
    q=d/4.;p=2*q-1
    l=np.array(ls,dtype=float)[:,None];n=np.array(ns,dtype=float)[None,:]
    N=l+2*n;an=l+q+n;bn=l+2*q+n
    logt=(gammaln(an)-gammaln(q)+gammaln(2*q)-gammaln(bn)
          +gammaln(n+1-q)-gammaln(1-q)-gammaln(n+1))
    lam=[]
    for m in range(1,r):
        lam.append(psi(m-1,an)-psi(m-1,bn)-(-1)**m*Cpsi(m-1,n,q)
                   +(1+(-1)**m)*psi(m-1,1.)-psi(m-1,n+1))
    ans=0.
    for j,theta in enumerate([2*q,2*q-1]):
        # Zero-spin second channel is omitted before evaluating its Gamma factors.
        NN=np.where(l==0,1.,N) if j==1 else N
        H=(gammasgn(theta-q)*gammasgn(-q)*gammasgn(theta+q+NN)
           *np.exp(gammaln(theta+q+NN)-gammaln(q+NN)
                   +gammaln(theta-q)-gammaln(-q)
                   +gammaln(1+q+NN)-gammaln(1+q)
                   +gammaln(1+q-theta)-gammaln(1+q-theta+NN)))
        kap=[]
        for m in range(1,r):
            he=2**m*(psi(m-1,theta+q+NN)+(-1)**m*Cpsi(m-1,NN,theta-q)
                     -psi(m-1,q+NN)-(-1)**m*Cpsi(m-1,NN,-q))
            kap.append(r*lam[m-1]+he)
        fact=1. if j==0 else l*(l+2*p)
        ans=ans+fact*H*ecoeff(kap,r-1)
    return ((-1.)**(r+1)/(2*math.gamma(2*q)**2)*((-1.)**(r*l))*degeneracy(d,l.ravel())[:,None]
            *np.exp(r*logt)*ans)

def partial(d,L,N,r=7):
    val=0.
    for i in range(0,L,12):
        val+=terms(d,np.arange(i,min(i+12,L)),np.arange(N),r).sum()
    return val

if __name__=='__main__':
    import time,json
    out=[]
    for d in [1.,2.,3.,2.6]:
        for k in [16,32,64,128]:
            t=time.time();val=partial(d,2 if d==1 else k,k)
            row=dict(d=d,L=2 if d==1 else k,N=k,P5=float(val),sec=time.time()-t)
            out.append(row); print(row,flush=True)
    open(__import__('pathlib').Path(__file__).resolve().parents[2]/'verification/general_closed/P5_raw_checks.json','w').write(json.dumps(out,indent=2))
