"""Analytic-regulator reconstruction through total integration-order plus jet-order four.
Completed-graph covariance, subgraph residues and uniqueness references.
New crossed-kite coefficient Ccross is a separately supplied input, not assumed.
"""
from __future__ import annotations
from fractions import Fraction as F
from itertools import combinations, permutations
from functools import lru_cache
from collections import defaultdict
import random, time
import mpmath as mp
import sympy as sp
from jet_engine import X,D,HALF,Engine
from polar_reconstruction import ZERO,edge,pole_sets,pole_L,graph_at,relabel,subset_graph,invert
from kite_quadratic import QuadraticEngine

@lru_cache(None)
def pairs(m):return tuple(p for p in combinations(range(m+2),2) if p!=(0,1))

def complete(es,m):
    g=dict(zip(pairs(m),es));nodes=tuple(range(m+2));inf=m+2
    g[(0,1)]=(m+1)*HALF-sum(es,ZERO)
    for i in nodes:g[(i,inf)]=D-sum((edge(g,i,j) for j in nodes if j!=i),ZERO)
    return g

@lru_cache(None)
def canonical_permutation(base,m):
    c=complete(tuple(X(x) for x in base),m);n=m+3;ps=tuple(combinations(range(n),2))
    # Preserve a convenient representative for the three named two-loop patterns.
    if m==2:
        for wanted in ((1,1,1,1,1),(1,1,1,1,2),(1,1,1,2,1),(1,2,2,1,1)):
            for p in permutations(range(n)):
                if tuple(edge(c,p[i],p[j]).a for i,j in pairs(m))==wanted:return p
    best=None;bp=None
    for p in permutations(range(n)):
        word=tuple(edge(c,p[i],p[j]).a for i,j in ps)
        if best is None or word<best:best,bp=word,p
    return bp

@lru_cache(None)
def completed_linear(m):
    cols=[]
    for j in range(len(pairs(m))):
        v=[X(0,int(i==j)) for i in range(len(pairs(m)))];c=complete(v,m)
        cols.append({p:x.b for p,x in c.items()})
    return {p:tuple(col[p] for col in cols) for p in cols[0]}

@lru_cache(None)
def monomials(n,k):
    if k==0:return ((),)
    if k==1:return tuple((i,) for i in range(n))
    if k==2:return tuple((i,j) for i in range(n) for j in range(i,n))
    raise ValueError(k)
def features(v,k):
    out=[]
    for mon in monomials(len(v),k):
        z=F(1)
        for j in mon:z*=v[j]
        out.append(z)
    return out

def matrix_rank(rows):
    # The small rational matrices here have at most 15 columns.
    return sp.polys.matrices.DomainMatrix.from_Matrix(sp.Matrix([[sp.Rational(x.numerator,x.denominator) for x in r] for r in rows])).rank() if rows else 0

def mv(v,w):return sum((a*b for a,b in zip(v,w)),F(0))

