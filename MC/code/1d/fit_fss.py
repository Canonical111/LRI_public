#!/usr/bin/env python3
"""Joint finite-size fit with independent simulated temperatures and block bootstrap.

F_Q(x)+r^(-omega)G_Q(x), Q=Y,U; r=N/1024,
x = tau(beta) * r^(1-Delta_epsilon),  tau = 100 [v + a_1 v^2 + ... + a_{K-1} v^K],  v = beta - beta_c
(K = --field-order; K=1 is the linear field x = 100(beta-beta_c) r^(1-Delta_epsilon) of the original protocol).
All six observables and their within-point covariance are used (--drop-second removes the second derivatives, for
diagnostics only). Linear amplitudes are profiled out. Neither six-loop coefficients nor endpoint CFT data are inputs.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
from scipy.linalg import solve_triangular
from scipy.optimize import least_squares
from scipy.stats import chi2
from analyze import cft_observables
from bootstrap_schedule import block_indices

class ProfileFit:
    def __init__(self, entries: list[dict], degree: int=3, correction_degree: int=2,
                 variant: str='leading', omega_bounds: tuple[float,float]=(.005,3.), field_order: int=1,
                 drop_second: bool=False):
        self.entries=entries;self.degree=degree;self.cdegree=correction_degree
        self.variant=variant;self.omega_bounds=omega_bounds;self.field_order=field_order;self.drop_second=drop_second
        # observable rows used: all six, or the four without second derivatives
        self.rows=[0,1,3,4] if drop_second else [0,1,2,3,4,5];self.nobs=len(self.rows)
        self.s=float(entries[0]['s']);self.L=np.array([e['N'] for e in entries],float)
        self.r=self.L/1024;self.beta=np.array([e['beta'] for e in entries]);self.ref=float(np.median(self.beta))
        self.data=np.array([e['data'] for e in entries])[:,self.rows]
        cov=np.array([e['cov'] for e in entries])[:,self.rows][:,:,self.rows]
        # Normalize covariance before Cholesky to avoid derivative scale problems.
        self.scale=np.sqrt(np.diagonal(cov,axis1=1,axis2=2))
        if np.any(self.scale<=0):raise ValueError('zero sampling variance; collect more data')
        corr=cov/self.scale[:,:,None]/self.scale[:,None,:]
        self.chol=np.linalg.cholesky(corr) # no silently added covariance regularizer
        self.cov_condition=np.array([np.linalg.cond(c) for c in corr])
        # nonlinear parameters: k (beta_c offset x100), Delta_epsilon, omega, a_1..a_{K-1} of the scaling field, and for the
        # 'log' variant the two amplitudes c_Y, c_U of the correction F_Q(x) c_Q / ln(N/256) (FIT_MODEL_V3 §4.8)
        self.nfield=field_order-1;self.nlog=2 if variant=='log' else 0
        self.lower=np.array([-2.,.001,omega_bounds[0]]+[-50.]*self.nfield+[-5.]*self.nlog)
        self.upper=np.array([2.,.999,omega_bounds[1]]+[50.]*self.nfield+[5.]*self.nlog)
        self.npar=len(self.lower)

    def colour(self, white):
        """Inverse of whiten for a stacked vector: returns (points x nobs) data with the points' sampling covariance."""
        w=white.reshape(len(self.L),self.nobs)
        return np.stack([sc*(c@z) for c,z,sc in zip(self.chol,w,self.scale)])
    def whiten(self, arr):
        if arr.ndim==2:return np.concatenate([solve_triangular(c,z/sc,lower=True) for c,z,sc in zip(self.chol,arr,self.scale)])
        return np.concatenate([solve_triangular(c,z/sc[:,None],lower=True) for c,z,sc in zip(self.chol,arr,self.scale)])

    def field(self,p):
        """Scaling field tau(beta) in units of 100*(beta-beta_c), and its first two beta derivatives."""
        k=p[0];acoef=np.asarray(p[3:3+self.nfield]);v=(self.beta-self.ref)-k/100   # v = beta - beta_c
        tau=v.copy();d1=np.ones_like(v);d2=np.zeros_like(v)
        for j,aj in enumerate(acoef,start=1):
            tau=tau+aj*v**(j+1);d1=d1+aj*(j+1)*v**j;d2=d2+aj*(j+1)*j*v**(j-1)
        return 100*tau,100*d1,100*d2
    def design(self,p):
        de,om=p[1],p[2];y=1-de;r=self.r
        tau,t1,t2=self.field(p)
        x=tau*r**y;D1=t1*r**y;D2=t2*r**y;z=r**(-om)
        def monomial(power):
            a=x**power;b=power*x**(power-1)*D1 if power else np.zeros_like(x)
            c=(power*(power-1)*x**(power-2)*D1**2 if power>=2 else np.zeros_like(x))+(power*x**(power-1)*D2 if power else np.zeros_like(x))
            return np.stack([a,b,c],axis=1)
        fpart=[monomial(i) for i in range(self.degree+1)]
        gpart=[z[:,None]*monomial(i) for i in range(self.cdegree+1)]
        if self.variant=='log':
            # regime-A correction (FIT_MODEL_V3 §4.8): F_Q(x) [1 + c_Q / ln(N/N0)], N0 = 256, one nonlinear amplitude per observable
            # family (Y, Y', Y'' share c_Y; U, U', U'' share c_U); c_Q = 0 reduces exactly to 'leading'
            lg=1/np.log(self.L/256.);cs=p[3+self.nfield:3+self.nfield+2]
            basis=[[(1+c*lg)[:,None]*m for m in fpart]+list(gpart) for c in cs]
        else:basis=[list(fpart)+list(gpart),list(fpart)+list(gpart)]
        if self.variant in ('background','both'):
            # Regular susceptibility background N^(-s), analytic in beta.
            v=r**(-self.s);zeros=np.zeros_like(v)
            basis[0]+=[np.stack([v,zeros,zeros],axis=1),
                       np.stack([v*100*(self.beta-self.ref),100*v,zeros],axis=1)]
        if self.variant in ('second','both'):
            for b in basis:b += [z[:,None]**2*monomial(i) for i in range(2)]
        A=np.zeros((len(x),6,sum(len(b) for b in basis)));pos=0
        for j,b in enumerate(basis):
            for v in b:A[:,3*j:3*j+3,pos]=v;pos+=1
        return A[:,self.rows,:]

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
            starts += [np.array([0.,de,om]+[0.]*(self.npar-3)) for de,om in [(.5,.15),(.6,.4),(.5,.8),(.7,1.5)]]
        starts=[np.clip(p,self.lower+1e-6,self.upper-1e-6) for p in starts]
        sols=[least_squares(solve,p,bounds=(self.lower,self.upper),x_scale='jac',
            max_nfev=1000,ftol=1e-10,xtol=1e-10,gtol=1e-8) for p in starts]
        sol=min(sols,key=lambda q:np.dot(q.fun,q.fun));res,amp,rank,sv,pred=solve(sol.x,True)
        nlin=len(amp);dof=data.size-nlin-self.npar;h=sol.jac.T@sol.jac;hrank=np.linalg.matrix_rank(h)
        pcov=np.linalg.pinv(h,rcond=1e-12);stat=float(np.sqrt(max(0.,pcov[1,1]))) if hrank==self.npar else None
        bound=bool(np.any((sol.x-self.lower)<1e-4*(self.upper-self.lower)) or np.any((self.upper-sol.x)<1e-4*(self.upper-self.lower)))
        flags=[]
        if bound:flags.append('nonlinear parameter at search boundary')
        if rank<nlin:flags.append('linear amplitude rank deficient')
        if hrank<self.npar:flags.append('profile Hessian rank deficient')
        if not sol.success:flags.append('optimizer did not converge')
        if dof<=0:flags.append('nonpositive degrees of freedom')
        if np.max(self.cov_condition)>1e10:flags.append('sampling covariance poorly conditioned')
        # observable-normalised pulls (residual / own standard error) per point, ordered as the entries; per-size whitened chi2
        pulls=(pred-data)/self.scale;res_pts=res.reshape(len(self.L),self.nobs)
        obs_names=[['Y',"Y'","Y''",'U',"U'","U''"][i] for i in self.rows]
        per_size={}
        for i,N in enumerate(self.L):per_size[int(N)]=per_size.get(int(N),0.)+float(np.sum(res_pts[i]**2))
        return dict(Delta_sigma=(1-self.s)/2,Delta_epsilon=float(sol.x[1]),
            conditional_statistical_error=stat,beta_c=float(self.ref+sol.x[0]/100),
            omega_correction=float(sol.x[2]),chi2=float(res@res),dof=dof,
            chi2_pvalue=float(chi2.sf(res@res,dof)) if dof>0 else None,
            parameters=sol.x.tolist(),amplitudes=amp.tolist(),linear_rank=int(rank),nlinear=nlin,
            profile_Hessian_rank=int(hrank),flags=flags,predictions=pred.tolist(),
            degree=self.degree,correction_degree=self.cdegree,variant=self.variant,
            Nmin=int(self.L.min()),Nmax=int(self.L.max()),distinct_sizes=int(len(np.unique(self.L))),
            simulated_points=len(self.L),success=bool(sol.success),max_covariance_condition=float(max(self.cov_condition)),
            field_order=self.field_order,field_coefficients=sol.x[3:3+self.nfield].tolist(),nonlinear_parameters=int(self.npar),
            log_coefficients=(sol.x[3+self.nfield:3+self.nfield+2].tolist() if self.variant=='log' else None),
            observables=obs_names,drop_second=self.drop_second,
            mean_abs_pull={n:float(np.mean(np.abs(pulls[:,j]))) for j,n in enumerate(obs_names)},
            pulls=[dict(N=int(N),beta=float(b),pull=pulls[i].tolist()) for i,(N,b) in enumerate(zip(self.L,self.beta))],
            chi2_per_size=per_size,whitened_residuals=res.tolist())

