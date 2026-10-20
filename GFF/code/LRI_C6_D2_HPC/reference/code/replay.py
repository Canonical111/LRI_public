"""Replay delivered digital matrices without regenerating a scramble.
Usage: python code/replay.py new_a 2 4 check_replay --replicates 2
"""
from pathlib import Path
import argparse,json,os,struct,subprocess,time
W=Path(__file__).resolve().parents[1];B=W/'baseline_previous'
p=argparse.ArgumentParser();p.add_argument('tag');p.add_argument('d',type=int,choices=[2,3]);p.add_argument('L',type=int,choices=[3,4,5,6]);p.add_argument('output_tag');p.add_argument('--replicates',type=int);a=p.parse_args()
ref=json.load(open(W/f'records/{a.tag}_d{a.d}_L{a.L}.json'))
nf=W/f'inputs/{a.tag}_d{a.d}_L{a.L}_net.bin';bb=nf.read_bytes();R,dim,bits=struct.unpack('<III',bb[:12]);r=a.replicates or R
if not 2<=r<=R:raise ValueError('replicates must lie between 2 and original count')
newnet=W/f'inputs/{a.output_tag}_d{a.d}_L{a.L}_net.bin';newnet.write_bytes(struct.pack('<III',r,dim,bits)+bb[12:12+r*dim*bits*8])
out=W/f'records/{a.output_tag}_d{a.d}_L{a.L}.json'
if out.exists():raise FileExistsError(out)
source=B/f'baseline/lri_C6_d3_complete_update/inputs/forest_L{a.L}.txt'
rates=B/f'baseline/lri_C6_d3_complete_update/inputs/rates_L{a.L}_0.8.txt' if a.d==3 else (B/'inputs/d2_full_rates_c6.txt'if a.L==6 else B/f'baseline/lri_C6_d2_complete_update/reproduction/mom_rates_c{a.L}.txt')
env=dict(os.environ);env.pop('GRID_FILE',None);env.pop('PREFIX_STRATA',None);env.pop('TRAIN_HIST',None)
if a.tag=='new_a' and a.d==2 and a.L==6:env['GRID_FILE']=str(W/'inputs/grid_d2_top11.txt')
cmd=[str(W/f'code/experiment_d{a.d}'),str(source),str(rates),str(W/f'inputs/{a.tag}_d{a.d}_L{a.L}_counts.txt'),str(ref['seed']),str(newnet),str(out),str(B/f'inputs/gamma_d{a.d}.txt'),ref['method'],str(ref['layout']),str(int(ref['antithetic'])),str(ref['rate_factor'])]
t=time.time();subprocess.run(cmd,check=True,env=env)
import numpy as np
fresh=json.load(open(out));x=np.array(fresh['graph_batches']);y=np.array(ref['graph_batches'])[:r]
result={'tag':a.tag,'d':a.d,'L':a.L,'replicates':r,'elapsed_seconds':time.time()-t,'samples':fresh['N'],'max_absolute_graph_replicate_difference':float(np.max(abs(x-y))),'max_normalized_graph_replicate_difference':float(np.max(abs(x-y)/(1+abs(y))))}
(W/f'verification/{a.output_tag}_d{a.d}_L{a.L}.json').write_text(json.dumps(result,indent=2));print(result)
