"""Homogeneous Laurent coefficient reconstruction from subgraph residues.
All exponents use squared-distance powers, and integration measure is /kappa_d.
At two internal vertices this computes the jet through epsilon^1 using only
Gamma products, plus the known finite tetrahedron in its regular orbit.
"""
from __future__ import annotations
from itertools import combinations, permutations
from fractions import Fraction as F
import random
from functools import lru_cache
import mpmath as mp
from jet_engine import X,D,HALF,Engine

ZERO=X()
def edge(g,i,j):return g.get(tuple(sorted((i,j))),ZERO)
def subset_graph(g,vs):return {(i,j):x for (i,j),x in g.items() if i in vs and j in vs and x}
def relabel(g,mapping):
    out={}
    for (i,j),x in g.items():
        if not x or mapping[i]==mapping[j]:continue
        p=tuple(sorted((mapping[i],mapping[j])));out[p]=out.get(p,ZERO)+x
    return out

def invert(g,nodes,root):
    out=dict(g)
    for i in nodes:
        if i!=root:
            # The other root is fixed at unit distance; its edge to root is irrelevant.
            out[tuple(sorted((i,root)))]=D-sum((edge(g,i,j) for j in nodes if j!=i),ZERO)
    return out

def pole_sets(g,nodes,roots):
    """All critical local and large-distance logarithmic cluster hyperplanes."""
    out=[];internal=tuple(v for v in nodes if v not in roots)
    for k in range(2,len(nodes)):
        for vs in combinations(nodes,k):
            vs=frozenset(vs)
            if all(r in vs for r in roots):continue
            a=sum((x for (i,j),x in g.items() if i in vs and j in vs),ZERO)
            if a.a==2*(k-1):out.append(('UV',vs))
    for k in range(1,len(internal)+1):
        for vs in combinations(internal,k):
            vs=frozenset(vs)
            a=sum((x for (i,j),x in g.items() if i in vs or j in vs),ZERO)
            if a.a==2*k:out.append(('IR',vs))
    return out

def pole_L(g,kind,vs):
    if kind=='UV':return HALF*(len(vs)-1)-sum((x for (i,j),x in g.items() if i in vs and j in vs),ZERO)
    return sum((x for (i,j),x in g.items() if i in vs or j in vs),ZERO)-HALF*len(vs)

def kernel_small(E,g,nodes,roots,kite=True):
    nodes=tuple(nodes);roots=tuple(roots);ints=[v for v in nodes if v not in roots]
    if not ints:return {0:mp.mpf(1)}
    if len(ints)==1:
        x=ints[0];return E.conv(edge(g,x,roots[0]),edge(g,x,roots[1]))
    if len(ints)==2:
        x,y=ints
        return E.kite(edge(g,roots[0],x),edge(g,roots[1],x),edge(g,roots[0],y),edge(g,roots[1],y),edge(g,x,y))
    raise ValueError('kernel has too many internal vertices')

def residue(E,g,nodes,roots,kind,vs):
    """Res_{L_gamma=0} I = normalized projective subgraph period times cograph."""
    if kind=='IR':
        g=invert(g,nodes,roots[0]);vs=vs|{roots[0]}
    vs=tuple(sorted(vs));anchor=next((v for v in roots if v in vs),vs[0]);other=next(v for v in vs if v!=anchor)
    sg=subset_graph(g,vs)
    period=kernel_small(E,sg,vs,(anchor,other))
    mapping={v:anchor if v in vs else v for v in nodes}
    cg=relabel(g,mapping);cn=tuple(sorted(set(mapping.values())));cr=tuple(mapping[r] for r in roots)
    cograph=kernel_small(E,cg,cn,cr)
    return E.mul(period,cograph)

def graph_at(g,w,z):return {p:X(x.a,x.b+z*w.get(p,F(0))) for p,x in g.items()}

def completion_star_value(E,comp,i,j):
    """K5: edge i-j=0, put i at infinity and integrate unique vertex j."""
    remaining=[v for v in range(5) if v not in (i,j)]
    # among remaining, two fixed roots and one integrated vertex
    r0,r1,v=remaining
    args=[edge(comp,j,k) for k in remaining]
    assert sum(args,ZERO)==D,(args,sum(args,ZERO))
    pref=E.gr([HALF]+[HALF-a for a in args],args)
    cg={}
    for a,b in combinations(remaining,2):
        opposite=next(k for k in remaining if k not in (a,b))
        cg[a,b]=edge(comp,a,b)+HALF-edge(comp,j,opposite)
    return E.mul(pref,kernel_small(E,cg,remaining,(r0,r1)))

