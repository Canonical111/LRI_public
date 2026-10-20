"""Independent monomial moments, including pole and negative-power cases."""
from pathlib import Path
import numpy as np,mpmath as mp,json
W=Path(__file__).resolve().parents[1];mp.mp.dps=100;checks=[]
for L in [3,5,6,7]:
 for N in [1,3,5,6]:
  fn=W/f'inputs/cw_L{L}_N{N}.bin'
  if not fn.exists():continue
  w=np.fromfile(fn,dtype=np.longdouble).reshape(L-1,2*L+1,8,N+1)
  for ax in sorted(set([0,L-2])):
   for b2 in [1,2,2*L-2,2*L]:
    a=mp.mpf(L-2-ax)-mp.mpf(b2)/2;b=mp.mpf(b2)/2
    for k in [0,1,N]:
     f=[((1+mp.cos(mp.pi*i/N))/2)**k for i in range(N+1)]
     for r in [-1,0,2,6]:
      exact=(1/b if r==-1 else 0)if a+k+1==0 else (0 if r==-1 else (-b)**r/(a+k+1)**(r+1))
      calc=mp.fsum(mp.mpf(str(w[ax,b2,r+1,i]))*f[i]for i in range(N+1));err=abs(calc-exact)/max(1,abs(exact));checks.append(dict(L=L,N=N,axis=ax,edge_count=b2,monomial=k,power=r,error=str(err)))
maxerr=max(mp.mpf(r['error'])for r in checks)
print('worst', sorted(checks,key=lambda r:mp.mpf(r['error']),reverse=True)[:10]);assert maxerr<mp.mpf('2e-8')
(W/'verification/meromorphic_weight_checks.json').write_text(json.dumps({'checks':len(checks),'maximum_normalized_error':str(maxerr),'rows':checks},indent=2));print('moment checks',len(checks),'max',mp.nstr(maxerr,8))
