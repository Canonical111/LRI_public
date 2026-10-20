"""Reciprocal-Gamma spectral trial. NOT a derived physical formula."""
from formal_series import *
from itertools import product
from collections import defaultdict
import json
NODES=[(0,1),(0,2),(0,3),(1,1),(1,2),(2,1),(2,2)]

def series_add(a,b,n):return [canonical((a[i] if i<len(a) else 0)+(b[i] if i<len(b) else 0)) for i in range(n)]
def scale(a,q,n):return [canonical(q*a[i]) if i<len(a) else s.Integer(0) for i in range(n)]
def shift(a,k,n):return [s.Integer(0)]*k+a[:n-k]
def power(a,k,n):
    out=[s.Integer(1)]+[s.Integer(0)]*(n-1)
    for j in range(k):out=mul(out,a,n)
    return out

def gamma_ratio(A,B,ys,n):
    yp=[power(ys,k,n) for k in range(n)]
    log=[s.Integer(0)]*n
    for r in range(2,n):
        zz=(-1)**r*z(r)/s.Integer(r)
        for k in range(2,r+1,2):
            co=zz*2*s.binomial(r,k)*A**(r-k)*B**k
            log=series_add(log,shift(scale(yp[r-k],co,n),k,n),n)
    log=[-v for v in log]
    ep=[s.Integer(1)]
    for r in range(1,n):
        ep.append(canonical(sum(k*log[k]*ep[r-k] for k in range(1,r+1))/r))
    ep[0]=s.Integer(0)
    return [-v for v in ep]

def weight_split(expr):
    out=defaultdict(lambda:0)
    for term in s.Add.make_args(canonical(expr)):
        rat,tail=term.as_coeff_Mul()
        out[tail]+=rat
    return out

def basis_on_series(ys,n,maxrat=6,maxg=4,nodes=NODES):
    yp=[power(ys,k,n) for k in range(max(maxrat,maxg)+1)]
    ratios=[gamma_ratio(s.Rational(a),s.Rational(b),ys,n-2) for a,b in nodes]
    result=[]
    for j in range(1,maxrat+1):result.append((('R',j),shift(yp[j],2,n)))
    # prioritize near-diagonal: constant highest-weight first
    for j in range(maxg+1):
        for (a,b),rat in zip(nodes,ratios):
            result.append(((a,b,j),shift(mul(yp[j],rat,n-2),2,n)))
    return result

def fit(order=7,nodes=NODES):
    n=order+2
    ys=[s.Integer(0)]+[-c[j] for j in range(1,order+1)]+[s.Integer(0)]
    baseline=power(ys,2,n);baseline[2]-=4
    # through t**(order+1)
    basis=basis_on_series(ys,n,order-1,order-3,nodes)
    features=set()
    vecs=[]
    for exprs in [baseline]+[rr for _,rr in basis]:
        vv={}
        for i in range(3,n):
            for term,co in weight_split(exprs[i]).items():
                if co:vv[(i,term)]=co;features.add((i,term))
        vecs.append(vv)
    features=sorted(features,key=lambda k:(k[0],s.default_sort_key(k[1])))
    M=s.Matrix([[v.get(feat,0) for v in vecs[1:]] for feat in features])
    rhs=s.Matrix([-vecs[0].get(feat,0) for feat in features])
    assert M.row_join(rhs).rank()==M.rank()
    # use pivot columns yields unique basis fit all other parameters zero
    _,piv=M.rref()
    Ms=M[:,list(piv)]
    result=s.linsolve((Ms,rhs))
    if not result:return None
    sol=list(result)[0]
    assert not any(co.free_symbols for co in sol)
    assert Ms*s.Matrix(sol)==rhs
    coeffs={basis[j][0]:co for j,co in zip(piv,sol) if co}


    return coeffs

def evaluate_F(coeffs,ys,n):
    bs=basis_on_series(ys,n,maxrat=max(k[1] for k in coeffs if k[0]=='R'),maxg=max(k[2] for k in coeffs if k[0]!='R'))
    out=power(ys,2,n);out[2]-=4
    for label,ex in bs:
        if label in coeffs:out=series_add(out,scale(ex,coeffs[label],n),n)
    return out

