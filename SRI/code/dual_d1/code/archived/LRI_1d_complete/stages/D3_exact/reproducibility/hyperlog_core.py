"""Exact rational/hyperlog integration for gapped ordered configurations.
All coefficients are rational functions over QQ. No numerical recognition.
"""
from collections import defaultdict,Counter
from functools import lru_cache
from math import comb,factorial
from sympy.polys.fields import field
from sympy.polys.domains import QQ
K,e,u,v,w,t,q,zeta2,zeta3,zeta4,zeta5=field('e,u,v,w,t,q,Z2,Z3,Z4,Z5',QQ)
GEN=(e,u,v,w,t,q); PGEN=tuple(q.to_poly() for q in GEN)

def polykey(p): return tuple(sorted(p.items()))
@lru_cache(maxsize=50000)
def _pc(k,idx):
    out={}
    for mon,c in k:
        mm=list(mon);n=mm[idx];mm[idx]=0
        if n not in out:out[n]=K.zero
        out[n]+=K(K.ring.from_dict({tuple(mm):c}))
    return out

def pcoeff(p,idx):return _pc(polykey(p),idx)
def psub(p,idx,a,order=0):
    cs=pcoeff(p,idx);r=K.zero
    for n in range(max(cs,default=-1),order-1,-1):
        r=r*a+comb(n,order)*cs.get(n,K.zero)
    return r

def sub(r,idx,a):
    r=K(r)
    return psub(r.numer,idx,a)/psub(r.denom,idx,a)

def degree(p,idx):return max((mm[idx] for mm in p),default=-999)

def clean(d):return {k:v for k,v in d.items() if v}
def addto(d,key,val):
    if val:d[key]=d.get(key,K.zero)+val

@lru_cache(maxsize=10000)
def factors(key):return K.ring.from_dict(dict(key)).factor_list()[1]

@lru_cache(maxsize=30000)
def apart(R,idx):
    R=K(R);pol={};poles={};X=GEN[idx]
    # Divide as univariate polynomials: never form a large multivariate R-c*X**n.
    if degree(R.numer,idx)>=degree(R.denom,idx):
        ns=dict(pcoeff(R.numer,idx)); ds=pcoeff(R.denom,idx); dd=max(ds)
        while ns and max(ns)>=dd:
            dn=max(ns);c=ns[dn]/ds[dd];k=dn-dd
            pol[k]=pol.get(k,K.zero)+c
            for j,b in ds.items():
                jn=j+k;cv=ns.get(jn,K.zero)-c*b
                if cv:ns[jn]=cv
                elif jn in ns:del ns[jn]
    # The original numerator is valid for all finite-pole residues.
    if degree(R.denom,idx)==0:return clean(pol),poles
    for fac,m in factors(polykey(R.denom)):
        deg=degree(fac,idx)
        if deg==0:continue
        if deg!=1:raise ValueError(('nonlinear pole',fac,idx))
        fc=pcoeff(fac,idx);b=fc[1];a=-fc.get(0,K.zero)/b
        core=R.denom.exquo(fac**m)
        ns=[psub(R.numer,idx,a,j) for j in range(m)]
        ds=[b**m*psub(core,idx,a,j) for j in range(m)]
        rr=[]
        for j in range(m):
            rr.append((ns[j]-sum((ds[k]*rr[j-k] for k in range(1,j+1)),K.zero))/ds[0])
            if rr[-1]:poles[a,m-j]=rr[-1]
    return clean(pol),poles

@lru_cache(maxsize=None)
def shuffle(a,b):
    if not a:return {b:1}
    if not b:return {a:1}
    d=Counter()
    for w,c in shuffle(a[1:],b).items():d[(a[0],)+w]+=c
    for w,c in shuffle(a,b[1:]).items():d[(b[0],)+w]+=c
    return dict(d)

