import numpy as np
import scipy.special as sp
import mpmath as mp
from check_integrals import gamma_ratio,k4_selberg,kite_parts

def integration_grid(d, h, L):
    q=d/4
    n=round(2*L/h)
    x=np.linspace(-L,L,n+1)
    return -q/3+1j*x, 2*L/n

def mb_core(d,e,kind,h=0.02,L=9):
    q=d/4;u=q-e/4
    z,step=integration_grid(d,h,L)
    s=z[:,None];t=z[None,:]
    if kind==2:a1,a2,a3,a4,a5=2*u,2*u,u,u,u
    elif kind==4:a1,a2,a3,a4,a5=u,u,2*u,u,u
    lg=sp.loggamma
    x=(lg(-s)+lg(-t)+lg(d/2-a2-a3-s)+lg(d/2-a5+s)-lg(a5-s)
       +lg(d/2-a4-a3-t)+lg(d/2-a1+t)-lg(a1-t)
       +lg(a3+s+t)+lg(a1+a5-d/2-s-t)+lg(a2+a3+a4-d/2+s+t)
       -lg(d-a1-a5+s+t))
    return np.exp(x).real.sum()*step**2/(2*np.pi)**2

def single(d,e,kind,h=0.005,L=12):
    q=d/4;u=q-e/4;b=q-3*e/4
    t,step=integration_grid(d,h,L)
    lg=sp.loggamma
    if kind==2:
        x=(lg(-t)+lg(e/2-t)+2*lg(e/2+t)+lg(2*b-t)+lg(u+t)
            -lg(2*u-t)-lg(3*e/2+t))
    elif kind==4:
        x=(lg(-t)+lg(-b-t)+2*lg(q+e/4+t)+lg(q-5*e/4-t)+lg(u+t)
           -lg(u-t)-lg(q+5*e/4+t))
    return np.exp(x).real.sum()*step/(2*np.pi)

def full(d,e,kind,h=0.02):
    mp.mp.dps=60
    dm=mp.mpf(d);em=mp.mpf(str(e));q=dm/4;u=q-em/4;b=q-3*em/4
    pref=gamma_ratio([2*q,2*q],[em,2*u,u,u])
    pres=gamma_ratio([2*q,2*q,b],[2*q-em,2*u,u,u])
    simple=kite_parts(dm,em)[f'K{kind}']
    # Restore the exact single contour in place of its epsilon=0 limit.
    if kind==2:
        val=simple+mp.polygamma(1,q)+pres*single(d,e,2)
    else:
        val=simple+2*mp.polygamma(1,q)+2*pres*single(d,e,4)
    return val+pref*mb_core(d,e,kind,h=h)

if __name__=='__main__':
 for d in (1,2,3):
  for e in (.04,.02,.01):
   v2=full(d,e,2,h=.01 if d==1 else .02)
   v4=full(d,e,4,h=.01 if d==1 else .02)
   q=mp.mpf(d)/4;A=mp.digamma(2*q)-2*mp.digamma(q)+mp.digamma(1);R=mp.polygamma(1,2*q)-mp.polygamma(1,1);em=mp.mpf(str(e))
   r2=v2-8/em**2-2*A/em-4*R
   r4=v4-4/em**2-2*A/em-A*A/2-7*R/2
   print(d,e,'K2 higher remainder/e',mp.nstr(r2/em,18),'K4 higher remainder/e',mp.nstr(r4/em,18))
   if d==2:print('Selberg difference',mp.nstr(v4-k4_selberg(em),20))
