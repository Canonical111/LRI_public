"""High-precision L_sub for the LRI circle spectrum: exact head sum to N plus tail from the
asymptotic expansion of f(n) = log(1-v)+v+v^2/2 in t = n^{-1/2}, summed with Hurwitz zeta."""
import mpmath as mp
mp.mp.dps = 50
a, b = mp.mpf(1)/4, mp.mpf(3)/4
p0 = mp.gamma(b)/mp.gamma(a)
v = lambda n: 3*p0*mp.gamma(n+a)/mp.gamma(n+b)
f = lambda n: mp.log(1-v(n)) + v(n) + v(n)**2/2
K = 40                                   # Stirling terms
d = [(-1)**(k+1)*(mp.bernpoly(k+1, a) - mp.bernpoly(k+1, b))/(k*(k+1)) for k in range(1, K+1)]
M = 60                                   # order in t
def fseries():
    # log r(n) + (1/2) ln n = sum_k d_k n^{-k} = sum_k d_k t^{2k}
    L = [mp.mpf(0)]*(M+1)
    for k, dk in enumerate(d, start=1):
        if 2*k <= M: L[2*k] = dk
    # v = 3 p0 t exp(L(t))
    E = mp.taylor(lambda t: mp.exp(sum(L[j]*t**j for j in range(M+1))), 0, M)
    V = [mp.mpf(0)] + [3*p0*E[j] for j in range(M)]          # coefficients of t^1..t^M
    F = mp.taylor(lambda t: (lambda x: mp.log(1-x)+x+x**2/2)(sum(V[j]*t**j for j in range(M+1))), 0, M)
    return F
F = fseries()
def tail(N):
    return mp.fsum(F[m]*mp.zeta(mp.mpf(m)/2, N+1) for m in range(3, M+1))
for N in (200, 400, 800):
    head = mp.fsum(f(n) for n in range(2, N+1))
    print(N, mp.nstr(2*(head + tail(N)), 30))
