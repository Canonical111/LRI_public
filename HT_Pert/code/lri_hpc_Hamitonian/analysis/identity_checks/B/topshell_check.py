import numpy as np, json
from htb_big import *
from fitlib import load
R=load()
# 1) identity: C4(Dfull_c)-C4(g2D) == -(1/3)[Evac_c(L)-Evac_c(L-1)]_4
for L in [8,16,32,48,64]:
    d=R[L]; v=d['vac']
    c=d['variants']
    sh_c=-(np.array(v[str(2*L)][1])-np.array(v[str(2*L-2)][1]))[4]/3
    sh_r=-(np.array(v[str(2*L)][0])-np.array(v[str(2*L-2)][0]))[4]/3
    print(L,'C4 shift Dfull_c-g2D %.15f  -(1/3)topshell_c %.15f | Dfull_raw-g2D %.15f -(1/3)topshell_raw %.15f'%(
        c['Dfull_c']['C'][4]-c['g2D']['C'][4], sh_c, c['Dfull_raw']['C'][4]-c['g2D']['C'][4], sh_r))
# 2) only g1^4 contributes: recompute top shell with r=0,g=(0,1/3,0,0,0)
for L in [8,16,24]:
    sp8=BigSpace(L,8); S=bubble_S_table(L+1,K)
    r0=np.zeros(K+1); g0=np.zeros(K+1); g0[1]=1/3
    d=R[L]; r=np.array(d['r3']); g=np.array(d['g3'])
    a=vacuum_at(sp8,r0,g0,[2*L,2*L-1,2*L-2],S)
    b=vacuum_at(sp8,r,g,[2*L,2*L-1,2*L-2],S)
    for i,nm in ((0,'raw'),(1,'conn')):
        Ya=a[2*L][i][4]-a[2*L-1][i][4]; Za=a[2*L-1][i][4]-a[2*L-2][i][4]
        Yb=b[2*L][i][4]-b[2*L-1][i][4]; Zb=b[2*L-1][i][4]-b[2*L-2][i][4]
        print(L,nm,'Y(E0=L) g1-only %.15f full %.15f | Z(E0=L-1/2) g1-only %.15f full %.15f'%(Ya,Yb,Za,Zb))
