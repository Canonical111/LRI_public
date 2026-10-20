#!/usr/bin/env python3
"""Numerical spot check of the structural identities used in PROOF.md (tag topmode).

 (A) R_tau(s) = g_l(s + (tau-q)/2; b' = d - 2 tau)           [the R factor is a balanced wheel factor, rim d-2tau, shifted]
     with g_l(s;b) = G(a+s)G(a-s)/(G(beta+s)G(beta-s)),  a = (l+b/2)/2,  beta = a + (d-b)/2   (foundation eq:kernel)
 (B) Gamma(2q)^2 g_l(s;d/2)^2 R_tau(s) at s = a_l+n+t equals Gamma(2q)^2 F_L(l+q+z) F_R(z), z = n+t,
     F_L(w) = f_q(w)^2 f_tau(w),  F_R(z) = f_q(-z)^2 f_tau(q-tau-z),  f_g(w) = G(w)/G(w+g)
 (C) t_l^2 S_tau (gs:RS) = Gamma(2q)^2 [G(q-tau/2)/G(q+tau/2)]^2 ... is the r=2 wheel at b = d/2 - tau:
     Gamma(2q)^2 g_l(s;d/2)^2 S_tau(s) = Gamma(2q)^2 g_l(s; d/2-tau)^2
"""
import mpmath as mp

mp.mp.dps = 40
G = mp.gamma


def gl(l, s, b, d):
    a = (l + b / 2) / 2
    be = a + (d - b) / 2
    return G(a + s) * G(a - s) / (G(be + s) * G(be - s))


def Rtau(l, s, tau, q):
    a = (l + q) / 2; b = a + q
    return G(a + s) * G(b - tau - s) / (G(a + tau + s) * G(b - s))


def Stau(l, s, tau, q):
    a = (l + q) / 2; b = a + q
    return (G(a - tau / 4 + s) * G(a - tau / 4 - s) * G(b + s) * G(b - s)
            / (G(b + tau / 4 + s) * G(b + tau / 4 - s) * G(a + s) * G(a - s))) ** 2


f = lambda g, w: G(w) / G(w + g)
worst = {'A': 0, 'B': 0, 'C': 0}
for d in (mp.mpf('0.7'), mp.mpf('1.7'), mp.mpf('2.9'), mp.mpf('3.6')):
    q = d / 4
    for tau in (mp.mpc('0.31', '0.17'), mp.mpc('1.13', '-0.4')):
        for l in (0, 1, 4):
            for s in (mp.mpc('0.123', '0.77'), mp.mpc('-0.31', '1.9')):
                lhs = Rtau(l, s, tau, q); rhs = gl(l, s + (tau - q) / 2, d - 2 * tau, d)
                worst['A'] = max(worst['A'], abs(lhs / rhs - 1))
                lhs = Stau(l, s, tau, q) * gl(l, s, d / 2, d) ** 2; rhs = gl(l, s, d / 2 - tau, d) ** 2
                worst['C'] = max(worst['C'], abs(lhs / rhs - 1))
            for n in (-7, -1, 0, 3):
                t = mp.mpc('0.2137', '0.05')
                s = (l + q) / 2 + n + t
                z = n + t
                lhs = gl(l, s, d / 2, d) ** 2 * Rtau(l, s, tau, q)
                rhs = f(q, l + q + z) ** 2 * f(tau, l + q + z) * f(q, -z) ** 2 * f(tau, q - tau - z)
                worst['B'] = max(worst['B'], abs(lhs / rhs - 1))
for k, vv in worst.items():
    print('identity (%s): max relative deviation %s' % (k, mp.nstr(vv, 3)))
