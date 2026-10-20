"""Exact rational hierarchy of telescoping counterterms for the C6 wheel."""
from fractions import Fraction as F
from math import comb
from functools import lru_cache
import sympy as sp

def poly_mul(a,b):
    c=[F(0)]*(len(a)+len(b)-1)
    for i,x in enumerate(a):
        if x:
            for j,y in enumerate(b):c[i+j]+=x*y
    return c

def poly_eval(a,x):
    r=F(0)
    for c in reversed(a):r=r*x+c
    return r

@lru_cache(None)
def basis_series(j,degree):
    """Coefficient of y^k, y=(t+1/4)^-2, in rational difference of phi_j."""
    out=[F(0)]*(degree+1)
    if j == -1:
        for k in range(1,degree+1):
            d=2*k-1
            num=sum((-2)**i*comb(3,i)*comb(d-i+3,3)*3**(d-i) for i in range(min(3,d)+1))
            out[k]=F(2*num,4**d)
    elif j>=0:
        def A(k):
            if j==0:return comb(k+3,3)*3**k
            return sum(comb(j+p-1,p)*comb(j+3+k-p,k-p)*3**(k-p) for p in range(k+1))
        for k in range(j+2,degree+1):
            d=2*(k-j-2)+1
            out[k]=F(2*(A(d)-2*A(d-1)),4**d)
    else:raise ValueError('j >= -1 required')
    return tuple(out)

@lru_cache(None)
def delta_coefficient(k):
    """delta(t) ~ sum_{k>=0} d_k/(t+1/4)^(2k+2)."""
    return F(int(sp.euler(2*k))*(2*k+1),2*16**k)

@lru_cache(None)
def coefficients(M):
    if not isinstance(M,int) or M<0:raise ValueError('M must be a nonnegative integer')
    a=[]
    for j in range(-1,M+1):
        k=j+2
        z=delta_coefficient(k-1)-sum(a[h+1]*basis_series(h,M+2)[k] for h in range(-1,j))
        lead=3 if j==-1 else 2*j+5
        a.append(z/lead)
    return tuple(a)

def phi(j,t):
    t=F(t); y=t-F(1,4)
    if j==-1:return y**3/(t-F(1,2))**4
    return y/(t**j*(t-F(1,2))**(j+4))

def q(M,t):
    return sum(c*phi(j,t) for j,c in zip(range(-1,M+1),coefficients(M)))

def R(M,t):
    t=F(t)
    return q(M,t)-((t+F(1,2))/(t+1))**4*q(M,t+1)

@lru_cache(None)
def rational_remainder_polynomials(M):
    """R_M=P/D and R_M-U_M=y^(M+3)*E/D, exactly."""
    deg=2*M+4
    D=poly_mul([F(comb(M,i)*(-1)**i,16**i) for i in range(M+1)],
               [F(comb(M+4,i)*(-9)**i,16**i) for i in range(M+5)])
    a=coefficients(M)
    rs=[sum(a[j+1]*basis_series(j,deg+3)[k] for j in range(-1,M+1)) for k in range(deg+4)]
    prod=poly_mul(D,rs)
    assert all(v==0 for v in prod[deg+1:deg+4])
    P=prod[:deg+1]
    U=[F(0)]+[delta_coefficient(k) for k in range(M+2)]
    DU=poly_mul(D,U)
    diff=[(P[k] if k<len(P) else F(0))-DU[k] for k in range(len(DU))]
    assert all(v==0 for v in diff[:M+3])
    E=diff[M+3:]
    return tuple(P),tuple(D),tuple(E)

def tail_bound(M,N):
    if N<2:raise ValueError('N>=2 required')
    _,D,E=rational_remainder_polynomials(M)
    y0=1/F(4*N+1,4)**2
    K=abs(delta_coefficient(M+2))+poly_eval([abs(x) for x in E],y0)/poly_eval(D,y0)
    return F(23,9*(2*M+7))*K/F(4*N-3,4)**(2*M+7)