ERROR_NOTE='Statistical errors condition on the finite-size model, temperature window and equilibrium assumption; not total physical errors.'

def load_entries(summary: Path, s: float, lmin: int=1024, lmax: int=2**28, beta_center=None, beta_halfwidth=None):
    """Independent simulated points of one s inside [lmin,lmax] (and an optional beta window)."""
    allentries=json.loads(Path(summary).read_text())['entries']
    entries=[e for e in allentries if abs(e['s']-s)<1e-12 and lmin<=e['N']<=lmax]
    if beta_halfwidth is not None:
        if beta_center is None:raise ValueError('--beta-halfwidth requires --beta-center')
        entries=[e for e in entries if abs(e['beta']-beta_center)<=beta_halfwidth]
    if len({e['N'] for e in entries})<4:raise ValueError('at least four distinct sizes are required')
    if any(abs(e['beta']-e.get('beta_simulated',e['beta']))>1e-14 for e in entries):
        raise ValueError('do not treat reweighted points as independent FSS data')
    return entries

def load_sources(summary: Path, entries):
    """Per entry: list of (replica id, blocks array) read from the summary's block files."""
    sources=[]
    for e in entries:
        with np.load(Path(summary).parent/e['blocks_file']) as z:
            b=z['blocks'];r=z['replicas'];sources.append([(int(i),b[r==i]) for i in np.unique(r)])
    return sources

