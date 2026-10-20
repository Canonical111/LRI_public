#!/usr/bin/env python3
"""Exact tests of all-order LRI trial formulas, NOT new RG coefficients.

Requires sympy and mpmath. Usage:
  python verify_all_order_trials.py --order 8 --output results.json

No guessed coefficient is used to calculate any n > 6 trial coefficient.
The entire trial functions, however, are fitted to the known n <= 6 data.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sympy as s
import mpmath as mp

Y = s.Symbol('y')

def z(n: int):
    return s.Symbol(f'Z{n}')

def even_ratio(k: int):
    return (-1)**(k+1)*s.bernoulli(2*k)*2**(2*k-1)*6**k/s.factorial(2*k)

def canonical(expr):
    expr = s.sympify(expr)
    repl = {v: even_ratio(int(str(v)[1:])//2)*z(2)**(int(str(v)[1:])//2)
            for v in expr.free_symbols
            if str(v).startswith('Z') and str(v)[1:].isdigit()
            and int(str(v)[1:]) > 2 and int(str(v)[1:]) % 2 == 0}
    expr = s.expand(expr.subs(repl))
    p = s.Poly(expr, z(2))
    return s.expand(sum(co*(z(2)**i if i < 2 else z(2*i)/even_ratio(i))
                        for (i,), co in p.terms()))

def truncate(expr, n: int):
    p = s.Poly(s.expand(expr), Y)
    return s.Add(*(co*Y**i for (i,), co in p.terms() if i < n))

def mul(a, b, n: int):
    out = [s.Integer(0)]*n
    for i, ai in enumerate(a[:n]):
        if ai == 0:
            continue
        for j, bj in enumerate(b[:n-i]):
            if bj != 0:
                out[i+j] += ai*bj
    return [canonical(v) for v in out]

def binomial_power(a, exponent, n: int):
    assert a[0] == 1
    v = list(a[:n]); v[0] = s.Integer(0)
    out = [s.Integer(1)] + [s.Integer(0)]*(n-1)
    p = list(out)
    for k in range(1, n):
        p = mul(p, v, n)
        if all(q == 0 for q in p):
            break
        co = s.binomial(exponent, k)
        out = [canonical(aa + co*bb) for aa, bb in zip(out, p)]
    return out

def known_coefficients():
    return {1:s.Integer(-2), 2:s.Rational(1,2),
        3:s.Rational(39,16)+2*z(2),
        4:4-4*z(2)-8*z(3),
        5:s.Rational(11249,1024)-s.Rational(361,16)*z(2)+24*z(3)+s.Rational(49,2)*z(4),
        6:26-38*z(2)+104*z(3)-80*z(4)-272*z(5)+112*z(2)*z(3)}

# A3 and A4 designate trial variants, not perturbative insertion counts.
R = [s.Integer(1),s.Rational(1,4),s.Rational(11,16),s.Rational(63,64),
     s.Rational(525,256),s.Rational(4077,1024)]
MODELS = {
 'A3': {'rates':(1,2,3),
        'p':[(s.Rational(3,8),s.Rational(9,64),s.Rational(5,8),-s.Rational(103,64)),
             (-s.Rational(1,8),-s.Rational(1,64),-s.Rational(19,32)),
             (s.Rational(1,8),-s.Rational(5,64))],
        'q':(-s.Rational(13,5),s.Rational(27,20))},
 'A4': {'rates':(1,2,4),
        'p':[(s.Rational(3,14),s.Rational(51,224),s.Rational(5,8),-s.Rational(103,64)),
             (s.Rational(5,56),-s.Rational(125,896),-s.Rational(19,32)),
             (s.Rational(3,112),-s.Rational(33,1792))],
        'q':(-s.Rational(103,35),s.Rational(207,140))}
}

def model_series(which: str, n: int):
    model = MODELS[which]
    hs = [[s.Integer(0),s.Integer(0)] +
          [(-1)**k*s.Integer(r)**(k-1)*z(k) for k in range(2,n)]
          for r in model['rates']]
    numer = [s.Integer(0)]*n
    for pp, hh in zip(model['p'],hs):
        tmp = mul(list(pp),hh,n)
        numer = [canonical(a+b) for a,b in zip(numer,tmp)]
    den = [s.Integer(1)] + [s.Integer(0)]*(n-1)
    for qq, hh in zip(model['q'],hs):
        den = [canonical(a+qq*b) for a,b in zip(den,hh)]
    quot=[]
    for i in range(n):
        quot.append(canonical(numer[i]-sum(den[j]*quot[i-j] for j in range(1,i+1))))
    return [canonical(quot[i]+(R[i] if i < len(R) else 0)) for i in range(n)]

def coefficient(g, n: int):
    power = binomial_power(g, -s.Rational(n,2), n)
    return canonical(-s.Rational(2**n,n)*power[n-1])

def numerical(expr, digits=30):
    mpvals={v:s.zeta(int(str(v)[1:])) for v in expr.free_symbols
            if str(v).startswith('Z') and str(v)[1:].isdigit()}
    return str(s.N(expr.subs(mpvals),digits))

def model_value(which: str, yy):
    yy=mp.mpf(yy)
    model=MODELS[which]
    def qval(q):
        q=s.Rational(q)
        return mp.mpf(int(q.p))/int(q.q)
    hs=[yy*(mp.digamma(1+r*yy)+mp.euler) for r in model['rates']]
    num=sum(sum(qval(co)*yy**k for k,co in enumerate(pp))*hh
            for pp,hh in zip(model['p'],hs))
    den=1+sum(qval(qq)*hh for qq,hh in zip(model['q'],hs))
    return sum(qval(co)*yy**k for k,co in enumerate(R))+num/den

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--order',type=int,default=8)
    ap.add_argument('--output',type=Path,default=Path('results.json'))
    args=ap.parse_args()
    if args.order < 6:
        ap.error('--order must be at least 6 for the verification tests')
    # The computation is formal. Large requested orders may require considerable resources.
    n=max(8,args.order)
    known=known_coefficients()
    report={'status':'TRIAL FUNCTIONS ONLY: no new physical C7 or D4 evaluated',
            'input_coefficients':{str(k):str(v) for k,v in known.items()},'models':{}}
    for name in MODELS:
        gs=model_series(name,n)
        cs={j:coefficient(gs,j) for j in range(1,args.order+1)}
        residual={j:canonical(cs[j]-known[j]) for j in known}
        assert all(v==0 for v in residual.values()), residual
        report['models'][name]={'fit_residuals':{str(k):str(v) for k,v in residual.items()},
            'coefficients':{str(k):str(v) for k,v in cs.items()},
            'numeric_coefficients':{str(k):numerical(v) for k,v in cs.items()},
            'G_series':{str(k):str(v) for k,v in enumerate(gs)}}
        print(name,'matches c1,...,c6 exactly')
        for j in range(7,args.order+1):
            print('  TRIAL c%d ='%j,numerical(cs[j],20))

    # Reconstruct the inverse curve from the known input without using either trial.
    phi=[s.Integer(2)]+[-known[j+1] for j in range(1,6)]
    phi_normal=[p/2 for p in phi]
    inv={m:canonical(s.Rational(2,m*2**m)*binomial_power(phi_normal,-m,m-1)[m-2])
         for m in range(2,8)}
    gknown=[canonical(4*inv[m]) for m in range(2,8)]
    assert all(canonical(a-b)==0 for a,b in zip(gknown,model_series('A3',6)))
    v=list(gknown);v[0]=s.Integer(0)
    lp=[s.Integer(0)]*6
    pp=[s.Integer(1)]+[s.Integer(0)]*5
    for j in range(1,6):
        pp=mul(pp,v,6)
        lp=[canonical(a+s.Rational((-1)**(j+1),j)*b) for a,b in zip(lp,pp)]
    assert s.expand(lp[5]).coeff(z(2)).coeff(z(3))==2
    report['inverse_curve']={str(k):str(v) for k,v in inv.items()}
    report['inverse_log']={str(k):str(v) for k,v in enumerate(lp)}

    # A matched lower-order one-kernel extrapolation fails its first unused weight.
    hh=[s.Integer(0),s.Integer(0)]+[(-1)**k*2**k*z(k)/8 for k in range(2,6)]
    gt=[s.Integer(1)]+[s.Integer(0)]*5
    for j in range(1,6):
        gt[j]=canonical(sum(hh[k]*gt[j-k] for k in range(1,j+1)))
    toy6=coefficient(gt,6)
    assert canonical(toy6-(-128*z(5)+32*z(2)*z(3)))==0
    report['one_kernel_holdout_c6_top']=str(toy6)

    # Explicit nonzero resultant excludes the stated single hypergeometric family.
    c=s.Symbol('c')
    p=56*c**4-248*c**3+210*c**2+181*c-64
    q=84*c**4-376*c**3+331*c**2+244*c-73
    # Derive the two polynomials from the coefficient equations, rather
    # than only checking a pre-entered resultant.
    d=c-2
    b=(7*c*c-14*c-5)/(3*(c-2))
    k2=d*d-s.Rational(3,4)*b*d-s.Rational(1,4)*c*d+c*c
    k3p=d*(-b*d-2*b*b+c*d+3*b*c-c*c)
    k3z=d**3+b*d*d+s.Rational(9,2)*b*b*d-2*c*d*d-s.Rational(11,2)*c*b*d+2*c*c*d-c**3
    assert s.cancel(k2-s.Rational(21,4))==0
    np=s.fraction(s.factor(k3p-3))[0]
    nq=s.fraction(s.factor(k3z+17))[0]
    assert not s.cancel(np/p).has(c)
    assert not s.cancel(nq/q).has(c)
    # The exceptional value c=2 gives d=0 and k2=4, not 21/4.
    assert s.Integer(4)!=s.Rational(21,4)
    res=s.resultant(p,q,c)
    assert res==375712344000
    report['hypergeometric_exclusion']={'polynomials':[str(p),str(q)],'resultant':str(res),
        'scope':'Only the normalized three-parameter K_{a,b,c} family in the note; formal zeta matching'}

    # Independent endpoint test using the published GFF side.
    mp.mp.dps=50
    endpoint_y=mp.findroot(lambda yy: yy**2*model_value('A3',yy)/4-mp.mpf(1)/4,
                          (mp.mpf('.6'),mp.mpf('.7')))
    report['endpoint_test']={
        'A3_x_at_y_half':mp.nstr(model_value('A3',mp.mpf('.5'))/16,40),
        'A3_Delta_at_x_quarter':mp.nstr(1-endpoint_y,40),
        'required_Delta_at_x_quarter':'1/2',
        'required_dDelta_dx_at_x_quarter':'2/3',
        'required_d2Delta_dx2_at_x_quarter':'32*(pi+4*log(2))/9',
        'required_f_second_t_derivative':'4/3 + 32*(pi+4*log(2))/9'}
    print('A3 endpoint Delta =',report['endpoint_test']['A3_Delta_at_x_quarter'],'!= 1/2')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print('Wrote',args.output)

if __name__=='__main__':
    main()
