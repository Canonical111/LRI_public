"""Two-dimensional five-edge two-point master via split-contour KLT.
All powers are actual coordinate distance powers; normalization d2x/pi.
Analytic continuation uses one common complex regulator, not conjugation.
"""
import mpmath as mp
from itertools import permutations

def hyper3(a,b,transform=True):
    a=list(map(mp.mpc,a));b=list(map(mp.mpc,b));S=sum(b)-sum(a)
    options=[(mp.re(S),a,b,mp.mpf(1))]
    if transform:
      for k in range(3):
        x=a[k]; y,z=[a[j] for j in range(3) if j!=k]
        for j in range(2):
          e,f=b[j],b[1-j]
          # Thomae transformation with new excess e-x.
          aa=[x,f-y,f-z];bb=[f,S+x]
          if any(mp.almosteq(w,mp.floor(mp.re(w))) and mp.im(w)==0 and mp.re(w)<=0 for w in bb):continue
          try:fac=mp.gammaprod([e,S],[e-x,S+x])
          except ValueError:continue
          options.append((mp.re(e-x),aa,bb,fac))
    options.sort(key=lambda t:float(t[0]),reverse=True)
    exc,aa,bb,fac=options[0]
    if exc<=0: raise ValueError(('no convergent Thomae representative',a,b,S))
    from hyper3_fast import hyper3_direct
    return fac*hyper3_direct(aa,bb,N=128,K=30,J=18)

def ordered(a,b,A,B,c,transform=True):
    return mp.beta(a+1,c+1)*mp.beta(a+A+c+2,B+1)*hyper3([-b,a+1,a+A+c+2],[a+c+2,a+A+B+c+3],transform)

def mixed(a,b,A,B,c,transform=True):
    return mp.beta(a+1,-a-b-c-1)*mp.beta(B+1,-A-B-c-1)*hyper3([-c,a+1,B+1],[-b-c,-A-c],transform)

def kite(p,transform=True):
    a,b,A,B,c=[-mp.mpc(x)/2 for x in p]
    v1=mp.sinpi(a)*mp.sinpi(B)*ordered(a,b,A,B,c,transform)*mixed(a,b,A,B,c,transform)
    v2=mp.sinpi(A)*mp.sinpi(b)*ordered(A,B,a,b,c,transform)*mixed(A,B,a,b,c,transform)
    return (v1+v2)/mp.pi**2

def beta(p,r):
    p=mp.mpc(p);r=mp.mpc(r)
    return mp.gammaprod([1-p/2,1-r/2,(p+r)/2-1],[p/2,r/2,2-(p+r)/2])

if __name__=='__main__':
 import time,json
 mp.mp.dps=40;t=time.time()
 out=[]
 for p in [[1]*5,[mp.mpf('0.9'),mp.mpf('1.2'),mp.mpf('0.8'),mp.mpf('1.15'),mp.mpf('0.95')]]:
  a=kite(p);print(p,mp.nstr(a,40),'sec',time.time()-t,flush=True)
  out.append(str(a))
 print('T check',mp.nstr(kite([1]*5)-mp.gamma(mp.mpf('.25'))**8/(8*mp.pi**4),5))
