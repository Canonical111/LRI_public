"""Exact affine-pole discovery; modular images only filter candidates.
Every accepted factor is checked by exact division and the remaining degree
must be zero. No probabilistic step enters an integration identity.
"""
from functools import lru_cache
from hyperlog_core import K,GEN,degree,polykey

def spec(p,idx,prime):
    values=[37,1009,7919,65537,99991,33461,45893,131,137,139,149]
    powers=[]
    for j in range(K.ngens):
        dj=degree(p,j)
        vv=1 if j==idx else values[j]%prime
        powers.append([pow(vv,n,prime) for n in range(dj+1)])
    coeff=[0]*(degree(p,idx)+1)
    for mon,c in p.items():
        val=int(c.numerator)%prime*pow(int(c.denominator),-1,prime)%prime
        for j,nn in enumerate(mon):
            if j!=idx and nn:val=val*powers[j][nn]%prime
        coeff[mon[idx]]=(coeff[mon[idx]]+val)%prime
    return coeff,values

def polyval(cs,z,p):
    ans=0
    for c in reversed(cs):ans=(ans*z+c)%p
    return ans

@lru_cache(maxsize=20000)
def affine_poles(key,idx):
    p=K.ring.from_dict(dict(key));dd=degree(p,idx)
    if dd<=0:return ()
    p1=1000000007;p2=1000000009
    cs1,vals=spec(p,idx,p1);cs2,_=spec(p,idx,p2)
    cand=[]
    for c in range(-24,25):
        for j in [0]+[j for j in range(1,len(GEN)) if j!=idx]:
            for sign in ([1] if j==0 else [1,-1]):
                ev=c*37+(sign*vals[j] if j else 0)
                if polyval(cs1,ev,p1)==0 and polyval(cs2,ev,p2)==0:
                    root=c*GEN[0]+(sign*GEN[j] if j else K.zero)
                    cand.append(root)
        for const in [-1,1]:
            ev=c*37+const
            if polyval(cs1,ev,p1)==0 and polyval(cs2,ev,p2)==0:cand.append(c*GEN[0]+const)
    out=[];core=p
    for root in dict.fromkeys(cand):
        fac=(GEN[idx]-root).to_poly();mult=0
        while degree(core,idx)>0:
            quo,rem=core.div(fac)
            if rem:break
            core=quo;mult+=1
        if mult:out.append((fac,mult))
    if degree(core,idx)>0:
        # General exact fallback: usually unnecessary for ordered gap integrals.
        for fac,m in core.factor_list()[1]:
            if degree(fac,idx)>0:out.append((fac,m))
    assert sum(m*degree(f,idx) for f,m in out)==dd
    return tuple(out)
