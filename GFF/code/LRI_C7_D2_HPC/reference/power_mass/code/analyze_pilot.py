from pathlib import Path
import json,numpy as np,sys
W=Path(__file__).resolve().parents[1];OLD=W.parent/'LRI_C7_d2_progress';sys.path.insert(0,str(OLD/'code'))
from analyze import coefficients,jacobians
base=json.load(open(OLD/'verification/C7_d2_progress_result.json'));bm={int(k):np.array(v)for k,v in base['jet_means'].items()}
pa={};means={};available=[]
for L in range(3,8):
 f=W/f'records/pilot_L{L}.json'
 if not f.exists():continue
 available.append(L);a=json.load(open(f));reps=sorted(set(r['rep']for r in a['rows']));v=np.zeros((len(reps),2*(8-L)))
 for r in a['rows']:v[r['rep']]+=np.array(r['values'],float)
 pa[L]=v;means[L]=v.mean(0)
pm={L:bm[L]+means.get(L,np.zeros_like(bm[L]))for L in bm};full=coefficients(pm);bare=coefficients(bm);delta=full-bare;J=jacobians(pm)
cov=sum(J[L]@np.cov(a,rowvar=False)@J[L].T/len(a)for L,a in pa.items());se=np.sqrt(np.maximum(0,np.diag(cov)))
res=dict(available=available,power_difference=delta.tolist(),power_sampling_se=se.tolist(),power_means={str(L):v.tolist()for L,v in means.items()},full_trial=(full+np.array([0]*7+[base['primitive']['mean']])).tolist(),status='EXPERIMENTAL mixed-forest MOM prescription; not accepted until analytic and lower-loop tests pass')
(W/'verification/mixed_pilot.json').write_text(json.dumps(res,indent=2));print('loops',available);print('delta',delta);print('powerse',se);print('trialfull',res['full_trial'])
