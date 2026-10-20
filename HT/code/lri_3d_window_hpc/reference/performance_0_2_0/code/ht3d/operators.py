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
from .kernels import (csr_batch, sparse_apply, combine_serial, combine_parallel,
    pack_local, combine_contiguous_parallel)


def normal_power(B,order):
    C=B.T.tocsr();I=eye(B.shape[0],format='csr');cc=[I];bb=[I]
    for j in range(order):cc.append(C@cc[-1]);bb.append(B@bb[-1])
    ans=csr_matrix(B.shape)
    for j in range(order+1):ans=ans+math.comb(order,j)*(cc[j]@bb[order-j])
    return canonical(ans)


def canonical(a):
    a=a.tocsr();a.sum_duplicates();a.sort_indices();a.eliminate_zeros()
    return a


SPARSE_PARALLEL_MIN_WORK=int(os.environ.get('HT3D_SPARSE_PARALLEL_MIN_WORK','250000'))

if SPARSE_PARALLEL_MIN_WORK<1:raise ValueError('HT3D_SPARSE_PARALLEL_MIN_WORK must be positive')

def spmm(a, x):
    # SciPy is fast on small blocks; row-owned compiled sweeps parallelize large
    # ones. Each output element's sparse accumulation order is unchanged by the
    # thread count. This is independent of BLAS threading used in local products.
    if get_num_threads()>1 and a.nnz*x.shape[1]>=SPARSE_PARALLEL_MIN_WORK:
        return csr_batch(a.indptr,a.indices,a.data,np.ascontiguousarray(x))
    return a @ x


class ProductOperator:
    def __init__(self,basis,delta,nz,angular=0,backend='tensor',nodes=None):
        from numpy.polynomial.legendre import leggauss
        from .block_vertices import build_vertices
        from .rotational_vertices import build_rotational_vertices
        if backend not in ('tensor','gram'):raise ValueError('3D backends: tensor or gram')
        self.basis=basis;self.delta=delta;self.nz=int(nz);self.angular=angular;self.backend=backend
        self.fullB=len(basis.N)
        self.S,self.N,self.P,self.keep,self.projection_tests=basis.highest_weight(angular,angular%2)
        self.nB=len(self.N)
        if not self.nB:raise ValueError('Empty rotational sector')
        self.bpar=(basis.P%2).astype(np.int64);self.kpar=(self.P%2).astype(np.int64)
        self.hb0=basis.N+delta*basis.P;self.hb=self.hb0.copy();self.levels=self.N
        self.hbk=self.hb[self.keep].copy();self.dim=self.nB*self.nz
        self.rows=tuple(np.flatnonzero(self.kpar==p) for p in (0,1))
        self.nodes=basis.cutoff+1 if nodes is None else int(nodes)
        if self.nodes<basis.cutoff+1:raise ValueError('Insufficient exact angular quadrature')
        self.W=None;self.edges=None;self.angular_grams=[];self.B=None;self.C=None
        t=time.perf_counter()
        if backend=='tensor':
            self.vertex_method = 'rotational_trace' if nodes is None else 'polar_quadrature'
            cache=None;saved=None
            params={'L':basis.cutoff,'spin':angular,'x_hex':float(delta).hex(),
                    'method':self.vertex_method,'nodes':self.nodes}
            if getattr(basis,'_cache_dir',None):
                from .cache import ArrayCache,sparse_hash
                params['projector_sha256']=sparse_hash(self.S)
                cache=ArrayCache(basis._cache_dir);saved=cache.load('vertices',params)
            if saved is not None:
                arrays,meta=saved
                self.W=[csr_matrix((arrays[f'data{j}'],arrays[f'indices{j}'],arrays[f'indptr{j}']),
                                   shape=(self.nB,self.nB)) for j in range(4)]
                self.hermiticity_residual=float(meta['hermiticity_residual'])
            else:
                self.W=[canonical(a) for a in (build_rotational_vertices(basis,self.S,self.P,delta,angular)
                    if nodes is None else build_vertices(basis,self.S,self.P,delta,self.nodes))]
                self.hermiticity_residual=max(float(np.max(abs((a-a.T).data),initial=0)) for a in self.W)
                self.W=[canonical((a+a.T)*.5) for a in self.W]
                if cache is not None:
                    arrays={f'{name}{j}':getattr(W,name) for j,W in enumerate(self.W) for name in ('data','indices','indptr')}
                    cache.save('vertices',params,arrays,{'hermiticity_residual':self.hermiticity_residual})
        else:
            self.edges=[csr_matrix((self.nB,self.nB)) for _ in range(4)]
            zz,ww=leggauss(self.nodes)
            for z,w in zip(zz,ww/2):
                if z<0:continue
                if z>0:w*=2
                B,_=basis.ladders(delta,z);v=self.S;ims=[]
                for j in range(4):
                    v=canonical(B@v);e=canonical(self.S.T@v)
                    self.edges[j]+=w*(e+e.T)
                    if j<3:ims.append(v)
                mask=np.zeros(self.fullB,bool)
                for a in ims:mask|=np.diff(a.indptr)>0
                rows=np.flatnonzero(mask)
                ims=[canonical(a[rows]*math.sqrt(w)) for a in ims]
                self.angular_grams.append((ims,[canonical(a.T) for a in ims]))
            self.edges=[canonical(a) for a in self.edges]
            self.hermiticity_residual=0.
        self.build_seconds=time.perf_counter()-t
        self.matvec_count=0;self.matvec_seconds=0.

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
        if get_num_threads()>1 and self.nB*self.nz*self.nz>=250_000:
            ans=combine_contiguous_parallel(*ys,pack_local(L,self.nz),L[3,0,0],w,self.hbk,self.kpar,field,X)
        else:
            ans=combine_serial(*ys,L,w,self.hbk,self.kpar,field,X)
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
        if self.W is not None:return [spmm(a,x) for a in self.W]
        out=[spmm(a,x) for a in self.edges]
        for images,image_t in self.angular_grams:
            a,b,c=[spmm(mat,x) for mat in images]
            u,v,w=image_t
            out[1]+=2*spmm(u,a)
            out[2]+=3*spmm(u,b)+3*spmm(v,a)
            out[3]+=4*spmm(u,c)+6*spmm(v,b)+4*spmm(w,a)
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
        arrs=[self.S]+list(self.W or [])+list(self.edges or [])
        for a,b in self.angular_grams:arrs.extend(a+b)
        return (sum(a.data.nbytes+a.indices.nbytes+a.indptr.nbytes for a in arrs)
                +self.basis.nbytes+self.hb0.nbytes+self.hb.nbytes+self.hbk.nbytes+self.keep.nbytes+self.kpar.nbytes+self.bpar.nbytes)

