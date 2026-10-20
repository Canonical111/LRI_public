#!/usr/bin/env python3
"""Independent exact matrix-tree, orbit, and primitive-gluing checks."""
import argparse,json,itertools
from fractions import Fraction as F
from pathlib import Path

def determinant(a):
    a=[row[:] for row in a]; det=F(1)
    for j in range(len(a)):
        r=next((r for r in range(j,len(a)) if a[r][j]),None)
        if r is None:return F(0)
        if r!=j:a[j],a[r]=a[r],a[j];det=-det
        v=a[j][j];det*=v
        for k in range(j+1,len(a)):
            c=a[k][j]/v
            for t in range(j+1,len(a)):a[k][t]-=c*a[j][t]
    return det

def components(n,edges,cut):
    adj=[set() for _ in range(n)]
    for a,b in edges:adj[a].add(b);adj[b].add(a)
    rem=set(range(n))-set(cut);out=[]
    while rem:
        todo=[rem.pop()];cc=set(todo)
        while todo:
            v=todo.pop()
            for w in (adj[v]-set(cut)) & rem:rem.remove(w);cc.add(w);todo.append(w)
        out.append(sorted(cc))
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('inventory',type=Path);p.add_argument('--output',type=Path,default=Path('inventory_checks.json'));args=p.parse_args()
    data=json.loads(args.inventory.read_text());count=0;primitive=[];vacuum=[]
    for row in data['loops']:
        n=row['vertices'];assert sum(g['orbit'] for g in row['graphs'])==row['labelled_count']
        for g in row['graphs']:
            edges=g['edges'];x=list(range(2,len(edges)+2));L=[[F(0) for _ in range(n)] for _ in range(n)]
            prod=1
            for e,(a,b) in enumerate(edges):
                c=F(1,x[e]);L[a][a]+=c;L[b][b]+=c;L[a][b]-=c;L[b][a]-=c;prod*=x[e]
            det=determinant([r[:-1] for r in L[:-1]])*prod
            val=0
            for mask in g['U_monomial_masks']:
                term=1
                for e in range(len(edges)):
                    if mask>>e&1:term*=x[e]
                val+=term
            assert val==det,(g['id'],val,det);count+=1
            for v in range(n):
                cc=components(n,edges,[v])
                if len(cc)>1 and any(sum(g['external_halfedges'][j] for j in c)==0 for c in cc):
                    vacuum.append(g['id']);break
            if g['primitive'] and row['loop']>=3:
                assert F(g['weight2'])==0
                completed=edges+[[j,n] for j,e in enumerate(g['external_halfedges']) for _ in range(e)]
                cuts=[]
                for cut in itertools.combinations(range(n+1),3):
                    cc=components(n+1,completed,cut)
                    if sorted(map(len,cc))==[2,2]:cuts.append(dict(cut=list(cut),components=cc))
                primitive.append(dict(id=g['id'],aut=g['automorphism_order'],completed_edges=completed,
                                      three_vertex_cuts_two_plus_two=cuts))
    out=dict(matrix_tree_checks=count,all_matrix_tree_checks_exact=True,
             primitive=primitive,vacuum_attached_classes=vacuum,
             scope='graph and polynomial algebra only; no four/five-loop integrals evaluated')
    args.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
