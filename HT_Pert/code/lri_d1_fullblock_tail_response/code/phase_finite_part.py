"""Finite parts of all 38 phase-response kernels via convergent regularized sums.
No fit to finite-cutoff data or thermal target. Finite-regulator limits are checked
separately by the shell implementation; component finite parts are scheme-specific.
"""
from pathlib import Path
from functools import lru_cache
from fractions import Fraction as F
import sys,json,time,argparse
import sympy as s
import mpmath as mp
ROOT=Path(__file__).resolve().parents[1]
from phase_response_shell import weights

def mpq(q):return mp.mpf(q.numerator)/q.denominator

@lru_cache(None)
def asympt(a,b,c,d,e,order):
    t,y=s.symbols('t y');z=s.symbols('z')
    def gamma_ratio(A,B):
        logs=[s.S(0)]+[(-1)**(j+1)*(s.bernoulli(j+1,A)-s.bernoulli(j+1,B))/(j*(j+1)) for j in range(1,order+1)]
        coeff=[s.S(1)]
        for n in range(1,order+1):coeff.append(s.expand(sum(j*logs[j]*coeff[n-j] for j in range(1,n+1))/n))
        return sum(v*t**(2*j) for j,v in enumerate(coeff))
    def G(k,d):
        d=s.Rational(d.numerator,d.denominator)
        if k==0:return (1+y)*t**2*sum((-d*t*t)**j for j in range(order+1))/2
        if k!=1:raise ValueError(k)
        beta=s.sqrt(s.pi)*t*gamma_ratio(d,d+s.Rational(1,2))/2
        J=s.S(0)
        for j in range(order+1):
            v=s.rf(s.Rational(1,2),j)/2**j*z**(j+1)
            for r in range(j+1):v/=1+(d+r)*z
            J+=s.series(v,z,0,order+2).removeO()
        return beta+y*J.subs(z,t*t)/(2*s.sqrt(2))
    vb=t**(2-b)*gamma_ratio(s.Rational(b,2),1)/s.gamma(s.Rational(b,2))
    expr=s.expand(vb*G(a,d)*G(c,e))
    poly=s.Poly(expr*t**max(b-2,0),t,y);out={}
    for (p,par),v in poly.terms():
        p-=max(b-2,0)
        if p>2*order+2:continue
        key=(s.Rational(p,2),par%2);out[key]=s.simplify(out.get(key,0)+v)
    return {k:v for k,v in out.items() if v}

@lru_cache(None)
def numeric_asympt(a,b,c,d,e,order,prec):
    return { (mp.mpf(str(p)),par):mp.mpf(str(s.N(v,prec))) for (p,par),v in asympt(a,b,c,d,e,order).items()}

@lru_cache(None)
def G_inf(a,d,k,prec):
    d=mpq(d);a=int(a)
    if a==0:return mp.mpf(int(k%2==0))/(k+d)
    x=mp.mpf(k)+d
    J=mp.hyper([mp.mpf('.5'),1],[x+1],mp.mpf('.5'))/(mp.sqrt(2)*x)
    return (mp.beta(x,mp.mpf('.5'))+(-1)**k*J)/2

def alt_zeta_tail(p,N):
    # sum k=N+1..infinity (-1)^k/k^p
    k=N+1
    return (-1)**k*mp.power(2,-p)*(mp.zeta(p,mp.mpf(k)/2)-mp.zeta(p,mp.mpf(k+1)/2)) if p!=1 else (-1)**k*(mp.digamma(mp.mpf(k+1)/2)-mp.digamma(mp.mpf(k)/2))/2

def regularized(a,b,c,d,e,N,order,prec):
    if b==0:return G_inf(a,d,0,prec)*G_inf(c,e,0,prec)
    coeff=numeric_asympt(a,b,c,d,e,order,prec)
    div={p:v for (p,par),v in coeff.items() if par==0 and p<=1}
    value=G_inf(a,d,0,prec)*G_inf(c,e,0,prec);w=mp.mpf(1)
    for k in range(1,N+1):
        w*= (mp.mpf(b)/2+k-1)/k
        h=w*G_inf(a,d,k,prec)*G_inf(c,e,k,prec)
        value+=h-sum(v*mp.power(k,-p) for p,v in div.items())
    value+=sum(v*(mp.euler if p==1 else mp.zeta(p)) for p,v in div.items())
    for (p,par),v in coeff.items():
        if par:value+=v*alt_zeta_tail(p,N)
        elif p>1:value+=v*mp.zeta(p,N+1)
    return value

def special_constants():
    S=mp.pi/2+mp.asinh(1)
    def fI(v):
        if not v or v==1:return mp.mpf(0)
        u=1-v*v
        if u==1:return 1/mp.sqrt(2)
        if u==0:return mp.mpf(0)
        return 2*v*(u*S-mp.asin(u)-mp.asinh(u))/(1-u**4)
    I=mp.quad(fI,[0,mp.mpf('.25'),mp.mpf('.5'),1])
    def fD(v):
        if not v or v==1:return mp.mpf(0)
        u=1-v*v
        if u==1 or u==0:return mp.mpf(0)
        return 8*v*(mp.log((1+u)/(1-u))+2*mp.atan(u))/(u*(1+u+u*u+u**3))
    D=mp.quad(fD,[0,mp.mpf('.25'),mp.mpf('.5'),1])
    return {(2,0,0):mp.euler+mp.log(2),
            (2,1,0):S*(mp.euler+mp.log(2))/2-2*I,
            (2,2,0):(mp.log(2)+mp.digamma(mp.mpf('.25')))**2/8+mp.polygamma(1,mp.mpf('.25'))/8-D/4},dict(S=str(S),I=str(I),D=str(D))

def main(N=256,order=6,prec=40):
    start=time.perf_counter();mp.mp.dps=prec;spec,ints=special_constants();terms,_=weights();rows=[];total=mp.mpf(0)
    for (a,b,c,d,e),w in terms.items():
        if c==2:a,c=c,a;d,e=e,d
        if a==2:
            assert c==0 and d==1 and e==F(1,2)
            val=spec[a,b,c]
        else:
            val=regularized(a,b,c,d,e,N,order,prec)
            if (a,b,c)==(1,2,1):val-=mp.pi*mp.log(2)/2+7*mp.zeta(3)/(4*mp.pi)
            elif (a,b,c) in [(1,3,0),(0,3,1)]:val-=mp.log(2)
        piece=mpq(w)*val;total+=piece
        rows.append(dict(edges=[a,b,c],d=str(d),e=str(e),weight=str(w),finite_part=str(val),contribution=str(piece)))
        print(a,b,c,d,e,mp.nstr(val,15),flush=True)
    out=dict(N=N,asymptotic_terms=order,precision=prec,finite_part=str(total),integrals=ints,rows=rows,seconds=time.perf_counter()-start,
      scope='Finite part after subtracting A sqrt(mu)+(log(mu))^2/81+B log(mu) from the complete phase-source first response; not a physical thermal coefficient.')
    (ROOT/f'results/phase_finite_part_N{N}_O{order}.json').write_text(json.dumps(out,indent=2)+'\n')
    print('RESULT',out['finite_part'],'seconds',out['seconds']);return out

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--N',type=int,default=256);ap.add_argument('--order',type=int,default=6);ap.add_argument('--dps',type=int,default=40);a=ap.parse_args();main(a.N,a.order,a.dps)
