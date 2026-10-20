from pathlib import Path
import networkx as nx,json,numpy as np
W=Path(__file__).resolve().parents[1];allrec={}
for L in range(2,8):
 t=(W/f'inputs/classes{L}.txt').read_text().split();n,NG=map(int,t[:2]);rec=[]
 for i in range(NG):
  key,aut,orbit=map(int,t[2+3*i:5+3*i]);ed=[];k=0
  for a in range(n):
   for b in range(a+1,n):
    m=key>>(2*k)&3;ed +=[(a,b)]*m;k+=1
  G=nx.Graph();G.add_nodes_from(range(n));G.add_edges_from(ed)
  if list(nx.articulation_points(G)):rec.append(i)
 allrec[str(L)]=rec
 print(L,len(rec))
 if L==7:
  rows=json.load(open(W/'inputs/graph_rows7.json'));mask=[i for i in rec if not rows[i][3]];d=json.load(open(W/'records/cpilot_L7.json'));a=np.array(d['graph_batches']);h=(3*a[:,:,13]-a[:,:,6])/6561;y=h[:,mask].sum(1)
  print('free articulation',len(mask),'sum',y,'SE',y.std(ddof=1)/len(y)**.5)
json.dump(allrec,open(W/'inputs/articulation.json','w'),indent=2)
