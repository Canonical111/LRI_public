"""Exact regularized-iterated-integral relations through weight five.
Word a=(a1,...,an) means Reg G(-a1,...,-an;T) at infinity.
Zero letters use the tangential-base-point convention G(0^n;T)=log(T)^n/n!.
"""
from collections import Counter
from fractions import Fraction as Q
from functools import lru_cache
from itertools import product

@lru_cache(maxsize=100000)
def sh(a,b):
    if not a:return {b:1}
    if not b:return {a:1}
    out=Counter()
    for w,c in sh(a[1:],b).items():out[(a[0],)+w]+=c
    for w,c in sh(a,b[1:]).items():out[(b[0],)+w]+=c
    return dict(out)

@lru_cache(maxsize=80000)
def fib(w):
    if not w:return {():1}
    ext=((1,0),)+w+((0,0),);out=Counter()
    for i,(ss,cc) in enumerate(w):
        lo=fib(w[:i]+w[i+1:])
        for sign,(s,c) in ((1,ext[i]),(-1,ext[i+2])):
            slope=s-ss;intercept=c-cc
            if not slope:continue
            assert slope in (-1,1)
            root=-intercept//slope
            assert root<=0,(w,root)
            for v,n in lo.items():out[(-root,)+v]+=sign*n
    return {w:c for w,c in out.items() if c}

# Each binary value is alpha*zeta(n), at n<=4, and
# alpha*zeta(5)+beta*zeta(2)*zeta(3) at n=5.
PHI={(0,1):(Q(-1),Q(0)),
 (0,0,1):(Q(-1),Q(0)),(0,1,1):(Q(1),Q(0)),
 (0,0,0,1):(Q(-1),Q(0)),(0,0,1,1):(Q(1,4),Q(0)),
 (0,1,0,1):(Q(3,4),Q(0)),(0,1,1,1):(Q(-1),Q(0)),
 (0,0,0,0,1):(Q(-1),Q(0)),
 (0,0,0,1,1):(Q(2),Q(-1)),
 (0,0,1,0,1):(Q(-11,2),Q(3)),
 (0,0,1,1,1):(Q(-2),Q(1)),
 (0,1,0,0,1):(Q(9,2),Q(-2)),
 (0,1,0,1,1):(Q(11,2),Q(-3)),
 (0,1,1,0,1):(Q(-9,2),Q(2)),
 (0,1,1,1,1):(Q(1),Q(0))}
ZETAR={2:Q(-2),3:Q(-4,3),4:Q(-8,7),5:Q(-16,15)}


def binary_value(bits):
    n=len(bits);alpha,beta=PHI[tuple(bits)]
    rr=Counter({(2,)+(1,)*(n-1):alpha*ZETAR[n]})
    if beta:
        for w,c in sh((2,1),(2,1,1)).items():rr[w]+=beta*Q(8,3)*c
    return {w:c for w,c in rr.items() if c}


def multiply(row,w):
    out=Counter()
    for v,c in row.items():
        for u,k in sh(v,w).items():out[u]+=c*k
    return {w:c for w,c in out.items() if c}


def relation(label):
    kind=label['kind'];rr=Counter()
    if kind=='confluence':
        bits=tuple(label['bits']);aa=tuple(label['a']);assert bits in PHI and len(bits)==len(aa)
        assert all(a>=0 if b==0 else a>0 for a,b in zip(aa,bits))
        rr.update(fib(tuple((b,a if b else -a) for b,a in zip(bits,aa))))
        for w,c in binary_value(bits).items():rr[w]-=c
    elif kind=='Rzero':
        assert label['a'] in (0,1);rr[(label['a'],)]=Q(1)
    elif kind=='logproduct':
        a,b=label['a'],label['b'];assert a>0 and b>0
        rr[(a*b,)]+=1;rr[(a,)]-=1;rr[(b,)]-=1
    elif kind=='scaling':
        d=label['d'];w=tuple(label['word']);assert d>0 and w[-1]>0 and all(a>=0 for a in w)
        rr[tuple(d*a for a in w)]+=1
        for j in range(len(w)+1):
            for v,c in sh((d,)*j,w[j:]).items():rr[v]-=c
    else:raise ValueError(kind)
    return multiply({w:Q(c) for w,c in rr.items() if c},tuple(label.get('times',())))


def confluence(n,M=10,zeros=True):
    for bits in [(0,)+mid+(1,) for mid in product((0,1),repeat=n-2)]:
        for aa in product(*(range(0 if zeros and b==0 else 1,M+1) for b in bits)):
            if max(a for a,b in zip(aa,bits) if not b)+max(a for a,b in zip(aa,bits) if b)>M:continue
            desc=dict(kind='confluence',bits=bits,a=aa)
            yield desc,relation(desc)


def relations(n,M=10,zeros=True):
    alphabet=range(0 if zeros else 1,M+1)
    basic=[dict(kind='Rzero',a=a) for a in ((0,1) if zeros else (1,))]
    for a in range(2,M+1):
        for b in range(a,M+1):
            if a*b<=M:basic.append(dict(kind='logproduct',a=a,b=b))
    for desc in basic:
        rr=relation(desc)
        for w in product(alphabet,repeat=n-1):
            row=multiply(rr,w)
            if row:yield {**desc,'times':w},row
    for k in range(2,n+1):
        for desc,rr in confluence(k,M,zeros):
            for w in product(alphabet,repeat=n-k):
                row=multiply(rr,w)
                if row:yield {**desc,'times':w},row
    for k in range(2,n+1):
        for d in range(2,M+1):
            for w in product(range(0 if zeros else 1,M//d+1),repeat=k):
                if w[-1]==0:continue
                desc=dict(kind='scaling',d=d,word=w);rr=relation(desc)
                if not rr:continue
                for tail in product(alphabet,repeat=n-k):
                    row=multiply(rr,tail)
                    if row:yield {**desc,'times':tail},row
