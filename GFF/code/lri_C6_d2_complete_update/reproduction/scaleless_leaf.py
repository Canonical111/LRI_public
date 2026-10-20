"""Precisely detect massless one-attachment factors with nonzero odd degree.
The proof and use are restricted to the analytic critical-mass prescription.
No logarithmic scaleless graph is assigned a zero UV counterterm by this test.
"""
import networkx as nx
from functools import lru_cache
@lru_cache(None)
def leaf(ed,roots):
 G=nx.Graph(ed);R=set(roots)
 for v in nx.articulation_points(G):
  H=G.copy();H.remove_node(v)
  for cc in nx.connected_components(H):
   if cc & R:continue
   ss=set(cc)|{v};ee=[e for e in ed if set(e)<=ss]
   degree=len(ee)-2*(len(ss)-1)
   if degree in(-1,1):
    return {'attachment':v,'vertices':sorted(ss),'edges':ee,'degree_at_d2':degree}
 return None
