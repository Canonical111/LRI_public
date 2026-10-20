#!/usr/bin/env python3
"""N0 dense-window diagnostic (FIT_MODEL_V3.md §5.0). Default rule (revision 12, test (j)): per size, one polynomial per observable
family fitted jointly to values, first and second derivatives with the full covariance; d* = lowest degree 2..7 with chi2 p >= 1 %;
PASS(d*) / FAIL (values smooth, joint not) / INCONCLUSIVE; window rule max d* >= 5 -> x_max 0.35; validation on models (i)-(iv).
Superseded value-only rules (--rule rev11 | preregistered: value-fit degree selection, T = r^T C^+ r against a mixture-calibrated
threshold) stay reproducible. Every run writes an immutable manifest (plan/code hashes, seed, inputs) and never overwrites a record.

Usage: n0_diagnostic.py SUMMARY.json [SUMMARY2.json ...] --out DIR [--reps 10000] [--validate]
Each summary is an analyze.py output of one N0 campaign (one size, 9 temperatures). Observables Q in {Y (cols 0,1,2), U (3,4,5)}.
Outcomes: PASS / FAIL / INCONCLUSIVE with the complete record written to DIR/n0_result.json and DIR/N0_RESULT.md.
"""
from __future__ import annotations
import argparse, hashlib, json, platform, re, sys, time
from collections import Counter
from pathlib import Path
import numpy as np
import scipy
from scipy.linalg import solve_triangular
from scipy.stats import chi2 as chi2_dist

DEGREES=range(2,7); INTERIOR=slice(2,7)   # interior points j=-2..2 of 9 (indices 2..6)
SMOOTH_P_MIN=0.01   # revision-11 value-only rule: lowest admissible degree whose value-fit chi2 p-value >= 1 %
PREREG_CHI2_DOF_MAX=1.5   # pre-registered value-only rule (revisions <= 10): lowest degree with chi2/dof <= 1.5
RULE='joint'   # 'joint' (revision 12, §5.0 test (j)) | 'rev11' | 'preregistered' — the superseded rules stay reproducible
# revision 12 joint test (j)
RANK_RCOND=1e-12   # single singular-value cutoff for rank checks and solves (REV-001)
JOINT_DEGREES=range(2,10); JOINT_PASS_MAX_DEGREE=7; JOINT_P_MIN=0.01; JOINT_FAIL_PER_SIZE=0.01; JOINT_POWER_MIN=0.95
JOINT_MC_ALPHA=0.01; JOINT_NOISELESS_CHI2_MAX=1e-8; XSCALE=100.; SYNTH_EXCURSION=0.2
def combined_fail_bound(n_sizes):return 1-(1-JOINT_FAIL_PER_SIZE)**n_sizes   # V3-028: FAIL if any size FAILs
OBSNAMES=['Y',"Y'","Y''",'U',"U'","U''"]
NULL_RATE_BAND=(0.007,0.013)   # §5.0: P(FAIL | conclusive) = 1 % ± 0.3 % for the validation models (i), (ii)
DATA_NULL_BAND=(0.005,0.02)    # gross-error band for the data's own null on an independent replicate set (post-review clarification
                               # 2026-09-18: the data null is a mixture over the degrees re-selected per replicate, see calibration_branches)
POWER_MIN=0.95                 # §5.0 (iii): P(FAIL | conclusive) >= 95 % for the +5 sigma_R biased model
NOISELESS_T_MAX=1e-8           # noiseless consistent fixture: T = 0 up to round-off
NUMFAIL_MAX=0.01               # numerical failures < 1 % of draws
N0_SIZES=(65536,262144); N0_S=0.65; N0_REPLICAS=4; N0_MEASUREMENTS=500000; N0_REPS=10000   # §5.0 inputs and budget (R2-001)
OBS={'Y':(0,1,2),'U':(3,4,5)}

def load(summary):
    S=json.loads(Path(summary).read_text());ent=sorted(S['entries'],key=lambda e:e['beta'])
    if len(ent)!=9:raise ValueError(f'{summary}: {len(ent)} temperatures, expected 9')
    if len({e['N'] for e in ent})!=1:raise ValueError('one size per summary expected')
    beta=np.array([e['beta'] for e in ent]);d=np.diff(beta)
    if np.max(np.abs(d-d.mean()))>1e-6*abs(d.mean()):raise ValueError(f'{summary}: temperature grid not equally spaced')
    if any(abs(e['beta']-e.get('beta_simulated',e['beta']))>1e-14 for e in ent):raise ValueError(f'{summary}: reweighted entries')
    return dict(N=ent[0]['N'],s=ent[0]['s'],beta=beta,data=np.array([e['data'] for e in ent]),cov=np.array([e['cov'] for e in ent]),center=float(beta[4]),delta=float(d.mean()),
                replicas=[len(e.get('replica_diagnostics',[])) for e in ent],used_sweeps=[e.get('used_sweeps') for e in ent],nblocks=[e.get('nblocks') for e in ent])

def input_problems(sets,reps):
    """§5.0 production inputs (R2-001): both sizes once each at s = 0.65, 9 equally spaced temperatures (checked in load), 4
    complete chains per temperature, and the full calibration budget. A run violating any of these is diagnostic only."""
    bad=[];sizes=sorted(d['N'] for d in sets)
    if sizes!=sorted(N0_SIZES):bad.append(f'sizes {sizes} != required {sorted(N0_SIZES)} (both N0 sizes, once each)')
    if any(abs(d['s']-N0_S)>1e-12 for d in sets):bad.append(f"s values {[d['s'] for d in sets]} != {N0_S}")
    if any(r!=N0_REPLICAS for d in sets for r in d.get('replicas',[N0_REPLICAS])):bad.append(f'chains per temperature != {N0_REPLICAS} (campaign incomplete?)')
    if any(u is None or u<0.99*N0_REPLICAS*N0_MEASUREMENTS for d in sets for u in d.get('used_sweeps',[N0_REPLICAS*N0_MEASUREMENTS])):bad.append(f'used sweeps below {N0_REPLICAS} x {N0_MEASUREMENTS} per temperature')
    if reps<N0_REPS:bad.append(f'--reps {reps} < {N0_REPS}')
    return bad

def design(beta,d):
    """Vandermonde in the scaled offset t = (beta - mean)/scale, |t| <= 1 (conditioning); derivatives use the chain rule."""
    x=beta-beta.mean();scale=float(np.max(np.abs(x))) or 1.;t=x/scale;return np.vander(t,d+1,increasing=True),t,scale

def value_fit(beta,vals,var,d):
    """weighted LS on the values; returns coefficients, the linear map M (coef = M v) and chi2/dof."""
    var=np.asarray(var,float)
    if not np.all(np.isfinite(var)) or np.any(var<=0):raise ValueError('nonpositive or non-finite variance in the value fit')   # same outcome on every numpy (R13-005)
    A,t,scale=design(beta,d);W=1/np.sqrt(var);Aw=A*W[:,None]
    M=np.linalg.pinv(Aw,rcond=1e-13)*W[None,:]    # coef = M @ vals (coefficients in t)
    coef=M@vals;res=(A@coef-vals)/np.sqrt(var);dof=len(vals)-d-1
    return coef,M,float(res@res),dof,A,(t,scale)

