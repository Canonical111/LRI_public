"""Direct 3F2(1) with explicitly controlled asymptotic-tail truncations.
No rigorous enclosure: compare (N,K,J) and precision in all production uses.
"""
import mpmath as mp
from functools import lru_cache
from math import comb

@lru_cache(None)
def bernoullis(K,dps):return tuple(mp.bernoulli(k)for k in range(K+1))

def bernpoly(n,z,B):
    v=mp.mpc(0)
    # Horner B_n(z), including vanishing odd Bernoulli numbers.
    for k in range(n+1):v=v*z+comb(n,k)*B[k]
    return v

def hyper3_direct(a,b,N=128,K=28,J=18):
    a=list(map(mp.mpc,a));b=list(map(mp.mpc,b));s=sum(b)-sum(a)
    if mp.re(s)<=0:raise ValueError('nonconvergent original 3F2; transform first')
    term=mp.mpc(1);value=term
    for n in range(1,N):
      term*=((n-1+a[0])*(n-1+a[1])*(n-1+a[2]))/((n-1+b[0])*(n-1+b[1])*n)
      value+=term
    B=bernoullis(max(K+1,2*J),mp.mp.dps)
    logs=[mp.mpc(0)]
    for k in range(1,K+1):
      bn=sum(bernpoly(k+1,x,B)for x in a)-sum(bernpoly(k+1,x,B)for x in b)-bernpoly(k+1,1,B)
      logs.append((-1)**(k+1)*bn/(k*(k+1)))
    cs=[mp.mpc(1)]
    for k in range(1,K+1):cs.append(sum(j*logs[j]*cs[k-j]for j in range(1,k+1))/k)
    n=mp.mpf(N);zbase=mp.exp(-s*mp.log(n));tail=mp.mpc(0)
    for k,c in enumerate(cs):
      w=s+1+k
      hz=zbase/(w-1)+zbase/(2*n)
      rising=w
      ni=zbase/n**2
      for j in range(1,J+1):
        if j>1:rising*=(w+2*j-3)*(w+2*j-2);ni/=n**2
        hz+=B[2*j]/mp.factorial(2*j)*rising*ni
      tail+=c*hz;zbase/=n
    fac=mp.gammaprod(b,a)
    return value+fac*tail

if __name__=='__main__':
 import time
 mp.mp.dps=45
 for a,b in [([.5,.5,.5],[1,1]),([mp.mpf('.5')+.012j,mp.mpf('.5')-.034j,mp.mpf('.1')+.001j],[1+.009j,mp.mpf('.3')-.005j]),([-.01j,.5+.01j,1-.02j],[.5+.023j,1+.024j])]:
  t=time.time();u=hyper3_direct(a,b);print('fast',mp.nstr(u,40),time.time()-t,flush=True)
  t=time.time();v=hyper3_direct(a,b,256,36,22);print('increased residual',mp.nstr(u-v,6),time.time()-t,flush=True)
  t=time.time();ref=mp.hyper(a,b,1);print('literal residual',mp.nstr(u-ref,6),time.time()-t,flush=True)
