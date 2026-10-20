"""Reassemble independent production RQMC replicates. Pilot-only adaptation.
The known 2D 76-kernel uncertainty is common to every production campaign.
No known physical C3--C5 value is used to fit, calibrate or select an estimate.
"""
import json,sys
from pathlib import Path
import numpy as np
from analysis import W,F,jacobians
K=json.load(open(W/'baseline/lri_C6_d2_complete_update/reproduction/mom_known_sectors.json'))
REF={2:np.array([-0.8748500126526336895,5.0488684313548,-38.8336458962282]),3:np.array([-0.3535815204331724,1.22806354532762308,-5.85035142075])}
def load(d,tag):
 raw={L:json.load(open(W/f'records/{tag}_d{d}_L{L}.json'))for L in range(3,7)};ar={L:np.array(v['batches'])for L,v in raw.items()}
 if d==2:
  ids=raw[6]['graph_ids'];sel=np.array([i not in K['excluded_graph_ids']for i in ids]);assert len(set(ids)&set(K['excluded_graph_ids']))==76
  ar[6]=np.array(raw[6]['graph_batches'])[:,sel,:].sum(1)
 return raw,ar

def eval_arrays(d,ar):
 means={L:a.mean(0)for L,a in ar.items()};J=jacobians(d,means);covs={L:np.cov(a,rowvar=False,ddof=1)/len(a)for L,a in ar.items()};cov=sum(J[L]@cv@J[L].T for L,cv in covs.items());coef=F[d](means)
 if d==2:coef[6]+=K['mean'];cov[6,6]+=K['se']**2
 return {'coefficients':coef.tolist(),'sampling_se':np.sqrt(np.maximum(0,np.diag(cov))).tolist(),'covariance':cov.tolist()}

def summarize(d,tags=('prod_a','prod_b'),write=True):
 data={tag:load(d,tag)for tag in tags};ar={tag:a for tag,(r,a)in data.items()};weights=np.ones(len(tags))/len(tags)
 means={L:sum(w*ar[tag][L].mean(0)for w,tag in zip(weights,tags))for L in range(3,7)};J=jacobians(d,means)
 jcov={L:sum(w*w*np.cov(ar[tag][L],rowvar=False,ddof=1)/len(ar[tag][L])for w,tag in zip(weights,tags))for L in means}
 cvparts={L:J[L]@jcov[L]@J[L].T for L in means};cov=sum(cvparts.values());mu=F[d](means);known=0
 if d==2:mu[6]+=K['mean'];cov[6,6]+=K['se']**2;known=K['se']
 se=np.sqrt(np.maximum(0,np.diag(cov)));runs={tag:eval_arrays(d,a)for tag,a in ar.items()}
 # Nonlinear bias: delete one independent replicate from one loop/campaign at a time.
 bias=np.zeros(7)
 for w,tag in zip(weights,tags):
  for L,a in ar[tag].items():
   n=len(a);leaves=[]
   for row in a:
    m={k:v.copy()for k,v in means.items()};m[L]+=w*(a.mean(0)-row)/(n-1);c=F[d](m)
    if d==2:c[6]+=K['mean']
    leaves.append(c)
   bias+=(n-1)*(np.mean(leaves,axis=0)-mu)
 # The known76 component is identical in paired diagnostics and cancels from their differences.
 half=[]
 for h in (0,1):
  m={L:sum(w*np.array_split(ar[tag][L],2)[h].mean(0)for w,tag in zip(weights,tags))for L in means};c=F[d](m)
  if d==2:c[6]+=K['mean']
  half.append(c.tolist())
 pulls=[]
 if len(tags)==2:
  a,b=[runs[t]for t in tags];den=(a['sampling_se'][6]**2+b['sampling_se'][6]**2-2*known**2)**.5
  pulls.append((a['coefficients'][6]-b['coefficients'][6])/den)
 # Normalized replicate influences expose isolated large-tail observations.
 diagnostics={}
 for tag in tags:
  diagnostics[tag]={}
  for L,a in ar[tag].items():
   inf=(a-a.mean(0))@J[L][6];sd=inf.std(ddof=1);v2=inf**2
   diagnostics[tag][str(L)]={'max_abs_standardized':float(np.max(abs(inf))/sd),'max_variance_fraction':float(max(v2)/sum(v2)),'skewness':float(np.mean((inf/sd)**3)),'excess_kurtosis':float(np.mean((inf/sd)**4)-3)}
 out={'dimension':d,'epsilon':f'2s-{d}','C6':float(mu[6]),'sampling_standard_error':float(se[6]),'coefficients':mu.tolist(),'standard_errors':se.tolist(),'coefficient_covariance':cov.tolist(),'weights':dict(zip(tags,weights.tolist())),'weight_rule':'Equal independent campaigns fixed before production; each has 64 independent randomized nets per loop.','runs':runs,'known76_common_uncertainty':known,'known76_record':K if d==2 else None,'error_by_loop':{str(L):float(max(0,c[6,6])**.5)for L,c in cvparts.items()},'pooled_jet_means':{str(L):a.tolist()for L,a in means.items()},'pooled_jet_covariances':{str(L):a.tolist()for L,a in jcov.items()},'nonlinear_jackknife_bias_estimate':bias.tolist(),'half_run_coefficients':half,'campaign_difference_pulls':pulls,'lower_order_checks':[{'order':i+3,'estimate':float(mu[i+3]),'se':float(se[i+3]),'reference':float(ref),'pull':float((mu[i+3]-ref)/se[i+3])}for i,ref in enumerate(REF[d])],'replicate_influence_diagnostics':diagnostics,'samples':{tag:{str(L):r['N']for L,r in raw.items()}for tag,(raw,a)in data.items()},'fallbacks':{tag:{str(L):{k:r[k]for k in ('quad_fallbacks','mp_fallbacks')}for L,r in raw.items()}for tag,(raw,a)in data.items()},'pilot_or_validation_samples_in_estimator':False,'lower_physical_coefficients_used_as_controls':False,'independent_field_theory_rederivation':False,'power_sector_correction':'Retained separately audited correction from original result, negligible at current sampling precision; not rerun here.'}
 if write:(W/f'verification/precision_d{d}_{"_".join(tags)}.json').write_text(json.dumps(out,indent=2))
 return out
if __name__=='__main__':
 tags=tuple(sys.argv[1:])or('prod_a','prod_b')
 for d in (2,3):
  try:
   v=summarize(d,tags);print(d,'C6',v['C6'],'SE',v['sampling_standard_error'],'loops',v['error_by_loop'],'controls',v['lower_order_checks'],'bias',v['nonlinear_jackknife_bias_estimate'][6],flush=True)
  except (FileNotFoundError,json.JSONDecodeError)as e:print('not ready',d,str(e))
