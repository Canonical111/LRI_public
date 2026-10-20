#!/usr/bin/env python3
"""Direct scalar quartic Hamiltonian with nonperturbatively dressed zero mode.

Separate regulator: retain all positive-mode partitions N<=bath_cut and the
lowest nz states *per parity* of the exactly diagonalized zero-mode Hamiltonian.
An auxiliary oscillator cap resolves the zero-mode eigenfunctions; it is varied
independently. No epsilon expansion and no physical thermal inputs are used.
This is bare Hamiltonian truncation, not complete effective-Hamiltonian matching.
"""
from __future__ import annotations
import argparse,json,math,os,time
from pathlib import Path
import numpy as np
from scipy.sparse import csr_matrix,diags,eye,kron
from scipy.sparse.linalg import eigsh,LinearOperator
from scipy.linalg import eigh
from scipy.optimize import root


def partitions_upto(N):
    states=[]
    def rec(prefix,left,start):
        states.append(tuple(prefix))
        for n in range(start,left+1):rec(prefix+[n],left-n,n)
    rec([],N,1)
    return states


def matpower_norm(B,order):
    C=B.T.tocsr(); I=eye(B.shape[0],format='csr')
    cb=[I];bb=[I]
    for j in range(order):cb.append(C@cb[-1]);bb.append(B@bb[-1])
    ans=csr_matrix(B.shape)
    for j in range(order+1):ans=ans+math.comb(order,j)*(cb[j]@bb[order-j])
    return ans.tocsr()