@lru_cache(maxsize=50000)
def integrate_basis(kind,place,n,w,idx):
    """Antiderivative of X**n G_w or (X-place)**(-n) G_w."""
    X=GEN[idx]
    if kind=='poly':
        b=X**(n+1)/(n+1)
        if not w:return {():b}
        out={w:b}
        for word,c in integrate_rat(b/(X-w[0]),w[1:],idx).items():addto(out,word,-c)
        return clean(out)
    if n==1:return {(place,)+w:K.one}
    b=-(X-place)**(1-n)/(n-1)
    if not w:return {():b}
    out={w:b}
    for word,c in integrate_rat(b/(X-w[0]),w[1:],idx).items():addto(out,word,-c)
    return clean(out)

def integrate_rat(R,w,idx):
    pol,poles=apart(R,idx);out={}
    for n,c in pol.items():
        for word,rr in integrate_basis('poly',K.zero,n,w,idx).items():addto(out,word,c*rr)
    for (a,n),c in poles.items():
        for word,rr in integrate_basis('pole',a,n,w,idx).items():addto(out,word,c*rr)
    return clean(out)

@lru_cache(maxsize=100000)
def fibrate(w,idx):
    """G(a_i(X);X) in fixed-letter G's. All nonempty base values vanish."""
    if not w:return {():1}
    X=GEN[idx];out=Counter()
    # This case is deliberately rejected: it would need a nonzero/singular base term.
    for a in w:
        if sub(a,idx,K.zero)==0:
            raise ValueError(('fibration base letter zero',w,idx))
    ext=(X,)+w+(K.zero,)
    for i in range(len(w)):
        lower=fibrate(w[:i]+w[i+1:],idx)
        for sign,p in [(1,ext[i]-w[i]),(-1,ext[i+2]-w[i])]:
            if not p or not p.diff(X):continue
            if p.denom!=K.ring.one or degree(p.numer,idx)!=1:
                raise ValueError(('nonaffine dlog',p,idx))
            slope=p.diff(X);root=-sub(p,idx,K.zero)/slope
            assert not root.diff(X)
            for ww,c in lower.items():out[(root,)+ww]+=sign*c
    return {w:c for w,c in out.items() if c}

def differentiate(ans,idx):
    X=GEN[idx];out={}
    for w,R in ans.items():
        addto(out,w,R.diff(X))
        if w:addto(out,w[1:],R/(X-w[0]))
    return clean(out)

if __name__=='__main__':
    tests=[(1/(u+e)**2,()),((u+v)/((u+e)**3*(u-v-e)),()),
           (u**2/((u+e)*(u-v-e)**2),(-e,)),
           (1/((u+e)**2*(u-v-e)**2),(-e,v+e))]
    for R,w in tests:
        ans=integrate_rat(R,w,1);diff=differentiate(ans,1)
        diff[w]=diff.get(w,K.zero)-R
        assert not clean(diff),(R,w,diff)
    print('Rational/hyperlog primitives: exact derivative checks PASS')
    for w in [(v+e,),(-e,v+e),(v+e,v+e),(-e,v+2*e,v+e)]:
        print('Fibration',tuple(map(str,w)),fibrate(w,2))

@lru_cache(maxsize=None)
def phi(word):
    if not word:return K.one
    if all(a==word[0] for a in word):return K.zero
    if word[0]==1:
        sh=shuffle((1,),word[1:]);mult=sh.pop(word)
        return -sum((c*phi(w) for w,c in sh.items()),K.zero)/mult
    if word[-1]==0:
        sh=shuffle((0,),word[:-1]);mult=sh.pop(word)
        return -sum((c*phi(w) for w,c in sh.items()),K.zero)/mult
    idx=[];k=0
    for a in word:
        k+=1
        if a==1:idx.append(k);k=0
    assert not k and idx[0]>=2
    tab={(2,):zeta2,(3,):zeta3,(2,1):zeta3,
         (4,):zeta4,(3,1):zeta4/4,(2,2):3*zeta4/4,(2,1,1):zeta4,
         (5,):zeta5,(4,1):2*zeta5-zeta2*zeta3,
         (3,2):3*zeta2*zeta3-11*zeta5/2,(2,3):9*zeta5/2-2*zeta2*zeta3,
         (3,1,1):2*zeta5-zeta2*zeta3,(2,2,1):3*zeta2*zeta3-11*zeta5/2,
         (2,1,2):9*zeta5/2-2*zeta2*zeta3,(2,1,1,1):zeta5}
    return (-1)**len(idx)*tab[tuple(idx)]

