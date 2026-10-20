import json,numpy as np
from analysis import W,jacobians
from run_precision import graph_ids
known=json.load(open(W/'baseline/lri_C6_d2_complete_update/reproduction/mom_known_sectors.json'))
for d in (2,3):
 srcs=['validation','sector_test'];raw={tag:{L:json.load(open(W/f'records/{tag}_d{d}_L{L}.json'))for L in range(3,7)}for tag in srcs}
 means={L:np.mean([np.array(raw[tag][L]['batches']).mean(0)for tag in srcs],axis=0)for L in range(3,7)};J=jacobians(d,means)
 for L in range(3,7):
  ids=raw[srcs[0]][L]['graph_ids'];v=[]
  for tag in srcs:
   p=raw[tag][L];a=np.array(p['graph_batches'])@J[L][6];n=np.array(p['counts_per_replicate']);v.append(np.var(a,axis=0,ddof=1)*n)
  scaled=np.sqrt(np.mean(v,axis=0));eligible=np.ones(len(ids),bool)
  if d==2 and L==6:eligible=np.array([i not in known['excluded_graph_ids']for i in ids])
  scaled[~eligible]=0
  probs=.96*scaled/scaled.sum()+.04*eligible/eligible.sum()
  out={'dimension':d,'L':L,'sources':srcs,'excluded_from_production_estimator':True,'target':'C6 first-order influence variance','probabilities':dict(zip(map(str,ids),probs.tolist())),'gradient':J[L][6].tolist(),'substitution_known76':bool(d==2 and L==6),'excluded_ids':np.array(ids)[~eligible].tolist()}
  (W/f'inputs/production_d{d}_L{L}.json').write_text(json.dumps(out,indent=2))
# Production counts are fixed before any production result is inspected.
plan=[]
for tag,seedbase,bits,encoding in [('prod_a',2609141701,52,'original'),('prod_b',7406113921,60,'single')]:
 for d in (2,3):
  for L,budget in [(3,65536),(4,131072),(5,524288),(6,1048576)]:
   plan.append({'tag':tag,'d':d,'L':L,'seed':seedbase+230119*d,'replicates':64,'budget':budget,'bits':bits,'encoding':encoding,'allocation':'production','rate':'0.8'})
(W/'inputs/production_plan.json').write_text(json.dumps(plan,indent=2))
print('Plan written',len(plan),'loop jobs')
