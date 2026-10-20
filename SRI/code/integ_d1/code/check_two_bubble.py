"""Independent check of the magnetization formula against the s=1 kink gas (no Bethe ansatz).
log Z / L = y^2 Gamma(1-2K)(2h)^(2K-1) + y^4 A2 (2h)^(4K-3) + ...,  M = 1 + d_h (log Z/L)
A2 = Gamma(3-4K) * int_0^1 dt (t(1-t))^(-2K) [ I(t) - 1/2 ],
I(t) = int_0^inf [ (t+g)^2K (g+1-t)^2K / (g^2K (1+g)^2K) - 1 ] dg      (connected two-bubble cluster)
Ratio R = [X^2 coeff]/[X coeff]^2 is independent of the normalization of X."""
import mpmath as mp
import sys
mp.mp.dps = 25
def R_gas(K):
    K = mp.mpf(K)
    def I(t):
        f = lambda g: ((t + g)**(2*K) * (g + 1 - t)**(2*K)) / (g**(2*K) * (1 + g)**(2*K)) - 1
        return mp.quad(f, [0, t, 1, mp.inf])
    inner = mp.quad(lambda t: (t*(1 - t))**(-2*K) * (I(t) - mp.mpf(1)/2), [0, mp.mpf(1)/2, 1])
    A2 = mp.gamma(3 - 4*K) * inner
    c1 = 2 * mp.gamma(2 - 2*K)            # M = 1 - c1 X + c2 X^2,  X = y^2 (2h)^(2K-2)
    c2 = 2 * (4*K - 3) * A2
    return c2 / c1**2
def R_ba(K):
    K = mp.mpf(K)
    return mp.sqrt(mp.pi) * mp.gamma(mp.mpf(5)/2 - 2*K) * mp.gamma(1 - K)**2 / (2 * mp.gamma(1 - 2*K) * mp.gamma(mp.mpf(3)/2 - K)**2)
for K in [sys.argv[1]]:
    rg = R_gas(K); rb = R_ba(K)
    print(f'K={K:5s}  kink gas {mp.nstr(rg, 18):>24}   formula {mp.nstr(rb, 18):>24}   diff {mp.nstr(rg - rb, 3)}')
