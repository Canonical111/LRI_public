from pathlib import Path
import json,sys,math,numpy as np
W=Path(__file__).resolve().parents[1];OLD=W.parent/'LRI_C7_d2_progress';sys.path.insert(0,str(OLD/'code'))
from analyze import jacobians
r=json.load(open(W/'verification/mixed_pilot.json'));b=json.load(open(OLD/'verification/C7_d2_progress_result.json'))
mean={L:np.array(b['jet_means'][str(L)])+np.array(r['power_means'][str(L)])for L in range(3,8)};J=jacobians(mean);plan={};rows=[]
for L in range(3,8):
 d=json.load(open(W/f'records/pilot_L{L}.json'));by={}
 for x in d['rows']:by.setdefault(x['graph'],[]).append(x)
 vals=[]
 for g,rr in by.items():
  v=np.array([z['values']for z in rr],float);pro=v@J[L][7];sd=pro.std(ddof=1);N=rr[0]['total'];c=sum(z['seconds']for z in rr)/(N*len(rr));vals.append((g,sd,N,c))
 arr=sum(np.array([z['values']for z in rr],float)for rr in by.values());print('L',L,'projected SE',(arr@J[L][7]).std(ddof=1)/len(arr)**.5,'pilot work',d['integration_seconds'],'fallbacks',sum(z['quad']for z in d['rows']),sum(z['mp']for z in d['rows']))
 # Target one pilot CPU budget per campaign and loop before floors and power-of-two rounding.
 cost=sum(N*c for g,sd,N,c in vals)*1
 alpha=[sd*sd*N for g,sd,N,c in vals];den=sum((a*c)**.5 for a,(g,sd,N,c)in zip(alpha,vals));pl={}
 for a,(g,sd,N,c)in zip(alpha,vals):
  raw=(a/max(c,1e-8))**.5*cost/max(den,1e-30);raw=max(64 if L>=6 else 1024, min(131072,raw));pl[str(g)]=2**int(math.ceil(math.log2(raw)))
 plan[str(L)]=pl
 rows.append(dict(loop=L,graphs=len(vals),points_per_replicate=sum(pl.values()),max_points=max(pl.values()),predicted_cpu_per_rep=sum(pl[str(g)]*c for g,sd,N,c in vals),counts=pl))
 print('top',sorted(vals,key=lambda r:r[1],reverse=True)[:5], '\nnewpoints',sum(pl.values()),'max',max(pl.values()))
out=dict(policy='pilot-only projected-variance/cost allocation, rounded up to powers of two; frozen before independent production',replicates_per_campaign=16,allocations=plan,loops=rows)
(W/'inputs/production_plan.json').write_text(json.dumps(out,indent=2))
