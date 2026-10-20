"""Exact Kronecker-free Hamiltonians: projected vertices or sparse Gram images.

The new gram backend stores A_j=B^j S (j=1,2,3) and E_j=S^T B^j S.
W4=E4+E4^T+4 A1^T A3+6 A2^T A2+4 A3^T A1. This is an
identity, not a tail/particle/angular approximation. All arrays are float64.
"""
import math
import time
import os
import numpy as np
from scipy.sparse import eye,csr_matrix
from scipy.sparse.linalg import LinearOperator
from numba import get_num_threads
from .kernels import csr_batch, sparse_apply, combine_serial, combine_parallel


def normal_power(B,order):
    C=B.T.tocsr();I=eye(B.shape[0],format='csr');cc=[I];bb=[I]
    for j in range(order):cc.append(C@cc[-1]);bb.append(B@bb[-1])
    ans=csr_matrix(B.shape)
    for j in range(order+1):ans=ans+math.comb(order,j)*(cc[j]@bb[order-j])
    return canonical(ans)


def canonical(a):
    a=a.tocsr();a.sum_duplicates();a.sort_indices();a.eliminate_zeros()
    return a


SPARSE_PARALLEL_MIN_WORK=int(os.environ.get('HT2D_SPARSE_PARALLEL_MIN_WORK','250000'))

if SPARSE_PARALLEL_MIN_WORK<1:raise ValueError('HT2D_SPARSE_PARALLEL_MIN_WORK must be positive')

def spmm(a, x):
    # SciPy is fast on small blocks; row-owned compiled sweeps parallelize large
    # ones. Each output element's sparse accumulation order is unchanged by the
    # thread count. This is independent of BLAS threading used in local products.
    if get_num_threads()>1 and a.nnz*x.shape[1]>=SPARSE_PARALLEL_MIN_WORK:
        return csr_batch(a.indptr,a.indices,a.data,np.ascontiguousarray(x))
    return a @ x


