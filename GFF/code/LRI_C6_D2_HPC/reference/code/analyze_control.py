"""Dimension-coupled primitive control, with uncertain reference carried once."""
from analyze import *

def controlled_arrays(tags):
    plan=json.load(open(W/'inputs/cross_primitive_production_plan.json'));beta=plan['beta']
    data={};aux={};diagnostics={}
    for tag in tags:
        raw,ar=load(3,tag);a=json.load(open(W/f'records/paired_{tag}_d2_L6.json'))
        assert a['seed']==raw[6]['seed'] and a['replicates']==raw[6]['replicates']
        p=np.array(a['batches'])@np.array([-1.,3.])/2187
        assert len(p)==len(ar[6])
        ix=[g in PIDS for g in raw[6]['graph_ids']]
        primitive=np.array(raw[6]['graph_batches'])[:,ix,:].sum(1)@np.array([-1.,3.])/2187
        res=primitive-beta*p
        diagnostics[tag]={'d3_primitive_mean':float(primitive.mean()),'d2_auxiliary_mean':float(p.mean()),'correlation':float(np.corrcoef(primitive,p)[0,1]),'primitive_variance_ratio':float(res.var(ddof=1)/primitive.var(ddof=1)),'control_correction':float(beta*(P-p.mean()))}
        # Auxiliary algebraic vector only: it is NOT a new physical RG coefficient.
        ar[6]=ar[6].copy();ar[6][:,1]-=729*beta*p
        data[tag]=ar;aux[tag]=a
    return plan,data,aux,diagnostics

def evaluate_control(tags=('prod_a','prod_b','new_a','new_b'),write=True):
    plan,data,aux,diagnostics=controlled_arrays(tags);beta=plan['beta'];ww=np.ones(len(tags))/len(tags)
    means={L:sum(w*data[t][L].mean(0)for t,w in zip(tags,ww))for L in range(3,7)}
    J=jacobians(3,means);jcov={L:sum(w*w*np.cov(data[t][L],rowvar=False,ddof=1)/len(data[t][L])for t,w in zip(tags,ww))for L in means}
    parts={L:J[L]@c@J[L].T for L,c in jcov.items()};cov=sum(parts.values());cov[6,6]+=(beta*SP)**2
    mu=F[3](means);mu[6]+=beta*P;se=np.sqrt(np.maximum(0,np.diag(cov)))
    plain=evaluate(3,tags,False)
    assert max(abs(np.array(plain['coefficients'])[:6]-mu[:6]))<1e-10
    direct=plain['C6']+sum(w*diagnostics[t]['control_correction']for t,w in zip(tags,ww))
    assert abs(direct-mu[6])<1e-9
    halves=[]
    for h in (0,1):
        mm={L:sum(w*np.array_split(data[t][L],2)[h].mean(0)for t,w in zip(tags,ww))for L in means};z=F[3](mm);z[6]+=beta*P;halves.append(z.tolist())
    out={'dimension':3,'epsilon':'2s-3','C6':float(mu[6]),'sampling_standard_error':float(se[6]),'coefficients':mu.tolist(),'standard_errors':se.tolist(),'covariance':cov.tolist(),'weights':dict(zip(tags,ww.tolist())),'beta':beta,'reference_mean':P,'reference_se':SP,'reference_contribution_se':abs(beta)*SP,'reference_weight_total':beta,'error_by_loop':{str(L):float(max(0,v[6,6])**.5)for L,v in parts.items()},'control_diagnostics':diagnostics,'plain_C6':plain['C6'],'plain_se':plain['sampling_standard_error'],'SE_improvement_over_plain':plain['sampling_standard_error']/se[6],'half_run_coefficients':halves,'control_adjusted_algebraic_means':{str(L):x.tolist()for L,x in means.items()},'jet_covariances':{str(L):x.tolist()for L,x in jcov.items()},'jet_interpretation':'A variance-reduced estimator representation, NOT physical RG Taylor coefficients. Original RG data are retained unchanged.','direct_control_correction_check':float(direct-mu[6]),'lower_order_checks':plain['lower_order_checks'],'auxiliary_samples':{t:x['N']for t,x in aux.items()},'cross_covariance_with_C6_d2_shared_reference_only':beta*SP**2,'controls_trained_on_production':False,'physical_coefficient_interpolation_in_dimension':False,'power_sector_audit_rerun':False}
    if write:(W/f'verification/cross_result_{"_".join(tags)}.json').write_text(json.dumps(out,indent=2))
    return out

def main():
    result=evaluate_control();result['fresh_campaigns']={t:evaluate_control((t,))for t in ['new_a','new_b']};result['fresh_only']=evaluate_control(('new_a','new_b'))
    result['previous_plain']=evaluate(3,('prod_a','prod_b'),False)
    result['precision_gain_over_previous']=result['previous_plain']['sampling_standard_error']/result['sampling_standard_error']
    aa,bb=[result['fresh_campaigns'][t]for t in ['new_a','new_b']]
    result['fresh_campaign_pull']=(aa['C6']-bb['C6'])/np.sqrt(aa['sampling_standard_error']**2+bb['sampling_standard_error']**2-2*(result['beta']*SP)**2)
    (W/'verification/controlled_precision_result.json').write_text(json.dumps(result,indent=2));print(result['C6'],result['sampling_standard_error'],'gain',result['precision_gain_over_previous'],'controlonlygain',result['SE_improvement_over_plain'],'diagnostics',result['control_diagnostics'],flush=True)
if __name__=='__main__':main()
