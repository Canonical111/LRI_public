#!/usr/bin/env python3
"""v2 fitting protocol (FIT_PLAN.md §3): family of global fits, data-driven degree selection, quotability gates,
calibrated residual-structure test, systematic spread, model-independent cross-check with a paired bootstrap, reblocking.

Usage: select_model.py --merged CAMP/merged_b4096_T --reblock CAMP/merged_b2048_T CAMP/merged_b8192_T --out CAMP/fits_v2_T
       [--s 0.875 0.8] [--bootstrap 300] [--schedule 20260916] [--calibration 500] [--workers W]

A run is PRODUCTION only with the protocol's fixed settings (bootstrap 300, calibration 500, calibration not skipped,
both reblocking inputs present, distinct and covering the block-4096 input); anything else is labelled NON-PRODUCTION
and can never be ACCEPTED. Nothing in here looks at the value of Delta_epsilon when selecting a model: the ladder uses
chi2 only, the gates use residual statistics only. The rules and caps are those written in FIT_PLAN.md before any v2 fit
was run. Provenance: every consumed summary and block archive, the plan and the implementation are hashed into the
manifest; the cross-check's bootstrap samples, covariances, per-draw extrapolations and validity masks are persisted.
"""
from __future__ import annotations
import argparse, hashlib, itertools, json, os, platform, sys, time, traceback
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import scipy
from scipy.stats import f as f_dist, norm
from scipy.linalg import solve_triangular
import fit_fss, quotients
from equilibration import check as equilibration_check

# ---------------------------------------------------------------- protocol constants (FIT_PLAN.md §2, §3.2–3.8)
WINDOWS={'full':'summary.json','c3':'summary_c3.json'}
VARIANTS=['leading','background','second']
NMINS=[4096,8192,16384]
FIELD_ORDERS=[1,2]
DEGREES=[3,4,5,6,7]           # quotable degrees; 8 only as comparator for d*=7
CDEG=2
LADDER_P=0.01                 # F-test significance for adding two amplitudes
CHI2_DOF_MAX=1.5
PULL_MAX=1.2
PROTOCOL_BOOTSTRAP=300;PROTOCOL_CALIBRATION=500
BOOT_VALID_FRAC=0.9           # >= 270 of 300 requested
STABILITY_SIGMAS=3.0
SYS_CAPS={0.0625:0.0015,0.1:0.004}   # the two anchors of FIT_PLAN.md §2 (exact)
def sys_cap(ds):
    """sigma_sys cap by Delta_sigma (FIT_PLAN.md §6): 0.0015 up to 1/16, linear between the anchors, 0.04*ds above 0.1."""
    ds=float(ds)
    for k,v in SYS_CAPS.items():
        if abs(ds-k)<1e-9:return v
    if ds<0.0625:return 0.0015
    if ds<=0.1:return 0.0015+(0.004-0.0015)*(ds-0.0625)/(0.1-0.0625)
    return 0.04*ds
SYS_MIN_FITS,SYS_MIN_NMIN,SYS_MIN_VARIANTS=4,2,2
XCHECK_DEGREES=[4,5,6]
XCHECK_PAIRS=[32768,65536,131072,262144]   # smaller size of the four largest doubling pairs
XCHECK_LOCAL_CHI2_MAX=2.0
XCHECK_JOINT_VALID_MIN=0.9
XCHECK_CHI2_DOF_MAX=2.0
OMEGA_GRID=np.round(np.arange(0.2,2.0+1e-9,0.01),2)
OMEGA_MARGIN=0.02
XCHECK_DRAW_CONVERGE_MIN=0.9
COMMON_VALID_FRAC=0.9         # >= 270 of 300 requested
CALIB_FAIL_MAX=0.02
REBLOCK_BLOCKS=(2048,8192);REBLOCK_TOL=0.30
VARIANT_RANK={'leading':0,'background':1,'second':2};WINDOW_RANK={'full':0,'c3':1}
IMPLEMENTATION_FILES=['FIT_PLAN.md','select_model.py','fit_fss.py','quotients.py','bootstrap_schedule.py','analyze.py','equilibration.py',
                      'run_fits_v2.sh','run_point_v2.sh','registry.py','completion_check.py','merge_summaries.py','window_filter.py']
NUMERICAL_ERRORS=(ValueError,np.linalg.LinAlgError,FloatingPointError,ZeroDivisionError)

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def key_of(c):return f"ds{c['ds']}_{c['window']}_{c['variant']}_Nmin{c['Nmin']}_K{c['K']}_deg{c['degree']}"
def cfg_of(c):return f"{c['window']}_{c['variant']}_Nmin{c['Nmin']}_K{c['K']}"
def ds_of(s):
    """Delta_sigma from s at the scan's declared precision (7 decimals, e.g. 0.1727335), as a float and a label."""
    ds=round((1-float(s))/2,7);return ds,('%.7f'%ds).rstrip('0').rstrip('.')
def f5(x,fmt='%.5f'):return '—' if x is None or (isinstance(x,float) and not np.isfinite(x)) else fmt%x

# ---------------------------------------------------------------- residual-structure statistics (§3.7)
def runs_pvalue(signs):
    signs=np.asarray(signs,bool);n=len(signs);n1=int(signs.sum());n2=n-n1
    if n1==0 or n2==0:return 0.0                      # a single run: maximal structure
    R=1+int(np.sum(signs[1:]!=signs[:-1]))
    mu=1+2*n1*n2/n;var=2*n1*n2*(2*n1*n2-n)/(n*n*(n-1))
    if var<=0:return 1.0
    return float(2*norm.sf(abs(R-mu)/np.sqrt(var)))

def residual_stats(pull_rows):
    """T = min_Q p_runs(Q) (signs ordered by N then beta), R = max_Q |rho_1(Q)| (pooled lag-1 along beta within N)."""
    rows=sorted(pull_rows,key=lambda d:(d['N'],d['beta']));P=np.array([d['pull'] for d in rows]);Ns=np.array([d['N'] for d in rows])
    T=1.0;R=0.0;per_obs=[]
    for q in range(P.shape[1]):
        p=P[:,q];pr=runs_pvalue(p>=0);num=0.;den=0.
        for N in np.unique(Ns):
            v=p[Ns==N];num+=float(np.sum(v[:-1]*v[1:]));den+=float(np.sum(v*v))
        rho=num/den if den>0 else 0.
        per_obs.append(dict(p_runs=pr,rho1=rho));T=min(T,pr);R=max(R,abs(rho))
    return T,R,per_obs

