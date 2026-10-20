#!/usr/bin/env python3
"""Bracketed size-doubling crossings and finite-size effective CFT dimensions.

Fits LOCAL temperature polynomials to independent simulated temperatures, with
full covariance of (Y,Y',Y'',U,U',U''). No fit in N, no assumed omega and no
perturbative dimensions. Crossings must lie inside both simulated beta brackets.
Joint block resampling preserves correlations between neighboring size pairs.
A local polynomial and finite-N corrections still introduce systematic error.
"""
from __future__ import annotations
import argparse, csv, json
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.linalg import solve_triangular
from analyze import cft_observables
from bootstrap_schedule import block_indices
RANK_RCOND=1e-12   # relative singular-value cutoff shared by the rank check and the pseudo-inverse (REV-001)

class LocalCurve:
    def __init__(self,entries,reference,degree=3):
        self.entries=entries;self.ref=reference;self.degree=degree;self.n=entries[0]['N']
        self.beta=np.array([e['beta'] for e in entries]);self.lo=min(self.beta);self.hi=max(self.beta)
        if self.lo==self.hi:raise ValueError('at least two simulated temperatures are needed for a bracket')
        x=100*(self.beta-reference);A=np.zeros((len(entries),6,2*(degree+1)))
        for j in range(2):
            for k in range(degree+1):
                A[:,3*j,j*(degree+1)+k]=x**k
                if k:A[:,3*j+1,j*(degree+1)+k]=100*k*x**(k-1)
                if k>=2:A[:,3*j+2,j*(degree+1)+k]=10000*k*(k-1)*x**(k-2)
        self.scale=np.sqrt(np.diagonal(np.array([e['cov'] for e in entries]),axis1=1,axis2=2))
        corr=np.array([e['cov'] for e in entries])/self.scale[:,:,None]/self.scale[:,None,:]
        self.chol=np.linalg.cholesky(corr)
        AA=np.concatenate([solve_triangular(c,a/sc[:,None],lower=True) for c,a,sc in zip(self.chol,A,self.scale)])
        self.norm=np.maximum(np.linalg.norm(AA,axis=0),1e-100);self.A=AA/self.norm
        sv=np.linalg.svd(self.A,compute_uv=False)   # REV-001: the same cutoff for the rank check and the pseudo-inverse
        if sv.size==0 or np.sum(sv>RANK_RCOND*sv[0])<self.A.shape[1]:raise ValueError('local polynomial rank deficient')
        self.pinv=np.linalg.pinv(self.A,rcond=RANK_RCOND)
    def fit(self,data=None):
        data=np.array([e['data'] for e in self.entries]) if data is None else data
        v=np.concatenate([solve_triangular(c,a/sc,lower=True) for c,a,sc in zip(self.chol,data,self.scale)])
        c=self.pinv@v;res=self.A@c-v
        return (c/self.norm).reshape(2,-1),float(res@res),len(v)-len(c)

def crossing(a,b,ca,cb,which):
    lo=max(a.lo,b.lo);hi=min(a.hi,b.hi)
    if lo>=hi:raise ValueError('no common simulated-beta bracket')
    # local polynomials of the two sizes may have different degrees (v3 per-size ladder): subtract with zero padding (FITV3-001)
    diff=np.polynomial.polynomial.polysub(np.asarray(ca[which],float),np.asarray(cb[which],float))
    if len(diff)<2 or not np.any(diff[1:]):raise ValueError('difference polynomial is constant: no crossing')
    roots=np.polynomial.polynomial.polyroots(diff)
    roots=[float(z.real/100+a.ref) for z in roots if abs(z.imag)<1e-8]
    roots=[x for x in roots if lo<=x<=hi]
    if len(roots)!=1:raise ValueError(f'{len(roots)} crossings inside common bracket')
    beta=roots[0];x=100*(beta-a.ref);out=[beta]
    for j in (0,1):
        da=np.polynomial.polynomial.polyval(x,np.polynomial.polynomial.polyder(ca[j]))*100
        db=np.polynomial.polynomial.polyval(x,np.polynomial.polynomial.polyder(cb[j]))*100
        if da*db<=0:raise ValueError('nonpositive slope ratio')
        out.append(1-np.log(db/da)/np.log(2))
    return np.array(out)

