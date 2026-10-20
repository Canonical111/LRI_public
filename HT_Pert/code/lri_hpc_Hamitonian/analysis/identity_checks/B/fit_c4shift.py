import numpy as np
from fitlib import *
R=load(); L=np.array(list(R.keys()),float)
sc=np.array([R[int(l)]['variants']['Dfull_c']['C'][4]-R[int(l)]['variants']['g2D']['C'][4] for l in L])
sr=np.array([R[int(l)]['variants']['Dfull_raw']['C'][4]-R[int(l)]['variants']['g2D']['C'][4] for l in L])
Hodd=np.array([sum(1/e for e in range(1,int(l),2)) for l in L])
print('check raw-conn == Hodd(L-1)/(81*3*36):',np.max(np.abs((sr-sc)-Hodd/(81*3*36))))
for l,a in zip(L,sc): pass
print(' L  shift_conn')
for l,a in list(zip(L,sc))[::4]: print(int(l),'%.12f'%a)
models={'1':[(1,0)],'1,2':[(1,0),(2,0)],'1,1l':[(1,0),(1,1)],'1,1l,2':[(1,0),(1,1),(2,0)],
        'h':[(0.5,0)],'h,1':[(0.5,0),(1,0)],'h,1,3h':[(0.5,0),(1,0),(1.5,0)],'1,3h':[(1,0),(1.5,0)],'1,3h,2':[(1,0),(1.5,0),(2,0)],
        '1,1l,2,2l':[(1,0),(1,1),(2,0),(2,1)],'h,1,1l':[(0.5,0),(1,0),(1,1)]}
for mn,m in models.items():
    out=[]
    for Lmin in [12,16,24,32,40,48]:
        c,res,n=fit(L,sc,m,Lmin); out.append('%.6f(%.0e)'%(c[0],res))
    print(f'{mn:12s}',' '.join(out))
# residual pattern Λ mod 4
c,res,n=fit(L,sc,models['1,1l,2'],16)
pred=basis_cols(L,models['1,1l,2'])@c
print('residuals (1,1l,2; Lmin16):',' '.join('%d:%+.1e'%(int(l),r) for l,r in zip(L,sc-pred) if l>=16))
