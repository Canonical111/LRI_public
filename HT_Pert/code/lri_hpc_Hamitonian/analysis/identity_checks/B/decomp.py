import numpy as np
from fitlib import *
R=load(); Ls=np.array([l for l in R if l>=8],float)
rows=[]
for l in Ls:
    L=int(l); d=R[L]; v={int(j):np.array(x[1]) for j,x in d['vac'].items()}   # conn tables
    vr={int(j):np.array(x[0]) for j,x in d['vac'].items()}
    Y=v[2*L][4]-v[2*L-1][4]; Z=v[2*L-1][4]-v[2*L-2][4]; O=v[2*L-2]-v[2*L-3]; H=v[2*L-3][4]-v[2*L-4][4]
    g2d=np.array(d['rows']['d1']['g2D'])
    D1=d['variants']['Dfull_c']['spacing_d1'][4]-d['variants']['g2D']['spacing_d1'][4]
    D2=d['variants']['Dfull_c']['spacing_d2'][4]-d['variants']['g2D']['spacing_d2'][4]
    pred=(O[4]-g2d[4])+Z+Y/2
    rows.append((L,Y,Z,O[2],O[3]-g2d[3],O[4]-g2d[4],H,D1,D2,pred))
rows=np.array(rows)
print(' L      Y(P8@L)     Z(P6@L-1/2)  O2(-1/54)  O3-g2D3(1/27)  O4-g2D4     H(P2@L-3/2)   Delta4(d1)   Delta4(d2)   pred')
for r in rows[::4]: print('%3d '%r[0]+' '.join('%+.9f'%x for x in r[1:]))
print('max|Delta4(d1)-pred| %.1e  max|Delta4(d1)-Delta4(d2)| %.1e'%(np.max(np.abs(rows[:,7]-rows[:,9])),np.max(np.abs(rows[:,7]-rows[:,8]))))
L=rows[:,0]
for name,col in [('Y',1),('Z',2),('O4-g2D4',5),('H',6),('Delta4',7)]:
    y=rows[:,col]; out=[]
    for mn in ['h,1','h,1,3h','hl,h,1','hl,h,1,1l','1,1l,2']:
        m=MODELS.get(mn) or {'1,1l,2':[(1,0),(1,1),(2,0)]}[mn]
        for Lmin in [16,32]:
            c,res,n=fit(L,y,m,Lmin); out.append('%s/%d:%+.5f'%(mn,Lmin,c[0]))
    print(name,' '.join(out))
