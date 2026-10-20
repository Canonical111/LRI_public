from pathlib import Path
import sys,math,json
import numpy as np
import mpmath as mp
W=Path(__file__).resolve().parents[1]
from chebyshev_coefficients import chebpoly

def weights(L,N,order=7):
 fn=W/f'inputs/cw_L{L}_N{N}.bin'
 if fn.exists():return
 mp.mp.dps=100;D=L-1;K=order-L;M=order-1;nn=N+1
 pol=chebpoly(N);cx=[[mp.cos(mp.pi*k*i/N) for k in range(nn)]for i in range(nn)]
 out=np.zeros((D,2*L+1,M+2,nn),dtype=np.longdouble)
 for axis in range(D):
  for b2 in range(2*L+1):
   a=mp.mpf(L-2-axis)-mp.mpf(b2)/2;b=mp.mpf(b2)/2
   jr=int(-a-1) if a<=-1 and int(2*a)%2==0 else -1
   mom=[]
   for pp in pol:
    row=[]
    for r in range(-1,M+1):
     if r==-1: val=mp.mpf(pp[jr])/b if 0<=jr<len(pp) and b else mp.mpf(0)
     else: val=mp.fsum(mp.mpf(c)*(-b)**r/(mp.mpf(k)+a+1)**(r+1)for k,c in enumerate(pp)if k!=jr)
     row.append(val)
    mom.append(row)
   for i in range(nn):
    factor=mp.mpf(2)/N*(mp.mpf('.5')if i in (0,N)else 1)
    for r in range(M+2):
     val=factor*mp.fsum((mp.mpf('.5')if k in (0,N)else 1)*cx[i][k]*mom[k][r]for k in range(nn))
     out[axis,b2,r,i]=np.longdouble(str(val))
   if jr==0:out[axis,b2,0,:]=0;out[axis,b2,0,-1]=np.longdouble(str(1/b))
 out.tofile(fn)
 # gamma(1+Lz)*2^(Lz)/gamma(1+z)^L, independent of forest.
 log=[mp.mpf(0)]*(M+1);log[1]=L*mp.log(2)
 for j in range(2,M+1):log[j]=(L**j-L)*mp.polygamma(j-1,1)/mp.factorial(j)
 cf=[mp.mpf(1)]+[mp.mpf(0)]*M
 for j in range(1,M+1):cf[j]=mp.fsum(k*log[k]*cf[j-k]for k in range(1,j+1))/j
 (W/f'inputs/cgamma_L{L}.txt').write_text(' '.join(str(x)for x in cf)+'\n')
 print('weights',L,N,flush=True)
if __name__=='__main__':
 for L in map(int,sys.argv[1].split(',')):
  for N in map(int,sys.argv[2].split(',')):weights(L,N)
