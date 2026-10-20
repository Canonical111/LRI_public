"""A rational-cubic-in-pi enclosure for the central wheel.
It uses the inherited fourth-power rational hierarchy and a newly derived
sixth-power hierarchy. Finite, global sech-Taylor remainders bound both tails.
No numerical reference value is used in any bound or interval endpoint.
"""
from fractions import Fraction as F
from functools import lru_cache
from math import comb
from pathlib import Path
import sys,json,time
from hierarchy4 import delta_coefficient,coefficients as coeff4,q as q4,poly_mul,poly_eval,rational_remainder_polynomials
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
ROOT=Path(__file__).resolve().parent

@lru_cache(None)
def basis6(j,degree):
    # Coefficient of y^k in R6(t)/w, w=1/(t+1/4), y=w^2.
    def AA(m):
        if j==0:return comb(m+5,5)*3**m
        return sum(comb(j+p-1,p)*comb(j+5+m-p,m-p)*3**(m-p) for p in range(m+1))
    out=[F(0)]*(degree+1)
    for k in range(j,degree+1):
        d=2*(k-j)+1
        num=sum(comb(6,i)*(-2)**i*AA(d-i) for i in range(min(6,d)+1))
        out[k]=F(2*num,4**d)
    return tuple(out)
@lru_cache(None)
def coeff6(L):
    out=[]
    for j in range(L+1):
        rem=4*delta_coefficient(j)-sum(out[r]*basis6(r,L)[j] for r in range(j))
        out.append(rem/F(2*j+3))
    return tuple(out)
def q6(L,t):
    t=F(t)
    return sum(c*(t-F(1,4))**6/(t**j*(t-F(1,2))**(j+6)) for j,c in enumerate(coeff6(L)))
def R6(L,t):
    t=F(t);return q6(L,t)-((t+F(1,2))/(t+1))**6*q6(L,t+1)
@lru_cache(None)
def polynomials6(L):
    deg=2*L+6
    den=poly_mul([F(comb(L,i)*(-1)**i,16**i) for i in range(L+1)],
                 [F(comb(L+6,i)*(-9)**i,16**i) for i in range(L+7)])
    aa=coeff6(L)
    seq=[sum(aa[j]*basis6(j,deg+2)[k] for j in range(L+1)) for k in range(deg+3)]
    raw=poly_mul(den,seq)
    assert all(c==0 for c in raw[deg:deg+3])
    num=raw[:deg]
    up=[4*delta_coefficient(k) for k in range(L+1)]
    dd=poly_mul(den,up)
    diff=[(num[k] if k<len(num) else F(0))-dd[k] for k in range(len(dd))]
    assert all(c==0 for c in diff[:L+1])
    return tuple(num),tuple(den),tuple(diff[L+1:])
def K4(M,N):
    _,den,e=rational_remainder_polynomials(M);y=1/F(4*N+1,4)**2
    return abs(delta_coefficient(M+2))+poly_eval(tuple(map(abs,e)),y)/poly_eval(den,y)
def K6(L,N):
    _,den,e=polynomials6(L);y=1/F(4*N+1,4)**2
    return 4*abs(delta_coefficient(L+1))+poly_eval(tuple(map(abs,e)),y)/poly_eval(den,y)
def tail_bound(M,N):
    if M<0 or N<2:raise ValueError('M>=0, N>=2 required')
    k4=K4(M,N);k6=K6(M+1,N)
    return (F(8,9)*k4+F(110,189)*k6)/((2*M+7)*F(4*N-3,4)**(2*M+7))
def approximant(N,M):
    """Returns A,B,C,D such that Wcen approximant = A*pi^3+B*pi^2+C*pi+D."""
    a=F(1);de=F(0);A=B=C=D=F(0)
    for n in range(N):
        if n:
            w4=a**4;w6=(4*n+1)*a**6
            A+=F(5,3)*w6; B+=F(8,3)*w4
            C-=5*w6*de;D-=8*w4*de
        a*=F(2*n+1,2*n+2)
        de+=F(4,(2*n+1)**2)-F(1,(n+1)**2)
    D+=8*a**4*q4(M,F(N))
    C+=5*a**6*q6(M+1,F(N))
    return A,B,C,D
# Exact rational interval operations.
def add(a,b):return a[0]+b[0],a[1]+b[1]
def mul(a,b):
    pp=[x*y for x in a for y in b];return min(pp),max(pp)
def pi_interval(terms=360):
    def at(q):
        value=sum((F((-1)**k,(2*k+1)*q**(2*k+1)) for k in range(terms)),F(0))
        err=F(1,(2*terms+1)*q**(2*terms+1))
        return (value,value+err) if terms%2==0 else (value-err,value)
    aa=mul((16,16),at(5));bb=mul((-4,-4),at(239));return add(aa,bb)
def pack(x):return {'numerator':str(x.numerator),'denominator':str(x.denominator)}
def hull(v,bits=700):
    den=1<<bits
    lo=(v[0].numerator*den)//v[0].denominator
    hi=-((-v[1].numerator*den)//v[1].denominator)
    return F(lo,den),F(hi,den)
def package(v):
    v=hull(v)
    return {'lower':pack(v[0]),'upper':pack(v[1]),'width':pack(v[1]-v[0])}
def interval_for(comp,pi):
    value=(F(0),F(0))
    for c in comp:value=add(mul(value,pi),(c,c))
    return value

def exact_checks():
    checks=[]
    for L in range(5):
        num,den,e=polynomials6(L)
        for t in [F(1),F(2),F(13,4),F(101,4)]:
            w=1/(t+F(1,4));y=w*w
            assert R6(L,t)==w*poly_eval(num,y)/poly_eval(den,y)
            checks.append(f'Sixth-power rational identity L={L}, t={t}')
        for j in range(L+1):
            assert basis6(j,L)[j]==2*j+3
    for L in range(4):
        aa=F(1,2)
        total=F(0)
        for n in range(1,12):
            total+=aa**6*R6(L,F(n))
            aa*=F(2*n+1,2*n+2)
        assert total==F(1,2)**6*q6(L,F(1))-aa**6*q6(L,F(12))
        checks.append(f'Sixth-power finite telescope L={L}')
    return checks

def main():
    st=time.time();checks=exact_checks();pi=pi_interval();assert pi[1]<F(22,7)
    records=[];raw=[]
    for N,M in [(64,12),(128,25),(256,40)]:
        comp=approximant(N,M);val=interval_for(comp,pi);err=tail_bound(M,N)
        inter=(val[0]-err,val[1]+err);raw.append(inter)
        record={'N':N,'M4':M,'M6':M+1,'coefficients_cubic_in_pi':dict(zip(['pi3','pi2','pi1','one'],map(pack,comp))),
           'arithmetic_only_width':pack(val[1]-val[0]),'tail_bound':pack(err),'Wcentral':package(inter)}
        records.append(record)
        print('N M',N,M,'tail',float(err),'width',float(inter[1]-inter[0]),'seconds',time.time()-st,flush=True)
    assert all(a[0]<=b[0]<b[1]<=a[1] for a,b in zip(raw,raw[1:]))
    data={'scope':'Rational interval of the newly specified central series, not the full upstream C6 graph sum.',
          'method':'Finite rational harmonic sum and exactly telescoped finite-order fourth/sixth-power tail corrections. Global finite Taylor bound, not a convergent-asymptotic-series assumption.',
          'checks':checks,'check_count':len(checks),'nested':True,'pi':package(pi),'enclosures':records,'seconds':time.time()-st}
    (ROOT/'results/rational_intervals.json').write_text(json.dumps(data,indent=2)+'\n')
if __name__=='__main__':main()
