# Cheap float64 checks of the top-log recursion c_n = -(w1/(n-2)) c_{n-1}, w1=7/2 (theory cross-check only).
import numpy as np, math
d4=np.load('<PROJECT>/lri_1d_c4_exact/results/a8b57b2e8475/c4_1d_L2000.npz')
d5=np.load('<PROJECT>/lri_1d_c5_exact/results/040d92b3bd1d/c5_1d_L500.npz')
A=math.pi+4*math.log(2); C2=A/9; C3=-3.71985632290183342249; C4=45.42488010356; C5=-731.1394766245398
a2=-40/(81*math.sqrt(math.pi)); w1=3.5
pred={2:a2}
for n in range(3,6): pred[n]=-(w1/(n-2))*pred[n-1]
print('predicted top-log coeffs', {k:round(v,6) for k,v in pred.items()})
L=d4['even_L'].astype(float); i4=4*d4['even_L']
c2=d4['C2'][i4]; c3=d4['C3'][i4]; c4=d4['even_C4Dconn']; c4r=d4['even_C4raw']
def fit(L,y,cols,lo,hi=1e9):
    m=(L>=lo)&(L<=hi); l=np.log(L[m]); X=np.column_stack([f(L[m],l) for f in cols])
    s=np.linalg.norm(X,axis=0); p,res,rk,sv=np.linalg.lstsq(X/s,y[m],rcond=None); p/=s
    return p, np.max(abs(X@p-y[m])), sv[0]/sv[-1]
def tower(maxlog):  # Lam^{-j/2} log^k with k<=maxlog(j)
    cols=[]; names=[]
    for j,K in maxlog:
        for k in range(K+1):
            cols.append(lambda L,l,j=j,k=k: L**(-j/2)*l**k); names.append(f'j{j}k{k}')
    return cols,names
# C2 amplitude
for lo in (200,800):
    cols,nm=tower([(1,0),(2,0),(3,0),(4,0)]); p,r,c=fit(L,c2-C2,cols,lo); print(f'C2 lo{lo}: a2={p[0]:.7f} (pred {a2:.7f}) res {r:.1e}')
# C3: top log j1k1 (A fixed exact)
for lo in (100,200,400):
    cols,nm=tower([(1,1),(2,1),(3,1),(4,1)]); p,r,c=fit(L,c3-C3,cols,lo)
    print(f'C3 lo{lo}: j1k1={p[1]:.7f} (pred {pred[3]:.7f}) j1k0={p[0]:.5f} res {r:.1e} cond {c:.1e}')
# C4 Dconn and raw: top log j1k2 (A fixed exact for Dconn; raw has extra Lam^0 log, free const+log)
for lo in (100,200,400):
    cols,nm=tower([(1,2),(2,2),(3,2),(4,1)]); p,r,c=fit(L,c4-C4,cols,lo)
    print(f'C4Dconn lo{lo}: j1k2={p[2]:.5f} (pred {pred[4]:.5f}) res {r:.1e} cond {c:.1e}')
# window difference Delta C4 = Dconn - raw: any Lam^{-1/2} log^2 ?
dC4=c4-c4r
for lo in (100,200):
    cols,nm=tower([(0,1),(1,2),(2,2),(3,1)]); p,r,c=fit(L,dC4,cols,lo)
    print(f'dC4 lo{lo}: const {p[0]:.6f} log {p[1]:.3e} (1/17496={1/17496:.3e}) j1k2 {p[4]:.2e} j1k1 {p[3]:.2e} j1k0 {p[2]:.2e} res {r:.1e}')
# C5: window difference only (cheap); log^3 at Lam^{-1/2} in Delta C5?
L5=d5['even_L'].astype(float); dC5=d5['even_C5Dconn']-d5['even_C5raw']
for lo in (60,100):
    cols,nm=tower([(0,1),(1,3),(2,2),(3,1)]); p,r,c=fit(L5,dC5,cols,lo)
    print(f'dC5 lo{lo}: const {p[0]:.5f} log {p[1]:.2e} j1k0..3 {p[2]:.2e} {p[3]:.2e} {p[4]:.2e} {p[5]:.2e} res {r:.1e} cond {c:.1e}')
    cols,nm=tower([(0,1),(1,1),(2,2),(3,1)]); p,r,c=fit(L5,dC5,cols,lo)
    print(f'   no j1k2/k3: const {p[0]:.5f} log {p[1]:.2e} j1k0,1 {p[2]:.2e} {p[3]:.2e} res {r:.1e}')
