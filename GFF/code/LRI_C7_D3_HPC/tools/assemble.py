#!/usr/bin/env python3
"""Assemble C0--C7(3) from complete independent finite-scheme RG-jet campaigns.

The power correction is measured, not zeroed. Whole randomized replicates are
statistical units; graph chunks are merged first. No lower coefficient is fitted.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
from common import ROOT,checked,digest,dump,load,object_hash
from production import verify_base
_low=load(ROOT/'inputs/two_loop.json')
if _low.get('dimension')!=3 or _low.get('order')!=7:raise ValueError('Wrong-dimensional two-loop data')
B2=np.asarray(_low['B2'],float)

def coefficients(vals):
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

def jacobians(means):
    out={}
    for L,a in means.items():
        columns=[]
        for j in range(len(a)):
            tmp={k:np.asarray(v,dtype=complex).copy()for k,v in means.items()};tmp[L][j]+=1e-20j;columns.append(coefficients(tmp).imag/1e-20)
        out[L]=np.array(columns).T
    return out

def calculate(ar,primitive=None,bootstrap=1024):
    """Pure assembly callable on independent replicate arrays.

    ar[sector][campaign][loop] has columns b Taylor jet followed by c jet.
    Equal campaign weights are precommitted. Shared primitive variance is added
    once, and cancels out of the power-sector difference.
    """
    if set(ar)!={'free','power'}:raise ValueError('Both sectors are required')
    for sector in ar:
        if set(ar[sector])!={'a','b'}:raise ValueError('Need two independent campaigns')
        for vals in ar[sector].values():
            if set(vals)!=set(range(3,8)):raise ValueError('Need all loops 3--7')
            for L,x in vals.items():
                if x.ndim!=2 or x.shape[1]!=2*(8-L) or len(x)<2 or not np.isfinite(x).all():raise ValueError('Invalid complete replicate data')
    means={s:{L:sum(x[L].mean(0)for x in ar[s].values())/2 for L in range(3,8)}for s in ar}
    vc={s:{L:sum(np.cov(x[L],rowvar=False,ddof=1)/len(x[L])for x in ar[s].values())/4 for L in range(3,8)}for s in ar}
    m={L:means['free'][L]+means['power'][L]for L in range(3,8)}
    J=jacobians(m);Jf=jacobians(means['free']);mu=coefficients(m);pf=coefficients(means['free']);delta=mu-pf
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
    se=np.sqrt(np.maximum(0,np.diag(cov)));dse=np.sqrt(np.maximum(0,np.diag(dcov)))
    campaigns={}
    for tag in ('a','b'):
        mm={L:ar['free'][tag][L].mean(0)+ar['power'][tag][L].mean(0)for L in m};jj=jacobians(mm);cc=coefficients(mm);cc[7]+=offset
        cv=sum(jj[L]@(np.cov(ar['free'][tag][L],rowvar=False)/len(ar['free'][tag][L])+np.cov(ar['power'][tag][L],rowvar=False)/len(ar['power'][tag][L]))@jj[L].T for L in m);cv[7,7]+=shared**2
        campaigns[tag]=dict(C7=float(cc[7]),sampling_se=float(max(0,cv[7,7])**.5))
    halves=[]
    for h in (0,1):
        mm={L:sum(ar[s][t][L][h*len(ar[s][t][L])//2:(h+1)*len(ar[s][t][L])//2].mean(0)for s in ar for t in ('a','b'))/2 for L in m};cc=coefficients(mm);cc[7]+=offset;halves.append(cc.tolist())
    boot=None
    if bootstrap:
        rng=np.random.default_rng(70530413);xs=[];dx=[]
        for _ in range(bootstrap):
            mm={s:{L:sum(ar[s][t][L][rng.integers(len(ar[s][t][L]),size=len(ar[s][t][L]))].mean(0)for t in ('a','b'))/2 for L in m}for s in ar}
            f=coefficients({L:mm['free'][L]+mm['power'][L]for L in m});fp=coefficients(mm['free']);dx.append(f-fp);f[7]+=offset+(rng.normal()*shared if shared else 0);xs.append(f)
        xx=np.array(xs);dd=np.array(dx);boot=dict(replicates=bootstrap,seed=70530413,full_se=xx.std(0,ddof=1).tolist(),correction_se=dd.std(0,ddof=1).tolist(),bias=(xx.mean(0)-mu).tolist(),diagnostic_only=True)
    return dict(schema='c7-d3-hpc-result-1',dimension=3,order=7,epsilon='2s-3',C7_full=float(mu[7]),sampling_standard_error=float(se[7]),coefficients=mu.tolist(),standard_errors=se.tolist(),covariance=cov.tolist(),power_free_C7=float(pf[7]),power_free_se=float(max(0,pcov[7,7])**.5),power_correction=float(delta[7]),power_correction_se=float(dse[7]),power_free_correction_covariance=float(cross[7,7]),power_differences=delta.tolist(),power_difference_errors=dse.tolist(),means={s:{str(L):v.tolist()for L,v in means[s].items()}for s in ar},error_by_loop={str(L):{s:float(max(0,contributions[s][L][7,7])**.5)for s in ar}for L in m},shared_primitive=primitive,shared_reference_se=shared,campaigns=campaigns,half_streams=halves,bootstrap=boot,empirical_allowance=None,scope='Sampling precision only. No analytic rederivation or interval enclosure. New production explicitly integrates both sectors; prior complete coefficient not an input; no lower physical coefficient imposed as a constraint.')

def evaluate(directory,bootstrap=1024):
    m,_=verify_base(directory);mh=digest(directory/'manifest.json');ar={s:{t:{}for t in ('a','b')}for s in ('free','power')};hashes={}
    if m['campaign_weights']!={'a':.5,'b':.5}:raise ValueError('Changed campaign weights')
    seen=set()
    for gr in m['groups']:
        p=directory/'groups'/gr['name'];checked(p/'config.json',gr['sha256']);cfg=load(p/'config.json');d=load(p/'merged.json')
        if not d['complete']or d['manifest_sha256']!=mh or d['config_hash']!=object_hash(cfg)or d['primitive_mode']!=m['primitive_mode']or d['sector']!=cfg['sector']or d['schema']!='c7-d3-merged-1':raise ValueError('Invalid merged metadata')
        if object_hash({k:v for k,v in d.items()if k!='payload_sha256'})!=d['payload_sha256']:raise ValueError('Merged payload corruption')
        checked(p/'graph_replicates.csv',d['graph_replicates_sha256']);key=(cfg['sector'],cfg['campaign'],cfg['L'])
        if key in seen:raise ValueError('Duplicate group')
        seen.add(key);x=np.asarray(d['batches'],float)
        if x.shape!=(cfg['replicates'],2*(8-cfg['L'])):raise ValueError('Wrong data shape')
        ar[key[0]][key[1]][key[2]]=x;hashes[gr['name']]=digest(p/'merged.json')
    primitive=load(ROOT/'inputs/primitive_reference.json')if m['primitive_mode']=='retained'else None
    r=calculate(ar,primitive,bootstrap);r.update(source_manifest_sha256=mh,merged_sha256=hashes,primitive_mode=m['primitive_mode'],backend=m['backend'],build=m['build'],test_only=m['test_only'])
    refs={3:-.3535815204332,4:1.228063545327623,5:-5.85035142075,6:33.56819679857058}
    r['lower_order_checks']=[dict(order=k,estimate=r['coefficients'][k],sampling_se=r['standard_errors'][k],reference=v)for k,v in refs.items()]
    if m['test_only']:
        r['test_partial_value']=r.pop('C7_full');r['C7_full']=None;r['scope']='INCOMPLETE workflow test. Not a physical coefficient; excludes graphs.'
    return r

def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--bootstrap',type=int,default=1024);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.bootstrap<0 or a.bootstrap==1:raise ValueError('bootstrap must be zero or >=2')
    r=evaluate(a.directory.resolve(),a.bootstrap);dump(a.output or a.directory/'C7_result.json',r);print(json.dumps({k:r[k]for k in ('C7_full','sampling_standard_error','primitive_mode','test_only')}))
if __name__=='__main__':main()
