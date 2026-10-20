from fractions import Fraction as F
from itertools import combinations
import json,random
import mpmath as mp
from jet_engine import X,D,HALF
from polar_reconstruction import PolarEngine,edge,pole_sets,pole_L,graph_at,residue,kernel_small,ZERO

def remove_two_vertex(E,g,nodes,roots,v):
    ns=[i for i in nodes if i!=v and edge(g,v,i)]
    if len(ns)!=2:raise ValueError('not a two-neighbour vertex')
    a,b=ns;x,y=edge(g,v,a),edge(g,v,b)
    pref=E.conv(x,y);gg={p:z for p,z in g.items() if v not in p}
    p=tuple(sorted((a,b)));gg[p]=gg.get(p,ZERO)+x+y-HALF
    nn=[x for x in nodes if x!=v]
    return E.mul(pref,kernel_small(E,gg,nn,roots))

def star_value(E,g,nodes,roots,v):
    ns=[i for i in nodes if i!=v and edge(g,v,i)]
    if len(ns)!=3:raise ValueError('not a three-neighbour vertex')
    alphas=[edge(g,v,i) for i in ns]
    if sum(alphas,ZERO)!=D:raise ValueError('not a unique star')
    pref=E.gr([HALF]+[HALF-a for a in alphas],alphas)
    gg={p:x for p,x in g.items() if v not in p}
    for a,b in combinations(ns,2):
        other=next(j for j in ns if j not in (a,b));p=tuple(sorted((a,b)))
        gg[p]=gg.get(p,ZERO)+HALF-edge(g,v,other)
    nn=[i for i in nodes if i!=v]
    return E.mul(pref,kernel_small(E,gg,nn,roots))

def evaluate(E,row,seed=0,star_choice=0):
    n=5;nodes=tuple(range(5));roots=(0,1);pairs=list(combinations(nodes,2))
    g={p:X(m,F(-m,4)) for p,m in zip(pairs,row['edges']) if m}
    for v in (2,3,4):
        if sum(bool(edge(g,v,i)) for i in nodes if i!=v)==2:
            val=remove_two_vertex(E,g,nodes,roots,v)
            return {k:val.get(k,0) for k in (-3,-2,-1,0)}, {'method':'convolution','vertex':v}
    if row['index']==7:
        return {-3:mp.mpf(0),-2:mp.mpf(0),-1:2*E.T/3,0:mp.mpf(0)},{'method':'completed tetrahedron; linear period jet vanishes'}
    stars=[v for v in (2,3,4) if sum(bool(edge(g,v,i)) for i in nodes if i!=v)==3]
    star=stars[star_choice%len(stars)]
    poles=pole_sets(g,nodes,roots)
    for attempt in range(120):
        rng=random.Random(881+seed*139+attempt)
        w={p:F(rng.randrange(-31,32)) for p in g}
        gw={p:X(x.a,w[p]) for p,x in g.items()}
        pdata=[];zs=[];bad=False
        for kind,vs in poles:
            L=pole_L(g,kind,vs);W=pole_L(gw,kind,vs).b
            if not W or not L.b:bad=True;break
            z=-L.b/W
            if z in zs:bad=True;break
            zs.append(z);pdata.append((kind,vs,z,W))
        if bad:continue
        Wstar=sum(w[p] for p in g if star in p)
        if not Wstar:continue
        zref=F(1,1)/Wstar
        if zref in zs:continue
        try:
            rdata=[]
            for kind,vs,z,W in pdata:
                rr=residue(E,graph_at(g,w,z),nodes,roots,kind,vs)
                rdata.append((z,{k:rr.get(k+1,mp.mpf(0))/E.m(W) for k in (-3,-2,-1,0)}))
            ref=star_value(E,graph_at(g,w,zref),nodes,roots,star)
            result={}
            for k in (-3,-2,-1,0):
                def polar(z):return sum(rr[k]/E.m(z-zp) for zp,rr in rdata)
                result[k]=polar(F(0))
                if k<0:
                    expected=ref.get(k,0);actual=polar(zref)
                    if abs(expected-actual)>mp.mpf('1e-30')*(1+abs(expected)+abs(actual)):
                        raise ArithmeticError(('five-vertex pole check failed',row['index'],k,expected,actual,seed,attempt))
                else:result[k]+=ref.get(0,0)-polar(zref)
            return result,{'method':'pole reconstruction and unique-star reference','star':star,'direction_attempt':attempt,'seed':seed,'poles':len(poles)}
        except (ZeroDivisionError,ValueError):continue
    raise ValueError(('unable to find reference for five-vertex graph',row['index']))

if __name__=='__main__':
    mp.mp.dps=60
    rows=json.load(open('graphs_n5.json'))
    for d in (2,):
        T=(mp.gamma(mp.mpf(1)/4)/mp.gamma(mp.mpf(3)/4))**4
        E=PolarEngine(d,T,N=5);sums={k:mp.mpf(0) for k in (-3,-2,-1,0)};out=[]
        for row in rows:
            val,meta=evaluate(E,row)
            print(row['index'], {k:mp.nstr(val[k],23) for k in val},meta,flush=True)
            w=E.m(F(row['weight']))
            for k in sums:sums[k]+=w*val[k]
            out.append(dict(index=row['index'],jet={k:mp.nstr(v,45) for k,v in val.items()},metadata=meta))
        A=E.A;R=E.R;M=mp.gamma(-E.q)*mp.gamma(2*E.q)**2/mp.gamma(3*E.q)
        b3=T+mp.mpf(87)/4*A*A-mp.mpf(9)/4*R+M
        expect={-3:mp.mpf(18),-2:11*A,-1:b3/9+mp.mpf(3)/2*A*A+mp.mpf(45)/2*R+mp.mpf(4)/3*M}
        print('SUM', {k:mp.nstr(v,35) for k,v in sums.items()})
        print('POLE EXPECTATION',{k:mp.nstr(v,35) for k,v in expect.items()})
        json.dump(dict(d=d,graphs=out,sums={k:mp.nstr(v,45) for k,v in sums.items()},expected_poles={k:mp.nstr(v,45) for k,v in expect.items()}),open(f'five_vertex_d{d}.json','w'),indent=2)
