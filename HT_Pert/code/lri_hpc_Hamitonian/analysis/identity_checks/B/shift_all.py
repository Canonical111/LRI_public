import json, glob, numpy as np
from fitlib import load, fit, basis_cols
R=load()
S={L:R[L]['variants']['Dfull_c']['C'][4]-R[L]['variants']['g2D']['C'][4] for L in R}
for f in ['topshell_a.log','topshell_b.log','topshell_c.log']:
    for line in open(f):
        if line.startswith('{'):
            d=json.loads(line); S.setdefault(d['L'],d['shift_conn'])
            if d['L'] in R: assert abs(S[d['L']]-d['shift_conn'])<1e-13
S=dict(sorted(S.items()))
L=np.array(list(S),float); y=np.array(list(S.values()))
print('n',len(L),'Lmax',L.max())
models={'1,2':[(1,0),(2,0)],'1,1l,2':[(1,0),(1,1),(2,0)],'1,1l,2,2l':[(1,0),(1,1),(2,0),(2,1)],'1,3h,2':[(1,0),(1.5,0),(2,0)],
        'h,1,3h':[(0.5,0),(1,0),(1.5,0)],'h,1,3h,2':[(0.5,0),(1,0),(1.5,0),(2,0)],'h,1,1l,2':[(0.5,0),(1,0),(1,1),(2,0)],'1,1l,3h,2':[(1,0),(1,1),(1.5,0),(2,0)]}
res={}
for mn,m in models.items():
    out=[]
    for Lmin in [16,24,32,48,64]:
        c,r,n=fit(L,y,m,Lmin); out.append(c[0]); 
    res[mn]=out
    print(f'{mn:12s}',' '.join('%.7f'%x for x in out))
c,r,n=fit(L,y,models['1,1l,2,2l'],24)
print('coeffs 1,1l,2,2l (Lmin24):',c,'maxres',r)
json.dump({'L':L.tolist(),'shift':y.tolist(),'fit_1_1l_2_2l_Lmin24':c.tolist()},open('shift_all.json','w'),indent=1)
