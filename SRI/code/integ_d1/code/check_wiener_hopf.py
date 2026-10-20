"""Check of the Wiener-Hopf step: solve the anisotropic-Kondo Bethe-ansatz impurity equation
   f(x) + int_0^inf a2(x-y) f(y) dy = a1(D - x),  x > 0      (x = B - lambda, D = B - Lambda)
numerically (Nystrom) and compare N_imp = int f with the derived Mellin-Barnes result
   M = 1 - 2 N_imp = 1 + pi^-1/2 (1/2 pi i) int dt Gamma(t) Gamma(1/2-(1-K)t) X^-t / Gamma(1+Kt),  -1<Re t<0,
   K = 1 - gamma/pi,  X = exp(gamma D'),  D' = D + c/pi,  c = p log p - (p-1) log(p-1),  p = pi/gamma."""
import numpy as np, mpmath as mp
from numpy.polynomial.legendre import leggauss
def a_n(lam, n, g):
    return g*np.sin(n*g)/(2*np.pi*(np.cosh(g*lam) - np.cos(n*g)))
def N_imp_numeric(D, g, L=None, n=1600):
    L = L or 60.0/g
    # Gauss-Legendre on [0, L] in two panels for accuracy near 0
    xs, ws = [], []
    for lo, hi, m in [(0, 10/g, n//2), (10/g, L, n//2)]:
        t, w = leggauss(m); xs.append((hi-lo)/2*t + (hi+lo)/2); ws.append((hi-lo)/2*w)
    x = np.concatenate(xs); w = np.concatenate(ws)
    A = np.eye(len(x)) + a_n(x[:, None] - x[None, :], 2, g) * w[None, :]
    f = np.linalg.solve(A, a_n(D - x, 1, g))
    return float(np.sum(w * f))
def M_mb(D, g):
    mp.mp.dps = 30
    p = mp.pi/g; K = 1 - g/mp.pi
    c = p*mp.log(p) - (p-1)*mp.log(p-1)
    X = mp.e**(g*(D + c/mp.pi))
    cc = mp.mpf(-0.5)
    f = lambda tau: (mp.gamma(cc+1j*tau)*mp.gamma(0.5-(1-K)*(cc+1j*tau))*X**(-(cc+1j*tau))/mp.gamma(1+K*(cc+1j*tau)))
    I = mp.quad(f, [-mp.inf, 0, mp.inf]) / (2*mp.pi)
    return 1 + mp.re(I)/mp.sqrt(mp.pi)
for g in [0.4, 0.7, 1.2]:
    for D in [-6.0, -2.0, 0.0, 2.0, 6.0]:
        Nn = N_imp_numeric(D, g)
        Mn = 1 - 2*Nn
        Mf = float(M_mb(D, g))
        print(f'gamma={g:.1f} (K={1-g/np.pi:.4f})  D={D:+.1f}   M_numeric={Mn:.12f}   M_formula={Mf:.12f}   diff={Mn-Mf:+.2e}')
