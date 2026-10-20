#!/usr/bin/env python3
"""Assemble C0--C7(3) from complete independent finite-scheme RG-jet campaigns.

The power correction is measured, not zeroed. Whole randomized replicates are statistical units; graph chunks are
merged first. No lower coefficient is fitted or imposed. The only assembly inputs (two-loop B2 and, in retained mode,
the shared primitive reference) are used only after their checksums match the inputs manifest frozen by the campaign
plan (verified_inputs). Lower-order references are consistency gates only (references/lower_order_d3.json).
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from pathlib import Path
import numpy as np
from common import ROOT,canon,digest,dump,load
REFERENCES=ROOT/'references/lower_order_d3.json'
_PACKAGE_INPUTS=None

def verified_inputs(expected_inputs_manifest_sha256:str|None)->dict:
    """B2 and the primitive reference, parsed from exactly the bytes verified against inputs/manifest.json, which is
    itself verified against the campaign's recorded hash (None: the package's own manifest, archive tests only)."""
    data=(ROOT/'inputs/manifest.json').read_bytes();msha=hashlib.sha256(data).hexdigest()
    if expected_inputs_manifest_sha256 is not None and msha!=expected_inputs_manifest_sha256:
        raise ValueError('Checksum mismatch: inputs/manifest.json differs from the one the campaign was planned with')
    im=json.loads(data)
    if im.get('schema')!='c7-d3-hpc-inputs-1'or im.get('dimension')!=3:raise ValueError('wrong inputs manifest')
    out={'sha256':{'inputs/manifest.json':msha}}
    for name in ('two_loop.json','primitive_reference.json'):
        raw=(ROOT/'inputs'/name).read_bytes();h=hashlib.sha256(raw).hexdigest()
        if h!=im['sha256'][name]:raise ValueError(f'Checksum mismatch: inputs/{name}')
        out[name]=json.loads(raw);out['sha256'][f'inputs/{name}']=h
    low=out['two_loop.json']
    if low.get('dimension')!=3 or low.get('order')!=7:raise ValueError('Wrong-dimensional two-loop data')
    prim=out['primitive_reference.json']
    if prim.get('dimension')!=3 or prim.get('order')!=7:raise ValueError('Wrong-dimensional primitive reference')
    return {'B2':np.asarray(low['B2'],float),'primitive':prim,'sha256':out['sha256']}

def package_B2():
    global _PACKAGE_INPUTS
    if _PACKAGE_INPUTS is None:_PACKAGE_INPUTS=verified_inputs(None)
    return _PACKAGE_INPUTS['B2']

def coefficients(vals,B2=None):
    B2=package_B2()if B2 is None else B2
    dtype=np.result_type(*[np.asarray(v).dtype for v in vals.values()]);N=8
    b={1:np.array([3],dtype=dtype),2:B2.astype(dtype)};c={1:np.array([1],dtype=dtype),2:B2.astype(dtype)/6}
    for L,a in vals.items():
        a=np.asarray(a);k=8-L
        if L not in range(3,8)or a.shape!=(2*k,):raise ValueError('Wrong loop jet shape')
        b[L]=a[:k];c[L]=a[k:]
    def mul(x,y):return np.convolve(x,y)[:N]
    g=np.zeros(N,dtype=dtype);e=g.copy();e[1]=1
    for _ in range(N):
        gp=g.copy();tmp=g.copy()*0
        for L in range(2,N):gp=mul(gp,g);tmp+=mul(b.get(L,np.zeros(1)),gp)
        g=(e-tmp)/3
    ga=np.zeros(N,dtype=dtype);gp=ga.copy();gp[0]=1
    for L in range(1,N):gp=mul(gp,g);ga+=mul(c.get(L,np.zeros(1)),gp)
    ga[0]+=1.5;ga[1]-=.5;return ga

def jacobians(means,B2=None):
    out={}
    for L,a in means.items():
        columns=[]
        for j in range(len(a)):
            tmp={k:np.asarray(v,dtype=complex).copy()for k,v in means.items()};tmp[L][j]+=1e-20j;columns.append(coefficients(tmp,B2).imag/1e-20)
        out[L]=np.array(columns).T
    return out

def calculate(ar,primitive=None,bootstrap=1024,B2=None):
    """Pure assembly callable on independent replicate arrays.

    ar[sector][campaign][loop] has columns b Taylor jet followed by c jet; loops 3..K with K in 5..7 (K < 7 only for
    prefix plans: coefficients up to order K are complete, higher ones are not reported). Equal campaign weights are
    precommitted. Shared primitive variance (retained mode, K = 7 only) is added once, and cancels out of the
    power-sector difference.
    """
    if set(ar)!={'free','power'}:raise ValueError('Both sectors are required')
    K=None
    for sector in ar:
        if set(ar[sector])!={'a','b'}:raise ValueError('Need two independent campaigns')
        for vals in ar[sector].values():
            k=max(vals,default=0)
            if k not in (5,6,7)or set(vals)!=set(range(3,k+1))or K not in (None,k):raise ValueError('Need loops 3..K (K = 5, 6 or 7) in every sector and campaign')
            K=k
            for L,x in vals.items():
                if x.ndim!=2 or x.shape[1]!=2*(8-L) or len(x)<2 or not np.isfinite(x).all():raise ValueError('Invalid complete replicate data')
    if primitive and K!=7:raise ValueError('the retained primitive reference needs all loops 3..7')
    loops=range(3,K+1)
    means={s:{L:sum(x[L].mean(0)for x in ar[s].values())/2 for L in loops}for s in ar}
    vc={s:{L:sum(np.cov(x[L],rowvar=False,ddof=1)/len(x[L])for x in ar[s].values())/4 for L in loops}for s in ar}
    m={L:means['free'][L]+means['power'][L]for L in loops}
    J=jacobians(m,B2);Jf=jacobians(means['free'],B2);mu=coefficients(m,B2);pf=coefficients(means['free'],B2);delta=mu-pf
    contributions={s:{L:J[L]@vc[s][L]@J[L].T for L in m}for s in ar}
    cov=sum(sum(v.values())for v in contributions.values())
    df={L:J[L]-Jf[L]for L in m}
    dcov=sum(df[L]@vc['free'][L]@df[L].T+contributions['power'][L]for L in m)
    cross=sum(Jf[L]@vc['free'][L]@df[L].T for L in m)
    pcov=sum(Jf[L]@vc['free'][L]@Jf[L].T for L in m)
    offset=0.;shared=0.
    if primitive:
        offset=float(primitive['mean']);shared=float(primitive['sampling_se']);mu[7]+=offset;pf[7]+=offset;cov[7,7]+=shared**2;pcov[7,7]+=shared**2
    if not np.allclose(cov,pcov+dcov+cross+cross.T,rtol=1e-10,atol=1e-8):raise ArithmeticError('Covariance decomposition failed')
    se=np.sqrt(np.maximum(0,np.diag(cov)));dse=np.sqrt(np.maximum(0,np.diag(dcov)));pse=np.sqrt(np.maximum(0,np.diag(pcov)))
    campaigns={}
    for tag in ('a','b'):
        mm={L:ar['free'][tag][L].mean(0)+ar['power'][tag][L].mean(0)for L in m};jj=jacobians(mm,B2);cc=coefficients(mm,B2);cc[7]+=offset
        cv=sum(jj[L]@(np.cov(ar['free'][tag][L],rowvar=False)/len(ar['free'][tag][L])+np.cov(ar['power'][tag][L],rowvar=False)/len(ar['power'][tag][L]))@jj[L].T for L in m);cv[7,7]+=shared**2
        campaigns[tag]=dict(C7=float(cc[7]),sampling_se=float(max(0,cv[7,7])**.5),top_order=K,top_estimate=float(cc[K]),top_sampling_se=float(max(0,cv[K,K])**.5))
    halves=[]
    for h in (0,1):
        mm={L:sum(ar[s][t][L][h*len(ar[s][t][L])//2:(h+1)*len(ar[s][t][L])//2].mean(0)for s in ar for t in ('a','b'))/2 for L in m};cc=coefficients(mm,B2);cc[7]+=offset;halves.append(cc.tolist())
    boot=None
    if bootstrap:
        rng=np.random.default_rng(70530413);xs=[];dx=[]
        for _ in range(bootstrap):
            mm={s:{L:sum(ar[s][t][L][rng.integers(len(ar[s][t][L]),size=len(ar[s][t][L]))].mean(0)for t in ('a','b'))/2 for L in m}for s in ar}
            f=coefficients({L:mm['free'][L]+mm['power'][L]for L in m},B2);fp=coefficients(mm['free'],B2);dx.append(f-fp);f[7]+=offset+(rng.normal()*shared if shared else 0);xs.append(f)
        xx=np.array(xs);dd=np.array(dx);boot=dict(replicates=bootstrap,seed=70530413,full_se=xx.std(0,ddof=1).tolist(),correction_se=dd.std(0,ddof=1).tolist(),bias=(xx.mean(0)-mu).tolist(),diagnostic_only=True)
    r=dict(schema='c7-d3-hpc-result-2',dimension=3,order=7,max_order=K,epsilon='2s-3',C7_full=float(mu[7]),sampling_standard_error=float(se[7]),coefficients=mu.tolist(),standard_errors=se.tolist(),covariance=cov.tolist(),
           power_free_C7=float(pf[7]),power_free_se=float(max(0,pcov[7,7])**.5),power_free_coefficients=pf.tolist(),power_free_standard_errors=pse.tolist(),
           power_correction=float(delta[7]),power_correction_se=float(dse[7]),power_free_correction_covariance=float(cross[7,7]),power_differences=delta.tolist(),power_difference_errors=dse.tolist(),
           means={s:{str(L):v.tolist()for L,v in means[s].items()}for s in ar},error_by_loop={str(L):{s:float(max(0,contributions[s][L][7,7])**.5)for s in ar}for L in m},shared_primitive=primitive,shared_reference_se=shared,
           campaigns=campaigns,half_streams=halves,bootstrap=boot,empirical_allowance=None,
           scope='Sampling precision only. No analytic rederivation or interval enclosure. New production explicitly integrates both sectors; prior complete coefficient not an input; no lower physical coefficient imposed as a constraint.')
    if K<7:
        # Prefix plan: orders above K would need the missing loops; nothing above K is reported.
        cut=K+1
        for key in ('coefficients','standard_errors','power_free_coefficients','power_free_standard_errors','power_differences','power_difference_errors'):r[key]=r[key][:cut]
        r['covariance']=[row[:cut]for row in r['covariance'][:cut]];r['half_streams']=[h[:cut]for h in r['half_streams']]
        for key in ('C7_full','sampling_standard_error','power_free_C7','power_free_se','power_correction','power_correction_se','power_free_correction_covariance','error_by_loop'):r[key]=None
        for c in r['campaigns'].values():c.pop('C7');c.pop('sampling_se')
        if boot:
            for key in ('full_se','correction_se','bias'):boot[key]=boot[key][:cut]
        r['scope']=f'Prefix plan (loops 3..{K}): coefficients up to order {K} only. '+r['scope']
    return r

def pull(x,s):return float(x/s)if s>0 else None

def gate_checks(r:dict,refs:dict)->dict:
    """Consistency gates (never constraints): lower orders against references, power differences against zero, the
    a/b campaigns, bootstrap against covariance SE, and the archived C7(3). |pull| > 3 is flagged. The archived C7(3)
    is flagged by the reporting rule's own measure, |difference| > 3 archived SE (in_archived_se); its combined-
    uncertainty pull is reported as a diagnostic only."""
    K=r['max_order'];out={'lower_order':[],'lower_order_secondary':[],'power_differences':[],'campaign_pull':None,'bootstrap_ratio':None,'archived':None}
    for key,target in (('coefficients','lower_order'),('secondary','lower_order_secondary')):
        for e in refs[key]:
            k=e['order']
            if k>K:continue
            est,se=r['coefficients'][k],r['standard_errors'][k]
            out[target].append({'order':k,'estimate':est,'sampling_se':se,'reference':e['value'],'reference_se':e['se'],'reference_source':e['source'],'pull':pull(est-e['value'],math.hypot(se,e['se']))})
    for k in refs['zero_power_differences_orders']:
        if k>K:continue
        d,s=r['power_differences'][k],r['power_difference_errors'][k];out['power_differences'].append({'order':k,'difference':d,'se':s,'pull':pull(d,s)})
    if K==7:
        a,b=r['campaigns']['a'],r['campaigns']['b'];sh=float(r.get('shared_reference_se')or 0.)
        # Each campaign SE includes the shared retained-primitive SE (retained mode), which cancels in a - b.
        ia,ib=(max(0.,x['sampling_se']**2-sh**2)**.5 for x in (a,b))
        out['campaign_pull']={'a':a['C7'],'a_se':a['sampling_se'],'b':b['C7'],'b_se':b['sampling_se'],'shared_se_excluded':sh,'pull':pull(a['C7']-b['C7'],math.hypot(ia,ib))}
        if r['bootstrap']:out['bootstrap_ratio']={'bootstrap_se':r['bootstrap']['full_se'][7],'covariance_se':r['sampling_standard_error'],'ratio':r['bootstrap']['full_se'][7]/r['sampling_standard_error']}
        arc=refs['archived_C7'];d=r['C7_full']-arc['value']
        out['archived']={'reference':arc['value'],'reference_se':arc['se'],'source':arc['source'],'difference':d,'pull':pull(d,math.hypot(r['sampling_standard_error'],arc['se'])),'in_archived_se':d/arc['se']}
    pulls=[(f'C{e["order"]}',e['pull'])for e in out['lower_order']]+[(f'power_difference[{e["order"]}]',e['pull'])for e in out['power_differences']]
    if out['campaign_pull']:pulls.append(('a/b campaigns',out['campaign_pull']['pull']))
    out['flags']=[{'check':n,'pull':p}for n,p in pulls if p is not None and abs(p)>3]
    if out['archived']and abs(out['archived']['in_archived_se'])>3:out['flags'].append({'check':'archived C7 (archived SE)','in_archived_se':out['archived']['in_archived_se']})
    if out['bootstrap_ratio']and not 0.8<=out['bootstrap_ratio']['ratio']<=1.2:out['flags'].append({'check':'bootstrap/covariance SE ratio','ratio':out['bootstrap_ratio']['ratio']})
    return out

def references()->tuple[dict,str]:
    data=REFERENCES.read_bytes();refs=json.loads(data)
    if refs.get('schema')!='c7-d3-references-1'or refs.get('dimension')!=3:raise ValueError('wrong references file')
    return refs,hashlib.sha256(data).hexdigest()

def provenance()->dict:return {n:digest(ROOT/'tools'/n)for n in ('assemble.py','report.py','production.py','common.py')if (ROOT/'tools'/n).exists()}

TEST_PHYSICAL=('C7_full','sampling_standard_error','coefficients','standard_errors','covariance','power_free_C7','power_free_se','power_free_coefficients','power_free_standard_errors','power_correction','power_correction_se',
               'power_free_correction_covariance','power_differences','power_difference_errors','means','error_by_loop','campaigns','half_streams','bootstrap','checks')
def finish(r:dict,test_only:bool)->dict:
    """Test-only campaigns (--test-graphs): every physical field moves under test_partial (A-L19)."""
    if not test_only:return r
    part={k:r.pop(k)for k in TEST_PHYSICAL if k in r};r.update(test_partial=part,C7_full=None,
        scope='INCOMPLETE workflow test (--test-graphs): graphs are excluded. Nothing here is a physical coefficient; partial values are under test_partial.')
    return r

def load_campaign(directory:Path):
    from production import group_of,validate_merged,verify_base
    m,_,mh=verify_base(directory,check_executable=False);ar={s:{t:{}for t in ('a','b')}for s in ('free','power')};hashes={}
    if m['campaign_weights']!={'a':.5,'b':.5}:raise ValueError('Changed campaign weights')
    want={(t,s,L)for t in 'ab'for s in ('free','power')for L in m['loops']};seen=set()
    for gr in m['groups']:
        p,cfg=group_of(directory,m,gr['name']);d=validate_merged(p,cfg,m,mh);key=(cfg['campaign'],cfg['sector'],cfg['L'])
        if key in seen:raise ValueError('Duplicate group')
        seen.add(key);x=np.asarray(d['batches'],float)
        if x.shape!=(cfg['replicates'],2*(8-cfg['L'])):raise ValueError('Wrong data shape')
        ar[cfg['sector']][cfg['campaign']][cfg['L']]=x;hashes[gr['name']]=digest(p/'merged.json')
    if seen!=want:raise ValueError('merged groups do not match the plan')
    return m,mh,ar,hashes

def evaluate(directory:Path,bootstrap=1024)->dict:
    m,mh,ar,hashes=load_campaign(directory);vi=verified_inputs(m['inputs_manifest_sha256']);refs,rsha=references()
    primitive=vi['primitive']if m['primitive_mode']=='retained'else None
    r=calculate(ar,primitive,bootstrap,vi['B2'])
    r.update(source_manifest_sha256=mh,merged_sha256=hashes,primitive_mode=m['primitive_mode'],backend=m['backend'],build=m['build'],test_only=m['test_only'],
             input_sha256=vi['sha256'],references_sha256=rsha,tool_sha256=provenance())
    r['checks']=gate_checks(r,refs)
    return finish(r,m['test_only'])

ROUNDING_REL=1e-10
def _numeric(x)->bool:return isinstance(x,(int,float))and not isinstance(x,bool)

def _rounding(a,b,rel:float,scale:float=0.)->float|None:
    """Largest relative difference over two JSON trees that are identical in structure and in every non-numeric leaf
    and whose integers are equal; None otherwise. Floats compare as |a-b| <= rel * max(|a|, |b|, scale), where scale
    is the largest magnitude among the numeric entries of the innermost containing list: last-bit noise in an entry
    that is zero in exact arithmetic (e.g. power_differences[3] ~ 1e-16 next to entries ~ 1) is judged against its
    vector's scale, not against itself."""
    if _numeric(a)and _numeric(b):
        if type(a)is int and type(b)is int:return 0. if a==b else None
        if a==b:return 0.
        m=max(abs(a),abs(b),scale);d=abs(a-b)/m
        return d if d<=rel else None
    if isinstance(a,dict)and isinstance(b,dict):
        if a.keys()!=b.keys():return None
        worst=0.
        for k in a:
            d=_rounding(a[k],b[k],rel)
            if d is None:return None
            worst=max(worst,d)
        return worst
    if isinstance(a,list)and isinstance(b,list):
        if len(a)!=len(b):return None
        sc=max([abs(x)for x in a+b if _numeric(x)],default=0.);worst=0.
        for x,y in zip(a,b):
            d=_rounding(x,y,rel,sc)
            if d is None:return None
            worst=max(worst,d)
        return worst
    return 0. if type(a)==type(b)and a==b else None