class DressedZero:
    def __init__(self,bath_cut=8,nz=8,osc=96,reflection=0,eig_tol=3e-11,zero_scale=1.):
        if bath_cut<2 or nz<2 or osc<2*nz+8 or osc%2:raise ValueError('Invalid caps')
        self.zero_scale=float(zero_scale)
        self.bath_cut=bath_cut; self.nz=nz; self.osc=osc;self.reflection=reflection;self.eig_tol=eig_tol
        self.states=partitions_upto(bath_cut);self.index={s:i for i,s in enumerate(self.states)}
        self.N=np.array([sum(s) for s in self.states]);self.P=np.array([len(s) for s in self.states])
        self.keep=np.flatnonzero(self.N%2==reflection)
        rows=[];cols=[];modes=[];amplitudes=[]
        for j,s in enumerate(self.states):
            for n in set(s):
                ss=list(s);ss.remove(n);rows.append(self.index[tuple(ss)]);cols.append(j);modes.append(n);amplitudes.append(math.sqrt(s.count(n)))
        self.rows=np.array(rows);self.cols=np.array(cols);self.modes=np.array(modes);self.amp=np.array(amplitudes)
        # Extended quadratures: form powers before projecting out auxiliary top rows.
        d=osc+4;C=diags(np.sqrt(np.arange(1,d)),offsets=-1,shape=(d,d)).toarray();Q=C+C.T;PP=-(C-C.T)@(C-C.T)
        self.q=[np.eye(osc),Q[:osc,:osc],(Q@Q)[:osc,:osc],(Q@Q@Q)[:osc,:osc],(Q@Q@Q@Q)[:osc,:osc]]
        self.pp=PP[:osc,:osc]
        self.local_parity=np.r_[np.zeros(nz,dtype=int),np.ones(nz,dtype=int)]
        self.nB=len(self.keep);self.Ib=eye(self.nB,format='csr');self.Iz=eye(2*nz,format='csr')
        self.field=np.repeat(self.local_parity,self.nB)+np.tile(self.P[self.keep],2*nz)
        self.ix={f:np.flatnonzero(self.field%2==f) for f in (0,1)}
        self.calls=0;self.warm={}
    def set_delta(self,delta):
        if not 0<delta<.25:raise ValueError('Use interior delta; endpoints are limiting theories')
        self.delta=float(delta)
        u=np.ones(self.bath_cut+1)
        for n in range(1,len(u)):u[n]=u[n-1]*math.sqrt((n-1+2*delta)/n)
        B=csr_matrix((self.amp*u[self.modes],(self.rows,self.cols)),shape=(len(self.states),len(self.states)))
        self.W={j:matpower_norm(B,j)[self.keep][:,self.keep].tocsr() for j in range(1,5)}
        self.Hb=diags(self.N[self.keep]+delta*self.P[self.keep])
    def local(self,A,g):
        """q=t(c+c†). Discard only a state-independent scalar in Hz.
        Hz=delta*p^2/4 + A*q^2 +g*q^4/12,
        A=delta/4+r-g/2. Polynomial matrices are projected after multiplication.
        """
        d=self.delta
        # Positive quartic width; enlarge if necessary so both wells are resolved.
        t=(3*d/max(g,1e-16))**(1/6)
        # For weak coupling choose the harmonic scale instead of a broad quartic one.
        if A>0:t=min(t,(d/(4*A))**.25)
        well=math.sqrt(max(0.,-6*A/max(g,1e-16)))
        t=max(t*self.zero_scale,well/math.sqrt(self.osc*.4))
        H=d/(4*t*t)*self.pp+A*t*t*self.q[2]+g*t**4*self.q[4]/12
        U=np.zeros((self.osc,2*self.nz));ww=[]
        for f in (0,1):
            ix=np.arange(f,self.osc,2)
            w,v=eigh(H[np.ix_(ix,ix)],subset_by_index=(0,self.nz-1),check_finite=False)
            U[np.ix_(ix,np.arange(f*self.nz,(f+1)*self.nz))]=v
            ww.extend(w)
        ww=np.array(ww);shift=ww[0];ww=ww-shift
        X={j:U.T@(t**j*self.q[j])@U for j in range(1,4)}
        # Numerical orthogonality and local finite-basis residual diagnostics.
        local_res=float(np.max(np.linalg.norm(H@U-U*(ww+shift)[None,:],axis=0)))
        # residual within finite auxiliary space; cap convergence is checked separately.
        edge=np.sum(U[-8:,:]**2,axis=0)
        return ww,X,U,t,local_res,edge
    def spectrum(self,theta,k=4,diagnostics=False):
        # Scale-free coordinates ensure positivity of g and stability for small delta.
        kap,loge=map(float,theta);e=math.exp(loge);d=self.delta
        g=192*e**3/d**2;A=4*e*e*kap/d;r=A+g/2-d/4
        w,X,U,t,locres,edge=self.local(A,g)
        W=self.W
        # Combine polynomial coefficients before Kronecker assembly to avoid
        # cancellation of r~g/2 terms close to the left endpoint.
        lin=(2*A-d/2)*X[1]+g*X[3]/3
        quad=(A-d/4)*np.eye(2*self.nz)+g*X[2]/2
        H=kron(diags(w),self.Ib,format='csr')+kron(self.Iz,self.Hb,format='csr')
        H=H+kron(csr_matrix(lin),W[1])+kron(csr_matrix(quad),W[2])+g/3*kron(csr_matrix(X[1]),W[3])+g/12*kron(self.Iz,W[4])
        H=H.tocsr();H.eliminate_zeros();out={};maxres=0.
        self.calls+=1
        for f in (0,1):
            ix=self.ix[f];h=H[ix][:,ix].tocsr();kk=min(k,len(ix)-1)
            if len(ix)<=650:
                ww,vv=eigh(h.toarray(),subset_by_index=(0,kk-1),check_finite=False,driver='evr')
            else:
                # Small positive energy shift protects an exactly zero vacuum.
                hs=h-1.23456789*eye(h.shape[0],format='csr')
                ww,vv=eigsh(hs,k=kk,which='SA',tol=self.eig_tol,ncv=min(h.shape[0],max(28,4*kk+4)),maxiter=10000,v0=self.warm.get(f))
                ww+=1.23456789;order=np.argsort(ww);ww=ww[order];vv=vv[:,order]
            self.warm[f]=vv@np.linspace(1.,.6,kk)
            if diagnostics:maxres=max(maxres,float(np.max(np.linalg.norm(h@vv-vv*ww[None,:],axis=0))))
            out[f]=(ww,vv)
        residual=np.array([out[1][0][0]-out[0][0][0]-d,out[1][0][1]-out[0][0][0]-(1-d)])
        return residual,{'r':r,'g':g,'A':A,'local_scale':t,'zero_basis_scale':self.zero_scale,'local_auxiliary_residual':locres,'local_edge_max':float(max(edge[:self.nz-2].max(),edge[self.nz:-2].max())),'max_eigenvector_residual':maxres},out,U
    def initial(self,eps):
        r=.3*eps*eps;g=max(1e-8,eps/3+2*eps*eps)
        A=self.delta/4+r-g/2;e=(g*self.delta**2/192)**(1/3)
        return np.array([A*self.delta/(4*e*e),math.log(e)])
    def solve(self,guess=None,tol=5e-10,maxiter=30,diagnostics=True):
        theta=self.initial(1-4*self.delta) if guess is None else np.array(guess,dtype=float)
        history=[];start=time.time();calls=self.calls
        for it in range(maxiter):
            f,info,out,U=self.spectrum(theta,k=3)
            err=float(max(abs(f)));history.append({'iteration':it,'theta':theta.tolist(),'residual':err})
            if err<tol:break
            jac=np.empty((2,2))
            for j in range(2):
                step=1e-5*max(1,abs(theta[j]));xp=theta.copy();xm=theta.copy();xp[j]+=step;xm[j]-=step
                jac[:,j]=(self.spectrum(xp,k=3)[0]-self.spectrum(xm,k=3)[0])/(2*step)
            dtheta=np.linalg.solve(jac,-f)
            accepted=False
            for ls in range(14):
                test=theta+dtheta*2**(-ls)
                if abs(test[1])>20:continue
                ft=self.spectrum(test,k=3)[0]
                if np.linalg.norm(ft)<np.linalg.norm(f):theta=test;accepted=True;break
            if not accepted:raise RuntimeError(f'No descent delta={self.delta} residual={err}')
        else:raise RuntimeError(f'No convergence delta={self.delta}')
        f,info,out,U=self.spectrum(theta,k=5,diagnostics=True)
        ev,ve=out[0];od,vo=out[1]
        if max(abs(f))>max(1e-8,5*tol):raise RuntimeError('Tuned branch not among expanded low eigenpairs')
        if info['max_eigenvector_residual']>2e-7:raise RuntimeError('Eigenvector gate')
        # Probability of the last two retained local states per parity, in the full states.
        bound=[];bweight=[];lrho=[]
        zedge=np.repeat(np.r_[np.arange(self.nz)>=self.nz-2,np.arange(self.nz)>=self.nz-2],self.nB)
        bedge=np.tile(self.N[self.keep]>=self.bath_cut-1,2*self.nz)
        for ff,jj in ((0,0),(1,0),(0,1),(1,1)):
            ix=self.ix[ff];vv=out[ff][1][:,jj];bound.append(float(np.sum(vv[zedge[ix]]**2)));bweight.append(float(np.sum(vv[bedge[ix]]**2)))
        row={'delta':self.delta,'epsilon':1-4*self.delta,'Delta_thermal':float(ev[1]-ev[0]),'Delta_sigma_measured':float(od[0]-ev[0]),'Delta_shadow_measured':float(od[1]-ev[0]),'even_gaps':(ev-ev[0]).tolist(),'odd_gaps':(od-ev[0]).tolist(),'bath_cut':self.bath_cut,'nz_per_parity':self.nz,'auxiliary_oscillator_size':self.osc,'theta':theta.tolist(),'dimension':2*self.nz*self.nB,'tuning_residual':float(max(abs(f))),'local_retained_edge_weights':bound,'bath_edge_weights':bweight,'seconds':time.time()-start,'spectral_evaluations':self.calls-calls,'history':history,'regulator':'Dressed zero-mode product basis; not the frozen total-energy regulator','scope':'Finite-cutoff raw Hamiltonian only. No claim of complete physical matching.'}
        row.update(info)
        return row