def select_degree(beta,vals,var):
    """§5.0(b) (revision 11): lowest admissible degree (dof >= 2) whose value-fit chi2 is not rejected at the 1 % level,
    P(chi2_dof >= chi2_obs) >= SMOOTH_P_MIN; returns (degree, chi2/dof, p) or (None, None, None) (INCONCLUSIVE)."""
    for d in DEGREES:
        coef,M,chi,dof,A,_=value_fit(beta,vals,var,d)
        if dof>=2:
            p=float(chi2_dist.sf(chi,dof))
            if (RULE=='preregistered' and chi/dof<=PREREG_CHI2_DOF_MAX) or (RULE!='preregistered' and p>=SMOOTH_P_MIN):return d,chi/dof,p
    return None,None,None

def residual_map(beta,d,M):
    """rows: interior j; r_j = Q'(j) - P'(beta_j) with P' = D1 @ coef = (D1 @ M) @ values.
    Returns the matrix acting on the stacked per-temperature vector [Q(0..8), Q'(0..8)] (18 entries)."""
    _,t,scale=design(beta,d);n=len(beta)
    D1=np.vstack([np.array([k*t[j]**(k-1) if k>0 else 0. for k in range(d+1)]) for j in range(n)])/scale   # dP/dbeta = (1/scale) dP/dt
    Bvals=-(D1@M)                                  # contribution of values to residual (minus polynomial derivative)
    R=np.zeros((5,2*n))
    for row,j in enumerate(range(2,7)):
        R[row,:n]=Bvals[j];R[row,n+j]=1.0
    return R

def procedure(sets,rng=None,perturb=None):
    """Run (b) then (a) on a list of per-size datasets. `perturb(ds)` optionally replaces ds['data'] (calibration draws).
    Returns dict(outcome=None|'INCONCLUSIVE', T, rank, rows, p_naive)."""
    rows=[];inconclusive=[]
    for ds in sets:
        beta=ds['beta'];data=ds['data'] if perturb is None else perturb(ds)
        for Q,(iv,i1,i2) in OBS.items():
            d,c2,pv=select_degree(beta,data[:,iv],ds['cov'][:,iv,iv])
            if d is None:inconclusive.append((int(ds['N']),Q));continue
            rows.append(dict(N=int(ds['N']),Q=Q,degree=d,chi2_dof=c2,p_value=pv))
    if inconclusive:return dict(outcome='INCONCLUSIVE',inconclusive=inconclusive,rows=rows)
    r,C=joint_residual(sets,rows,perturb)
    w,V=np.linalg.eigh(C);keep=w>1e-10*w.max();Cp=(V[:,keep]/w[keep])@V[:,keep].T;T=float(r@Cp@r);rank=int(keep.sum())
    return dict(outcome=None,T=T,rank=rank,rows=rows,p_naive=float(chi2_dist.sf(T,rank)))

def joint_residual(sets,rows,perturb=None):
    """Exact residual vector and covariance including Y-U cross terms within a temperature (same chains)."""
    rs=[];Cs=[]
    for ds in sets:
        beta=ds['beta'];data=ds['data'] if perturb is None else perturb(ds)
        degs={rw['Q']:rw['degree'] for rw in rows if rw['N']==ds['N']}
        # stacked vector per size: [Y(9), Y'(9), U(9), U'(9)]
        v=np.concatenate([data[:,0],data[:,1],data[:,3],data[:,4]]);Sig=np.zeros((36,36))
        pos={0:0,1:9,3:18,4:27}
        for j in range(9):
            for a,pa in pos.items():
                for b,pb in pos.items():Sig[pa+j,pb+j]=ds['cov'][j,a,b]
        Rall=np.zeros((10,36))
        for qi,(Q,(iv,i1,_)) in enumerate(OBS.items()):
            d=degs[Q];vals=data[:,iv];var=ds['cov'][:,iv,iv];coef,M,chi,dof,A,_=value_fit(beta,vals,var,d);Rm=residual_map(beta,d,M)
            Rall[5*qi:5*qi+5,pos[iv]:pos[iv]+9]=Rm[:,:9];Rall[5*qi:5*qi+5,pos[i1]:pos[i1]+9]=Rm[:,9:]
        rs.append(Rall@v);Cs.append(Rall@Sig@Rall.T)
    r=np.concatenate(rs);C=np.zeros((len(r),len(r)));o=0
    for Cb in Cs:k=Cb.shape[0];C[o:o+k,o:o+k]=Cb;o+=k
    return r,C

def detectable_bias(sets,rows):
    """sigma_R / sigma(Q') per interior residual: the derivative bias (in units of its own standard error) that the test
    resolves at 1 sigma. The value-polynomial derivative dominates sigma_R, so this ratio is typically 10-100 at N0 spacing."""
    r,C=joint_residual(sets,rows);sig_r=np.sqrt(np.diag(C));out=[];k=0
    for ds in sets:
        for Q,(iv,i1,i2) in OBS.items():
            sq=np.sqrt(ds['cov'][2:7,i1,i1]);out.append(dict(N=int(ds['N']),Q=Q,ratio=(sig_r[k:k+5]/sq).tolist()));k+=5
    return out

def null_mean(sets,rows):
    """polynomial-consistent null: values and derivatives from the selected value polynomial (§5.0(a), V3-023)."""
    out=[]
    for ds in sets:
        beta=ds['beta'];d0=np.array(ds['data'],float).copy()
        for Q,(iv,i1,i2) in OBS.items():
            d=next(rw['degree'] for rw in rows if rw['N']==ds['N'] and rw['Q']==Q)
            coef,M,chi,dof,A,(t,scale)=value_fit(beta,ds['data'][:,iv],ds['cov'][:,iv,iv],d)
            d0[:,iv]=A@coef
            D1=np.vstack([np.array([k*t[j]**(k-1) if k>0 else 0. for k in range(d+1)]) for j in range(9)])/scale;d0[:,i1]=D1@coef
            D2=np.vstack([np.array([k*(k-1)*t[j]**(k-2) if k>1 else 0. for k in range(d+1)]) for j in range(9)])/scale**2;d0[:,i2]=D2@coef
        out.append(dict(ds,data=d0))
    return out

