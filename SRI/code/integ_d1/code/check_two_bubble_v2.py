"""Two-bubble check with singularities handled analytically (scipy, double precision, error estimates)."""
import numpy as np
from scipy.integrate import quad
from scipy.special import gamma as G
def C1(t, g, K):
    return np.exp(2*K*(np.log(t+g) + np.log(g+1-t) - np.log(g) - np.log1p(g))) - 1.0
def I(t, K):
    a = 1.0 - 2*K
    # (0, t): g = t w^(1/a), removes g^(-2K)
    f0 = lambda w: C1(t, t*w**(1/a), K) * t/a * w**(1/a - 1) if w > 0 else (t/a if K > 0 else 0.0) * 0.0
    def f0(w):
        g = t*w**(1/a)
        # (C-1) g^{2K} is regular; write C-1 = [(t+g)^2K (g+1-t)^2K (1+g)^-2K - g^2K] g^-2K
        reg = (t+g)**(2*K)*(g+1-t)**(2*K)*(1+g)**(-2*K) - g**(2*K)
        return reg * t**(1-2*K) / a          # g^{-2K} dg = t^{1-2K}/a dw
    i0, e0 = quad(f0, 0, 1, limit=200, epsabs=1e-14, epsrel=1e-13)
    i1, e1 = quad(lambda g: C1(t, g, K), t, 1, limit=200, epsabs=1e-14, epsrel=1e-13)
    i2, e2 = quad(lambda v: C1(t, 1/v, K)/v**2, 0, 1, limit=200, epsabs=1e-14, epsrel=1e-13)
    return i0 + i1 + i2, e0 + e1 + e2
def R_gas(K):
    if K == 0: return 1.5, 0.0
    errs = []
    def outer(t):
        v, e = I(t, K); errs.append(e); return v - 0.5
    val, err = quad(outer, 0, 1, weight='alg', wvar=(-2*K, -2*K), limit=200, epsabs=1e-13, epsrel=1e-12)
    A2 = G(3 - 4*K) * val
    c1 = 2*G(2 - 2*K); c2 = 2*(4*K - 3)*A2
    return c2/c1**2, abs(G(3-4*K)*err*2*(4*K-3)/c1**2) + max(errs)
def R_ba(K):
    return np.sqrt(np.pi)*G(2.5 - 2*K)*G(1 - K)**2/(2*G(1 - 2*K)*G(1.5 - K)**2)
for K in [0.0, 0.1, 0.2, 0.3, 0.4, 0.45]:
    rg, er = R_gas(K); rb = R_ba(K)
    print(f'K={K:<5} kink gas {rg:.13f} (+-{er:.1e})   formula {rb:.13f}   diff {rg-rb:+.2e}')