def atomic_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2,allow_nan=False));os.replace(tmp,path)

def main():
    p=argparse.ArgumentParser();p.add_argument('--bath-cut',type=int,default=8);p.add_argument('--nz',type=int,default=8);p.add_argument('--osc',type=int,default=96);p.add_argument('--out',default='../results/dressed');p.add_argument('--min-delta',type=float,default=.001);p.add_argument('--max-delta',type=float,default=.245);p.add_argument('--deltas',type=float,nargs='+');p.add_argument('--seed-results');args=p.parse_args()
    h=DressedZero(args.bath_cut,args.nz,args.osc)
    grid=sorted(set([.245,.24,.235,.23,.225,.22,.21,.20,.19,.18,.175,.17,.16,.15,.14,.13,.125,.12,.11,.10,.09,.08,.075,.07,.06,.05,.04,.03,.025,.02,.015,.0125,.01,.0075,.005,.003,.002,.001,.0005,.0002,.0001]),reverse=True)
    if args.deltas is not None:grid=sorted(set(args.deltas),reverse=True)
    prev=None
    for delta in grid:
        if not args.min_delta<=delta<=args.max_delta:continue
        path=Path(args.out)/f'N{args.bath_cut}_z{args.nz}_o{args.osc}_d{delta:.8f}.json'
        if path.exists():prev=json.loads(path.read_text());continue
        h.set_delta(delta)
        try:
            guess=None if prev is None else prev['theta']
            if args.seed_results:
                seeds=list(Path(args.seed_results).glob(f'N*_z*_o*_d{delta:.8f}.json'))
                if seeds:
                    sr=[json.loads(p.read_text()) for p in seeds]
                    sr.sort(key=lambda x: (abs(x['bath_cut']-args.bath_cut),-x['nz_per_parity']))
                    guess=sr[0]['theta']
            row=h.solve(guess);atomic_json(path,row);prev=row
            print(args.bath_cut,args.nz,delta,row['Delta_thermal'],row['g'],max(row['local_retained_edge_weights']),row['seconds'],flush=True)
        except Exception as ex:
            atomic_json(path.with_suffix('.failure.json'),{'delta':delta,'error':str(ex)});print('FAILED',delta,ex,flush=True);break
if __name__=='__main__':main()