def synthetic_model_legacy(sets,deg):
    """ORIGINAL generator of the superseded rules (revisions <= 12, V3-033): (i) degree-5 cancellation polynomial and (ii) degree-6
    polynomial with amplitude 0.02 mean|Q| / delta^deg. Kept unchanged so that the historical validation records reproduce exactly."""
    models=[]
    for ds in sets:
        beta=ds['beta'];x=beta-beta.mean();delta=x[1]-x[0];data=np.array(ds['data'],float).copy()
        for Q,(iv,i1,i2) in OBS.items():
            amp=0.02*abs(ds['data'][:,iv]).mean()/max(delta**deg,1e-300)
            if deg==5:f=amp*x*(x**2-delta**2)*(x**2-4*delta**2);f1=amp*(5*x**4-15*delta**2*x**2+4*delta**4);f2=amp*(20*x**3-30*delta**2*x)
            else:f=amp*(x**6-3*delta**2*x**4);f1=amp*(6*x**5-12*delta**2*x**3);f2=amp*(30*x**4-36*delta**2*x**2)
            data[:,iv]=ds['data'][:,iv].mean()+f;data[:,i1]=f1;data[:,i2]=f2
        models.append(dict(ds,data=data))
    return models

def synthetic_model(sets,deg):
    """§5.0 validation models with Sigma from the summaries: (i) deg 5 = the cancellation polynomial a t(t^2-d^2)(t^2-4d^2),
    (ii) deg 6; derivatives consistent with the values."""
    P=np.polynomial.polynomial;models=[]
    for ds in sets:
        beta=ds['beta'];x=beta-beta.mean();delta=x[1]-x[0];t=x/delta;data=np.array(ds['data'],float).copy()
        if deg==5:c=P.polyfromroots([0,1,-1,2,-2])          # cancellation polynomial t(t^2-1)(t^2-4)
        elif deg==6:c=np.array([0,0,0,0,-3.,0,1.])           # t^6 - 3 t^4
        elif deg==7:c=P.polyfromroots([0,1,-1,2,-2,3,-3])    # t(t^2-1)(t^2-4)(t^2-9)
        else:raise ValueError('synthetic degree must be 5, 6 or 7')
        f=P.polyval(t,c);f1=P.polyval(t,P.polyder(c))/delta;f2=P.polyval(t,P.polyder(c,2))/delta**2
        for Q,(iv,i1,i2) in OBS.items():
            amp=SYNTH_EXCURSION*abs(ds['data'][:,iv]).mean()/max(np.max(np.abs(f)),1e-300)   # well resolved: 20 % of mean |Q| excursion
            data[:,iv]=ds['data'][:,iv].mean()+amp*f;data[:,i1]=amp*f1;data[:,i2]=amp*f2
        models.append(dict(ds,data=data))
    return models

def validate_model(models,reps,seed,bias_units=0.):
    """§5.0 procedure validation on one synthetic model with INDEPENDENT replicate sets (FITV3-006): set A fixes the 99 %
    threshold; set B (independent draws) measures P(FAIL | conclusive) and P(INCONCLUSIVE); set C (independent, derivatives
    biased by bias_units x median(sigma_R/sigma(Q'))) measures the power. Nothing is evaluated on the set that set the threshold."""
    res0=procedure(models);rec=dict(noiseless=dict(outcome=res0['outcome'],T=res0.get('T')))
    if res0['outcome'] is not None:rec['reason']='noiseless model INCONCLUSIVE';return rec
    TsA,exA,nfA,dA=calibrate(models,reps,np.random.default_rng(seed))
    thr=float(np.quantile(TsA,0.99)) if len(TsA)>=reps else None
    TsB,exB,nfB,dB=calibrate(models,reps,np.random.default_rng(seed+1))
    pA=exA/max(dA,1);pB=exB/max(dB,1);se=float(np.sqrt(pA*(1-pA)/max(dA,1)+pB*(1-pB)/max(dB,1)))
    rec.update(threshold_set=dict(conclusive=len(TsA),smoothness_excluded=exA,numerical_failures=nfA,draws=dA,T_threshold_99=thr,inconclusive_rate=pA),
               evaluation_set=dict(conclusive=len(TsB),smoothness_excluded=exB,numerical_failures=nfB,draws=dB,inconclusive_rate=pB,
                   fail_rate_conditional=(float(np.mean(TsB>=thr)) if thr is not None and len(TsB) else None),
                   fail_rate_unconditional=(float(np.sum(TsB>=thr))/max(dB,1) if thr is not None else None)),
               inconclusive_consistent=bool(abs(pA-pB)<=2*se+1e-12))
    if bias_units:
        ratio=float(np.median([v for d_ in detectable_bias(models,res0['rows']) for v in d_['ratio']]))
        TsC,exC,nfC,dC=calibrate(models,reps,np.random.default_rng(seed+2),bias_sigma=bias_units*ratio)
        rec['biased_set']=dict(conclusive=len(TsC),smoothness_excluded=exC,numerical_failures=nfC,draws=dC,bias_in_derivative_sigmas=bias_units*ratio,bias_in_sigma_R=bias_units,
            fail_rate_conditional=(float(np.mean(TsC>=thr)) if thr is not None and len(TsC) else None),
            fail_rate_unconditional=(float(np.sum(TsC>=thr))/max(dC,1) if thr is not None else None))
    return rec

def validation_failures(val,reps):
    """§5.0 acceptance criteria of the procedure validation; returns the list of violated criteria (empty = validated)."""
    bad=[]
    for name,rec in val.items():
        if rec.get('reason'):bad.append(f'{name}: {rec["reason"]}');continue
        if rec['noiseless']['T'] is None or rec['noiseless']['T']>NOISELESS_T_MAX:bad.append(f'{name}: noiseless T {rec["noiseless"]["T"]} > {NOISELESS_T_MAX}')
        for part in ('threshold_set','evaluation_set','biased_set'):
            st=rec.get(part)
            if st is None:continue
            if st['conclusive']<reps:bad.append(f'{name}/{part}: only {st["conclusive"]} conclusive replicates (< {reps})')
            if st['numerical_failures']>NUMFAIL_MAX*max(st['draws'],1):bad.append(f'{name}/{part}: numerical failures {st["numerical_failures"]}/{st["draws"]}')
        fr=rec['evaluation_set']['fail_rate_conditional']
        if fr is None or not (NULL_RATE_BAND[0]<=fr<=NULL_RATE_BAND[1]):bad.append(f'{name}: P(FAIL | conclusive) = {fr} outside {NULL_RATE_BAND}')
        if not rec['inconclusive_consistent']:bad.append(f'{name}: P(INCONCLUSIVE) of the evaluation set inconsistent with the smoothness-exclusion rate')
        if 'biased_set' in rec:
            pw=rec['biased_set']['fail_rate_conditional']
            if pw is None or pw<POWER_MIN:bad.append(f'{name}: power {pw} < {POWER_MIN}')
    return bad

def branch_summary(Ts,degs):
    """Mixture structure of the null: per combination of re-selected degrees (Y, U, per size) the count, median T and
    99 % quantile of T. The threshold of the complete procedure is a quantile of this mixture (§5.0)."""
    from collections import Counter
    Ts=np.asarray(Ts);out=[]
    for d,c in Counter(degs).most_common(12):
        m=np.array([g==d for g in degs]);t=Ts[m]
        out.append(dict(degrees=list(d),count=int(c),fraction=float(c/len(degs)),median_T=float(np.median(t)),q99_T=(float(np.quantile(t,0.99)) if c>=100 else None)))
    return out

