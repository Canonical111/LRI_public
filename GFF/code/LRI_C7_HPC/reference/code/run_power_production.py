from pathlib import Path
import os,sys,json,time,subprocess
W=Path(__file__).resolve().parents[1];mode=sys.argv[1];plans=[]
if mode=='coarseA':
 for L,ns in [(5,512),(6,256),(7,128)]:plans.append((L,1,ns,32,9183241+7351*L))
elif mode=='coarseB':
 for L,ns in [(5,512),(6,256),(7,128)]:plans.append((L,1,ns,16,18175231+6481*L))
elif mode=='refine3':
 for L,ns,B in [(5,128,32),(6,32,16),(7,4,16)]:
  for N in [1,3]:plans.append((L,N,ns,B,13824193+5129*L))
elif mode=='refine5':
 for L,ns,B in [(5,32,16),(6,8,16),(7,1,8)]:
  for N in [3,5]:plans.append((L,N,ns,B,8273149+5623*L))
elif mode=='refine6':
 for L,ns,B in [(5,8,8),(6,2,8),(7,1,4)]:
  for N in [5,6]:plans.append((L,N,ns,B,7215947+3583*L))
elif mode=='refine7':
 for L,ns,B in [(5,8,8),(6,2,8),(7,1,4)]:
  for N in [5,7]:plans.append((L,N,ns,B,7215947+3583*L))
else:raise ValueError(mode)
rows=[]
for L,N,ns,B,seed in plans:
 out=W/f'records/power_{mode}_L{L}_N{N}.json'
 if out.exists():continue
 cmd=[str(W/'code/coordinate_tree_integrate_safe'),str(W/'inputs'),str(L),str(N),str(ns),str(B),str(seed),str(out),'power','.8']
 t=time.time()
 with open(W/f'logs/power_{mode}_L{L}_N{N}.log','w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 rows.append(dict(L=L,N=N,command=cmd,seconds=time.time()-t));(W/f'records/power_{mode}_manifest.json').write_text(json.dumps(rows,indent=2))
