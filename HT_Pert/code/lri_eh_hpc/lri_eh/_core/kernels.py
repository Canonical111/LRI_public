"""Race-free float64 kernels. Deliberately no fastmath or mixed precision."""
from __future__ import annotations
import numpy as np
from numba import njit,prange

@njit(cache=True,parallel=True,fastmath=False)
def ladder(ptr,index,mode,occ,weights,x,ghost,degree,P,output_parity):
    d=len(ptr)-1;nx=x.shape[1];nlocal=x.shape[0]
    y=np.zeros((d,degree+1),dtype=np.float64)
    for r in prange(d):
        if output_parity>=0 and P[r]%2!=output_parity:continue
        for e in range(ptr[r],ptr[r+1]):
            src=index[e];m=mode[e];o=occ[e]
            for k in range(min(nx,degree+1)):
                val=x[src,k] if src<nlocal else ghost[src-nlocal,k]
                # Exact-zero skipping only; never discard a small nonzero term.
                if val!=0.:
                    for j in range(min(weights.shape[2],degree-k+1)):
                        y[r,k+j]+=weights[m,o,j]*val
    return y

@njit(cache=True,parallel=True,fastmath=False)
def dot_blocks(x,y,degree,diag,block_size):
    """Fixed-size block sums independent of the number of OpenMP threads."""
    nr=x.shape[0];nb=(nr+block_size-1)//block_size
    out=np.zeros((nb,degree+1),dtype=np.float64)
    for b in prange(nb):
        lo=b*block_size;hi=min(nr,lo+block_size)
        for i in range(min(x.shape[1],degree+1)):
            for j in range(min(y.shape[1],degree-i+1)):
                s=0.
                for r in range(lo,hi):
                    val=y[r,j] if len(diag)==0 else diag[r]*y[r,j]
                    s+=x[r,i]*val
                out[b,i+j]+=s
    return out

@njit(cache=True,parallel=True,fastmath=False)
def mask_vertex(m,v,N):
    for i in prange(len(N)):
        if N[i]%2:
            for k in range(m.shape[1]):m[i,k]=0.;v[i,k]=0.

@njit(cache=True,parallel=True,fastmath=False)
def solve_wave(t,psi,E,k,p,P,N):
    for i in prange(len(P)):
        val=t[i]
        for j in range(1,k+1):val-=E[j]*psi[i,k-j]
        den=p*.25-P[i]*.25-N[i]
        if N[i]%2==0 and P[i]%2==p%2 and den!=0.:
            psi[i,k]=val/den
        else:psi[i,k]=0.

@njit(cache=True,parallel=True,fastmath=False)
def vertex_start(c1,b1):
    """Fuse two linear combinations, using c1 as scratch after V is formed."""
    v=np.empty_like(c1)
    for i in prange(c1.shape[0]):
        for k in range(c1.shape[1]):
            v[i,k]=c1[i,k]/12+b1[i,k]/3
            c1[i,k]+=2*b1[i,k]
    return v

@njit(cache=True,parallel=True,fastmath=False)
def add_divided(dst,src,den):
    for i in prange(dst.shape[0]):
        for k in range(dst.shape[1]):dst[i,k]+=src[i,k]/den
