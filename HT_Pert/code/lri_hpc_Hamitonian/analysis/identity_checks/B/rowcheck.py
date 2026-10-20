import numpy as np
from htb import *
for L in [8,16,24]:
    sp=Space(L,11,4); r,g,refs=tune(sp,4)
    S=bubble_S_table(L+1,4)
    raw,conn,sp8=vacuum_tables(L,4,r,g,None,S)
    Xg=g2D_diag(sp,g,4*L,S); W=window_W(sp)
    for nm,tab in (('raw',raw),('conn',conn)):
        Xd=dfull_diag(sp,tab)
        e2=np.max(np.abs(Xd[:,2]-Xg[:,2])); e3=np.max(np.abs(Xd[:,3]-Xg[:,3]-g[1]**3*W))
        # eps^4 difference beyond g2D, grouped by window type (Lam-E0 floor to half-integer)
        print(f'L={L} {nm}: max|Dfull2-g2D2|={e2:.1e}  max|Dfull3-g2D3-g1^3 W|={e3:.1e} over {sp.dim} states')
