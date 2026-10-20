"""Elementary/gamma/zeta constants with finite, rigorous remainder bounds."""
from fractions import Fraction as F
from functools import lru_cache
from math import comb
import sympy as sp
from dyadic import I,log,exp,machin_pi

def euler_weights(N):
    den=1<<N;c=1;total=0
    for n in range(N):
        total+=c
        yield F(den-total,den)
        c=c*(N-n)//(n+1)

def eta_zeta(s,N):
    if s<=1:raise ValueError('s>1 required')
    total=I(0)
    for n,w in enumerate(euler_weights(N)):total+=(-1)**n*w*I(F(1,(n+1)**s))
    # The positive Hausdorff-moment Euler remainder is at most 2**(-N).
    total+=I.bounds(0,F(1,1<<N))
    return total/(1-F(1,2**(s-1)))

def catalan(N):
    total=I(0)
    for n,w in enumerate(euler_weights(N)):total+=(-1)**n*w*I(F(1,(2*n+1)**2))
    return total+I.bounds(0,F(1,1<<N))

class Constants:
    def __init__(self,euler_N=900,gamma_shift=256,gamma_M=100):
        self.euler_N=euler_N;self.gamma_shift=gamma_shift;self.gamma_M=gamma_M
        self.pi=machin_pi();self.ell=log(I(2));self.rt2=I(2).sqrt()
        self.z2=self.pi**2/6
        self.z3=eta_zeta(3,euler_N);self.z5=eta_zeta(5,euler_N)
        self.G=catalan(euler_N)
        self._gamma={F(1):I(1),F(1,2):self.pi.sqrt()}
    def gamma(self,a):
        a=F(a)
        if a<=0:raise ValueError('positive gamma argument required')
        if a in self._gamma:return self._gamma[a]
        if a>1:
            value=(a-1)*self.gamma(a-1);self._gamma[a]=value;return value
        N=self.gamma_shift;M=self.gamma_M;X=a+N;xx=I(X)
        lg=(xx-F(1,2))*log(xx)-xx+log(2*self.pi)/2
        for k in range(1,M):
            bb=F(sp.bernoulli(2*k));lg+=I(bb/(2*k*(2*k-1)*X**(2*k-1)))
        neglected=F(sp.bernoulli(2*M))/(2*M*(2*M-1)*X**(2*M-1))
        lg+=I.bounds(min(F(0),neglected),max(F(0),neglected))
        product=F(1)
        for j in range(N):product*=a+j
        lg-=log(I(product))
        value=exp(lg)
        self._gamma[a]=value
        return value
    def environment(self):
        Q=self.gamma(F(1,4))**4/self.pi
        c=((2+self.rt2).sqrt()/2)**7;s=((2-self.rt2).sqrt()/2)**7
        return {'pi':self.pi,'ell':self.ell,'A':self.pi+4*self.ell,
                'Q':Q,'G':self.G,'z3':self.z3,'z5':self.z5,'c7':c,'s7':s}