def calibration_seed(schedule,s,cfg_index,chunk_index):
    """Stable integer entropy for one calibration chunk (FITV2-003): no Python hash() of strings."""
    return [int(schedule),int(round(s*1e6)),int(cfg_index),int(chunk_index)]

# ---------------------------------------------------------------- worker functions (module level for multiprocessing)
def w_central(job):
    try:
        entries=fit_fss.load_entries(job['summary'],job['s'],job['Nmin'])
        r=fit_fss.run_fit(job['summary'],entries,job['degree'],CDEG,job['variant'],field_order=job['K'],tag=job['window'])
        r['config']=cfg_of(job);r['window']=job['window'];r['K']=job['K']
        return job,r
    except NUMERICAL_ERRORS as ex:
        return job,dict(error=f'{type(ex).__name__}: {ex}',config=cfg_of(job),window=job['window'],K=job['K'],degree=job['degree'],variant=job['variant'],Nmin=job['Nmin'])

def w_bootstrap(job):
    try:
        entries=fit_fss.load_entries(job['summary'],job['s'],job['Nmin'])
        r=fit_fss.run_fit(job['summary'],entries,job['degree'],CDEG,job['variant'],field_order=job['K'],
                          bootstrap=job['bootstrap'],schedule=job['schedule'],tag=job['window'])
        r['config']=cfg_of(job);r['window']=job['window'];r['K']=job['K']
        return job,r
    except NUMERICAL_ERRORS as ex:
        return job,dict(error=f'{type(ex).__name__}: {ex}',config=cfg_of(job),window=job['window'],K=job['K'],degree=job['degree'],variant=job['variant'],Nmin=job['Nmin'])

def w_calibration(job):
    """n pseudo-datasets from the fitted model with the points' sampling covariance; complete refit (amplitudes and all
    nonlinear parameters, warm start); returns (T, R, converged) per pseudo-dataset. A numerical exception in one refit
    counts as a non-converged replicate (FITV2-007)."""
    entries=fit_fss.load_entries(job['summary'],job['s'],job['Nmin'])
    model=fit_fss.ProfileFit(entries,job['degree'],CDEG,job['variant'],field_order=job['K'])
    p0=np.array(job['parameters']);pred=np.array(job['predictions']);rng=np.random.default_rng(np.random.SeedSequence(job['seed']));out=[]
    for _ in range(job['n']):
        pseudo=pred+model.colour(rng.standard_normal(pred.size))
        try:
            f=model.fit(pseudo,initial=p0,multistart=False);ok=bool(f['success'] and not f['flags'])
            T,R,_=residual_stats(f['pulls']);out.append((T,R,ok))
        except NUMERICAL_ERRORS:out.append((np.nan,np.nan,False))
    return job['key'],out

def w_quotients(job):
    entries=[e for e in json.loads(Path(job['summary']).read_text())['entries'] if abs(e['s']-job['s'])<1e-12]
    r,samples=quotients.process(entries,Path(job['summary']).parent,job['degree'],job['bootstrap'],
                                np.random.default_rng(1348772),job['schedule'])
    return job,r,samples

# ---------------------------------------------------------------- cross-check extrapolation (§3.5)
def gls_extrapolate(values,cov,sizes,kinds):
    """values (8), cov (8x8), sizes (8), kinds (8: 0=U,1=Y). Generalised least squares on the omega' grid with Cholesky
    whitening (FITV2-006: a non-finite or non-positive-definite covariance, or a rank-deficient whitened design, is
    rejected explicitly instead of being pseudo-inverted). Returns a dict (with 'reason' when unusable)."""
    values=np.asarray(values,float);cov=np.asarray(cov,float)
    if not (np.all(np.isfinite(values)) and np.all(np.isfinite(cov))):return dict(reason='non-finite values or covariance')
    try:L=np.linalg.cholesky(cov)
    except np.linalg.LinAlgError:return dict(reason='covariance not positive definite')
    if np.linalg.cond(cov)>1e12:return dict(reason='covariance condition number > 1e12')
    wv=solve_triangular(L,values,lower=True);best=None;chis=[];grid=[]
    for om in OMEGA_GRID:
        X=np.zeros((len(values),3));X[:,0]=1.
        X[:,1]=np.where(kinds==0,sizes**(-om),0.);X[:,2]=np.where(kinds==1,sizes**(-om),0.)
        wX=solve_triangular(L,X,lower=True)
        theta,_,rank,_=np.linalg.lstsq(wX,wv,rcond=None)
        if rank<3:chis.append(np.inf);continue
        res=wv-wX@theta;chi=float(res@res);chis.append(chi);grid.append((float(om),chi,float(theta[0])))
        if best is None or chi<best['chi2']:best=dict(omega=float(om),Delta_inf=float(theta[0]),c_U=float(theta[1]),c_Y=float(theta[2]),chi2=chi)
    chis=np.array(chis)
    if best is None or not np.isfinite(best['chi2']):return dict(reason='no finite grid minimum')
    # omega' profile: grid points with Delta chi2 <= 1 (FIT_MODEL_V3 §4.6 standalone Delta_omega'; additive record, v2 logic unchanged)
    prof=[g for g in grid if np.isfinite(g[1]) and g[1]<=best['chi2']+1.]
    best['profile_Delta_inf_range']=[min(g[2] for g in prof),max(g[2] for g in prof)];best['profile_omega_range']=[min(g[0] for g in prof),max(g[0] for g in prof)]
    best['unique']=bool(np.sum(chis<=best['chi2']*(1+1e-9)+1e-12)==1)
    best['dof']=len(values)-4;best['on_bound']=bool(best['omega']<OMEGA_GRID[0]+OMEGA_MARGIN-1e-9 or best['omega']>OMEGA_GRID[-1]-OMEGA_MARGIN+1e-9)
    return best