def rounding_difference(a,b,rel=ROUNDING_REL)->float|None:
    """Largest relative difference between two results (or values) that may differ only by float rounding, else None.
    Every non-numeric leaf (all data, input, reference and tool hashes) and every integer must be identical, and
    every float within rel of its vector's scale. The float64 assembly is reproducible bit for bit on one CPU type
    but not across types (NumPy/OpenBLAS SIMD dispatch: symmetry EPYC 7532/7543 (AVX2) vs EPYC 8534P (AVX-512)
    differ by 4 ulp in C7). The consistency gates (`checks`) are not compared value by value, because pulls of
    quantities that vanish in exact arithmetic are ratios of rounding noise: instead each result's stored gates must
    equal the gates recomputed from its own fields (consistent_checks)."""
    if isinstance(a,dict)and isinstance(b,dict):
        # The gates' VALUES are not compared, but their presence and location are: a missing or relocated `checks`
        # differs structurally (inspection C7I-11).
        mark=lambda v:'<checks>'if isinstance(v,dict)else v
        strip=lambda r:{k:({kk:(mark(vv)if kk=='checks'else vv)for kk,vv in v.items()}if k=='test_partial'and isinstance(v,dict)else mark(v)if k=='checks'else v)for k,v in r.items()}
        return _rounding(strip(a),strip(b),rel)
    return _rounding(a,b,rel)

