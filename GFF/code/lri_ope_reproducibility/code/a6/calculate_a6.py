#!/usr/bin/env python3
"""Sixth coefficient of the bulk one-point function in long-range Ising.
Physical dimension d, epsilon=2s-d, and < :Phi^2: >= a_phi2/|y|^(2 Delta_phi).
This is a finite-order coefficient calculation, not a resummation.

Dependencies: mpmath. Example: python calculate_a6.py --dimension 1 --precision 60
For generic d, supply the six master inputs to coefficients() or supply
thermal C3,C4,C5 and the three nonprimitive masters K,L,Z.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
import mpmath as mp

def number(x:Any)->mp.mpf:
    if isinstance(x,str) and '/' in x:
        a,b=x.split('/');return mp.mpf(a)/mp.mpf(b)
    return mp.mpf(x)

def d1_inputs()->dict:
    q=mp.mpf(1)/4
    fm=mp.hyper([q,q,2*q,2*q],[3*q,3*q,1],1)
    fp=mp.hyper([3*q,3*q,2*q,2*q],[5*q,5*q,1],1)
    bm=mp.gamma(q)**4*fm;bp=64*mp.pi**4/mp.gamma(q)**4*fp
    T=6*mp.gamma(q)**4/mp.pi;P=13*bm-3*bp
    A=mp.pi+4*mp.log(2)
    K=(mp.polygamma(1,q)*(3*mp.polygamma(1,q)-mp.polygamma(1,1-q))+A*mp.polygamma(2,q))/2
    L=-(3*A-mp.pi)*P/6-2*mp.pi*bm/3
    Z=(T/6)*(2*mp.pi**2/3+8*mp.catalan)
    def Yr(r):
        r=mp.mpf(r);a=(r+2)/8;b=(r+6)/8
        return r/8*(mp.gamma(a)/mp.gamma(b))**7*mp.hyper([1,1+r/8]+[a]*7,[r/8]+[b]*7,-1)
    c=mp.cos(mp.pi/8);s=mp.sin(mp.pi/8);r2=mp.sqrt(2)
    P5=16*mp.pi**mp.mpf('1.5')*(-35*Yr(2)+(22*r2-13)*(c**7*Yr(3)-s**7*Yr(5))+(22*r2+13)*(c**7*Yr(1)+s**7*Yr(7)))
    return {'T':T,'P4':P,'P5':P5,'K':K,'L':L,'Z':Z,
            'method':'fixed Gamma / hypergeometric formulas and exact master identities in the supplied note'}

def coefficients(d:Any,*,T:Any=None,P4:Any=None,P5:Any=None,K:Any=None,L:Any=None,Z:Any=None,
                 C3:Any=None,C4:Any=None,C5:Any=None)->dict:
    d=number(d)
    if not mp.isfinite(d) or not 0<d<4:raise ValueError('Require fixed 0<d<4.')
    q=d/4
    A=mp.digamma(2*q)-2*mp.digamma(q)+mp.digamma(1)
    R=mp.polygamma(1,2*q)-mp.polygamma(1,1)
    U=mp.polygamma(2,q);V=mp.polygamma(2,1)+mp.polygamma(2,2*q)
    X=mp.polygamma(3,2*q)-mp.polygamma(3,1)
    reflected=[mp.polygamma(j,1-q)-mp.polygamma(j,q)+mp.factorial(j)/q**(j+1) for j in range(4)]
    B,S,D2,D3=reflected
    a2=-mp.gamma(1-q)*mp.gamma(2*q)**3/(54*mp.gamma(1+q)*mp.gamma(4*q))
    supplied=[T,P4,P5,K,L,Z,C3,C4,C5]
    method='user-supplied master values'
    if all(v is None for v in supplied):
        if d!=1:raise ValueError('For d other than 1 supply masters or thermal C3,C4,C5 plus K,L,Z.')
        inputs=d1_inputs();T,P4,P5,K,L,Z=[inputs[k] for k in ('T','P4','P5','K','L','Z')];method=inputs['method']
    if any(v is not None for v in (C3,C4,C5)):
        if any(v is not None for v in (T,P4,P5)):raise ValueError('Supply periods OR thermal coefficients, not both.')
        if any(v is None for v in (C3,C4,C5,K,L,Z)):raise ValueError('Thermal mode needs C3,C4,C5,K,L,Z.')
        C3,C4,C5,K,L,Z=map(number,(C3,C4,C5,K,L,Z))
        T=mp.mpf(3)/4*(A*A+R)-81*C3
        P4=(648*C4+A**3+mp.mpf(4)/3*A*T+3*A*R-mp.mpf(53)/2*U+3*V)/16
        h4=(6*C5+5*A*C4+(5*A*A-R)*C3/6+9*C3*C3-A**4/5184+7*A*A*R/2592
            +235*A*U/2592-5*A*V/432-7*R*R/1728-47*X/7776+(13*Z-L-12*K)/81)
        method='thermal C3,C4,C5 and independent nonprimitive master inputs; not an independent check of those thermal coefficients'
    else:
        if any(v is None for v in (T,P4,P5,K,L,Z)):raise ValueError('Period mode needs T,P4,P5,K,L,Z.')
        T,P4,P5,K,L,Z=map(number,(T,P4,P5,K,L,Z))
        h4=(-7*A**4/5184-7*A*A*R/288-7*A*A*T/972+14*A*P4/81+301*A*U/864-7*A*V/144
            -28*K/81-7*L/81-16*P5/81-103*R*R/5184+7*R*T/324-7*T*T/1458-61*X/3888+175*Z/162)
    h1=4*A/3
    h2=25*A*A/36+R/6-2*T/27
    h3=17*A**3/108+A*R/12-2*A*T/27+4*P4/27+71*U/216-V/36
    f=[mp.mpf(1),-B/4,(B*B+S)/32,-(B**3+3*B*S+D2)/384,
       (B**4+6*B*B*S+3*S*S+4*B*D2+D3)/6144]
    h=[mp.mpf(1),h1,h2,h3,h4]
    aa={n:a2*sum(h[j]*f[n-2-j] for j in range(n-1)) for n in range(2,7)}
    return {'d':d,'coefficients':aa,'h':h,'external_factor':f,'T':T,'P4':P4,'P5':P5,'K':K,'L':L,'Z':Z,
            'method':method,'warning':'Numerical stability and coefficient precision do not bound omitted powers of epsilon.'}

def serial(x):
    if isinstance(x,dict):return {str(k):serial(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [serial(v) for v in x]
    if isinstance(x,mp.mpf):return mp.nstr(x,mp.mp.dps)
    return x

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dimension',default='1');parser.add_argument('--precision',type=int,default=60)
    parser.add_argument('--inputs',type=Path,help='JSON object with T,P4,P5,K,L,Z or C3,C4,C5,K,L,Z')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.precision<20:parser.error('Use at least 20 digits of working precision.')
    mp.mp.dps=args.precision
    inputs=json.loads(args.inputs.read_text()) if args.inputs else {}
    result=serial(coefficients(args.dimension,**inputs));text=json.dumps(result,indent=2)
    print(text)
    if args.output:args.output.write_text(text+'\n')
