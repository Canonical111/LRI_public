#!/usr/bin/env python3
"""Check (session L) the simplified closed forms of the coefficients printed in L_general_d.tex against the
sympy coefficients of sym_L.py, at several d.  At b = d/2:  x = q/2, y = 3q/2, S = sin(pi q), C = cos(pi q),
  P4 = a_x hx + B0 (s0 + 2 rho0^4 h1) + Bh (s1 + 2 rhoh^4 hh)
  a_x  = -4 pi^3 C/S^3,                        a_x' = 2 pi^4 (1 + 2C^2)/S^4
  B0   = Gamma(2q)^4 G0^8 sin(3 pi q/2)/(16 pi cos^3(pi q/2)),   G0 = Gamma(q/2)/Gamma(3q/2)
  Bh   = Gamma(2q)^4 Gh^8 cos(3 pi q/2)/(16 pi sin^3(pi q/2)),   Gh = Gamma((1+q)/2)/Gamma((1+3q)/2)
  rho0 = (2-3q)/(3(2-q)),  rhoh = (1-3q)/(1-q)
  L    = a_x' hx + a_x hx' + B0 [Lam0 S0 + S0'] + Bh [Lamh Sh + Sh'],
  S0 = s0 + 2 rho0^4 h1,  S0' = s0' + 2 rho0^4 (h1' + 4 mu0 h1),  Sh likewise with rhoh, muh,
  Lam0 = -4 psi(q) + 2 psi(q/2) + 2 psi(3q/2) + pi cot(pi q/2) - (3 pi/2) cot(pi q) - pi S/(1+2C),
  Lamh = -4 psi(q) + 2 psi((1+q)/2) + 2 psi((1+3q)/2) - pi tan(pi q/2) - (3 pi/2) cot(pi q) + pi S/(1-2C),
  mu0  = (1/2)[4/(3q) + 1/(2-3q) + 1/(2-q)],   muh = (1/2)[1/(1-3q) + 1/(1-q)].
"""
import sys
import os
import mpmath as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sym_L import coeffs_at  # noqa: E402
from L_general import coeffs_closed  # noqa: E402  (the module's implementation of the printed forms)

mp.mp.dps = 40


def closed_final(d):
    """the regularized forms printed in Theorem (eq:Lfinal): B0 = (1+2C) beta0, Bh = (2C-1) betah,
    (1+2C) Lam0 = (1+2C) Lt0 - pi S, (2C-1) Lamh = (2C-1) Lth - pi S, nu = rho^4 mu (finite)."""
    q = mp.mpf(d) / 4
    pi = mp.pi
    S, C = mp.sin(pi * q), mp.cos(pi * q)
    G0 = mp.gamma(q / 2) / mp.gamma(3 * q / 2)
    Gh = mp.gamma((1 + q) / 2) / mp.gamma((1 + 3 * q) / 2)
    beta0 = mp.gamma(2 * q) ** 4 * G0 ** 8 * mp.tan(pi * q / 2) / (16 * pi * mp.cos(pi * q / 2) ** 2)
    betah = mp.gamma(2 * q) ** 4 * Gh ** 8 * mp.cot(pi * q / 2) / (16 * pi * mp.sin(pi * q / 2) ** 2)
    Lt0 = (-4 * mp.psi(0, q) + 2 * mp.psi(0, q / 2) + 2 * mp.psi(0, 3 * q / 2) + pi * mp.cot(pi * q / 2)
           - 3 * pi / 2 * mp.cot(pi * q))
    Lth = (-4 * mp.psi(0, q) + 2 * mp.psi(0, (1 + q) / 2) + 2 * mp.psi(0, (1 + 3 * q) / 2) - pi * mp.tan(pi * q / 2)
           - 3 * pi / 2 * mp.cot(pi * q))
    r0 = (2 - 3 * q) / (3 * (2 - q))
    rh = (1 - 3 * q) / (1 - q)
    nu0 = r0 ** 4 * (4 / (3 * q) + 1 / (2 - q)) / 2 + r0 ** 3 / (6 * (2 - q))
    nuh = rh ** 3 * (1 - 2 * q) / (1 - q) ** 2
    ax = -4 * pi ** 3 * C / S ** 3
    axp = 2 * pi ** 4 * (1 + 2 * C ** 2) / S ** 4
    e0, eh = 1 + 2 * C, 2 * C - 1
    return dict(hx=(ax, axp),
                s0=(e0 * beta0, beta0 * (e0 * Lt0 - pi * S)),
                h1=(2 * r0 ** 4 * e0 * beta0, beta0 * (2 * r0 ** 4 * (e0 * Lt0 - pi * S) + 8 * e0 * nu0)),
                s1=(eh * betah, betah * (eh * Lth - pi * S)),
                hh=(2 * rh ** 4 * eh * betah, betah * (2 * rh ** 4 * (eh * Lth - pi * S) + 8 * eh * nuh)))


