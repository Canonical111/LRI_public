"""Three-dimensional primitive period identities and numerical evaluators.
The asymptotic tails used below are numerical accelerations, not interval bounds.
All formula-side hypergeometric moments have fixed parameters and no derivatives.
"""
from functools import lru_cache
import mpmath as mp


def conv(a,b,K):
    c=[mp.mpc(0)]*(K+1)
    for i,x in enumerate(a):
        if not x: continue
        for j in range(min(len(b)-1,K-i)+1): c[i+j]+=x*b[j]
    return c


def coeffs(A,B,r,delta,m,K):
    """f(n)=(n+delta)^m [Gamma(n+A)/Gamma(n+B)]^r.
    f(n) ~ n^(-alpha) sum c[k]/n^k, alpha=r(B-A)-m.
    """
    logs=[mp.mpc(0)]+[r*(-1)**(j+1)*(mp.bernpoly(j+1,A)-mp.bernpoly(j+1,B))/(j*(j+1)) for j in range(1,K+1)]
    ex=[mp.mpc(1)]
    for j in range(1,K+1): ex.append(sum(h*logs[h]*ex[j-h] for h in range(1,j+1))/j)
    poly=[mp.binomial(m,j)*delta**j for j in range(m+1)]
    return conv(ex,poly,K)


def ztail(s,N,epsilon):
    if epsilon==1: return mp.zeta(s,N)
    return (-1)**N*mp.power(2,-s)*(mp.zeta(s,mp.mpf(N)/2)-mp.zeta(s,mp.mpf(N+1)/2))


def gamma_moment(A,B,r,delta,m,epsilon=1,N=100,K=36):
    A,B,delta=map(mp.mpc,(A,B,delta))
    alpha=r*(B-A)-m
    if mp.re(alpha)<=1: raise ValueError('absolute moment convergence requires alpha>1')
    c=coeffs(A,B,r,delta,m,K)
    h=(mp.gamma(A)/mp.gamma(B))**r
    partial=mp.mpc(0)
    for n in range(N):
        partial+=epsilon**n*(n+delta)**m*h
        h*=((n+A)/(n+B))**r
    return partial+sum(c[k]*ztail(alpha+k,N,epsilon) for k in range(K+1))


def U(r,m,epsilon,u,N=100,K=36,literal=False):
    u=mp.mpc(u); a=mp.mpf(1)/8
    if literal:
        return u**m*(mp.gamma(u+a)/mp.gamma(u+1-a))**r*mp.hyper([1]+[u+a]*r+[u+1]*m,[u+1-a]*r+[u]*m,epsilon)
    return gamma_moment(u+a,u+1-a,r,u,m,epsilon,N,K)


def Psi(r,m,epsilon,u,N=100,K=36,literal=False):
    u=mp.mpc(u);a=mp.mpf(1)/8
    s1=mp.sin(mp.pi*(u+a))**r
    s2=epsilon*(-1)**m*mp.sin(mp.pi*(a-u))**r
    # Exact zeros matter at u=a; don't force evaluation of the cancelled term.
    first=s1*U(r,m,epsilon,u,N,K,literal)
    second=0 if abs(s2)<mp.eps**(mp.mpf(3)/4) else s2*U(r,m,epsilon,1-u,N,K,literal)
    return first+second


