"""Numerical tests of the analytic Laurent coefficients; not a bootstrap fit."""
import numpy as np
import scipy.special as sp
import mpmath as mp
import json

def tetra(d, h=0.025, L=9):
    q=d/4
    x=np.arange(-L,L+h/2,h)
    s=-q/3+1j*x[:,None]
    t=-q/3+1j*x[None,:]
    v=(2*sp.loggamma(-s)+2*sp.loggamma(-t)+sp.loggamma(q+s)+sp.loggamma(q+t)
       +2*sp.loggamma(q+s+t)+sp.loggamma(-s-t)-sp.loggamma(q-s)-sp.loggamma(q-t)-sp.loggamma(2*q+s+t))
    total=np.exp(v).real.sum()*h*h/(2*np.pi)**2
    return 2*np.exp(2*sp.gammaln(2*q)-4*sp.gammaln(q))*total

def gamma_ratio(num,den):
    return mp.fprod(mp.gamma(x) for x in num)/mp.fprod(mp.gamma(x) for x in den)

def k4_selberg(e):
    """Exact, analytically continued d=2 raw kite divided by kappa_2^2=pi^2."""
    u=(2-e)/4
    g=lambda x:mp.gamma(x)/mp.gamma(1-x)
    a=1-u; c=-u
    return 2*g(a)**2*g(a+c)**2*g(2*c)/(g(2*a+c)*g(2*a+2*c)*g(c))

def kite_parts(d,e):
    q=mp.mpf(d)/4;u=q-e/4;b=q-3*e/4
    A=mp.digamma(2*q)-2*mp.digamma(q)+mp.digamma(1)
    R=mp.polygamma(1,2*q)-mp.polygamma(1,1)
    # Gamma and digamma pieces that determine the full Laurent jet through epsilon^0.
    D4=gamma_ratio([2*q,2*q,b,b,e,e,2*q-2*e,e/2],
                   [u,u,2*u,2*q-e,2*q-e,2*e])
    P2=gamma_ratio([2*q,e/2,b,b],[2*u,u,u])
    W=(-mp.digamma(e/2)-2*mp.digamma(e)-mp.digamma(2*q-e)
       +2*mp.digamma(b)+mp.digamma(2*q)-mp.digamma(2*b)+2*mp.digamma(1))
    K2=P2*W-mp.polygamma(1,q)
    K4=D4-2*mp.polygamma(1,q)
    return dict(K2=K2,K4=K4,A=A,R=R)

if __name__=='__main__':
 mp.mp.dps=80
 print('Tetrahedron MB checks:')
 for d in (1,2,3):
  for h in (0.03,0.02,0.0125):
   print(d,h,repr(tetra(d,h)))
 print('Laurent checks:')
 e=mp.mpf('1e-20')
 for d in ('1','2','3'):
  k=kite_parts(d,e);A=k['A'];R=k['R']
  c2=k['K2']-8/e**2-2*A/e
  c4=k['K4']-4/e**2-2*A/e
  print(d,'K2 finite',mp.nstr(c2,25),'target',mp.nstr(4*R,25))
  print(d,'K4 finite',mp.nstr(c4,25),'target',mp.nstr(A*A/2+7*R/2,25))
 A=4*mp.log(2)
 exact=k4_selberg(e)-4/e**2-2*A/e
 print('d2 complex Selberg K4 finite',mp.nstr(exact,30),'target',mp.nstr(A*A/2,30))
