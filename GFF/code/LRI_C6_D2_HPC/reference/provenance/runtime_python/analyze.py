"""Reassemble old and fresh RG jets, accounting for retained inputs ONCE."""
from pathlib import Path
import sys,json,os
import numpy as np
W=Path(__file__).resolve().parents[1]
B=Path(os.environ.get('LRI_BASELINE',str(W/'baseline_previous')))
if not B.exists():B=Path('/mnt/data/c6_method_work/lri_C6_precision_update')
sys.path.insert(0,str(B/'code'))
from analysis import F,jacobians
K=json.load(open(B/'baseline/lri_C6_d2_complete_update/reproduction/mom_known_sectors.json'))
PIDS={639,648,649,651,653,654,655,657,658,659}
P=float(K['group_means'][0]);SP=float(K['group_sampling_ses'][0])
S=sum(K['group_means'][1:]);SS=float(np.linalg.norm(K['group_sampling_ses'][1:]))
REF={2:[-0.8748500126526336895,5.0488684313548,-38.8336458962282],3:[-0.3535815204331724,1.22806354532762308,-5.85035142075]}

def load(d,tag):
    old=tag.startswith('prod');root=B if old else W
    raw={L:json.load(open(root/f'records/{tag}_d{d}_L{L}.json'))for L in range(3,7)}
    ar={L:np.array(x['batches'],float)for L,x in raw.items()}
    if d==2:
        excluded=set(K['excluded_graph_ids']) if old else PIDS
        data=raw[6];sel=np.array([g not in excluded for g in data['graph_ids']])
        ar[6]=np.array(data['graph_batches'],float)[:,sel,:].sum(1)
        if not old:
            assert all(n==0 for i,n in zip(data['graph_ids'],data['counts_per_replicate'])if i in PIDS)
    return raw,ar

def evaluate(d,tags=('prod_a','prod_b','new_a','new_b'),write=True):
    data={t:load(d,t)for t in tags};weights=np.ones(len(tags))/len(tags)
    oldweight=sum(w for t,w in zip(tags,weights)if t.startswith('prod'))
    means={L:sum(w*data[t][1][L].mean(0)for t,w in zip(tags,weights))for L in range(3,7)}
    J=jacobians(d,means)
    jcov={L:sum(w*w*np.cov(data[t][1][L],rowvar=False,ddof=1)/len(data[t][1][L])for t,w in zip(tags,weights))for L in means}
    cps={L:J[L]@c@J[L].T for L,c in jcov.items()};cov=sum(cps.values());mu=F[d](means)
    offset=0;shared=0
    if d==2:
        offset=P+oldweight*S;mu[6]+=offset;shared=SP**2+oldweight**2*SS**2;cov[6,6]+=shared
    sem=np.sqrt(np.maximum(0,np.diag(cov)))
    halves=[]
    for h in range(2):
        mm={L:sum(w*np.array_split(data[t][1][L],2)[h].mean(0)for t,w in zip(tags,weights))for L in means}
        cc=F[d](mm);cc[6]+=offset;halves.append(cc.tolist())
    diag={}
    for t in tags:
        diag[t]={}
        for L,a in data[t][1].items():
            zz=(a-a.mean(0))@J[L][6];sd=zz.std(ddof=1);v2=zz**2
            diag[t][str(L)]={'max_abs_standardized':float(max(abs(zz))/sd),'max_variance_fraction':float(max(v2)/sum(v2)),'skewness':float(np.mean((zz/sd)**3)),'excess_kurtosis':float(np.mean((zz/sd)**4)-3)}
    out={'dimension':d,'epsilon':f'2s-{d}','C6':float(mu[6]),'sampling_standard_error':float(sem[6]),'coefficients':mu.tolist(),'standard_errors':sem.tolist(),'covariance':cov.tolist(),'weights':dict(zip(tags,weights.tolist())),'weight_rule':'Equal RG-jet weights frozen before fresh production; no inverse-error or result-dependent weighting.', 'error_by_loop':{str(L):float(max(0,c[6,6])**.5)for L,c in cps.items()},'shared_input_standard_error':shared**.5,'d2_offset':offset,'d2_primitive':{'mean':P,'se':SP,'total_weight':1}if d==2 else None,'d2_retained_66':{'mean':S,'se':SS,'total_weight':oldweight}if d==2 else None,'means':{str(L):v.tolist()for L,v in means.items()},'jet_covariances':{str(L):v.tolist()for L,v in jcov.items()},'jacobians':{str(L):v.tolist()for L,v in J.items()},'half_run_coefficients':halves,'replicate_diagnostics':diag,'lower_order_checks':[{'order':j+3,'value':float(mu[j+3]),'reference':ref,'se':float(sem[j+3]),'pull':float((mu[j+3]-ref)/sem[j+3])}for j,ref in enumerate(REF[d])],'samples':{t:{str(L):r['N']for L,r in raw.items()}for t,(raw,ar)in data.items()},'fallbacks':{t:{str(L):{k:r[k]for k in ['quad_fallbacks','mp_fallbacks']}for L,r in raw.items()}for t,(raw,ar)in data.items()},'new_pilot_or_validation_samples_in_estimator':False,'previous_production_reused_for_lower_loop_allocation':True,'lower_physical_coefficients_fitted_as_controls':False,'power_compensation_rerun':False,'independent_field_theory_validation':False}
    if write:(W/f'verification/result_d{d}_{"_".join(tags)}.json').write_text(json.dumps(out,indent=2))
    return out

def main():
    allout={}
    for d in (2,3):
        x=evaluate(d);prev=evaluate(d,('prod_a','prod_b'));fresh=evaluate(d,('new_a','new_b'))
        runs={t:evaluate(d,(t,))for t in ('new_a','new_b')}
        pcov=SP**2 if d==2 else 0
        denom=(prev['sampling_standard_error']**2+fresh['sampling_standard_error']**2-2*pcov)**.5
        denom2=(sum(r['sampling_standard_error']**2 for r in runs.values())-2*pcov)**.5
        x['previous']=prev;x['fresh_only']=fresh;x['fresh_campaigns']=runs;x['fresh_minus_old_pull']=(fresh['C6']-prev['C6'])/denom;x['fresh_campaign_pull']=(runs['new_a']['C6']-runs['new_b']['C6'])/denom2
        x['precision_improvement']=prev['sampling_standard_error']/x['sampling_standard_error']
        allout[str(d)]=x
        print(d,'C6',x['C6'],'SE',x['sampling_standard_error'],'old',prev['C6'],prev['sampling_standard_error'],'fresh',fresh['C6'],fresh['sampling_standard_error'],'gain',x['precision_improvement'],'pieces',x['error_by_loop'],'common',x['shared_input_standard_error'],'lower',x['lower_order_checks'],flush=True)
    (W/'verification/method_precision_results.json').write_text(json.dumps(allout,indent=2))
if __name__=='__main__':main()