def crosscheck_series(qr,samples):
    """One (degree, window) combination: central eligibility, central extrapolation and per-draw extrapolations.
    Per-draw validity is existence/convergence only (FIT-010); the chi2 and omega' gates apply to the central fit."""
    rows=qr['crossings'];idx=[]
    for N in XCHECK_PAIRS:
        j=[i for i,r in enumerate(rows) if r['N']==N and r['crossing_observable']=='U']
        if len(j)!=1:return dict(eligible=False,reason=f'missing U crossing at N={N}')
        idx.append(j[0])
    diag={str(k):v for k,v in qr['local_fit_diagnostics'].items()};sizes5=[str(N) for N in XCHECK_PAIRS]+[str(2*XCHECK_PAIRS[-1])]
    bad=[N for N in sizes5 if N not in diag or diag[N]['chi2']/max(diag[N]['dof'],1)>XCHECK_LOCAL_CHI2_MAX]
    out=dict(row_indices=idx,local_chi2_dof={N:diag[N]['chi2']/max(diag[N]['dof'],1) for N in sizes5 if N in diag})
    if bad:out.update(eligible=False,reason=f'local chi2/dof > {XCHECK_LOCAL_CHI2_MAX} at N={bad}');return out
    S=np.asarray(samples)[:,idx,:]                         # (draws, 4, 3): beta, Delta_Y, Delta_U
    valid=np.all(np.isfinite(S),axis=(1,2));frac=float(valid.mean()) if len(valid) else 0.
    out['joint_valid_fraction']=frac;out['draw_valid']=valid.tolist()
    if frac<XCHECK_JOINT_VALID_MIN:out.update(eligible=False,reason=f'joint validity {frac:.3f} < {XCHECK_JOINT_VALID_MIN}');return out
    # eight effective exponents: U rows then Y rows
    vals=np.array([rows[i]['Delta_epsilon_eff_from_U'] for i in idx]+[rows[i]['Delta_epsilon_eff_from_Y'] for i in idx])
    draws8=np.concatenate([S[:,:,2],S[:,:,1]],axis=1)      # (draws, 8)
    cov=np.cov(draws8[valid],rowvar=False);sizes=np.array(XCHECK_PAIRS*2,float);kinds=np.array([0]*4+[1]*4)
    out['values']=vals.tolist();out['covariance']=cov.tolist();out['covariance_order']='Delta_eff_U(pairs) then Delta_eff_Y(pairs), pairs ascending'
    central=gls_extrapolate(vals,cov,sizes,kinds);out['central']=central
    if 'reason' in central:out.update(eligible=False,reason='central extrapolation: '+central['reason']);return out
    if central['chi2']/central['dof']>XCHECK_CHI2_DOF_MAX:out.update(eligible=False,reason=f"extrapolation chi2/dof {central['chi2']/central['dof']:.2f} > {XCHECK_CHI2_DOF_MAX}");return out
    if central['on_bound'] or not central['unique']:out.update(eligible=False,reason="omega' at grid bound or not unique");return out
    per_draw=np.full(len(valid),np.nan);conv=np.zeros(len(valid),bool)
    for k in np.flatnonzero(valid):
        g=gls_extrapolate(draws8[k],cov,sizes,kinds)
        if 'reason' not in g and g['unique'] and np.isfinite(g['Delta_inf']):per_draw[k]=g['Delta_inf'];conv[k]=True
    cfrac=float(conv[valid].mean());out['draw_convergence_fraction']=cfrac;out['per_draw_Delta_inf']=per_draw.tolist();out['draw_converged']=conv.tolist()
    if cfrac<XCHECK_DRAW_CONVERGE_MIN:out.update(eligible=False,reason=f'per-draw extrapolation converged in {cfrac:.3f} < {XCHECK_DRAW_CONVERGE_MIN}');return out
    q=np.percentile(per_draw[conv],[16,84]);out['sigma_Delta_inf']=float((q[1]-q[0])/2);out['eligible']=True
    return out

def paired_comparison(series,E,qdraws,nd,quoted_value):
    """§3.6 on the fixed eligible set E: common-valid mask (global fit converged & unflagged AND every member of E
    converged on that draw), per-draw median over E, sigma_inf, D_k, sigma_D with the model spread, criterion 3."""
    X={'eligible':list(E)}
    if len(E)<2:X['status']='CROSS-CHECK UNAVAILABLE (fewer than 2 eligible series)';return X
    central=np.array([series[n]['central']['Delta_inf'] for n in E]);Dinf=float(np.median(central));spread=float((central.max()-central.min())/2)
    gvalid=np.zeros(nd,bool);gq=np.full(nd,np.nan)
    for d in qdraws:
        gvalid[d['draw']]=bool(d['success'] and not d['flags'] and np.isfinite(d['Delta_epsilon']));gq[d['draw']]=d['Delta_epsilon']
    common=gvalid.copy()
    for n in E:common&=np.array(series[n]['draw_converged'],bool)
    X.update(Delta_inf_central=Dinf,model_spread=spread,global_valid_draws=int(gvalid.sum()),common_valid_draws=int(common.sum()),
             global_valid_mask=gvalid.tolist(),common_valid_mask=common.tolist())
    need=int(np.ceil(COMMON_VALID_FRAC*nd))
    if common.sum()<need:X['status']=f'CROSS-CHECK UNAVAILABLE (common-valid {int(common.sum())} < {need})';return X
    per=np.array([series[n]['per_draw_Delta_inf'] for n in E]);Dk=np.median(per[:,common],axis=0)
    D=gq[common]-Dk;q16,q84=np.percentile(Dk,[16,84]);s_inf=(q84-q16)/2;d16,d84=np.percentile(D,[16,84])
    s_D=float(np.hypot((d84-d16)/2,spread));diff=quoted_value-Dinf
    X.update(sigma_Delta_inf=float(s_inf),sigma_D=s_D,paired_difference_central=float(diff),per_draw_Delta_inf_median=Dk.tolist(),
             paired_differences=D.tolist(),paired_difference_draws_16_50_84=np.percentile(D,[16,50,84]).tolist(),passed=bool(abs(diff)<=2*s_D))
    X['status']='pass' if X['passed'] else 'CROSS-CHECK FAILED (|difference| > 2 sigma_D)'
    return X

