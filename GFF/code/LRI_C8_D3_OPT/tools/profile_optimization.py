#!/usr/bin/env python3
"""Profile the archived baseline by precision tier; not a coefficient estimate."""
import json,pathlib,subprocess,struct,time
import numpy as np
from scipy.stats import qmc
p=pathlib.Path(__file__).resolve().parents[1];d=p/'verification/performance';d.mkdir(exist_ok=True)
s=json.load(open(p/'results/pilot_20261008/graph_statistics.json')); inv=json.load(open(p/'inputs/inventory.json'))
groups=[]
for l in (3,6,7,8):
 for sec in ('free','power'):
  rows=sorted(inv[sec][str(l)],key=lambda r:(r['cost'],r['id']))
  ids={rows[int((len(rows)-1)*q)]['id'] for q in (0,.5,.95,1)}
  ids.update(int(i) for i in sorted(s[sec][str(l)],key=lambda i:sum(x['cpu_seconds'] for x in s[sec][str(l)][i].values()),reverse=True)[:2])
  name=f'{sec}_L{l}';td=d/name;td.mkdir(exist_ok=True);dim=4*l-1;bits=52
  with (td/'net.bin').open('wb') as f:
   f.write(struct.pack('<III',4,dim,bits))
   for rep in range(4):f.write(qmc.Sobol(dim,scramble=True,bits=bits,seed=9158+rep+l)._sv.astype('<u8').tobytes())
  n=256 if l<8 else 128
  tasks=[[i,rep,g,0,n,n] for i,(rep,g) in enumerate((rep,g) for rep in range(4) for g in sorted(ids))]
  (td/'tasks').write_text(f'C8D3TASKS1 {l} {len(tasks)}\n'+''.join(' '.join(map(str,t))+'\n' for t in tasks))
  cmd=[str(p/'bin/c8d3_profile'),str(p/'inputs'/sec),str(p/'inputs/gamma_d3_8.txt'),str(td/'net.bin'),str(td/'tasks'),str(td/'profile.json'),'716397108621','0','.8','1','compensated','-']
  t0=time.time();cp=subprocess.run(['/usr/bin/time','-v',*cmd],capture_output=True,text=True,check=True);(td/'profile.log').write_text(cp.stderr)
  profile={}
  for ln in cp.stderr.splitlines():
   if ln.startswith('PROFILE '):_,label,ns,calls=ln.split();profile[label]={'seconds':int(ns)/1e9,'calls':int(calls)}
  row=dict(L=l,sector=sec,graphs=sorted(ids),points=n,replicates=4,profile=profile,wall=time.time()-t0)
  groups.append(row);json.dump(groups,open(d/'profile_summary.json','w'),indent=2);print(name,json.dumps(profile),flush=True)
