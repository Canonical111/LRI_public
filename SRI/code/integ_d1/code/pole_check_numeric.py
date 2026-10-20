"""Magnetization scheme, one bubble: does F(0,X,delta) have poles at X = 0 (K = 1)?
J(K,delta) formal = sum_k delta^k J_k(K), J_k = combinations of Gamma^{(n)}(2-2K) (log insertions),
g = -2 + 2K - delta K d_K log J,  F(0,X,delta) = (g - delta K g_K / g)/2,  K = 1 + X.
Print the delta^k Taylor coefficient of F(0,X,delta) for X -> 0; finite limits mean the poles cancel."""
import mpmath as mp
mp.mp.dps = 30
from functools import lru_cache
def Gd(n, s):
    # Gamma^{(n)}(s) = Gamma(s) Y_n(psi, psi', ...), complete Bell polynomial recursion
    psi = [mp.polygamma(k, s) for k in range(n + 1)]
    Y = [mp.mpf(1)]
    for m in range(n):
        Y.append(sum(mp.binomial(m, k) * psi[k] * Y[m - k] for k in range(m + 1)))
    return mp.gamma(s) * Y[n]
def J(K, d):
    s = 2 - 2*K
    L = lambda n: Gd(n, s)
    J0 = L(0)
    J1 = -K*L(2)
    J2 = -(K/3)*L(3) + (K**2/2)*L(4)
    J3 = -(K/12)*L(4) + (K**2/3)*L(5) - (K**3/6)*L(6)
    return J0 + d*J1 + d**2*J2 + d**3*J3
def F0(X, d):
    K = 1 + X
    g = lambda KK: -2 + 2*KK - d*KK*mp.diff(lambda k: mp.log(J(k, d)), KK)
    gv = g(K); gK = mp.diff(g, K)
    return (gv - d*K*gK/gv)/2
for X in ['0.2', '0.1', '0.05', '0.02', '-0.02', '-0.05']:
    X = mp.mpf(X)
    co = mp.taylor(lambda d: F0(X, d), 0, 3)
    print('X=%6s  ' % mp.nstr(X, 3) + '  '.join('d^%d: %s' % (k, mp.nstr(co[k], 10)) for k in range(4)))