def consistent_checks(r:dict)->bool:
    """True if a result's stored consistency gates equal gate_checks recomputed from its own fields."""
    base={**r,**(r.get('test_partial')or{})};stored=base.get('checks')
    if not isinstance(stored,dict):return False  # every result carries its gates (top level, or under test_partial)
    try:refs,_=references();return canon(gate_checks(base,refs))==canon(stored)
    except (KeyError,TypeError,ValueError,ZeroDivisionError):return False

def publish_result(dest:Path,result:dict)->str:
    """No-clobber, idempotent: an existing identical result is kept, and so is one that differs only by float
    rounding (recomputed on another CPU type: rounding_difference); anything else is an error, never overwritten."""
    if dest.exists():
        prior=load(dest);new=json.loads(json.dumps(result,allow_nan=False))
        if canon(prior)==canon(new):return 'identical result already present; kept'
        d=rounding_difference(prior,new)
        if d is None or not consistent_checks(prior):raise ValueError(f'{dest} exists and differs from the recomputed result; not overwritten')
        return f'existing result kept: this host\'s recomputation differs only by float rounding (max relative {d:.1e}; CPU-dependent NumPy/OpenBLAS paths)'
    try:dump(dest,result);return 'written'
    except FileExistsError:return publish_result(dest,result)

