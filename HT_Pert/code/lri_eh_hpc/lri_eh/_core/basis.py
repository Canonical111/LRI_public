"""Exact ranked Fock basis, no Python big integers or state hash table.

Ordering is the depth-first nondecreasing-mode ordering of the reference.
All energies/cutoffs are integer multiples of 1/4. Counts use checked int64.
Construction can be performed independently for a contiguous MPI row shard.
"""
from __future__ import annotations
import time
from dataclasses import dataclass
import numpy as np
from numba import njit, prange

@njit(cache=True)
def count_tables(cutoff, pmax, qmax):
    """Positive-mode suffix counts G[k, E4, minmode] plus zero-mode counts."""
    E=4*cutoff
    # A count at minmode==cutoff is the empty suffix only.
    G=np.ones((qmax+1,E+1,cutoff+1),dtype=np.int64)
    cap=np.int64(9223372036854775807)
    overflow=False
    for s in range(cutoff-1,0,-1):
        cost=4*s+1
        for k in range(1,qmax+1):
            for e in range(E+1):
                a=G[k,e,s+1]
                b=G[k-1,e-cost,s] if e>=cost else np.int64(0)
                if a>cap-b:
                    G[k,e,s]=cap;overflow=True
                else:G[k,e,s]=a+b
    Z=np.zeros((pmax+1,qmax+1,E+1),dtype=np.int64)
    for p in range(pmax+1):
        for q in range(qmax+1):
            for e in range(E+1):
                a=G[min(p,q),e,1]
                b=Z[p-1,q,e-1] if p>0 and e>0 else np.int64(0)
                if a>cap-b:
                    Z[p,q,e]=cap;overflow=True
                else:Z[p,q,e]=a+b
    if overflow:raise OverflowError('Fock suffix count exceeds signed int64.')
    return G,Z

@njit(cache=True,inline='always')
def suffix(G,Z,p,q,e,s):
    if s==0:return Z[p,q,e]
    return G[min(p,q),e,s]

