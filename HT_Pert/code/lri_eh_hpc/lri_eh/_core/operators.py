from __future__ import annotations
import math,time
import numpy as np
from .basis import RankedBasis
from .kernels import ladder,dot_blocks,mask_vertex,vertex_start,add_divided
from .parallel import Halo,global_sum

def square_root_jets(nmodes:int,degree:int)->np.ndarray:
    # Same float64 recurrence as the original; Taylor coefficients, not derivatives.
    out=np.zeros((degree+1,nmodes),dtype=np.float64)
    v=np.zeros(degree+1);v[0]=1.
    for n in range(nmodes):
        if n:
            old=v.copy();v=(n-.5)/n*old;v[1:]-=old[:-1]/(2*n)
        u=np.zeros(degree+1);u[0]=math.sqrt(v[0])
        for k in range(1,degree+1):
            u[k]=(v[k]-np.dot(u[1:k],u[k-1:0:-1]))/(2*u[0])
        out[:,n]=u
    return out

class Space(RankedBasis):
    def __init__(self,cutoff,pmax,qmax,degree,comm=None,memory_limit_gib=None,basis_cache=None,compact_single=False):
        super().__init__(cutoff,pmax,qmax,comm,memory_limit_gib,basis_cache,compact_single)
        u=square_root_jets(cutoff,degree)
        self.weights=np.ascontiguousarray(u.T[:,None,:]*np.sqrt(np.arange(pmax+1,dtype=np.float64))[None,:,None])
        self.haloC=Halo(self,self.creation);self.haloB=Halo(self,self.annihilation)
        self.edges_bytes=self.creation.nbytes+self.annihilation.nbytes
        self.timings={'basis':self.build_seconds,'ladder':0.,'inner':0.,'vertices':0.}
        self.ladder_calls=0

    def linear(self,x,degree,creation=False,parity=-1):
        if degree<0 or degree>=self.weights.shape[2]:raise ValueError('Invalid jet degree')
        if x.dtype!=np.float64 or x.ndim!=2 or len(x)!=self.dim:raise ValueError('Expected local float64 row-major jet array')
        e,h=(self.creation,self.haloC) if creation else (self.annihilation,self.haloB)
        t=time.perf_counter();ghost=h.exchange(x)
        y=ladder(e.ptr,e.index,e.mode,e.occ,self.weights,x,ghost,degree,self.P,1-parity if parity>=0 else -1)
        self.timings['ladder']+=time.perf_counter()-t;self.ladder_calls+=1
        return y

    def inner(self,x,y,degree,diag=None):
        t=time.perf_counter()
        blocks=dot_blocks(x,y,degree,np.empty(0,dtype=np.float64) if diag is None else diag,4096)
        # math.fsum reduces block partial sums, retaining float64 input/output.
        out=np.array([math.fsum(blocks[:,k]) for k in range(degree+1)])
        out=global_sum(self.comm,out)
        self.timings['inner']+=time.perf_counter()-t
        return out

    def sample(self,x,p):
        # Zero-mode reference |p> has DFS rank p in every admissible basis.
        v=x[p-self.begin] if self.begin<=p<self.end else 0.
        return float(global_sum(self.comm,np.array([v]))[0])

    def vertices(self,psi,degree,parity=-1):
        """Exact Horner factorization: 9 ladder sweeps instead of 17.

        V=(C^4+4 C^3 B+6 C^2 B^2+4 C B^3+B^4)/12;
        M=C(C+2B)+B^2. Operators are never commuted; parity projected LAST.
        """
        t0=time.perf_counter()
        opposite=1-parity if parity>=0 else -1
        b1=self.linear(psi,degree,parity=parity)
        c1=self.linear(psi,degree,True,parity=parity)
        v=vertex_start(c1,b1)
        m=self.linear(c1,degree,True,parity=opposite)
        del c1
        b2=self.linear(b1,degree,parity=opposite);del b1
        add_divided(m,b2,1.)
        v=self.linear(v,degree,True,parity=opposite);add_divided(v,b2,2.)
        b3=self.linear(b2,degree,parity=parity);del b2
        v=self.linear(v,degree,True,parity=parity);add_divided(v,b3,3.)
        b4=self.linear(b3,degree,parity=opposite);del b3
        v=self.linear(v,degree,True,parity=opposite);add_divided(v,b4,12.);del b4
        mask_vertex(m,v,self.N)
        self.timings['vertices']+=time.perf_counter()-t0
        return m,v

def divide_series(a,b,degree):
    out=np.zeros(degree+1)
    if b[0]==0:raise ZeroDivisionError('zero constant in norm series')
    for k in range(degree+1):
        out[k]=((a[k] if k<len(a) else 0.)-sum(b[j]*out[k-j] for j in range(1,min(k,len(b)-1)+1)))/b[0]
    return out

def quotient_components(space,psi,degree,parity=-1):
    norm=space.inner(psi,psi,degree)
    f=space.inner(psi,psi,degree,space.Efree)
    f[1:]+=space.inner(psi,psi,degree-1,space.F1)
    q=degree-1
    # Stream the B^j psi intermediates; do not keep five dense series alive.
    opposite=1-parity if parity>=0 else -1
    b1=space.linear(psi,q,parity=parity);b2=space.linear(b1,q,parity=opposite)
    m=2*space.inner(psi,b2,q)+2*space.inner(b1,b1,q)
    v=.5*space.inner(b2,b2,q)
    b3=space.linear(b2,q,parity=parity);del b2
    v+=(2/3)*space.inner(b1,b3,q);del b1
    b4=space.linear(b3,q,parity=opposite);del b3
    v+=space.inner(psi,b4,q)/6;del b4
    return divide_series(f,norm,degree),divide_series(m,norm,degree),divide_series(v,norm,degree)
