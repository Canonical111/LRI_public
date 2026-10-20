#!/usr/bin/env python3
"""Integer-count multihistogram/MBAR and thermal observables.

Temperature dependence of the extended FK ensemble is beta**K. Equal integer
K values are grouped exactly, so this is NOT energy-bin approximation. Raw sweep
counts are used for point estimates. Correlated uncertainty is handled by the
stratified block bootstrap in precision_analysis.py, not iid MBAR error formulas.
"""
from __future__ import annotations
import numpy as np
from scipy.special import logsumexp

class MultiHistogram:
    def __init__(self,K,counts,sums,betas,d,L,s,initial=None):
        self.K=np.asarray(K,dtype=float);self.H=np.asarray(counts,dtype=float)
        self.S=np.asarray(sums,dtype=float);self.betas=np.asarray(betas,dtype=float)
        self.d=d;self.L=L;self.s=s
        if self.H.ndim!=2 or self.S.shape!=(4,len(self.K)):raise ValueError('wrong count/moment dimensions')
        self.N=self.H.sum(1);self.total=self.H.sum(0)
        if np.any(self.N<=0) or np.any(self.total<=0) or np.any(self.betas<=0):raise ValueError('empty histogram state or count support')
        self.kref=float(self.total@self.K/self.total.sum());self.q=self.K-self.kref
        self.theta=np.log(self.betas/self.betas[0]);self.theta_q=self.theta[:,None]*self.q
        self.f=self.solve(initial);self.logden=logsumexp(np.log(self.N)[:,None]+self.f[:,None]+self.theta_q,axis=0)
        P=np.exp(np.log(self.N)[:,None]+self.f[:,None]+self.theta_q-self.logden)
        self.overlap=(P*self.total)@P.T/self.N[:,None]
        self.overlap_eigenvalues=np.sort(np.linalg.eigvals(self.overlap).real)[::-1]

    def solve(self,initial):
        n=len(self.N)
        if n==1:return np.zeros(1)
        f=np.zeros(n) if initial is None else np.array(initial,dtype=float)-initial[0]
        logN=np.log(self.N);total=self.total/self.total.sum();fractions=self.N/self.N.sum()
        def parts(v):
            z=logN[:,None]+v[:,None]+self.theta_q;ld=logsumexp(z,axis=0);p=np.exp(z-ld)
            obj=float(total@ld-fractions@v);g=p@total-fractions
            h=np.diag(p@total)-(p*total)@p.T
            return obj,g[1:],h[1:,1:]
        for _ in range(200):
            obj,g,h=parts(f)
            if np.max(np.abs(g))<2e-11:return f
            eigen=np.linalg.eigvalsh(h)
            if eigen[0]<1e-15:raise ValueError('disconnected or numerically singular temperature overlap')
            step=np.linalg.solve(h,g);scale=1
            while scale>1e-7:
                new=f.copy();new[1:]-=scale*step
                if parts(new)[0]<=obj-1e-4*scale*np.dot(g,step)+1e-14:break
                scale*=.5
            f=new
        raise ValueError('multihistogram free-energy solve failed to converge')

    def evaluate(self,beta):
        if beta<=0:raise ValueError('beta must be positive')
        z=np.log(beta/self.betas[0])*self.q-self.logden;w=np.exp(z-z.max())
        norm=self.total@w;prob=self.total*w/norm;q0=prob@self.q;v0=prob@(self.q*self.q)-q0*q0
        moments=(self.S@w)/norm
        qA=(self.S@(w*self.q))/(self.S@w)
        vA=(self.S@(w*self.q**2))/(self.S@w)-qA*qA
        dl=(qA-q0)/beta;ddl=(vA-v0-(qA-q0))/beta**2
        y=self.L**(self.d-self.s)*moments[0]
        values=[[y,y*dl[0],y*(ddl[0]+dl[0]**2)]]
        for j,norm_gauss in enumerate((3.,15.,105.),start=1):
            power=j+1;r=moments[j]/(norm_gauss*moments[0]**power)
            r1=dl[j]-power*dl[0];r2=ddl[j]-power*ddl[0]
            values.append([1-r,-r*r1,-r*(r2+r1*r1)])
        ess=norm*norm/(self.total.sum()*(self.total@(w*w)))
        return np.array(values),float(ess)

    def diagnostics(self):
        p=self.H/self.N[:,None];bc=np.sqrt(p[:-1]*p[1:]).sum(1)
        return {'betas':self.betas.tolist(),'free_energies_gauge_f0_zero':self.f.tolist(),
                'overlap_matrix':self.overlap.tolist(),'overlap_eigenvalues':self.overlap_eigenvalues.tolist(),
                'adjacent_histogram_affinities':bc.tolist(),
                'warning': 'Near-unit second overlap eigenvalue or very small affinity requires intermediate temperatures.'}
