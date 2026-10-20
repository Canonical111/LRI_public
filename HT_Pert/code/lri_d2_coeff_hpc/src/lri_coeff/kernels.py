"""Row-owned sparse Taylor convolutions. No transpose-scatter races or fastmath.

Node-major arrays keep the short Taylor axis contiguous. Every edge stores one
oscillator label and one amplitude; mode jets are shared across all edges.
"""
import numpy as np
from numba import njit, prange

def _creation(ptr,child,mode,amp,u,x,y,n):
    nd=y.shape[1];nx=x.shape[1]
    for i in prange(n):
        for k in range(nd):y[i,k]=0.
        for e in range(ptr[i],ptr[i+1]):
            c=child[e];md=mode[e];w=amp[e]
            for j in range(min(nd,u.shape[1])):
                coeff=w*u[md,j]
                if coeff==0:continue  # exact zeros only (e.g. zero-mode derivatives)
                for l in range(min(nx,nd-j)):
                    y[i,l+j]+=coeff*x[c,l]

def _annihilation(ptr,parent,edge,mode,amp,u,x,y,n):
    nd=y.shape[1];nx=x.shape[1]
    for i in prange(n):
        for k in range(nd):y[i,k]=0.
        for e in range(ptr[i],ptr[i+1]):
            p=parent[e]
            if p>=n:break  # rows in transpose adjacency are monotonically sorted
            f=edge[e];md=mode[f];w=amp[f]
            for j in range(min(nd,u.shape[1])):
                coeff=w*u[md,j]
                if coeff==0:continue
                for l in range(min(nx,nd-j)):
                    y[i,l+j]+=coeff*x[p,l]

creation=njit(cache=True,parallel=True,fastmath=False)(_creation)
creation_serial=njit(cache=True,parallel=False,fastmath=False)(_creation)
annihilation=njit(cache=True,parallel=True,fastmath=False)(_annihilation)
annihilation_serial=njit(cache=True,parallel=False,fastmath=False)(_annihilation)

@njit(cache=True,parallel=True)
def axpy_inplace(y,x,a):
    for i in prange(len(y)):
        for k in range(y.shape[1]):y[i,k]+=a*x[i,k]

@njit(cache=True,parallel=True)
def project(x,scalar,div):
    for i in prange(len(x)):
        for k in range(x.shape[1]):
            x[i,k]=x[i,k]/div if scalar[i] else 0.

# The dot coefficient routine is deliberately outside numba: extended accumulators
# match the reference precision. Thread-parallel deterministic reductions are in
# the optional native helper; NumPy remains the independent fallback.
def poly_dot(x,y,d):
    out=np.zeros(d+1,dtype=np.longdouble)
    for k in range(d+1):
        for j in range(max(0,k-y.shape[1]+1),min(k+1,x.shape[1])):
            out[k]+=np.sum(x[:,j]*y[:,k-j],dtype=np.longdouble)
    return out

def vector_moments(psi,energy,particles,d):
    h=len(psi)-1
    norms=np.zeros(d+1);me=np.zeros(d+1);mf=np.zeros(d)
    for i in range(h+1):
        for j in range(h+1):
            k=i+j
            if k>d:continue
            a=psi[i]*psi[j]
            norms[k]+=float(np.sum(a,dtype=np.longdouble))
            me[k]+=float(np.sum(a*energy,dtype=np.longdouble))
            if k<d:mf[k]+=float(np.sum(a*(-particles/4),dtype=np.longdouble))
    return norms,me,mf
