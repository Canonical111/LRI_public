# C4Dconn(L) - C4 exact: free vs fixed Lam^{-1/2} log^2 coefficient across bases (float64, cheap).
import numpy as np, math, itertools
d4=np.load('<PROJECT>/lri_1d_c4_exact/results/a8b57b2e8475/c4_1d_L2000.npz')
C4=45.42488010356; a2=-40/(81*math.sqrt(math.pi)); P=a2*3.5**2/2
L=d4['even_L'].astype(float); y0=d4['even_C4Dconn']-C4
def run(spec,lo,fix):
    m=L>=lo; l=np.log(L[m]); y=y0[m].copy(); cols=[]
    for j,K in spec:
        for k in range(K+1):
            if fix and (j,k)==(1,2): y-=P*L[m]**-0.5*l**2; continue
            cols.append(L[m]**(-j/2)*l**k)
    X=np.column_stack(cols); s=np.linalg.norm(X,axis=0)
    p=np.linalg.lstsq(X/s,y,rcond=None)[0]/s; r=y-X@p
    return (p[2] if not fix else P), np.sqrt(np.mean(r**2)), np.max(abs(r))
specs={'S1':[(1,2),(2,2),(3,2),(4,1)],'S2':[(1,2),(2,1),(3,2),(4,1)],'S3':[(1,2),(2,2),(3,2),(4,2),(5,1)],
       'S4':[(1,2),(2,2),(3,1)],'S5':[(1,2),(2,2),(3,2),(4,2)],'S6':[(1,2),(2,3),(3,2),(4,1)]}
print('pred log^2 coeff',P)
for nm,sp in specs.items():
    for lo in (60,100,200,300):
        cf,rms,mx=run(sp,lo,False); _,rms2,mx2=run(sp,lo,True)
        print(f'{nm} lo{lo:4d}: free c12={cf:+.5f} rms {rms:.2e} max {mx:.2e} | fixed rms {rms2:.2e} max {mx2:.2e} ratio {rms2/rms:.2f}')