# ---------------------------------------------------------------- provenance and input validation
def group_set(summary):
    return {(round(e['s'],12),int(e['N']),round(e['beta'],12)) for e in json.loads(Path(summary).read_text())['entries']}

def window_consistency(d):
    """FITV2-010/014: the block size of BOTH summaries of a directory; unique coordinates; every (s, N) group has exactly
    five distinct temperatures in the full window and exactly their middle three in c3; every c3 entry is the same
    measurement as its full-window counterpart (data, covariance, block size, resolved block archive). Returns (block size, notes)."""
    notes=[];full={};bs=set();groups={}
    for f in WINDOWS.values():
        seen=set()
        for e in json.loads((d/f).read_text())['entries']:
            bs.add(e['block_size']);k=(round(e['s'],12),int(e['N']),round(e['beta'],12))
            if k in seen:notes.append(f'{d}: {f}: duplicate coordinate {k}');return None,notes
            seen.add(k)
            if f=='summary.json':full[k]=e;groups.setdefault(k[:2],[]).append(k[2])
    if len(bs)!=1:notes.append(f'{d}: mixed block sizes {sorted(bs)} across summary.json/summary_c3.json');return None,notes
    c3groups={}
    for e in json.loads((d/WINDOWS['c3']).read_text())['entries']:
        k=(round(e['s'],12),int(e['N']),round(e['beta'],12));g=full.get(k)
        if g is None:notes.append(f'{d}: c3 entry {k} absent from summary.json');break
        if e['data']!=g['data'] or e['cov']!=g['cov'] or e['block_size']!=g['block_size'] or (d/e['blocks_file']).resolve()!=(d/g['blocks_file']).resolve():
            notes.append(f'{d}: c3 entry {k} differs from its full-window counterpart (data/cov/block archive)');break
        c3groups.setdefault(k[:2],[]).append(k[2])
    if notes:return None,notes
    for g,betas in groups.items():
        if len(betas)!=5:notes.append(f'{d}: group {g} has {len(betas)} temperatures in the full window, not 5');break
        mid=sorted(betas)[1:4]
        if sorted(c3groups.get(g,[]))!=mid:notes.append(f'{d}: group {g}: c3 window is not exactly the middle three of the five temperatures');break
    if set(c3groups)-set(groups):notes.append(f'{d}: c3 has groups absent from the full window')
    return (bs.pop() if not notes else None),notes

def validate_reblock(merged,reblock):
    """FITV2-001/010: production needs exactly one block-2048 and one block-8192 input, distinct from the block-4096 input,
    with a uniform block size in both summaries, c3 entries identical to their full-window counterparts, and the same
    (s, N, beta) groups as the block-4096 input in both windows."""
    notes=[];byblock={}
    base={w:group_set(merged/f) for w,f in WINDOWS.items()}
    b0,n0=window_consistency(merged);notes+=n0
    if b0 is not None and b0!=4096:notes.append(f'block-4096 input has block size {b0}')
    for d in reblock:
        if not all((d/f).exists() for f in WINDOWS.values()):notes.append(f'{d}: missing summary files');continue
        b,nb=window_consistency(d)
        if nb:notes+=nb;continue
        if b not in REBLOCK_BLOCKS:notes.append(f'{d}: block size {b} not in {REBLOCK_BLOCKS}');continue
        if b in byblock:notes.append(f'{d}: duplicate block size {b}');continue
        if d.resolve()==merged.resolve():notes.append(f'{d}: same directory as the block-4096 input');continue
        for w,f in WINDOWS.items():
            if group_set(d/f)!=base[w]:notes.append(f'{d}: {f} does not cover the same (s,N,beta) groups as the block-4096 input');break
        else:byblock[b]=d
    missing=[b for b in REBLOCK_BLOCKS if b not in byblock]
    if missing:notes.append(f'reblocking inputs missing for block sizes {missing}')
    return (not notes),notes,byblock

def provenance(out,merged,reblock,argv):
    """Hash every consumed file (FITV2-004): summaries, every distinct block archive they reference, plan, implementation."""
    here=Path(__file__).resolve().parent;rec=dict(invocation=' '.join(argv),cwd=os.getcwd(),host=platform.node(),
        platform=platform.platform(),python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,
        implementation={},inputs={},block_archives={})
    for f in IMPLEMENTATION_FILES:
        if (here/f).exists():rec['implementation'][f]=sha256(here/f)
    for d in [merged]+list(reblock):
        for w in WINDOWS.values():
            p=d/w
            if not p.exists():continue
            rec['inputs'][str(p.resolve())]=sha256(p)
            for e in json.loads(p.read_text())['entries']:
                bp=(p.parent/e['blocks_file']).resolve()
                if str(bp) not in rec['block_archives']:rec['block_archives'][str(bp)]=sha256(bp) if bp.exists() else 'MISSING'
    missing=[k for k,v in rec['block_archives'].items() if v=='MISSING']
    if missing:raise SystemExit(f'{len(missing)} referenced block archives are missing, e.g. {missing[0]}')
    with (out/'MANIFEST.txt').open('a') as m:
        m.write(f"{time.strftime('%F_%T')} {rec['invocation']}\n{rec['platform']} python {rec['python']} numpy {rec['numpy']} scipy {rec['scipy']} host {rec['host']}\n")
        for k,v in rec['implementation'].items():m.write(f'{v}  {k}\n')
        for k,v in rec['inputs'].items():m.write(f'{v}  {k}\n')
        m.write(f"{len(rec['block_archives'])} block archives hashed (list in fit_v2.json provenance)\n")
    return rec