def closed(d):
    q = mp.mpf(d) / 4
    pi = mp.pi
    S, C = mp.sin(pi * q), mp.cos(pi * q)
    G0 = mp.gamma(q / 2) / mp.gamma(3 * q / 2)
    Gh = mp.gamma((1 + q) / 2) / mp.gamma((1 + 3 * q) / 2)
    ax = -4 * pi ** 3 * C / S ** 3
    axp = 2 * pi ** 4 * (1 + 2 * C ** 2) / S ** 4
    B0 = mp.gamma(2 * q) ** 4 * G0 ** 8 * mp.sin(3 * pi * q / 2) / (16 * pi * mp.cos(pi * q / 2) ** 3)
    Bh = mp.gamma(2 * q) ** 4 * Gh ** 8 * mp.cos(3 * pi * q / 2) / (16 * pi * mp.sin(pi * q / 2) ** 3)
    r0 = (2 - 3 * q) / (3 * (2 - q))
    rh = (1 - 3 * q) / (1 - q)
    L0 = (-4 * mp.psi(0, q) + 2 * mp.psi(0, q / 2) + 2 * mp.psi(0, 3 * q / 2) + pi * mp.cot(pi * q / 2)
          - 3 * pi / 2 * mp.cot(pi * q) - pi * S / (1 + 2 * C))
    Lh = (-4 * mp.psi(0, q) + 2 * mp.psi(0, (1 + q) / 2) + 2 * mp.psi(0, (1 + 3 * q) / 2) - pi * mp.tan(pi * q / 2)
          - 3 * pi / 2 * mp.cot(pi * q) + pi * S / (1 - 2 * C))
    m0 = (4 / (3 * q) + 1 / (2 - 3 * q) + 1 / (2 - q)) / 2
    mh = (1 / (1 - 3 * q) + 1 / (1 - q)) / 2
    # map to the per-function coefficients of sym_L (a_i, a_i')
    return dict(hx=(ax, axp), s0=(B0, B0 * L0), h1=(2 * r0 ** 4 * B0, 2 * r0 ** 4 * B0 * (L0 + 4 * m0)),
                s1=(Bh, Bh * Lh), hh=(2 * rh ** 4 * Bh, 2 * rh ** 4 * Bh * (Lh + 4 * mh)))


if __name__ == '__main__':
    worst = 0
    for d in ('0.7', '1', '1.25', '4/3', '1.5', '2', '2.5', '8/3', '2.9', '3', '3.6'):
        cf = coeffs_at(mp.mpf(d), 40)
        cl = closed_final(d)
        cm = coeffs_closed(mp.mpmathify(d))
        for k in cl:
            for i in (0, 1):
                assert abs(cl[k][i] - cm[k][i]) <= mp.mpf(10) ** -35 * max(1, abs(cl[k][i])), (d, k, i)
        devs = []
        for k in ('hx', 'h1', 'hh', 's0', 's1'):
            for i in (0, 1):
                a, b = cf[k][i], cl[k][i]
                dev = abs(a - b) / max(abs(a), mp.mpf(10) ** -25)
                devs.append(dev)
        worst = max(worst, max(devs))
        print('d=%-4s max rel dev closed vs sympy: %s' % (d, mp.nstr(max(devs), 3)))
    print('worst', mp.nstr(worst, 3))