def resample_entries(entries,sources,k,rng,schedule=None):
    """Draw k of the block bootstrap for a list of entries; sources[i] = [(replica id, blocks)] of entry i.
    Replica allocation preserved; blocks resampled within each chain, indices from the shared deterministic schedule
    (FIT_PLAN §3.6) when `schedule` is given, else from `rng`. Returns the (points x 6) observables."""
    vv=[]
    for e,src in zip(entries,sources):
        count=sum(len(b) for _,b in src);total=np.zeros((4,3))
        for rep_id,b in src:
            idx=block_indices(schedule,e['s'],e['N'],e['beta'],rep_id,k,len(b),campaign=e.get('campaign')) if schedule is not None else rng.integers(len(b),size=len(b))
            total+=b[idx].sum(axis=0)
        vv.append(cft_observables(total/count,e['N'],e['s'],e['beta']))
    return np.asarray(vv)

def degree_for(degree,n):
    """degree may be an int (all sizes) or a mapping {N: degree} (v3 per-size local degrees)."""
    if isinstance(degree,dict):
        if n in degree:return degree[n]
        if str(n) in degree:return degree[str(n)]
        return None
    return degree

def process(entries,summary_dir,degree,bootstrap,rng,schedule=None):
    byn=defaultdict(list)
    for e in entries:byn[e["N"]].append(e)
    ref=float(np.median([e['beta'] for e in entries]));curves={};polys={};fits={};warnings=[];sources={}
    for n,ee in sorted(byn.items()):
        try:
            dn=degree_for(degree,n)
            if dn is None:warnings.append(f'N={n}: no local degree assigned (size unusable)');continue
            curve=LocalCurve(ee,ref,dn);c,chi,dof=curve.fit()
        except (ValueError,np.linalg.LinAlgError) as ex:
            warnings.append(f'N={n}: {ex}');continue
        curves[n]=curve;polys[n]=c;fits[n]=dict(chi2=chi,dof=dof)
        if bootstrap:
            src=[]
            for e in ee:
                with np.load(summary_dir/e['blocks_file']) as z:
                    blocks=z['blocks'];rep=z['replicas'];src.append([(int(r),blocks[rep==r]) for r in np.unique(rep)])
            sources[n]=src
    pairs=[];central=[]
    for n in sorted(curves):
        if 2*n not in curves:continue
        for which in (0,1):
            try:v=crossing(curves[n],curves[2*n],polys[n],polys[2*n],which)
            except ValueError as ex:
                warnings.append(f'N={n}, crossing={"YU"[which]}: {ex}');continue
            pairs.append((n,which));central.append(v)
    samples=np.full((bootstrap,len(pairs),3),np.nan);draw_failures=[]
    for k in range(bootstrap):
        cp={}
        for n,curve in curves.items():
            # an expected numerical failure of one size on one draw leaves that size's polynomial missing for the draw:
            # every crossing that uses it stays NaN (invalid draw for those rows); other sizes and draws continue (FITV2-012)
            try:cp[n]=curve.fit(resample_entries(curve.entries,sources[n],k,rng,schedule))[0]
            except (ValueError,np.linalg.LinAlgError,FloatingPointError,ZeroDivisionError) as ex:draw_failures.append(f'draw {k} N={n}: {type(ex).__name__}: {ex}')
        for j,(n,which) in enumerate(pairs):
            if n not in cp or 2*n not in cp:continue
            try:samples[k,j]=crossing(curves[n],curves[2*n],cp[n],cp[2*n],which)
            except (ValueError,np.linalg.LinAlgError,FloatingPointError):pass
    rows=[]
    for j,((n,which),v) in enumerate(zip(pairs,central)):
        good=np.all(np.isfinite(samples[:,j]),axis=1);draws=samples[good,j]
        rows.append(dict(N=n,N2=2*n,crossing_observable='YU'[which],beta_crossing=float(v[0]),
            Delta_epsilon_eff_from_Y=float(v[1]),Delta_epsilon_eff_from_U=float(v[2]),
            bootstrap_standard_error=draws.std(axis=0,ddof=1).tolist() if len(draws)>1 else None,
            valid_bootstrap_draws=int(good.sum()),failed_bootstrap_draws=bootstrap-int(good.sum())))
    complete=np.all(np.isfinite(samples),axis=(1,2)) if len(pairs) else np.zeros(bootstrap,bool)
    joint=samples[complete].reshape(int(complete.sum()),3*len(pairs)) if len(pairs) else np.empty((0,0))
    return dict(Delta_sigma=(1-entries[0]['s'])/2,local_polynomial_degree=degree if not isinstance(degree,dict) else {str(k):v for k,v in degree.items()},local_fit_diagnostics=fits,
        bootstrap_requested=bootstrap,bootstrap_schedule=schedule,
        crossings=rows,warnings=warnings,bootstrap_draw_failures=draw_failures[:50],bootstrap_draw_failure_count=len(draw_failures),
        joint_valid_bootstrap=int(complete.sum()),
        joint_covariance=np.cov(joint,rowvar=False).tolist() if len(joint)>1 else None,
        joint_covariance_order='For each crossing row: beta_crossing, Delta_eff_Y, Delta_eff_U',
        note='Finite-size effective dimensions, NOT infinite-volume CFT estimates. Vary local degree and beta range.'),samples

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('summary',type=Path);p.add_argument('--s',type=float,nargs='+')
    p.add_argument('--degree',type=int,choices=[2,3,4,5,6],default=3)
    p.add_argument('--bootstrap',type=int,default=200);p.add_argument('--seed',type=int,default=1348772)
    p.add_argument('--bootstrap-schedule',type=int,help='deterministic shared resampling seed (bootstrap_schedule.block_indices)')
    p.add_argument('--out',type=Path);p.add_argument('--centers-out',type=Path,
        help='provisional beta centers from largest bracketed U crossing, not fitted critical temperatures')
    a=p.parse_args()
    if a.bootstrap<0:p.error('bootstrap must be nonnegative')
    entries=json.loads(a.summary.read_text())['entries'];groups=defaultdict(list)
    for e in entries:
        if a.s is None or any(abs(e['s']-s)<1e-12 for s in a.s):
            if abs(e['beta']-e.get('beta_simulated',e['beta']))>1e-14:p.error('use independently simulated temperatures, not reweighted points')
            groups[e['s']].append(e)
    rng=np.random.default_rng(a.seed);result={};centers=[];allsamples={}
    for s,ee in sorted(groups.items()):
        r,draws=process(ee,a.summary.parent,a.degree,a.bootstrap,rng,a.bootstrap_schedule);result[str(s)]=r;allsamples[str(s)]=draws
        valid=[v for v in r['crossings'] if v['crossing_observable']=='U']
        if valid:
            row=max(valid,key=lambda v:v['N']);centers.append(dict(s=s,N='',beta=row['beta_crossing']))
        print(f's={s}: {len(r["crossings"])} bracketed crossing estimates; warnings={r["warnings"]}',flush=True)
    out=a.out or a.summary.parent/f'quotients_deg{a.degree}.json'
    out.write_text(json.dumps(result,indent=2)+'\n');print(out)
    # bootstrap samples per s: shape (bootstrap, crossing rows, 3) with NaN for failed roots; row order = 'crossings'
    np.savez_compressed(out.with_suffix('.samples.npz'),**allsamples)
    if a.centers_out:
        with a.centers_out.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['s','N','beta']);w.writeheader();w.writerows(centers)
        print(f'{a.centers_out}: provisional finite-size crossing centers; inspect warnings and local chi2 before use')
if __name__=='__main__':main()
