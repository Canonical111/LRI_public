"""Row-owned float64 kernels; no fastmath, no scatter/atomic operations."""
import numpy as np
from numba import njit, prange

@njit(cache=True,parallel=True)
def csr_batch(ptr,col,data,x):
    out=np.zeros_like(x)
    for i in prange(len(ptr)-1):
        for q in range(ptr[i],ptr[i+1]):
            j=col[q];w=data[q]
            for a in range(x.shape[1]):out[i,a]+=w*x[j,a]
    return out

@njit(cache=True,parallel=True)
def tensor_action(ptrs,cols,values,L,w,hb,bpar,field,x):
    nb,z=x.shape;out=np.empty_like(x)
    for i in prange(nb):
        p=field^bpar[i]
        acc=np.zeros((3,z),np.float64)
        for a in range(z):out[i,a]=(w[p*z+a]+hb[i])*x[i,a]
        for j in range(4):
            for q in range(ptrs[j][i],ptrs[j][i+1]):
                col=cols[j][q];v=values[j][q]
                if j<3:
                    for a in range(z):acc[j,a]+=v*x[col,a]
                else:
                    for a in range(z):out[i,a]+=L[3,p*z+a,p*z+a]*v*x[col,a]
        for j in range(3):
            pin=p^((j+1)&1)
            for a in range(z):
                s=0.
                for b in range(z):s+=L[j,p*z+a,pin*z+b]*acc[j,b]
                out[i,a]+=s
    return out

@njit(cache=True,parallel=True)
def mix_add(out,x,M,bpar,field_out,degree,factor):
    z=x.shape[1]
    for i in prange(len(x)):
        p=field_out^bpar[i];pin=p^(degree&1)
        for a in range(z):
            s=0.
            for b in range(z):s+=M[p*z+a,pin*z+b]*x[i,b]
            out[i,a]+=factor*s
    return out

@njit(cache=True,parallel=True)
def diagonal_add(out,x,w,hb,bpar,field):
    z=x.shape[1]
    for i in prange(len(x)):
        p=field^bpar[i]
        for a in range(z):out[i,a]+=(w[p*z+a]+hb[i])*x[i,a]
    return out

@njit(cache=True,parallel=True)
def tensor_multi(ptrs,cols,values,L,w,hb,bpar,field,x):
    nb,z,k=x.shape;out=np.empty_like(x)
    for i in prange(nb):
        p=field^bpar[i];acc=np.zeros((3,z,k),np.float64)
        for a in range(z):
            for r in range(k):out[i,a,r]=(w[p*z+a]+hb[i])*x[i,a,r]
        for j in range(4):
            for q in range(ptrs[j][i],ptrs[j][i+1]):
                col=cols[j][q];v=values[j][q]
                if j<3:
                    for a in range(z):
                        for r in range(k):acc[j,a,r]+=v*x[col,a,r]
                else:
                    for a in range(z):
                        for r in range(k):out[i,a,r]+=L[3,p*z+a,p*z+a]*v*x[col,a,r]
        for j in range(3):
            pin=p^((j+1)&1)
            for a in range(z):
                for b in range(z):
                    v=L[j,p*z+a,pin*z+b]
                    for r in range(k):out[i,a,r]+=v*acc[j,b,r]
    return out

@njit(cache=True,parallel=True)
def mix_multi(out,x,M,bpar,field_out,degree):
    nb,z,k=x.shape
    for i in prange(nb):
        p=field_out^bpar[i];pin=p^(degree&1)
        for a in range(z):
            for b in range(z):
                v=M[p*z+a,pin*z+b]
                for r in range(k):out[i,a,r]+=v*x[i,b,r]
    return out

@njit(cache=True)
def csr_serial(ptr,col,data,x):
    out=np.zeros_like(x)
    for i in range(len(ptr)-1):
        for q in range(ptr[i],ptr[i+1]):
            j=col[q];w=data[q]
            for a in range(x.shape[1]):out[i,a]+=w*x[j,a]
    return out

@njit(cache=True)
def mix_serial(out,x,M,bpar,field_out,degree,factor):
    z=x.shape[1]
    for i in range(len(x)):
        p=field_out^bpar[i];pin=p^(degree&1)
        for a in range(z):
            s=0.
            for b in range(z):s+=M[p*z+a,pin*z+b]*x[i,b]
            out[i,a]+=factor*s
    return out

# Avoid launching a parallel team for tiny per-action sparse/dense kernels.
# This affects execution only: identical loop order within every output element.
PARALLEL_MIN_WORK=2_000_000

def sparse_apply(ptr,col,data,x):
    fun=csr_serial if len(data)*x.shape[1]<PARALLEL_MIN_WORK else csr_batch
    return fun(ptr,col,data,x)

def local_mix(out,x,M,bpar,field_out,degree,factor):
    fun=mix_serial if len(x)*x.shape[1]**2<PARALLEL_MIN_WORK else mix_add
    return fun(out,x,M,bpar,field_out,degree,factor)

@njit(cache=True)
def diagonal_serial(out,x,w,hb,bpar,field):
    z=x.shape[1]
    for i in range(len(x)):
        p=field^bpar[i]
        for a in range(z):out[i,a]+=(w[p*z+a]+hb[i])*x[i,a]
    return out

def diagonal_apply(out,x,w,hb,bpar,field):
    fun=diagonal_serial if x.size<PARALLEL_MIN_WORK else diagonal_add
    return fun(out,x,w,hb,bpar,field)