# ---------------------------------------------------------------- main protocol
def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--merged',type=Path,required=True,help='merged_b4096 directory with summary.json and summary_c3.json')
    p.add_argument('--reblock',type=Path,nargs='*',default=[],help='merged_b2048 and merged_b8192 directories (both required for production)')
    p.add_argument('--out',type=Path,required=True);p.add_argument('--s',type=float,nargs='*')
    p.add_argument('--bootstrap',type=int,default=PROTOCOL_BOOTSTRAP);p.add_argument('--schedule',type=int,default=20260916)
    p.add_argument('--calibration',type=int,default=PROTOCOL_CALIBRATION);p.add_argument('--workers',type=int)
    p.add_argument('--skip-calibration',action='store_true',help='development only: marks the run NON-PRODUCTION')
    p.add_argument('--analysis-manifest',type=Path,help='run_point_v2.sh manifest of the analysis snapshot (hashed into the provenance)')
    a=p.parse_args()
    t0=time.time();a.out.mkdir(parents=True,exist_ok=True);fitdir=a.out/'fits';fitdir.mkdir(exist_ok=True)
    workers=a.workers or (len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else os.cpu_count())
    prov=provenance(a.out,a.merged,a.reblock,sys.argv)
    if a.analysis_manifest:
        prov['analysis_manifest']=dict(path=str(a.analysis_manifest.resolve()),sha256=sha256(a.analysis_manifest))
        with (a.out/'MANIFEST.txt').open('a') as m:m.write(f"{prov['analysis_manifest']['sha256']}  {prov['analysis_manifest']['path']} (analysis snapshot manifest)\n")
    reblock_ok,reblock_notes,reblock_dirs=validate_reblock(a.merged,a.reblock)
    nonprod=[]
    if a.skip_calibration:nonprod.append('calibration skipped')
    if a.bootstrap!=PROTOCOL_BOOTSTRAP:nonprod.append(f'bootstrap {a.bootstrap} != {PROTOCOL_BOOTSTRAP}')
    if a.calibration!=PROTOCOL_CALIBRATION:nonprod.append(f'calibration {a.calibration} != {PROTOCOL_CALIBRATION}')
    if not reblock_ok:nonprod.append('reblocking inputs invalid: '+'; '.join(reblock_notes))
    production=not nonprod
    svals=a.s or sorted({e['s'] for e in json.loads((a.merged/'summary.json').read_text())['entries']})
    report={'protocol':'FIT_PLAN.md v2','production':production,'non_production_reasons':nonprod,'schedule':a.schedule,
            'bootstrap':a.bootstrap,'calibration':a.calibration,'reblock_inputs':{str(b):str(d) for b,d in reblock_dirs.items()},
            'reblock_notes':reblock_notes,'provenance':prov,'points':{},'errors':[]}
    print(f"production={production} {nonprod}",flush=True)
    pool=Pool(workers)
    try:
        for s in svals:
            try:run_point(a,s,pool,fitdir,report,reblock_dirs,production,t0)
            except Exception as ex:      # keep the outputs of the other points and the manifest (FITV2-008)
                report['errors'].append(dict(s=s,error=f'{type(ex).__name__}: {ex}',traceback=traceback.format_exc()))
                print(f'  point s={s} FAILED: {type(ex).__name__}: {ex}',flush=True)
    finally:
        pool.close();pool.join()
        (a.out/'fit_v2.json').write_text(json.dumps(report,indent=1,default=float)+'\n')
        try:write_report(report,a.out/'FIT_V2_RESULTS.md')
        except Exception as ex:report['errors'].append(dict(error=f'report: {type(ex).__name__}: {ex}'));(a.out/'fit_v2.json').write_text(json.dumps(report,indent=1,default=float)+'\n')
        with (a.out/'MANIFEST.txt').open('a') as m:
            for f in sorted(a.out.glob('xcheck_*'))+[a.out/'fit_v2.json']:
                if f.exists():m.write(f'{sha256(f)}  {f}\n')
            m.write(f"{time.strftime('%F_%T')} done in {time.time()-t0:.0f}s; errors {len(report['errors'])}\n")
    print(a.out/'FIT_V2_RESULTS.md')
    if report['errors']:sys.exit(1)