class ProductOperator:
    def __init__(self,basis,delta,nz,angular=0,backend='tensor'):
        if backend not in ('tensor','ladder','gram'):
            raise ValueError('Unknown backend; choose tensor, ladder or gram')
        self.basis=basis;self.delta=delta;self.nz=nz;self.angular=angular;self.backend=backend
        self.fullB=len(basis.N)
        candidates=np.flatnonzero(basis.J==angular)
        self.S=None
        if angular==0:
            if hasattr(basis,'mirror'):
                partners=basis.mirror[candidates]
            else:
                # Compatibility with independently supplied legacy bases.
                index={state:i for i,state in enumerate(basis.states)}
                swap={k:basis.labels.index((b,a)) for k,(a,b) in enumerate(basis.labels)}
                partners=np.array([index[tuple(sorted(swap[k] for k in basis.states[i]))] for i in candidates])
            ok=partners>=candidates;self.keep=candidates[ok];partners=partners[ok]
            distinct=partners!=self.keep
            col=np.arange(len(self.keep))
            sr=np.concatenate((self.keep,partners[distinct]));sc=np.concatenate((col,col[distinct]))
            sv=np.concatenate((np.where(distinct,1/math.sqrt(2),1.),np.full(int(distinct.sum()),1/math.sqrt(2))))
            self.S=csr_matrix((sv,(sr,sc)),shape=(self.fullB,len(self.keep)))
        else:
            self.keep=candidates
        self.nB=len(self.keep)
        self.bpar=(basis.P%2).astype(np.int64);self.kpar=self.bpar[self.keep]
        self.hb0=basis.N+delta*basis.P;self.hb=self.hb0.copy();self.dim=self.nB*nz
        self.levels=basis.N[self.keep]
        self.hbk=self.hb[self.keep].copy()
        self.rows=tuple(np.flatnonzero(self.kpar==p) for p in (0,1))
        self.B,self.C=basis.ladders(delta)
        self.W=None;self.images=None;self.edges=None;self.image_t=None
        self.auxiliary_rows=0
        if backend in ('tensor','gram'):
            S=self.S
            if S is None:
                S=csr_matrix((np.ones(self.nB),(self.keep,np.arange(self.nB))),shape=(self.fullB,self.nB))
            if backend=='tensor':
                images=[S]
                for _ in range(4):images.append(canonical(self.B@images[-1]))
                self.W=[]
                for k in range(1,5):
                    a=csr_matrix((self.nB,self.nB))
                    for j in range(k+1):a=a+math.comb(k,j)*(images[j].T@images[k-j])
                    self.W.append(canonical(a))
                self.ptrs=tuple(a.indptr for a in self.W);self.cols=tuple(a.indices for a in self.W);self.values=tuple(a.data for a in self.W)
            else:
                images=[];self.edges=[];v=S
                for j in range(1,5):
                    v=canonical(self.B@v)
                    e=canonical(S.T@v);self.edges.append(canonical(e+e.T))
                    if j<4:images.append(v)
                occupied=np.zeros(self.fullB,bool)
                for a in images:occupied|=np.diff(a.indptr)>0
                rows=np.flatnonzero(occupied);self.auxiliary_rows=len(rows)
                self.images=[canonical(a[rows]) for a in images]
                self.image_t=[canonical(a.T) for a in self.images]
                # Do not retain full-space ladder arrays for a backend not using
                # them after construction. The topology stays in basis.
                self.B=self.C=None
        self.matvec_count=0;self.matvec_seconds=0.

    def ladder(self,x,creation=False):
        a=self.C if creation else self.B
        if a is None:raise RuntimeError('Full ladders are not stored by the gram backend')
        return spmm(a,x)

    def _product(self, X, w, L, field):
        ys=self.bath_powers(X)
        ans=L[3,0,0]*ys[3]
        z=self.nz;k=X.shape[1]//z
        out=ans.reshape(self.nB,z,k)
        for bathpar,rows in enumerate(self.rows):
            if not len(rows):continue
            p=field^bathpar
            for j in range(3):
                pin=p^((j+1)&1)
                y=ys[j][rows].reshape(len(rows),z,k)
                block=L[j,p*z:(p+1)*z,pin*z:(pin+1)*z]
                if k==1:
                    out[rows,:,0]+=y[:,:,0]@block.T
                else:
                    # BLAS acts on the local index; no cross-vector mixing.
                    flat=y.transpose(0,2,1).reshape(len(rows)*k,z)
                    val=(flat@block.T).reshape(len(rows),k,z).transpose(0,2,1)
                    out[rows]+=val
            diagonal=w[p*z:(p+1)*z][None,:]+self.hbk[rows,None]
            out[rows]+=diagonal[:,:,None]*X[rows].reshape(len(rows),z,k)
        return out.reshape(self.nB,z*k)

    def apply(self,x,w,L,field):
        start=time.perf_counter();X=np.ascontiguousarray(np.asarray(x,dtype=np.float64).reshape(self.nB,self.nz))
        ys=self.bath_powers(X)
        combine=combine_parallel if get_num_threads()>1 and self.nB*self.nz**2>=250000 else combine_serial
        ans=combine(*ys,L,w,self.hbk,self.kpar,field,X)
        self.matvec_count+=1;self.matvec_seconds+=time.perf_counter()-start
        return ans.ravel()

    def apply_block(self,x,w,L,field):
        start=time.perf_counter();k=x.shape[1]
        X=np.ascontiguousarray(x,dtype=np.float64).reshape(self.nB,self.nz*k)
        ans=self._product(X,w,L,field)
        self.matvec_count+=k;self.matvec_seconds+=time.perf_counter()-start
        return ans.reshape(self.dim,k)

    def linear_operator(self,w,L,field,shift=0.):
        def mv(x):return self.apply(x,w,L,field)-shift*np.asarray(x).reshape(-1)
        def mm(x):return self.apply_block(x,w,L,field)-shift*x
        return LinearOperator((self.dim,self.dim),matvec=mv,rmatvec=mv,matmat=mm,dtype=np.float64)

    def bath_powers(self,x):
        x=np.ascontiguousarray(x,dtype=np.float64)
        if self.W is not None:
            return [spmm(a,x) for a in self.W]
        if self.backend=='gram':
            a,b,c=[spmm(mat,x) for mat in self.images]
            u,v,w=self.image_t
            out=[spmm(mat,x) for mat in self.edges]
            out[1]+=2*spmm(u,a)
            out[2]+=3*spmm(u,b)+3*spmm(v,a)
            out[3]+=4*spmm(u,c)+6*spmm(v,b)+4*spmm(w,a)
            return out
        if self.S is None:
            X=np.zeros((self.fullB,x.shape[1]));X[self.keep]=x
        else:X=self.S@x
        powers=[X]
        for _ in range(4):powers.append(self.ladder(powers[-1]))
        out=[]
        for j in range(1,5):
            a=X.copy()
            for k in range(j-1,-1,-1):a=self.ladder(a,True)+math.comb(j,k)*powers[j-k]
            out.append(a[self.keep] if self.S is None else self.S.T@a)
        return out

    def contractions(self,vec,field):
        x=np.asarray(vec).reshape(self.nB,self.nz);z=self.nz
        weights=np.zeros(2*z);corr=np.zeros((4,2*z,2*z));ys=self.bath_powers(x)
        for p in (0,1):
            rows=self.rows[p^field];block=x[rows]
            weights[p*z:(p+1)*z]=np.sum(block*block,axis=0)
            for j in range(4):
                pin=p^((j+1)&1)
                corr[j,p*z:(p+1)*z,pin*z:(pin+1)*z]=block.T@ys[j][rows]
        bath=float(np.sum((x*x)*self.hbk[:,None]))
        return weights,corr,bath

    def set_bath_shift(self,shift):
        if shift is None:self.hb=self.hb0.copy()
        else:
            shift=np.asarray(shift,dtype=np.float64)
            if shift.shape!=self.hb0.shape or not np.all(np.isfinite(shift)):raise ValueError('Invalid bath shift')
            self.hb=self.hb0+shift
        self.hbk=self.hb[self.keep].copy()

    def level_weights(self,vec):
        X=np.asarray(vec).reshape(self.nB,self.nz)
        return np.bincount(self.levels,weights=np.sum(X*X,axis=1),minlength=self.basis.cutoff+1)

    @property
    def nbytes(self):
        arrs=[self.B,self.C,self.S]+list(self.W or [])+list(self.images or [])+list(self.image_t or [])+list(self.edges or [])
        return (sum(a.data.nbytes+a.indices.nbytes+a.indptr.nbytes for a in arrs if a is not None)
                +self.basis.nbytes+self.hb0.nbytes+self.hb.nbytes+self.hbk.nbytes+self.keep.nbytes+self.kpar.nbytes+self.bpar.nbytes)
