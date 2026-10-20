"""Independent common-random-number pilot; no physical C6 relation assumed."""
from driver import *
import os
for e in ['GRID_FILE','TRAIN_HIST','PREFIX_STRATA']:os.environ.pop(e,None)
K=json.load(open(B/'baseline/lri_C6_d2_complete_update/reproduction/mom_known_sectors.json'))
forest=json.load(open(B/'baseline/lri_C6_d3_complete_update/inputs/powerfree_forests.json'))
groups=[[i for i in K['excluded_graph_ids']if len(forest[f'L6G{i+1:03d}'])==n]for n in [1,2,4]]
base=json.load(open(W/'inputs/frozen_d3_L6.json'))['counts'];keep=set(K['excluded_graph_ids']);total=sum(n for i,n in base.items()if int(i)in keep)
counts={i:(max(16,2**round(np.log2(max(16,n*65536/total))))if int(i)in keep else 0)for i,n in base.items()}
for d in [2,3]:run('cross_train',d,6,counts,32,1749107361,0,1,False,'rqmc',False,60)
def group_arrays(tag,d):
    x=json.load(open(W/f'records/{tag}_d{d}_L6.json'));a=np.array(x['graph_batches'])@np.array([-1.,3.])/2187
    return np.column_stack([a[:,np.array([i in g for i in x['graph_ids']])].sum(1)for g in groups])
y2=group_arrays('cross_train',2);y3=group_arrays('cross_train',3)
beta=np.array([np.cov(y2[:,i],y3[:,i],ddof=1)[0,1]/y2[:,i].var(ddof=1)for i in range(3)])
co={str(i):np.corrcoef(y2[:,i],y3[:,i])[0,1]for i in range(3)}
record={'beta':beta.tolist(),'groups':groups,'references':K['group_means'],'reference_standard_errors':K['group_sampling_ses'],'training':'cross_train','correlations':co,'rule':'Separate group control coefficients fitted only on this independent paired pilot; never fitted to production samples.'}
(W/'inputs/cross_control_frozen.json').write_text(json.dumps(record,indent=2));print('TRAINED',record,flush=True)
for d in [2,3]:run('cross_validate',d,6,{k:v*2 for k,v in counts.items()},32,1937451133,0,1,False,'rqmc',False,52)
y2=group_arrays('cross_validate',2);y3=group_arrays('cross_validate',3);res=y3-y2*beta
out={'training':record,'validation_replicates':32,'uncorrected_var_per_replicate':float(y3.sum(1).var(ddof=1)),'controlled_var_per_replicate':float(res.sum(1).var(ddof=1)), 'variance_ratio':float(res.sum(1).var(ddof=1)/y3.sum(1).var(ddof=1)), 'group_variance_ratios':(res.var(0,ddof=1)/y3.var(0,ddof=1)).tolist(),'reference_floor_if_full_control':float(np.linalg.norm(beta*np.array(K['group_sampling_ses']))),'validation_controlled_minus_reference_known_data_note':'Controls are noisy estimates; their uncertainty must be added once. Pilot and validation are not production.'}
(W/'verification/cross_dimension_validation.json').write_text(json.dumps(out,indent=2));print('VALIDATION',out,flush=True)
