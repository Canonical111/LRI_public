"""Benchmark sampling efficiency separately from evaluator runtime."""
import json
from pathlib import Path
import numpy as np
W=Path(__file__).resolve().parents[1]
out={'target':'six-loop contribution (3c6-b6)/2187, with all finite kernels in pilot','variance_estimator':'sum of graph-stratum randomized-replicate sample variances divided by replicate count; benchmark only, final assembly uses full jet covariance','rows':{},'validation':{},'speed':{}}
def data(tag,d):return json.load(open(W/f'records/{tag}_d{d}_L6.json'))
def stats(x):
 ar=np.array(x['graph_batches'])@np.array([-1.,3.])/2187
 var=np.var(ar,axis=0,ddof=1).sum()/len(ar)
 return {'N':x['N'],'replicates':x['replicates'],'stratified_se':float(var**.5),'seconds':x['seconds'],'variance_time':float(var*x['seconds']),'method':x['method'],'layout':x['layout'],'rate_factor':x['rate_factor'],'antithetic':x['antithetic']}
for d in (2,3):
 rows={tag:stats(data('pilot_'+tag,d))for tag in ['base','radial','single','smooth6','smooth5','rate1','anti','mc']}
 base=rows['base']
 for tag,x in rows.items():
  x['variance_ratio']=x['stratified_se']**2/base['stratified_se']**2;x['variance_time_ratio']=x['variance_time']/base['variance_time']
 out['rows'][str(d)]=rows
 valid={tag:stats(data('validation_'+tag,d))for tag in ['grid0','grid3','grid11','prefix']}
 for tag,x in valid.items():
  x['relative_variance_per_evaluation']=(x['stratified_se']/valid['grid0']['stratified_se'])**2*x['N']/valid['grid0']['N']
  x['same_evaluator_as_baseline']=tag!='prefix'
 out['validation'][str(d)]=valid
 old=data('pilot_ref',d);new=data('speed_v2',d)
 aa=np.array(old['graph_batches']);bb=np.array(new['graph_batches']);maxnorm=float(np.max(abs(aa-bb)/(1+abs(aa))))
 out['speed'][str(d)]={'N':old['N'],'old_seconds':old['seconds'],'new_seconds':new['seconds'],'speedup':old['seconds']/new['seconds'],'max_abs_graph_batch_difference':float(np.max(abs(aa-bb))),'max_normalized_graph_batch_difference':maxnorm,'identical_seeds':old['seed']==new['seed'],'identical_counts':old['counts_per_replicate']==new['counts_per_replicate'],'identical_bits':old['bits']==new['bits'],'same_samples':True,'effect':'Runtime only; no reduction in the variance of an individual sample.'}
(W/'verification/method_benchmarks.json').write_text(json.dumps(out,indent=2))
for d in (2,3):
 print('d',d,'speed',out['speed'][str(d)])
 for tag,x in out['rows'][str(d)].items():print(tag,round(x['variance_ratio'],3),round(x['variance_time_ratio'],3))
 print('maps',{k:round(x['relative_variance_per_evaluation'],4)for k,x in out['validation'][str(d)].items()})
