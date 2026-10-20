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

class LocalCurve:
    def __init__(self,entries,reference,degree=3):
        self.entries=entries;self.ref=reference;self.degree=degree;self.n=entries[0]['L'];self.dim=entries[0]['d']
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
        if np.linalg.matrix_rank(self.A)<self.A.shape[1]:raise ValueError('local polynomial rank deficient')
        self.pinv=np.linalg.pinv(self.A,rcond=1e-12)
    def fit(self,data=None):
        data=np.array([e['data'] for e in self.entries]) if data is None else data
        v=np.concatenate([solve_triangular(c,a/sc,lower=True) for c,a,sc in zip(self.chol,data,self.scale)])
        c=self.pinv@v;res=self.A@c-v
        return (c/self.norm).reshape(2,-1),float(res@res),len(v)-len(c)

def crossing(a,b,ca,cb,which):
    lo=max(a.lo,b.lo);hi=min(a.hi,b.hi)
    if lo>=hi:raise ValueError('no common simulated-beta bracket')
    roots=np.polynomial.polynomial.polyroots(ca[which]-cb[which])
    roots=[float(z.real/100+a.ref) for z in roots if abs(z.imag)<1e-8]
    roots=[x for x in roots if lo<=x<=hi]
    if len(roots)!=1:raise ValueError(f'{len(roots)} crossings inside common bracket')
    beta=roots[0];x=100*(beta-a.ref);out=[beta]
    for j in (0,1):
        da=np.polynomial.polynomial.polyval(x,np.polynomial.polynomial.polyder(ca[j]))*100
        db=np.polynomial.polynomial.polyval(x,np.polynomial.polynomial.polyder(cb[j]))*100
        if da*db<=0:raise ValueError('nonpositive slope ratio')
        out.append(a.dim-np.log(db/da)/np.log(2))
    return np.array(out)

def process(entries,summary_dir,degree,bootstrap,rng):
    byn=defaultdict(list)
    for e in entries:byn[e["L"]].append(e)
    ref=float(np.median([e['beta'] for e in entries]));curves={};polys={};fits={};warnings=[];sources={}
    for n,ee in sorted(byn.items()):
        try:
            curve=LocalCurve(ee,ref,degree);c,chi,dof=curve.fit()
        except (ValueError,np.linalg.LinAlgError) as ex:
            warnings.append(f'N={n}: {ex}');continue
        curves[n]=curve;polys[n]=c;fits[n]=dict(chi2=chi,dof=dof)
        if bootstrap:
            src=[]
            for e in ee:
                with np.load(summary_dir/e['blocks_file']) as z:
                    blocks=z['blocks'];rep=z['replicas'];src.append([blocks[rep==r] for r in np.unique(rep)])
            sources[n]=src
    pairs=[];central=[]
    for n in sorted(curves):
        if 2*n not in curves:continue
        for which in (0,1):
            try:v=crossing(curves[n],curves[2*n],polys[n],polys[2*n],which)
            except ValueError as ex:
                warnings.append(f'N={n}, crossing={"YU"[which]}: {ex}');continue
            pairs.append((n,which));central.append(v)
    samples=np.full((bootstrap,len(pairs),3),np.nan)
    for k in range(bootstrap):
        cp={}
        for n,curve in curves.items():
            vv=[]
            for e,src in zip(curve.entries,sources[n]):
                count=sum(map(len,src));total=np.zeros((4,3))
                for b in src:total+=b[rng.integers(len(b),size=len(b))].sum(axis=0)
                vv.append(cft_observables(total/count,e['N'],e['s'],e['beta'],e['d']))
            cp[n]=curve.fit(vv)[0]
        for j,(n,which) in enumerate(pairs):
            try:samples[k,j]=crossing(curves[n],curves[2*n],cp[n],cp[2*n],which)
            except ValueError:pass
    rows=[]
    for j,((n,which),v) in enumerate(zip(pairs,central)):
        good=np.all(np.isfinite(samples[:,j]),axis=1);draws=samples[good,j]
        rows.append(dict(L=n,L2=2*n,crossing_observable='YU'[which],beta_crossing=float(v[0]),
            Delta_epsilon_eff_from_Y=float(v[1]),Delta_epsilon_eff_from_U=float(v[2]),
            bootstrap_standard_error=draws.std(axis=0,ddof=1).tolist() if len(draws)>1 else None,
            valid_bootstrap_draws=int(good.sum()),failed_bootstrap_draws=bootstrap-int(good.sum())))
    complete=np.all(np.isfinite(samples),axis=(1,2)) if len(pairs) else np.zeros(bootstrap,bool)
    joint=samples[complete].reshape(int(complete.sum()),3*len(pairs)) if len(pairs) else np.empty((0,0))
    return dict(d=entries[0]['d'],s=entries[0]['s'],Delta_sigma=(entries[0]['d']-entries[0]['s'])/2,local_polynomial_degree=degree,local_fit_diagnostics=fits,
        crossings=rows,warnings=warnings,joint_valid_bootstrap=int(complete.sum()),
        joint_covariance=np.cov(joint,rowvar=False).tolist() if len(joint)>1 else None,
        joint_covariance_order='For each crossing row: beta_crossing, Delta_eff_Y, Delta_eff_U',
        note='Finite-size effective dimensions, NOT infinite-volume CFT estimates. Vary local degree and beta range.'),samples

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('summary',type=Path);p.add_argument('--dim',type=int,required=True);p.add_argument('--s',type=float,nargs='+')
    p.add_argument('--degree',type=int,choices=[2,3,4],default=3)
    p.add_argument('--bootstrap',type=int,default=200);p.add_argument('--seed',type=int,default=1348772)
    p.add_argument('--out',type=Path);p.add_argument('--centers-out',type=Path,
        help='provisional beta centers from largest bracketed U crossing, not fitted critical temperatures')
    a=p.parse_args()
    if a.bootstrap<0:p.error('bootstrap must be nonnegative')
    entries=json.loads(a.summary.read_text())['entries'];groups=defaultdict(list)
    for e in entries:
        if e['d']==a.dim and (a.s is None or any(abs(e['s']-s)<1e-12 for s in a.s)):
            if abs(e['beta']-e.get('beta_simulated',e['beta']))>1e-14:p.error('use independently simulated temperatures, not reweighted points')
            groups[e['s']].append(e)
    rng=np.random.default_rng(a.seed);result={};centers=[]
    for s,ee in sorted(groups.items()):
        r,draws=process(ee,a.summary.parent,a.degree,a.bootstrap,rng);result[str(s)]=r
        valid=[v for v in r['crossings'] if v['crossing_observable']=='U']
        if valid:
            row=max(valid,key=lambda v:v['L']);centers.append(dict(d=a.dim,s=s,L='',beta=row['beta_crossing']))
        print(f's={s}: {len(r["crossings"])} bracketed crossing estimates; warnings={r["warnings"]}',flush=True)
    out=a.out or a.summary.parent/f'quotients_d{a.dim}_deg{a.degree}.json'
    out.write_text(json.dumps(result,indent=2)+'\n');print(out)
    if a.centers_out:
        with a.centers_out.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['d','s','L','beta']);w.writeheader();w.writerows(centers)
        print(f'{a.centers_out}: provisional finite-size crossing centers; inspect warnings and local chi2 before use')
if __name__=='__main__':main()
