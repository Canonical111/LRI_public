"""Articulation-point classes per loop order (networkx), generalization of
reference/code/check_articulation.py to any L range. Same definition: class i of classesL.txt is
listed when the simple graph on nodes 0..n-1 (multi-edges collapsed) has an articulation point.
The reference's extra L=7 Monte-Carlo printout (needs records/) is dropped.
Output: json.dump(..., indent=2) of {"L": [ids]} exactly as the reference writes it.
Usage: python check_articulation.py <dir with classesL.txt> <Lmin> <Lmax> <output.json>
"""
from pathlib import Path
import networkx as nx,json,sys
D=Path(sys.argv[1]);Lmin,Lmax=int(sys.argv[2]),int(sys.argv[3]);allrec={}
for L in range(Lmin,Lmax+1):
 t=(D/f'classes{L}.txt').read_text().split();n,NG=map(int,t[:2]);rec=[]
 assert len(t)==2+3*NG
 for i in range(NG):
  key,aut,orbit=map(int,t[2+3*i:5+3*i]);ed=[];k=0
  for a in range(n):
   for b in range(a+1,n):
    m=key>>(2*k)&3;ed +=[(a,b)]*m;k+=1
  assert key>>(2*k)==0
  G=nx.Graph();G.add_nodes_from(range(n));G.add_edges_from(ed)
  if list(nx.articulation_points(G)):rec.append(i)
 allrec[str(L)]=rec
 print(L,len(rec),flush=True)
json.dump(allrec,open(sys.argv[4],'w'),indent=2)
