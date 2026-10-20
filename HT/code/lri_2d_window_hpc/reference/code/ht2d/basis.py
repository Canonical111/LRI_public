"""Complete positive circle modes below N<=L; no particle truncation.

All intermediate angular sectors are retained in normally ordered products.
Only complete vertices are projected to fixed J in ProductOperator.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections import Counter
from array import array
import math
import numpy as np
from scipy.sparse import csr_matrix


def dimension(cutoff: int) -> int:
    dp=[0]*(cutoff+1);dp[0]=1
    for n in range(1,cutoff+1):
        for _ in range(n+1):
            for k in range(n,cutoff+1):dp[k]+=dp[k-n]
    return sum(dp)


@dataclass
class CircleBathBasis:
    cutoff: int
    labels: tuple
    states: list
    N: np.ndarray
    P: np.ndarray
    J: np.ndarray
    indptr: np.ndarray
    parent: np.ndarray
    mode: np.ndarray
    sqocc: np.ndarray

    @classmethod
    def build(cls,cutoff: int,max_states=250000):
        cutoff=int(cutoff)
        size=dimension(cutoff)
        if size>max_states:raise MemoryError(f'{size} bath states exceeds guard {max_states}')
        labels=tuple((a,n-a) for n in range(1,cutoff+1) for a in range(n+1))
        levels=[a+b for a,b in labels];spins=[a-b for a,b in labels]
        states=[];ps=[];ns=[];js=[]
        def rec(state,left,start,j):
            states.append(state);ps.append(len(state));ns.append(cutoff-left);js.append(j)
            for k in range(start,len(labels)):
                n=levels[k]
                if n>left:break
                rec(state+(k,),left-n,k,j+spins[k])
        rec((),cutoff,0,0)
        if len(states)!=size:raise AssertionError('DP / enumeration dimension mismatch')
        idx={s:i for i,s in enumerate(states)}
        parents=array('i');modes=array('H');amps=array('d');ptr=np.zeros(size+1,dtype=np.int64)
        for i,s in enumerate(states):
            for mode,n in Counter(s).items():
                t=list(s);t.remove(mode)
                parents.append(idx[tuple(t)]);modes.append(mode);amps.append(math.sqrt(n))
            ptr[i+1]=len(parents)
        return cls(cutoff,labels,states,np.array(ns,np.int32),np.array(ps,np.int16),np.array(js,np.int32),ptr,
                   np.array(parents,np.int32),np.array(modes,np.uint16),np.array(amps,np.float64))

    def ladders(self,delta):
        # v_a=(delta)_a/a!, u_(a,b)=sqrt(v_a v_b).
        v=np.ones(self.cutoff+1)
        for n in range(1,len(v)):v[n]=v[n-1]*(delta+n-1)/n
        u=np.array([math.sqrt(v[a]*v[b]) for a,b in self.labels])
        C=csr_matrix((self.sqocc*u[self.mode],self.parent.copy(),self.indptr.copy()),shape=(len(self.N),len(self.N)))
        C.sort_indices();B=C.T.tocsr();B.sort_indices()
        return B,C

    @property
    def nbytes(self):
        return sum(x.nbytes for x in (self.N,self.P,self.J,self.indptr,self.parent,self.mode,self.sqocc))