@lru_cache(maxsize=None)
def scaled_phi(word):
    """G(0 or X;X) as powers of log X. Output canonical G(0,...,0;X)."""
    if not word:return {():K.one}
    if all(a==0 for a in word):return {tuple(K.zero for a in word):K.one}
    if word[-1]!=0:return {():phi(word)}
    sh=shuffle((0,),word[:-1]);mult=sh.pop(word)
    out={}
    for w,c in scaled_phi(word[:-1]).items():
        addto(out,(K.zero,)+w,c*(len(w)+1))
    for ww,m in sh.items():
        for w,c in scaled_phi(ww).items():addto(out,w,-m*c)
    return {w:c/mult for w,c in clean(out).items()}

@lru_cache(maxsize=100000)
def endpoint_fibrate(w,idx):
    """Regularized endpoint fibration, including coalescing 0/X words."""
    if not w:return {():K.one}
    X=GEN[idx];out={};ext=(X,)+w+(K.zero,)
    if all(a==K.zero or a==X for a in w):
        return scaled_phi(tuple(int(a==X) for a in w))
    for a in w:
        if sub(a,idx,K.zero)==0 and a not in (K.zero,X):
            raise ValueError(('unsupported zero base',a))
    for i in range(len(w)):
        lower=endpoint_fibrate(w[:i]+w[i+1:],idx)
        for side,sign,p in [('prev',1,ext[i]-w[i]),('next',-1,ext[i+2]-w[i])]:
            if not p:
                if side=='prev' and i==0 and w[i]==X:root=K.zero
                else:continue
            else:
                if not p.diff(X):continue
                if p.denom!=K.ring.one or degree(p.numer,idx)!=1:raise ValueError(('nonaffine dlog',p))
                root=-sub(p,idx,K.zero)/p.diff(X)
            for ww,c in lower.items():addto(out,(root,)+ww,sign*c)
    return clean(out)

@lru_cache(maxsize=100000)
def local_gpl(w,B,P,lower=False):
    """Jet in h=X-B and log(-h/B), coefficients linear in Reg G(subword;B).
    For the lower point B=0 the logarithm is log X and all nonempty base
    constants are zero. This computes every finite contribution from poles.
    """
    if not w:return {(0,0,()):K.one}
    out={} if lower else {(0,0,w):K.one}
    tail=local_gpl(w[1:],B,P,lower)
    a=w[0]
    if a==B:
        for (n,m,sw),c in tail.items():
            if n==0:addto(out,(0,m+1,sw),c/(m+1))
            else:
                for j in range(m+1):
                    addto(out,(n,m-j,sw),c*(-1)**j*factorial(m)/factorial(m-j)/K(n)**(j+1))
    else:
        for (n,m,sw),c in tail.items():
            for k in range(P-n):
                p=n+k+1;cc=c*(-1)**k/(B-a)**(k+1)
                for j in range(m+1):
                    addto(out,(p,m-j,sw),cc*(-1)**j*factorial(m)/factorial(m-j)/K(p)**(j+1))
    return clean(out)

def endpoint_value(c,w,idx,B,lower=False):
    """Finite part of c(X)G(w;X) at X=B, as linear endpoint G values."""
    try:c0=sub(c,idx,B);poles_here={}
    except ZeroDivisionError:
        poly,poles=apart(c,idx)
        poles_here={n:r for (a,n),r in poles.items() if a==B}
        assert poles_here
        c0=sum((r*B**n for n,r in poly.items()),K.zero)+sum((r/(B-a)**n for (a,n),r in poles.items() if a!=B),K.zero)
    out={}
    if not lower or not w:addto(out,w,c0)
    if poles_here:
        jet=local_gpl(w,B,max(poles_here),lower)
        for (n,m,ww),cjet in jet.items():
            if m==0 and n in poles_here:addto(out,ww,poles_here[n]*cjet)
    return clean(out)
