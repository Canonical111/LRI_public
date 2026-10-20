"""Freeze per-graph sampling allocations from disjoint pilot replicates."""
import json,sys
import numpy as np
from analysis import W,jacobians,base_module
for d in (2,3):
 pilot={L:json.load(open(W/f'records/pilot_d{d}_L{L}.json'))for L in range(3,7)}
 means={L:np.array(v['batches']).mean(0)for L,v in pilot.items()};J=jacobians(d,means)
 for L,p in pilot.items():
  ar=np.array(p['graph_batches']);nn=np.array(p['counts_per_replicate']);ids=p['graph_ids']
  # The target is the first-order influence on C6, not the separate beta/mass errors.
  influence=ar@J[L][6]
  scaled=np.std(influence,axis=0,ddof=1)*np.sqrt(nn)
  probabilities=.96*scaled/scaled.sum()+.04/len(ids)
  out={'dimension':d,'L':L,'source':'pilot','excluded_from_production_estimator':True,'target':'C6 influence variance','probabilities':dict(zip(map(str,ids),probabilities.tolist())),'gradient':J[L][6].tolist(),'pilot_scaled_sd':scaled.tolist()}
  (W/f'inputs/target_d{d}_L{L}.json').write_text(json.dumps(out,indent=2));print(d,L,'graphs',len(ids),'largest allocations',sorted(zip(ids,probabilities),key=lambda x:-x[1])[:3])
