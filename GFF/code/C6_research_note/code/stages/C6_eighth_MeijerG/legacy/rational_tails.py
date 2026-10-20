"""Finite exact telescopers for positive rational-ratio hypergeometric sums.
No convergence of a formal infinite asymptotic expansion is assumed.
"""
from fractions import Fraction as F
from math import comb
from functools import lru_cache

def mul(a,b):
    o=[F(0)]*(len(a)+len(b)-1)
    for i,x in enumerate(a):
        for j,y in enumerate(b):o[i+j]+=x*y
    return o

def prod_linear(shifts):
    out=[F(1)]
    for a in shifts:out=mul(out,[1,F(a)])
    return out

def horner(a,y):
    out=F(0)
    for c in reversed(a):out=out*y+c
    return out

def binomial_integer(a,k):
    if a>=0:return comb(a,k) if k<=a else 0
    return (-1)**k*comb(k-a-1,k)

@lru_cache(None)
def construct(up,down,M):
    up=tuple(map(F,up));down=tuple(map(F,down))
    if len(up)!=len(down) or min(up+down)<=0 or M<1:
        raise ValueError('positive equal-degree shifts and M>=1 required')
    decay=sum(down)-sum(up)
    if decay<=1:raise ValueError('series must have decay exponent >1')
    A=prod_linear(up);B=prod_linear(down)
    # Series of A(y)/B(y), only to the finite order needed for construction.
    R=[]
    for k in range(M+2):
        R.append((A[k] if k<len(A) else F(0))-sum(B[j]*R[k-j] for j in range(1,min(k,len(B)-1)+1)))
    def basis(j,k):
        m=k-j+1
        return -sum(R[h]*binomial_integer(1-j,m-h) for h in range(m+1))
    c=[]
    for j in range(M+1):
        assert basis(j,j)==decay+j-1
        target=F(1) if j==0 else F(0)
        c.append((target-sum(c[k]*basis(k,j) for k in range(j)))/(decay+j-1))
    # E=y*(1+y)^(M-1)*B*(1-q+R*q_next), an exact polynomial.
    Db=mul(B,[F(comb(M-1,j)) for j in range(M)])
    part1=[F(0)]+Db
    part2=mul(Db,c)
    Qnext=[F(0)]*(M+1)
    for j,cj in enumerate(c):
        for k in range(M-j+1):Qnext[j+k]+=cj*comb(M-j,k)
    part3=mul(A,Qnext)
    n=max(len(part1),len(part2),len(part3));E=[F(0)]*n
    for sign,p in [(1,part1),(-1,part2),(1,part3)]:
        for k,x in enumerate(p):E[k]+=sign*x
    assert all(x==0 for x in E[:M+2])
    return tuple(c),tuple(E),decay

def ratio(n,up,down):
    r=F(1)
    for a,b in zip(up,down):r*=F(n)+a;r/=F(n)+b
    return r

def enclosure(up,down,N=256,M=80):
    up=tuple(map(F,up));down=tuple(map(F,down))
    if N<2:raise ValueError('N>=2 required')
    c,E,decay=construct(up,down,M)
    y=F(1,N)
    eps=horner(tuple(map(abs,E)),y)/y
    q=N*horner(c,y)
    assert 0<=eps<1 and q>0
    term=F(1);partial=F(0)
    for n in range(N):partial+=term;term*=ratio(n,up,down)
    center=term*q
    lo=partial+center/(1+eps);hi=partial+center/(1-eps)
    # Independent rational residual checks, not used to choose coefficients.
    for n in [N,N+1,2*N+7]:
        qn=n*horner(c,F(1,n));qn1=(n+1)*horner(c,F(1,n+1))
        r=1-qn+ratio(n,up,down)*qn1
        A=prod_linear(up);B=prod_linear(down);yy=F(1,n)
        rhs=horner(E,yy)/(yy*horner(B,yy)*(1+yy)**(M-1))
        assert r==rhs and abs(r)<=eps
    return (lo,hi),{'N':N,'M':M,'decay':str(decay),'epsilon':eps,'tail_center':center,
                    'width':hi-lo,'coefficient_count':len(c),'residual_vanishing_order':M+2}
