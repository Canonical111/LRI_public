from pathlib import Path
import json,math,argparse
W=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--pilot',default='pilot');p.add_argument('--cpu-budget',type=float,default=60.);a=p.parse_args()
gg=json.load(open(W/'verification'/f'graphs_{a.pilot}.json'));work=[]
for s,loops in gg.items():
 for L,gs in loops.items():
  for g,r in gs.items():
   n=r['points']/r['replicates'];cost=max(1e-7,r['cpu_seconds']/r['points']);var=max(1e-18,r['projected_sd']**2*n)
   # A small baseline prevents a spuriously constant short pilot from omitting a graph.
   var=max(var,(0.01*abs(r['projected_mean']))**2)
   work.append((s,L,g,cost,var))
def get(b):
 den=sum(math.sqrt(c*v)for _,_,_,c,v in work);r={s:{str(L):{}for L in range(3,8)}for s in gg}
 for s,L,g,c,v in work:
  n=b*math.sqrt(v/c)/den;n=max(64,min(524288,2**round(math.log2(max(1,n)))));r[s][L][g]=int(n)
 return r
lo,hi=0,a.cpu_budget*2
for _ in range(40):
 mid=(lo+hi)/2;r=get(mid);cost=sum(c*r[s][L][g]for s,L,g,c,v in work)
 if cost>a.cpu_budget:hi=mid
 else:lo=mid
r=get(lo);totals={s:{L:sum(gs.values())for L,gs in loops.items()}for s,loops in r.items()};cost=sum(c*r[s][L][g]for s,L,g,c,v in work)
(W/'inputs/allocation.json').write_text(json.dumps(r,indent=2));out=dict(pilot=a.pilot,excluded_from_production=True,target_cpu_seconds_per_replicate=a.cpu_budget,estimated_cpu_seconds_per_replicate=cost,points_per_replicate=totals,estimated_independent_graph_se_48_replicates=math.sqrt(sum(v/r[s][L][g]for s,L,g,c,v in work)/48),policy='fixed before independent production; no error-dependent reweighting of campaigns')
(W/'verification/frozen_allocation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
