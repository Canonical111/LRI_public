"""Replay a recorded production job using shipped digital matrices exactly.

Usage: python code/run_from_saved_inputs.py prod_a 2 6 replay_name
The output tag must be new; this deliberately does not regenerate matrices.
"""
import argparse,json,subprocess,time
from pathlib import Path
W=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('campaign',choices=['prod_a','prod_b']);p.add_argument('d',type=int,choices=[2,3]);p.add_argument('L',type=int,choices=[3,4,5,6]);p.add_argument('output_tag');a=p.parse_args()
plan=json.load(open(W/'inputs/production_plan.json'));row=next(x for x in plan if x['tag']==a.campaign and x['d']==a.d and x['L']==a.L)
L=a.L;d=a.d;stem=f'{a.campaign}_d{d}_L{L}';out=W/f'records/{a.output_tag}_d{d}_L{L}.json'
if out.exists():raise RuntimeError('Refusing to overwrite '+str(out))
rates=W/f'baseline/lri_C6_d3_complete_update/inputs/rates_L{L}_0.8.txt'if d==3 else W/f'baseline/lri_C6_d2_complete_update/reproduction/mom_rates_c{L}.txt'
if d==2 and L==6:rates=W/'inputs/d2_full_rates_c6.txt'
cmd=[str(W/f'code/stratified_d{d}{"_single"if row["encoding"]=="single"else""}'),str(W/f'baseline/lri_C6_d3_complete_update/inputs/forest_L{L}.txt'),str(rates),str(W/f'inputs/{stem}_counts.txt'),str(row['seed']+1279*L),str(W/f'inputs/{stem}_net.bin'),str(out),str(W/f'inputs/gamma_d{d}.txt'),'rqmc']
t=time.time()
with (W/f'logs/{a.output_tag}_d{d}_L{L}.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
result=json.load(open(out));old=json.load(open(W/f'records/{stem}.json'))
import numpy as np
err=float(np.max(np.abs(np.array(result['batches'])-np.array(old['batches']))))
record={'command':cmd,'seconds':time.time()-t,'same_seed_exact_replay':True,'max_abs_replicate_difference':err,'note':'Different compiler/platform arithmetic can affect final roundoff; this is not an independent statistical observation.'}
(W/f'verification/{a.output_tag}_replay.json').write_text(json.dumps(record,indent=2));print(record)
