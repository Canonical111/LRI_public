"""Exact rational/hyperlog integration for gapped ordered configurations.
All coefficients are rational functions over QQ. No numerical recognition.
"""
from collections import defaultdict,Counter
from functools import lru_cache
from math import comb,factorial
from factored_field import field, Frac
from sympy.polys.domains import QQ
K,e,u,v,w,t,q,r,h,zeta2,zeta3,zeta4,zeta5,zeta6=field('e,u,v,w,t,q,r,h,Z2,Z3,Z4,Z5,Z6',QQ)
GEN=(e,u,v,w,t,q,r,h); PGEN=tuple(q.to_poly() for q in GEN)

def polykey(p): return tuple(sorted(p.items()))
@lru_cache(maxsize=300)
def _pc(k,idx):
    # Assemble polynomial coefficients once, avoiding a gcd after each monomial.
    polys={}
    for mon,c in k:
        mm=list(mon);n=mm[idx];mm[idx]=0
        polys.setdefault(n,{})[tuple(mm)]=c
    return {n:K(K.ring.from_dict(pp)) for n,pp in polys.items()}

def pcoeff(p,idx):return _pc(polykey(p),idx)
def psub(p,idx,a,order=0):
    cs=pcoeff(p,idx)
    if a.denom==K.ring.one:
        # All poles in the gap integration are affine polynomials.
        rr=K.ring.zero
        for n in range(max(cs,default=-1),order-1,-1):
            rr=rr*a.numer+comb(n,order)*cs.get(n,K.zero).numer
        return K(rr)
    rr=K.zero
    for n in range(max(cs,default=-1),order-1,-1):
        rr=rr*a+comb(n,order)*cs.get(n,K.zero)
    return rr

def sub(r,idx,a):
    r=K(r);out=psub(r.numer,idx,a)
    for f,m in r.denf.items():out/=psub(f,idx,a)**m
    return out

def degree(p,idx):return max((mm[idx] for mm in p),default=-999)

def clean(d):return {k:v for k,v in d.items() if v}
def addto(d,key,val):
    if val:d[key]=d.get(key,K.zero)+val

@lru_cache(maxsize=10000)
def factors(key):return K.ring.from_dict(dict(key)).factor_list()[1]

@lru_cache(maxsize=400)
def apart(R,idx):
    """Exact local Laurent series with factored denominator coefficients."""
    R=K(R);pol={};poles={};X=GEN[idx]
    if not R:return pol,poles
    active=[(f,m) for f,m in R.denf.items() if degree(f,idx)>0]
    if not active:
        from factored_field import cancel_factors
        out={}
        for n,c in pcoeff(R.numer,idx).items():
            nn,dd=cancel_factors(c.numer,R.denf)
            out[n]=Frac(K,nn,dd)
        return out,poles
    den_degree=sum(m*degree(f,idx) for f,m in active)
    if degree(R.numer,idx)>=den_degree:
        activepoly=K.ring.one
        spectator={ff:mm for ff,mm in R.denf.items() if degree(ff,idx)<=0}
        for ff,mm in active:activepoly*=ff**mm
        ns=dict(pcoeff(R.numer,idx));ds=pcoeff(activepoly,idx);dd=max(ds)
        sinv=Frac(K,K.ring.one,spectator)
        while ns and max(ns)>=dd:
            dn=max(ns);c=ns[dn]/ds[dd];k=dn-dd
            pol[k]=pol.get(k,K.zero)+c*sinv
            for j,b in ds.items():
                jn=j+k;cv=K.zero if j==dd else ns.get(jn,K.zero)-c*b
                if cv:ns[jn]=cv
                elif jn in ns:del ns[jn]
    for fac,m in active:
        assert degree(fac,idx)==1
        fc=pcoeff(fac,idx);b=fc[1];a=-fc.get(0,K.zero)/b
        inv=b**(-m);ratio={0:K.one}
        for ff,mm in R.denf.items():
            if ff==fac:continue
            va=psub(ff,idx,a)
            inv/=va**mm
            sl=K(ff.diff(K.ring.gens[idx]))
            if sl:
                local={j:K((-1)**j*comb(mm+j-1,j))*(sl/va)**j for j in range(m)}
                prod={}
                for i,ci in ratio.items():
                    for j,cj in local.items():
                        if i+j<m:addto(prod,i+j,ci*cj)
                ratio=clean(prod)
        ns=[psub(R.numer,idx,a,j) for j in range(m)]
        for j in range(m):
            vj=sum((ns[i]*ratio.get(j-i,K.zero) for i in range(j+1)),K.zero)*inv
            if vj:poles[a,m-j]=vj
    return clean(pol),poles

@lru_cache(maxsize=5000)
def shuffle(a,b):
    if not a:return {b:1}
    if not b:return {a:1}
    d=Counter()
    for w,c in shuffle(a[1:],b).items():d[(a[0],)+w]+=c
    for w,c in shuffle(a,b[1:]).items():d[(b[0],)+w]+=c
    return dict(d)

