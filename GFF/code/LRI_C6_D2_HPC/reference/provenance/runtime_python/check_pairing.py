from pathlib import Path
import json,subprocess,struct,os
import numpy as np
W=Path(__file__).resolve().parents[1];B=W/'baseline_previous'
plan=json.load(open(W/'inputs/cross_primitive_production_plan.json'));ids=set(plan['primitive_ids']);checks=[]
for tag in ['prod_b','new_a']:
 root=B if tag.startswith('prod')else W;ref=json.load(open(root/f'records/{tag}_d3_L6.json'));nb=root/f'inputs/{tag}_d3_L6_net.bin';bb=nb.read_bytes();R,dim,bits=struct.unpack('<III',bb[:12]);net=W/f'inputs/check_pair_{tag}_net.bin';net.write_bytes(struct.pack('<III',2,dim,bits)+bb[12:12+2*dim*bits*8])
 count=W/f'inputs/check_pair_{tag}_counts.txt';count.write_text(str(len(ref['graph_ids']))+'\n'+'\n'.join(f'{i} {n if i in ids else 0}'for i,n in zip(ref['graph_ids'],ref['counts_per_replicate']))+'\n');out=W/f'records/check_pair_{tag}_d3.json'
 if out.exists():raise FileExistsError(out)
 env=dict(os.environ)
 for e in ['GRID_FILE','TRAIN_HIST','PREFIX_STRATA']:env.pop(e,None)
 cmd=[str(W/'code/experiment_d3'),str(B/'baseline/lri_C6_d3_complete_update/inputs/forest_L6.txt'),str(B/'baseline/lri_C6_d3_complete_update/inputs/rates_L6_0.8.txt'),str(count),str(ref['seed']),str(net),str(out),str(B/'inputs/gamma_d3.txt'),'rqmc',str(2 if tag=='prod_b'else 0),'0','1']
 subprocess.run(cmd,check=True,env=env)
 a=json.load(open(out));sel=np.array([i in ids for i in ref['graph_ids']]);x=np.array(a['graph_batches'])[:,sel,:];y=np.array(ref['graph_batches'])[:2,sel,:];err=float(np.max(abs(x-y)/(1+abs(y))));assert err<1e-10
 checks.append({'tag':tag,'samples':a['N'],'paired_graphs':sum(sel).item(),'replicates':2,'max_normalized_graph_replay_error':err,'max_absolute_graph_replay_error':float(np.max(abs(x-y)))})
(W/'verification/pairing_checks.json').write_text(json.dumps(checks,indent=2));print(checks)
