import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import sys,mpmath as mp,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'lri_numerical_resolution/verification/source'))
from ising_five_loop import chebpoly
root=Path(__file__).resolve().parent
def weights(N,L=6,maxr=5):
 fn=root/f'w_{L}_{N}.bin'
 if fn.exists():return
 mp.mp.dps=80
 pol=chebpoly(N);cx=[[mp.cos(mp.pi*k*i/N)for k in range(N+1)]for i in range(N+1)]
 out=np.zeros((L-1,2*L+1,maxr+2,N+1))
 for axis in range(L-1):
  for b2 in range(2*L+1):
   a2=2*(L-2-axis)-b2;a=mp.mpf(a2)/2;b=mp.mpf(b2)/2
   jr=int(-a-1) if a2<=-2 and a2%2==0 else -1
   mom=[]
   for poly in pol:
    row=[]
    for r in range(-1,maxr+1):
     if r==-1:val=mp.mpf(poly[jr])/b if 0<=jr<len(poly) else mp.mpf(0)
     else:val=mp.fsum(mp.mpf(c)*(-b)**r/(mp.mpf(k)+a+1)**(r+1)for k,c in enumerate(poly)if k!=jr)
     row.append(val)
    mom.append(row)
   for i in range(N+1):
    factor=mp.mpf(2)/N*(mp.mpf('.5')if i in (0,N)else 1)
    for r in range(maxr+2):out[axis,b2,r,i]=float(factor*mp.fsum((mp.mpf('.5')if k in (0,N)else 1)*cx[i][k]*mom[k][r]for k in range(N+1)))
   if jr==0:out[axis,b2,0,:]=0;out[axis,b2,0,-1]=float(1/b)
 out.tofile(fn)
 print('weights',L,N,flush=True)
if __name__=='__main__':
 for L in map(int,sys.argv[1].split(',')):
  for N in map(int,sys.argv[2].split(',')):weights(N,L)
