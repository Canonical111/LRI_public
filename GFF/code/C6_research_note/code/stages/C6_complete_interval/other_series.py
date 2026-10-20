"""Euler-enclosed alternating periods and geometric polylogarithm series."""
from fractions import Fraction as F
from dyadic import I,evaluate
from elementary import euler_weights

def alternating_periods(constants,env,L7obj,N=900):
    weights=list(euler_weights(N));Z={};L={};info={}
    for r in [1,2,3,5,7]:
        t=F(r,8);a=t+F(1,4);b=t+F(3,4)
        g0=constants.gamma(a)/constants.gamma(b);pref=g0**7
        seq=I(1);harm=I(0);zs=I(0);ls=I(0)
        for n,w in enumerate(weights):
            f=(-1)**n*w*(n+t)*seq
            zs+=f;ls+=f*harm
            harm+=F(1,2*n+2*a)+F(1,2*n+2*a+1)
            seq*=I((F(n)+a)/(F(n)+b))**7
        ze=((t+2)*pref/(1<<N)).upper();le=17*ze
        Z[r]=(pref*zs).inflate(ze);L[r]=(pref*ls).inflate(le)
        info[str(r)]={'Z_tail_bound':str(ze),'harmonic_tail_bound':str(le)}
    L7=sum((evaluate(L7obj['weights'][str(r)],env)*L[r] for r in L),I(0))
    return Z,L7,{'Euler_N':N,'bound_on_log_density_total_variation':17,'shifts':info}

def half_argument(N=700):
    a=I(1);h3=I(0);h5=I(0)
    for n in range(N):
        h3+=a/(2*n+1)**3;h5+=I(F(1,2**n*(n+1)**5))
        a*=F(2*n+1,4*(n+1))
    h3+=I.bounds(0,(2*a/(2*N+1)**3).upper())
    h5+=I.bounds(0,F(1,2**(N-1)*(N+1)**5))
    return h3,h5

def lambda_value(constants,N=1600):
    h1=h2=h3=I(0);zr=I(1);zi=I(0);total=I(0)
    for r in range(1,N+1):
        h1+=F(1,r);h2+=F(1,r*r);h3+=F(1,r**3)
        zr,zi=(zr-zi)/2,(zr+zi)/2
        cr=(constants.z3-h3)/r**2+(3*constants.z2-2*h2)/r**3-3*h1/r**4
        total+=zr*cr
    error=8*F(3,4)**(N+1)/(N+2)**3
    return total.inflate(error),{'N':N,'tail_bound':str(error)}