def calibrate(sets_null,reps,rng,max_draws=None,bias_sigma=0.,record=None):
    """Replicates v* ~ N(v̂, Σ) (per temperature 6x6 blocks); each repeats the complete procedure. Returns T values of
    conclusive replicates, counts of smoothness-excluded and numerical failures. `record`, if a list, receives the tuple of
    selected degrees of every conclusive replicate (branch bookkeeping)."""
    max_draws=max_draws or 5*reps;Ts=[];excl=0;numfail=0;draws=0
    chols=[[np.linalg.cholesky(ds['cov'][j]+1e-30*np.eye(6)) for j in range(9)] for ds in sets_null]
    while len(Ts)<reps and draws<max_draws:
        draws+=1
        def perturb_factory():
            store={}
            def perturb(ds):
                key=ds['N']
                if key not in store:
                    i=[d['N'] for d in sets_null].index(key);z=rng.standard_normal((9,6));dat=ds['data']+np.stack([chols[i][j]@z[j] for j in range(9)])
                    if bias_sigma:
                        for _,(iv,i1,_) in OBS.items():dat[:,i1]+=bias_sigma*np.sqrt(ds['cov'][:,i1,i1])
                    store[key]=dat
                return store[key]
            return perturb
        try:
            res=procedure(sets_null,perturb=perturb_factory())
        except (np.linalg.LinAlgError,ValueError):numfail+=1;continue
        if res['outcome']=='INCONCLUSIVE':excl+=1;continue
        if not np.isfinite(res['T']):numfail+=1;continue
        Ts.append(res['T'])
        if record is not None:record.append(tuple(rw['degree'] for rw in res['rows']))
    return np.array(Ts),excl,numfail,draws


# ---------------------------------------------------------------- revision 12: joint polynomial test (j) (FIT_MODEL_V3.md §5.0)
def joint_polyfit(ds,d):
    """One polynomial per observable family (Y, U) of degree d fitted to the values, first and second beta-derivatives of the 9
    temperatures with the full 6x6 covariance per temperature (the quotients.LocalCurve construction: x = 100 (beta - ref),
    derivative columns 100 k x^(k-1) and 10^4 k(k-1) x^(k-2)). Returns chi2, dof, p, per-point pulls and per-observable mean |pull|."""
    beta=ds['beta'];ref=float(np.median(beta));x=XSCALE*(beta-ref);n=len(beta);A=np.zeros((n,6,2*(d+1)))
    for j in range(2):
        for k in range(d+1):
            A[:,3*j,j*(d+1)+k]=x**k
            if k:A[:,3*j+1,j*(d+1)+k]=XSCALE*k*x**(k-1)
            if k>=2:A[:,3*j+2,j*(d+1)+k]=XSCALE**2*k*(k-1)*x**(k-2)
    cov=np.asarray(ds['cov'],float);data=np.asarray(ds['data'],float);scale=np.sqrt(np.diagonal(cov,axis1=1,axis2=2))
    if np.any(scale<=0):raise ValueError('zero sampling variance')
    corr=cov/scale[:,:,None]/scale[:,None,:];chol=np.linalg.cholesky(corr)
    Aw=np.concatenate([solve_triangular(c,a/sc[:,None],lower=True) for c,a,sc in zip(chol,A,scale)])
    vw=np.concatenate([solve_triangular(c,v/sc,lower=True) for c,v,sc in zip(chol,data,scale)])
    norm=np.maximum(np.linalg.norm(Aw,axis=0),1e-100);An=Aw/norm
    coef,_,rank,sv=np.linalg.lstsq(An,vw,rcond=RANK_RCOND)   # REV-001: the solver's own rank at the declared cutoff decides
    if rank<An.shape[1]:raise ValueError(f'joint polynomial design rank deficient ({rank} < {An.shape[1]} at rcond {RANK_RCOND})')
    res=An@coef-vw;chi=float(res@res);dof=int(vw.size-An.shape[1])
    pred=np.einsum('nok,k->no',A,coef/norm);pulls=(pred-data)/scale
    return dict(degree=d,chi2=chi,dof=dof,p=float(chi2_dist.sf(chi,dof)),pulls=pulls,mean_abs_pull={q:float(np.mean(np.abs(pulls[:,i]))) for i,q in enumerate(OBSNAMES)})

def values_smooth(ds):
    """Values-only screen used to separate FAIL from INCONCLUSIVE: per family the lowest degree whose value fit has dof >= 1 and p >= JOINT_P_MIN.
    Documented deviation (V3-R16-003): FIT_MODEL_V3.md §5.0 says "not fitted by any degree <= 9", but with nine distinct temperatures a
    degree-8 polynomial interpolates any values and degree 9 is rank deficient, so the realisable reading is "no degree with dof >= 1"
    (2..7 for nine temperatures); the outcome text states this. The approved N0 result never reached this branch (d* = 5 at both sizes)."""
    out={}
    for Q,(iv,_,_) in OBS.items():
        sel=None
        for d in JOINT_DEGREES:
            if d>=len(ds['beta'])-1:break   # a 9-point value fit needs dof >= 1
            try:coef,M,chi,dof,A,_=value_fit(ds['beta'],ds['data'][:,iv],ds['cov'][:,iv,iv],d)
            except (ValueError,np.linalg.LinAlgError,FloatingPointError):continue   # a failed value fit does not fit (R13-005); the joint fits carry the NUMERICAL FAILURE bookkeeping
            if dof>=1 and chi2_dist.sf(chi,dof)>=JOINT_P_MIN:sel=d;break
        out[Q]=sel
    return out

def joint_size(ds):
    """Test (j) for one size (revision 13): all degrees 2..9 with per-degree failure bookkeeping (V3-031); d* = lowest degree with
    p >= 1 %. PASS(d*) if d* <= 7; INCONCLUSIVE if d* in {8, 9} or the values alone are not fitted by any degree <= 9 (V3-030);
    FAIL if no joint polynomial of degree <= 9 fits; NUMERICAL FAILURE if a fit at or below the selection point failed."""
    fits=[];failed={}
    for d in JOINT_DEGREES:
        try:fits.append(joint_polyfit(ds,d))
        except (ValueError,np.linalg.LinAlgError,FloatingPointError) as ex:failed[d]=f'{type(ex).__name__}: {ex}'
    sel=next((f for f in fits if f['p']>=JOINT_P_MIN),None);vs=values_smooth(ds);dstar=sel['degree'] if sel is not None else None
    if failed and (dstar is None or any(d<dstar for d in failed)):outcome='NUMERICAL FAILURE';reason=f'fit failed at degree(s) {sorted(failed)}'
    elif dstar is not None and dstar<=JOINT_PASS_MAX_DEGREE:outcome='PASS';reason=None
    elif dstar is not None:outcome='INCONCLUSIVE';reason=f'polynomial degree unresolved at this spacing (d* = {dstar} > {JOINT_PASS_MAX_DEGREE})'
    elif any(v is None for v in vs.values()):outcome='INCONCLUSIVE';reason=f'values alone not fitted by any degree with dof >= 1 (<= {len(ds["beta"])-2} for {len(ds["beta"])} temperatures; the plan text "<= 9" is unrealisable with 9 temperatures — V3-R16-003)'
    else:outcome='FAIL';reason='incompatible with every joint polynomial of degree <= 9'
    return dict(N=int(ds['N']),outcome=outcome,reason=reason,d_star=dstar,fits=[{k:v for k,v in f.items() if k!='pulls'} for f in fits],failed_degrees=failed,values_only_degree=vs,
                pulls_at_dstar=(sel['pulls'].tolist() if sel is not None else None),mean_abs_pull=(sel['mean_abs_pull'] if sel is not None else None))

