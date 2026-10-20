"""Freeze a two-campaign power-sector production. Pilots are excluded."""
from pathlib import Path
import json,sys,subprocess,time,hashlib
W=Path(__file__).resolve().parents[1];OLD=W.parent/'LRI_C7_d2_progress';sys.path.insert(0,str(OLD/'code'))
from sobol_net import make_net
plan=json.load(open(W/'inputs/production_plan.json'));B=16
specs=[('powerA',738482951,98371163,'.8'),('powerB',932618475,83740517,'.9')]
if any((W/f"records/{tag}_L{L}.json").exists() for tag,_,_,_ in specs for L in range(3,8)):
 raise SystemExit("Production output already exists. Use a separate working copy with a fresh records directory; refusing to overwrite saved scientific data.")
manifest=dict(campaigns=[],allocation_sha256=hashlib.sha256((W/'inputs/production_plan.json').read_bytes()).hexdigest(),pilot_excluded=True)
commands=[]
for tag,seed,netseed,rate in specs:
 cc=dict(tag=tag,seed=seed,net_seed=netseed,rate=rate,replicates=B,loops=[])
 for L in range(3,8):
  net=W/f'inputs/{tag}_L{L}.net';make_net(net,B,4*L-1,52,netseed+L*7893)
  pl=plan['allocations'][str(L)];tf=W/f'records/{tag}_L{L}.tasks'
  with tf.open('w')as f:
   f.write(f'C7D2TASKS1 {L} {len(pl)*B}\n');uid=0
   for rep in range(B):
    for g,points in pl.items():f.write(f'{uid} {rep} {g} 0 {points} {points}\n');uid+=1
  out=W/f'records/{tag}_L{L}.json';cmd=[str(W/'code/integrate'),str(W/'inputs'),str(OLD/'inputs/gamma_d2_7.txt'),str(net),str(tf),str(out),str(seed),'0',rate,'4','compensated','-']
  cc['loops'].append(dict(loop=L,graphs=len(pl),points=B*sum(pl.values()),command=cmd,output=str(out.relative_to(W))));commands.append((tag,L,cmd))
 manifest['campaigns'].append(cc)
(W/'verification/production_manifest.json').write_text(json.dumps(manifest,indent=2))
# Run sequentially to keep the four available cores on one task family.
for tag,L,cmd in commands:
 print('START',tag,L,flush=True);st=time.time()
 with open(W/f'records/{tag}_L{L}.log','w')as log:subprocess.run(cmd,stdout=log,stderr=log,check=True)
 print('FINISH',tag,L,time.time()-st,flush=True)