@lru_cache(maxsize=300)
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

@lru_cache(maxsize=2000)
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
        if degree(R.numer,idx)>0 or degree(R.denom,idx)>0:addto(out,w,R.diff(X))
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
        sh=shuffle((1,),word[1:]).copy();mult=sh.pop(word)
        return -sum((c*phi(w) for w,c in sh.items()),K.zero)/mult
    if word[-1]==0:
        sh=shuffle((0,),word[:-1]).copy();mult=sh.pop(word)
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

    tab.update({(2, 1, 1, 1, 1):zeta6,(2, 1, 1, 2):-zeta3**2 + 25*zeta6/12,(2, 1, 2, 1):zeta3**2/2 - zeta6/2,(2, 1, 3):zeta3**2 - 13*zeta6/16,(2, 2, 1, 1):zeta3**2 - 4*zeta6/3,(2, 2, 2):3*zeta6/16,(2, 3, 1):-3*zeta3**2/2 + 53*zeta6/24,(2, 4):-zeta3**2 + 25*zeta6/12,(3, 1, 1, 1):-zeta3**2/2 + 3*zeta6/4,(3, 1, 2):-3*zeta3**2/2 + 53*zeta6/24,(3, 2, 1):3*zeta3**2 - 203*zeta6/48,(3, 3):zeta3**2/2 - zeta6/2,(4, 1, 1):-zeta3**2 + 23*zeta6/16,(4, 2):zeta3**2 - 4*zeta6/3,(5, 1):-zeta3**2/2 + 3*zeta6/4,(6,):zeta6})
    return (-1)**len(idx)*tab[tuple(idx)]

@lru_cache(maxsize=None)
def scaled_phi(word):
    """G(0 or X;X) as powers of log X. Output canonical G(0,...,0;X)."""
    if not word:return {():K.one}
    if all(a==0 for a in word):return {tuple(K.zero for a in word):K.one}
    if word[-1]!=0:return {():phi(word)}
    sh=shuffle((0,),word[:-1]).copy();mult=sh.pop(word)
    out={}
    for w,c in scaled_phi(word[:-1]).items():
        addto(out,(K.zero,)+w,c*(len(w)+1))
    for ww,m in sh.items():
        for w,c in scaled_phi(ww).items():addto(out,w,-m*c)
    return {w:c/mult for w,c in clean(out).items()}

@lru_cache(maxsize=2000)
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

@lru_cache(maxsize=2000)
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

def audit_primitive(ant,R,word,idx):
    """Exact derivative check in the unique partial-fraction basis.
    Differentiate the basis, not an enormous spectator denominator squared.
    """
    residual={};X=GEN[idx]
    def accum(f,w,sign=1):
        pp,po=apart(f,idx)
        for nn,c in pp.items():addto(residual,(w,'poly',K.zero,nn),sign*c)
        for (aa,nn),c in po.items():addto(residual,(w,'pole',aa,nn),sign*c)
    for ww,c in ant.items():
        pp,po=apart(c,idx)
        for nn,co in pp.items():
            if nn:addto(residual,(ww,'poly',K.zero,nn-1),nn*co)
        for (aa,nn),co in po.items():
            addto(residual,(ww,'pole',aa,nn+1),-nn*co)
        if ww:accum(c/(X-ww[0]),ww[1:])
    accum(R,word,-1)
    assert not clean(residual),('Exact primitive audit',idx,residual)
    return True

# Large spectator fractions are certified by linearity from elementary
# primitives and the complete exact partial-fraction decomposition. This
# avoids expanding a common spectator denominator merely to cancel it again.
_full_audit_primitive=audit_primitive
AUDIT_METHODS={'full_normal_form':0,'linear_constructor':0,'elementary_primitives':0}
@lru_cache(maxsize=5000)
def audit_basis(kind,root,power,word,idx):
    ans=integrate_basis(kind,root,power,word,idx)
    R=GEN[idx]**power if kind=='poly' else (GEN[idx]-root)**(-power)
    _full_audit_primitive(ans,R,word,idx)
    AUDIT_METHODS['elementary_primitives']+=1
    return True

def audit_primitive(ant,R,word,idx):
    denominator_bound=1
    for ff,mm in R.denf.items():
        denominator_bound*=comb(len(ff)+mm-1,mm)
        if denominator_bound>=350:break
    if len(R.numer)+denominator_bound<350:
        AUDIT_METHODS['full_normal_form']+=1
        return _full_audit_primitive(ant,R,word,idx)
    pp,po=apart(R,idx)
    for nn,c in pp.items():
        assert degree(c.numer,idx)<=0 and degree(c.denom,idx)<=0
        audit_basis('poly',K.zero,nn,word,idx)
    for (root,nn),c in po.items():
        assert degree(c.numer,idx)<=0 and degree(c.denom,idx)<=0
        audit_basis('pole',root,nn,word,idx)
    AUDIT_METHODS['linear_constructor']+=1
    return True
