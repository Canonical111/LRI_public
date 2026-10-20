#!/usr/bin/env python3
"""Joint multi-temperature, block-bootstrap size-doubling CFT dimensions.

No continuum curve is imposed. Each bootstrap resamples every chain ONCE per
replicate, preserving correlations between adjacent size pairs. All free energies,
Binder crossing temperatures and thermal slopes are recalculated each time.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
import numpy as np
from scipy.optimize import brentq
from multihist import MultiHistogram

class Group:
    def __init__(self,tasks,root):
        self.tasks=tasks;self.d=tasks[0]['d'];self.L=tasks[0]['L'];self.s=tasks[0]['s'];self.nn=tasks[0].get('nn_extra',0)
        if any((t['d'],t['L'],t['s'],t.get('nn_extra',0))!=(self.d,self.L,self.s,self.nn) for t in tasks):raise ValueError('mixed physical models in histogram group')
        self.betas=np.unique([t['beta'] for t in tasks]);self.data=[]
        import hashlib
        for t in tasks:
            f_=root/t['histogram'];want=t.get('diagnostics',{}).get('packed_sha256')
            if not want:raise ValueError(f'{f_}: index has no packed_sha256 (packed with an older pack_histograms.py): repack before analysing (FIT2D-007)')
            if hashlib.sha256(f_.read_bytes()).hexdigest()!=want:raise ValueError(f'{f_}: packed histogram differs from the index record (FIT2D-007)')
            with np.load(f_) as f:a={k:f[k] for k in ('indptr','K','counts','sums')}
            a['ib']=int(np.argmin(abs(self.betas-t['beta'])));a['blocks']=len(a['indptr'])-1;self.data.append(a)
        self.K=np.unique(np.concatenate([a['K'] for a in self.data]))
        for a in self.data:a['index']=np.searchsorted(self.K,a['K'])
        self.central=self.curve()

    def curve(self,rng=None):
        h=np.zeros((len(self.betas),len(self.K)));S=np.zeros((4,len(self.K)))
        for a in self.data:
            weights=np.ones(len(a['K']))
            if rng is not None:
                B=a['blocks'];mult=rng.multinomial(B,np.ones(B)/B)
                weights=np.repeat(mult,np.diff(a['indptr']))
            h[a['ib']]+=np.bincount(a['index'],weights=a['counts']*weights,minlength=len(self.K))
            for j in range(4):S[j]+=np.bincount(a['index'],weights=a['sums'][:,j]*weights,minlength=len(self.K))
        keep=h.sum(0)>0;initial=self.central.f if hasattr(self,'central') else None
        return MultiHistogram(self.K[keep],h[:,keep],S[:,keep],self.betas,self.d,self.L,self.s,initial)

def crossing(a,b,miness=.2,which=1):
    if b.L!=2*a.L or a.d!=b.d or abs(a.s-b.s)>1e-12:
        raise ValueError('size-doubling requires the same model and L2=2L')
    lo=max(a.betas.min(),b.betas.min());hi=min(a.betas.max(),b.betas.max())
    if hi<=lo:raise ValueError('overlap needs >=2 simulated temperatures per size, or a wider shared bracket')
    grid=np.linspace(lo,hi,41)
    def diff(beta):return b.evaluate(beta)[0][which,0]-a.evaluate(beta)[0][which,0]
    vals=[diff(x) for x in grid];roots=[]
    for i in range(len(grid)-1):
        if vals[i]==0:roots.append(grid[i])
        elif vals[i]*vals[i+1]<0:roots.append(brentq(diff,grid[i],grid[i+1],xtol=5e-14))
    if vals[-1]==0:roots.append(grid[-1])
    if len(roots)!=1:raise ValueError(f'{len(roots)} Binder crossings in simulated-temperature bracket')
    beta=roots[0];A,e1=a.evaluate(beta);B,e2=b.evaluate(beta)
    if min(e1,e2)<miness:raise ValueError('crossing has insufficient mixture-importance overlap')
    if np.any(A[:,1]*B[:,1]<=0):raise ValueError('nonpositive thermal slope ratio')
    values=np.r_[beta,a.d-np.log(B[:,1]/A[:,1])/np.log(2)]
    return values,{'beta_bracket':[float(lo),float(hi)],'ESS_fraction':[e1,e2],
                   'U4_crossing':[float(A[1,0]),float(B[1,0])],'U6_crossing':[float(A[2,0]),float(B[2,0])]}

def run(index,dim,s,nn=0,bootstrap=200,seed=571239,miness=.2):
    root=index.parent;itext=index.read_bytes();mf=json.loads(itext)
    tasks=[t for t in mf['tasks'] if t['d']==dim and abs(t['s']-s)<1e-10 and abs(t.get('nn_extra',0)-nn)<1e-12]
    if not tasks:raise ValueError('no matching histogram files')
    groups={L:Group([t for t in tasks if t['L']==L],root) for L in sorted({t['L'] for t in tasks})}
    rows=[];central={};warnings=[]
    for L,g in groups.items():
        if 2*L not in groups:continue
        try:
            v,diag=crossing(g.central,groups[2*L].central,miness);central[L]=v
            rows.append(dict(L=L,L2=2*L,values=v.tolist(),diagnostics=diag))
        except ValueError as e:warnings.append({'L':L,'reason':str(e)})
    rng=np.random.default_rng(seed);order=sorted(central);draws=np.full((bootstrap,len(order),5),np.nan)
    for b in range(bootstrap):
        curves={}
        for L,g in groups.items():
            try:curves[L]=g.curve(rng)
            except (ValueError,np.linalg.LinAlgError):pass
        for j,L in enumerate(order):
            if L not in curves or 2*L not in curves:continue
            try:draws[b,j]=crossing(curves[L],curves[2*L],miness)[0]
            except ValueError:pass
        if (b+1)%20==0:print(f'bootstrap {b+1}/{bootstrap}',flush=True)
    for r in rows:
        j=order.index(r['L']);keep=np.isfinite(draws[:,j]).all(1);v=draws[keep,j]
        r.update(bootstrap_successes=int(keep.sum()),bootstrap_failure_fraction=float(1-keep.mean()) if bootstrap else None)
        if len(v)>=30:
            r.update(statistical_stderr=v.std(0,ddof=1).tolist(),bootstrap_percentile_95=np.quantile(v,[.025,.975],axis=0).tolist(),
                     covariance=np.cov(v,rowvar=False,ddof=1).tolist(),bootstrap_bias=(v.mean(0)-r['values']).tolist())
        r['finite_size_diagnostics']={}
        if len(v)>=30:
            dv=v[:,1]-v[:,2];err=float(dv.std(ddof=1));central_diff=float(r['values'][1]-r['values'][2])
            r['finite_size_diagnostics']={'Delta_Y_minus_U4':central_diff,'correlated_statistical_stderr':err,
                'z':central_diff/err if err>0 else None,
                'warning':('different slope observables disagree beyond 3 statistical errors: no common continuum error established'
                    if abs(central_diff)>3*err else 'agreement is a check, not a bound on finite-size error')}
        r['precision_flags']=[]
        if len(v)<50:r['precision_flags'].append('fewer than 50 valid bootstrap replicates')
        if bootstrap and 1-keep.mean()>.05:r['precision_flags'].append('>5% failed bootstrap roots: rebracket / increase statistics')
    complete=np.isfinite(draws).all(axis=(1,2)) if len(order) else np.zeros(bootstrap,dtype=bool)
    covariance=None
    if complete.sum()>=50:covariance=np.cov(draws[complete].reshape(complete.sum(),-1),rowvar=False).tolist()
    chain_diags=[dict(task_id=t['id'],initialization=t['initialization'],**t['diagnostics']) for t in tasks]
    for dg in chain_diags:
        if dg['block_over_max_tau']<20:warnings.append({'task':dg['task_id'],'reason':'block <20 times estimated max autocorrelation: increase block and recheck'})
        if abs(dg['half_drift_z'])>4:warnings.append({'task':dg['task_id'],'reason':'large within-chain drift: revisit thermalization'})
    import hashlib
    here=Path(__file__).resolve().parent
    result=dict(d=dim,s=s,nn_extra=nn,Delta_sigma=(dim-s)/2,block=mf['block'],min_ess=miness,campaign_id=mf.get('campaign_id'),manifest_sha256=mf.get('manifest_sha256'),
                manifest_tasks=mf.get('manifest_tasks'),index_path=str(index.resolve()),index_sha256=hashlib.sha256(itext).hexdigest(),index_skipped_tasks=mf.get('skipped',[]),
                code_sha256={f:hashlib.sha256((here/f).read_bytes()).hexdigest() for f in ('precision_analysis.py','multihist.py','pack_histograms.py','analyze.py')},   # FIT2D-001/007 provenance
                observable_order=['beta_cross','Delta_eff_Y','Delta_eff_U4','Delta_eff_U6','Delta_eff_U8'],
                rows=rows,warnings=warnings,histogram_diagnostics={L:g.central.diagnostics() for L,g in groups.items()},
                chains=chain_diags,bootstrap=bootstrap,bootstrap_seed=seed,joint_pair_order=order,
                joint_complete_bootstraps=int(complete.sum()),joint_pair_covariance=covariance,
                qualification='Finite-size dimensions. Statistical bootstrap intervals exclude continuum extrapolation bias. ESS describes importance weights, not independent Markov samples.')
    return result,draws

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('index',type=Path)
    p.add_argument('--dim',type=int,required=True);p.add_argument('--s',type=float,required=True);p.add_argument('--nn-extra',type=float,default=0)
    p.add_argument('--bootstrap',type=int,default=200);p.add_argument('--seed',type=int,default=571239);p.add_argument('--min-ess',type=float,default=.2)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.bootstrap<0 or not 0<a.min_ess<=1:p.error('invalid bootstrap count or ESS threshold')
    try:a.out.mkdir(parents=True)   # FIT2D-008: atomic claim before the long computation
    except FileExistsError:p.error(f'{a.out} exists: analysis records are immutable, use a new --out (FIT2D-008)')
    result,draws=run(a.index,a.dim,a.s,a.nn_extra,a.bootstrap,a.seed,a.min_ess)
    (a.out/'results.json').write_text(json.dumps(result,indent=2)+'\n');np.save(a.out/'bootstrap.npy',draws)
    with (a.out/'dimensions.csv').open('w',newline='') as f:
        cols=['d','s','Delta_sigma','L','L2','beta_cross','Delta_epsilon_eff','statistical_stderr','bootstrap_failure_fraction','flags']
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for r in result['rows']:
            e=r.get('statistical_stderr',[None]*5)[2]
            w.writerow(dict(d=a.dim,s=a.s,Delta_sigma=result['Delta_sigma'],L=r['L'],L2=r['L2'],beta_cross=r['values'][0],
                 Delta_epsilon_eff=r['values'][2],statistical_stderr=e,bootstrap_failure_fraction=r['bootstrap_failure_fraction'],flags='; '.join(r['precision_flags'])))
            print('L',r['L'],'->',r['L2'],'Delta_eff(U4)=',r['values'][2],'+/-',e,flush=True)
    print(a.out/'results.json')
if __name__=='__main__':main()
