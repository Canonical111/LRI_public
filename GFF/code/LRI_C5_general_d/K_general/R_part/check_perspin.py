#!/usr/bin/env python3
"""Per-spin check of the R-family finite-mode identity at generic q.

f_l(s) = Gamma(2q)^2 g_l(s)^2 R_tau(s)
       = Gamma(2q)^2 G(a+s)^3 G(a-s)^2 G(b-tau-s) / [G(b+s)^2 G(b-s)^3 G(a+tau+s)],   a=(l+q)/2, b=a+q.
Xi_l(t) = D_R(t) sum_{n in Z} f_l(a+n+t),  D_R(t) = sin^2(pi t) sin^3(pi(t+q)) sin(pi(t-q+tau)).
Claims: Xi_l is a trigonometric polynomial with modes |k|<=2, and
        I_l := int ds/(2 pi i) f_l(s) (imaginary axis) = sum_k rho_k c_k,
        rho_k = -Res_{t=0}[e^{2 pi i k t}/D_R] - Res_{t=q-tau}[e^{2 pi i k t}/D_R].
"""
import sys
import mpmath as mp
from emsum import emsum

mp.mp.dps = 30


def setup(d, tau):
    q = mp.mpf(d) / 4
    return q, mp.mpf(tau)


def f(l, s, q, tau):
    a = (l + q) / 2
    b = a + q
    G, rG = mp.gamma, mp.rgamma
    return (G(2 * q) ** 2 * G(a + s) ** 3 * G(a - s) ** 2 * G(b - tau - s)
            * rG(b + s) ** 2 * rG(b - s) ** 3 * rG(a + tau + s))


def DR(t, q, tau):
    return mp.sin(mp.pi * t) ** 2 * mp.sin(mp.pi * (t + q)) ** 3 * mp.sin(mp.pi * (t - q + tau))


def Xi_l(l, t, q, tau):
    """smooth three-piece form of the per-spin bilateral sum (right n>=0, middle -l<=n<=-1, left n<=-l-1)"""
    G, rG, pi, sin = mp.gamma, mp.rgamma, mp.pi, mp.sin
    Phi = lambda m: G(m + q + t) ** 3 * rG(m + 2 * q + t) ** 2 * rG(m + q + tau + t)
    Psi = lambda n: G(-n - t) ** 2 * G(q - tau - n - t) * rG(q - n - t) ** 3
    TR = sin(pi * (q - t)) ** 3 / (sin(pi * t) ** 2 * sin(pi * (q - tau - t)))
    TL = sin(pi * (2 * q - 1 + t)) ** 2 * sin(pi * (q + tau - 1 + t)) / sin(pi * (q - 1 + t)) ** 3
    Psip = lambda n: G(n + 1 - q + t) ** 3 * rG(n + 1 + t) ** 2 * rG(n + 1 - q + tau + t)
    Phip = lambda p: G(p + 2 - 2 * q - t) ** 2 * G(p + 2 - q - tau - t) * rG(p + 2 - q - t) ** 3
    right = TR * emsum(lambda n: Phi(l + n) * Psip(n), 0, 30)
    mid = mp.fsum(Phi(l + n) * Psi(n) for n in range(-l, 0))
    left = TL * emsum(lambda p: Phip(p) * Psi(-l - 1 - p), 0, 30)
    return DR(t, q, tau) * G(2 * q) ** 2 * (right + mid + left)


def rho(k, q, tau):
    pi = mp.pi
    r0 = (2j * pi * k - pi * (3 * mp.cot(pi * q) + mp.cot(pi * (tau - q)))) / (pi ** 2 * mp.sin(pi * q) ** 3 * mp.sin(pi * (tau - q)))
    r1 = mp.expj(2 * pi * k * (q - tau)) / (pi * mp.sin(pi * (q - tau)) ** 2 * mp.sin(pi * (2 * q - tau)) ** 3)
    return -r0 - r1


def I_l(l, q, tau):
    g = lambda nu: mp.re(f(l, 1j * nu, q, tau))
    return mp.quad(g, [0, 1, 4, 16, 64, mp.inf]) / mp.pi


def modes_from_samples(vals, ts):
    # solve for c_{-2..2} from 5 samples
    M = mp.matrix([[mp.expj(2 * mp.pi * k * t) for k in range(-2, 3)] for t in ts])
    c = mp.lu_solve(M, mp.matrix(vals))
    return {k: c[k + 2] for k in range(-2, 3)}


if __name__ == '__main__':
    d = sys.argv[1] if len(sys.argv) > 1 else '1.5'
    tau = sys.argv[2] if len(sys.argv) > 2 else '0.3'
    q, tau = setup(d, tau)
    print('d', d, 'q', q, 'tau', tau)
    ts = [mp.mpf('0.0731') + mp.mpf(j) / 5 + 0.05j for j in range(5)]
    tchk = [mp.mpf('0.31') + 0.11j, mp.mpf('-0.42') - 0.07j]
    for l in [0, 1, 2, 5]:
        vals = [Xi_l(l, t, q, tau) for t in ts]
        c = modes_from_samples(vals, ts)
        for t in tchk:
            pred = sum(c[k] * mp.expj(2 * mp.pi * k * t) for k in c)
            print('  l', l, 't', mp.nstr(t, 4), 'mode-check rel err', mp.nstr(abs(pred - Xi_l(l, t, q, tau)) / abs(pred), 3))
        lhs = sum(rho(k, q, tau) * c[k] for k in c)
        rhs = I_l(l, q, tau)
        print('  l', l, 'rho.c =', mp.nstr(lhs, 20), '  I_l =', mp.nstr(rhs, 20), ' diff', mp.nstr(abs(lhs - rhs), 3))
