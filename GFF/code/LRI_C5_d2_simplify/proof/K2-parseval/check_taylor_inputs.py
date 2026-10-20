# Check the d=1 Taylor inputs imported from the note (eq:KproofLowerCoefficients, eq:KproofTaylorCancellation):
#   FF(t) = 3F2(1/2,1/2,t;1,1;1) = 1 + u t + v t^2 + ...,   GG(t) = 3F2(t,t,t;1/2+t,1/2+t;1) = 1 + sigma t^3 + w t^4 + ...
#   u = sum c_n^2/n = 4 log2 - 8G/pi ;  v = sum c_n^2 H_{n-1}/n
#   sigma = sum (n-1)!^3/((1/2)_n^2 n!) = 8 pi G - 14 zeta3 ;  w = sum (n-1)!^3/((1/2)_n^2 n!) [3H_{n-1} - 2(psi(n+1/2)-psi(1/2))]
#   claim: w + pi^2 v = pi^2 u^2/2 - pi^4/6
import sys, mpmath as mp
sys.path.insert(0, '<PROJECT>/LRI_C5_d2_simplify')
from emsum import emsum
mp.mp.dps = 25
h = mp.mpf(1)/2
c2 = lambda n: mp.exp(2*(mp.loggamma(n+h)-mp.loggamma(n+1)))/mp.pi
Hm1 = lambda n: mp.psi(0, n) + mp.euler           # H_{n-1}
gs = lambda n: mp.exp(3*mp.loggamma(n) - 2*(mp.loggamma(n+h)-mp.loggamma(h)) - mp.loggamma(n+1))
u = emsum(lambda n: c2(n)/n, 1, 40)
v = emsum(lambda n: c2(n)*Hm1(n)/n, 1, 40)
sig = emsum(gs, 1, 40)
w = emsum(lambda n: gs(n)*(3*Hm1(n) - 2*(mp.psi(0, n+h)-mp.psi(0, h))), 1, 40)
G = mp.catalan
print('u     - (4log2 - 8G/pi)      =', mp.nstr(u - (4*mp.log(2) - 8*G/mp.pi), 3))
print('sigma - (8 pi G - 14 zeta3)  =', mp.nstr(sig - (8*mp.pi*G - 14*mp.zeta(3)), 3))
print('w + pi^2 v - (pi^2u^2/2 - pi^4/6) =', mp.nstr(w + mp.pi**2*v - (mp.pi**2*u**2/2 - mp.pi**4/6), 3))
# Taylor coefficients by direct numerical differentiation of the series as a cross-check of the conventions
FF = lambda t: emsum(lambda n: mp.exp(2*(mp.loggamma(n+h)-mp.loggamma(h)) + mp.loggamma(n+t) - mp.loggamma(t) - 3*mp.loggamma(n+1)), 0, 40)
print('FF(0.01) vs 1+u t+v t^2 :', mp.nstr(FF(mp.mpf('0.01')) - (1 + u*mp.mpf('0.01') + v*mp.mpf('0.0001')), 3), ' (expect O(1e-6))')
K2 = 32*G**2 - 28*mp.zeta(3)*mp.log(2)
print('32G^2 - 28 zeta3 log2 =', mp.nstr(K2, 22), '  (finder 70-digit K2 = 3.5181091385902522416490901703077...)')
