#!/usr/bin/env python3
"""N1: numerical check of the two Stirling inputs of PROOF.md.

(a) DLMF 5.11(ii), K=1:  |R(w)| <= sec^2(ph(w)/2) / (12|w|),
    R(w) = LnGamma(w) - [(w-1/2) Ln w - w + ln(2 pi)/2],   |ph w| < pi  (principal branches).
(b) Lemma 2 (uniform Gamma ratio): for Re z >= 0, |z| >= max(1, 2 rho), |u|,|v| <= rho,
    theta := LnGamma(z+u) - LnGamma(z+v) - (u-v) Ln z   satisfies   |theta| <= kappa(rho)/|z|,
    kappa(rho) = rho + 3 rho^2/2 + 11 rho^3/3 + 4/3.
Random samples (fixed seed); prints the largest observed ratio |error| / bound (must be <= 1).
"""
import random
import mpmath as mp

mp.mp.dps = 30
random.seed(20261003)


def stirling_R(w):
    return mp.loggamma(w) - ((w - mp.mpf(1) / 2) * mp.log(w) - w + mp.log(2 * mp.pi) / 2)


def kappa(rho):
    return rho + mp.mpf(3) / 2 * rho ** 2 + mp.mpf(11) / 3 * rho ** 3 + mp.mpf(4) / 3


def rand_modulus(lo, hi):
    return mp.mpf(lo) * (mp.mpf(hi) / lo) ** random.random()


# (a) remainder bound, sectors up to 0.97 pi
worst_a = (0, None)
for i in range(4000):
    r = rand_modulus(0.05, 1e4)
    ph = (2 * random.random() - 1) * mp.mpf('0.97') * mp.pi
    w = r * mp.expj(ph)
    bound = 1 / (12 * abs(w) * mp.cos(ph / 2) ** 2)
    ratio = abs(stirling_R(w)) / bound
    if ratio > worst_a[0]:
        worst_a = (ratio, (mp.nstr(r, 6), mp.nstr(ph / mp.pi, 6)))
print('(a) max |R(w)| / [sec^2(ph/2)/(12|w|)] over 4000 samples, |ph w| <= 0.97 pi, 0.05 <= |w| <= 1e4:',
      mp.nstr(worst_a[0], 20), ' at (|w|, ph/pi) =', worst_a[1])

# (b) Lemma 2
for rho in (mp.mpf('0.25'), mp.mpf('0.5'), mp.mpf(1), mp.mpf(2), mp.mpf(3)):
    worst = (0, None)
    for i in range(3000):
        R0 = max(1, 2 * rho)
        z = rand_modulus(R0, 1e3 * R0) * mp.expj((2 * random.random() - 1) * mp.pi / 2)
        u = rho * mp.sqrt(random.random()) * mp.expj(2 * mp.pi * random.random())
        v = rho * mp.sqrt(random.random()) * mp.expj(2 * mp.pi * random.random())
        theta = mp.loggamma(z + u) - mp.loggamma(z + v) - (u - v) * mp.log(z)
        ratio = abs(theta) * abs(z) / kappa(rho)
        if ratio > worst[0]:
            worst = (ratio, (mp.nstr(z, 6), mp.nstr(u, 4), mp.nstr(v, 4)))
    print('(b) rho = %-4s  max |theta| |z| / kappa(rho) = %s   (kappa = %s)  worst at z,u,v = %s'
          % (mp.nstr(rho, 3), mp.nstr(worst[0], 6), mp.nstr(kappa(rho), 6), worst[1]))

# (b') the boundary region |z| = max(1, 2 rho) exactly, Re z = 0 (hardest corner)
for rho in (mp.mpf('0.5'), mp.mpf(1), mp.mpf(2), mp.mpf(3)):
    worst = 0
    for i in range(2000):
        R0 = max(1, 2 * rho)
        z = R0 * mp.expj(random.choice([-1, 1]) * mp.pi / 2 * (1 - mp.mpf(random.random()) ** 4 * mp.mpf('0.2')))
        u = rho * mp.expj(2 * mp.pi * random.random())
        v = rho * mp.expj(2 * mp.pi * random.random())
        theta = mp.loggamma(z + u) - mp.loggamma(z + v) - (u - v) * mp.log(z)
        worst = max(worst, abs(theta) * abs(z) / kappa(rho))
    print("(b') rho = %-4s  corner |z| = max(1,2rho), ph z near +-pi/2, |u|=|v|=rho: max ratio = %s"
          % (mp.nstr(rho, 3), mp.nstr(worst, 6)))
