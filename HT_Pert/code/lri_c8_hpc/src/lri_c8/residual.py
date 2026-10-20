"""Exact C8 high-sector residual. No epsilon series or fourth-order wavefunction here.

The physical state space is NOT reduced: the outside V0 psi3 contribution is
retained through a scalar free resolvent. No small entries are thresholded.
"""
from __future__ import annotations
import math
import time
import numpy as np
from numba import njit, prange
from ._core.basis import count_tables, unrank, rank_seq, make_edges
from ._core.operators import square_root_jets

@njit(cache=True,parallel=True,fastmath=False)
def outer_metadata(dim,G,Z,cutoff):
    P=np.empty(dim,dtype=np.uint8);Q=np.empty(dim,dtype=np.uint8)
    N=np.empty(dim,dtype=np.int32);counts=np.empty(dim,dtype=np.int64)
    for i0 in prange(dim):
        i=np.int64(i0);seq=np.empty(20,dtype=np.int32)
        p,q,n=unrank(i,G,Z,cutoff,19,16,seq)
        P[i]=p;Q[i]=q;N[i]=n;distinct=0
        for j in range(p):
            if j==0 or seq[j]!=seq[j-1]:distinct+=1
        counts[i]=distinct
    return P,Q,N,counts

@njit(cache=True,parallel=True,fastmath=False)
def creation_edges(G,Z,L,ptr,index,mode,occ):
    for i0 in prange(len(ptr)-1):
        i=np.int64(i0);seq=np.empty(20,dtype=np.int32);other=np.empty(20,dtype=np.int32)
        p,q,n=unrank(i,G,Z,L,19,16,seq)
        edge=ptr[i];j=0
        while j<p:
            md=seq[j];end=j+1
            while end<p and seq[end]==md:end+=1
            for k in range(j):other[k]=seq[k]
            for k in range(j,p-1):other[k]=seq[k+1]
            index[edge]=rank_seq(other,p-1,G,Z,L,19,16)
            mode[edge]=md;occ[edge]=end-j
            edge+=1;j=end

@njit(cache=True,parallel=True,fastmath=False)
def embedding(dim,ga,za,gb,zb,L,out):
    for i0 in prange(dim):
        i=np.int64(i0);seq=np.empty(20,dtype=np.int32)
        p,q,n=unrank(i,ga,za,L,15,12,seq)
        out[i]=rank_seq(seq,p,gb,zb,L,19,16)

@njit(cache=True,parallel=True,fastmath=False)
def creation_stored(ptr,index,mode,occ,w,x,P,output_parity):
    y=np.zeros(len(P),dtype=np.float64)
    for i in prange(len(P)):
        if P[i]%2!=output_parity:continue
        s=0.
        for k in range(ptr[i],ptr[i+1]):
            val=x[index[k]]
            if val!=0.:s+=w[mode[k],occ[k]]*val
        y[i]=s
    return y

@njit(cache=True,parallel=True,fastmath=False)
def creation_ranked(G,Z,L,w,x,P,output_parity):
    y=np.zeros(len(P),dtype=np.float64)
    for i0 in prange(len(P)):
        i=np.int64(i0)
        if P[i]%2!=output_parity:continue
        seq=np.empty(20,dtype=np.int32);other=np.empty(20,dtype=np.int32)
        p,q,n=unrank(i,G,Z,L,19,16,seq)
        j=0;s=0.
        while j<p:
            md=seq[j];end=j+1
            while end<p and seq[end]==md:end+=1
            for k in range(j):other[k]=seq[k]
            for k in range(j,p-1):other[k]=seq[k+1]
            src=rank_seq(other,p-1,G,Z,L,19,16)
            val=x[src]
            if val!=0.:s+=w[md,end-j]*val
            j=end
        y[i]=s
    return y

@njit(cache=True,parallel=True,fastmath=False)
def embed_add(out,idx,src,coef):
    # idx is an injective exact embedding: each output location has one writer.
    for i in prange(len(idx)):out[idx[i]]+=coef*src[i,0]

