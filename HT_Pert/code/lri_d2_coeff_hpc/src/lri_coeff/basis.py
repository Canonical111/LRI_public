"""Ranked exact auxiliary envelope A<=L/2,B<=L/2 with particle support.

A=sum a n_ab, B=sum b n_ab. This is N+|J|<=L, NOT a new physical cutoff.
Only the reflection-even orbit is stored in the expanded zero-mode graph.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from numba import njit, prange

@njit(cache=True)
def _counts(aa,bb,K,Q):
    d=np.ones((len(aa)+1,K+1,K+1,Q+1),np.int64)
    for k in range(len(aa)-1,-1,-1):
        a,b=aa[k],bb[k]
        for A in range(K+1):
            for B in range(K+1):
                for q in range(Q+1):
                    v=d[k+1,A,B,q]
                    if A>=a and B>=b and q>0:
                        w=d[k,A-a,B-b,q-1]
                        if v>9223372036854775807-w:raise OverflowError('Rank count exceeds int64')
                        v+=w
                    d[k,A,B,q]=v
    return d

@njit(cache=True)
def _enumerate(aa,bb,K,Q,size):
    N=np.zeros(size,np.int32);P=np.zeros(size,np.int16);J=np.zeros(size,np.int32)
    tree=np.zeros(size,np.int64);last=np.zeros(size,np.int32)
    path=np.empty(Q+1,np.int32);nodes=np.zeros(Q+1,np.int64)
    choices=np.zeros(Q+1,np.int32);As=np.zeros(Q+1,np.int32);Bs=np.zeros(Q+1,np.int32)
    row=1;depth=0
    while depth>=0:
        k=choices[depth]
        if depth==Q or k>=len(aa):depth-=1;continue
        choices[depth]=k+1
        if As[depth]+aa[k]>K or Bs[depth]+bb[k]>K:continue
        parent=nodes[depth];path[depth]=k
        As[depth+1]=As[depth]+aa[k];Bs[depth+1]=Bs[depth]+bb[k]
        depth+=1;nodes[depth]=row;choices[depth]=k
        N[row]=As[depth]+Bs[depth];J[row]=As[depth]-Bs[depth];P[row]=depth
        tree[row]=parent;last[row]=k;row+=1
    if row!=size:raise AssertionError('Count/enumeration disagreement')
    return N,P,J,tree,last

@njit(cache=True)
def _rank(path,n,aa,bb,K,Q,d,skip=-1):
    rank=0;A=K;B=K;q=Q;start=0
    for i in range(n):
        if i==skip:continue
        k=path[i]
        rank+=1+d[start,A,B,q]-d[k,A,B,q]
        A-=aa[k];B-=bb[k];q-=1;start=k
    return rank

@njit(cache=True)
def _mirror_one(row,P,tree,last,aa,bb,swap,K,Q,d):
    n=np.int64(P[row]);path=np.empty(n,np.int32);node=np.int64(row)
    for i in range(n-1,-1,-1):
        path[i]=swap[last[node]]
        node=tree[node]
    # Explicit small insertion sort avoids a second auto-parallel transform.
    for i in range(1,n):
        val=path[i];j=i-1
        while j>=0 and path[j]>val:path[j+1]=path[j];j-=1
        path[j+1]=val
    return _rank(path,n,aa,bb,K,Q,d)

@njit(cache=True,parallel=True)
def _mirrors(P,tree,last,aa,bb,swap,K,Q,d):
    mirror=np.empty(len(P),np.int64)
    for row in prange(len(P)):
        mirror[row]=_mirror_one(np.int64(row),P,tree,last,aa,bb,swap,K,Q,d)
    return mirror

@njit(cache=True)
def _count_one(row,P,tree,last):
    node=np.int64(row);nu=0;prev=-1
    for i in range(P[row]):
        lab=last[node]
        if lab!=prev:nu+=1
        prev=lab;node=tree[node]
    return nu

@njit(cache=True,parallel=True)
def _edgecounts(reps,counts,starts,P,tree,last,n):
    nedge=np.zeros(n,np.int32)
    for at in prange(len(reps)):
        row=reps[at];nu=_count_one(row,P,tree,last);start=starts[row]
        for z in range(counts[at]):nedge[start+z]=nu+int(z>0)
    return nedge

@njit(cache=True)
def _edges_one(at,reps,counts,starts,P,tree,last,mirror,aa,bb,K,Q,d,ptr,cols,mode,amp):
    row=reps[at];n=int(P[row]);path=np.empty(n,np.int32);node=np.int64(row)
    for i in range(n-1,-1,-1):path[i]=last[node];node=tree[node]
    di=1 if mirror[row]==row else 2
    child=np.empty(n,np.int64);md=np.empty(n,np.int32);am=np.empty(n)
    nu=0;j=0
    while j<n:
        end=j+1
        while end<n and path[end]==path[j]:end+=1
        ch=_rank(path,n,aa,bb,K,Q,d,j);ch=min(ch,mirror[ch])
        dj=1 if mirror[ch]==ch else 2
        if starts[ch]<0:return False
        child[nu]=starts[ch];md[nu]=path[j]+1;am[nu]=math.sqrt(end-j)*math.sqrt(di/dj)
        nu+=1;j=end
    for z in range(counts[at]):
        i=starts[row]+z;e=ptr[i]
        if z>0:cols[e]=i-1;mode[e]=0;amp[e]=math.sqrt(z);e+=1
        for j in range(nu):cols[e]=child[j]+z;mode[e]=md[j];amp[e]=am[j];e+=1
        # Keep multiplicity edges separate: two mirror modes can share a child.
        # Every term is evaluated, with its own (identical under reflection) weight.

    return True

@njit(cache=True,parallel=True)
def _edges(reps,counts,starts,P,tree,last,mirror,aa,bb,K,Q,d,ptr,cols,mode,amp):
    okay=np.empty(len(reps),np.bool_)
    for at in prange(len(reps)):
        okay[at]=_edges_one(np.int64(at),reps,counts,starts,P,tree,last,mirror,aa,bb,K,Q,d,ptr,cols,mode,amp)
    return okay

@njit(cache=True)
def _transpose(n,ptr,cols):
    bp=np.zeros(n+1,np.int64)
    for j in cols:bp[j+1]+=1
    for i in range(n):bp[i+1]+=bp[i]
    at=bp[:-1].copy();eid=np.empty(len(cols),np.int64)
    parent=np.empty_like(cols)
    for i in range(n):
        for e in range(ptr[i],ptr[i+1]):
            p=at[cols[e]];at[cols[e]]+=1;eid[p]=e;parent[p]=i
    return bp,parent,eid

def mode_jets(labels,L,degree):
    v=np.zeros((degree,L+1));v[0,0]=1
    for n in range(1,L+1):
        v[:,n]=v[:,n-1]*(n-.5)/n;v[1:,n]-=v[:-1,n-1]/(4*n)
    u=np.zeros_like(v);u[0]=np.sqrt(v[0])
    for k in range(1,degree):u[k]=(v[k]-sum(u[j]*u[k-j] for j in range(1,k)))/(2*u[0])
    out=np.zeros((len(labels)+1,degree));out[0,0]=1
    for i,(a,b) in enumerate(labels,1):out[i]=np.convolve(u[:,a],u[:,b])[:degree]
    return out

def _validate(L,degree,pmax):
    if isinstance(L,bool) or not isinstance(L,(int,np.integer)) or L<0 or L%2:raise ValueError('L must be a nonnegative even integer')
    if not 2<=degree<=8:raise ValueError('Supported degree is 2..8')
    if pmax<3+4*(degree//2):raise ValueError('Particle cap is below proven support')
    if L>2048 or pmax>32760:raise ValueError('Index guard; a new typed implementation is needed for these ranges')

@njit(cache=True)
def _moments_dp(items,K,Q):
    count=np.zeros((K+1,K+1,Q+1),np.int64);count[0,0,0]=1
    distinct=np.zeros_like(count)
    for z in range(len(items)):
        da,db,dq,weight=items[z]
        old=count.copy()
        for A in range(da,K+1):
            for B in range(db,K+1):
                for q in range(dq,Q+1):
                    val=count[A-da,B-db,q-dq]
                    if count[A,B,q]>9223372036854775807-val:raise OverflowError('Plan state counts exceed int64')
                    count[A,B,q]+=val
                    val=distinct[A-da,B-db,q-dq]+weight*old[A-da,B-db,q-dq]
                    if val<0 or distinct[A,B,q]>9223372036854775807-val:raise OverflowError('Plan edge counts exceed int64')
                    distinct[A,B,q]+=val
    return count,distinct

def plan(L,degree=8,pmax=None):
    pmax=3+4*(degree//2) if pmax is None else int(pmax);_validate(L,degree,pmax)
    K=L//2;Q=4*(degree//2)
    labels=tuple((a,n-a) for n in range(1,L+1) for a in range(n+1) if a<=K and n-a<=K)
    dpbytes=(len(labels)+1)*(K+1)**2*(Q+1)*8
    if dpbytes>2*1024**3:raise MemoryError('Rank DP alone exceeds 2 GiB guard')
    items=np.array([(a,b,1,1) for a,b in labels],np.int64).reshape(-1,4)
    full,full_d=_moments_dp(items,K,Q)
    items=np.array([(a,a,1,1) for a in range(1,K+1)]+[(a+b,a+b,2,2) for a in range(K+1) for b in range(a+1,K+1) if a+b<=K],np.int64).reshape(-1,4)
    fixed,fixed_d=_moments_dp(items,K,Q)
    ns=ed=nb=0;sc_even=[];sc_odd=[]
    for A in range(K+1):
        for B in range(K+1):
            for q in range(Q+1):
                nf=int(full[A,B,q]);nfix=int(fixed[A,B,q]);nb+=nf
                ns+=(nf+nfix)*(pmax-q+1)
                ed+=(int(full_d[A,B,q])+int(fixed_d[A,B,q]))*(pmax-q+1)+(nf+nfix)*(pmax-q)
    ns//=2;ed//=2
    for H in range(K+1):
        cnt=[0,0]
        for a in range(H+1):
            for q in range(Q+1):
                nr=(int(full[a,a,q])+int(fixed[a,a,q]))//2
                for parity in (0,1):
                    z0=(parity-q)%2
                    count=(pmax-q-z0)//2+1
                    cnt[parity]+=nr*max(count,0)
        sc_even.append(cnt[0]);sc_odd.append(cnt[1])
    idxbytes=4 if ns<2**31 else 8;modebytes=2 if len(labels)+1<=65536 else 4
    graphbytes=ns*(14+16)+ed*(2*idxbytes+modebytes+8+8)+(len(labels)+1)*degree*8+48
    scalarentries=sum(sc_even)+2*sc_even[-1]+2*sc_odd[-1]
    wavebytes=(degree//2+1)*scalarentries*8
    channelbytes=scalarentries*42+wavebytes
    # Explicit safe envelope, not an empirical fitted confidence bound. Runtime
    # allocator/OpenMP overhead is not included and is covered by the safety factor.
    scratchbytes=ns*8*max(3*degree,5*(degree//2))
    steady=graphbytes+channelbytes+scratchbytes
    build=graphbytes+dpbytes+nb*96+ns*24
    suggested=int(max(steady,build)*1.35+256*1024**2)
    return dict(L=int(L),degree=int(degree),pmax=pmax,qmax=Q,bath_envelope_states=nb,auxiliary_states=ns,ladder_edges=ed,rank_dp_bytes=dpbytes,labels=len(labels),scalar_even_by_cutoff=sc_even,scalar_odd_by_cutoff=sc_odd,graph_bytes_estimate=graphbytes,wave_bytes_estimate=wavebytes,scratch_bytes_estimate=scratchbytes,recommended_memory_bytes=suggested,precision='float64 vectors; longdouble scalar reductions',planning_scope='Exact state/edge counts; conservative live-array memory model plus safety factor, not a measured cluster envelope.')

@dataclass
class Graph:
    L:int
    degree:int
    pmax:int
    qmax:int
    N:np.ndarray
    P:np.ndarray
    Jabs:np.ndarray
    extent:np.ndarray
    refs:np.ndarray
    cptr:np.ndarray
    child:np.ndarray
    mode:np.ndarray
    amp:np.ndarray
    bptr:np.ndarray
    parent:np.ndarray
    edge:np.ndarray
    u:np.ndarray
    bath_size:int
    @property
    def n(self):return len(self.N)
    @property
    def E(self):return self.N+.5*self.P
    @property
    def scalar(self):return self.Jabs==0
    @property
    def nnz(self):return len(self.child)
    @property
    def nbytes(self):return sum(x.nbytes for x in self.__dict__.values() if isinstance(x,np.ndarray))
    def prefix_size(self,ell):return int(np.searchsorted(self.extent,ell,side='right'))

    @classmethod
    def build(cls,L,degree=8,pmax=None,max_states=3000000,max_bytes=3*1024**3):
        import gc
        p=plan(L,degree,pmax);pmax=p['pmax'];Q=p['qmax'];K=L//2
        if p['auxiliary_states']>max_states:raise MemoryError(f"Exact auxiliary count {p['auxiliary_states']:,} exceeds --max-states={max_states:,}")
        # Conservative persistent bound; runtime planning adds the contraction workspace.
        minbytes=p['rank_dp_bytes']+p['bath_envelope_states']*80+p['auxiliary_states']*50
        if minbytes>max_bytes:raise MemoryError('Preallocation estimate exceeds memory budget')
        labels=tuple((a,n-a) for n in range(1,L+1) for a in range(n+1) if a<=K and n-a<=K)
        aa=np.array([a for a,b in labels],np.int32);bb=np.array([b for a,b in labels],np.int32)
        d=_counts(aa,bb,K,Q);size=int(d[0,K,K,Q])
        N,P,J,tree,last=_enumerate(aa,bb,K,Q,size)
        lookup={x:i for i,x in enumerate(labels)};swap=np.array([lookup[b,a] for a,b in labels],np.int32)
        mir=_mirrors(P,tree,last,aa,bb,swap,K,Q,d)
        if np.any(mir<0) or np.any(mir>=size) or not np.array_equal(mir[mir],np.arange(size)):raise AssertionError('Invalid reflection involution')
        reps=np.flatnonzero(np.arange(size)<=mir);extent=N+np.abs(J)
        reps=reps[np.argsort(extent[reps],kind='stable')];counts=(pmax-P[reps]+1).astype(np.int64)
        starts=np.full(size,-1,np.int64);starts[reps]=np.r_[0,np.cumsum(counts)[:-1]];n=int(counts.sum())
        if n!=p['auxiliary_states']:raise AssertionError('Burnside/count mismatch')
        ne=_edgecounts(reps,counts,starts,P,tree,last,n);ptr=np.r_[0,np.cumsum(ne,dtype=np.int64)];del ne
        nnz=int(ptr[-1])
        if nnz!=p['ladder_edges']:raise AssertionError('Exact edge-count mismatch')
        itype=np.int32 if n<2**31 else np.int64;mtype=np.uint16 if len(labels)+1<=65536 else np.uint32
        estimate=minbytes+nnz*(2*np.dtype(itype).itemsize+np.dtype(mtype).itemsize+16)+16*n
        if estimate>max_bytes:raise MemoryError(f'Graph-build estimate {estimate/2**30:.3f} GiB exceeds budget {max_bytes/2**30:.3f} GiB')
        cols=np.empty(nnz,itype);modes=np.empty(nnz,mtype);amps=np.empty(nnz)
        okay=_edges(reps,counts,starts,P,tree,last,mir,aa,bb,K,Q,d,ptr,cols,modes,amps)
        if not np.all(okay):raise AssertionError('Missing annihilation support')
        del okay
        rb=np.repeat(reps,counts);z=np.arange(n)-np.repeat(starts[reps],counts)
        N1=N[rb].copy();P1=(P[rb]+z).astype(np.int16);J1=np.abs(J[rb]);ex=extent[rb].copy();refs=np.arange(starts[0],starts[0]+4,dtype=np.int64)
        del N,P,J,tree,last,mir,reps,counts,starts,rb,z,d;gc.collect()
        bp,parents,edge=_transpose(n,ptr,cols)
        return cls(L,degree,pmax,Q,N1,P1,J1,ex,refs,ptr,cols,modes,amps,bp,parents,edge,mode_jets(labels,L,degree),size)
