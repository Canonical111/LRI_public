"""Hellmann-Feynman response of the moving finite zero-mode subspace.

Finite differences are taken of projected Hamiltonian expectation values,
including the parameter dependence of its zero-mode basis (Pulay response).
No extra full many-body eigensolve is needed for each Jacobian column.
This is not the incomplete fixed-basis Hellmann-Feynman approximation.
"""
import math,time
import numpy as np
from dressed_zero import DressedZero

class FastDressedZero(DressedZero):
    def projected_expectations(self,theta,states,Uref):
        kap,loge=map(float,theta);energy=math.exp(loge);d=self.delta
        g=192*energy**3/d**2;A=4*energy*energy*kap/d
        w,X,U,t,*_=self.local(A,g)
        signs=np.sign(np.sum(U*Uref,axis=0));signs[signs==0]=1
        X={j:v*signs[:,None]*signs[None,:] for j,v in X.items()}
        lin=(2*A-d/2)*X[1]+g*X[3]/3
        quad=(A-d/4)*np.eye(2*self.nz)+g*X[2]/2
        ans=[]
        for field,vec in states:
            coeff=np.zeros((2*self.nz,self.nB));coeff.ravel()[self.ix[field]]=vec
            action=w[:,None]*coeff+(self.Hb@coeff.T).T
            action+=lin@(self.W[1]@coeff.T).T
            action+=quad@(self.W[2]@coeff.T).T
            action+=g/3*X[1]@(self.W[3]@coeff.T).T
            action+=g/12*(self.W[4]@coeff.T).T
            ans.append(float(np.sum(coeff*action)))
        return np.array(ans)
    def response_jacobian(self,theta,out,U,step_scale=1e-5):
        states=[(0,out[0][1][:,0]),(1,out[1][1][:,0]),(1,out[1][1][:,1])]
        jac=np.empty((2,2))
        for j in range(2):
            h=step_scale*max(1,abs(theta[j]));plus=np.array(theta);minus=np.array(theta);plus[j]+=h;minus[j]-=h
            dp=(self.projected_expectations(plus,states,U)-self.projected_expectations(minus,states,U))/(2*h)
            jac[:,j]=dp[1:]-dp[0]
        return jac
    def solve(self,guess=None,tol=5e-10,maxiter=30,diagnostics=True):
        theta=self.initial(1-4*self.delta) if guess is None else np.array(guess,dtype=float)
        history=[];start=time.time();calls=self.calls;cache=None
        for it in range(maxiter):
            f,info,out,U=self.spectrum(theta,k=3) if cache is None else cache
            err=float(max(abs(f)));history.append({'iteration':it,'theta':theta.tolist(),'residual':err})
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
        ev,ve=out[0];od,vo=out[1]
        if max(abs(f))>max(1e-8,5*tol):raise RuntimeError('Expanded eigenpair gate')
        if info['max_eigenvector_residual']>2e-7:raise RuntimeError('Eigenvector residual gate')
        bound=[];bweight=[]
        zedge=np.repeat(np.r_[np.arange(self.nz)>=self.nz-2,np.arange(self.nz)>=self.nz-2],self.nB)
        bedge=np.tile(self.N[self.keep]>=self.bath_cut-1,2*self.nz)
        for ff,jj in ((0,0),(1,0),(0,1),(1,1)):
            ix=self.ix[ff];vv=out[ff][1][:,jj];bound.append(float(np.sum(vv[zedge[ix]]**2)));bweight.append(float(np.sum(vv[bedge[ix]]**2)))
        row={'delta':self.delta,'epsilon':1-4*self.delta,'Delta_thermal':float(ev[1]-ev[0]),'Delta_sigma_measured':float(od[0]-ev[0]),'Delta_shadow_measured':float(od[1]-ev[0]),'even_gaps':(ev-ev[0]).tolist(),'odd_gaps':(od-ev[0]).tolist(),'bath_cut':self.bath_cut,'nz_per_parity':self.nz,'auxiliary_oscillator_size':self.osc,'theta':theta.tolist(),'dimension':2*self.nz*self.nB,'tuning_residual':float(max(abs(f))),'local_retained_edge_weights':bound,'bath_edge_weights':bweight,'seconds':time.time()-start,'spectral_evaluations':self.calls-calls,'history':history,'regulator':'Dressed zero-mode product basis; not the frozen total-energy regulator','scope':'Finite-cutoff raw Hamiltonian only. No claim of complete physical matching.','solver':'moving-subspace response Jacobian'}
        row.update(info);return row
