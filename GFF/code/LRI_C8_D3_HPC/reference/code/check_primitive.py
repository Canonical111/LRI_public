from pathlib import Path
import json,numpy as np,mpmath as m,sys
from analyze import load_campaign
m.mp.dps=65
W=Path(__file__).resolve().parents[1];tags=sys.argv[1:];ref=json.load(open(W/'reference/d3_primitive_values.json'))['values'];q,p4,p5=[m.mpf(ref[k].split('(')[1].split(' +')[0])for k in ['Q3','P4_3','P5_3']];mapping=json.load(open(W/'reference/primitive_completion.json'))['mapping']
targets={6:-2*m.mpf(18)*p4*p4/6561,7:-2*m.mpf(729)/4*q**3/6561,12:-2*m.mpf(162)*q*p5/6561};sets={int(k):{}for k in range(14)};prim=[]
for tag in tags:
 a,g,t,ma=load_campaign(tag);B=ma['args']['replicates'];pp=np.zeros(B)
 for period in sets:
  x=np.zeros(B)
  for gid,p in mapping.items():
   if p==period:
    v=np.array(g['free'][7][int(gid)],float);x+=(3*v[:,1]-v[:,0])/6561
  sets[period][tag]=x;pp+=x
 prim.append(pp)
out=dict(campaigns=tags,primitive_classes=44,completed_periods=14,primitive_mean=float(sum(v.mean()for v in prim)/len(tags)),primitive_sampling_se=float(sum(v.var(ddof=1)/len(v)for v in prim)**.5/len(tags)),products=[])
for period,ex in targets.items():
 xs=sets[period].values();mean=sum(v.mean()for v in xs)/len(tags);se=sum(v.var(ddof=1)/len(v)for v in xs)**.5/len(tags);out['products'].append(dict(period=period,estimate=float(mean),reference=float(ex),sampling_se=float(se),pull=float((mean-float(ex))/se)))
out['scope']='Product-period values are retained independent diagnostics, not substituted into production; primitive data already counted in the full estimator.'
(W/'verification/primitive_checks.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
