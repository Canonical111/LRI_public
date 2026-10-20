#!/usr/bin/env python3
"""Quick independent evaluation of gs:Kspectral (direct spin sum + nu quadrature), for sanity checks only."""
import mpmath as mp, sys
mp.mp.dps = 20
d = mp.mpf(sys.argv[1]); Lmax = int(sys.argv[2])
q = d / 4
A = mp.digamma(2*q) + mp.digamma(1) - 2*mp.digamma(q); U = mp.polygamma(2, q); cs = mp.digamma(1) + mp.digamma(2*q)
def mult(l):
    if l == 0: return mp.mpf(1)
    return (2*l + d - 2) * mp.gamma(l + d - 2) / (mp.gamma(d - 1) * mp.factorial(l))
def spin(l):
    a = mp.mpf(l)/2 + q/2; b = a + q
    def f(nu):
        za, zb = a + 1j*nu, b + 1j*nu
        t = mp.gamma(2*q) * abs(mp.exp(mp.loggamma(za) - mp.loggamma(zb)))**2
        pa, pb = mp.digamma(za), mp.digamma(zb)
        p1a, p1b = mp.polygamma(1, za), mp.polygamma(1, zb)
        p = mp.re(pa + pb); hh = mp.im(pa - pb); j = mp.re(p1a - p1b); k = mp.im(p1a + p1b)
        r = mp.re(mp.polygamma(2, za) + mp.polygamma(2, zb))
        E2 = -hh**2/2 - 5*j/8
        return t**2 * ((cs - p)*E2 - hh*k/2 - 5*r/32)
    sc = max(l, 1)
    return mp.quad(f, [0, 0.5*sc, 2*sc, 8*sc, 40*sc, mp.inf]) / mp.pi
S = mp.mpf(0); partial = {}
for l in range(Lmax + 1):
    S += mult(l) * spin(l)
    if l in (Lmax//4, Lmax//2, Lmax):
        partial[l] = S
        print(l, mp.nstr(-A*U/4 + S/4, 15), flush=True)