def summary_lines(r:dict)->list[str]:
    ch=r.get('checks')or(r.get('test_partial')or{}).get('checks')or{};out=[]
    for e in ch.get('lower_order',[]):out.append(f"C{e['order']}: {e['estimate']:.12g} +- {e['sampling_se']:.3g} vs {e['reference']:.12g} +- {e['reference_se']:.3g}: pull {e['pull']:+.2f}"if e['pull']is not None else f"C{e['order']}: no SE")
    for e in ch.get('power_differences',[]):out.append(f"power difference [{e['order']}]: {e['difference']:.4g} +- {e['se']:.3g}: pull {e['pull']:+.2f}"if e['pull']is not None else f"power difference [{e['order']}]: no SE")
    if ch.get('campaign_pull'):out.append(f"a/b campaigns: pull {ch['campaign_pull']['pull']:+.2f}")
    if ch.get('bootstrap_ratio'):out.append(f"bootstrap/covariance SE: {ch['bootstrap_ratio']['ratio']:.3f}")
    if ch.get('archived'):out.append(f"archived C7(3): {ch['archived']['in_archived_se']:+.2f} archived SE (pull {ch['archived']['pull']:+.2f})")
    for f in ch.get('flags',[]):out.append('FLAG: '+json.dumps(f))
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--bootstrap',type=int,default=1024);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.bootstrap<0 or a.bootstrap==1:raise ValueError('bootstrap must be zero or >=2')
    d=a.directory.resolve();r=evaluate(d,a.bootstrap)
    dest=a.output or d/('C7_test_result.json'if r['test_only']else'C7_result.json');state=publish_result(dest,r)
    print(json.dumps({'C7_full':r['C7_full'],'sampling_standard_error':r.get('sampling_standard_error'),'max_order':r.get('max_order',(r.get('test_partial')or{}).get('max_order')),
                      'primitive_mode':r['primitive_mode'],'test_only':r['test_only'],'output':str(dest),'state':state}))
    for line in summary_lines(r):print(line)
if __name__=='__main__':main()
