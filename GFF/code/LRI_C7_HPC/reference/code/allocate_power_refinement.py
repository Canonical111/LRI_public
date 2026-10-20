"""Freeze a fresh, graph-stratified degree-1/3 refinement allocation.
The old L7 refinement is training/validation only and is excluded from the final mean.
"""
from pathlib import Path
import json,numpy as np
W=Path(__file__).resolve().parents[1];L=7
ref=json.load(open(W/'verification/full_affine_assembly.json'));j=np.array(ref['loops']['7']['adjusted'])[7]
a=np.array(json.load(open(W/'records/power_refine3_L7_N3.json'))['graph_batches']);b=np.array(json.load(open(W/'records/power_refine3_L7_N1.json'))['graph_batches']);Y=(a-b)@j
rows=json.load(open(W/'inputs/power_rows_L7.json'))['rows'];zero=set(json.load(open(W/'verification/forest_polynomials.json.zero.json'))['7']);active=np.array([r['power'] and r['terms'] and abs(3*r['wb']-r['wa'])>1e-17 and r['id']not in zero for r in rows],dtype=bool);cost=np.array([max(8,r['terms'])for r in rows],float);s2=Y.var(0,ddof=1)*4
# Positive floor covers strata whose finite pilot happened to be constant.
floor=np.median(s2[active&s2.astype(bool)])*1e-4;s2[active]=np.maximum(s2[active],floor)
base=4*cost[active].sum();budget=base*1.5;weight=np.sqrt(s2/cost)
def counts(t):return np.where(active,np.maximum(1,np.rint(t*weight)),0).astype(int)
lo,hi=0.,1.
while (counts(hi)*cost).sum()<budget:hi*=2
for _ in range(70):
 mid=(lo+hi)/2
 if (counts(mid)*cost).sum()<budget:lo=mid
 else:hi=mid
ns=counts(lo);B=16
v=np.sum(s2[active]/ns[active])/B
info={'training_files':['power_refine3_L7_N1.json','power_refine3_L7_N3.json'],'training_L7_not_used_in_final_mean':True,'pilot_B':16,'pilot_ns':4,'new_B':B,'active':int(active.sum()),'sampled_trees_per_replicate':int(ns.sum()),'model_cost_ratio':float((ns*cost).sum()/base),'forecast_sampling_se':float(v**.5),'pilot_diag_se':float(np.sqrt(s2[active].sum()/4/16)),'maximum_ns':int(ns.max()),'counts':ns.tolist()}
(W/'verification/frozen_power_refinement_allocation.json').write_text(json.dumps(info,indent=2));(W/'inputs/power_refine3B_counts_L7.txt').write_text(str(len(ns))+'\n'+''.join(f'{i} {k}\n'for i,k in enumerate(ns)));print({k:v for k,v in info.items()if k!='counts'})
