"""Direct spectra and safeguarded moving-subspace response tuning.

This computes the SAME bare, finite product-regulator Hamiltonian as the
reference. It does not introduce effective-Hamiltonian matching or change caps.
"""
from __future__ import annotations
import math,time
import numpy as np
from scipy.linalg import eigh
from scipy.sparse.linalg import eigsh,ArpackNoConvergence
from .basis import BathBasis
from .local import LocalProblem
from .operators import ProductOperator

class DressedSolver:
    def __init__(self,bath_cut=12,nz=20,osc=160,reflection=0,eig_tol=3e-11,
                 zero_scale=1.,backend='auto',ncv=28,max_eig_iter=10000,residual_tol=2e-7,
                 checkpoint=None,basis=None):
        if reflection not in (0,1):raise ValueError('reflection must be 0 or 1')
        if bath_cut<2:raise ValueError('bath cutoff must be >=2')
        if not 0<=eig_tol<1 or residual_tol<=0:raise ValueError('Invalid solver tolerances')
        if backend=='auto':backend='tensor' if bath_cut<=18 else 'ladder'
        self.backend=backend;self.bath_cut=int(bath_cut);self.nz=int(nz);self.osc=int(osc);self.reflection=int(reflection)
        self.eig_tol=eig_tol;self.ncv=int(ncv);self.max_eig_iter=max_eig_iter;self.residual_tol=residual_tol
        self.local_problem=LocalProblem(nz,osc,zero_scale);self.checkpoint=checkpoint
        t=time.perf_counter();self.basis=basis or BathBasis.build(bath_cut)
        if self.basis.cutoff!=bath_cut:raise ValueError('basis cutoff mismatch')
        self.timings={'basis':time.perf_counter()-t,'bath_operators':0.,'local':0.,'eigensolver':0.,'jacobian':0.}
        self.warm={};self.calls=0;self.delta=None;self.op=None

    def set_delta(self,delta):
        if not np.isfinite(delta) or not 0<delta<.25:raise ValueError('Require 0<Delta_sigma<1/4')
        t=time.perf_counter();self.delta=float(delta)
        self.op=None;self.warm.clear();self._warm_U=None
        self.op=ProductOperator(self.basis,delta,self.nz,self.reflection,self.backend)
        self.timings['bath_operators']+=time.perf_counter()-t
        self.warm={}

    def initial(self,eps):
        r=.3*eps*eps;g=max(1e-8,eps/3+2*eps*eps)
        A=self.delta/4+r-g/2;e=(g*self.delta**2/192)**(1/3)
        return np.array([A*self.delta/(4*e*e),math.log(e)])

    def spectrum(self,theta,k=4,diagnostics=False):
        if self.op is None:raise RuntimeError('Call set_delta first')
        t=time.perf_counter();w,L,U,info=self.local_problem.evaluate(self.delta,theta)
        self.timings['local']+=time.perf_counter()-t
        # Align only the gauge/sign of the previous warm vector to the new local
        # basis. This changes initialization, not the operator or spectrum.
        if self._warm_U is not None:
            signs=np.sign(np.sum(U*self._warm_U,axis=0));signs[signs==0]=1
            for f in self.warm:
                factor=signs.reshape(2,self.nz)[self.op.kpar^f]
                self.warm[f]=(self.warm[f].reshape(self.op.nB,self.nz)*factor).ravel()
        self._warm_U=U.copy()
        out={};maxres=0.;maxorth=0.;self.calls+=1
        for f in (0,1):
            h=self.op.linear_operator(w,L,f);n=h.shape[0];kk=min(k,n-1)
            t=time.perf_counter()
            if n<=650:
                # Preserve the original dense threshold for small blocks.
                H=h@np.eye(n)
                ww,vv=eigh(H,subset_by_index=(0,kk-1),check_finite=False,driver='evr')
            else:
                hs=self.op.linear_operator(w,L,f,1.23456789)
                v0=self.warm.get(f)
                if v0 is None:v0=np.random.default_rng(4901+f).normal(size=n)
                ww,vv=eigsh(hs,k=kk,which='SA',tol=self.eig_tol,
                    ncv=min(n,max(self.ncv,4*kk+4)),maxiter=self.max_eig_iter,v0=v0)
                ww+=1.23456789;order=np.argsort(ww);ww=ww[order];vv=vv[:,order]
            self.timings['eigensolver']+=time.perf_counter()-t
            self.warm[f]=vv@np.linspace(1.,.6,kk)
            if diagnostics:
                maxres=max(maxres,float(np.max(np.linalg.norm(h@vv-vv*ww[None,:],axis=0))))
                maxorth=max(maxorth,float(np.max(abs(vv.T@vv-np.eye(kk)))))
            out[f]=(ww,vv)
        info['max_eigenvector_residual']=maxres;info['max_orthogonality_residual']=maxorth
        residual=np.array([out[1][0][0]-out[0][0][0]-self.delta,out[1][0][1]-out[0][0][0]-(1-self.delta)])
        return residual,info,out,U

    def response_jacobian(self,theta,out,Uref,step_scale=1e-5):
        t=time.perf_counter()
        con=[self.op.contractions(out[f][1][:,j],f) for f,j in ((0,0),(1,0),(1,1))]
        jac=np.empty((2,2))
        for j in range(2):
            h=step_scale*max(1,abs(theta[j]));vals=[]
            for sign in (1,-1):
                th=np.array(theta);th[j]+=sign*h
                w,L,U,info=self.local_problem.evaluate(self.delta,th)
                signs=np.sign(np.sum(U*Uref,axis=0));signs[signs==0]=1
                L=L*signs[None,:,None]*signs[None,None,:]
                vals.append(np.array([weights@w+np.sum(corr*L)+bath for weights,corr,bath in con]))
            dp=(vals[0]-vals[1])/(2*h);jac[:,j]=dp[1:]-dp[0]
        self.timings['jacobian']+=time.perf_counter()-t
        return jac

    def solve(self,guess=None,tol=5e-10,maxiter=30,diagnostics=True):
        if self.reflection!=0:raise ValueError('Primary tuning requires reflection=0; use spectrum for odd diagnostics')
        theta=self.initial(1-4*self.delta) if guess is None else np.array(guess,dtype=float)
        history=[];start=time.perf_counter();calls=self.calls;cache=None
        for it in range(maxiter):
            f,info,out,U=self.spectrum(theta,k=3) if cache is None else cache
            err=float(max(abs(f)));history.append({'iteration':it,'theta':theta.tolist(),'residual':err})
            if self.checkpoint:self.checkpoint(theta,history)
            if err<tol:break
            jac=self.response_jacobian(theta,out,U)
            history[-1]['jacobian_condition']=float(np.linalg.cond(jac))
            dtheta=np.linalg.solve(jac,-f);accepted=False
            for ls in range(14):
                test=theta+dtheta*2**(-ls)
                if abs(test[1])>20:continue
                new=self.spectrum(test,k=3)
                if np.linalg.norm(new[0])<np.linalg.norm(f):theta=test;cache=new;accepted=True;break
            if not accepted:raise RuntimeError(f'No descent delta={self.delta} residual={err}')
        else:raise RuntimeError(f'No convergence delta={self.delta}')
        f,info,out,U=self.spectrum(theta,k=5,diagnostics=True)
        ev=out[0][0];od=out[1][0]
        if max(abs(f))>max(1e-8,5*tol):raise RuntimeError('Expanded eigenpair gate failed')
        if info['max_eigenvector_residual']>self.residual_tol:raise RuntimeError('Eigenvector residual gate failed')
        if info['max_orthogonality_residual']>1e-9:raise RuntimeError('Eigenvector orthogonality gate failed')
        bound=[];bweight=[]
        for ff,jj in ((0,0),(1,0),(0,1),(1,1)):
            v=out[ff][1][:,jj].reshape(self.op.nB,self.nz)
            bound.append(float(np.sum(v[:,-2:]**2)))
            edge=self.basis.N[self.op.keep]>=self.bath_cut-1
            bweight.append(float(np.sum(v[edge]**2)))
        row={'delta':self.delta,'epsilon':1-4*self.delta,'Delta_thermal':float(ev[1]-ev[0]),
            'Delta_sigma_measured':float(od[0]-ev[0]),'Delta_shadow_measured':float(od[1]-ev[0]),
            'even_gaps':(ev-ev[0]).tolist(),'odd_gaps':(od-ev[0]).tolist(),'bath_cut':self.bath_cut,
            'nz_per_parity':self.nz,'auxiliary_oscillator_size':self.osc,'theta':theta.tolist(),
            'dimension':2*self.op.dim,'tuning_residual':float(max(abs(f))),
            'local_retained_edge_weights':bound,'bath_edge_weights':bweight,
            'seconds':time.perf_counter()-start,'spectral_evaluations':self.calls-calls,'history':history,
            'regulator':'Dressed zero-mode product basis; not the frozen total-energy regulator',
            'scope':'Finite-cutoff raw Hamiltonian only. No claim of complete physical matching.',
            'solver':'factorized operator; moving-subspace reduced-density response Jacobian',
            'backend':self.backend,'timings':dict(self.timings),'matvec_count':self.op.matvec_count,
            'matvec_seconds':self.op.matvec_seconds,'operator_storage_bytes':self.op.nbytes}
        row.update(info);return row
