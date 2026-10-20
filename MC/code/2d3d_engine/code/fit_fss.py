#!/usr/bin/env python3
"""Joint finite-size fit with independent simulated temperatures and block bootstrap.

F_Q(x)+r^(-omega)G_Q(x), Q=Y,U; r=L/L_ref,
x=100*(beta-beta_c)*r^(d-Delta_epsilon).
All six observables and their within-point covariance are used. Linear amplitudes
are profiled out. Neither six-loop coefficients nor endpoint CFT data are inputs.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
from scipy.linalg import solve_triangular
from scipy.optimize import least_squares
from scipy.stats import chi2
from analyze import cft_observables

class ProfileFit:
    def __init__(self, entries: list[dict], degree: int=3, correction_degree: int=2,
                 variant: str='leading', omega_bounds: tuple[float,float]=(.005,3.)):
        self.entries=entries;self.degree=degree;self.cdegree=correction_degree
        self.variant=variant;self.omega_bounds=omega_bounds
        self.s=float(entries[0]['s']);self.dim=int(entries[0]['d']);self.L=np.array([e['L'] for e in entries],float)
        self.Lref=float(np.exp(np.mean(np.log(np.unique(self.L)))));self.r=self.L/self.Lref;self.beta=np.array([e['beta'] for e in entries]);self.ref=float(np.median(self.beta))
        self.data=np.array([e['data'] for e in entries]);cov=np.array([e['cov'] for e in entries])
        # Normalize covariance before Cholesky to avoid derivative scale problems.
        self.scale=np.sqrt(np.diagonal(cov,axis1=1,axis2=2))
        if np.any(self.scale<=0):raise ValueError('zero sampling variance; collect more data')
        corr=cov/self.scale[:,:,None]/self.scale[:,None,:]
        self.chol=np.linalg.cholesky(corr) # no silently added covariance regularizer
        self.cov_condition=np.array([np.linalg.cond(c) for c in corr])
        self.lower=np.array([-2.,.001,omega_bounds[0]])
        self.upper=np.array([2.,self.dim-.001,omega_bounds[1]])

    def whiten(self, arr):
        if arr.ndim==2:return np.concatenate([solve_triangular(c,z/sc,lower=True) for c,z,sc in zip(self.chol,arr,self.scale)])
        return np.concatenate([solve_triangular(c,z/sc[:,None],lower=True) for c,z,sc in zip(self.chol,arr,self.scale)])

    def design(self,p):
        k,de,om=p;y=self.dim-de;r=self.r
        x=(100*(self.beta-self.ref)-k)*r**y;D=100*r**y;z=r**(-om)
        def monomial(power):
            a=x**power;b=power*x**(power-1)*D if power else np.zeros_like(x)
            c=power*(power-1)*x**(power-2)*D**2 if power>=2 else np.zeros_like(x)
            return np.stack([a,b,c],axis=1)
        base=[monomial(i) for i in range(self.degree+1)]
        base += [z[:,None]*monomial(i) for i in range(self.cdegree+1)]
        basis=[base.copy(),base.copy()]
        if self.variant in ('background','both'):
            # Regular susceptibility background L^(-s), analytic in beta.
            v=r**(-self.s);zeros=np.zeros_like(v)
            basis[0]+=[np.stack([v,zeros,zeros],axis=1),
                       np.stack([v*100*(self.beta-self.ref),100*v,zeros],axis=1)]
        if self.variant in ('second','both'):
            for b in basis:b += [z[:,None]**2*monomial(i) for i in range(2)]
        A=np.zeros((len(x),6,sum(len(b) for b in basis)));pos=0
        for j,b in enumerate(basis):
            for v in b:A[:,3*j:3*j+3,pos]=v;pos+=1
        return A

    def fit(self,data=None,initial=None,multistart=True):
        data=self.data if data is None else np.asarray(data);vec=self.whiten(data)
        def solve(p,details=False):
            A=self.design(p);AA=self.whiten(A)
            scale=np.maximum(np.linalg.norm(AA,axis=0),1e-100);An=AA/scale
            coeff,_,rank,sv=np.linalg.lstsq(An,vec,rcond=1e-12)
            res=An@coeff-vec
            return (res,coeff/scale,rank,sv,A@(coeff/scale)) if details else res
        starts=[]
        if initial is not None:starts.append(np.asarray(initial))
        if multistart or not starts:
            starts += [np.array([0.,de,om]) for de,om in [(self.dim/2-.03,.15),(self.dim/2-.08,.4),(self.dim/2-.03,.8),(self.dim/2-.05,1.5)]]
        starts=[np.clip(p,self.lower+1e-6,self.upper-1e-6) for p in starts]
        sols=[least_squares(solve,p,bounds=(self.lower,self.upper),x_scale='jac',
            max_nfev=1000,ftol=1e-10,xtol=1e-10,gtol=1e-8) for p in starts]
        sol=min(sols,key=lambda q:np.dot(q.fun,q.fun));res,amp,rank,sv,pred=solve(sol.x,True)
        nlin=len(amp);dof=data.size-nlin-3;h=sol.jac.T@sol.jac;hrank=np.linalg.matrix_rank(h)
        pcov=np.linalg.pinv(h,rcond=1e-12);stat=float(np.sqrt(max(0.,pcov[1,1]))) if hrank==3 else None
        bound=bool(np.any((sol.x-self.lower)<1e-4*(self.upper-self.lower)) or np.any((self.upper-sol.x)<1e-4*(self.upper-self.lower)))
        flags=[]
        if bound:flags.append('nonlinear parameter at search boundary')
        if rank<nlin:flags.append('linear amplitude rank deficient')
        if hrank<3:flags.append('profile Hessian rank deficient')
        if not sol.success:flags.append('optimizer did not converge')
        if dof<=0:flags.append('nonpositive degrees of freedom')
        if dof>0 and chi2.sf(float(res@res),dof)<.05:flags.append('poor nominal goodness of fit (p<0.05)')
        if np.max(self.cov_condition)>1e10:flags.append('sampling covariance poorly conditioned')
        return dict(d=self.dim,s=self.s,Delta_sigma=(self.dim-self.s)/2,Delta_epsilon=float(sol.x[1]),
            conditional_statistical_error=stat,beta_c=float(self.ref+sol.x[0]/100),
            omega_correction=float(sol.x[2]),chi2=float(res@res),dof=dof,
            chi2_pvalue=float(chi2.sf(res@res,dof)) if dof>0 else None,
            parameters=sol.x.tolist(),amplitudes=amp.tolist(),linear_rank=int(rank),nlinear=nlin,
            profile_Hessian_rank=int(hrank),flags=flags,predictions=pred.tolist(),
            degree=self.degree,correction_degree=self.cdegree,variant=self.variant,
            Lmin=int(self.L.min()),Lmax=int(self.L.max()),L_reference=self.Lref,distinct_sizes=int(len(np.unique(self.L))),
            simulated_points=len(self.L),success=bool(sol.success),max_covariance_condition=float(max(self.cov_condition)))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('summary',type=Path);p.add_argument('--dim',type=int,required=True);p.add_argument('--s',type=float,required=True)
    p.add_argument('--lmin',type=int,default=4);p.add_argument('--lmax',type=int,default=2**28)
    p.add_argument('--variant',choices=['leading','background','second','both'],default='leading')
    p.add_argument('--degree',type=int,default=3);p.add_argument('--correction-degree',type=int,default=2)
    p.add_argument('--omega-min',type=float,default=.005);p.add_argument('--omega-max',type=float,default=3.)
    p.add_argument('--beta-center',type=float);p.add_argument('--beta-halfwidth',type=float)
    p.add_argument('--bootstrap',type=int,default=0);p.add_argument('--seed',type=int,default=981724)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    if not 1<=a.degree<=5 or not 0<=a.correction_degree<=3 or a.bootstrap<0:p.error('invalid degrees or bootstrap count')
    if not 0<a.omega_min<a.omega_max:p.error('require 0 < omega-min < omega-max')
    allentries=json.loads(a.summary.read_text())['entries']
    entries=[e for e in allentries if e['d']==a.dim and abs(e['s']-a.s)<1e-12 and a.lmin<=e['L']<=a.lmax]
    if a.beta_halfwidth is not None:
        if a.beta_center is None:p.error('--beta-halfwidth requires --beta-center')
        entries=[e for e in entries if abs(e['beta']-a.beta_center)<=a.beta_halfwidth]
    if len({e['L'] for e in entries})<3:p.error('at least three distinct sizes are required; four or more recommended')
    if any(abs(e['beta']-e.get('beta_simulated',e['beta']))>1e-14 for e in entries):
        p.error('do not treat reweighted points as independent FSS data')
    model=ProfileFit(entries,a.degree,a.correction_degree,a.variant,(a.omega_min,a.omega_max))
    nlinear=model.design([0,.5,.4]).shape[-1]
    if len(entries)*6<=nlinear+3:p.error('not enough independent data for this model')
    result=model.fit();result['error_note']='Statistical errors condition on the finite-size model, temperature window and equilibrium assumption; not total physical errors.'
    print(json.dumps({k:v for k,v in result.items() if k not in ('amplitudes','predictions')},indent=2),flush=True)
    if a.bootstrap:
        rng=np.random.default_rng(a.seed);sources=[]
        for e in entries:
            with np.load(a.summary.parent/e['blocks_file']) as z:
                b=z['blocks'];r=z['replicas'];sources.append([b[r==i] for i in np.unique(r)])
        draws=[]
        for ib in range(a.bootstrap):
            vals=[]
            for e,replica_blocks in zip(entries,sources):
                # Preserve replica allocation; resample long time blocks independently within each chain.
                total=np.zeros((4,3));nblocks=0
                for b in replica_blocks:
                    sample=b[rng.integers(len(b),size=len(b))];total+=sample.sum(axis=0);nblocks+=len(b)
                vals.append(cft_observables(total/nblocks,e['N'],e['s'],e['beta'],e['d']))
            f=model.fit(vals,initial=result['parameters'],multistart=False)
            draws.append({k:f[k] for k in ('Delta_epsilon','beta_c','omega_correction','flags','success')})
            if (ib+1)%10==0:print(f'bootstrap {ib+1}/{a.bootstrap}',flush=True)
        valid=np.array([d['Delta_epsilon'] for d in draws if d['success'] and not d['flags']])
        result['bootstrap']=dict(requested=a.bootstrap,valid=len(valid),flagged_or_failed=a.bootstrap-len(valid),draws=draws,
            percentile_16_50_84=np.percentile(valid,[16,50,84]).tolist() if len(valid) else None,
            note='Conditional block bootstrap; flagged fits retained in draws. Assess optimizer minima and model changes separately.')
    out=a.out or a.summary.parent/f'fit_d{a.dim}_s{a.s}_Lmin{a.lmin}_{a.variant}_deg{a.degree}.json'
    out.write_text(json.dumps(result,indent=2)+'\n');print(out)
if __name__=='__main__':main()
