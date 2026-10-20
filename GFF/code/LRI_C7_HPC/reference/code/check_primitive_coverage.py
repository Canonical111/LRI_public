from pathlib import Path
from fractions import Fraction as F
from math import factorial
import json,networkx as nx
W=Path(__file__).resolve().parents[1]
retained=W/'retained/primitive_completion.json'
old=json.load(open(retained));oldgraphs=[]
for r in old:
 g=nx.Graph();g.add_nodes_from(range(9));k=0
 for i in range(9):
  for j in range(i+1,9):
   if r['completion_key'][k]:g.add_edge(i,j)
   k+=1
 oldgraphs.append(g)
it=iter((W/'inputs/L7_inventory.txt').read_text().split());n=int(next(it));ng=int(next(it));rows=[];totals=[F(0)]*len(old)
for _ in range(ng):
 idx,key,aut,orbit,den,ss,nlog,npow=[int(next(it))for _ in range(8)]
 for _ in range(nlog+npow):next(it)
 if nlog or npow:continue
 g=nx.Graph();g.add_nodes_from(range(n+1));deg=[0]*n;k=0;mf=1
 for i in range(n):
  for j in range(i+1,n):
   m=(key>>(2*k))&3;k+=1;mf*=factorial(m);deg[i]+=m;deg[j]+=m
   assert m<=1
   if m:g.add_edge(i,j)
 ef=1
 for i,a in enumerate(deg):
  e=4-a;ef*=factorial(e);assert e in [0,1]
  if e:g.add_edge(i,n)
 assert all(g.degree(i)==4 for i in g)
 wa=F(24,aut*mf*ef);match=[j for j,h in enumerate(oldgraphs)if nx.is_isomorphic(g,h)];assert len(match)==1
 j=match[0];totals[j]+=wa;rows.append({'new_id':idx,'completed_period':old[j]['label'],'weight_A':str(wa),'mass_weight_zero':ss==0})
assert len(rows)==44
for j,r in enumerate(old):assert totals[j]==F(r['weightA'])
result={'primitive_classes':len(rows),'completed_periods':len(old),'all_period_weights_match_exactly':True,'all_mass_weights_zero':all(r['mass_weight_zero']for r in rows),'rows':rows,'sums':[{ 'label':r['label'],'weight':str(totals[j]),'old_weight':r['weightA']}for j,r in enumerate(old)]}
(W/'verification/primitive_coverage_new.json').write_text(json.dumps(result,indent=2));print('44 primitive classes mapped exactly to all 14 retained weighted periods')
