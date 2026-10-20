#!/usr/bin/env python3
"""Alternative *trial* generators for the archived 1D LRI thermal series.

No new RG coefficients are computed. All fits use exact rational algebra in a
formal zeta polynomial ring. The log-Gamma and Borel-log-Gamma trials are fitted
independently. The default also withholds C7 and refits the same dictionary.

Requirements: Python 3.10+, SymPy, mpmath.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple
import sympy as S

Z = {n: S.Symbol(f'Z{n}') for n in [2,3,5,7,9,11,13,15,17,19]}
GENS = tuple(Z.values())


def zeta(n: int):
    if n < 2:
        raise ValueError('zeta index must be at least two')
    if n % 2:
        if n not in Z:
            raise ValueError(f'index {n} exceeds configured maximum')
        return Z[n]
    k = n // 2
    return S.Rational((-1)**(k+1)*2**(2*k-1)*6**k, math.factorial(2*k))*S.bernoulli(2*k)*Z[2]**k


def num(expr, digits=40) -> str:
    return str(S.N(expr.subs({v:S.zeta(k) for k,v in Z.items()}), digits))


def input_coeffs():
    return {
      1:S.Integer(-2), 2:S.Rational(1,2),
      3:S.Rational(39,16)+2*zeta(2),
      4:4-4*zeta(2)-8*zeta(3),
      5:S.Rational(11249,1024)-S.Rational(361,16)*zeta(2)+24*zeta(3)+S.Rational(49,2)*zeta(4),
      6:26-38*zeta(2)+104*zeta(3)-80*zeta(4)-272*zeta(5)+112*zeta(2)*zeta(3),
      7:S.Rational(1798583,32768)-S.Rational(90637,1024)*zeta(2)+S.Rational(453,4)*zeta(3)-S.Rational(16835,64)*zeta(4)+1224*zeta(5)-540*zeta(2)*zeta(3)+S.Rational(4335,8)*zeta(6)-320*zeta(3)**2,
    }


def zero(n): return [S.Integer(0) for _ in range(n+1)]


def mul(a,b,n):
    out=zero(n)
    for k in range(n+1):
        out[k]=S.expand(sum(a[j]*b[k-j] for j in range(max(0,k-len(b)+1),min(k,len(a)-1)+1)))
    return out


def logarithm(a,n):
    assert a[0]==1
    # a' = a * (log a)'
    out=zero(n)
    for k in range(1,n+1):
        out[k]=S.expand(a[k]-sum(j*out[j]*a[k-j] for j in range(1,k))/S.Integer(k))
    return out


def exponential(ell,n):
    assert ell[0]==0
    out=zero(n);out[0]=S.Integer(1)
    for m in range(1,n+1):
        out[m]=S.expand(sum(k*ell[k]*out[m-k] for k in range(1,m+1))/m)
    return out


def gamma_log(r,n):
    # F_r(t) = log Gamma(1+r t) + gamma r t
    a=zero(n)
    for k in range(2,n+1):
        a[k]=S.Rational((-1)**k*r**k,k)*zeta(k)
    return a


def weighted_part(expr,w):
    p=S.Poly(S.expand(expr),*GENS)
    return S.Add(*(coef*S.prod(g**j for g,j in zip(GENS,mon))
            for mon,coef in p.terms()
            if sum(n*j for n,j in zip(Z,mon))==w))


def fit_kernel(N:int, borel:bool=False, dictionary:str="theta"):
    if not (3 <= N <= 7): raise ValueError('Fit order must be 3,...,7')
    c=input_coeffs();M=N-1
    H=[S.Integer(1)]+[-c[k+1]/2 for k in range(1,M+1)]
    ell=logarithm(H,M)
    target=[S.expand(e / (math.factorial(k) if borel else 1)) for k,e in enumerate(ell)]
    rational=[weighted_part(e,0) for e in target]
    # Terms (kind, defect, scale, coefficient). kind L, LL (1,1), LM (1,2).
    terms=[]; ranks=[]
    for defect in range(M-1):
        maxweight=M-defect
        basis=[];labels=[]
        for r in range(1,maxweight):
            if dictionary=='theta':
                basis.append([v*S.Integer(k)**(r-1) for k,v in enumerate(gamma_log(1,maxweight))]);labels.append(('Theta',defect,r-1))
            else:
                basis.append(gamma_log(r,maxweight));labels.append(('L',defect,r))
        if maxweight>=5:
            basis.append(mul(gamma_log(1,maxweight),gamma_log(1,maxweight),maxweight));labels.append(('LL',defect,1))
        if maxweight>=6:
            if dictionary=='theta':
                basis.append([v*k for k,v in enumerate(mul(gamma_log(1,maxweight),gamma_log(1,maxweight),maxweight))]);labels.append(('Dsq',defect,0))
            else:
                basis.append(mul(gamma_log(1,maxweight),gamma_log(2,maxweight),maxweight));labels.append(('LM',defect,2))
        rows=[];rhs=[]
        for w in range(2,maxweight+1):
            tgt=weighted_part(target[w+defect],w)
            pp=[S.Poly(b[w],*GENS) for b in basis];pt=S.Poly(tgt,*GENS)
            mons=set(pt.monoms())
            for p in pp: mons.update(p.monoms())
            for mon in sorted(mons):
                if mon==(0,)*len(GENS): continue
                rows.append([p.coeff_monomial(mon) for p in pp]);rhs.append(pt.coeff_monomial(mon))
        mat=S.Matrix(rows);vec=S.Matrix(rhs)
        sol, parameters=mat.gauss_jordan_solve(vec)
        if parameters.rows:
            raise ValueError('Dictionary does not uniquely determine the fit')
        assert mat*sol==vec, (defect, mat, vec, sol, mat*sol-vec)
        assert all(v.is_Rational for v in sol)
        ranks.append({'defect':defect,'equations':mat.rows,'parameters':mat.cols,'rank':mat.rank()})
        terms.extend([(*lab,coef) for lab,coef in zip(labels,sol) if coef])
    fit={'fit_order':N,'borel':borel,'dictionary':dictionary,'rational':rational,'terms':terms,'ranks':ranks,'target':target}
    assert all(S.expand(a-b)==0 for a,b in zip(kernel_series(fit,M),target))
    return fit


def kernel_series(fit,n):
    out=zero(n)
    for k,coef in enumerate(fit['rational']):
        if k<=n: out[k]=coef
    cache={}
    for kind,d,r,c in fit['terms']:
        key=(kind,r)
        if key not in cache:
            if kind=='L':v=gamma_log(r,n)
            elif kind=='Theta':v=[e*S.Integer(k)**r for k,e in enumerate(gamma_log(1,n))]
            elif kind=='Dsq':v=[e*k for k,e in enumerate(mul(gamma_log(1,n),gamma_log(1,n),n))]
            elif kind=='LL':v=mul(gamma_log(1,n),gamma_log(1,n),n)
            else:v=mul(gamma_log(1,n),gamma_log(2,n),n)
            cache[key]=v
        v=cache[key]
        for k in range(d,n+1): out[k]+=c*v[k-d]
    return [S.expand(v) for v in out]


def model_coeffs(fit,n):
    ker=kernel_series(fit,n-1)
    ell=[e * (math.factorial(k) if fit['borel'] else 1) for k,e in enumerate(ker)]
    h=exponential(ell,n-1)
    return {k:S.expand(-2*h[k-1]) for k in range(1,n+1)}


def write_fit(fit,n):
    cs=model_coeffs(fit,n)
    for k in range(1,fit['fit_order']+1): assert S.expand(cs[k]-input_coeffs()[k])==0
    # polynomial weight rather than rational functions in zetas
    for k,e in cs.items():
        assert max([sum(j*w for j,w in zip(mon,Z)) for mon in S.Poly(e,*GENS).monoms()]+[0])<=k-1
    return {'fit_order':fit['fit_order'],'borel':fit['borel'],'dictionary':fit['dictionary'],
      'rational_polynomial':[str(v) for v in fit['rational']],
      'kernel_terms':[{'kind':a,'defect':b,'scale':c,'coefficient':str(d)} for a,b,c,d in fit['terms']],
      'linear_systems':fit['ranks'],
      'coefficients':{str(k):{'exact':str(e),'numeric':num(e),'top_weight':str(weighted_part(e,k-1))} for k,e in cs.items()},
      'exact_input_match':True,'weight_bound_checked_to_order':n}


def invariants():
    c=input_coeffs()
    Ts=[0,S.Rational(1,2),c[4]/2,c[6]/4]
    Ds=[0,S.Integer(-2),c[3]+S.Rational(1,16),
        S.expand((c[5]+Ts[2]/2-c[3]**2/4)/2),
        S.expand((c[7]+Ts[3]+Ts[2]**2-c[3]*c[5]/2)/4)]
    return Ts,Ds


def rational_rg(n,N=7):
    Ts,Ds=invariants()
    nt=N//2;nd=(N+1)//2
    m=(n+1)//2
    T=[S.Integer(0)]+[Ts[k] for k in range(1,nt+1)]
    D=[S.Integer(0)]+[Ds[k] for k in range(1,nd+1)]
    # [nt-2 /1] for T/delta, [nd-2 /1] for D/delta.
    rt=Ts[nt]/Ts[nt-1];rd=Ds[nd]/Ds[nd-1]
    for k in range(nt+1,m+1):T.append(S.cancel(Ts[nt]*rt**(k-nt)))
    for k in range(nd+1,m+1):D.append(S.cancel(Ds[nd]*rd**(k-nd)))
    ss=[S.Integer(1)]
    C={1:S.Integer(-2)}
    for k in range(1,m):
        q=sum(T[i]*T[k+1-i] for i in range(1,k+1))/8-D[k+1]/2
        ss.append(S.cancel((q-sum(ss[i]*ss[k-i] for i in range(1,k)))/2))
        if 2*k+1<=n:C[2*k+1]=S.cancel(-2**(k+1)*ss[k])
    for k in range(1,m+1):
        if 2*k<=n:C[2*k]=S.cancel(2**(k-1)*T[k])
    assert all(S.cancel(C[k]-input_coeffs()[k])==0 for k in range(1,N+1))
    return {str(k):{'exact':str(e),'numeric':num(e)} for k,e in sorted(C.items())}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--order',type=int,default=9)
    p.add_argument('--dictionary',choices=['theta','scales'],default='theta')
    p.add_argument('--output',type=Path,default=Path('results.json'))
    args=p.parse_args()
    if not (8<=args.order<=12):p.error('--order must be 8,...,12')
    result={'status':'trial models only; no new physical coefficient evaluated',
            'inputs':{str(k):{'exact':str(v),'numeric':num(v)} for k,v in input_coeffs().items()},'models':{}}
    for borel in [False,True]:
        name='borel_log_gamma' if borel else 'quadratic_log_gamma'
        print('Fitting',name,flush=True)
        result['models'][name]=write_fit(fit_kernel(7,borel,args.dictionary),args.order)
        result['models'][name]['holdouts']={}
        for N in [5,6]:
            f=fit_kernel(N,borel,args.dictionary);h=model_coeffs(f,N+1)[N+1]
            result['models'][name]['holdouts'][str(N+1)]={'trained_through':N,'prediction':num(h),'exact':str(h),'actual':num(input_coeffs()[N+1]),'error':num(h-input_coeffs()[N+1])}
    print('Fitting rational invariant baseline',flush=True)
    result['models']['rational_rg']={'coefficients':rational_rg(args.order),'holdouts':{}}
    for N in [5,6]:
        result['models']['rational_rg']['holdouts'][str(N+1)]={'trained_through':N,'prediction':rational_rg(N+1,N)[str(N+1)]['numeric'],'actual':num(input_coeffs()[N+1])}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    for name,res in result['models'].items():
        print('\n',name)
        for k in ['8','9']:
            if k in res['coefficients']:print('C'+k,res['coefficients'][k]['numeric'])
        print('Holdouts',res['holdouts'])
    print('Written',args.output)

if __name__=='__main__':main()
