from pathlib import Path
import json,glob,math
W=Path(__file__).resolve().parents[1];d=json.load(open(W/'verification/analysis_pilot3.json'));cost={}
for p in(W/'records/pilot3').glob('L*_block*.json'):
 a=json.load(open(p));L=a['L']
 if L==2:continue
 for r in a['rows']:
  k=(L,r['graph']);v=cost.setdefault(k,[0.,0]);v[0]+=r['seconds'];v[1]+=r['end']-r['begin']
work=[]
for L,gg in d['graphs'].items():
 L=int(L);iv={g['id']:g for g in json.load(open(W/f'inputs/L{L}/inventory.json'))}
 for gi,r in gg.items():
  gi=int(gi)
  if L==7 and iv[gi]['primitive']:continue
  c=max(1e-7,cost[L,gi][0]/cost[L,gi][1]);var=max(1e-12,r['projected_sd']**2*128)
  work.append((L,gi,c,var))
target=50.;den=sum(math.sqrt(c*v)for L,gi,c,v in work)
def alloc(budget):
 ans={str(L):{}for L in range(3,8)}
 for L,gi,c,v in work:
  n=budget*math.sqrt(v/c)/den;n=max(16,min(262144,2**round(math.log2(max(1,n)))));ans[str(L)][str(gi)]=int(n)
 for g in json.load(open(W/'inputs/L7/inventory.json')):
  if g['primitive']:ans['7'][str(g['id'])]=0
 return ans
lo,hi=0,target
for _ in range(30):
 mid=(lo+hi)/2;ns=alloc(mid);costp=sum(c*ns[str(L)][str(gi)]for L,gi,c,v in work)
 if costp>target:hi=mid
 else:lo=mid
ns=alloc(lo);record=dict(pilot='pilot3',fresh_only=True,target_cpu_seconds_per_replicate=target,estimated_cpu_seconds_per_replicate=sum(c*ns[str(L)][str(gi)]for L,gi,c,v in work),points_per_replicate={L:sum(v.values())for L,v in ns.items()},counts=ns)
(W/'verification/frozen_allocation.json').write_text(json.dumps(record,indent=2));(W/'inputs/allocation.json').write_text(json.dumps(ns,indent=2));print(json.dumps({k:v for k,v in record.items()if k!='counts'},indent=2))
