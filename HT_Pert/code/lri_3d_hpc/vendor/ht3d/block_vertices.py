"""Exact particle-block assembly of spherical bath vertices.
A_j = B^j S.  Particle selection fixes j for each block (P_left,P_right).
This avoids full-space Gram-product temporaries. No amplitude threshold is used.
"""
from collections import OrderedDict
import math,time,resource
import numpy as np
from scipy.sparse import csr_matrix,csc_matrix,coo_matrix
from numpy.polynomial.legendre import leggauss

def build_vertices(basis,S,P,delta,nodes,progress=False):
 nB=S.shape[1];full=S.shape[0];ix={int(p):np.flatnonzero(P==p) for p in np.unique(P)}
 Sc=S.tocsc();blocks={p:Sc[:,ii] for p,ii in ix.items()};del Sc
 ans=[{} for _ in range(4)];z,w=leggauss(nodes);w0=basis.weights(delta)
 for it,(zz,ww) in enumerate(zip(z,w/2)):
  if zz<0:continue
  if zz>0:ww*=2
  vals=w0*basis.angular_values(zz)
  C=csr_matrix((basis.sqocc*vals[basis.modes],basis.parents,basis.ptr),shape=(full,full))
  B=C.T # CSC: column pointer length belongs to bath, not each image.
  cache={}
  def images(p):
   if p not in cache:
    arr=[blocks[p]]
    for k in range(1,5):arr.append((B@arr[-1]).tocsc() if k<=p else csc_matrix(arr[0].shape))
    cache[p]=arr
   return cache[p]
  for pb in sorted(ix):
   for old in [k for k in cache if k<pb]:del cache[old]
   ar=images(pb)
   for diff in range(5):
    pa=pb+diff
    if pa not in ix:continue
    al=images(pa)
    for k in range(1,5):
     if diff>k or (diff+k)%2:continue
     j=(diff+k)//2
     v=(al[j].T@ar[k-j]).tocsr()
     if not v.nnz:continue
     key=(pa,pb);v=v*(ww*math.comb(k,j))
     if key in ans[k-1]:ans[k-1][key]=ans[k-1][key]+v
     else:ans[k-1][key]=v
   # Drop variables which might otherwise retain an evicted large block.
   del ar,al
  del cache,B,C
  if progress:print('ANGLE',float(zz),'maxrss_kib',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'nnz',sum(v.nnz for d in ans for v in d.values()),flush=True)
 out=[]
 for d in ans:
  rows=[];cols=[];data=[]
  for (pa,pb),v in d.items():
   v=v.tocoo();rr=ix[pa][v.row];cc=ix[pb][v.col]
   rows.append(rr);cols.append(cc);data.append(v.data)
   if pa!=pb:rows.append(cc);cols.append(rr);data.append(v.data)
  if rows:out.append(coo_matrix((np.concatenate(data),(np.concatenate(rows),np.concatenate(cols))),shape=(nB,nB)).tocsr())
  else:out.append(csr_matrix((nB,nB)))
  d.clear()
 return out
