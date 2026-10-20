"""First-order scalar four-point conformal-block engine.
Extracted without numerical changes from the supplied project module.
Only block recurrences, tensor normalization and the leading integral are retained.
Source/provenance: data/provenance/package_sources.json.
"""
from __future__ import annotations

import numpy as np

from scipy.special import eval_legendre, poch, gammaln

from functools import lru_cache

@lru_cache(None)
def operators(L,N):
    size=L+N+8
    I=np.eye(size); M=np.zeros((size,size)); D=np.zeros_like(M)
    for j in range(size):
        if j+1<size:M[j+1,j]=(j+1)/(2*j+1)
        if j:M[j-1,j]=j/(2*j+1)
        for k in range(j-1,-1,-2): D[k,j]=2*k+1
    T=[I,M]; U=[I,2*M]
    for k in range(2,N+1):
        T.append(2*M@T[-1]-T[-2]);U.append(2*M@U[-1]-U[-2])
    A=2*M@M-I; B=2*M@(I-M@M)@D
    Ua=[I,2*A]
    for k in range(2,N//2+1):Ua.append(2*A@Ua[-1]-Ua[-2])
    return I,M,D,T,U,A,B,Ua

@lru_cache(None)
def coefficients(Delta,ell,N=16,da=0.,db=0.):
    a=-da/2; b=db/2; c=a+b; p=a*b
    I,M,D,T,U,A,B,Ua=operators(ell,N)
    size=len(I); out=np.zeros((N+1,size));out[0,ell]=1
    C0=Delta*(Delta-3)+ell*(ell+1)
    js=np.arange(size)
    for n in range(1,N+1):
        rhs=np.zeros(size)
        for m in range(1,n+1):
            E=Delta+n-m; v=out[n-m]
            if not np.any(v):continue
            if m%2==0:
                k=m//2-1
                AA=-A@Ua[k]+(Ua[k-1] if k else 0)-0.5*I
                op=4*(E*AA+Ua[k]@B)
                rhs-=op@v
            if m%2==1 and c:
                rhs+=8*c*(E*T[m]+(M@M-I)@U[m-1]@D)@v
            if p:rhs+=16*p*(-1)**(m-1)*m*T[m]@v
        den=(Delta+n)*(Delta+n-3)+js*(js+1)-C0
        mask=np.abs(den)>1e-9
        out[n,mask]=rhs[mask]/den[mask]
        if np.max(abs(rhs[~mask]),initial=0)>1e-8:raise ValueError('uncanceled null state')
    return out[:,:ell+N+1]

class Block:
    def __init__(self,Delta,ell,N=16,da=0.,db=0.):
        self.Delta=Delta;self.ell=ell
        self.coefs=coefficients(float(Delta),ell,N,float(da),float(db))
    def __call__(self,z):
        z=np.asarray(z,dtype=complex)
        rho=z/(1+np.sqrt(1-z))**2
        r=np.abs(rho);eta=np.real(rho)/r
        P=np.array([eval_legendre(j,eta) for j in range(self.coefs.shape[1])])
        val=np.zeros_like(r)
        for n in range(len(self.coefs)-1,-1,-1):
            val=val*r+np.tensordot(self.coefs[n],P,axes=(0,0))
        return (4*r)**self.Delta*val

def stt_factor(ell):
    return float(np.exp(gammaln(ell+1)-ell*np.log(2)-gammaln(ell+.5)+gammaln(.5)))

import json

from pathlib import Path

from scipy.special import roots_legendre

from numpy.polynomial import polynomial as poly,legendre as leg

from spectrum import S,E,LOW
CHI=3-S

EVEN=[('eps',E,0,1.05185373,1.53244304),('ep',3.82968,0,.053012,1.536),('T',3.,2,-2*S*np.sqrt(3/(8*LOW['ct'][0])),-2*E*np.sqrt(3/(8*LOW['ct'][0]))),('C4',5.022665,4,.276304,.99168),('S6',7.028488,6,.1259328,.529088),('X8',9.031023,8,.05896,.277088),('X10',11.0324141,10,.02801984,.1433952)]

ODD=[('sig',S,0,1.05185373),('sp',5.2906,0,.057235),('Si2',4.180305,2,.77831882),('Si3',4.63804,3,.39173716),('Si4',6.112674,4,.4308208),('Si5',6.709778,5,.2371098),('Si6',8.08097,6,.2295216),('Si7',8.747293,7,.1313810)]

def zcoefs(delta,ell,N=32,da=0.,db=0.):
    a=np.zeros((N+1,ell+N+1)); a[0,ell]=1
    C0=delta*(delta-3)+ell*(ell+1)
    for n in range(1,N+1):
        E=delta+n-1
        for j in range(ell+n+1):
            rhs=0.
            if j>0:
                k=j-1
                rhs+=(E+k-da)*(E+k+db)*(k+1)/(2*k+1)*a[n-1,k]
            if j+1<a.shape[1]:
                k=j+1
                rhs+=(E-k-1-da)*(E-k-1+db)*k/(2*k+1)*a[n-1,k]
            den=(delta+n)*(delta+n-3)+j*(j+1)-C0
            if abs(den)>1e-9:a[n,j]=rhs/den
            elif abs(rhs)>1e-8:raise ValueError('null')
    return a

def integrate(r0=.2,nr=90,na=90,level=16,cut=11.1):
    ev=[p for p in EVEN if p[1]<cut]; od=[p for p in ODD if p[1]<cut]
    eb=[Block(p[1],p[2],level) for p in ev]
    ob=[Block(p[1],p[2],level,E-S,S-E) for p in od]
    beta_small=-4*np.pi/(3*r0**3); eps_small=beta_small
    for p in ev:
        name,d,l,cs,ce=p
        a=zcoefs(d,l)
        vals=4*np.pi*sum(a[n,0]*r0**(d+n-3)/(d+n-3) for n in range(len(a)) if abs(a[n,0])>1e-18)
        beta_small+=cs**2*stt_factor(l)*vals
        eps_small+=cs*ce*stt_factor(l)*vals
    qs,ws=roots_legendre(nr);qa,wa=roots_legendre(na)
    beta=beta_small;eps=eps_small
    # Split r at 0.5 where angular domain changes.
    for lo,hi,small in [(0,r0,True),(r0,.5,False),(.5,1,False)]:
        u=(qs+1)/2
        if small:
            r=hi*u**4;wr=4*hi*u**3*ws/2
        else:
            r=lo+(hi-lo)*u;wr=(hi-lo)*ws/2
        mx=np.minimum(1,1/(2*r))
        eta=-1+(mx[:,None]+1)*(qa[None,:]+1)/2
        weights=2*np.pi*r[:,None]**2*wr[:,None]*(mx[:,None]+1)*wa[None,:]/2
        z=r[:,None]*(eta+1j*np.sqrt(1-eta**2));v=abs(1-z)**2
        SB=np.ones_like(eta);SE=np.ones_like(eta)
        for p,bl in zip(ev,eb):
            name,d,l,cs,ce=p;g=bl(z)*stt_factor(l)
            SB+=cs*cs*g;SE+=cs*ce*g
        odd=np.zeros_like(eta)
        for p,bl in zip(od,ob):
            name,d,l,c=p;odd+=c*c*stt_factor(l)*bl(z)
        bf=r[:,None]**(-2*S)*(1+v**(-CHI))*SB
        ef=2*r[:,None]**(-S-E)*v**(-CHI)*odd
        if not small:
            bf+=r[:,None]**(-6)*SB;ef+=r[:,None]**(-6)*SE
        beta+=np.sum(weights*bf);eps+=np.sum(weights*ef)
    return dict(level=level,cut=cut,nr=nr,na=na,r0=r0,b0=-2*np.pi*beta,a0=-2*np.pi*eps,C1=eps/beta,even_count=len(ev),odd_count=len(od))
