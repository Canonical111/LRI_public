# C5Dconn(L) - C5 exact: free vs fixed Lam^{-1/2} log^3 coefficient (float64 sanity only; cond is high).
import numpy as np, math
d5=np.load('<PROJECT>/lri_1d_c5_exact/results/040d92b3bd1d/c5_1d_L500.npz')
C5=-731.1394766245398; a2=-40/(81*math.sqrt(math.pi)); P=-a2*3.5**3/6
L=d5['even_L'].astype(float)
for sch in ('even_C5Dconn','even_C5raw'):
  y0=d5[sch]-C5
  specs={'M3':[(1,3),(2,3),(3,2),(4,1)],'M3b':[(1,3),(2,2),(3,2),(4,1)],'M3c':[(1,3),(2,3),(3,3),(4,2)]}
  if sch=='even_C5raw': specs={k:[(0,1)]+v for k,v in specs.items()}  # raw: allow Lam^0 log (window artifact); constant column = free intercept shift
  for nm,sp in specs.items():
    for lo in (80,120):
      out=[]
      for fix in (False,True):
        m=L>=lo; l=np.log(L[m]); y=y0[m].copy(); cols=[]
        for j,K in sp:
            for k in range(K+1):
                if fix and (j,k)==(1,3): y-=P*L[m]**-0.5*l**3; continue
                cols.append(L[m]**(-j/2)*l**k)
        X=np.column_stack(cols); s=np.linalg.norm(X,axis=0); p=np.linalg.lstsq(X/s,y,rcond=None)[0]/s; r=y-X@p
        idx=[c for c,(j,k) in enumerate([(j,k) for j,K in sp for k in range(K+1)]) if (j,k)==(1,3)][0]
        out.append((p[idx] if not fix else P, np.max(abs(r))))
      print(f'{sch[7:]:5s} {nm:4s} lo{lo}: free c13={out[0][0]:+.4f} max {out[0][1]:.1e} | fixed c13={P:.4f} max {out[1][1]:.1e}')
