"""Rotationally projected, sphere-integrated bath vertices.

The complete vertex is integrated before truncation to rotational states.
Between N<=L states the angular polynomial degree is <=2L, hence L+1
Gauss--Legendre nodes suffice; the azimuthal integral is exact at fixed M.
"""
import math,time
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import LinearOperator
from numpy.polynomial.legendre import leggauss

class ProductOperator:
    def __init__(self,basis,delta,nz,angular=0,backend='tensor',nodes=None):
        self.basis=basis;self.delta=delta;self.nz=nz;self.angular=angular;self.backend='tensor'
        self.fullB=len(basis.N)
        self.S,self.N,self.P,self.keep,self.projection_tests=basis.highest_weight(angular,angular%2)
        self.nB=len(self.N);self.kpar=(self.P%2).astype(np.int64);self.hb=self.N+delta*self.P
        self.dim=self.nB*nz;self.matvec_count=0;self.matvec_seconds=0.
        self.nodes=basis.cutoff+1 if nodes is None else nodes
        z,w=leggauss(self.nodes);W=[np.zeros((self.nB,self.nB)) for _ in range(4)]
        for zi,wi in zip(z,w/2):
            B,C=basis.ladders(delta,zi);As=[self.S]
            for j in range(4):As.append(B@As[-1])
            for k in range(1,5):
                for j in range(k+1):W[k-1]+=wi*math.comb(k,j)*(As[j].T@As[k-j]).toarray()
        # Symmetrization only removes roundoff, not matrix entries.
        self.W=[csr_matrix((a+a.T)*.5) for a in W]
        self.hermiticity_residual=max(float(np.max(abs(a-a.T),initial=0)) for a in W)
        self.parity_residual=max(float(np.max(abs(W[k][(self.kpar[:,None]^self.kpar[None,:])!=((k+1)%2)]),initial=0)) for k in range(4))
        if self.hermiticity_residual>2e-9 or self.parity_residual>2e-9:raise RuntimeError('Sphere operator gate failed')

    def apply(self,x,w,L,field):
        start=time.perf_counter();X=np.asarray(x,dtype=float).reshape(self.nB,self.nz)
        ans=X*(self.hb[:,None]+w.reshape(2,self.nz)[self.kpar^field])
        for j,a in enumerate(self.W):
            Y=a@X
            for pout in (0,1):
                ix=np.flatnonzero((self.kpar^field)==pout);pin=pout^((j+1)%2)
                ans[ix]+=Y[ix]@L[j,pout*self.nz:(pout+1)*self.nz,pin*self.nz:(pin+1)*self.nz].T
        self.matvec_count+=1;self.matvec_seconds+=time.perf_counter()-start
        return ans.ravel()

    def apply_block(self,x,w,L,field):
        return np.column_stack([self.apply(x[:,j],w,L,field) for j in range(x.shape[1])])

    def linear_operator(self,w,L,field,shift=0.):
        def mv(x):return self.apply(x,w,L,field)-shift*np.asarray(x).ravel()
        def mm(x):return self.apply_block(x,w,L,field)-shift*x
        return LinearOperator((self.dim,self.dim),matvec=mv,rmatvec=mv,matmat=mm,dtype=float)

    def bath_powers(self,x):return [a@x for a in self.W]
    def contractions(self,vec,field):
        x=np.asarray(vec).reshape(self.nB,self.nz);z=self.nz
        weights=np.zeros(2*z);corr=np.zeros((4,2*z,2*z));ys=self.bath_powers(x)
        for p in (0,1):
            rows=np.flatnonzero((self.kpar^field)==p);block=x[rows]
            weights[p*z:(p+1)*z]=np.sum(block*block,axis=0)
            for j in range(4):
                pin=p^((j+1)&1)
                corr[j,p*z:(p+1)*z,pin*z:(pin+1)*z]=block.T@ys[j][rows]
        bath=float(np.sum(x*x*self.hb[:,None]));return weights,corr,bath
    @property
    def nbytes(self):
        return self.basis.nbytes+sum(a.data.nbytes+a.indices.nbytes+a.indptr.nbytes for a in [self.S]+self.W)
