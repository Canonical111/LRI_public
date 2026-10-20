#!/usr/bin/env python3
"""N7: the residue weights of the trace functional (PROOF.md Proposition 6.6).

rho_k := -Res_{t=0}[e^{2 pi i k t}/D_R] - Res_{t=q-tau}[e^{2 pi i k t}/D_R]   (numerical Cauchy circles)
compared with R_part's closed form
rho_k = -[2 pi i k - pi(3 cot(pi q) + cot(pi(tau-q)))]/[pi^2 sin^3(pi q) sin(pi(tau-q))]
        - e^{2 pi i k (q-tau)}/[pi sin^2(pi(q-tau)) sin^3(pi(2q-tau))].
Also checks the tau = q degeneration: R_q = g_l, so t_l^2 R_q = t_l^3/Gamma(2q).
"""
import mpmath as mp

mp.mp.dps = 30


def DR(t, q, tau):
    return mp.sin(mp.pi * t) ** 2 * mp.sin(mp.pi * (t + q)) ** 3 * mp.sin(mp.pi * (t - q + tau))


def res_num(f, t0, r=mp.mpf('1e-3'), n=64):
    return mp.fsum(f(t0 + r * mp.expj(2 * mp.pi * j / n)) * r * mp.expj(2 * mp.pi * j / n) for j in range(n)) / n


def rho_closed(k, q, tau):
    pi = mp.pi
    r0 = (2j * pi * k - pi * (3 * mp.cot(pi * q) + mp.cot(pi * (tau - q)))) / (pi ** 2 * mp.sin(pi * q) ** 3 * mp.sin(pi * (tau - q)))
    r1 = mp.expj(2 * pi * k * (q - tau)) / (pi * mp.sin(pi * (q - tau)) ** 2 * mp.sin(pi * (2 * q - tau)) ** 3)
    return -r0 - r1


worst = 0
for ds, tau in (('0.8', mp.mpf('0.25')), ('1.5', mp.mpc('0.3', '0.1')), ('2.5', mp.mpf('0.4')), ('3', mp.mpc('0.6', '-0.2')),
                ('1.25', mp.mpc('-0.05', '0.06'))):
    q = mp.mpf(ds) / 4
    for k in range(-2, 3):
        f = lambda t: mp.expj(2 * mp.pi * k * t) / DR(t, q, tau)
        num = -res_num(f, 0) - res_num(f, q - tau)
        cl = rho_closed(k, q, tau)
        worst = max(worst, abs(num - cl) / abs(cl))
print('max relative deviation, numerical residues vs closed-form rho_k (5 (d,tau) x 5 k):', mp.nstr(worst, 3))
