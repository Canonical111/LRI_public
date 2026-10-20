"""Numerical checks of NEW binomial sums against the saved period intervals.
Finite asymptotic acceleration is used; this is not a new interval certificate.
"""
from pathlib import Path
from fractions import Fraction as F
from functools import lru_cache
import json,time
import sympy as sp
import mpmath as mp
ROOT=Path(__file__).resolve().parent
MOMENTS={
 'S4':(4,0,0,0),'S4d':(4,0,0,1),
 'S6y':(6,1,0,0),'S6h':(6,0,1,0),'S6hh':(6,0,2,0),
 'S6d':(6,0,0,1),'S6yd':(6,1,0,1),
 'S8y':(8,1,0,0),'S8':(8,0,0,0),'S8yh':(8,1,1,0),
 'S8yhh':(8,1,2,0),'S8h':(8,0,1,0),'S8yd':(8,1,0,1)
}
def rat(q):return mp.mpf(int(q.numerator))/int(q.denominator)
@lru_cache(None)
def coefficients(J):
    b=[F(0)]
    for j in range(1,J+1):
        v=-2*sp.bernoulli(2*j+1,sp.Rational(1,4))/(2*j*(2*j+1))
        b.append(F(int(v.p),int(v.q)))
    H=[F(1,4)]+[j*b[j] for j in range(1,J+1)]
    D=[F(1,2)]+[2*j*(2*j+1)*b[j] for j in range(1,J+1)]
    def mul(a,b):
        return [sum((a[j]*b[k-j] for j in range(k+1)),F(0)) for k in range(J+1)]
    exps={}
    for r in [4,6,8]:
        c=[F(1)]
        for k in range(1,J+1):
            c.append(sum((j*r*b[j]*c[k-j] for j in range(1,k+1)),F(0))/k)
        exps[r]=c
    out={}
    for name,(r,p,h,d) in MOMENTS.items():
        c=exps[r]
        for _ in range(h):c=mul(c,H)
        for _ in range(d):c=mul(c,D)
        out[name]=c
    return out

def moments(N,J):
    a=mp.mpf(1);h=mp.log(2);de=mp.pi**2/3
    out={k:mp.mpf(0) for k in MOMENTS}
    for n in range(N):
        y=mp.mpf(n)+mp.mpf(1)/4
        for name,(r,p,i,j) in MOMENTS.items():
            out[name]+=a**r*y**p*h**i*de**j
        a*=mp.mpf(2*n+1)/(2*n+2)
        h+=mp.mpf(1)/(2*n+2)-mp.mpf(1)/(2*n+1)
        de-=mp.mpf(4)/(2*n+1)**2-mp.mpf(1)/(n+1)**2
    coeff=coefficients(J);x=mp.mpf(N)+mp.mpf(1)/4;zs={}
    for name,(r,p,i,j) in MOMENTS.items():
        base=r//2-p+i+2*j
        for k in range(J+1):
            e=base+2*k
            if e not in zs:zs[e]=mp.zeta(e,x)
        out[name]+=mp.pi**(-r//2)*mp.fsum(rat(c)*zs[base+2*k] for k,c in enumerate(coeff[name]))
    return out

def transformed(S):
    p=mp.pi;rt=mp.sqrt(2);A=p+4*mp.log(2);Q=mp.gamma(mp.mpf(1)/4)**4/p
    Cs=-mp.mpf(105)/4*A*A-9*A*p+60*Q-mp.mpf(2469)/4*p*p
    Cd=-42*A*A-18*A*p+96*Q-1227*p*p
    bs=8*p**4*S['S6y'];bd=4*p**3*S['S4']
    pb=24*p**3*(88*p*S['S6h']+312*S['S6hh']+13*S['S6d'])
    gg=[S['S8y'],S['S8']-16*S['S8yh'],
        256*S['S8yhh']-32*S['S8h']+8*S['S8yd']-8*p*p*S['S8y']]
    yz=p**6*(816+92*rt)*gg[0]-368*p**5*gg[1]+46*rt*p**4*gg[2]
    yk=p**6*(432+48*rt)*gg[0]-192*p**5*gg[1]+24*rt*p**4*gg[2]
    # Expanded central polynomial, independent of the moment-to-period assembly above.
    E=(384*Q-168*A*A-72*A*p-4908*p*p)*S['S4']-3144*S['S4d']
    E+=p*(480*Q-210*A*A-72*A*p-4938*p*p)*S['S6y']
    E+=50688*p*S['S6h']+179712*S['S6hh']+7488*S['S6d']-7860*p*S['S6yd']
    E+=8*p*((2466-834*rt)*p*p*S['S8y']-1112*p*(S['S8']-16*S['S8yh'])
            +139*rt*(256*S['S8yhh']-32*S['S8h']+8*S['S8yd']))
    return {'Bminus':(bs+bd)/2,'Bplus':(bs-bd)/2,'PB6':pb,'PZ6':yz,'PK6':yk,'Ecentral':E}

def midpoint(obj):
    return (mp.mpf(obj['lower_numerator'])+mp.mpf(obj['upper_numerator']))/mp.power(2,obj['denominator_power_of_two']+1)
def main(dps=80,N=160,J=34):
    st=time.time();mp.mp.dps=dps
    new=transformed(moments(N,J))
    alternative=transformed(moments(N+32,J+6))
    inherited=json.loads((ROOT/'inputs/complete_intervals.json').read_text())
    V={k:midpoint(v) for k,v in inherited['values'].items()}
    p=mp.pi;A=p+4*mp.log(2);Q=mp.gamma(mp.mpf(1)/4)**4/p
    cm=91*A*A+36*A*p-208*Q+2459*p*p
    cp=7*A*A+4*A*p-16*Q+271*p*p
    oldsector=-mp.mpf(3)/4*cm*V['Bminus']+mp.mpf(9)/4*cp*V['Bplus']
    oldsector+=24*V['PB6']+24*V['PZ6']+V['PK6']/3-393*p**3*V['Wcentral']
    newsector=p**3*new['Ecentral']+1048*p**5+655*p**6
    diff={k:mp.nstr(new[k]-V[k],20) for k in ['Bminus','Bplus','PB6','PZ6','PK6']}
    out={
      'scope':'Floating-point checks of exact identities. No asymptotic expansion is assumed convergent, no new interval error bound is claimed.',
      'working_digits':dps,'N':N,'J':J,
      'new_values':{k:mp.nstr(v,dps) for k,v in new.items()},
      'differences_from_inherited_period_interval_midpoints':diff,
      'cutoff_and_order_change':{k:mp.nstr(alternative[k]-new[k],20) for k in new},
      'weighted_sector_difference_r6':mp.nstr(newsector-oldsector,20),
      'weighted_C6_difference':mp.nstr((newsector-oldsector)/2187,20),
      'seconds':time.time()-st
    }
    (ROOT/'results'/f'numerical_{dps}.json').write_text(json.dumps(out,indent=2)+'\n')
    return out
if __name__=='__main__':
    import sys
    args=list(map(int,sys.argv[1:]));out=main(*args) if args else main()
    print(json.dumps(out,indent=2))
