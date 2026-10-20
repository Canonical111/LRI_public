"""Kronecker-free field-parity-packed product Hamiltonian.

Tensor backend: materialize ONLY bath W1..W4, never H or Kronecker terms.
Ladder backend: store only B and B^dagger; 14 shared ladder sweeps and three local contractions per action.
Both are algebraically identical to the reference product regulator.
"""
import math,time
import numpy as np
from scipy.sparse import eye,csr_matrix
from scipy.sparse.linalg import LinearOperator
from .kernels import csr_batch,tensor_action,mix_add,diagonal_add,tensor_multi,mix_multi,sparse_apply,local_mix,diagonal_apply


def normal_power(B,order):
    C=B.T.tocsr();I=eye(B.shape[0],format='csr');cc=[I];bb=[I]
    for j in range(order):cc.append(C@cc[-1]);bb.append(B@bb[-1])
    ans=csr_matrix(B.shape)
    for j in range(order+1):ans=ans+math.comb(order,j)*(cc[j]@bb[order-j])
    ans=ans.tocsr();ans.sum_duplicates();ans.sort_indices();ans.eliminate_zeros()
    return ans

class ProductOperator:
    def __init__(self,basis,delta,nz,reflection=0,backend='tensor'):
        if backend not in ('tensor','ladder'):raise ValueError('Unknown backend')
        self.basis=basis;self.delta=delta;self.nz=nz;self.reflection=reflection;self.backend=backend
        self.keep=np.flatnonzero(basis.N%2==reflection);self.nB=len(self.keep);self.fullB=len(basis.N)
        self.bpar=(basis.P%2).astype(np.int64);self.kpar=self.bpar[self.keep]
        self.hb=basis.N+delta*basis.P;self.dim=self.nB*nz
        self.B,self.C=basis.ladders(delta)
        self.W=None
        if backend=='tensor':
            self.W=[normal_power(self.B,j)[self.keep][:,self.keep].tocsr() for j in range(1,5)]
            for a in self.W:a.sum_duplicates();a.sort_indices();a.eliminate_zeros()
            self.ptrs=tuple(a.indptr for a in self.W);self.cols=tuple(a.indices for a in self.W);self.values=tuple(a.data for a in self.W)
        self.matvec_count=0;self.matvec_seconds=0.

    def ladder(self,x,creation=False):
        a=self.C if creation else self.B
        return sparse_apply(a.indptr,a.indices,a.data,np.ascontiguousarray(x))

    def apply(self,x,w,L,field):
        start=time.perf_counter();X=np.asarray(x,dtype=np.float64).reshape(self.nB,self.nz)
        if self.backend=='tensor':
            ans=tensor_action(self.ptrs,self.cols,self.values,L,w,self.hb[self.keep],self.kpar,field,np.ascontiguousarray(X))
        else:
            # 14 sparse ladder sweeps, but only three local dense multiplies
            # on the retained reflection sector. Faster than the 8-sweep
            # combined Horner form for the measured dressed local dimensions.
            ys=self.bath_powers(X)
            ans=L[3,0,0]*ys[3]
            for j in range(3):
                local_mix(ans,ys[j],L[j],self.kpar,field,j+1,1.)
            diagonal_apply(ans,X,w,self.hb[self.keep],self.kpar,field)
        self.matvec_count+=1;self.matvec_seconds+=time.perf_counter()-start
        return ans.ravel()

    def apply_block(self,x,w,L,field):
        start=time.perf_counter();k=x.shape[1]
        X=np.ascontiguousarray(x).reshape(self.nB,self.nz,k)
        if self.backend=='tensor':
            ans=tensor_multi(self.ptrs,self.cols,self.values,L,w,self.hb[self.keep],self.kpar,field,X)
        else:
            ys=self.bath_powers(X.reshape(self.nB,self.nz*k))
            ans=(L[3,0,0]*ys[3]).reshape(self.nB,self.nz,k)
            for j in range(3):mix_multi(ans,ys[j].reshape(self.nB,self.nz,k),L[j],self.kpar,field,j+1)
            diag=w.reshape(2,self.nz)[self.kpar^field]+self.hb[self.keep,None]
            ans+=diag[:,:,None]*X
        self.matvec_count+=k;self.matvec_seconds+=time.perf_counter()-start
        return ans.reshape(self.dim,k)

    def linear_operator(self,w,L,field,shift=0.):
        def mv(x):return self.apply(x,w,L,field)-shift*np.asarray(x).reshape(-1)
        def mm(x):return self.apply_block(x,w,L,field)-shift*x
        return LinearOperator((self.dim,self.dim),matvec=mv,rmatvec=mv,matmat=mm,dtype=np.float64)

    def bath_powers(self,x):
        """Complete W_j actions without local matrices, packed by local-index label."""
        if self.W is not None:
            return [sparse_apply(a.indptr,a.indices,a.data,np.ascontiguousarray(x)) for a in self.W]
        X=np.zeros((self.fullB,x.shape[1]));X[self.keep]=x;powers=[X]
        for j in range(4):powers.append(self.ladder(powers[-1]))
        out=[]
        for j in range(1,5):
            a=X.copy()
            for k in range(j-1,-1,-1):a=self.ladder(a,True)+math.comb(j,k)*powers[j-k]
            out.append(a[self.keep])
        return out

    def contractions(self,vec,field):
        """Sufficient small matrices for ANY local-Hamiltonian expectation.
        The moving-subspace Jacobian reuses these instead of large matvecs.
        """
        x=np.asarray(vec).reshape(self.nB,self.nz);z=self.nz
        weights=np.zeros(2*z);corr=np.zeros((4,2*z,2*z))
        ys=self.bath_powers(x)
        for p in (0,1):
            rows=np.flatnonzero((self.kpar^field)==p);block=x[rows]
            weights[p*z:(p+1)*z]=np.sum(block*block,axis=0)
            for j in range(4):
                pin=p^((j+1)&1)
                corr[j,p*z:(p+1)*z,pin*z:(pin+1)*z]=block.T@ys[j][rows]
        bath=float(np.sum((x*x)*self.hb[self.keep,None]))
        return weights,corr,bath

    @property
    def nbytes(self):
        arrs=(self.B,self.C)+tuple(self.W or [])
        return sum(a.data.nbytes+a.indices.nbytes+a.indptr.nbytes for a in arrs)+self.basis.nbytes
