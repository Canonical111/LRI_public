from driver import *
from analysis import F,jacobians
# Training data and old records are frozen now. Production tags below are unused.
old=json.load(open(B/'verification/precision_results.json'))
forest=json.load(open(B/'baseline/lri_C6_d3_complete_update/inputs/powerfree_forests.json'))
allplans=[]
for d in (2,3):
    means={int(L):np.array(a)for L,a in old[str(d)]['pooled_jet_means'].items()};J=jacobians(d,means)
    for L in range(3,7):
        _,rows=graph_ids(B/f'baseline/lri_C6_d3_complete_update/inputs/forest_L{L}.txt');ids=[r[0]for r in rows]
        # Independent graph replicate variances, multiplied by point count.
        if L==6:
            tags=['validation_grid0','validation_grid11'] if d==2 else ['validation_grid0','validation_grid3']
            datasets=[json.load(open(W/f'records/{tag}_d{d}_L6.json')) for tag in tags]
        else:
            datasets=[json.load(open(B/f'records/{tag}_d{d}_L{L}.json')) for tag in ['prod_a','prod_b']]
        vv=[];cc=[]
        for data in datasets:
            ar=np.array(data['graph_batches']);y=ar@J[L][6];nn=np.array(data['counts_per_replicate'],dtype=float)
            vv.append(y.var(axis=0,ddof=1)*nn)
            if 'graph_cpu_seconds'in data:cc.append(np.array(data['graph_cpu_seconds'])/(nn*data['replicates']))
        var=np.mean(vv,axis=0)
        # For lower loops use structural operation counts, calibrated only in relative cost.
        cost=np.mean(cc,axis=0) if cc else np.array([12*L+0.7*r[3]+r[4]*(2*L+6) for r in rows],dtype=float)
        cost=np.maximum(cost,np.median(cost)*.1)
        oldprobs=np.array([json.load(open(B/f'inputs/production_d{d}_L{L}.json'))['probabilities'][str(i)] for i in ids])
        budget={3:131072,4:262144,5:1048576,6:4194304}[L]
        excluded=[]
        if d==2 and L==6:
            excluded=[i for i in ids if len(forest[f'L6G{i+1:03d}'])==1]
            assert len(excluded)==10
        active=np.array([i not in excluded and (L!=6 or abs(-r[1]+3*r[2])>1e-14) for i,r in zip(ids,rows)])
        var=np.where(active,var,0)
        score=np.sqrt(np.maximum(var,0)/cost)
        # The objective is fixed predicted CPU, not a fixed total point count.
        targetcost=np.dot(cost,oldprobs*budget)
        scale=targetcost/np.dot(cost,score)
        raw=scale*score
        counts=np.where(active,np.maximum(8,2**np.rint(np.log2(np.maximum(raw,8)))),0).astype(np.int64)
        # Numerical exact-zero influences in lower loops are kept at a small count for checks.
        if L<6:counts=np.maximum(counts,8)
        path=W/f'inputs/frozen_d{d}_L{L}.json'
        record={'dimension':d,'L':L,'budget_label':budget,'counts':dict(zip(map(str,ids),map(int,counts))), 'excluded_primitive_ids':excluded,'source_datasets':[str(x) for x in tags] if L==6 else ['previous prod_a','previous prod_b'],'criterion':'MC-variance-model Neyman allocation with per-point cost; model, not a QMC optimality theorem','variance_parameters':var.tolist(),'relative_costs':cost.tolist(),'predicted_cpu_ratio_to_old_allocation':float(np.dot(cost,counts)/targetcost),'jacobian':J[L][6].tolist(),'actual_points_per_replicate':int(sum(counts))}
        path.write_text(json.dumps(record,indent=2))
        for campaign in ['new_a','new_b']:
            allplans.append({'tag':campaign,'d':d,'L':L,'replicates':32,'seed':int((881709317 if campaign=='new_a'else 1298743317)+d*110001+L*173),'layout':0,'rate_factor':1,'antithetic':False,'grid':str(W/'inputs/grid_d2_top11.txt') if d==2 and L==6 and campaign=='new_a'else None,'counts_file':str(path),'bits':52 if campaign=='new_a'else 60})
        print(d,L,'counts/rep',sum(counts),'predcostratio',record['predicted_cpu_ratio_to_old_allocation'],flush=True)
(W/'inputs/frozen_production_plan.json').write_text(json.dumps({'plan':allplans,'combination_weights':{'previous_prod_a':.25,'previous_prod_b':.25,'new_a':.25,'new_b':.25},'d2_primitive_mean':718.7129769223133,'d2_primitive_se':.041404328278345545,'d2_old_66_weight':.5,'d2_new_66_weight':.5,'pilots_excluded_from_estimator':True,'date':'2026-09-14'},indent=2))
