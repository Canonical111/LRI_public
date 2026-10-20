#!/usr/bin/env python3
"""Review check B (foundation-rigor): Steps 2-3 of the top-mode proof (Theorem 6), r = 2, double precision.
(1) eq:Il   I_l = int_{R+iY} F(l+sigma+z) F(-z) e^{-2 pi i z} dz
            = 2 pi/Gamma(g)^{2r} int_0^{2pi} e^{i(l+sigma)V} a(V) a'(2pi-V) dV
    with, by Step 5, a(V) a'(2pi-V) = e^{i(g-1)(V-pi)} P(V) P(2pi-V),
    P(V) = int_0^V (2 sin(v/2))^{g-1} (2 sin((V-v)/2))^{g-1} dv   (r = 2).
    LHS by direct Fourier quadrature (scipy QAWF), independent of the Laplace representation.
    Balance is NOT needed for eq:Il, so sigma and g are chosen independently.
(2) the endpoint claim 'a(V) a'(2pi-V) = O(V^{2rg-2})' of Step 3: for rg > 1 the product behaves like V^{rg-1}."""
import numpy as np
from scipy.special import loggamma, gamma
from scipy.integrate import quad

r = 2


def F(z, g):
    return np.exp(r * (loggamma(z) - loggamma(z + g)))


def lhs(l, sig, g, Y=0.7):
    h = lambda x: F(l + sig + x + 1j * Y, g) * F(-x - 1j * Y, g) * np.exp(2 * np.pi * Y)
    tot = 0j
    for sgn in (1, -1):
        hr = lambda x: (h(sgn * x)).real
        hi = lambda x: (h(sgn * x)).imag
        # int_0^inf h(sgn x) e^{-2 pi i sgn x} dx
        c_r = quad(hr, 0, np.inf, weight='cos', wvar=2 * np.pi, limlst=200)[0]
        s_r = quad(hr, 0, np.inf, weight='sin', wvar=2 * np.pi, limlst=200)[0]
        c_i = quad(hi, 0, np.inf, weight='cos', wvar=2 * np.pi, limlst=200)[0]
        s_i = quad(hi, 0, np.inf, weight='sin', wvar=2 * np.pi, limlst=200)[0]
        tot += (c_r + 1j * c_i) - 1j * sgn * (s_r + 1j * s_i)
    return tot


def P(V, g):
    f = lambda v: (2 * np.sin(v / 2)) ** (g - 1) * (2 * np.sin((V - v) / 2)) ** (g - 1)
    a = quad(f, 0, V / 2, limit=200, epsabs=0, epsrel=1e-13)[0]
    return 2 * a


def rhs(l, sig, g):
    w = lambda V: P(V, g) * P(2 * np.pi - V, g)
    re = quad(lambda V: np.cos((l + sig) * V + (g - 1) * (V - np.pi)) * w(V), 0, 2 * np.pi, limit=400,
              epsabs=0, epsrel=1e-12, points=[np.pi])[0]
    im = quad(lambda V: np.sin((l + sig) * V + (g - 1) * (V - np.pi)) * w(V), 0, 2 * np.pi, limit=400,
              epsabs=0, epsrel=1e-12, points=[np.pi])[0]
    return 2 * np.pi / gamma(g) ** (2 * r) * (re + 1j * im)


if __name__ == '__main__':
    import warnings
    warnings.simplefilter('ignore')
    for sig, g in ((0.3, 0.8), (0.15, 0.6), (0.6, 1.3)):
        for l in (0, 1, 3):
            a = lhs(l, sig, g)
            b = rhs(l, sig, g)
            ph = (np.angle(a) / np.pi - (l + sig)) % 1.0
            print('sigma=%.2f g=%.2f l=%d  direct I_l=%s  eq:Il=%s  rel.dev=%.1e  [arg(I_l)/pi-(l+sigma)] mod 1=%.2e'
                  % (sig, g, l, np.round(a, 10), np.round(b, 10), abs(a - b) / abs(a), min(ph, 1 - ph)), flush=True)
    print("\nendpoint behaviour of |a(V) a'(2pi-V)| = P(V) P(2pi-V), r=2:")
    for g in (0.8, 0.4):
        rg = r * g
        print(' g=%.2f, rg=%.2f: claimed O(V^%.2f); expected V^min(rg-1,2rg-2) = V^%.2f' % (
            g, rg, 2 * rg - 2, min(rg - 1, 2 * rg - 2)))
        for V in (1e-2, 1e-3, 1e-4, 1e-5):
            prod = P(V, g) * P(2 * np.pi - V, g)
            print('   V=%.0e  prod/V^(2rg-2)=%.6g   prod/V^(rg-1)=%.6g' % (V, prod / V ** (2 * rg - 2), prod / V ** (rg - 1)))
