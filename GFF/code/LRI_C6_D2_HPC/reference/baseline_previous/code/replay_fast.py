import json,subprocess,time,numpy as np
from pathlib import Path
from analysis import W,F,jacobians
rows=[]
for d in (2,3):
 before={};after={}
 for L in range(3,7):
  source=W/f'baseline/lri_C6_d3_complete_update/inputs/forest_L{L}.txt'
  if d==3:rates=W/f'baseline/lri_C6_d3_complete_update/inputs/rates_L{L}_0.8.txt'
  elif L==6:rates=W/'inputs/d2_full_rates_c6.txt'
  else:rates=W/f'baseline/lri_C6_d2_complete_update/reproduction/mom_rates_c{L}.txt'
  out=W/f'records/fast_replay_d{d}_L{L}.json';seed=(14798021 if d==2 else 43672819)+1279*L
  cmd=[str(W/f'code/stratified_d{d}_fast'),str(source),str(rates),str(W/f'inputs/pilot_d{d}_L{L}_counts.txt'),str(seed),str(W/f'inputs/pilot_d{d}_L{L}_net.bin'),str(out),str(W/f'inputs/gamma_d{d}.txt'),'rqmc']
  t=time.time()
  with open(W/f'logs/fast_replay_d{d}_L{L}.log','w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
  a=np.array(json.load(open(W/f'records/pilot_d{d}_L{L}.json'))['batches']);b=np.array(json.load(open(out))['batches']);before[L]=a.mean(0);after[L]=b.mean(0)
  rows.append({'d':d,'L':L,'samples':json.load(open(out))['N'],'max_abs_jet_difference':float(np.max(abs(a-b))),'seconds':time.time()-t});print(rows[-1],flush=True)
 delta=F[d](after)-F[d](before);assert max(abs(delta[3:]))<1e-7
 rows.append({'d':d,'coefficient_difference':delta.tolist()});print('COEFFICIENT DELTA',d,delta,flush=True)
(W/'verification/fast_replay.json').write_text(json.dumps(rows,indent=2))
