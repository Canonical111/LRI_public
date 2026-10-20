import json, numpy as np, mpmath as mp
from fitlib import fit
D={}
for f in ['topshell_a.log','topshell_b.log','topshell_c.log']:
    for line in open(f):
        if line.startswith('{'): d=json.loads(line); D[d['L']]=d
# add small L via the full runs (conn tables) in g1=1 units: Y_c = 81*Y, Z=81*Z
from fitlib import load
R=load()
for L,d in R.items():
    if L<16 or L in D: continue
    v={int(j):np.array(x[1]) for j,x in d['vac'].items()}
    D[L]={'Yc':81*(v[2*L][4]-v[2*L-1][4]),'Z':81*(v[2*L-1][4]-v[2*L-2][4])}
L=np.array(sorted(D),float)
for key in ['Yc','Z']:
    y=np.array([D[int(l)][key] for l in L]); out=[]
    for mn,m in {'1,2':[(1,0),(2,0)],'1,1l,2,2l':[(1,0),(1,1),(2,0),(2,1)],'1,3h,2':[(1,0),(1.5,0),(2,0)],'h,1,3h,2':[(0.5,0),(1,0),(1.5,0),(2,0)],'1,1l,2':[(1,0),(1,1),(2,0)]}.items():
        for Lmin in [24,40]:
            c,r,n=fit(L,y,m,Lmin); out.append(c[0])
    print(key,'L<=%d'%L.max(),'last %.8f'%y[-1],'limits',np.round(out,6).tolist())