def run_point(a,s,pool,fitdir,report,reblock_dirs,production,t0):
    ds,dsl=ds_of(s);P={'Delta_sigma':ds,'s':s};print(f'=== s={s} (Delta_sigma={dsl}) ===',flush=True)
    # equilibration prerequisite (FITV2-013): the same gate as accept.py criterion 2, on this point's block-4096 full summary
    eq=equilibration_check([e for e in json.loads((a.merged/'summary.json').read_text())['entries'] if abs(e['s']-s)<1e-12])
    P['equilibration']=eq;print(f"  equilibration: {'PASS' if eq['passed'] else 'FAIL'} ({eq['groups']} groups, {eq['replicas']} replicas, {len(eq['failing'])} failing)",flush=True)
    # ---- stage A: the family, central fits only
    jobs=[dict(summary=str(a.merged/WINDOWS[w]),s=s,ds=dsl,window=w,variant=v,Nmin=n,K=K,degree=d)
          for w,v,n,K,d in itertools.product(WINDOWS,VARIANTS,NMINS,FIELD_ORDERS,DEGREES)]
    fits={}
    for job,r in pool.imap_unordered(w_central,jobs):
        fits[key_of(job)]=r;(fitdir/(key_of(job)+'.json')).write_text(json.dumps(r,indent=1)+'\n')
    print(f'  family: {len(jobs)} fits, {sum(1 for r in fits.values() if "error" in r)} failed to build, {time.time()-t0:.0f}s',flush=True)
    # ---- stage B: F-test ladder per configuration, comparator
    configs=[dict(summary=str(a.merged/WINDOWS[w]),s=s,ds=dsl,window=w,variant=v,Nmin=n,K=K) for w,v,n,K in itertools.product(WINDOWS,VARIANTS,NMINS,FIELD_ORDERS)]
    selection={};comp_jobs=[]
    for ci,c in enumerate(configs):
        get=lambda d:fits.get(key_of({**c,'degree':d}))
        dstar=DEGREES[0];steps=[]
        for d in DEGREES[:-1]:
            lo,hi=get(d),get(d+1)
            if lo is None or hi is None or 'error' in lo or 'error' in hi or hi['flags'] or lo['flags'] or hi['dof']<=0:
                steps.append(dict(from_degree=d,to_degree=d+1,p=None,note='fit missing or flagged: ladder stops'));break
            q=hi['nlinear']-lo['nlinear'];F=((lo['chi2']-hi['chi2'])/q)/(hi['chi2']/hi['dof']) if hi['chi2']>0 else np.inf
            pv=float(f_dist.sf(F,q,hi['dof'])) if np.isfinite(F) else 0.
            steps.append(dict(from_degree=d,to_degree=d+1,F=float(F),p=pv,significant=bool(pv<LADDER_P)))
            if pv<LADDER_P:dstar=d+1
            else:break
        selection[cfg_of(c)]=dict(config=c,config_index=ci,d_star=dstar,ladder=steps)
        if dstar==DEGREES[-1]:comp_jobs.append({**c,'degree':DEGREES[-1]+1})
    for job,r in pool.imap_unordered(w_central,comp_jobs):
        r['comparator_only']=True;fits[key_of(job)]=r;(fitdir/(key_of(job)+'.json')).write_text(json.dumps(r,indent=1)+'\n')
    # ---- stage C: cheap gates at d*, bootstrap for candidates
    boot_jobs=[]
    for cfg,sel in selection.items():
        c=sel['config'];r=fits.get(key_of({**c,'degree':sel['d_star']}));reasons=[]
        if r is None or 'error' in r:reasons.append('fit at d* missing')
        else:
            if r['chi2']/r['dof']>CHI2_DOF_MAX:reasons.append(f"chi2/dof {r['chi2']/r['dof']:.2f} > {CHI2_DOF_MAX}")
            if r['flags']:reasons.append('flags: '+'; '.join(r['flags']))
            bad=[q for q,v in r['mean_abs_pull'].items() if v>PULL_MAX]
            if bad:reasons.append(f'mean |pull| > {PULL_MAX} for {bad}')
        sel['cheap_gate_failures']=reasons
        if not reasons:boot_jobs.append({**c,'degree':sel['d_star'],'bootstrap':a.bootstrap,'schedule':a.schedule})
    print(f'  ladder done; {len(boot_jobs)} candidates pass the cheap gates; bootstrapping ({time.time()-t0:.0f}s)',flush=True)
    for job,r in pool.imap_unordered(w_bootstrap,boot_jobs):
        fits[key_of(job)]=r;(fitdir/(key_of(job)+'.json')).write_text(json.dumps(r,indent=1)+'\n')
    # ---- stage D: bootstrap validity + order stability
    need_valid=int(np.ceil(BOOT_VALID_FRAC*a.bootstrap));calib_candidates=[]
    for cfg,sel in selection.items():
        if sel['cheap_gate_failures']:sel['quotable']=False;sel['reasons']=sel['cheap_gate_failures'];continue
        c=sel['config'];r=fits[key_of({**c,'degree':sel['d_star']})];reasons=[]
        if 'error' in r or 'bootstrap' not in r:
            sel['quotable']=False;sel['reasons']=['bootstrap failed: '+r.get('error','no bootstrap')];continue
        b=r['bootstrap'];sel['bootstrap_valid']=b['valid']
        if b['valid']<need_valid:reasons.append(f"bootstrap valid {b['valid']} < {need_valid}")
        sigma=(b['percentile_16_50_84'][2]-b['percentile_16_50_84'][0])/2 if b['percentile_16_50_84'] else None
        sel['sigma_stat']=sigma;comp=fits.get(key_of({**c,'degree':sel['d_star']+1}))
        if comp is None or 'error' in comp or comp['flags'] or not comp['success']:reasons.append('stability-unresolved: comparator missing, non-converged or flagged')
        elif sigma is None or abs(comp['Delta_epsilon']-r['Delta_epsilon'])>STABILITY_SIGMAS*sigma:
            reasons.append(f"order-unstable: |dDelta_eps(d*,d*+1)| = {abs(comp['Delta_epsilon']-r['Delta_epsilon']):.5f} > {STABILITY_SIGMAS} sigma_stat")
        sel['comparator_Delta_epsilon']=None if comp is None or 'error' in comp else comp['Delta_epsilon']
        sel['reasons']=reasons
        if not reasons:calib_candidates.append(cfg)
    # ---- stage E: calibrated residual-structure gate (full refits)
    if a.skip_calibration:
        for cfg in calib_candidates:selection[cfg]['residual_gate']=dict(evaluated=False,decision='SKIPPED (non-production)');selection[cfg]['quotable']=True
    else:
        cjobs=[];chunk=25
        for cfg in calib_candidates:
            sel=selection[cfg];c=sel['config'];r=fits[key_of({**c,'degree':sel['d_star']})]
            T,R,per=residual_stats(r['pulls']);sel['residual_gate']=dict(T_observed=T,R_observed=R,per_observable=per,seed_entropy=[])
            for i in range(0,a.calibration,chunk):
                seed=calibration_seed(a.schedule,s,sel['config_index'],i//chunk);sel['residual_gate']['seed_entropy'].append(seed)
                cjobs.append({**c,'degree':sel['d_star'],'key':cfg,'parameters':r['parameters'],'predictions':r['predictions'],'seed':seed,'n':min(chunk,a.calibration-i)})
        print(f'  residual-gate calibration: {len(calib_candidates)} candidates x {a.calibration} refits ({time.time()-t0:.0f}s)',flush=True)
        null=defaultdict(list)
        for key,out in pool.imap_unordered(w_calibration,cjobs):null[key].extend(out)
        for cfg in calib_candidates:
            sel=selection[cfg];g=sel['residual_gate'];arr=np.array(null[cfg],float);ok=arr[:,2]>0.5
            g['null_replicates']=int(len(arr));g['null_nonconverged']=int((~ok).sum())
            if (~ok).mean()>CALIB_FAIL_MAX:
                g['evaluated']=False;g['decision']='not evaluable (> 2 % of null refits failed)';sel['reasons'].append('residual gate not evaluable')
            else:
                g['T_q01']=float(np.quantile(arr[ok,0],0.01));g['R_q99']=float(np.quantile(arr[ok,1],0.99));g['evaluated']=True
                rej=g['T_observed']<g['T_q01'] or g['R_observed']>g['R_q99'];g['decision']='structured residuals' if rej else 'pass'
                if rej:sel['reasons'].append(f"structured residuals (T={g['T_observed']:.3g} vs q01={g['T_q01']:.3g}; R={g['R_observed']:.3f} vs q99={g['R_q99']:.3f})")
            sel['quotable']=not sel['reasons']
    for cfg,sel in selection.items():sel.setdefault('quotable',False)
    # ---- stage F: quotable set, quoted value, sigma_sys
    quotable=[]
    for cfg,sel in selection.items():
        if sel['quotable']:
            c=sel['config'];r=fits[key_of({**c,'degree':sel['d_star']})]
            quotable.append(dict(config=cfg,degree=sel['d_star'],Nmin=c['Nmin'],window=c['window'],variant=c['variant'],K=c['K'],
                Delta_epsilon=r['Delta_epsilon'],sigma_stat=sel['sigma_stat'],chi2=r['chi2'],dof=r['dof'],
                nparams=r['nlinear']+r['nonlinear_parameters'],key=key_of({**c,'degree':sel['d_star']})))
    P['selection']=selection;P['quotable']=quotable
    if not quotable:
        near=sorted([dict(config=cfg,d_star=sel['d_star'],reasons=sel['reasons'],
                Delta_epsilon=fits.get(key_of({**sel['config'],'degree':sel['d_star']}),{}).get('Delta_epsilon'),
                chi2_dof=(lambda r:r['chi2']/r['dof'] if r and 'chi2' in r else None)(fits.get(key_of({**sel['config'],'degree':sel['d_star']}))))
                for cfg,sel in selection.items()],key=lambda d:(d['chi2_dof'] is None,d['chi2_dof'] or 0))
        P['near_admissible']=near[:12];P['decision']=('' if production else 'NON-PRODUCTION; ')+('EQUILIBRATION FAILED; ' if not eq['passed'] else '')+'MODEL-LIMITED (no quotable fit)';report['points'][dsl]=P
        print(f'  no quotable fit; decision {P["decision"]}',flush=True);return
    nmin=min(q['Nmin'] for q in quotable)
    quoted=min([q for q in quotable if q['Nmin']==nmin],key=lambda q:(q['nparams'],WINDOW_RANK[q['window']],VARIANT_RANK[q['variant']],q['K']))
    P['quoted']=quoted;vals=[q['Delta_epsilon'] for q in quotable]
    cov_ok=len(quotable)>=SYS_MIN_FITS and len({q['Nmin'] for q in quotable})>=SYS_MIN_NMIN and len({q['variant'] for q in quotable})>=SYS_MIN_VARIANTS
    sig_sys=(max(vals)-min(vals))/2 if cov_ok else None;cap=sys_cap(ds)
    P['sigma_sys']=dict(value=sig_sys,coverage_ok=cov_ok,n_quotable=len(quotable),range=[min(vals),max(vals)],cap=cap,
                        within_cap=(None if sig_sys is None or cap is None else bool(sig_sys<=cap)))
    # ---- stage G: cross-check series and paired comparison; everything persisted (FITV2-005)
    qjobs=[dict(summary=str(a.merged/WINDOWS[w]),s=s,degree=d,window=w,bootstrap=a.bootstrap,schedule=a.schedule) for d in XCHECK_DEGREES for w in WINDOWS]
    series={};npz={}
    for job,qr,smp in pool.imap_unordered(w_quotients,qjobs):
        name=f"deg{job['degree']}_{job['window']}";series[name]=crosscheck_series(qr,smp);series[name]['warnings']=qr['warnings']
        series[name]['rows']=[dict(N=r['N'],N2=r['N2'],crossing_observable=r['crossing_observable']) for r in qr['crossings']]
        (a.out/f'quot_{name}_ds{dsl}.json').write_text(json.dumps(qr,indent=1)+'\n');npz[name]=np.asarray(smp)
    E=[n for n,sr in series.items() if sr.get('eligible')]
    qfit=fits[quoted['key']];X=paired_comparison(series,E,qfit['bootstrap']['draws'],a.bootstrap,quoted['Delta_epsilon'])
    X['series']={n:{k:v for k,v in sr.items() if k not in ('per_draw_Delta_inf','draw_valid','draw_converged')} for n,sr in series.items()}
    np.savez_compressed(a.out/f'xcheck_ds{dsl}.samples.npz',**npz)
    (a.out/f'xcheck_ds{dsl}.json').write_text(json.dumps(dict(schedule=a.schedule,bootstrap=a.bootstrap,quoted_fit=quoted['key'],eligible=E,
        samples_file=f'xcheck_ds{dsl}.samples.npz',samples_layout='per series: (draw, crossing row, [beta_crossing, Delta_eff_Y, Delta_eff_U]); rows as in series[name].rows; draw index = schedule draw',
        series=series,paired={k:v for k,v in X.items() if k!='series'}),indent=1,default=float)+'\n')
    for k in ('global_valid_mask','common_valid_mask','per_draw_Delta_inf_median','paired_differences'):X.pop(k,None)
    P['crosscheck']=X
    # ---- stage H: reblocking of the quoted configuration (only with validated inputs)
    rb={}
    for b,d in sorted(reblock_dirs.items()):
        job=dict(summary=str(d/WINDOWS[quoted['window']]),s=s,ds=dsl,window=quoted['window'],variant=quoted['variant'],Nmin=quoted['Nmin'],K=quoted['K'],degree=quoted['degree'],bootstrap=a.bootstrap,schedule=a.schedule)
        _,r=w_bootstrap(job)
        if 'error' in r:rb[str(b)]=dict(sigma_stat=None,within_tol=False,note='fit failed: '+r['error']);continue
        pc=r['bootstrap']['percentile_16_50_84'];sig=(pc[2]-pc[0])/2 if pc else None;problems=[]
        # FITV2-011: a reblocked interval counts only from a converged, unflagged central fit with enough valid draws
        if not r['success'] or r['flags']:problems.append('central fit not converged/unflagged: '+'; '.join(r['flags']))
        if r['bootstrap']['valid']<need_valid:problems.append(f"bootstrap valid {r['bootstrap']['valid']} < {need_valid}")
        if sig is None:problems.append('no valid bootstrap draws')
        rb[str(b)]=dict(Delta_epsilon=r['Delta_epsilon'],sigma_stat=sig,chi2=r['chi2'],dof=r['dof'],valid=r['bootstrap']['valid'],
                        within_tol=(False if problems or not quoted['sigma_stat'] else bool(abs(sig-quoted['sigma_stat'])<=REBLOCK_TOL*quoted['sigma_stat'])),
                        note='; '.join(problems) or None)
        (fitdir/f"reblock_b{b}_{quoted['key']}.json").write_text(json.dumps(r,indent=1)+'\n')
    P['reblocking']=rb;rb_ok=len(rb)==len(REBLOCK_BLOCKS) and all(v['within_tol'] for v in rb.values())
    # ---- decision
    if not eq['passed']:dec='EQUILIBRATION FAILED'
    elif not cov_ok:dec='CONDITIONAL (sigma_sys unresolved: coverage absent)'
    elif not P['sigma_sys']['within_cap']:dec='MODEL-LIMITED (sigma_sys above cap)'
    elif X['status']!='pass':dec=X['status']
    elif len(rb)<len(REBLOCK_BLOCKS):dec='REBLOCKING UNAVAILABLE'
    elif not rb_ok:dec='REBLOCKING FAILED'
    else:dec='ACCEPTED'
    P['decision']=dec if production else f'NON-PRODUCTION ({"; ".join(report["non_production_reasons"])}); would be: {dec}'
    report['points'][dsl]=P
    print(f"  quoted {quoted['config']} deg{quoted['degree']}: Delta_eps = {quoted['Delta_epsilon']:.5f} +- {f5(quoted['sigma_stat'])} (stat) "
          f"sigma_sys={f5(sig_sys)} n_quotable={len(quotable)} xcheck={X['status']} decision={P['decision']} ({time.time()-t0:.0f}s)",flush=True)

def write_report(rep,path):
    L=[f"# FIT v2 results ({'production' if rep['production'] else 'NON-PRODUCTION: '+'; '.join(rep['non_production_reasons'])}; schedule seed {rep['schedule']}, bootstrap {rep['bootstrap']}, calibration {rep['calibration']})",'',
       'Protocol: FIT_PLAN.md (rules fixed before these fits ran). Selection is blind to Delta_epsilon.','']
    if rep.get('errors'):L+=['**Errors:** '+'; '.join(e['error'] for e in rep['errors']),'']
    for ds,P in rep['points'].items():
        L+=[f"## Delta_sigma = {ds} (s = {P['s']})",'',f"**Decision: {P['decision']}**",'']
        if 'quoted' in P:
            q=P['quoted'];ss=P['sigma_sys']
            L+=[f"Quoted: Delta_epsilon = {q['Delta_epsilon']:.5f} ± {f5(q['sigma_stat'])} (stat)"+(f" ± {ss['value']:.5f} (sys)" if ss['value'] is not None else ' (sigma_sys unresolved)'),
                f"from {q['config']} degree {q['degree']} (chi2/dof = {q['chi2']:.1f}/{q['dof']}); quotable fits: {ss['n_quotable']}, range [{ss['range'][0]:.5f}, {ss['range'][1]:.5f}], cap {ss['cap']}",'']
        L+=['| configuration | d* | ladder p (3→4, 4→5, 5→6, 6→7) | chi2/dof at d* | Delta_eps at d* | sigma_stat | comparator | quotable | reasons |','|---|---|---|---|---|---|---|---|---|']
        for cfg,sel in P['selection'].items():
            ps=' '.join('—' if st.get('p') is None else f"{st['p']:.2g}" for st in sel['ladder'])
            fitkey=f"ds{ds}_{cfg}_deg{sel['d_star']}";r=None
            try:r=json.load(open(Path(path).parent/'fits'/(fitkey+'.json')))
            except Exception:pass
            c2=f"{r['chi2']/r['dof']:.2f}" if r and 'chi2' in r and r['dof'] else '—';de=f5(r.get('Delta_epsilon') if r else None)
            L.append(f"| {cfg} | {sel['d_star']} | {ps} | {c2} | {de} | {f5(sel.get('sigma_stat'))} | {f5(sel.get('comparator_Delta_epsilon'))} | {'yes' if sel['quotable'] else 'no'} | {'; '.join(sel.get('reasons',[]))[:160]} |")
        L.append('')
        if 'crosscheck' in P:
            X=P['crosscheck'];L+=[f"Cross-check: {X['status']}; eligible series {X['eligible']}"]
            for n,sr in X['series'].items():
                c=sr.get('central') or {}
                L.append(f"- {n}: "+(f"Delta_inf = {c['Delta_inf']:.5f}, omega' = {c['omega']:.2f}, chi2/dof = {c['chi2']:.2f}/{c['dof']}, sigma = {f5(sr.get('sigma_Delta_inf'))}" if 'Delta_inf' in c else '')+(f" — {sr['reason']}" if not sr.get('eligible') else ' — eligible'))
            if 'Delta_inf_central' in X:L.append(f"Delta_inf (median over E) = {X['Delta_inf_central']:.5f}, model spread {X['model_spread']:.5f}, common-valid draws {X['common_valid_draws']}"+(f", paired difference {X['paired_difference_central']:+.5f} vs 2 sigma_D = {2*X['sigma_D']:.5f}" if 'sigma_D' in X else ''))
            L.append('')
        if 'reblocking' in P:
            L.append('Reblocking of the quoted configuration: '+('; '.join(f"block {k}: sigma_stat {f5(v['sigma_stat'])} ({'ok' if v['within_tol'] else 'FAIL'}{'; '+v['note'] if v.get('note') else ''})" for k,v in P['reblocking'].items()) or 'UNAVAILABLE (no validated reblocking inputs)'));L.append('')
        if 'near_admissible' in P:
            L.append('Nearest non-quotable configurations:');L+=[f"- {n['config']} d*={n['d_star']}: Delta_eps {f5(n['Delta_epsilon'])}, chi2/dof {f5(n['chi2_dof'],'%.2f')}: {'; '.join(n['reasons'])}" for n in P['near_admissible']];L.append('')
    Path(path).write_text('\n'.join(L)+'\n')

if __name__=='__main__':main()