class ReconstructionEngine(QuadraticEngine):
    def __init__(self,d,T,P4=0,L=0,K=0,Z=0,Ccross=0,N=7,verbose=False):
        super().__init__(d,T,K=K,Z=Z,N=N)
        self.P4=mp.mpf(P4);self.L=mp.mpf(L);self.Ccross=mp.mpf(Ccross)
        self.verbose=verbose;self.pcache={};self.gcache={};self._building=set();self.counter=defaultdict(int);self.dir_offsets=defaultdict(int);self.pole_seed=0;self.reference_seed=0
    def kernel(self,g,nodes,roots):
        nodes=tuple(nodes);r0,r1=roots;ints=[i for i in nodes if i not in roots];order=(r0,r1,*ints);m=len(ints)
        es=tuple(edge(g,order[i],order[j]) for i,j in pairs(m))
        return self.integral(es,m)
    def integral(self,es,m):
        es=tuple(es);key=(m,es)
        if key in self.gcache:return self.gcache[key]
        out=self._integral(es,m)
        self.gcache[key]=out;return out
    def _integral(self,es,m):
        if m==0:return {0:mp.mpf(1)}
        if m==1:return self.conv(*es)
        if m>4:raise ValueError('more than four integrations')
        # Exact factorization or star reduction BEFORE changing critical representative.
        g=dict(zip(pairs(m),es));nodes=tuple(range(m+2))
        for v in range(2,m+2):
            ns=[i for i in nodes if i!=v and edge(g,i,v)]
            if len(ns)==2:
                x,y=ns;a,b=edge(g,x,v),edge(g,y,v);pref=self.conv(a,b)
                if not pref:return {}
                gg={p:t for p,t in g.items() if v not in p};p=tuple(sorted((x,y)));gg[p]=gg.get(p,ZERO)+a+b-HALF
                return self.mul(pref,self.kernel(gg,[i for i in nodes if i!=v],(0,1)))
            if len(ns)==3 and sum((edge(g,v,i) for i in ns),ZERO)==D:
                return self.star(g,nodes,(0,1),v)
        c=complete(es,m);ns=tuple(range(m+3))
        # An exact zero-completion star can be evaluated without interpolation.
        for v in ns:
            present=[i for i in ns if i!=v and edge(c,i,v)]
            absent=[i for i in ns if i!=v and not edge(c,i,v)]
            if len(present)==3 and absent:
                try:return self.completed_star(c,m,v,absent[0])
                except (ZeroDivisionError,ValueError):pass
        # Regular tetrahedron and regular octahedral period.
        if m==2 and all(x.a==1 for x in c.values()):
            return {0:self.T/2,1:mp.mpf(0),2:self.Z*sum(self.m(x.b)**2 for x in c.values())}
        if m==3:
            ones=[p for p,x in c.items() if x.a==1];zeroes=[p for p,x in c.items() if x.a==0]
            if len(ones)==12 and len(zeroes)==3 and all(sum(v in p for p in zeroes)==1 for v in ns):
                return {0:self.P4,1:self.L*sum(self.m(c[p].b) for p in zeroes)/2}
        base=tuple(x.a for x in es);p=canonical_permutation(base,m)
        new=tuple(edge(c,p[i],p[j]) for i,j in pairs(m))
        # Use explicit supplied-note jets for A and B; the crossed pattern is independent here.
        nb=tuple(x.a for x in new)
        if m==2 and nb in ((1,1,1,1,2),(1,1,1,2,1)):
            try:
                ordered=(new[0],new[2],new[1],new[3],new[4])
                o=self.patternA(ordered) if nb==(1,1,1,1,2) else self.patternB(ordered)
                return {k:v for k,v in o.items() if k<=2}
            except (ZeroDivisionError,ValueError):pass
        return self.reconstruct(nb,tuple(x.b for x in new),m)
    def star(self,g,nodes,roots,v):
        ns=[i for i in nodes if i!=v and edge(g,v,i)];aa=[edge(g,v,i) for i in ns]
        if len(ns)!=3 or sum(aa,ZERO)!=D:raise ValueError('nonunique star')
        pref=self.gr([HALF]+[HALF-a for a in aa],aa)
        gg={p:x for p,x in g.items() if v not in p}
        for a,b in combinations(ns,2):
            other=next(j for j in ns if j not in (a,b));p=tuple(sorted((a,b)))
            gg[p]=gg.get(p,ZERO)+HALF-edge(g,v,other)
        return self.mul(pref,self.kernel(gg,[i for i in nodes if i!=v],roots))
    def completed_star(self,c,m,v,inf):
        nodes=[i for i in range(m+3) if i!=inf];gg={p:x for p,x in c.items() if inf not in p}
        remaining=[i for i in nodes if i!=v]
        return self.star(gg,nodes,remaining[:2],v)
    def residue(self,g,nodes,roots,kind,vs):
        if kind=='IR':g=invert(g,nodes,roots[0]);vs=vs|{roots[0]}
        vs=tuple(sorted(vs));anchor=next((v for v in roots if v in vs),vs[0]);other=next(v for v in vs if v!=anchor)
        sg=subset_graph(g,vs);period=self.kernel(sg,vs,(anchor,other))
        if not period:return {}
        mapping={v:anchor if v in vs else v for v in nodes};cg=relabel(g,mapping)
        cn=tuple(sorted(set(mapping.values())));cr=tuple(mapping[r] for r in roots)
        return self.mul(period,self.kernel(cg,cn,cr))
    def pole_data(self,base,m,seed=0):
        n=len(base);nodes=tuple(range(m+2));g=dict(zip(pairs(m),(X(a) for a in base)))
        pp=pole_sets(g,nodes,(0,1));Ls=[]
        for kind,vs in pp:
            row=[]
            for i in range(n):
                gg=dict(zip(pairs(m),(X(a,int(j==i)) for j,a in enumerate(base))))
                row.append(pole_L(gg,kind,vs).b)
            if any(row):Ls.append((kind,vs,tuple(row)))
        rng=random.Random(23741+int(seed)+self.pole_seed)
        for _ in range(100):
            w=tuple(F(rng.randint(-23,23)) for i in range(n))
            if all(mv(L,w) for _,_,L in Ls):return Ls,w
        raise ValueError('no regular direction')
    def polar(self,base,v,m,Ls,w):
        kmax=4-m;out={k:mp.mpf(0) for k in range(-m,kmax+1)}
        zs=[]
        for kind,vs,L in Ls:
            lv=mv(L,v);lw=mv(L,w)
            if not lv:raise ZeroDivisionError('critical pole at physical slope')
            z=-lv/lw
            if z in zs:raise ZeroDivisionError('colliding pole projections')
            zs.append(z)
        for (kind,vs,L),z in zip(Ls,zs):
            vp=tuple(vi+z*wi for vi,wi in zip(v,w));g=dict(zip(pairs(m),(X(a,b) for a,b in zip(base,vp))))
            rr=self.residue(g,tuple(range(m+2)),(0,1),kind,vs)
            lv=self.m(mv(L,v))
            for k in out:out[k]+=rr.get(k+1,0)/lv
        return out
    def reconstruction_references(self,base,m):
        c=complete(tuple(X(a) for a in base),m);lin=completed_linear(m);n=m+3;out=[]
        for v in range(n):
            zeros=[p for p,x in c.items() if v in p and x.a==0]
            for removed in combinations(zeros,m-1):
                rows=[lin[p] for p in removed]
                S=sp.Matrix([[sp.Rational(x.numerator,x.denominator) for x in r] for r in rows]);null=S.nullspace()
                if not null:continue
                ns=tuple(tuple(F(x) for x in z) for z in null)
                inf=next(i for i in removed[0] if i!=v)
                out.append((v,inf,ns))
        return out
    def build_polynomials(self,base,m,seedoffset=0):
        key=(m,base)
        if key in self._building:raise RuntimeError(('recursive polynomial construction',key))
        self._building.add(key)
        n=len(base);kmax=4-m
        refs=self.reconstruction_references(base,m)
        if not refs:raise ValueError(('no uniqueness reference',m,base))
        for attempt in range(8):
            Ls,w=self.pole_data(base,m,seed=attempt+seedoffset)
            matrices={k:[] for k in range(kmax+1)};values={k:[] for k in matrices};vslist=[]
            rng=random.Random(61439+attempt+self.reference_seed);success=False
            # A crossed-kite calibration supplies the one independent quadratic datum.
            for j in range(400):
                which=j%len(refs);star,inf,ns=refs[which]
                co=[F(rng.randint(-31,31)) for _ in ns]
                v=tuple(sum((co[i]*ns[i][j] for i in range(len(ns))),F(0)) for j in range(n))
                try:
                    fes={k:features(v,k) for k in matrices}
                    useful=[k for k in matrices if len(matrices[k])<len(fes[k]) and matrix_rank(matrices[k]+[fes[k]])>len(matrices[k])]
                    if not useful:continue
                    pol=self.polar(base,v,m,Ls,w)
                    es=tuple(X(a,b) for a,b in zip(base,v));c=complete(es,m)
                    exact=self.completed_star(c,m,star,inf)
                    for k in useful:
                        matrices[k].append(fes[k]);values[k].append(exact.get(k,0)-pol.get(k,0))
                    vslist.append(v)
                    if all(len(matrices[k])==len(monomials(n,k)) for k in matrices):success=True;break
                except (ZeroDivisionError,ValueError):continue
                if j>90 and m==2 and base==(1,2,2,1,1) and len(matrices[2])==14:break
            if m==2 and base==(1,2,2,1,1) and len(matrices[2])==14:
                v=tuple(-F(a,4) for a in base)
                try:
                    pol=self.polar(base,v,m,Ls,w);fe=features(v,2)
                    if matrix_rank(matrices[2]+[fe])==15:
                        matrices[2].append(fe);values[2].append(self.Ccross-pol[2]);success=True
                except (ZeroDivisionError,ValueError):pass
            if not success:
                if self.verbose:print('REF FAIL',m,base,{k:len(v) for k,v in matrices.items()},flush=True)
                continue
            coeff={}
            for k,mat in matrices.items():
                sm=sp.Matrix([[sp.Rational(x.numerator,x.denominator) for x in r] for r in mat]);iv=sm.inv()
                coeff[k]=[sum(self.m(F(iv[i,j]))*values[k][j] for j in range(iv.cols)) for i in range(iv.rows)]
            if self.verbose:print('POLY',m,base,'refs',len(vslist),'attempt',attempt,flush=True)
            self._building.remove(key);return Ls,w,coeff
        self._building.remove(key)
        raise ValueError(('cannot reconstruct polynomial remainder',m,base))
    def reconstruct(self,base,v,m):
        key=(m,base)
        if key not in self.pcache:self.pcache[key]=self.build_polynomials(base,m)
        for attempt in range(12):
            Ls,w,coeff=self.pcache[key]
            try:
                pol=self.polar(base,v,m,Ls,w)
                for k,cs in coeff.items():pol[k]+=sum(c*self.m(x) for c,x in zip(cs,features(v,k)))
                return pol
            except ZeroDivisionError as err:
                if 'critical pole at physical slope' in str(err):raise
                self.dir_offsets[key]+=11
                if self.verbose:print('NEW DIRECTION',m,base,self.dir_offsets[key],str(err),flush=True)
                self.pcache[key]=self.build_polynomials(base,m,self.dir_offsets[key])
        raise ValueError(('no noncolliding direction',m,base,v))

if __name__=='__main__':
    import json
    mp.mp.dps=45
    d=2;T=(mp.gamma(mp.mpf(1)/4)/mp.gamma(mp.mpf(3)/4))**4
    E=ReconstructionEngine(2,T,Ccross=0,N=6,verbose=True)
    u=X(1,F(-1,4));es=(u,2*u,2*u,u,u)
    print('CROSS:',E.integral(es,2),flush=True)
    from polar_reconstruction import PolarEngine
    O=PolarEngine(d,T,N=5);old=O.kite(*es)
    new=E.integral(es,2)
    print('diff', {k:mp.nstr(new[k]-old[k],10) for k in (-2,-1,0,1)},flush=True)
    rows=json.load(open('graphs_n5.json'))
    for r in rows:
        pp=list(combinations(range(5),2));g={p:m*u for p,m in zip(pp,r['edges']) if m}
        print('BEGIN',r['index'],flush=True)
        val=E.kernel(g,range(5),(0,1))
        print('RESULT',r['index'],{k:mp.nstr(val.get(k,0),15) for k in (-3,-2,-1,0,1)},flush=True)
