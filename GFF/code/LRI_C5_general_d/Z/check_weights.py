#!/usr/bin/env python3
"""Check the explicit polygamma weights of the jet series (Z_general_d.tex, Prop. 'series form') term by term
against numerical differentiation in b:
  T_ln(b)   = (sigma)_{l+n} (1-g)_n / ((2q)_{l+n} n!):   d/db log T = m1,  d/db m1 = m2
  tau_l(s;b)= N_b g_l(s;b) at fixed s:                    d/db log tau = w1, d/db w1 = w2
and, at b = d/2, m1, m2 = mu_1, mu_2 of the note (gs:etaTheta), w1, w2 = gs:w12 continued to i nu = s."""
import mpmath as mp
mp.mp.dps = 30
psi, psi1 = mp.digamma, lambda x: mp.psi(1, x)


def T(l, n, d, b):
    q, s = mp.mpf(d) / 4, b / 2
    g = 2 * q - s
    return mp.rf(s, l + n) * mp.rf(1 - g, n) / (mp.rf(2 * q, l + n) * mp.factorial(n))


def m12(l, n, d, b):
    q, s = mp.mpf(d) / 4, b / 2
    g = 2 * q - s
    m1 = (psi(s + l + n) - psi(s) + psi(1 - g + n) - psi(1 - g)) / 2
    m2 = (psi1(s + l + n) - psi1(s) + psi1(1 - g + n) - psi1(1 - g)) / 4
    return m1, m2


def tau(l, sv, d, b):
    q, sg = mp.mpf(d) / 4, b / 2
    g = 2 * q - sg
    a = (l + sg) / 2
    be = a + g
    Nb = mp.gamma(2 * q) * mp.gamma(g) / mp.gamma(sg)
    return Nb * mp.gamma(a + sv) * mp.gamma(a - sv) / (mp.gamma(be + sv) * mp.gamma(be - sv))


def w12(l, sv, d, b):
    q, sg = mp.mpf(d) / 4, b / 2
    g = 2 * q - sg
    a = (l + sg) / 2
    be = a + g
    w1 = -(psi(g) + psi(sg)) / 2 + (psi(a + sv) + psi(a - sv) + psi(be + sv) + psi(be - sv)) / 4
    w2 = (psi1(g) - psi1(sg)) / 4 + (psi1(a + sv) + psi1(a - sv) - psi1(be + sv) - psi1(be - sv)) / 16
    return w1, w2


worst = 0
for d, b in [(1.5, mp.mpf('0.75')), (2.5, mp.mpf('1.2')), (3, mp.mpf('1.5')), (0.8, mp.mpf('0.4'))]:
    for l, n in [(0, 0), (0, 3), (2, 1), (5, 4)]:
        f = lambda bb: mp.log(T(l, n, d, bb))
        m1, m2 = m12(l, n, d, b)
        e = max(abs(mp.diff(f, b) - m1), abs(mp.diff(f, b, 2) - m2))
        worst = max(worst, e)
    for l, n in [(0, 0), (0, -1), (1, 2), (3, -2), (4, -5)]:
        sv = n + mp.mpf(l + 1) / 2
        f = lambda bb: mp.log(tau(l, sv, d, bb))
        w1, w2 = w12(l, sv, d, b)
        e = max(abs(mp.diff(f, b) - w1), abs(mp.diff(f, b, 2) - w2))
        worst = max(worst, e)
print('max |numerical d/db - formula| over test terms:', mp.nstr(worst, 3))
# b = d/2: compare with the note's mu_1, mu_2 and gs:w12 (continued to i nu = s)
d = mp.mpf('1.5'); q = d / 4; b = d / 2
l, n = 2, 3
m1, m2 = m12(l, n, d, b)
a_ln = l + n + q
mu1 = (psi(a_ln) - psi(q) + psi(n + 1 - q) - psi(1 - q)) / 2
mu2 = (psi1(a_ln) - psi1(q) + psi1(n + 1 - q) - psi1(1 - q)) / 4
print('m1-mu1, m2-mu2 at b=d/2:', mp.nstr(m1 - mu1, 3), mp.nstr(m2 - mu2, 3))
sv = mp.mpf(-1) + mp.mpf(l + 1) / 2
al, bl = mp.mpf(l) / 2 + q / 2, mp.mpf(l) / 2 + 3 * q / 2
nu = -1j * sv
W1 = -psi(q) + mp.re(psi(al + 1j * nu) + psi(bl + 1j * nu)) / 2 if False else \
    -psi(q) + ((psi(al + 1j * nu) + psi(bl + 1j * nu)) + (psi(al - 1j * nu) + psi(bl - 1j * nu))) / 4
W2 = ((psi1(al + 1j * nu) - psi1(bl + 1j * nu)) + (psi1(al - 1j * nu) - psi1(bl - 1j * nu))) / 16
w1, w2 = w12(l, sv, d, b)
print('w1-gs:w12, w2-gs:w12 at b=d/2 (Re{.} continued as the even part in nu):', mp.nstr(abs(w1 - W1), 3), mp.nstr(abs(w2 - W2), 3))
