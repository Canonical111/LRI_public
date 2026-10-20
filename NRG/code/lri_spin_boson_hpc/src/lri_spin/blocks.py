"""Occupation-major exact parity blocks; no global Kronecker matrix."""
from __future__ import annotations
import numpy as np
from scipy.linalg import eigh, eig_banded

class Layout:
    def __init__(self, sizes, nb, sector):
        self.sector=sector; self.nb=nb
        self.sizes=tuple(int(sizes[sector^(n&1)]) for n in range(nb))
        self.offsets=np.r_[0,np.cumsum(self.sizes)]
        self.slices=tuple(slice(int(self.offsets[n]),int(self.offsets[n+1])) for n in range(nb))
        self.dimension=int(self.offsets[-1])
    def split(self,U):
        return tuple(U[s,:] for s in self.slices)

class HamiltonianBlock:
    def __init__(self, layout, diagonal, upper):
        self.layout=layout; self.diagonal=diagonal; self.upper=upper
    def apply(self,U):
        X=self.layout.split(U); Y=np.empty_like(U,order='F')
        for n,sl in enumerate(self.layout.slices):
            y=self.diagonal[n][:,None]*X[n]
            if n:
                y+=self.upper[n-1].T@X[n-1]
            if n+1<self.layout.nb:
                y+=self.upper[n]@X[n+1]
            Y[sl]=y
        return Y
    def dense(self):
        d=self.layout.dimension
        H=np.zeros((d,d),dtype=np.float64,order='F')
        for n,sl in enumerate(self.layout.slices):
            ids=np.arange(sl.start,sl.stop); H[ids,ids]=self.diagonal[n]
            if n+1<self.layout.nb:
                nxt=self.layout.slices[n+1]
                H[sl,nxt]=self.upper[n];H[nxt,sl]=self.upper[n].T
        return H
    def banded(self):
        D=self.layout.dimension
        bw=max((self.layout.sizes[n]+self.layout.sizes[n+1]-1 for n in range(self.layout.nb-1)),default=0)
        band=np.zeros((bw+1,D),order='F')
        for n,sl in enumerate(self.layout.slices):
            band[0,sl]=self.diagonal[n]
            if n+1<self.layout.nb:
                ns=self.layout.slices[n+1]
                # Lower triangle H[next,current]; exact band storage ab[i-j,j].
                col=np.arange(sl.start,sl.stop)
                for i in range(ns.start,ns.stop):
                    band[i-col,col]=self.upper[n][:,i-ns.start]
        return band
    def solve(self,keep,full=False,backend='dense'):
        d=self.layout.dimension;k=min(keep,d)
        if backend=='dense':
            H=self.dense()
            e,U=eigh(H,check_finite=False,overwrite_a=True,
                       driver='evd' if full else 'evr',
                       subset_by_index=None if full else (0,k-1))
        elif backend=='banded':
            H=self.banded()
            e,U=eig_banded(H,lower=True,eigvals_only=False,overwrite_a_band=True,
                          select='a' if full else 'i',select_range=(0,k-1),check_finite=False)
        else:
            raise ValueError('backend must be dense or banded')
        return e,U


def make_block(en, b_odd, onsite, hopping, rescale, nb, sector):
    """b_odd[p] has output parity p, input parity 1-p."""
    L=Layout(tuple(map(len,en)),nb,sector)
    ds=tuple(rescale*en[sector^(n&1)]+n*onsite for n in range(nb))
    upper=tuple(hopping*np.sqrt(n+1)*b_odd[1-(sector^(n&1))].T for n in range(nb-1))
    return HamiltonianBlock(L,ds,upper)


def tangent_apply(layout,U,de,db,hop,scale):
    """Apply dH without constructing any dense dH or Kronecker product."""
    X=layout.split(U);Y=np.empty_like(U,order='F');s=layout.sector
    for n,sl in enumerate(layout.slices):
        p=s^(n&1)
        y=scale*(de[p]@X[n])
        if n:
            y+=hop*np.sqrt(n)*(db[p]@X[n-1])
        if n+1<layout.nb:
            y+=hop*np.sqrt(n+1)*(db[1-p].T@X[n+1])
        Y[sl]=y
    return Y


def project_old(vectors,layouts,ops,odd=False):
    """Project an old operator by occupation slices (operator parity exact)."""
    result=[]
    spl=[l.split(v) for l,v in zip(layouts,vectors)]
    for s in (0,1):
        t=1-s if odd else s
        out=np.zeros((vectors[s].shape[1],vectors[t].shape[1]))
        for n in range(layouts[s].nb):
            p=s^(n&1)
            out+=spl[s][n].T@(ops[p]@spl[t][n])
        result.append(out)
    return result


def project_b(vectors,layouts,left=None,right=None):
    """<left| b_new |right>; left/right default to retained eigenvectors."""
    left=vectors if left is None else left
    right=vectors if right is None else right
    ls=[l.split(v) for l,v in zip(layouts,left)]
    rs=[l.split(v) for l,v in zip(layouts,right)]
    result=[]
    for s in (0,1):
        out=np.zeros((left[s].shape[1],right[1-s].shape[1]))
        for n in range(layouts[s].nb-1):
            out+=np.sqrt(n+1)*(ls[s][n].T@rs[1-s][n+1])
        result.append(out)
    return result
