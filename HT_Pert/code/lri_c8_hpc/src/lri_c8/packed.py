"""Exact field-parity packed ladder jets.

Every intermediate retains both reflection parities. Reflection is projected
only after the COMPLETE vertex, exactly as in the reference prescription.
"""
from __future__ import annotations
import math,time,gc
import numpy as np
from numba import njit,prange
from ._core.basis import RankedBasis,make_edges
from ._core.operators import square_root_jets,divide_series
from ._core.kernels import dot_blocks,mask_vertex

@njit(cache=True)
def pack_indices(P,out):
    count=np.zeros(2,dtype=np.int64)
    for i in range(len(P)):
        p=P[i]%2;out[i]=count[p];count[p]+=1
    return count

@njit(cache=True,parallel=True)
def copy_edges(rows,mapping,oldptr,oldidx,oldmode,oldocc,ptr,idx,mode,occ):
    for r in prange(len(rows)):
        for offset in range(oldptr[rows[r]+1]-oldptr[rows[r]]):
            e=oldptr[rows[r]]+offset;dst=ptr[r]+offset
            idx[dst]=mapping[oldidx[e]];mode[dst]=oldmode[e];occ[dst]=oldocc[e]

@njit(cache=True,parallel=True,fastmath=False)
def packed_ladder(ptr,idx,mode,occ,weights,x,degree):
    n=len(ptr)-1;y=np.empty((n,degree+1),dtype=np.float64)
    for r in prange(n):
        for j in range(degree+1):y[r,j]=0.
        for e in range(ptr[r],ptr[r+1]):
            s=idx[e];m=mode[e];o=occ[e]
            for k in range(min(x.shape[1],degree+1)):
                val=x[s,k]
                if val!=0.:
                    for j in range(min(weights.shape[2],degree-k+1)):
                        y[r,k+j]+=weights[m,o,j]*val
    return y

@njit(cache=True,parallel=True,fastmath=False)
def initial_combinations(c1,b1):
    m=np.empty_like(c1);v=np.empty_like(c1)
    for i in prange(c1.shape[0]):
        for j in range(c1.shape[1]):
            m[i,j]=c1[i,j]+2*b1[i,j]
            v[i,j]=c1[i,j]/12+b1[i,j]/3
    return m,v

@njit(cache=True,parallel=True,fastmath=False)
def axpy(y,x,a):
    for i in prange(y.shape[0]):
        for j in range(y.shape[1]):y[i,j]+=a*x[i,j]

class PackedCore:
    def __init__(self,cutoff):
        t=time.perf_counter();base=RankedBasis(cutoff,15,12)
        self.cutoff=cutoff;self.dim=base.global_dim;self.table_bytes=base.table_bytes
        self.rows=[];self.P=[];self.N=[];self.Efree=[];self.F1=[]
        dtype=np.int32 if self.dim<=np.iinfo(np.int32).max else np.int64
        mapping=np.empty(self.dim,dtype=dtype);counts=pack_indices(base.P,mapping)
        self.reference_index=[int(mapping[p]) for p in range(4)]
        for p in (0,1):
            rows=np.flatnonzero(base.P%2==p).astype(dtype);self.rows.append(rows)
            self.P.append(base.P[rows]);self.N.append(base.N[rows])
            self.Efree.append(self.N[p]+.25*self.P[p]);self.F1.append(-.25*self.P[p])
        self.edges={}
        for tag,e in [('C',base.creation),('B',base.annihilation)]:
            for p in (0,1):
                rows=self.rows[p];counts=e.ptr[rows+1]-e.ptr[rows]
                ne=make_edges(counts,self.dim,cutoff)
                copy_edges(rows,mapping,e.ptr,e.index,e.mode,e.occ,ne.ptr,ne.index,ne.mode,ne.occ)
                self.edges[tag,p]=ne
        del base,mapping;gc.collect()
        u=square_root_jets(cutoff,7)
        self.weights=np.ascontiguousarray(u.T[:,None,:]*np.sqrt(np.arange(16,dtype=np.float64))[None,:,None])
        self.edges_bytes=sum(e.nbytes for e in self.edges.values())
        self.ladder_calls=0;self.timings={'basis':time.perf_counter()-t,'ladder':0.,'inner':0.,'vertices':0.}
    def sector(self,p):return Sector(self,p%2)

class Sector:
    def __init__(self,core,parity):
        self.core=core;self.parity=parity;self.cutoff=core.cutoff;self.comm=None
        self.P=core.P[parity];self.N=core.N[parity];self.Efree=core.Efree[parity];self.F1=core.F1[parity]
        self.dim=len(self.P)
    def seed(self,p,order):
        if p%2!=self.parity:raise ValueError('reference parity mismatch')
        if np.count_nonzero((self.N%2==0)&(4*self.N+self.P==p))!=1:raise RuntimeError('degenerate reference')
        psi=np.zeros((self.dim,order+1));psi[self.core.reference_index[p],0]=1.;return psi
    def sample(self,x,p):return float(x[self.core.reference_index[p]])
    def linear(self,x,degree,creation=False,parity=-1):
        if parity not in (0,1):raise ValueError('packed input parity must be specified')
        if degree<0 or degree>7 or x.dtype!=np.float64 or len(x)!=len(self.core.P[parity]):raise ValueError('bad ladder input')
        t=time.perf_counter();e=self.core.edges['C' if creation else 'B',1-parity]
        y=packed_ladder(e.ptr,e.index,e.mode,e.occ,self.core.weights,x,degree)
        self.core.timings['ladder']+=time.perf_counter()-t;self.core.ladder_calls+=1;return y
    def inner(self,x,y,degree,diag=None):
        t=time.perf_counter();blocks=dot_blocks(x,y,degree,np.empty(0) if diag is None else diag,4096)
        out=np.array([math.fsum(blocks[:,k]) for k in range(degree+1)])
        self.core.timings['inner']+=time.perf_counter()-t;return out
    def vertices(self,psi,degree,parity=-1):
        if parity!=self.parity:raise ValueError('incorrect vertex parity')
        t=time.perf_counter();opp=1-parity
        b1=self.linear(psi,degree,parity=parity);c1=self.linear(psi,degree,True,parity=parity)
        a,v=initial_combinations(c1,b1);del c1
        m=self.linear(a,degree,True,parity=opp);del a
        b2=self.linear(b1,degree,parity=opp);del b1
        axpy(m,b2,1.)
        v=self.linear(v,degree,True,parity=opp);axpy(v,b2,.5)
        b3=self.linear(b2,degree,parity=parity);del b2
        v=self.linear(v,degree,True,parity=parity);axpy(v,b3,1/3)
        b4=self.linear(b3,degree,parity=opp);del b3
        v=self.linear(v,degree,True,parity=opp);axpy(v,b4,1/12);del b4
        mask_vertex(m,v,self.N)
        self.core.timings['vertices']+=time.perf_counter()-t;return m,v