class PolarEngine(Engine):
    @lru_cache(None)
    def kite(self,*es):
        direct=self.direct_kite(es)
        if direct is not None:return direct
        comp=self.completion(es)
        # An identically absent completion edge gives an exact Gamma reduction.
        for (i,j),x in comp.items():
            if not x:
                try:return completion_star_value(self,comp,i,j)
                except (ZeroDivisionError,ValueError):pass
        if all(x.a==1 for x in comp.values()):return {0:self.T/2,1:mp.mpf(0)}
        a,b,c,f,r=es;g={(0,2):a,(1,2):b,(0,3):c,(1,3):f,(2,3):r};nodes=(0,1,2,3);roots=(0,1)
        poles=pole_sets(g,nodes,roots)
        for attempt in range(80):
            rng=random.Random(793+attempt)
            w={p:F(rng.randrange(-13,14)) for p in g}
            gw={p:X(x.a,w[p]) for p,x in g.items()}
            pdata=[];zs=[];bad=False
            for kind,vs in poles:
                L=pole_L(g,kind,vs);W=pole_L(gw,kind,vs).b
                if not W or not L.b:bad=True;break
                z=-L.b/W
                if z in zs:bad=True;break
                zs.append(z);pdata.append((kind,vs,z,W))
            if bad:continue
            # Two distinct zero-edge reference points fix the polynomial of degree 1.
            cw=self.completion(tuple(X(x.a,w[p]) for x,p in zip(es,[(0,2),(1,2),(0,3),(1,3),(2,3)])))
            refs=[]
            for p,x in comp.items():
                if x.a==0 and cw[p].b:
                    z=-x.b/cw[p].b
                    if z not in zs and z not in [s[0] for s in refs]:refs.append((z,p))
            if len(refs)<2:continue
            try:
                residues=[]
                for kind,vs,z,W in pdata:
                    rr=residue(self,graph_at(g,w,z),nodes,roots,kind,vs)
                    residues.append((z,{k:rr.get(k+1,mp.mpf(0))/self.m(W) for k in (-2,-1,0,1)}))
                values=[]
                for z,(i,j) in refs[:2]:
                    ee=tuple(X(x.a,x.b+z*w[p]) for x,p in zip(es,[(0,2),(1,2),(0,3),(1,3),(2,3)]))
                    val=completion_star_value(self,self.completion(ee),i,j)
                    values.append((z,val))
                out={}
                for k in (-2,-1,0,1):
                    def polar(z):return sum(rr[k]/self.m(z-zp) for zp,rr in residues)
                    ps0=polar(F(0))
                    if k<0:out[k]=ps0
                    elif k==0:out[k]=ps0+values[0][1].get(0,0)-polar(values[0][0])
                    else:
                        z1,v1=values[0];z2,v2=values[1]
                        c1=v1.get(1,0)-polar(z1);c2=v2.get(1,0)-polar(z2)
                        out[k]=ps0+(self.m(z2)*c1-self.m(z1)*c2)/self.m(z2-z1)
                # reference consistency for the constant
                ck0=values[1][1].get(0,0)-sum(rr[0]/self.m(values[1][0]-zp) for zp,rr in residues)
                ck1=values[0][1].get(0,0)-sum(rr[0]/self.m(values[0][0]-zp) for zp,rr in residues)
                if abs(ck0-ck1)>mp.mpf('1e-35')*(1+abs(ck0)+abs(ck1)):
                    raise ArithmeticError(('inconsistent kite reconstruction',es,ck0,ck1,attempt))
                return out
            except (ZeroDivisionError,ValueError):continue
        raise ValueError(('unable to find regular kite reconstruction',es,comp))

if __name__=='__main__':
    mp.mp.dps=60;d=2;T=(mp.gamma(mp.mpf(1)/4)/mp.gamma(mp.mpf(3)/4))**4
    E=PolarEngine(d,T,N=5);u=X(1,F(-1,4))
    for name,es in [('parallel',(u,u,u,u,2*u)),('cross',(u,2*u,2*u,u,u))]:
        out=E.kite(*es);print(name,{k:mp.nstr(out.get(k,0),25) for k in (-2,-1,0,1)})
