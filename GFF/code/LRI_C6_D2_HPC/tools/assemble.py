#!/usr/bin/env python3
"""Full C6(2) fixed-point assembly from complete independent loop-jet replicates.

Never average chunks as if they were new randomizations. The same primordial
reference, if retained, contributes its uncertainty ONCE across both campaigns.
The two assembly-only inputs (two-loop B2, primitive reference P10) are used only
after their checksums match the inputs manifest frozen by the campaign plan.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from common import ROOT,canon,checked,digest,dump,load,object_hash
REFERENCE_LOWER=[-0.8748500126526336895,5.0488684313548,-38.8336458962282]
_DEFAULT=None

def verified_inputs(expected_manifest_sha256:str|None=None)->dict:
    """B2 and P10 from inputs/, checked against inputs/manifest.json (itself checked against the plan when given)."""
    data=(ROOT/'inputs/manifest.json').read_bytes();msha=hashlib.sha256(data).hexdigest()
    if expected_manifest_sha256 is not None and msha!=expected_manifest_sha256:raise ValueError('Checksum mismatch: inputs/manifest.json differs from the campaign plan')
    table=json.loads(data)['sha256'];out={'sha256':{'inputs/manifest.json':msha}}
    for name in ('two_loop.json','primitive_reference.json'):
        raw=(ROOT/'inputs'/name).read_bytes();h=hashlib.sha256(raw).hexdigest()
        if h!=table[name]:raise ValueError('Checksum mismatch: inputs/'+name)
        out[name]=json.loads(raw);out['sha256']['inputs/'+name]=h
    return {'B2':np.array(out['two_loop.json']['B2']),'primitive_reference':out['primitive_reference.json'],'sha256':out['sha256']}

def default_B2():
    global _DEFAULT
    if _DEFAULT is None:_DEFAULT=verified_inputs()
    return _DEFAULT['B2']

def coefficients(vals,B2=None):
    B2=default_B2()if B2 is None else B2
    dtype=np.result_type(*[np.asarray(v).dtype for v in vals.values()]);N=7
    b={1:np.array([3.],dtype=dtype),2:B2.astype(dtype)};c={1:np.array([1.],dtype=dtype),2:B2.astype(dtype)/6}
    for L,a in vals.items():
        a=np.asarray(a);k=7-L
        if a.shape!=(2*k,):raise ValueError('wrong jet shape')
        b[L]=a[:k];c[L]=a[k:]
    def mul(x,y):return np.convolve(x,y)[:N]
    g=np.zeros(N,dtype=dtype);e=g.copy();e[1]=1
    for _ in range(7):
        gp=g.copy();temp=np.zeros(N,dtype=dtype)
        for L in range(2,7):gp=mul(gp,g);temp[:len(gp)]+=mul(b.get(L,np.zeros(1)),gp)
        g=(e-temp)/3
    ga=np.zeros(N,dtype=dtype);gp=ga.copy();gp[0]=1
    for L in range(1,7):gp=mul(gp,g);ga+=mul(c.get(L,np.zeros(1)),gp)
    ga[0]+=1;ga[1]-=.5
    return ga

def jacobians(means,B2=None):
    J={}
    for L,a in means.items():
        out=[]
        for j in range(len(a)):
            tmp={k:np.asarray(v,dtype=complex).copy()for k,v in means.items()};tmp[L][j]+=1e-20j;out.append(coefficients(tmp,B2).imag/1e-20)
        J[L]=np.array(out).T
    return J

def combine(ar:dict,weights:dict,primitive_mode:str,B2,pref:dict,bootstrap:int=1024)->dict:
    """Pure assembly of replicate arrays ar[campaign][L] (replicates x jet) with fixed campaign weights."""
    means={L:sum(weights[t]*ar[t][L].mean(0)for t in weights)for L in range(3,7)};J=jacobians(means,B2)
    jc={L:sum(weights[t]**2*np.cov(ar[t][L],rowvar=False,ddof=1)/len(ar[t][L])for t in weights)for L in means};parts={L:J[L]@v@J[L].T for L,v in jc.items()};cov=sum(parts.values());mu=coefficients(means,B2)
    shared=0;offset=0
    if primitive_mode=='retained':
        offset=float(pref['mean']);shared=float(pref['sampling_se']);mu[6]+=offset;cov[6,6]+=shared**2
    sem=np.sqrt(np.maximum(0,np.diag(cov)))
    campaigns={}
    for t in weights:
        mm={L:a.mean(0)for L,a in ar[t].items()};jj=jacobians(mm,B2);cc=coefficients(mm,B2);cc[6]+=offset;cv=sum(jj[L]@np.cov(a,rowvar=False,ddof=1)@jj[L].T/len(a)for L,a in ar[t].items());cv[6,6]+=shared**2
        campaigns[t]={'C6':float(cc[6]),'sampling_se':float(max(0,cv[6,6])**.5)}
    # Paired lower jets stay together inside each bootstrap replicate; independent
    # loops/campaigns are resampled independently. One shared draw for the reference.
    boot=None
    if bootstrap:
        rng=np.random.default_rng(82491001);v=[]
        for _ in range(bootstrap):
            mm={L:sum(weights[t]*ar[t][L][rng.integers(0,len(ar[t][L]),len(ar[t][L]))].mean(0)for t in weights)for L in means}
            v.append(coefficients(mm,B2)[6]+offset+(rng.normal()*shared if shared else 0))
        boot={'replicates':bootstrap,'sampling_se':float(np.std(v,ddof=1)),'mean_minus_estimate':float(np.mean(v)-mu[6]),'diagnostic_only':True}
    return {'C6':float(mu[6]),'sampling_standard_error':float(sem[6]),'coefficients':mu.tolist(),'covariance':cov.tolist(),'standard_errors':sem.tolist(),'jet_means':{str(k):v.tolist()for k,v in means.items()},'jet_covariances':{str(k):v.tolist()for k,v in jc.items()},'error_by_loop':{str(k):float(max(0,v[6,6])**.5)for k,v in parts.items()},'primitive_mode':primitive_mode,'shared_primitive_input':pref if shared else None,'shared_reference_standard_error':shared,'campaigns':campaigns,'campaign_weights':weights,'lower_order_checks':[{'order':i+3,'estimate':float(mu[i+3]),'reference':r,'sampling_se':float(sem[i+3]),'pull':float((mu[i+3]-r)/sem[i+3])if sem[i+3]else None}for i,r in enumerate(REFERENCE_LOWER)],'bootstrap':boot}

def load_campaign(directory:Path):
    from production import group_of,validate_merged,verify_base
    m,_,mh=verify_base(directory,check_executable=False);weights=m['campaign_weights'];ar={t:{}for t in weights};inputhash={}
    if set(weights)!={'a','b'}or any(w!=.5 for w in weights.values()):raise ValueError('unexpected frozen weighting plan')
    for gr in m['groups']:
        p,cfg=group_of(directory,m,gr['name']);d=validate_merged(p,cfg,m,mh);inputhash[gr['name']]=digest(p/'merged.json')
        a=np.array(d['batches'],float)
        if a.shape!=(cfg['replicates'],2*(7-cfg['L']))or not np.isfinite(a).all()or len(a)<2:raise ValueError('invalid replicate array')
        ar[cfg['campaign']][cfg['L']]=a
    if any(set(v)!=set(range(3,7))for v in ar.values()):raise ValueError('missing loop/campaign data')
    return m,mh,ar,inputhash

def evaluate(directory:Path,bootstrap:int=1024):
    m,mh,ar,inputhash=load_campaign(directory);vi=verified_inputs(m['inputs_manifest_sha256'])
    out={'schema':'c6-d2-hpc-result-2','dimension':2,'epsilon':'2s-2'}
    out.update(combine(ar,m['campaign_weights'],m['primitive_mode'],vi['B2'],vi['primitive_reference'],bootstrap))
    out.update({'input_sha256':vi['sha256'],'empirical_allowance':None,'empirical_allowance_reason':'Do not infer certified physical digits from sampling SE alone. Examine independent campaigns, tails and lower-order checks. No rigorous error bound is supplied.','source_manifest_sha256':mh,'merged_sha256':inputhash,'power_correction':'Uses the retained analytic compensation of the reference finite-MOM calculation, not a fresh independent power-sector audit.','old_complete_C6_included_in_estimator':False,'lower_order_physical_values_used_as_constraints':False})
    return out

def publish_result(dest:Path,result:dict)->str:
    """No-clobber, idempotent: an existing identical result is kept; a different one is an error."""
    if dest.exists():
        if canon(load(dest))!=canon(json.loads(json.dumps(result,allow_nan=False))):raise ValueError(f'{dest} exists and differs from the recomputed result; not overwritten')
        return 'identical result already present; kept'
    try:dump(dest,result);return 'written'
    except FileExistsError:return publish_result(dest,result)

def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--bootstrap',type=int,default=1024);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.bootstrap<0:raise ValueError('negative bootstrap count')
    result=evaluate(a.directory.resolve(),a.bootstrap);dest=a.output or a.directory/'C6_result.json';state=publish_result(dest,result)
    print(json.dumps({**{k:result[k]for k in ('C6','sampling_standard_error','primitive_mode')},'output':str(dest),'state':state}))
if __name__=='__main__':main()