def joint_procedure(sets):
    per=[joint_size(ds) for ds in sets];outs=[q['outcome'] for q in per]
    outcome=('PASS' if all(o=='PASS' for o in outs) else 'NUMERICAL FAILURE' if 'NUMERICAL FAILURE' in outs else 'FAIL' if 'FAIL' in outs else 'INCONCLUSIVE')
    dmax=max([q['d_star'] for q in per if q['d_star'] is not None],default=None)
    window=None if dmax is None else ('x_max 0.35 (max d* >= 5)' if dmax>=5 else 'x_max 0.45 stands (max d* <= 4)')
    return dict(outcome=outcome,per_size=per,max_d_star=dmax,window_rule=window)

def joint_models(sets):
    """§5.0 validation models with Sigma from the summaries: (i) degree-5 cancellation, (ii) degree 6, (iii) = (i) with +5 sigma(Q') on
    every first derivative (bias applied per dataset), (iv) boundary model: the data's own quadratic (values and derivatives from the
    degree-2 value fit) plus a weak cubic whose amplitude puts the NOISELESS quadratic value fit at the 5 % critical value of chi2_6."""
    m5=synthetic_model(sets,5);m6=synthetic_model(sets,6);crit=float(chi2_dist.isf(0.05,6));m4=[]
    base2=null_mean(sets,[dict(N=ds['N'],Q=Q,degree=2) for ds in sets for Q in OBS])
    for ds,b in zip(sets,base2):
        beta=ds['beta'];x=beta-beta.mean();data=np.array(b['data'],float).copy()
        for Q,(iv,i1,i2) in OBS.items():
            chi_unit=value_fit(beta,x**3,ds['cov'][:,iv,iv],2)[2];eps=float(np.sqrt(crit/chi_unit))
            data[:,iv]+=eps*x**3;data[:,i1]+=3*eps*x**2;data[:,i2]+=6*eps*x
        m4.append(dict(ds,data=data))
    m7=synthetic_model(sets,7)
    # (viii) interpolation null-space fixture (V3-030): model (i) + a prod_j (beta - beta_j): sampled values unchanged, derivatives shifted
    P=np.polynomial.polynomial;m9=[]
    for ds,b in zip(sets,m5):
        beta=ds['beta'];delta=float(np.diff(beta).mean());t=(beta-beta.mean())/delta;c=P.polyfromroots(t);data=np.array(b['data'],float).copy()
        d1=P.polyval(t,P.polyder(c))/delta;d2=P.polyval(t,P.polyder(c,2))/delta**2
        for Q,(iv,i1,i2) in OBS.items():
            a=20.*float(np.median(np.sqrt(ds['cov'][2:7,i1,i1])/np.abs(d1[2:7])))   # first-derivative shift ~ 20 sigma(Q') at the interior points
            data[:,i1]+=a*d1;data[:,i2]+=a*d2   # values: a * prod(t - t_j) = 0 at every sampled temperature
        m9.append(dict(ds,data=data))
    blocks=[[int(n) if n else 488 for n in (ds.get('nblocks') or [None]*9)] for ds in sets]   # block counts of the summaries (default 488)
    return {'cancellation_deg5':(m5,0.,5,{}),'deg6':(m6,0.,6,{}),'deg7':(m7,0.,7,{}),'cancellation_deg5_bias5sigma':(m5,5.,None,{}),
            'boundary_quadratic_plus_weak_cubic':(m4,0.,3,{}),'nullspace_deg9_values_unchanged':(m9,0.,9,{}),
            'cancellation_deg5_reestimated_cov':(m5,0.,5,dict(reestimate_blocks=blocks)),'deg6_reestimated_cov':(m6,0.,6,dict(reestimate_blocks=blocks)),
            'boundary_quadratic_plus_weak_cubic_reestimated_cov':(m4,0.,3,dict(reestimate_blocks=blocks)),
            'sensitivity_first_derivatives_x1.005':(m5,0.,None,dict(bias_rel=0.005,bias_cols=(1,4))),'sensitivity_second_derivatives_x1.05':(m5,0.,None,dict(bias_rel=0.05,bias_cols=(2,5)))}

def joint_validate(models,reps,rng,bias_sigma=0.,bias_rel=0.,bias_cols=(1,4),reestimate_blocks=None):
    """Complete procedure (all degrees, selection, classification, failure bookkeeping) on `reps` independent synthetic datasets of
    `models`. bias_sigma: constant shift of every first derivative by that many standard errors (model (iii)); bias_rel: multiplicative
    bias (1 + bias_rel) on the observable columns `bias_cols` (sensitivity records); reestimate_blocks: per size the per-temperature
    block counts B — each dataset is then generated as B Gaussian blocks per temperature whose mean and re-estimated covariance
    (sample covariance / B) enter the procedure (V3-029). Datasets with NUMERICAL FAILURE or an exception count as numerical
    failures, never as PASS/FAIL (V3-031). Per-size FAIL counts are recorded (V3-028)."""
    chols=[[np.linalg.cholesky(np.asarray(ds['cov'][j])+1e-30*np.eye(6)) for j in range(9)] for ds in models]
    counts=Counter();dstars=[];numfail=0;per_size_fail=[0]*len(models);n_class=0
    for _ in range(reps):
        noisy=[]
        for i,ds in enumerate(models):
            mean=np.asarray(ds['data'],float)
            if reestimate_blocks:
                dat=np.empty_like(mean);cov=np.empty((9,6,6))
                for j in range(9):
                    B=int(reestimate_blocks[i][j]);blk=mean[j]+np.sqrt(B)*(rng.standard_normal((B,6))@chols[i][j].T)   # blocks with covariance B*Sigma
                    dat[j]=blk.mean(0);cov[j]=np.cov(blk,rowvar=False,ddof=1)/B
            else:
                z=rng.standard_normal((9,6));dat=mean+np.stack([chols[i][j]@z[j] for j in range(9)]);cov=np.asarray(ds['cov'])
            if bias_sigma:
                for _,(iv,i1,_) in OBS.items():dat[:,i1]+=bias_sigma*np.sqrt(np.asarray(ds['cov'])[:,i1,i1])
            if bias_rel:
                for col in bias_cols:dat[:,col]*=(1+bias_rel)
            noisy.append(dict(ds,data=dat,cov=cov))
        try:res=joint_procedure(noisy)
        except (ValueError,np.linalg.LinAlgError,FloatingPointError):numfail+=1;continue
        if res['outcome']=='NUMERICAL FAILURE':numfail+=1;continue
        counts[res['outcome']]+=1;dstars.append(res['max_d_star']);n_class+=1
        for i,ps in enumerate(res['per_size']):per_size_fail[i]+=int(ps['outcome']=='FAIL')
    return dict(datasets=reps,classified=n_class,numerical_failures=numfail,counts={k:counts.get(k,0) for k in ('PASS','FAIL','INCONCLUSIVE')},
                rates={k:counts.get(k,0)/max(n_class,1) for k in ('PASS','FAIL','INCONCLUSIVE')},per_size_fail_counts=per_size_fail,
                per_size_fail_rates=[c/max(n_class,1) for c in per_size_fail],max_d_star_distribution={str(k):v for k,v in sorted(Counter(dstars).items(),key=lambda kv:(kv[0] is None,kv[0] or 0))})

