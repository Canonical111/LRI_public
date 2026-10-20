"""Frozen primitive-only dimension-coupled control; old d3 samples are reused.
No relation between physical coefficients in different dimensions is assumed.
"""
from pathlib import Path
import json,os,time,subprocess,hashlib
W=Path(__file__).resolve().parents[1];B=W/'baseline_previous'
train=json.load(open(W/'inputs/cross_control_frozen.json'));val=json.load(open(W/'verification/cross_dimension_validation.json'))
plan={'beta':train['beta'][0],'groups_used':[0],'primitive_ids':train['groups'][0],'reference':train['references'][0],'reference_se':train['reference_standard_errors'][0],'campaign_weights':{'prod_a':.25,'prod_b':.25,'new_a':.25,'new_b':.25},'source_training':'cross_train','source_validation':'cross_validate','decision_rule':'Use group only when twice the independent-validation residual variance is below its plain variance. Only the primitive group passed. Coefficient comes from training, not production.','validation_ratio':val['group_variance_ratios'][0],'coefficients_fitted_to_production':False,'date':'2026-09-14'}
path=W/'inputs/cross_primitive_production_plan.json'
if path.exists():assert json.load(open(path))==plan
else:path.write_text(json.dumps(plan,indent=2))
(W/'verification/cross_plan_hash.json').write_text(json.dumps({'plan_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'beta_source_sha256':hashlib.sha256((W/'inputs/cross_control_frozen.json').read_bytes()).hexdigest()},indent=2))
ids=set(plan['primitive_ids']);manifest=[]
for tag in plan['campaign_weights']:
 root=B if tag.startswith('prod')else W
 source_record=root/f'records/{tag}_d3_L6.json'
 while not source_record.exists():time.sleep(2)
 j=json.load(open(source_record))
 out=W/f'records/paired_{tag}_d2_L6.json'
 if out.exists():raise FileExistsError(out)
 net=root/f'inputs/{tag}_d3_L6_net.bin';copied=W/f'inputs/paired_{tag}_d2_L6_net.bin';copied.write_bytes(net.read_bytes())
 counts=W/f'inputs/paired_{tag}_d2_L6_counts.txt';counts.write_text(str(len(j['graph_ids']))+'\n'+'\n'.join(f'{g} {n if g in ids else 0}'for g,n in zip(j['graph_ids'],j['counts_per_replicate']))+'\n')
 layout=j.get('layout',2 if tag=='prod_b'else 0)
 env=dict(os.environ)
 for e in ['GRID_FILE','PREFIX_STRATA','TRAIN_HIST']:env.pop(e,None)
 cmd=[str(W/'code/experiment_d2'),str(B/'baseline/lri_C6_d3_complete_update/inputs/forest_L6.txt'),str(B/'inputs/d2_full_rates_c6.txt'),str(counts),str(j['seed']),str(copied),str(out),str(B/'inputs/gamma_d2.txt'),'rqmc',str(layout),'0','1']
 t=time.time()
 with open(W/f'logs/paired_{tag}.log','w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,check=True)
 rec=json.load(open(out));row={'tag':tag,'samples':rec['N'],'seconds':time.time()-t,'command':cmd,'same_seed':rec['seed']==j['seed'],'same_net_sha256':hashlib.sha256(net.read_bytes()).hexdigest()==hashlib.sha256(copied.read_bytes()).hexdigest(),'target_source_record':str(source_record),'layout':layout}
 manifest.append(row);(W/'verification/cross_production_manifest.json').write_text(json.dumps(manifest,indent=2));print(row,flush=True)
