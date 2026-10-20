#!/usr/bin/env python3
"""N0: the exact identities of PROOF.md Section 1-2, at random complex parameters.

 (1.3)  f_l(a_l+n+t) = Gamma(2q)^2 Phi_t(l+n) Psi_t(n)                       (all l >= 0, n in Z)
 (2.1)  Psi_t(n)     = T_R(t) Phi_{t+1-2q}(n)                                (n >= 0)
 (2.2)  Phi_t(-1-p)  = T_L(t) PhiL_t(p)                                      (p >= 0)
 (2.3)  middle and left factors written with z = j+1-t, p+1-t, l+p+1-t
 (5.2)  D_R(t) = -(1/64) e^{-i pi (2q+tau)} w^{-3} (1-w)^2 (1-e^{2 pi i q} w)^3 (1-e^{2 pi i (tau-q)} w),  w = e^{2 pi i t}
"""
import random
import mpmath as mp

mp.mp.dps = 40
random.seed(7)
G, rG, sin, pi = mp.gamma, mp.rgamma, mp.sin, mp.pi


def rnd(a, b):
    return mp.mpf(a) + (mp.mpf(b) - mp.mpf(a)) * mp.mpf(random.random())


worst = {}
for trial in range(40):
    q = rnd(0.05, 0.95)
    tau = mp.mpc(rnd(-0.4, 1.5), rnd(-0.5, 0.5))
    t = mp.mpc(rnd(-1, 2), rnd(-2, 2))
    Phi = lambda m, tt: G(m + q + tt) ** 3 * rG(m + 2 * q + tt) ** 2 * rG(m + q + tau + tt)
    Psi = lambda n: G(-n - t) ** 2 * G(q - tau - n - t) * rG(q - n - t) ** 3
    TR = sin(pi * (q - t)) ** 3 / (sin(pi * t) ** 2 * sin(pi * (q - tau - t)))
    TL = sin(pi * (2 * q - 1 + t)) ** 2 * sin(pi * (q + tau - 1 + t)) / sin(pi * (q - 1 + t)) ** 3
    PhiL = lambda p: G(p + 2 - 2 * q - t) ** 2 * G(p + 2 - q - tau - t) * rG(p + 2 - q - t) ** 3

    def f(l, s):
        a = (l + q) / 2
        b = a + q
        return G(2 * q) ** 2 * G(a + s) ** 3 * G(a - s) ** 2 * G(b - tau - s) * rG(b + s) ** 2 * rG(b - s) ** 3 * rG(a + tau + s)

    for l in (0, 1, 3, 7):
        for n in (-9, -4, -1, 0, 2, 5):
            a = (l + q) / 2
            lhs = f(l, a + n + t)
            rhs = G(2 * q) ** 2 * Phi(l + n, t) * Psi(n)
            worst['(1.3)'] = max(worst.get('(1.3)', 0), abs(lhs - rhs) / abs(lhs))
    for n in range(0, 8):
        lhs = Psi(n)
        rhs = TR * Phi(n, t + 1 - 2 * q)
        worst['(2.1)'] = max(worst.get('(2.1)', 0), abs(lhs - rhs) / abs(lhs))
    for p in range(0, 8):
        lhs = Phi(-1 - p, t)
        rhs = TL * PhiL(p)
        worst['(2.2)'] = max(worst.get('(2.2)', 0), abs(lhs - rhs) / abs(lhs))
    for j in range(0, 6):
        z = j + 1 - t
        lhs = Psi(-j - 1)
        rhs = G(z) ** 2 * G(z + q - tau) * rG(z + q) ** 3
        worst['(2.3) middle'] = max(worst.get('(2.3) middle', 0), abs(lhs - rhs) / abs(lhs))
    w = mp.expj(2 * pi * t)
    DR = sin(pi * t) ** 2 * sin(pi * (t + q)) ** 3 * sin(pi * (t - q + tau))
    pred = -mp.mpf(1) / 64 * mp.expj(-pi * (2 * q + tau)) * w ** (-3) * (1 - w) ** 2 * (1 - mp.expj(2 * pi * q) * w) ** 3 \
        * (1 - mp.expj(2 * pi * (tau - q)) * w)
    worst['(5.2)'] = max(worst.get('(5.2)', 0), abs(DR - pred) / abs(DR))
for k, v in worst.items():
    print('identity %-12s max relative deviation over 40 random (q, tau, t): %s' % (k, mp.nstr(v, 3)))