@njit(cache=True)
def unrank(index,G,Z,cutoff,pmax,qmax,seq):
    p=0;q=0;N=0;e=4*cutoff;start=0
    while index>0:
        index-=1
        total=suffix(G,Z,pmax-p,qmax-q,e,start)
        hi=min(cutoff-1,(e-1)//4)
        if q==qmax:hi=min(hi,0)
        lo=start
        # Monotone cumulative sibling-subtree count, exact integer arithmetic.
        while lo<hi:
            mid=(lo+hi+1)//2
            before=total-suffix(G,Z,pmax-p,qmax-q,e,mid)
            if before<=index:lo=mid
            else:hi=mid-1
        n=lo
        index-=total-suffix(G,Z,pmax-p,qmax-q,e,n)
        seq[p]=n;p+=1;N+=n;q+=int(n!=0);e-=4*n+1;start=n
    return p,q,N

@njit(cache=True)
def rank_seq(seq,p,G,Z,cutoff,pmax,qmax):
    rank=np.int64(0);q=0;e=4*cutoff;start=0
    for j in range(p):
        n=seq[j]
        rank+=1
        if n!=start:
            rank+=suffix(G,Z,pmax-j,qmax-q,e,start)-suffix(G,Z,pmax-j,qmax-q,e,n)
        q+=int(n!=0);e-=4*n+1;start=n
    return rank

@njit(cache=True,parallel=True)
def row_metadata(begin,end,G,Z,cutoff,pmax,qmax):
    d=end-begin
    P=np.empty(d,dtype=np.int16);N=np.empty(d,dtype=np.int32)
    cc=np.empty(d,dtype=np.int64);bc=np.empty(d,dtype=np.int64)
    for i0 in prange(d):
        i=np.int64(i0)
        seq=np.empty(pmax+1,dtype=np.int32)
        p,q,n=unrank(begin+i,G,Z,cutoff,pmax,qmax,seq)
        P[i]=p;N[i]=n
        distinct=0
        for j in range(p):
            if j==0 or seq[j]!=seq[j-1]:distinct+=1
        cc[i]=distinct
        upper=min(cutoff-1,(4*cutoff-p-4*n-1)//4)
        if q==qmax:upper=min(upper,0)
        bc[i]=max(0,upper+1) if p<pmax else 0
    return P,N,cc,bc

@njit(cache=True,parallel=True)
def fill_edges(begin,G,Z,cutoff,pmax,qmax,cptr,bptr,cidx,cmode,cocc,bidx,bmode,bocc):
    d=len(cptr)-1
    for i0 in prange(d):
        i=np.int64(i0)
        seq=np.empty(pmax+1,dtype=np.int32)
        other=np.empty(pmax+1,dtype=np.int32)
        p,q,N=unrank(begin+i,G,Z,cutoff,pmax,qmax,seq)
        edge=cptr[i];j=0
        while j<p:
            n=seq[j];h=j+1
            while h<p and seq[h]==n:h+=1
            for k in range(j):other[k]=seq[k]
            for k in range(j,p-1):other[k]=seq[k+1]
            cidx[edge]=rank_seq(other,p-1,G,Z,cutoff,pmax,qmax)
            cmode[edge]=n;cocc[edge]=h-j;edge+=1;j=h
        for n in range(bptr[i+1]-bptr[i]):
            j=0
            while j<p and seq[j]<n:j+=1
            h=j
            while h<p and seq[h]==n:h+=1
            for k in range(j):other[k]=seq[k]
            other[j]=n
            for k in range(j,p):other[k+1]=seq[k]
            edge=bptr[i]+n
            bidx[edge]=rank_seq(other,p+1,G,Z,cutoff,pmax,qmax)
            bmode[edge]=n;bocc[edge]=h-j+1

@dataclass
class Edges:
    ptr: np.ndarray
    index: np.ndarray
    mode: np.ndarray
    occ: np.ndarray
    @property
    def nbytes(self):return sum(x.nbytes for x in (self.ptr,self.index,self.mode,self.occ))

def make_edges(counts,global_dimension,cutoff):
    ptr=np.empty(len(counts)+1,dtype=np.int64);ptr[0]=0
    np.cumsum(counts,out=ptr[1:])
    ne=int(ptr[-1])
    itype=np.int32 if global_dimension<=np.iinfo(np.int32).max else np.int64
    mtype=np.uint16 if cutoff<=65536 else np.uint32
    return Edges(ptr,np.empty(ne,dtype=itype),np.empty(ne,dtype=mtype),np.empty(ne,dtype=np.uint8))

class RankedBasis:
    def __init__(self,cutoff:int,pmax:int,qmax:int,comm=None,memory_limit_gib=None,basis_cache=None,compact_single=False):
        if cutoff<2 or cutoff%2:raise ValueError('cutoff must be even and >=2')
        if not 6<=pmax<=255 or not 0<=qmax<=pmax:raise ValueError('invalid particle caps')
        if compact_single and (comm is not None or basis_cache is not None):raise ValueError('Compact memory estimate is for uncached single-process correction work only')
        self.cutoff=cutoff;self.pmax=pmax;self.qmax=qmax
        self.comm=comm;self.rank=0 if comm is None else comm.Get_rank()
        self.size=1 if comm is None else comm.Get_size()
        t=time.perf_counter()
        cache_path=None
        self.cache_hit=False
        if basis_cache is not None:
            from .cache import key_dir,load_basis,save_basis
            cache_path=key_dir(basis_cache,cutoff,pmax,qmax,self.rank,self.size)
            if load_basis(self,cache_path):
                if memory_limit_gib and self.estimated_working_bytes>memory_limit_gib*2**30:
                    raise MemoryError('Cached basis exceeds requested working-memory budget')
                self.Efree=self.N+self.P*.25;self.F1=-self.P*.25;self.even=self.N%2==0
                self.edges_bytes=self.creation.nbytes+self.annihilation.nbytes
                self.build_seconds=time.perf_counter()-t;self.cache_hit=True
                return
        table_bytes=(qmax+1)*(4*cutoff+1)*(cutoff+1)*8+(pmax+1)*(qmax+1)*(4*cutoff+1)*8
        if memory_limit_gib and table_bytes>memory_limit_gib*2**30/2:
            raise MemoryError('Suffix tables alone exceed half the requested per-rank budget')
        G,Z=count_tables(cutoff,pmax,qmax)
        self.global_dim=int(Z[pmax,qmax,4*cutoff])
        self.begin=self.global_dim*self.rank//self.size;self.end=self.global_dim*(self.rank+1)//self.size
        self.dim=self.end-self.begin
        if memory_limit_gib and (512 if compact_single else 800)*self.dim+table_bytes>memory_limit_gib*2**30:
            raise MemoryError(f'{self.global_dim:,} states; vector working-set estimate alone exceeds the per-rank budget')
        self.P,self.N,cc,bc=row_metadata(self.begin,self.end,G,Z,cutoff,pmax,qmax)
        # Estimate includes conservative 100 float64 vectors, two edge orientations,
        # metadata, and temporary indices. Halo communication can add more.
        if compact_single:
            indexbytes=4 if self.global_dim<=np.iinfo(np.int32).max else 8
            modebytes=2 if cutoff<=65536 else 4
            edgebytes=16*(self.dim+1)+(indexbytes+modebytes+1)*(int(cc.sum())+int(bc.sum()))
            self.estimated_working_bytes=int(64*8*self.dim+48*self.dim+edgebytes+table_bytes+512*2**20)
        else:
            self.estimated_working_bytes=int(100*8*self.dim+2*16*(int(cc.sum())+int(bc.sum()))+table_bytes)
        if memory_limit_gib and self.estimated_working_bytes>memory_limit_gib*2**30:
            raise MemoryError(f'Conservative per-rank estimate {self.estimated_working_bytes/2**30:.2f} GiB exceeds budget')
        self.creation=make_edges(cc,self.global_dim,cutoff)
        self.annihilation=make_edges(bc,self.global_dim,cutoff)
        del cc,bc
        fill_edges(self.begin,G,Z,cutoff,pmax,qmax,
                   self.creation.ptr,self.annihilation.ptr,
                   self.creation.index,self.creation.mode,self.creation.occ,
                   self.annihilation.index,self.annihilation.mode,self.annihilation.occ)
        del G,Z
        self.Efree=self.N+self.P*.25;self.F1=-self.P*.25
        self.even=self.N%2==0
        self.build_seconds=time.perf_counter()-t
        self.table_bytes=table_bytes
        self.edges_bytes=self.creation.nbytes+self.annihilation.nbytes
        if cache_path is not None:save_basis(self,cache_path)
