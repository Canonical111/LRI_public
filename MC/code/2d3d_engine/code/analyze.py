#!/usr/bin/env python3
"""Stream completed chains into block moments and full covariances in CFT variables.

No spin scaling dimension is fitted. No perturbative Delta_epsilon is read.
Raw samples are memory-mapped; only one block's feature arrays are allocated.
Reweighting at different beta values from the SAME chain is correlated; the FSS
summary contains only simulated beta values, never reweighted pseudo-replicas.
"""
from __future__ import annotations
import argparse, json, warnings
from collections import defaultdict
from pathlib import Path
import numpy as np

OBSERVABLES=['Y','dY_dbeta','d2Y_dbeta2','U','dU_dbeta','d2U_dbeta2']

def tau_int(x: np.ndarray) -> float:
    """Initial-positive-pair autocorrelation estimate; diagnostic, not a proof."""
    x=np.asarray(x[:262144],dtype=float);x=x-x.mean();n=len(x)
    if n<16 or np.dot(x,x)==0:return .5
    f=np.fft.rfft(x,n=1<<(2*n-1).bit_length())
    c=np.fft.irfft(f*f.conj())[:n//4]
    c/=np.arange(n,n-len(c),-1);c/=c[0]
    q=c[1:1+2*((len(c)-1)//2)].reshape(-1,2).sum(axis=1)
    bad=np.flatnonzero(q<=0);q=q[:bad[0]] if len(bad) else q
    return float(max(.5,.5+q.sum()))

def cft_observables(m: np.ndarray, n: int, s: float, beta: float, dim: int=1) -> np.ndarray:
    """Input (...,4,3) mean features: w*(1,m2,m4,m2_sample)*(1,q,q^2).

    q=K-Kref with a common Kref. The answer is independent of Kref.
    This uses factorial count cumulants: the -dlog/beta term in d2log
    is essential because the distribution is proportional to beta^K.
    """
    m=np.asarray(m,dtype=float)
    z=m[..., :,0];mean=m[..., :,1]/z;var=m[..., :,2]/z-mean**2
    a2=z[...,1]/z[...,0];a4=z[...,2]/z[...,0]
    dl=(mean[...,1:3]-mean[...,0,None])/beta
    d2l=(var[...,1:3]-var[...,0,None]-(mean[...,1:3]-mean[...,0,None]))/beta**2
    y=n**((dim-s)/dim)*a2;ratio=a4/(3*a2*a2);u=1-ratio
    r1=dl[...,1]-2*dl[...,0];r2=d2l[...,1]-2*d2l[...,0]
    return np.stack([y,y*dl[...,0],y*(d2l[...,0]+dl[...,0]**2),
                     u,-ratio*r1,-ratio*(r2+r1*r1)],axis=-1)

def block_estimate(blocks: np.ndarray, n: int, s: float, beta: float, dim: int=1) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    b=len(blocks)
    if b<20:raise ValueError('fewer than 20 complete blocks; increase statistics or reduce block size after tau check')
    m=blocks.mean(axis=0);val=cft_observables(m,n,s,beta,dim)
    jk=cft_observables((b*m-blocks)/(b-1),n,s,beta,dim)
    d=jk-jk.mean(axis=0);cov=(b-1)/b*(d.T@d)
    return val,cov,jk

def completed_groups(campaign: Path):
    manifest=json.loads((campaign/'manifest.json').read_text());groups=defaultdict(list)
    if len({t.get('nn_extra',0) for t in manifest['tasks']})>1:raise ValueError('analyze different nn-extra campaigns separately')
    skipped=[]
    for task in manifest['tasks']:
        d=campaign/task['directory'];marker=d/'DONE.json'
        if not marker.exists():skipped.append(task['id']);continue
        status=json.loads(marker.read_text());rows=status['measurements_done']
        raw=d/'samples.bin'
        if raw.stat().st_size!=rows*status.get('record_columns',4)*8:raise ValueError(f'inconsistent complete raw file: {raw}')
        t=dict(task,raw=str(raw),rows=rows,columns=status.get('record_columns',4))
        groups[(t['d'],t['s'],t['N'],t['beta'])].append(t)
    return groups,skipped

def collect_group(tasks: list[dict], block_size: int, target_beta: float | None=None,
                  diagnostics: bool=True):
    n=tasks[0]['N'];s=tasks[0]['s'];dim=tasks[0]['d'];beta0=tasks[0]['beta'];beta=beta0 if target_beta is None else target_beta
    if beta<=0:raise ValueError('target beta must be positive')
    arrays=[];kmean=0.;used=0;kmin=np.inf;kmax=-np.inf;discarded=0
    for t in tasks:
        a=np.memmap(t['raw'],dtype='<f8',mode='r',shape=(t['rows'],t.get('columns',4)))
        count=len(a)//block_size*block_size;discarded+=len(a)-count
        if count==0:raise ValueError(f"chain {t['id']} shorter than block size")
        a=a[:count];arrays.append((t,a));used+=count
        kmean+=float(a[:,0].mean())*count;kmin=min(kmin,float(a[:,0].min()));kmax=max(kmax,float(a[:,0].max()))
    kref=kmean/used;h=np.log(beta/beta0)
    shift=max(h*(kmin-kref),h*(kmax-kref),0.)
    blocks=[];replicas=[];w2=0.;diags=[]
    for t,a in arrays:
        chainblocks=[]
        for start in range(0,len(a),block_size):
            x=np.asarray(a[start:start+block_size]);q=x[:,0]-kref
            powers=np.stack([np.ones_like(q),q,q*q],axis=1)
            v=np.column_stack([np.ones_like(q),x[:,1:4]])
            w=np.exp(h*q-shift)
            b=(v*w[:,None]).T@powers/block_size
            blocks.append(b);chainblocks.append(b);replicas.append(t['replica']);w2+=np.dot(w,w)
        if diagnostics:
            prefix=np.asarray(a[:262144]);qc=prefix[:,0]-prefix[:,0].mean()
            taus={name:tau_int(v) for name,v in [('K',prefix[:,0]),('m2_cluster',prefix[:,1]),
                ('m4_cluster',prefix[:,2]),('m2_sample',prefix[:,3]),('m2_times_centered_K',prefix[:,1]*qc)]}
            b2=np.array(chainblocks)[:,1,0] if target_beta is None else np.asarray(a[:,1]).reshape(-1,block_size).mean(axis=1)
            half=len(b2)//2;z=None
            if half>=2:
                v1,v2=b2[:half],b2[half:];err=np.sqrt(v1.var(ddof=1)/len(v1)+v2.var(ddof=1)/len(v2))
                z=float((v1.mean()-v2.mean())/err) if err else None
            diags.append(dict(task_id=t['id'],replica=t['replica'],initialization=t['initialization'],
                m2_mean=float(a[:,1].mean()),m2_block_stderr=float(b2.std(ddof=1)/np.sqrt(len(b2))) if len(b2)>1 else None,
                first_vs_second_half_z=z,tau_estimate=taus,block_over_max_tau=block_size/max(taus.values()),
                tau_prefix_samples=len(prefix)))
    blocks=np.array(blocks);replicas=np.array(replicas,dtype=int)
    val,cov,jk=block_estimate(blocks,n,s,beta,dim)
    # ESS concerns importance weights only; it does NOT correct autocorrelation.
    weight_sum=blocks[:,0,0].sum()*block_size;ess_fraction=weight_sum**2/(used*w2)
    info=dict(s=s,d=dim,L=tasks[0]["L"],Delta_sigma=(dim-s)/2,N=n,beta=beta,beta_simulated=beta0,
        data=val.tolist(),cov=cov.tolist(),stderr=np.sqrt(np.diag(cov)).tolist(),
        block_size=block_size,nblocks=len(blocks),used_sweeps=used,discarded_tail_sweeps=discarded,
        K_reference=kref,K_mean=float(kref+blocks.mean(axis=0)[0,1]/blocks.mean(axis=0)[0,0]),
        reweighting_ESS_fraction=float(ess_fraction),replica_diagnostics=diags,
        jackknife_bias_estimate=((len(blocks)-1)*(jk.mean(axis=0)-val)).tolist())
    if ess_fraction<.2:warnings.warn('Poor count-histogram overlap: simulate closer to the target beta.')
    return info,blocks,replicas

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('campaign',type=Path);p.add_argument('--block',type=int,default=4096)
    p.add_argument('--out',type=Path);p.add_argument('--dim',type=int);p.add_argument('--s',type=float)
    p.add_argument('--n',type=int);p.add_argument('--beta',type=float,help='reweight one chosen simulated-beta group')
    p.add_argument('--sim-beta',type=float,help='select a simulated beta in a multi-temperature group')
    p.add_argument('--no-tau',action='store_true')
    a=p.parse_args()
    if a.block<2:p.error('block must be >= 2')
    groups,skipped=completed_groups(a.campaign)
    groups={k:v for k,v in groups.items() if (a.s is None or np.isclose(k[1],a.s,rtol=0,atol=1e-12))
        and (a.n is None or k[2]==a.n) and (a.dim is None or k[0]==a.dim) and (a.sim_beta is None or np.isclose(k[3],a.sim_beta,rtol=0,atol=1e-12))}
    if a.beta is not None and len(groups)!=1:
        p.error('reweight exactly one (s,N,beta_simulated) group; use --s --n --sim-beta')
    if not groups:p.error('no completed matching chains')
    out=a.out or a.campaign/(f'reweighted_{a.beta:.12g}' if a.beta else f'analysis_b{a.block}')
    out.mkdir(parents=True,exist_ok=True);entries=[]
    for idx,(key,tasks) in enumerate(sorted(groups.items())):
        info,blocks,reps=collect_group(tasks,a.block,a.beta,not a.no_tau)
        bfile=f'blocks_{idx:04d}.npz';np.savez_compressed(out/bfile,blocks=blocks,replicas=reps)
        info['blocks_file']=bfile;entries.append(info)
        print(f"d={key[0]} s={key[1]} N={key[2]} beta={info['beta']:.10g} blocks={len(blocks)} "
              f"Y={info['data'][0]:.7g} U={info['data'][3]:.7g} ESS_fraction={info['reweighting_ESS_fraction']:.3f}",flush=True)
    result=dict(observable_order=OBSERVABLES,entries=entries,skipped_tasks=skipped,
        covariance_note='Each entry is independent only at a distinct simulated beta or size. Reweighted targets from one chain are correlated.')
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(out/'summary.json')
if __name__=='__main__':main()