@njit(cache=True,parallel=True,fastmath=False)
def resolvent_blocks(x,P,N,p,Q,exclude_core,block_size=4096):
    out=np.zeros((len(P)+block_size-1)//block_size,dtype=np.float64)
    for b in prange(len(out)):
        acc=0.
        for i in range(b*block_size,min(len(P),(b+1)*block_size)):
            if N[i]%2 or P[i]%2!=p%2:continue
            if exclude_core and P[i]<=15 and Q[i]<=12:continue
            den=.25*p-.25*P[i]-N[i]
            if den!=0.:acc+=x[i]*x[i]/den
        out[b]=acc
    return out

def resolvent_norm(x,P,N,p,Q=None,exclude_core=False):
    if Q is None:Q=np.empty(0,dtype=np.uint8)
    return math.fsum(resolvent_blocks(x,P,N,p,Q,exclude_core))

class OuterSpace:
    """Full P<=19,Q<=16 space, but only scalar creation operations are stored.

    `ranked` generates edges on demand: lower memory, usually slower. Neither
    backend changes the state space, arithmetic precision, or numerical target.
    """
    def __init__(self,cutoff,core_dimension,backend='stored',core_rows=None):
        if backend not in ('stored','ranked'):raise ValueError('unknown outer backend')
        start=time.perf_counter();self.cutoff=cutoff;self.backend=backend
        G,Z=count_tables(cutoff,19,16);self.dim=int(Z[19,16,4*cutoff])
        self.P,self.Q,self.N,counts=outer_metadata(self.dim,G,Z,cutoff)
        self.nedges=int(np.sum(counts,dtype=np.int64));self.edge=None
        if backend=='stored':
            self.edge=make_edges(counts,self.dim,cutoff)
            creation_edges(G,Z,cutoff,self.edge.ptr,self.edge.index,self.edge.mode,self.edge.occ)
        del counts
        ga,za=count_tables(cutoff,15,12)
        dtype=np.int32 if self.dim<=np.iinfo(np.int32).max else np.int64
        self.map=np.empty(core_dimension,dtype=dtype)
        embedding(core_dimension,ga,za,G,Z,cutoff,self.map)
        self.maps=[self.map[rows] for rows in core_rows] if core_rows is not None else [self.map,self.map]
        if core_rows is not None:del self.map
        if backend=='ranked':self.G,self.Z=G,Z
        u=square_root_jets(cutoff,0)[0]
        self.weights=np.ascontiguousarray(u[:,None]*np.sqrt(np.arange(20,dtype=np.float64))[None,:])
        self.build_seconds=time.perf_counter()-start;self.calls=0;self.seconds=0.
        self.bytes=(self.P.nbytes+self.Q.nbytes+self.N.nbytes+sum(a.nbytes for a in self.maps)+
                    (self.edge.nbytes if self.edge is not None else G.nbytes+Z.nbytes))
    def creation(self,x,output_parity):
        t=time.perf_counter()
        if self.edge is not None:
            e=self.edge;y=creation_stored(e.ptr,e.index,e.mode,e.occ,self.weights,x,self.P,output_parity)
        else:y=creation_ranked(self.G,self.Z,self.cutoff,self.weights,x,self.P,output_parity)
        self.calls+=1;self.seconds+=time.perf_counter()-t
        return y
    def correction(self,space,psi3,p,g1=1/3):
        # last_resolvent_* skips rows with P>p+16. That is exact only because a genuine
        # psi3 has support P<=p+12 (three vertices on |p>); enforce the precondition.
        if np.any(psi3[np.asarray(space.P)>p+12]!=0.):raise ValueError('psi3 has support beyond P<=p+12')
        # Horner evaluation of C^4 u0/12+C^3 u1/3+C^2 u2/2+C u3/3.
        # u_j=B0^j psi3 live entirely in the core. B0^4 psi3 has no outside part.
        u=np.ascontiguousarray(psi3.reshape(-1,1));y=np.zeros(self.dim)
        embed_add(y,self.maps[p%2],u,1/12)
        for j,coef in ((1,1/3),(2,1/2),(3,1/3)):
            y=self.creation(y,(p+j)%2)
            if coef:
                u=space.linear(u,0,parity=(p+j-1)%2)
                embed_add(y,self.maps[(p+j)%2],u,coef)
        t=time.perf_counter()
        if self.edge is not None:
            e=self.edge;parts=last_resolvent_stored(e.ptr,e.index,e.mode,e.occ,self.weights,y,self.P,self.N,self.Q,p)
        else:parts=last_resolvent_ranked(self.G,self.Z,self.cutoff,self.weights,y,self.P,self.N,self.Q,p)
        self.calls+=1;self.seconds+=time.perf_counter()-t
        return g1*g1*math.fsum(parts)

@njit(cache=True,parallel=True,fastmath=False)
def last_resolvent_stored(ptr,idx,mode,occ,w,x,P,N,Q,p,block_size=4096):
    parts=np.zeros((len(P)+block_size-1)//block_size)
    for b in prange(len(parts)):
        accum=0.
        for i in range(b*block_size,min(len(P),(b+1)*block_size)):
            if P[i]%2!=p%2 or N[i]%2 or (P[i]<=15 and Q[i]<=12):continue
            if P[i]>p+16:continue
            val=0.
            for e in range(ptr[i],ptr[i+1]):
                v=x[idx[e]]
                if v!=0.:val+=w[mode[e],occ[e]]*v
            den=.25*p-.25*P[i]-N[i]
            if den!=0.:accum+=val*val/den
        parts[b]=accum
    return parts

@njit(cache=True,parallel=True,fastmath=False)
def last_resolvent_ranked(G,Z,L,w,x,P,N,Q,p,block_size=4096):
    parts=np.zeros((len(P)+block_size-1)//block_size)
    for b in prange(len(parts)):
        accum=0.
        for i in range(b*block_size,min(len(P),(b+1)*block_size)):
            if P[i]%2!=p%2 or N[i]%2 or (P[i]<=15 and Q[i]<=12):continue
            if P[i]>p+16:continue
            seq=np.empty(20,dtype=np.int32);other=np.empty(20,dtype=np.int32)
            pp,qq,nn=unrank(i,G,Z,L,19,16,seq)
            j=0;val=0.
            while j<pp:
                md=seq[j];end=j+1
                while end<pp and seq[end]==md:end+=1
                for k in range(j):other[k]=seq[k]
                for k in range(j,pp-1):other[k]=seq[k+1]
                src=rank_seq(other,pp-1,G,Z,L,19,16)
                v=x[src]
                if v!=0.:val+=w[md,end-j]*v
                j=end
            den=.25*p-.25*pp-nn
            if den!=0.:accum+=val*val/den
        parts[b]=accum
    return parts
