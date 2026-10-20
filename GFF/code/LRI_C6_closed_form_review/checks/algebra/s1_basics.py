import sympy as sp
from mpmath import mp, mpf, mpc, gamma, psi, pi, log, zeta, sqrt, atan, cos, sin, tan, exp, binomial, harmonic, diff, taylor, catalan, nsum, inf
mp.dps = 40
# --- delta_n trigamma and values
def H(n,p=1): return sum(mpf(1)/mpf(j)**p for j in range(1,n+1))
def a(n): return binomial(2*n,n)/mpf(4)**n
def hh(n): return log(2)+H(n)-H(2*n)
def dl(n): return pi**2/3-4*H(2*n,2)+2*H(n,2)
for n in range(0,6):
    print('delta trig', n, dl(n)-(psi(1,n+mpf(1)/2)-psi(1,n+1)))
print('d1', dl(1)-(pi**2/3-3), 'd2', dl(2)-(pi**2/3-mpf(115)/36))
# --- gamma Laurent: Gamma(-n+e)/Gamma(1/2-n+e) = a_n/(sqrt(pi) e) exp(2h e + (d-2pi^2/3)/2 e^2 + ...)
for n in range(0,5):
    f = lambda e: log(gamma(-n+e)/gamma(mpf(1)/2-n+e)*e*sqrt(pi)/a(n))
    c = taylor(f, mpf(10)**-12, 2)  # near zero
    # evaluate at small eps via taylor at eps0
    e0 = mpf('1e-15')
    c1 = diff(f, e0, 1); c2 = diff(f, e0, 2)/2
    print('gammaLaurent n=%d'%n, 'lin', c1-2*hh(n), 'quad', c2-(dl(n)-2*pi**2/3)/2, 'f(0)', f(e0))
