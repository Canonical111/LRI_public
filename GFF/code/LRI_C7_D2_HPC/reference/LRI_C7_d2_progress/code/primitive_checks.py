from pathlib import Path
from fractions import Fraction as F
import json,networkx as nx,mpmath as m,numpy as np,sys
W=Path(__file__).resolve().parents[1];sys.path.insert(0,str(W/'code'));from analyze import read
old=json.load(open(W/'reference/primitive_completion.json'));og=[]
for r in old:
 g=nx.Graph();g.add_nodes_from(range(9));k=0
 for i in range(9):
  for j in range(i+1,9):
   if r['completion_key'][k]:g.add_edge(i,j)
   k+=1
 og.append(g)
rows=json.load(open(W/'inputs/L7/inventory.json'));mapping={};tot=[F(0)]*len(old)
for r in rows:
 if not r['primitive']:continue
 g=nx.Graph();g.add_nodes_from(range(9));g.add_edges_from(r['edges']);deg=dict(g.degree())
 for i in range(8):
  assert 4-deg[i] in(0,1)
  if deg[i]==3:g.add_edge(i,8)
 assert all(g.degree(i)==4 for i in g)
 matches=[j for j,h in enumerate(og)if nx.is_isomorphic(g,h)];assert len(matches)==1
 j=matches[0];mapping[r['id']]=j;tot[j]+=F(24,r['denominator'])
assert all(tot[j]==F(o['weightA'])for j,o in enumerate(old))
m.mp.dps=40
q=m.gamma(m.mpf('.25'))**8/(24*m.pi**4);a=m.gamma(m.mpf('.25'))**4
fminus=m.hyper([m.mpf('.25')]*2+[m.mpf('.5')]*2,[m.mpf('.75')]*2+[1],1)
fplus=m.hyper([m.mpf('.75')]*2+[m.mpf('.5')]*2,[m.mpf('1.25')]*2+[1],1)
bm=a*fminus;bp=64*m.pi**4/a*fplus;p4=(bm**2-bp**2)/(4*m.pi**3)
def Y(r):
 z=m.mpf(r)/8;v=z*(m.gamma(z+m.mpf('.25'))/m.gamma(z+m.mpf('.75')))**7
 return v*m.hyper([1,1+z]+[z+m.mpf('.25')]*7,[z]+[z+m.mpf('.75')]*7,-1)
y={r:Y(r)for r in[1,2,3,5,7]};s=m.sin(m.pi/8);c=m.cos(m.pi/8);x0=y[2];xp=c**7*y[3]-s**7*y[5];xm=c**7*y[1]+s**7*y[7]
p5=8/m.pi*(25*x0*x0-28*m.sqrt(2)*x0*(xp+xm)+18*(xp*xp+xm*xm)+28*xp*xm)
known={6:p4**2,7:(3*q)**3,12:3*q*p5}
refs={j:-2*m.mpf(str(tot[j]))*v/6561 for j,v in known.items()}
ar,per=read('primitiveA');B=len(ar[7]);blocks={j:sum((per[7][gid]@np.array([-1/6561,1/2187])for gid,k in mapping.items()if k==j),np.zeros(B))for j in range(len(old))}
checks=[]
for j,ref in refs.items():
 v=blocks[j];mean=v.mean();se=v.std(ddof=1)/B**.5;checks.append(dict(label=old[j]['label'],estimate=float(mean),reference=str(ref),sampling_se=float(se),pull=float((mean-float(ref))/se)))
res=sum(blocks[j]for j in range(len(old))if j not in known)+float(sum(refs.values()))
out=dict(dps=m.mp.dps,primitive_classes=44,completed_periods=14,mapping=mapping,exact_period_weights=list(map(str,tot)),Q2=str(q),P4_2=str(p4),P5_2=str(p5),product_checks=checks,primitive_raw_mean=float((ar[7]@np.array([-1/6561,1/2187])).mean()),primitive_with_exact_products_mean=float(res.mean()),primitive_with_exact_products_sampling_se=float(res.std(ddof=1)/B**.5),replicate_values=res.tolist(),known_product_contribution=str(sum(refs.values())),full_C7_2=None)
(W/'verification/primitive_completion_checks.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
