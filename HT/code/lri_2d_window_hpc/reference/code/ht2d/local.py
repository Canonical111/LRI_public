"""Same auxiliary oscillator prescription as the supplied dressed solver."""
import math
import numpy as np
from scipy.sparse import diags
from scipy.linalg import eigh

class LocalProblem:
    def __init__(self,nz,osc,zero_scale=1.):
        if nz<2 or osc<2*nz+8 or osc%2:raise ValueError('Invalid zero-mode caps')
        if not math.isfinite(zero_scale) or zero_scale<=0:raise ValueError('zero_scale must be positive')
        self.nz=nz;self.osc=osc;self.zero_scale=zero_scale
        d=osc+4;C=diags(np.sqrt(np.arange(1,d)),offsets=-1,shape=(d,d)).toarray();Q=C+C.T
        self.pp=(-(C-C.T)@(C-C.T))[:osc,:osc]
        self.q=[np.eye(osc),Q[:osc,:osc],(Q@Q)[:osc,:osc],(Q@Q@Q)[:osc,:osc],(Q@Q@Q@Q)[:osc,:osc]]

    def local(self,delta,A,g):
        t=(3*delta/max(g,1e-16))**(1/6)
        if A>0:t=min(t,(delta/(4*A))**.25)
        well=math.sqrt(max(0.,-6*A/max(g,1e-16)))
        t=max(t*self.zero_scale,well/math.sqrt(self.osc*.4))
        H=delta/(4*t*t)*self.pp+A*t*t*self.q[2]+g*t**4*self.q[4]/12
        U=np.zeros((self.osc,2*self.nz));ww=[]
        for f in (0,1):
            ix=np.arange(f,self.osc,2)
            w,v=eigh(H[np.ix_(ix,ix)],subset_by_index=(0,self.nz-1),check_finite=False)
            U[np.ix_(ix,np.arange(f*self.nz,(f+1)*self.nz))]=v
            ww.extend(w)
        ww=np.array(ww);shift=ww[0];ww-=shift
        X={j:U.T@(t**j*self.q[j])@U for j in range(1,4)}
        res=float(np.max(np.linalg.norm(H@U-U*(ww+shift)[None,:],axis=0)))
        edge=np.sum(U[-8:,:]**2,axis=0)
        return ww,X,U,t,res,edge

    def evaluate(self,delta,theta):
        kap,loge=map(float,theta)
        if not np.all(np.isfinite(theta)) or abs(loge)>25:raise ValueError('Invalid coupling coordinates')
        e=math.exp(loge);g=192*e**3/delta**2;A=4*e*e*kap/delta;r=A+g/2-delta/4
        w,X,U,t,res,edge=self.local(delta,A,g)
        L=np.empty((4,2*self.nz,2*self.nz))
        L[0]=(2*A-delta/2)*X[1]+g*X[3]/3
        L[1]=(A-delta/4)*np.eye(2*self.nz)+g*X[2]/2
        L[2]=g*X[1]/3;L[3]=g/12*np.eye(2*self.nz)
        return w,L,U,{'r':r,'g':g,'A':A,'local_scale':t,'zero_basis_scale':self.zero_scale,
            'local_auxiliary_residual':res,'local_edge_max':float(max(edge[:self.nz-2].max(initial=0),edge[self.nz:-2].max(initial=0)))}
