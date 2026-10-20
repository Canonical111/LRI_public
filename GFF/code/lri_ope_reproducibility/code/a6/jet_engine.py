"""Laurent jets of normalized massless convolution and two-loop kite kernels.
Exponents are a*q+b*epsilon, q=d/4.
The base class supplies Gamma products and completion transformations.
Use PolarEngine in polar_reconstruction.py for general two-loop kite jets.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction as F
from itertools import permutations, combinations
from collections import Counter
from functools import lru_cache
import mpmath as mp

@dataclass(frozen=True)
class X:
    a:F=F(0)
    b:F=F(0)
    def __post_init__(self):
        object.__setattr__(self,'a',F(self.a));object.__setattr__(self,'b',F(self.b))
    def __add__(self,o):
        if o==0:return self
        if not isinstance(o,X):return NotImplemented
        return X(self.a+o.a,self.b+o.b)
    __radd__=__add__
    def __neg__(self):return X(-self.a,-self.b)
    def __sub__(self,o):return self+-o
    def __mul__(self,r):return X(self.a*F(r),self.b*F(r))
    __rmul__=__mul__
    def __truediv__(self,r):return self*F(1,r)
    def __bool__(self):return bool(self.a or self.b)
D=X(4);HALF=X(2)

class Engine:
    def __init__(self,d,T,N=8):
        self.d=mp.mpf(d);self.q=self.d/4;self.T=mp.mpf(T);self.N=N
        self.A=mp.digamma(2*self.q)+mp.digamma(1)-2*mp.digamma(self.q)
        self.R=mp.polygamma(1,2*self.q)-mp.polygamma(1,1)
        self.U=mp.polygamma(2,self.q)
        self.V=mp.polygamma(2,1)+mp.polygamma(2,2*self.q)
    def m(self,x):return mp.mpf(x.numerator)/x.denominator if isinstance(x,F) else mp.mpf(x)
    def add(self,*xs):
        out={}
        for x in xs:
            for k,v in x.items():out[k]=out.get(k,mp.mpf(0))+v
        return out
    def scale(self,x,c):return {k:v*self.m(c) for k,v in x.items()}
    def mul(self,*xs):
        out={0:mp.mpf(1)}
        for x in xs:
            y={}
            for k,v in out.items():
                for l,w in x.items():
                    if -8<=k+l<=self.N:y[k+l]=y.get(k+l,mp.mpf(0))+v*w
            out=y
        return out
    def shift(self,x,k,c=1):return {j+k:v*self.m(c) for j,v in x.items() if -8<=j+k<=self.N}
    @lru_cache(None)
    def gamma_log(self,x):
        a=self.m(x.a)*self.q;b=self.m(x.b)
        if a<=0 and a==int(a):
            if b==0:raise ZeroDivisionError(('gamma pole identically',x))
            n=int(-a)
            pref=(-1)**n/(mp.factorial(n)*b)
            coeff=[mp.mpf(0)]+[(mp.polygamma(k-1,1)/mp.factorial(k)+sum(mp.mpf(1)/j**k for j in range(1,n+1))/k)*b**k for k in range(1,self.N+5)]
            return -1,pref,coeff
        pref=mp.gamma(a)
        coeff=[mp.mpf(0)]+[mp.polygamma(k-1,a)*b**k/mp.factorial(k) for k in range(1,self.N+5)]
        return 0,pref,coeff
    def gr(self,nums,dens=()):
        counts=Counter(nums);counts.subtract(dens);counts={x:c for x,c in counts.items() if c}
        zeros=[(x,c) for x,c in counts.items() if x.b==0 and self.m(x.a)*self.q<=0 and self.m(x.a)*self.q==int(self.m(x.a)*self.q)]
        if any(c>0 for x,c in zeros):raise ZeroDivisionError(('uncancelled gamma pole',nums,dens,zeros))
        if zeros:return {}
        p=0;pref=mp.mpf(1);log=[mp.mpf(0)]*(self.N+5)
        for x,c in counts.items():
            px,g,l=self.gamma_log(x);p+=c*px;pref*=g**c
            for k in range(1,len(log)):log[k]+=c*l[k]
        v=[mp.mpf(1)]
        for n in range(1,self.N-p+1):v.append(sum(k*log[k]*v[n-k] for k in range(1,n+1))/n)
        return {p+n:pref*c for n,c in enumerate(v) if -8<=p+n<=self.N}
    def conv(self,a,b):
        return self.gr([HALF,HALF-a,HALF-b,a+b-HALF],[a,b,D-a-b])
    def linear_inverse(self,x,factor=1):
        if x.a!=0 or x.b==0:raise ValueError(('not nonzero infinitesimal',x))
        return {-1:self.m(factor)/self.m(x.b)}
    def infinitesimal(self,x):
        if x.a:raise ValueError(('not infinitesimal',x))
        return {1:self.m(x.b)}
    def completion(self,es):
        a,b,c,f,r=es
        edges=[3*HALF-a-b-c-f-r,a,c,b+f+r-HALF,b,f,a+c+r-HALF,r,D-a-b-r,D-c-f-r]
        pairs=list(combinations(range(5),2));return dict(zip(pairs,edges))
    def direct_kite(self,es):
        a,b,c,f,r=es
        if not r:return self.mul(self.conv(a,b),self.conv(c,f))
        if not a:return self.mul(self.conv(b,r),self.conv(c,f+b+r-HALF))
        if not b:return self.mul(self.conv(a,r),self.conv(f,c+a+r-HALF))
        if not c:return self.mul(self.conv(f,r),self.conv(a,b+f+r-HALF))
        if not f:return self.mul(self.conv(c,r),self.conv(b,a+c+r-HALF))
        return None
    def kite(self,*es):
        ans=self.direct_kite(es)
        if ans is not None:
            return ans
        raise NotImplementedError("Use PolarEngine for nonfactorized kite integrals.")