def tail_coefficients(c,alpha,epsilon,K):
    """Tail from n=k+1. For +: k^(1-alpha)*sum T_i/k^i.
    For -: (-1)^(k+1) k^(-alpha)*sum T_i/k^i.
    """
    out=[mp.mpc(0)]*(K+1)
    for j in range(K+1):
        s=alpha+j
        if epsilon==1:
            out[j]+=c[j]/(s-1)
            if j+1<=K: out[j+1]-=c[j]/2
            for h in range(1,(K-j)//2+1):
                out[j+2*h]+=c[j]*mp.bernpoly(2*h,0)/mp.factorial(2*h)*mp.rf(s,2*h-1)
        else:
            out[j]+=c[j]/2
            for h in range(1,(K-j+1)//2+1):
                k=2*h-1
                out[j+k]-=c[j]*(2**(2*h)-1)*mp.bernpoly(2*h,0)/mp.factorial(2*h)*mp.rf(s,k)
    return out


def ordered(r,m,n,epsilon,t,N=100,K=36):
    """Ordered positive quadrant sum of A_m(k) B_n(j), 0<=j<=k.
    k=ell+j. This is a direct accelerated evaluation of the stated Horn term,
    NOT an evaluation using the physical period as input.
    """
    t=mp.mpc(t); q=mp.mpf(3)/4
    A=q+t; B=2*q+t; C=1-q+t; D=1+t
    da=t+mp.mpf(5)/8; db=t+mp.mpf(1)/8
    alpha=3*mp.mpf(r)/4-m; beta=3*mp.mpf(r)/4-n
    ca=coeffs(A,B,r,da,m,K); cb=coeffs(C,D,r,db,n,K)
    btotal=gamma_moment(C,D,r,db,n,epsilon,N,K)
    ha=(mp.gamma(A)/mp.gamma(B))**r
    hb=(mp.gamma(C)/mp.gamma(D))**r
    prefix=mp.mpc(0); val=mp.mpc(0)
    for k in range(N):
        prefix+=epsilon**k*(k+db)**n*hb
        val+=epsilon**k*(k+da)**m*ha*prefix
        ha*=((k+A)/(k+B))**r
        hb*=((k+C)/(k+D))**r
    val+=btotal*sum(ca[j]*ztail(alpha+j,N,epsilon) for j in range(K+1))
    tb=tail_coefficients(cb,beta,epsilon,K)
    prod=conv(ca,tb,K)
    exponent=alpha+beta-(1 if epsilon==1 else 0)
    val-=epsilon*sum(prod[j]*mp.zeta(exponent+j,N) for j in range(K+1))
    return val


def V(r,t,N=100,K=36):
    if r in (3,4):return 2*(ordered(r,1,0,1,t,N,K)-ordered(r,0,1,1,t,N,K))
    if r==7:return 8*(ordered(7,3,1,-1,t,N,K)-ordered(7,1,3,-1,t,N,K))
    raise ValueError('r must be 3,4,7')


def middle(r,t,N=100,K=36):
    t=mp.mpc(t); x=t+mp.mpf(5)/8;y=mp.mpf(7)/8-t
    if r in (3,4):
        return 2*(U(r,1,1,x,N,K)*U(r,0,1,y,N,K)+U(r,0,1,x,N,K)*U(r,1,1,y,N,K))
    return 8*mp.tan(mp.pi*(mp.mpf(3)/4+2*t))*(U(7,3,-1,x,N,K)*U(7,1,-1,y,N,K)-U(7,1,-1,x,N,K)*U(7,3,-1,y,N,K))


def Xi(r,t,N=100,K=36):
    t=mp.mpc(t);q=mp.mpf(3)/4;tp=1-q-t
    f=lambda v: -mp.cos(2*mp.pi*v)/2
    D=mp.sin(mp.pi*t)*mp.sin(mp.pi*(t+q))
    if t==0:
        return f(t)**r*V(r,t,N,K)*(-1 if r==7 else 1)
    if r in (3,4):return f(t)**r*V(r,t,N,K)+f(tp)**r*V(r,tp,N,K)+D**r*middle(r,t,N,K)
    return mp.tan(mp.pi*(q+2*t))*(f(t)**7*V(7,t,N,K)-f(tp)**7*V(7,tp,N,K))+D**7*middle(7,t,N,K)


def amplitudes(N=100,K=36,literal=False):
    u=mp.mpf(1)/8
    a3=Psi(3,0,1,u,N,K,literal)/mp.cos(mp.pi*u)
    b3=Psi(3,1,1,u,N,K,literal)/mp.sin(mp.pi*u)
    a4=Psi(4,0,1,mp.mpf(1)/4,N,K,literal)
    b4=Psi(4,1,1,mp.mpf(1)/4,N,K,literal)
    mat=mp.matrix([[mp.sin(2*mp.pi*k*u) for k in range(1,4)] for u in [mp.mpf(1)/8,mp.mpf(1)/4,mp.mpf(3)/8]])
    coeff=[]
    for m in (1,3):
        vals=mp.matrix([Psi(7,m,-1,u,N,K,literal) for u in [mp.mpf(1)/8,mp.mpf(1)/4,mp.mpf(3)/8]])
        coeff.append(mp.lu_solve(mat,vals))
    h1,h3=coeff
    aa=h3[1]*h1[0]-h3[0]*h1[1]
    bb=h3[1]*h1[2]-h3[2]*h1[1]
    return {'a3':a3,'b3':b3,'a4':a4,'b4':b4,'h1':list(h1),'h3':list(h3),'aa':aa,'bb':bb}


def expected_product(r,t,amp):
    t=mp.mpc(t);theta=2*mp.pi*(t+mp.mpf(3)/8)
    if r==3:return -2*amp['a3']*amp['b3']
    if r==4:return 4*amp['a4']*amp['b4']*mp.cos(theta)
    z=mp.cos(theta);a=amp['aa'];b=amp['bb']
    return 32*z*(1-z*z)*(-a-3*b+4*b*z*z)


def ordinary_odd7(t,amp):
    z=mp.cos(2*mp.pi*(mp.mpc(t)+mp.mpf(3)/8));a=amp['aa'];b=amp['bb']
    return 16*z*(1-z*z)*(-a-3*b+4*b*z*z)


def periods(N=100,K=36,amp=None):
    if amp is None:amp=amplitudes(N,K)
    pi=mp.pi;rt=mp.sqrt(2)
    x30=Xi(3,0,N,K)
    Q=rt*mp.sqrt(pi)/3*(-amp['a3']*amp['b3']-3*x30)
    x40=Xi(4,0,N,K);x4h=Xi(4,mp.mpf(1)/8,N,K)
    P4=2*pi*x40-10*pi*x4h+(14*rt-20)*pi*amp['a4']*amp['b4']
    a=amp['aa'];b=amp['bb']
    ts=[mp.mpf(0),mp.mpf(1)/16,-mp.mpf(1)/16]
    ps=[];xs=[]
    for t in ts:
        x=Xi(7,t,N,K);xs.append(x)
        u=mp.cos(4*pi*(t+mp.mpf(3)/8))
        ps.append((x-ordinary_odd7(t,amp))/(1-u))
    F=-35*ps[0]+(22+13/rt)*ps[1]+(22-13/rt)*ps[2]
    P5=4*rt*pi**mp.mpf('1.5')*F-448*pi**mp.mpf('1.5')*(2*b-a)
    return {'Q3':Q,'P4_3':P4,'P5_3':P5,'Xi3_0':x30,'Xi4_0':x40,'Xi4_1_8':x4h,'Xi7_samples':xs,'reduced_polynomial_samples':ps,'amplitudes':amp}


def gamma_amplitudes():
    """Dixon and Rogers--Dougall evaluations; no fit."""
    g=mp.gamma(mp.mpf(1)/4)
    return {'a3b3':g**10/(16*mp.sqrt(2)*mp.pi**4),
            'b4':g**6/(16*mp.pi**mp.mpf('2.5'))}


def boundary(r,t,N=100,K=36):
    t=mp.mpc(t);x=t+mp.mpf(5)/8;y=t+mp.mpf(1)/8
    ry=(mp.gamma(y+mp.mpf(1)/8)/mp.gamma(y+mp.mpf(7)/8))**r
    if r in (3,4):return 2*ry*(U(r,1,1,x,N,K)-y*U(r,0,1,x,N,K))
    return 8*ry*(y*U(7,3,-1,x,N,K)-y**3*U(7,1,-1,x,N,K))


def Xi_axis(r,sigma,N=100,K=36):
    """Only one ordered Horn evaluation on t=-3/8+i*sigma.
    The other tail is its conjugate minus an ordinary boundary term.
    """
    t=-mp.mpf(3)/8+mp.j*sigma
    f=-mp.cos(2*mp.pi*t)/2
    D=mp.sin(mp.pi*t)*mp.sin(mp.pi*(t+mp.mpf(3)/4))
    vr=V(r,t,N,K);br=boundary(r,t,N,K)
    second=mp.conj(vr-br)
    if r in (3,4):
        return mp.re(f**r*vr+mp.conj(f)**r*second+D**r*middle(r,t,N,K))
    tan=mp.tan(mp.pi*(mp.mpf(3)/4+2*t))
    return mp.re(tan*(f**7*vr-mp.conj(f)**7*second)+D**7*middle(7,t,N,K))


def complex_periods(N=100,K=36,amp=None):
    if amp is None:amp=amplitudes(N,K)
    pi=mp.pi;s4=mp.log(2)/(4*pi)
    x4=Xi_axis(4,s4,N,K)
    p4=8*pi*(3*mp.sqrt(2)*amp['a4']*amp['b4']-x4)
    s7=mp.acosh(mp.mpf(22)/13)/(4*pi)
    x7=Xi_axis(7,s7,N,K);t7=-mp.mpf(3)/8+mp.j*s7
    a=amp['aa'];b=amp['bb']
    e0=Xi(7,0,N,K)-ordinary_odd7(0,amp)
    es=x7-ordinary_odd7(t7,amp)
    p5=2*mp.sqrt(2)*pi**mp.mpf('1.5')/11*(29*e0-mp.mpf(2197)/9*es)-448*pi**mp.mpf('1.5')*(2*b-a)
    return {'P4_3_complex':p4,'P5_3_complex':p5,'sigma4':s4,'sigma7':s7,'Xi4_axis':x4,'Xi7_axis':x7}
