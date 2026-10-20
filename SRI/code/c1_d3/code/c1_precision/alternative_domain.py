"""Independent disk-and-cap integration for the first-order CPT coefficient.
At delta=0 inversion gives I=2 int_|x|<1 F(x). Split at |1-x|=h.
The cap uses the even OPE with y=1-x, angular range eta_y in [|y|/2,1].
The rest uses the direct OPE. Analytically continue the small-y power series.
Unlike the original three-way folded domain, this permits moving the channel
boundary, yielding an integrated crossing-consistency diagnostic.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import sys,json,time
from pathlib import Path
import numpy as np
from scipy.special import roots_legendre,gammaln
from numpy.polynomial import legendre as leg,polynomial as poly
from spectrum import get_rows,as_upstream
from kernels import cb

class CapFunctional:
    def __init__(self,h=.7,S=cb.S,E=cb.E,level=28,nr=100,na=100,r0=.15):
        if not 0<r0<h<1:raise ValueError('Require 0<r0<h<1')
        self.h=h;self.r0=r0;self.S=S;self.E=E;self.level=level
        q,w=roots_legendre(nr);qa,wa=roots_legendre(na);u=(q+1)/2
        self.pieces=[];self.const=np.zeros(2)
        for lo,hi in [(0,1-h),(1-h,1)]:
            if lo==0:r=hi*u**4;wr=4*hi*u**3*w/2
            else:r=lo+(hi-lo)*u;wr=(hi-lo)*w/2
            mx=np.minimum(1,(1+r*r-h*h)/(2*r))
            eta=-1+(mx[:,None]+1)*(qa[None,:]+1)/2
            wg=4*np.pi*r[:,None]**2*wr[:,None]*(mx[:,None]+1)*wa[None,:]/2
            z=r[:,None]*(eta+1j*np.sqrt(1-eta**2));v=abs(1-z)**2
            ks=wg*v**(-(3-S))*r[:,None]**(-2*S)
            ko=wg*v**(-(3-S))*r[:,None]**(-S-E)
            self.pieces.append((z,ks,ko))
            self.const+=np.array([np.sum(ks-wg*v**(-3)),-np.sum(wg*v**(-3))])
        r=r0+(h-r0)*u;wr=(h-r0)*w/2
        eta=r[:,None]/2+(1-r[:,None]/2)*(qa[None,:]+1)/2
        self.y=r[:,None]*(eta+1j*np.sqrt(1-eta**2))
        self.capweights=4*np.pi*r[:,None]**(-4)*wr[:,None]*(1-r[:,None]/2)*wa[None,:]/2
        self.const*=-2*np.pi
        # J_j(r)=int_{r/2}^1 P_j(eta) d eta.
        self.J=[]
        for j in range(level+56):
            basis=np.zeros(j+1);basis[j]=1.
            integ=leg.legint(basis)
            pp=leg.leg2poly(integ)
            val=leg.legval(1.,integ)
            pp=-pp*2.**(-np.arange(len(pp)));pp[0]+=val
            if j>0 and j%2==0:pp[0]=0.
            self.J.append(pp)
    def block_kernel(self,Delta,ell,sector):
        fac=np.exp(gammaln(ell+1)-gammaln(ell+.5)+gammaln(.5))
        if sector=='even':
            bl=cb.Block(Delta,ell,self.level)
            small=0.;A=cb.zcoefs(Delta,ell,32)
            for n in range(len(A)):
                for j in range(A.shape[1]):
                    if abs(A[n,j])<1e-18:continue
                    pol=self.J[j]
                    for k,x in enumerate(pol):
                        if abs(x)<1e-18:continue
                        alpha=Delta+n+k-3
                        if abs(alpha)<1e-9:raise ValueError(f'log divergence {Delta,ell,n,j,k,A[n,j]*x}')
                        small+=A[n,j]*x*self.r0**alpha/alpha
            even=4*np.pi*small+np.sum(self.capweights*bl(self.y))
            direct=sum(np.sum(ks*bl(z)) for z,ks,ko in self.pieces)
            return -2*np.pi*fac*np.array([even+direct,even])
        else:
            bl=cb.Block(Delta,ell,self.level,self.E-self.S,self.S-self.E)
            direct=sum(np.sum(ko*bl(z)) for z,ks,ko in self.pieces)
            return -2*np.pi*fac*np.array([0.,direct])
    def evaluate(self,rows):
        out=self.const.copy();parts=[]
        for p in rows:
            K=self.block_kernel(p['Delta'],p['ell'],p['sector'])
            w=np.array([p['f']**2,p['f']*p['h'] if p['sector']=='even' else p['f']**2])
            part=K*w;out+=part
            parts.append(dict(name=p['name'],kernel=K.tolist(),contribution_b=float(part[0]),contribution_a=float(part[1])))
        return dict(h=self.h,level=self.level,b=float(out[0]),a=float(out[1]),C1=float(out[1]/out[0]),constant=self.const.tolist(),parts=parts)

def main():
    from threadpoolctl import threadpool_limits
    rows=get_rows();out=[]
    with threadpool_limits(limits=1):
        for h in [.45,.5,.55,.6,.65,.7,.75,.8,.85,.9,.95]:
            t=time.time();fn=CapFunctional(h=h,level=32,nr=120,na=120)
            r=fn.evaluate(rows);out.append(r)
            json.dump(out,open(Path(__file__).resolve().parent/'cap_results.json','w'),indent=2)
            print(h,r['a'],r['b'],r['C1'],time.time()-t,flush=True)
    json.dump(out,open(Path(__file__).resolve().parent/'cap_results.json','w'),indent=2)
if __name__=='__main__':main()
