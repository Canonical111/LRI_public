"""Exact full-period boundary functional using sparse rational word coefficients.
No transcendental values are assigned. Constant at infinity of G(w;t) is R_w.
The returned dict maps words to rational coefficients; () denotes 1.
"""
from fractions import Fraction as F
from functools import lru_cache
from math import factorial, comb

def add(out,src,scale=F(1)):
 if not scale:return
 for k,c in (src.items() if isinstance(src,dict) else src):
  x=out.get(k,F(0))+scale*c
  if x:out[k]=x
  else:out.pop(k,None)

@lru_cache(maxsize=150000)
def small(w,P):
 """Taylor--log expansion through t^P at the tangential origin."""
 if not w:return (((0,0),F(1)),)
 a=w[0];tail=dict(small(w[1:],P));out={}
 if a==0:
  for (n,k),c in tail.items():
   if n==0:
    out[(0,k+1)]=out.get((0,k+1),F(0))+c/F(k+1)
   else:
    for j in range(k+1):
     key=(n,k-j);v=c*F((-1)**j*factorial(k),factorial(k-j)*n**(j+1));out[key]=out.get(key,F(0))+v
 else:
  for (n,k),c in tail.items():
   for j in range(P-n):
    nn=n+j+1;coef=-c/F(a)**(j+1)
    for z in range(k+1):
     key=(nn,k-z);v=coef*F((-1)**z*factorial(k),factorial(k-z)*nn**(z+1));out[key]=out.get(key,F(0))+v
 return tuple((k,c) for k,c in out.items() if c)

@lru_cache(maxsize=100000)
def ant(kind,a,p,w):
 """Laurent polynomial (degree >= -1) of primitive coefficients, and CT at 0.
Terms O(t^-2) in rational prefactors cannot contribute for kappa >= -1.
"""
 a=F(a)
 if kind=='poly':
  out={(p+1,w):F(1,p+1)}
  if w:
   b=F(w[0]);scale=-F(1,p+1)
   for j in range(p+1):
    aa,_=ant('poly',0,p-j,w[1:]);add(out,aa,scale*b**j)
   aa,_=ant('pole',b,1,w[1:]);add(out,aa,scale*b**(p+1))
  return tuple(out.items()),F(0)
 if p==1:return (((0,(a,)+w),F(1)),),F(0)
 m=p-1;out={}
 if m==1:out[(-1,w)]=F(-1)
 if a:
  low= -F(1,m)*(-a)**(-m) if not w else F(0)
 else:low=-F(1,m)*dict(small(w,m)).get((m,0),F(0))
 if w:
  b=F(w[0])
  if a==b:
   aa,bb=ant('pole',a,m+1,w[1:]);add(out,aa,F(1,m));low+=bb/F(m)
  else:
   aa,bb=ant('pole',b,1,w[1:]);sc=F(1,m)*(b-a)**(-m);add(out,aa,sc);low+=sc*bb
   for j in range(1,m+1):
    aa,bb=ant('pole',a,j,w[1:]);sc=-F(1,m)*(b-a)**(-(m-j+1));add(out,aa,sc);low+=sc*bb
 return tuple(out.items()),low

@lru_cache(maxsize=150000)
def big(w,n,k):
 """[t^-n log(t)^k]G(w;t) as a sparse vector of R periods."""
 if k<0:return ()
 if not w:return (((),F(1)),) if n==0 and k==0 else ()
 if n==0:return ((w[k:],F(1,factorial(k))),) if k<=len(w) else ()
 if k>len(w)-1:return ()
 out={}
 for h in range(len(w)-k):
  scale=-F(factorial(k+h),factorial(k)*n**(h+1))
  for r in range(n+1):add(out,big(w[1:],n-r,k+h),scale*F(w[0])**r)
 return tuple(out.items())

@lru_cache(None)
def shiftweight(power,k,kappa,N,eps_power=0,log_power=0):
 """[eps^eps_power log(eps)^log_power] eps^kappa L^power log(L)^k.
L=eps^-1-N. Includes derivatives of generalized integer binomials.
"""
 d=eps_power-kappa+power
 if d<0 or k<log_power or k-log_power>d:return F(0)
 j=k-log_power
 poly=[F(1)]
 for h in range(d):
  out=[F(0)]*(len(poly)+1)
  for i,c in enumerate(poly):out[i]+=c*(power-h);out[i+1]+=c
  poly=out
 return F((-N)**d*comb(k,log_power)*(-1)**log_power*factorial(j),factorial(d))*poly[j]

@lru_cache(maxsize=150000)
def upperword(w,p,kappa,N,eps_power=0,log_power=0):
 out={}
 for n in range(max(0,eps_power-kappa+p+1)):
  for k in range(log_power,len(w)+1):
   c=shiftweight(p-n,k,kappa,N,eps_power,log_power)
   if c:add(out,big(w,n,k),c)
 return tuple(out.items())

def upperant(AA,kappa,N,eps_power=0,log_power=0):
 out={}
 for (p,w),c in AA:add(out,upperword(w,p,kappa,N,eps_power,log_power),c)
 return out

@lru_cache(maxsize=90000)
def functional(kind,a,p,w,N,kappa=0,interval=True,eps_power=0,log_power=0):
 """Coefficient of eps^kappa int_0^L (1-eps(N+t)) R_basis(t)G_w(t)dt.
For interval=False omit the interval-length factor.
"""
 AA,low=ant(kind,F(a),p,w)
 out=upperant(AA,kappa,N,eps_power,log_power)
 if eps_power==kappa and log_power==0:add(out,{():low},F(-1))
 if not interval:return tuple(out.items())
 add(out,upperant(AA,kappa+1,N,eps_power,log_power),F(-N))
 if eps_power==kappa+1 and log_power==0:add(out,{():low},F(N))
 if kind=='poly':BB,lowB=ant('poly',0,p+1,w)
 else:
  B1,l1=ant('poly',0,0,w) if p==1 else ant('pole',F(a),p-1,w)
  temp=dict(B1);add(temp,AA,F(a));BB=tuple(temp.items());lowB=l1+F(a)*low
 add(out,upperant(BB,kappa+1,N,eps_power,log_power),F(-1))
 if eps_power==kappa+1 and log_power==0:add(out,{():lowB})
 return tuple(out.items())
