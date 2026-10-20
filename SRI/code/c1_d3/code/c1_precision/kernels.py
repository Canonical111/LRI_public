"""Linear integrated four-point functionals for C1; no C2 evaluation.
Same angular/radial sector decomposition as the validated upstream module.
Weights are in the 1612.08471 f convention. Power divergences integrated by
analytic continuation via the small-z Casimir series.
"""
import sys,os
from pathlib import Path
import numpy as np
from scipy.special import roots_legendre, gammaln
import blocks as cb

class Functional:
    def __init__(self,S=cb.S,E=cb.E,level=24,nr=100,na=100,r0=.2):
        self.S=S;self.E=E;self.level=level;self.r0=r0
        q,w=roots_legendre(nr);qa,wa=roots_legendre(na);self.pieces=[]
        self.const=np.zeros(2)
        for lo,hi,small in [(0,r0,True),(r0,.5,False),(.5,1,False)]:
            u=(q+1)/2
            if small: r=hi*u**4;wr=4*hi*u**3*w/2
            else:r=lo+(hi-lo)*u;wr=(hi-lo)*w/2
            mx=np.minimum(1,1/(2*r))
            eta=-1+(mx[:,None]+1)*(qa[None,:]+1)/2
            wg=2*np.pi*r[:,None]**2*wr[:,None]*(mx[:,None]+1)*wa[None,:]/2
            z=r[:,None]*(eta+1j*np.sqrt(1-eta**2));v=abs(1-z)**2
            self.const+=np.array([np.sum(wg*2*(v**(-(3-S))*r[:,None]**(-2*S)-v**(-3))),np.sum(wg*(-2)*v**(-3))])
            ke=np.zeros_like(wg) if small else wg*r[:,None]**(-6)
            ks=wg*2*v**(-(3-S))*r[:,None]**(-2*S)+ke
            ko=wg*2*v**(-(3-S))*r[:,None]**(-S-E)
            self.pieces.append((z,ks,ke,ko))
        self.const*=-2*np.pi

    def block_kernel(self,Delta,ell,sector):
        # 2^ell stt_factor(ell) = ell!/(1/2)_ell
        fac=np.exp(gammaln(ell+1)-gammaln(ell+.5)+gammaln(.5))
        if sector=='even':
            bl=cb.Block(Delta,ell,self.level)
            A=cb.zcoefs(Delta,ell,32)
            active=[n for n in range(len(A)) if abs(A[n,0])>1e-18]
            if any(abs(Delta+n-3)<1e-10 for n in active):
                raise ValueError('Analytic continuation near resonance requires separate logarithmic treatment')
            small=4*np.pi*sum(A[n,0]*self.r0**(Delta+n-3)/(Delta+n-3) for n in active)
            out=np.array([small,small])
            for z,ks,ke,ko in self.pieces:
                g=bl(z);out+=np.array([np.sum(ks*g),np.sum(ke*g)])
        else:
            bl=cb.Block(Delta,ell,self.level,self.E-self.S,self.S-self.E)
            out=np.array([0.,sum(np.sum(ko*bl(z)) for z,ks,ke,ko in self.pieces)])
        return -2*np.pi*fac*out

    def evaluate(self,rows):
        out=self.const.copy(); parts=[]
        for p in rows:
            K=self.block_kernel(p['Delta'],p['ell'],p['sector'])
            w=np.array([p['f']**2,p['f']*p['h'] if p['sector']=='even' else p['f']**2])
            part=K*w;out+=part
            parts.append(dict(name=p['name'],kernel=K.tolist(),contribution_b=float(part[0]),contribution_a=float(part[1])))
        return dict(b=float(out[0]),a=float(out[1]),C1=float(out[1]/out[0]),constant=self.const.tolist(),parts=parts)

def crossing_rows(rows,z,level=24,S=cb.S,E=cb.E):
    z=np.asarray(z,dtype=complex)
    sigma=np.zeros_like(z.real);eps=np.zeros_like(z.real);mixed=np.zeros_like(z.real)
    sigma_t=np.zeros_like(z.real);eps_t=np.zeros_like(z.real);mixed_t=np.zeros_like(z.real)
    sigma+=abs(z)**(-2*S);eps+=abs(z)**(-2*E)
    sigma_t+=abs(1-z)**(-2*S);eps_t+=abs(1-z)**(-2*E);mixed_t+=abs(1-z)**(-2*S)
    for p in rows:
        ell=p['ell'];de=p['Delta'];fac=np.exp(gammaln(ell+1)-gammaln(ell+.5)+gammaln(.5))
        if p['sector']=='even':
            bl=cb.Block(de,ell,level);g=fac*bl(z);gt=fac*bl(1-z)
            sigma+=p['f']**2*abs(z)**(-2*S)*g
            sigma_t+=p['f']**2*abs(1-z)**(-2*S)*gt
            eps+=p['h']**2*abs(z)**(-2*E)*g
            eps_t+=p['h']**2*abs(1-z)**(-2*E)*gt
            mixed_t+=p['f']*p['h']*abs(1-z)**(-2*S)*gt
        else:
            mixed+=p['f']**2*fac*abs(z)**(-S-E)*cb.Block(de,ell,level,E-S,S-E)(z)
    return {kind:dict(direct=a.tolist(),crossed=b.tolist(),relative=(2*(a-b)/(abs(a)+abs(b))).tolist()) for kind,a,b in [('sigma',sigma,sigma_t),('epsilon',eps,eps_t),('mixed',mixed,mixed_t)]}
