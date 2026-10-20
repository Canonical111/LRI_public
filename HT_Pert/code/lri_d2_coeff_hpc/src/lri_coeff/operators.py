"""Complete vertices and exact annihilation-only energy moments."""
import math
import numpy as np
from . import kernels as K

class Operators:
    def __init__(self,graph,parallel_threshold=5000,backend="native"):
        self.g=graph;self.threshold=parallel_threshold;self.backend=backend
        if backend=="native":
            from . import native
            self.native=native;native.library()
            self.dot=native.poly_dot
        else:self.dot=K.poly_dot
    def lin(self,x,d,n,creation=False,add=None,scale=1.):
        if self.backend=="native":return self.native.apply(self.g,x,d,n,creation,add,scale)
        g=self.g;y=np.empty((n,d+1))
        if creation:
            f=K.creation if n>=self.threshold else K.creation_serial
            f(g.cptr,g.child,g.mode,g.amp,g.u,x,y,n)
        else:
            f=K.annihilation if n>=self.threshold else K.annihilation_serial
            f(g.bptr,g.parent,g.edge,g.mode,g.amp,g.u,x,y,n)
        if add is not None:y+=scale*add
        return y
    def vertices(self,x,d,n):
        # Horner evaluation: no scalar projector is inserted between ladders.
        low=x;v=x;m=x
        for j in range(1,5):
            low=self.lin(low,d,n)
            v=self.lin(v,d,n,True,add=low,scale=math.comb(4,j))
            if j<=2:
                m=self.lin(m,d,n,True,add=low,scale=math.comb(2,j))
        if self.backend=="native":self.native.project(self.g,m,v,n)
        else:
            mask=self.g.Jabs[:n]!=0
            v/=12;m[mask]=0;v[mask]=0
        return m,v
    def moments(self,psi,ids,n,d):
        """<M>=2<psi,B²psi>+2<Bpsi,Bpsi>;
        <V>=(2<psi,B⁴psi>+8<Bpsi,B³psi>+6<B²psi,B²psi>)/12.
        All arrays are real Taylor jets. Angular integration may be omitted ONLY
        in these scalar-to-scalar moments, not in a wavefunction update.
        """
        x=np.zeros((n,len(psi)));x[ids]=psi.T
        b1=self.lin(x,d,n);del x
        b2=self.lin(b1,d,n)
        m=2*self.dot(psi.T,b2[ids],d)+2*self.dot(b1,b1,d)
        v=6*self.dot(b2,b2,d)
        b3=self.lin(b2,d,n);del b2
        v+=8*self.dot(b1,b3,d);del b1
        b4=self.lin(b3,d,n);del b3
        v+=2*self.dot(psi.T,b4[ids],d)
        return np.asarray(m,float),np.asarray(v/12,float)