def joint_validation_failures(val,n_sizes):
    """§5.0 acceptance (V3-028): one-sided Monte Carlo tests at level JOINT_MC_ALPHA — null models and the null-space fixture: the FAIL
    count must not exceed the declared combined bound significantly; the biased model: the FAIL count must not fall short of the 95 %
    power significantly; noiseless fixtures exact; numerical failures < 1 % of datasets. Sensitivity records are not gated."""
    from scipy.stats import binom
    bad=[];bound=combined_fail_bound(n_sizes)
    for name,v in val.items():
        if v['numerical_failures']>NUMFAIL_MAX*v['datasets']:bad.append(f"{name}: numerical failures {v['numerical_failures']}/{v['datasets']}")
        if name.startswith('sensitivity_'):continue
        n=v['classified'];x=v['counts']['FAIL']
        if name.endswith('bias5sigma'):
            if n and binom.cdf(x,n,JOINT_POWER_MIN)<JOINT_MC_ALPHA:bad.append(f'{name}: FAIL count {x}/{n} significantly below the {JOINT_POWER_MIN:.0%} power requirement')
        elif n and binom.sf(x-1,n,bound)<JOINT_MC_ALPHA:bad.append(f'{name}: FAIL count {x}/{n} significantly above the declared combined bound {bound:.4f}')
        nl=v.get('noiseless')
        if nl and nl.get('expected_d_star') is not None:
            exp_out='INCONCLUSIVE' if nl['expected_d_star']>JOINT_PASS_MAX_DEGREE else 'PASS'
            if nl['outcome']!=exp_out or nl['max_chi2_at_dstar'] is None or nl['max_chi2_at_dstar']>JOINT_NOISELESS_CHI2_MAX or any(d!=nl['expected_d_star'] for d in nl['d_star']):
                bad.append(f"{name}: noiseless fixture {nl['outcome']} d*={nl['d_star']} chi2={nl['max_chi2_at_dstar']} (expected {exp_out} at d*={nl['expected_d_star']}, chi2 <= {JOINT_NOISELESS_CHI2_MAX})")
    return bad

# ---------------------------------------------------------------- immutable, provenance-bound run records (V3-027)
def sha256(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
RECORD_FILES=('n0_result.json','n0_manifest.json','N0_RESULT.md')
def check_fresh_out(out):
    out=Path(out)
    if out.exists() and any((out/f).exists() for f in RECORD_FILES):raise SystemExit(f'refusing to overwrite an existing N0 record in {out}; use a new --out directory (V3-027)')
def write_manifest(out,a,rule):
    here=Path(__file__).resolve().parent;plan=here/'FIT_MODEL_V3.md';txt=plan.read_text() if plan.exists() else ''
    m=re.search(r'Status: revision (\d+)',txt);rev=m.group(1) if m else None
    man=dict(protocol=f'FIT_MODEL_V3.md revision {rev} §5.0 rule {rule}',plan_path=str(plan),plan_sha256=(sha256(plan) if plan.exists() else None),
             implementation={f:sha256(here/f) for f in ('n0_diagnostic.py','quotients.py','analyze.py') if (here/f).exists()},
             invocation=' '.join(sys.argv),arguments={k:(str(v) if isinstance(v,Path) else ([str(x) for x in v] if isinstance(v,list) else v)) for k,v in vars(a).items()},
             seed=a.seed,rule=rule,constants=dict(JOINT_DEGREES=list(JOINT_DEGREES),JOINT_PASS_MAX_DEGREE=JOINT_PASS_MAX_DEGREE,JOINT_P_MIN=JOINT_P_MIN,JOINT_FAIL_PER_SIZE=JOINT_FAIL_PER_SIZE,JOINT_MC_ALPHA=JOINT_MC_ALPHA,JOINT_POWER_MIN=JOINT_POWER_MIN,SYNTH_EXCURSION=SYNTH_EXCURSION,
             SMOOTH_P_MIN=SMOOTH_P_MIN,PREREG_CHI2_DOF_MAX=PREREG_CHI2_DOF_MAX,DEGREES=list(DEGREES),NULL_RATE_BAND=NULL_RATE_BAND,DATA_NULL_BAND=DATA_NULL_BAND,POWER_MIN=POWER_MIN),
             inputs={str(Path(p).resolve()):(sha256(p) if Path(p).exists() else 'MISSING') for p in a.summaries},versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__),
             host=platform.node(),time=time.strftime('%Y-%m-%d_%H:%M:%S'))
    (Path(out)/'n0_manifest.json').write_text(json.dumps(man,indent=1,default=str)+'\n')
    # executable source snapshot of the diagnostic beside the record (V3-033)
    src=Path(out)/'source';src.mkdir(exist_ok=True)
    for f in ('n0_diagnostic.py','quotients.py'):
        if (here/f).exists():(src/f).write_bytes((here/f).read_bytes())
    man['source_snapshot']=str(src);return man

def write_failure_record(a,rec,reason):
    """IR14-006: an attempted run always leaves an immutable record; used for central NUMERICAL FAILURE and for any exception
    raised during validation or setup."""
    rec.update(outcome='NUMERICAL FAILURE',reason=reason,production=False,production_problems=list(rec.get('production_problems',[]))+[reason])
    (a.out/'n0_result.json').write_text(json.dumps(rec,indent=1,default=float)+'\n')
    (a.out/'N0_RESULT.md').write_text(f"# N0 diagnostic — outcome **NUMERICAL FAILURE** (NON-PRODUCTION)\n\nreason: {reason}\ninputs: {rec.get('inputs')}\n");print(f'NUMERICAL FAILURE: {reason}')
    raise SystemExit(1)   # IR5-005: a numerical failure is never a zero exit