class _SectorBasisView:
    """Metadata only: the lower scalar space is an exact restriction of the parent.

    Annihilation followed by creation never exceeds both endpoint free levels;
    therefore restricting each completed normally ordered W_j is exact. This view
    is used only in the vacuum hierarchy, not for a new angular construction.
    """
    def __init__(self, cutoff, N, P):
        self.cutoff=int(cutoff);self.N=N;self.P=P
    @property
    def nbytes(self):return self.N.nbytes+self.P.nbytes


def restrict_operator(parent, cutoff):
    """Exact lower-cutoff scalar operator, with independent mutable window shifts.

    Shares no mutable CSR storage or window tables with its parent. Does not
    duplicate full auxiliary Fock graphs, angular SVDs, or quadrature work.
    """
    if parent.angular!=0 or parent.W is None or not 0<=cutoff<=parent.basis.cutoff:
        raise ValueError('Restriction requires a tensor scalar parent and valid cutoff')
    chosen=np.flatnonzero(parent.N<=cutoff)
    if not np.array_equal(chosen,np.arange(len(chosen))):
        raise RuntimeError('Expected the fixed angular basis ordered by bath level')
    a=object.__new__(ProductOperator)
    n=len(chosen)
    a.N=parent.N[:n].copy();a.P=parent.P[:n].copy()
    a.basis=_SectorBasisView(cutoff,a.N,a.P)
    a.delta=parent.delta;a.nz=parent.nz;a.angular=0;a.backend='tensor'
    a.fullB=a.nB=n;a.dim=n*a.nz
    a.keep=np.arange(n,dtype=np.int64);a.kpar=(a.P%2).astype(np.int64);a.bpar=a.kpar.copy()
    a.hb0=a.N+a.delta*a.P;a.hb=a.hb0.copy();a.hbk=a.hb.copy();a.levels=a.N
    a.rows=tuple(np.flatnonzero(a.kpar==p) for p in (0,1))
    a.S=eye(n,format='csr');a.nodes=parent.nodes
    a.W=[canonical(W[:n,:n].copy()) for W in parent.W]
    a.edges=None;a.angular_grams=[];a.B=a.C=None
    a.projection_tests=dict(parent.projection_tests)
    a.vertex_method='exact_parent_restriction';a.hermiticity_residual=parent.hermiticity_residual
    a.build_seconds=0.;a.matvec_count=0;a.matvec_seconds=0.
    return a