def resample_data(entries, sources, rng, schedule, draw):
    """One block-bootstrap resample of all entries: (points x 6) observables. Replica allocation preserved; blocks
    resampled independently within each chain, with indices from the shared schedule when `schedule` is not None."""
    vals=[]
    for e,replica_blocks in zip(entries,sources):
        total=np.zeros((4,3));nblocks=0
        for rep_id,b in replica_blocks:
            idx=block_indices(schedule,e['s'],e['N'],e['beta'],rep_id,draw,len(b),campaign=e.get('campaign')) if schedule is not None else rng.integers(len(b),size=len(b))
            total+=b[idx].sum(axis=0);nblocks+=len(b)
        vals.append(cft_observables(total/nblocks,e['N'],e['s'],e['beta']))
    return np.asarray(vals)

def run_fit(summary: Path, entries, degree=3, correction_degree=2, variant='leading', omega_bounds=(.005,3.),
            field_order=1, drop_second=False, bootstrap=0, seed=981724, schedule=None, tag='', verbose=False):
    """Central fit plus optional block bootstrap; returns the result dictionary written by the CLI."""
    model=ProfileFit(entries,degree,correction_degree,variant,omega_bounds,field_order,drop_second)
    nlinear=model.design(np.array([0,.5,.4]+[0.]*(model.npar-3))).shape[-1]
    if len(entries)*model.nobs<=nlinear+model.npar:raise ValueError('not enough independent data for this model')
    result=model.fit();result['error_note']=ERROR_NOTE
    result['tag']=tag;result['summary_file']=str(Path(summary).resolve());result['bootstrap_schedule']=schedule
    result['window_betas']={str(int(N)):sorted(float(e['beta']) for e in entries if e['N']==N) for N in np.unique(model.L)}
    if bootstrap:
        rng=np.random.default_rng(seed);sources=load_sources(summary,entries);draws=[]
        for ib in range(bootstrap):
            try:
                vals=resample_data(entries,sources,rng,schedule,ib)
                f=model.fit(vals[:,model.rows],initial=result['parameters'],multistart=False)
                draws.append({k:f[k] for k in ('Delta_epsilon','beta_c','omega_correction','flags','success')})
            except (ValueError,np.linalg.LinAlgError,FloatingPointError,ZeroDivisionError) as ex:
                # an expected numerical failure of ONE refit: the draw is invalid, the run continues (FITV2-007)
                draws.append(dict(Delta_epsilon=float('nan'),beta_c=float('nan'),omega_correction=float('nan'),success=False,
                                  flags=[f'refit exception: {type(ex).__name__}: {ex}']))
            draws[-1]['draw']=ib
            if verbose and (ib+1)%10==0:print(f'bootstrap {ib+1}/{bootstrap}',flush=True)
        valid=np.array([d['Delta_epsilon'] for d in draws if d['success'] and not d['flags']])
        result['bootstrap']=dict(requested=bootstrap,valid=len(valid),flagged_or_failed=bootstrap-len(valid),draws=draws,
            percentile_16_50_84=np.percentile(valid,[16,50,84]).tolist() if len(valid) else None,
            note='Conditional block bootstrap; flagged fits retained in draws. Assess optimizer minima and model changes separately.')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('summary',type=Path);p.add_argument('--s',type=float,required=True)
    p.add_argument('--lmin',type=int,default=1024);p.add_argument('--lmax',type=int,default=2**28)
    p.add_argument('--variant',choices=['leading','background','second','both','log'],default='leading')
    p.add_argument('--degree',type=int,default=3);p.add_argument('--correction-degree',type=int,default=2)
    p.add_argument('--field-order',type=int,default=1,help='K: tau = 100[v + a_1 v^2 + ... + a_{K-1} v^K]; K=1 linear field')
    p.add_argument('--drop-second',action='store_true',help='diagnostic: exclude the second-derivative rows')
    p.add_argument('--bootstrap-schedule',type=int,help='deterministic shared resampling seed (bootstrap_schedule.block_indices)')
    p.add_argument('--tag',default='',help='free label stored in the result (e.g. window name)')
    p.add_argument('--omega-min',type=float,default=.005);p.add_argument('--omega-max',type=float,default=3.)
    p.add_argument('--beta-center',type=float);p.add_argument('--beta-halfwidth',type=float)
    p.add_argument('--bootstrap',type=int,default=0);p.add_argument('--seed',type=int,default=981724)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    if not 1<=a.degree<=8 or not 0<=a.correction_degree<=3 or a.bootstrap<0:p.error('invalid degrees or bootstrap count')
    if not 1<=a.field_order<=3:p.error('field order must be 1, 2 or 3')
    if not 0<a.omega_min<a.omega_max:p.error('require 0 < omega-min < omega-max')
    try:
        entries=load_entries(a.summary,a.s,a.lmin,a.lmax,a.beta_center,a.beta_halfwidth)
        result=run_fit(a.summary,entries,a.degree,a.correction_degree,a.variant,(a.omega_min,a.omega_max),a.field_order,
                       a.drop_second,a.bootstrap,a.seed,a.bootstrap_schedule,a.tag,verbose=True)
    except ValueError as ex:p.error(str(ex))
    print(json.dumps({k:v for k,v in result.items() if k not in ('amplitudes','predictions','pulls','whitened_residuals','bootstrap','window_betas')},indent=2),flush=True)
    if 'bootstrap' in result:print(json.dumps({k:v for k,v in result['bootstrap'].items() if k!='draws'}),flush=True)
    out=a.out or a.summary.parent/f'fit_s{a.s}_Nmin{a.lmin}_{a.variant}_deg{a.degree}.json'
    out.write_text(json.dumps(result,indent=2)+'\n');print(out)
if __name__=='__main__':main()