def main_joint(a,sets,rec,inprob,man):
    J=joint_procedure(sets);rec.update(outcome=J['outcome'],joint=J,window_rule=J['window_rule'],max_d_star=J['max_d_star']);problems=list(inprob)
    if J['outcome']=='NUMERICAL FAILURE':   # persist before any validation work (IR14-006)
        return write_failure_record(a,rec,'central fit: '+'; '.join(f"N={ps['N']}: {ps['reason']}" for ps in J['per_size'] if ps['outcome']=='NUMERICAL FAILURE'))
    if a.validate:
        val={};k=0
        for name,(models,bias,expected,extra) in joint_models(sets).items():
            nl=joint_procedure(models);chi_at=[f['chi2'] for ps in nl['per_size'] for f in ps['fits'] if ps['d_star'] is not None and f['degree']==ps['d_star']]
            v=joint_validate(models,a.reps,np.random.default_rng(np.random.SeedSequence([a.seed,101,k])),bias_sigma=bias,**extra);k+=1
            v['noiseless']=dict(outcome=nl['outcome'],d_star=[ps['d_star'] for ps in nl['per_size']],max_chi2_at_dstar=(max(chi_at) if chi_at else None),expected_d_star=expected);val[name]=v
        rec['validation']=val;rec['validation_failures']=joint_validation_failures(val,len(sets));problems+=rec['validation_failures']
    else:problems.append('procedure validation not run (--validate)')
    for ps in J['per_size']:
        if ps['outcome']=='NUMERICAL FAILURE':problems.append(f"N={ps['N']}: {ps['reason']}")
    rec['combined_false_fail_bound']=combined_fail_bound(len(sets));rec['production']=not problems;rec['production_problems']=problems
    if rec['outcome']=='PASS' and problems:rec['outcome_before_validation']='PASS';rec['outcome']='INCONCLUSIVE';rec['reason']='procedure validation failed or absent, or inputs incomplete: '+'; '.join(problems)
    (a.out/'n0_result.json').write_text(json.dumps(rec,indent=1,default=float)+'\n')
    L=[f"# N0 diagnostic (test (j), joint polynomial) — outcome **{rec['outcome']}**"+('' if rec['production'] else ' (NON-PRODUCTION: '+'; '.join(problems)+')'),'',
       f"protocol: {man['protocol']} (plan {str(man['plan_sha256'])[:12]}…, code {man['implementation'].get('n0_diagnostic.py','')[:12]}…, seed {a.seed})",f"inputs: {rec['inputs']}",'']
    for g in rec['grid']:L.append(f"- grid N={g['N']} s={g['s']}: center {g['center']:.8f}, delta {g['delta']:.4e}, chains per temperature {g['replicas']}, used sweeps {g['used_sweeps']}")
    L.append('')
    for ps in J['per_size']:
        L.append(f"- N={ps['N']}: {ps['outcome']}"+(f" at d* = {ps['d_star']}" if ps['d_star'] else '')+(f" ({ps['reason']})" if ps.get('reason') else '')+"; joint chi2/dof (p) by degree: "+', '.join(f"d{f['degree']}: {f['chi2']/f['dof']:.2f} ({f['p']:.3g})" for f in ps['fits'])+(f"; failed degrees {ps['failed_degrees']}" if ps['failed_degrees'] else '')+f"; values-only degrees {ps['values_only_degree']}"+(f"; mean |pull| at d*: "+', '.join(f'{q} {v:.2f}' for q,v in ps['mean_abs_pull'].items()) if ps['mean_abs_pull'] else ''))
    L+=['',f"window rule: {J['window_rule']}",f"error budget: {JOINT_FAIL_PER_SIZE:.0%} false FAIL per size, combined bound {combined_fail_bound(len(sets)):.4f} for {len(sets)} sizes"]
    if rec.get('reason'):L.append(f"reason: {rec['reason']}")
    if 'validation' in rec:
        L+=['',f"validation of the procedure ({a.reps} independent datasets per model, complete procedure per dataset; one-sided Monte Carlo acceptance at {JOINT_MC_ALPHA:.0%}: null FAIL counts against the combined bound {combined_fail_bound(len(sets)):.4f}, the biased model against {JOINT_POWER_MIN:.0%} power; noiseless fixtures exact; numerical failures < {NUMFAIL_MAX:.0%}):"]
        for k2,v in rec['validation'].items():L.append(f"- {k2}: counts {v['counts']} of {v['classified']} classified (numerical failures {v['numerical_failures']}); rates PASS {v['rates']['PASS']:.4f} FAIL {v['rates']['FAIL']:.4f} INCONCLUSIVE {v['rates']['INCONCLUSIVE']:.4f}; per-size FAIL rates {[round(r,4) for r in v['per_size_fail_rates']]}; max d* {v['max_d_star_distribution']}; noiseless {v['noiseless']}")
        L.append('validation verdict: '+('all criteria satisfied' if not rec['validation_failures'] else 'FAILED — '+'; '.join(rec['validation_failures'])))
    (a.out/'N0_RESULT.md').write_text('\n'.join(L)+'\n');print('\n'.join(L))

def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('summaries',type=Path,nargs='+');p.add_argument('--out',type=Path,required=True);p.add_argument('--reps',type=int,default=10000)
    p.add_argument('--seed',type=int,default=20260918);p.add_argument('--validate',action='store_true',help='run the procedure validation on synthetic models (§5.0)')
    p.add_argument('--rule',choices=['joint','rev11','preregistered'],default='joint',help='joint = revision-12 test (j); rev11 / preregistered = superseded value-only rules, kept reproducible')
    a=p.parse_args();check_fresh_out(a.out);a.out.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(a.seed)
    global RULE;RULE=a.rule
    man=write_manifest(a.out,a,a.rule)   # provenance first (AUDIT-003): input hashes are taken from the files, before any parsing
    rec=dict(inputs=[str(s.resolve()) for s in a.summaries],rule=a.rule,protocol=man['protocol'],plan_sha256=man['plan_sha256'],implementation=man['implementation'],seed=a.seed,input_sha256=man['inputs'])
    try:
        sets=[load(s) for s in a.summaries];rec['sizes']=[d['N'] for d in sets]
        inprob=input_problems(sets,a.reps);rec['input_problems']=inprob
        rec['grid']=[dict(N=d['N'],s=d['s'],center=d['center'],delta=d['delta'],replicas=sorted(set(d['replicas'])),used_sweeps=[min(d['used_sweeps']),max(d['used_sweeps'])] if all(u is not None for u in d['used_sweeps']) else None) for d in sets]
        if a.rule=='joint':return main_joint(a,sets,rec,inprob,man)
        return main_legacy(a,sets,rec,inprob,man,rng)
    except Exception as ex:   # CLI boundary (IR14-006): never leave an attempted run without a record
        if not (a.out/'n0_result.json').exists():write_failure_record(a,rec,f'{type(ex).__name__}: {ex}')
        raise SystemExit(1)

