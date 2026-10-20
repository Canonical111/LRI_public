#!/usr/bin/env python3
"""Assemble C0--C8(2) from complete independent finite-scheme RG-jet campaigns.

The power correction is measured, not zeroed. Whole randomized replicates are
statistical units; graph chunks are merged first. No lower coefficient is fitted.
load_campaign() reads and verifies a campaign; combine() is the pure assembly.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
from common import ROOT,canon,digest,dump,load
B2=np.asarray(load(ROOT/'inputs/two_loop.json')['B2'],float)
RESULT_SCHEMA='c8-d2-hpc-result-2'
# Lower-order references (D9). C3-C5: the archived 13-digit values of the exact results
# (reference/power_mass/code/assemble_full.py; longer evaluations differ by up to 1.8e-12, at C5), reference SE 0.
# C6: the C6(2) production M=8192 (LRI_C6_D2_HPC, 2026-09-28), with the archived Monte Carlo value as a secondary entry.
ARCHIVED='archived 13-digit value of the exact result (reference/power_mass/code/assemble_full.py)'
REFERENCE_LOWER={3:(-.8748500126526,0.,ARCHIVED),
                 4:(5.048868431355,0.,ARCHIVED),
                 5:(-38.83364589623,0.,ARCHIVED),
                 6:(362.36647176375726,0.0007997306822612242,'C6(2) production, supplied manuscript'),
                 7:(-3876.1260927949925,0.5244496691,'C7(2) production, supplied manuscript section app:C7d2')}
C6_SECONDARY=(362.3489137997967,0.15264446036381157,'archived Monte Carlo estimate in the C7 package, reference/LRI_C7_d2_progress/code/finalize.py')
FLAG_PULL=3.
ROUNDING=1e-12
META=('schema','dimension','order','epsilon','scope','empirical_allowance')

def coefficients(vals):
    dtype=np.result_type(*[np.asarray(v).dtype for v in vals.values()]);N=9
    b={1:np.array([3],dtype=dtype),2:B2.astype(dtype)};c={1:np.array([1],dtype=dtype),2:B2.astype(dtype)/6}
    for L,a in vals.items():
        a=np.asarray(a);k=9-L
        if L not in range(3,9)or a.shape!=(2*k,):raise ValueError('Wrong loop jet shape')
        b[L]=a[:k];c[L]=a[k:]
    def mul(x,y):return np.convolve(x,y)[:N]
    g=np.zeros(N,dtype=dtype);e=g.copy();e[1]=1
    for _ in range(N):
        gp=g.copy();tmp=g.copy()*0
        for L in range(2,N):gp=mul(gp,g);tmp+=mul(b.get(L,np.zeros(1)),gp)
        g=(e-tmp)/3
    ga=np.zeros(N,dtype=dtype);gp=ga.copy();gp[0]=1
    for L in range(1,N):gp=mul(gp,g);ga+=mul(c.get(L,np.zeros(1)),gp)
    ga[0]+=1;ga[1]-=.5;return ga

def jacobians(means):
    out={}
    for L,a in means.items():
        columns=[]
        for j in range(len(a)):
            tmp={k:np.asarray(v,dtype=complex).copy()for k,v in means.items()};tmp[L][j]+=1e-20j;columns.append(coefficients(tmp).imag/1e-20)
        out[L]=np.array(columns).T
    return out

def pull(estimate:float,se:float,reference:float,reference_se:float):
    s=math.sqrt(se*se+reference_se*reference_se);return (estimate-reference)/s if s>0 else None

def lower_order_checks(mu,se)->list:
    """C3--C7 against supplied references, including both sampling standard errors."""
    out=[]
    for k,(ref,rse,src)in REFERENCE_LOWER.items():
        p=pull(float(mu[k]),float(se[k]),ref,rse)
        row={'order':k,'estimate':float(mu[k]),'sampling_se':float(se[k]),'reference':ref,'reference_se':rse,'reference_source':src,'pull':p,'flag':p is not None and abs(p)>FLAG_PULL}
        if k==6:
            q=pull(float(mu[k]),float(se[k]),C6_SECONDARY[0],C6_SECONDARY[1])
            row['secondary']={'reference':C6_SECONDARY[0],'reference_se':C6_SECONDARY[1],'reference_source':C6_SECONDARY[2],'pull':q,'flag':q is not None and abs(q)>FLAG_PULL}
        out.append(row)
    return out

def power_null_checks(delta,dse)->list:
    """power_differences[3..6] are expected to vanish: pull = delta/SE. Order 3 is rounding when |delta| < 1e-12."""
    out=[]
    for k in range(3,7):
        d,s=float(delta[k]),float(dse[k])
        if k==3 and abs(d)<ROUNDING:out.append({'order':k,'delta':d,'se':s,'pull':None,'flag':False,'note':'rounding (|delta| < 1e-12)'});continue
        p=d/s if s>0 else None;out.append({'order':k,'delta':d,'se':s,'pull':p,'flag':p is not None and abs(p)>FLAG_PULL})
    return out

def combine(ar,primitive=None,bootstrap=1024):
    """Pure assembly callable on independent replicate arrays.

    ar[sector][campaign][loop] has columns b Taylor jet followed by c jet.
    Equal campaign weights are precommitted. All primitive graphs are recomputed.
    """
    if set(ar)!={'free','power'}:raise ValueError('Both sectors are required')
    for sector in ar:
        if set(ar[sector])!={'a','b'}:raise ValueError('Need two independent campaigns')
        for vals in ar[sector].values():
            if set(vals)!=set(range(3,9)):raise ValueError('Need all loops 3--8')
            for L,x in vals.items():
                if x.ndim!=2 or x.shape[1]!=2*(9-L) or len(x)<4 or len(x)%2 or not np.isfinite(x).all():raise ValueError('Invalid complete replicate data')
    means={s:{L:sum(x[L].mean(0)for x in ar[s].values())/2 for L in range(3,9)}for s in ar}
    vc={s:{L:sum(np.cov(x[L],rowvar=False,ddof=1)/len(x[L])for x in ar[s].values())/4 for L in range(3,9)}for s in ar}
    m={L:means['free'][L]+means['power'][L]for L in range(3,9)}
    J=jacobians(m);Jf=jacobians(means['free']);mu=coefficients(m);pf=coefficients(means['free']);delta=mu-pf
    contributions={s:{L:J[L]@vc[s][L]@J[L].T for L in m}for s in ar}
    cov=sum(sum(v.values())for v in contributions.values())
    df={L:J[L]-Jf[L]for L in m}
    dcov=sum(df[L]@vc['free'][L]@df[L].T+contributions['power'][L]for L in m)
    cross=sum(Jf[L]@vc['free'][L]@df[L].T for L in m)
    pcov=sum(Jf[L]@vc['free'][L]@Jf[L].T for L in m)
    offset=0.;shared=0.
    if primitive:raise ValueError('No retained primitive offset is valid for C8')
    if not np.allclose(cov,pcov+dcov+cross+cross.T,rtol=1e-10,atol=1e-8):raise ArithmeticError('Covariance decomposition failed')
    se=np.sqrt(np.maximum(0,np.diag(cov)));dse=np.sqrt(np.maximum(0,np.diag(dcov)))
    campaigns={}
    for tag in ('a','b'):
        mm={L:ar['free'][tag][L].mean(0)+ar['power'][tag][L].mean(0)for L in m};jj=jacobians(mm);cc=coefficients(mm);cc[8]+=offset
        cv=sum(jj[L]@(np.cov(ar['free'][tag][L],rowvar=False)/len(ar['free'][tag][L])+np.cov(ar['power'][tag][L],rowvar=False)/len(ar['power'][tag][L]))@jj[L].T for L in m);cv[8,8]+=shared**2
        campaigns[tag]=dict(C8=float(cc[8]),sampling_se=float(max(0,cv[8,8])**.5))
    halves=[]
    for h in (0,1):
        mm={L:sum(ar[s][t][L][h*len(ar[s][t][L])//2:(h+1)*len(ar[s][t][L])//2].mean(0)for s in ar for t in ('a','b'))/2 for L in m};cc=coefficients(mm);cc[8]+=offset;halves.append(cc.tolist())
    boot=None
    if bootstrap:
        rng=np.random.default_rng(70530413);xs=[];dx=[]
        for _ in range(bootstrap):
            mm={s:{L:sum(ar[s][t][L][rng.integers(len(ar[s][t][L]),size=len(ar[s][t][L]))].mean(0)for t in ('a','b'))/2 for L in m}for s in ar}
            f=coefficients({L:mm['free'][L]+mm['power'][L]for L in m});fp=coefficients(mm['free']);dx.append(f-fp);f[8]+=offset+(rng.normal()*shared if shared else 0);xs.append(f)
        xx=np.array(xs);dd=np.array(dx);boot=dict(replicates=bootstrap,seed=70530413,full_se=xx.std(0,ddof=1).tolist(),correction_se=dd.std(0,ddof=1).tolist(),bias=(xx.mean(0)-mu).tolist(),diagnostic_only=True)
    return dict(schema=RESULT_SCHEMA,dimension=2,order=8,epsilon='2s-2',C8_full=float(mu[8]),sampling_standard_error=float(se[8]),coefficients=mu.tolist(),standard_errors=se.tolist(),covariance=cov.tolist(),power_free_C8=float(pf[8]),power_free_se=float(max(0,pcov[8,8])**.5),power_correction=float(delta[8]),power_correction_se=float(dse[8]),power_free_correction_covariance=float(cross[8,8]),power_differences=delta.tolist(),power_difference_errors=dse.tolist(),means={s:{str(L):v.tolist()for L,v in means[s].items()}for s in ar},error_by_loop={str(L):{s:float(max(0,contributions[s][L][8,8])**.5)for s in ar}for L in m},shared_primitive=primitive,shared_reference_se=shared,campaigns=campaigns,half_streams=halves,bootstrap=boot,
                lower_order_checks=lower_order_checks(mu,se),power_null_checks=power_null_checks(delta,dse),empirical_allowance=None,
                scope='Sampling precision only. The C8 extension uses the supplied finite scheme, without an independent field-theoretic derivation or an interval enclosure. New production explicitly integrates both sectors; prior complete coefficient not an input; no lower physical coefficient imposed as a constraint. Lower-order pulls are diagnostics, not gates.')
calculate=combine  # name used by tools/reassemble_reference.py

def load_campaign(directory:Path,accept_tool_change=False):
    from production import group_of,validate_merged,verify_base
    m,_,mh,changes=verify_base(directory,check_executable=False,accept_tool_change=accept_tool_change)
    if m['campaign_weights']!={'a':.5,'b':.5}:raise ValueError('Changed campaign weights')
    ar={s:{t:{}for t in ('a','b')}for s in ('free','power')};hashes={};seen=set()
    for gr in m['groups']:
        p,cfg=group_of(directory,m,gr['name']);d=validate_merged(p,cfg,m,mh);key=(cfg['sector'],cfg['campaign'],cfg['L'])
        if key in seen:raise ValueError('Duplicate group')
        seen.add(key);x=np.asarray(d['batches'],float)
        if x.shape!=(cfg['replicates'],2*(9-cfg['L'])):raise ValueError('Wrong data shape')
        ar[key[0]][key[1]][key[2]]=x;hashes[gr['name']]=digest(p/'merged.json')
    return m,mh,ar,hashes,changes

def evaluate(directory,bootstrap=1024,accept_tool_change=False):
    m,mh,ar,hashes,changes=load_campaign(directory,accept_tool_change)
    primitive=None
    if m['primitive_mode']!='recompute':raise ValueError('C8 requires all primitive jets to be recomputed')
    r=combine(ar,primitive,bootstrap)
    if m['test_only']:
        # A-L19: an incomplete-graph workflow test; every physical-looking field moves under test_partial.
        part={k:r.pop(k)for k in list(r)if k not in META};r.update({k:None for k in part});r['test_partial']=part
        r['scope']='INCOMPLETE workflow test (--test-graphs). Not a physical coefficient; graphs are excluded. Partial values only under test_partial.'
    r.update(source_manifest_sha256=mh,merged_sha256=hashes,primitive_mode=m['primitive_mode'],backend=m['backend'],build=m['build'],test_only=m['test_only'],allocation=m.get('allocation'),purpose=m.get('purpose','pilot'))
    r['numerical_status']='incomplete workflow test' if r['test_only'] else ('complete-coverage pilot; convergence not established' if r['purpose']=='pilot' else 'complete-coverage numerical campaign; inspect convergence diagnostics before reporting')
    if changes:r['accepted_tool_changes']=changes
    return r

def default_output(directory:Path,result:dict)->Path:return directory/('C8_test_result.json'if result['test_only']else'C8_result.json')

def publish_result(dest:Path,result:dict)->str:
    """No-clobber, idempotent: an existing identical result is kept; a different one is an error."""
    if dest.exists():
        if canon(load(dest))!=canon(json.loads(json.dumps(result,allow_nan=False))):raise ValueError(f'{dest} exists and differs from the recomputed result; not overwritten')
        return 'identical result already present; kept'
    try:dump(dest,result);return 'written'
    except FileExistsError:return publish_result(dest,result)

def summary_lines(r:dict)->list[str]:
    """Human-readable lower-order diagnostics (D9); FLAG marks |pull| > 3 (a diagnostic, not a hard gate)."""
    src=r.get('test_partial')or r;out=[]
    for c in src.get('lower_order_checks')or[]:
        f=lambda p:'n/a'if p is None else f'{p:+.2f}'
        line=f"C{c['order']}: {c['estimate']:.12g} +/- {c['sampling_se']:.3g} vs {c['reference']:.12g} +/- {c['reference_se']:.3g}  pull {f(c['pull'])}"
        if 'secondary'in c:line+=f"  (secondary {c['secondary']['reference']:.10g} +/- {c['secondary']['reference_se']:.3g}: pull {f(c['secondary']['pull'])})"
        out.append(('FLAG |pull|>3 (diagnostic) 'if c['flag']else'')+line)
    for c in src.get('power_null_checks')or[]:
        tail=c.get('note')or('pull n/a'if c['pull']is None else f"pull {c['pull']:+.2f}")
        line=f"power_differences[{c['order']}]: {c['delta']:.3g} +/- {c['se']:.3g}  {tail}"
        out.append(('FLAG |pull|>3 (diagnostic) 'if c['flag']else'')+line)
    if r.get('test_only'):out=['(test-only partial values)']+out
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--bootstrap',type=int,default=1024);p.add_argument('--output',type=Path)
    p.add_argument('--accept-tool-change',action='store_true',help='assemble although a pinned tool changed; old and new hashes are recorded in the result');a=p.parse_args()
    if a.bootstrap<0 or a.bootstrap==1:raise ValueError('bootstrap must be zero or >=2')
    r=evaluate(a.directory.resolve(),a.bootstrap,a.accept_tool_change);dest=a.output or default_output(a.directory,r);state=publish_result(dest,r)
    print(json.dumps({'C8_full':r['C8_full'],'sampling_standard_error':r['sampling_standard_error'],'primitive_mode':r['primitive_mode'],'test_only':r['test_only'],'output':str(dest),'state':state}))
    for line in summary_lines(r):print(line)
if __name__=='__main__':main()
