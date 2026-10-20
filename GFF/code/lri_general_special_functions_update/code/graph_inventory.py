#!/usr/bin/env python3
"""Exact tadpole-free 1PI phi^4 graph data for L=1,...,5, no integrals.
Each isomorphism class records a vertex automorphism factor, exact Wick
weights and the first Symanzik polynomial as complements of spanning trees.
Python >=3.10; standard library only.  Parallel edges have distinct indices.
"""
from itertools import combinations, permutations
from fractions import Fraction
from math import factorial, prod
from pathlib import Path
import argparse, json, time

def labelled_graphs(n):
    pairs=list(combinations(range(n),2)); E=2*n-2
    deg=[0]*n; vals=[0]*len(pairs)
    remaining=[[0]*n for _ in range(len(pairs)+1)]
    for k in range(len(pairs)-1,-1,-1):
        remaining[k]=remaining[k+1].copy()
        i,j=pairs[k]; remaining[k][i]+=1; remaining[k][j]+=1
    def rec(k,total):
        if total>E or total+sum(4-v for v in deg)//2<E:return
        if k==len(pairs):
            if total!=E or min(deg)<2:return
            for mask in range(1,1<<(n-1)):
                if sum(v for v,(i,j) in zip(vals,pairs) if ((mask>>i)^(mask>>j))&1)<2:return
            yield tuple(vals); return
        i,j=pairs[k]
        for v in range(min(3,4-deg[i],4-deg[j],E-total)+1):
            vals[k]=v; deg[i]+=v; deg[j]+=v
            if all(deg[q]+3*remaining[k+1][q]>=2 for q in range(n)):
                yield from rec(k+1,total+v)
            deg[i]-=v; deg[j]-=v
    return list(rec(0,0))

def weights(n,m):
    pairs=list(combinations(range(n),2));deg=[0]*n
    for v,(i,j) in zip(m,pairs):deg[i]+=v;deg[j]+=v
    e=[4-k for k in deg]
    w4=Fraction(24,prod(factorial(x) for x in e)*prod(factorial(x) for x in m))
    w2=w4*Fraction(sum(x*(x-1) for x in e),12)
    return e,w4,w2

def primitive(n,m):
    pairs=list(combinations(range(n),2))
    # Proper connected subgraphs with >=4 external legs: their maximal
    # induced version suffices to detect an ultraviolet subdivergence.
    for mask in range(1,(1<<n)-1):
        v=mask.bit_count()
        if v<2:continue
        E=sum(x for x,(i,j) in zip(m,pairs) if mask>>i&1 and mask>>j&1)
        if E>=2*(v-1):return False
    return True

def U_masks(n,edges):
    allmask=(1<<len(edges))-1; out=[]
    for ids in combinations(range(len(edges)),n-1):
        parent=list(range(n))
        def root(i):
            while parent[i]!=i:i=parent[i]
            return i
        ok=True
        for e in ids:
            a,b=map(root,edges[e])
            if a==b:ok=False;break
            parent[a]=b
        if ok:out.append(allmask^sum(1<<i for i in ids))
    return sorted(out)

def inventory(L):
    n=L+1;pairs=list(combinations(range(n),2));idx={p:i for i,p in enumerate(pairs)}
    maps=[[idx[tuple(sorted((p[i],p[j])))] for i,j in pairs] for p in permutations(range(n))]
    gg=labelled_graphs(n); todo=set(gg); rows=[]
    while todo:
        m=min(todo)
        orbit={tuple(m[i] for i in pp) for pp in maps}
        assert orbit<=set(gg)
        todo-=orbit;aut=factorial(n)//len(orbit)
        e,w4,w2=weights(n,m)
        edges=[list(pair) for v,pair in zip(m,pairs) for _ in range(v)]
        u=U_masks(n,edges)
        assert all(mask.bit_count()==L for mask in u)
        rows.append(dict(id=f'L{L}G{len(rows)+1:03d}',multiplicities=list(m),edges=edges,
             external_halfedges=e,orbit=len(orbit),automorphism_order=aut,
             wick4=str(w4),wick2=str(w2),weight4=str(w4/aut),weight2=str(w2/aut),
             weightH=str((3*w2-w4)/aut),primitive=primitive(n,m),U_monomial_masks=u))
    all4=sum((Fraction(row['weight4']) for row in rows),Fraction(0))
    all2=sum((Fraction(row['weight2']) for row in rows),Fraction(0))
    nz=sum(row['orbit'] for row in rows if Fraction(row['weightH']))
    return dict(loop=L,vertices=n,edges=2*L,labelled_count=len(gg),class_count=len(rows),
           total_weight4=str(all4),total_weight2=str(all2),
           labelled_nonzero_combined=nz,labelled_zero_combined=len(gg)-nz,
           primitive_class_count=sum(row['primitive'] for row in rows),graphs=rows)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('graph_inventory.json'))
    parser.add_argument('--max-loops',type=int,default=5,choices=range(1,6));args=parser.parse_args()
    data={'convention':'sum over vertex-isomorphism classes with w/Aut; every internal edge is separately indexed',
          'U_definition':'sum over masks: product(x_e for e whose bit is set); no external-momentum polynomial',
          'loops':[]}
    for L in range(1,args.max_loops+1):
        t=time.time();row=inventory(L);data['loops'].append(row)
        print({k:v for k,v in row.items() if k!='graphs'},'seconds',round(time.time()-t,3),flush=True)
    expected=[1,6,85,1890,59145]
    assert [r['labelled_count'] for r in data['loops']]==expected[:args.max_loops]
    if args.max_loops==5:
        assert data['loops'][-1]['labelled_zero_combined']==9540
        assert data['loops'][-1]['labelled_nonzero_combined']==49605
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,indent=2)+'\n')

if __name__=='__main__':main()