def main_legacy(a,sets,rec,inprob,man,rng):
    obs=procedure(sets);rec['smoothness']=[{k:v for k,v in rw.items() if k!='r'} for rw in obs['rows']]
    if obs['outcome']=='INCONCLUSIVE':
        rec.update(outcome='INCONCLUSIVE',reason=f"values not fit by any degree <= 6 under rule {RULE} at {obs['inconclusive']}")
    else:
        null=null_mean(sets,obs['rows']);degs=[];Ts,excl,numfail,draws=calibrate(null,a.reps,rng,record=degs)
        rec.update(T=obs['T'],rank=obs['rank'],p_naive_chi2=obs['p_naive'],calibration=dict(conclusive=len(Ts),smoothness_excluded=excl,numerical_failures=numfail,draws=draws),
                   calibration_branches=branch_summary(Ts,degs),detectable_bias=detectable_bias(sets,obs['rows']))
        if len(Ts)<a.reps or numfail>0.01*draws:rec.update(outcome='INCONCLUSIVE',reason='calibration could not reach the required conclusive replicates or too many numerical failures')
        else:
            thr=float(np.quantile(Ts,0.99));rec.update(T_threshold_99=thr,outcome='PASS' if obs['T']<thr else 'FAIL',calibrated_p=float(np.mean(Ts>=obs['T'])))
            # achieved rejection rate on an INDEPENDENT replicate set (never the set that fixed the threshold)
            Ts2,e2,n2,d2=calibrate(null,a.reps,np.random.default_rng(a.seed+1));rec['achieved_null_fail_rate']=float(np.mean(Ts2>=thr))
            rec['achieved_set']=dict(conclusive=len(Ts2),smoothness_excluded=e2,numerical_failures=n2,draws=d2)
    # ---- production status: a PASS is production only if the data's own null reproduces the 1 % rate on the independent set
    # AND the procedure validation (§5.0 (i)-(iii), independent sets) was run and satisfied (FITV3-006)
    problems=list(inprob)
    if rec.get('outcome') in ('PASS','FAIL'):
        r=rec['achieved_null_fail_rate']
        if not (DATA_NULL_BAND[0]<=r<=DATA_NULL_BAND[1]):problems.append(f'achieved null FAIL rate {r:.4f} outside the gross-error band {DATA_NULL_BAND}')
        if len(rec['achieved_set']['conclusive'] and [1] or [])==0 or rec['achieved_set']['conclusive']<a.reps:problems.append('independent null set short of the required conclusive replicates')
    if a.validate:
        # (i) cancellation degree 5 (unbiased sets A, B; biased set C = model (iii)), (ii) degree 6
        val={'cancellation_deg5':validate_model(synthetic_model_legacy(sets,5),a.reps,a.seed+7,bias_units=5.),
             'deg6':validate_model(synthetic_model_legacy(sets,6),a.reps,a.seed+17)}   # original generators of the superseded rules (V3-033)
        rec['validation']=val;rec['validation_failures']=validation_failures(val,a.reps);problems+=rec['validation_failures']
    else:problems.append('procedure validation not run (--validate)')
    rec['production']=not problems;rec['production_problems']=problems
    if rec.get('outcome')=='PASS' and problems:
        rec['outcome_before_validation']='PASS';rec['outcome']='INCONCLUSIVE';rec['reason']='procedure validation failed or absent: '+'; '.join(problems)
    (a.out/'n0_result.json').write_text(json.dumps(rec,indent=1,default=float)+'\n')
    L=[f"# N0 diagnostic (superseded value-only rule '{RULE}') — outcome **{rec['outcome']}**"+('' if rec['production'] else ' (NON-PRODUCTION: '+'; '.join(problems)+')'),'',f"protocol: {man['protocol']} (plan {str(man['plan_sha256'])[:12]}…, seed {a.seed})",f"inputs: {rec['inputs']}",'']
    for g in rec['grid']:L.append(f"- grid N={g['N']} s={g['s']}: center {g['center']:.8f}, delta {g['delta']:.4e}, chains per temperature {g['replicas']}, used sweeps {g['used_sweeps']}")
    L.append('')
    for rw in rec['smoothness']:L.append(f"- N={rw['N']} {rw['Q']}: value polynomial degree {rw['degree']}, chi2/dof {rw['chi2_dof']:.2f} (p = {rw.get('p_value',float('nan')):.3f}; rule {RULE}: lowest degree with {'chi2/dof <= 1.5' if RULE=='preregistered' else 'p >= 0.01'})")
    if 'T' in rec:L+=['',f"T = {rec['T']:.2f} (rank {rec['rank']}); calibrated threshold (99 %) = {rec.get('T_threshold_99','—')}; calibrated p = {rec.get('calibrated_p','—')}; achieved null FAIL rate = {rec.get('achieved_null_fail_rate','—')}",f"calibration: {rec['calibration']}"]
    if rec.get('reason'):L.append(f"reason: {rec['reason']}")
    if rec.get('calibration_branches'):
        L+=['','null mixture by re-selected degrees (Y, U per size): count, fraction, median T, 99 % quantile of T:']+[f"- {b['degrees']}: {b['count']} ({b['fraction']:.1%}), median T {b['median_T']:.1f}, q99 {b['q99_T'] if b['q99_T'] is None else round(b['q99_T'],1)}" for b in rec['calibration_branches']]
    if 'validation' in rec:
        L+=['','validation of the procedure (independent replicate sets; criteria: P(FAIL|conclusive) in %s, power >= %.2f, noiseless T <= %g, numerical failures < %.0f %%):'%(NULL_RATE_BAND,POWER_MIN,NOISELESS_T_MAX,100*NUMFAIL_MAX)]
        for k,v in rec['validation'].items():
            ev=v.get('evaluation_set',{});bs=v.get('biased_set')
            L.append(f"- {k}: noiseless T = {v['noiseless']['T']}; threshold set {v.get('threshold_set',{}).get('conclusive')} conclusive, T99 = {v.get('threshold_set',{}).get('T_threshold_99')}; "
                     f"evaluation set {ev.get('conclusive')} conclusive: P(FAIL|conclusive) = {ev.get('fail_rate_conditional')}, P(INCONCLUSIVE) = {ev.get('inconclusive_rate')} (consistent: {v.get('inconclusive_consistent')})"
                     +(f"; biased set ({bs['bias_in_sigma_R']} sigma_R = {bs['bias_in_derivative_sigmas']:.1f} sigma(Q')): P(FAIL|conclusive) = {bs['fail_rate_conditional']}, unconditional {bs['fail_rate_unconditional']}" if bs else ''))
        L.append('validation verdict: '+('all criteria satisfied' if not rec['validation_failures'] else 'FAILED — '+'; '.join(rec['validation_failures'])))
    (a.out/'N0_RESULT.md').write_text('\n'.join(L)+'\n');print('\n'.join(L))
if __name__=='__main__':main()
