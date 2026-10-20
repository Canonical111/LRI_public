#!/usr/bin/env python3
"""Immutable, complete per-graph randomized replicate campaigns (d=3, order 7)."""
from pathlib import Path
import argparse,json,subprocess,time,hashlib,os,math
from sobol_net import make_net
W=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(a):
 out=W/'records'/a.tag;out.mkdir(exist_ok=True)
 inv=json.load(open(W/'inputs/inventory.json'));alloc=json.load(open(a.allocation))if a.allocation else None
 args={k:str(v)if isinstance(v,Path)else v for k,v in vars(a).items()};config=out/'config.json'
 if config.exists()and json.load(open(config))!=args:raise ValueError('Refuse changed campaign config')
 config.write_text(json.dumps(args,indent=2));records=[];t0=time.monotonic();evals=0
 for sector in a.sectors:
  for L in a.loops:
   rr=inv[sector][str(L)] if L!=2 else ([dict(id=0)]if sector=='free'else[])
   net=out/f'{sector}_L{L}.net'
   if not net.exists():make_net(net,a.replicates,4*L-1,52,a.seed+L*27403+(592731 if sector=='power'else 0))
   for off in range(0,len(rr),a.block):
    group=rr[off:off+a.block];tasks=[]
    for rep in range(a.replicates):
     for g in group:
      n=int(alloc[sector][str(L)][str(g['id'])])if alloc else a.points
      if n<=0 or n&(n-1):raise ValueError('every graph requires a full positive power-of-two net')
      tasks.append((len(tasks),rep,g['id'],0,n,n));evals+=n
    path=out/f'{sector}_L{L}_block{off:04d}';tp=path.with_suffix('.tasks');dest=path.with_suffix('.json');log=path.with_suffix('.log')
    text=f'C7D3TASKS1 {L} {len(tasks)}\n'+''.join(' '.join(map(str,r))+'\n'for r in tasks)
    if tp.exists()and tp.read_text()!=text:raise ValueError('changed tasks')
    tp.write_text(text)
    if not dest.exists():
     tmp=dest.with_suffix('.tmp');cmd=[str(W/'bin/c7d3_gmp'),str(W/'inputs'/sector),str(W/'inputs/gamma_d3_7.txt'),str(net),str(tp),str(tmp),str(a.seed+(348612 if sector=='power'else 0)),str(a.layout),str(a.rate),str(a.threads),'compensated','-']
     with log.open('w')as f:subprocess.run(cmd,stdout=f,stderr=f,check=True,env={**os.environ,'OMP_PROC_BIND':'false'})
     data=json.load(open(tmp));assert len(data['rows'])==len(tasks);tmp.rename(dest)
    records.append(dict(sector=sector,L=L,file=str(dest.relative_to(W)),sha256=sha(dest),net_sha256=sha(net),tasks_sha256=sha(tp)))
    print(a.tag,sector,L,off,'/',len(rr),'seconds',round(time.monotonic()-t0,2),flush=True)
 manifest=dict(args=args,records=records,evaluations=evals,seconds=time.monotonic()-t0,executable_sha256=sha(W/'bin/c7d3_gmp'),gamma_sha256=sha(W/'inputs/gamma_d3_7.txt'))
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2));return manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('tag');p.add_argument('--replicates',type=int,default=8);p.add_argument('--points',type=int,default=128);p.add_argument('--seed',type=int,required=True);p.add_argument('--rate',type=float,default=.8);p.add_argument('--layout',type=int,default=0);p.add_argument('--threads',type=int,default=4);p.add_argument('--loops',nargs='+',type=int,default=list(range(3,8)));p.add_argument('--sectors',nargs='+',default=['free','power']);p.add_argument('--allocation',type=Path);p.add_argument('--block',type=int,default=48);a=p.parse_args();run(a)
