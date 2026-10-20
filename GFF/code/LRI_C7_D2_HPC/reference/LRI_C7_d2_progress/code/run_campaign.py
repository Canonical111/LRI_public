#!/usr/bin/env python3
from pathlib import Path
import json,argparse,subprocess,time,math
W=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('tag');ap.add_argument('--replicates',type=int,default=8);ap.add_argument('--points',type=int,default=128);ap.add_argument('--loops',type=int,nargs='+',default=list(range(3,8)));ap.add_argument('--rate',default='.8');ap.add_argument('--seed',default='10298421');ap.add_argument('--allocation',type=Path);ap.add_argument('--primitive',action='store_true');ap.add_argument('--nonprimitive',action='store_true');ap.add_argument('--net',default='pilot');ap.add_argument('--block',type=int,default=80);ap.add_argument('--threads',default='4');a=ap.parse_args()
out=W/'records'/a.tag;out.mkdir(exist_ok=True);result=[];t0=time.monotonic();alloc=json.load(open(a.allocation))if a.allocation else None
for L in a.loops:
 inv=json.load(open(W/f'inputs/L{L}/inventory.json'))
 rows=[g for g in inv if g['status']=='finite-kernel'and(not a.primitive or g['primitive'])and(not a.nonprimitive or not g['primitive'])and(L<7 or g['mass_numerator']!=4)]
 for off in range(0,len(rows),a.block):
  group=rows[off:off+a.block];tasks=[]
  for rep in range(a.replicates):
   for g in group:
    n=int(alloc[str(L)][str(g['id'])])if alloc else a.points
    if n>0:tasks.append((len(tasks),rep,g['id'],0,n,n))
  path=out/f'L{L}_block{off:04d}';taskpath=path.with_suffix('.tasks');dest=path.with_suffix('.json')
  if dest.exists():result.append(str(dest.relative_to(W)));continue
  taskpath.write_text(f'C7D2TASKS1 {L} {len(tasks)}\n'+'\n'.join(' '.join(map(str,r))for r in tasks)+'\n')
  cmd=[str(W/'code/c7d2_integrate'),str(W/'inputs'),str(W/'inputs/gamma_d2_7.txt'),str(W/f'inputs/{a.net}_L{L}.net'),str(taskpath),str(dest),a.seed,'0',a.rate,a.threads,'compensated','-']
  with open(path.with_suffix('.log'),'w')as f:subprocess.run(cmd,stdout=f,stderr=f,check=True)
  result.append(str(dest.relative_to(W)));print(a.tag,'L',L,off,'of',len(rows),'elapsed',time.monotonic()-t0,flush=True)
meta=dict(tag=a.tag,args={k:str(v)if isinstance(v,Path)else v for k,v in vars(a).items()},records=result,seconds=time.monotonic()-t0)
(out/'manifest.json').write_text(json.dumps(meta,indent=2))
