"""3F2(1) by explicit gamma-ratio tail subtraction (not an error enclosure)."""
import mpmath as mp
from functools import lru_cache
@lru_cache(None)
def bern_coeff(n):
 return tuple(mp.bernfrac(k) if hasattr(mp,'bernfrac')else None for k in range(n+1))

def hyp3(a,b,N=64,order=32):
 a=list(map(mp.mpc,a));b=list(map(mp.mpc,b))
 # exact terminating numerator
 termin=[int(-x.real)for x in a if x.imag==0 and x.real<=0 and x.real==int(x.real)]
 limit=min(termin)+1 if termin else N
 term=mp.mpc(1);sm=mp.mpc(0)
 for n in range(limit):
  sm+=term
  if n+1<limit:term*=mp.fprod(x+n for x in a)/(mp.fprod(x+n for x in b)*(n+1))
 if termin:return sm
 sigma=sum(b)-sum(a)
 logs=[mp.mpc(0)]
 for k in range(1,order):
  logs.append((-1)**(k+1)*(sum(mp.bernpoly(k+1,x)for x in a)-sum(mp.bernpoly(k+1,x)for x in b)-mp.bernpoly(k+1,1))/(k*(k+1)))
 cc=[mp.mpc(1)]
 for k in range(1,order):cc.append(sum(j*logs[j]*cc[k-j]for j in range(1,k+1))/k)
 pref=mp.fprod(mp.gamma(x)for x in b)*mp.fprod(mp.rgamma(x)for x in a)
 return sm+pref*sum(cc[k]*mp.zeta(1+sigma+k,N)for k in range(order))

if __name__=='__main__':
 import time
 mp.mp.dps=40;t=time.time()
 a=[.5,.5,.3];b=[1,1.2]
 x=hyp3(a,b);y=mp.hyper(a,b,1)
 print('reference',mp.nstr(x-y,12),'time',time.time()-t)
 a=[mp.mpc('.5','.02'),mp.mpc('.02','.01'),mp.mpc('.02','.01')];b=[mp.mpc('.52','.01')]*2
 x=hyp3(a,b);y=hyp3(a,b,N=96,order=40)
 print('different tails',mp.nstr(x-y,12),'time',time.time()-t)
