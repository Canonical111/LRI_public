"""Exact endpoint completion of the trial, NOT physical coefficient data."""
from formal_series import *
from spectral_model import *

TAU=s.Symbol('tau'); PI=s.Symbol('pi0'); LOG2=s.Symbol('log2')

def correction_rows(tau=TAU):
    R=s.Rational
    return {
        (8,1,None):-R(158684509,23040)-2*tau/3,
        (10,0,None):R(182483575,20736)+4*tau/3,
        (6,1,(0,1)):R(904279,160)+2*tau/3,
        (8,0,(0,1)):-R(8757751,1296)-4*tau/3,
        (6,1,(1,1)):-R(3037,4),
        (8,0,(1,1)):R(2852,3),
        (6,1,(2,1)):R(596,3)-tau/2,
        (8,0,(2,1)):tau}

# Exact (value, y-partial, t-partial) at y=t=1/2.
ENDPOINT_KERNELS={
    (0,1):(1-2/PI,0,4/PI),
    (0,2):(1,0,2),
    (0,3):(1+2/(3*PI),0,-4/(3*PI)),
    (1,1):(1-PI/4,-PI*(3-4*LOG2)/4,PI/4),
    (1,2):(s.Rational(2,3),-s.Rational(4,9),s.Rational(16,9)),
    (2,1):(1-8/(3*PI),-64*LOG2/(3*PI)+128/(9*PI),16/(9*PI)),
    (2,2):(s.Rational(1,2),-s.Rational(1,2),s.Rational(3,2))}

def endpoint_monomial(a,b,ab=None):
    v=s.Rational(1,2)**(a+b); row=[v,2*b*v,2*a*v]
    if ab is None:return row
    k,ky,kt=ENDPOINT_KERNELS[ab]
    return [v*k,row[1]*k+v*ky,row[2]*k+v*kt]

def exact_endpoint(coeffs, completed=False,tau=TAU):
    row=[s.Rational(-3,4),s.Integer(1),s.Integer(-4)]
    for key,co in coeffs.items():
        vv=endpoint_monomial(2,key[1]) if key[0]=='R' else endpoint_monomial(2,key[2],key[:2])
        row=[s.expand(a+co*b) for a,b in zip(row,vv)]
    if completed:
        for (a,b,ab),co in correction_rows(tau).items():
            vv=endpoint_monomial(a,b,ab)
            row=[s.expand(aa+co*bb) for aa,bb in zip(row,vv)]
    return row

def completed_F(coeffs,ys,n,tau=TAU):
    out=evaluate_F(coeffs,ys,n)
    for (a,b,ab),co in correction_rows(tau).items():
        if a>=n:continue
        tmp=power(ys,b,n-a)
        if ab is not None:tmp=mul(tmp,gamma_ratio(*ab,ys,n-a),n-a)
        out=series_add(out,shift(scale(tmp,co,n-a),a,n),n)
    return out

def numeric_kernel(a,b,y,t):
    return 1-mp.gamma(1+a*y)**2*mp.rgamma(1+a*y+b*t)*mp.rgamma(1+a*y-b*t)

def numeric_function(coeffs,completed=False,tau=0):
    def number(q):
        q=s.Rational(q);return mp.mpf(int(q.p))/int(q.q)
    cc={k:number(v) for k,v in coeffs.items()}
    extras={k:number(v) for k,v in correction_rows(s.Rational(tau)).items()} if completed else {}
    def fun(y,t):
        val=y*y-4*t*t
        for k,v in cc.items():
            if k[0]=='R':val+=t*t*v*y**k[1]
            else:
                a,b,j=k;val+=t*t*v*y**j*numeric_kernel(a,b,y,t)
        for (a,b,ab),v in extras.items():
            val+=v*t**a*y**b*(numeric_kernel(*ab,y,t) if ab is not None else 1)
        return val
    return fun
