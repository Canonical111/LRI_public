import mpmath as mp
from check_integrals import gamma_ratio
from full_kite_checks import full
mp.mp.dps=65

def J(d,alpha,b):
    return mp.pi**d*gamma_ratio([d/2-b,2*alpha+b-d,alpha+b-d/2,alpha+b-d/2],
                               [alpha,alpha,d/2,2*alpha+2*b-d])
def chain(d,indices):
    x=sum(indices)-d
    return mp.gamma(d/2)**2*mp.fprod(mp.gamma(d/2-a)/mp.gamma(a) for a in indices)*mp.gamma(x)/mp.gamma(d/2-x)

def coeffs(d,T):
 q=d/4
 A=mp.digamma(2*q)-2*mp.digamma(q)+mp.digamma(1)
 R=mp.polygamma(1,2*q)-mp.polygamma(1,1)
 B=mp.digamma(-q)-mp.digamma(q)
 S=mp.polygamma(1,-q)-mp.polygamma(1,q)
 K=gamma_ratio([1-q,2*q,2*q,2*q],[1+q,4*q])/54
 M=gamma_ratio([-q,2*q,2*q],[3*q])
 b3=T+mp.mpf(87)/4*A*A-mp.mpf(9)/4*R+M
 a2=-K;a3=a2*(4*A/3-B/4)
 a4=a2*(mp.mpf(25)/36*A*A-A*B/3+(B*B+S)/32+R/6-2*T/27)
 return A,R,M,b3,a2,a3,a4

if __name__=='__main__':
 for ds in ('1','2','3'):
  d=mp.mpf(ds);q=d/4
  T=(6*mp.gamma(mp.mpf(1)/4)**4/mp.pi if d==1 else (mp.gamma(mp.mpf(1)/4)/mp.gamma(mp.mpf(3)/4))**4 if d==2 else mp.mpf('30.1026153873244'))
  A,R,M,b3,a2,a3,a4=coeffs(d,T)
  kap=mp.pi**(d/2)/mp.gamma(d/2)
  print('d',ds,'target a4',mp.nstr(a4,28))
  for es in ('0.02','0.01','0.005'):
   e=mp.mpf(es);u=(d-e)/4
   J2=J(d,u,3*u);J3=J(d,u,5*u-d/2);J4=J(d,u,7*u-d)
   H=mp.gamma(d/2)*gamma_ratio([e/2,e/2,d/2-e],[2*u,2*u,e])
   p2=full(float(d),float(e),2,h=.01 if d==1 else .02)
   p4=full(float(d),float(e),4,h=.01 if d==1 else .02)
   Ksum=chain(d,[3*u,u,3*u])/36+p2/4+chain(d,[2*u,2*u,2*u])/8+p4/4+chain(d,[u,3*u,u])/12
   f2=J2/(6*kap**2)
   f3=(J2/e-H*J3/4)/kap**2
   f4=((mp.mpf(9)/(2*e**2)-A/e)*J2-9*H*J3/(4*e)+Ksum*J4)/kap**2
   gs=e/3+2*A/9*e**2+(8*A*A/27-b3/81)*e**3
   amp=f2*gs**2+f3*gs**3+f4*gs**4
   extr=(amp-a2*e**2-a3*e**3)/e**4
   print(' epsilon',es,'extracted effective a4',mp.nstr(extr,24))
