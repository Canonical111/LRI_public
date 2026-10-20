"""Exact DFS-ranked positive-mode partitions; no Python state dictionary.

All partitions of total level <= N are retained. There is no particle cap.
The integer ordering agrees with reference.partitions_upto.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from numba import njit, prange
from scipy.sparse import csr_matrix


def count_table(n: int) -> np.ndarray:
    if not isinstance(n, (int,np.integer)) or n < 0 or n > 65534:
        raise ValueError('bath cutoff must be an integer in [0,65534]')
    if n > 512:
        raise OverflowError('Cutoffs above 512 are outside the supported exact-int64 partition range')
    # Python integers check the table before converting to signed int64.
    c=[[1]*(n+2) for _ in range(n+1)]
    for k in range(n,0,-1):
        for r in range(n+1):
            c[r][k]=c[r][k+1]+(c[r-k][k] if r>=k else 0)
            if c[r][k] > np.iinfo(np.int64).max:
                raise OverflowError('Exact partition count exceeds int64')
    return np.asarray(c,dtype=np.int64)

@njit(cache=True)
def _decode(idx,n,counts):
    occ=np.zeros(n+1,np.int64);rem=n;start=1
    while idx:
        idx-=1
        for mode in range(start,rem+1):
            size=counts[rem-mode,mode]
            if idx<size:
                occ[mode]+=1;rem-=mode;start=mode;break
            idx-=size
    return occ

@njit(cache=True)
def _rank(occ,n,counts):
    rank=0;rem=n;start=1
    for mode in range(1,n+1):
        for j in range(occ[mode]):
            rank+=1+counts[rem,start]-counts[rem,mode]
            rem-=mode;start=mode
    return rank

@njit(cache=True,parallel=True)
def _metadata(n,counts,N,P,degree):
    for i in prange(len(N)):
        occ=_decode(i,n,counts)
        lev=0;num=0;edges=0
        for k in range(1,n+1):
            lev+=k*occ[k];num+=occ[k];edges+=int(occ[k]>0)
        N[i]=lev;P[i]=num;degree[i]=edges

@njit(cache=True,parallel=True)
def _edges(n,counts,ptr,col,mode,amplitude):
    for i in prange(len(ptr)-1):
        occ=_decode(i,n,counts);q=ptr[i]
        for k in range(1,n+1):
            if occ[k]:
                amp=math.sqrt(occ[k]);occ[k]-=1
                col[q]=_rank(occ,n,counts);mode[q]=k;amplitude[q]=amp
                occ[k]+=1;q+=1

@dataclass
class BathBasis:
    cutoff:int
    N:np.ndarray
    P:np.ndarray
    ptr:np.ndarray
    col:np.ndarray
    mode:np.ndarray
    amp:np.ndarray

    @classmethod
    def build(cls,n):
        c=count_table(n);d=int(c[n,1]);ix=np.int32 if d<=np.iinfo(np.int32).max else np.int64
        N=np.empty(d,np.int32);P=np.empty(d,np.int32);degree=np.empty(d,np.int64)
        _metadata(n,c,N,P,degree)
        ptr=np.r_[np.int64(0),np.cumsum(degree,dtype=np.int64)]
        col=np.empty(ptr[-1],ix);mode=np.empty(ptr[-1],np.uint16);amp=np.empty(ptr[-1],np.float64)
        _edges(n,c,ptr,col,mode,amp)
        return cls(n,N,P,ptr,col,mode,amp)

    def ladders(self,delta):
        u=np.ones(self.cutoff+1)
        for n in range(1,len(u)):u[n]=u[n-1]*math.sqrt((n-1+2*delta)/n)
        C=csr_matrix((self.amp*u[self.mode],self.col.copy(),self.ptr.copy()),shape=(len(self.N),)*2)
        C.sort_indices();B=C.T.tocsr();B.sort_indices()
        return B,C

    @property
    def nbytes(self):
        return sum(x.nbytes for x in (self.N,self.P,self.ptr,self.col,self.mode,self.amp))
