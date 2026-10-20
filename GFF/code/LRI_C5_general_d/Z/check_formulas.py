#!/usr/bin/env python3
"""Numerical check of the displayed formulas of Z_general_d.tex with the 90-digit jets (results/zj90.json):
eq:first, eq:firstzm, eq:simplified, eq:simplifiedQ, the d=1 and d=3 specializations, and the R' reduction."""
import json
import os
import sys
import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_blocks as cb  # noqa: E402

mp.mp.dps = 100
res = json.load(open(os.path.join(HERE, 'results', 'zj90.json')))['results']
G = mp.catalan
worst = {}


def note(key, val):
    worst[key] = max(worst.get(key, mp.mpf(0)), abs(val))


for d, r in res.items():
    dm = cb.zb_parse(d)
    q = dm / 4
    s, c, pi = mp.sin(pi_q := mp.pi * q), mp.cos(pi_q), mp.pi
    R = [mp.re(mp.mpmathify(x)) for x in r['R']]
    M = [mp.re(mp.mpmathify(x)) for x in r['Mh']]
    Z = mp.re(mp.mpmathify(r['Z']))
    Q = mp.re(mp.mpmathify(r['W'])) / 3
    c0 = cb.c0hat_jets(d, R, M)
    # eq:first
    lhs = 8 * pi ** 3 * s ** 2 * (1 + 2 * c) * R[1] + 2 * s * c * (1 + c) ** 2 * M[1]
    rhs = 8 * pi ** 4 * s * (1 + c + c ** 2) * R[0] + pi * (1 + c) ** 2 * (1 + 2 * c) * M[0]
    note('eq:first (rel)', (lhs - rhs) / abs(rhs))
    # eq:firstzm
    lhs = 3 * pi ** 3 * s ** 2 * R[1] + 2 * s * c0[1]
    rhs = 3 * pi * c * (pi ** 3 * s * R[0] + c0[0])
    note('eq:firstzm (rel)', (lhs - rhs) / max(abs(rhs), abs(3 * pi ** 3 * s ** 2 * R[1])))
    # R' reduction
    Rp = pi * c / s * R[0] + c / (pi ** 2 * s ** 2) * c0[0] - 2 / (3 * pi ** 3 * s) * c0[1]
    note("R' reduction (rel)", (Rp - R[1]) / R[1])
    # eq:simplified and eq:simplifiedQ
    Zs = (2 * pi ** 2 / (3 * s ** 2) * R[2] - pi ** 4 * mp.cos(pi * dm / 2) / (3 * s ** 4) * R[0]
          + (3 * pi / s ** 3 * c0[0] - 4 * c / s ** 4 * c0[1] + 4 / (pi * s ** 3) * c0[2]) / 9)
    note('eq:simplified (rel)', (Zs - Z) / Z)
    ZQ = (2 * pi ** 2 / (3 * s ** 2) * R[2] - pi ** 2 * mp.cos(pi * dm / 2) / (6 * s ** 2) * Q
          + (pi * (1 + c ** 2) / s ** 5 * c0[0] - 4 * c / s ** 4 * c0[1] + 4 / (pi * s ** 3) * c0[2]) / 9)
    note('eq:simplifiedQ (rel)', (ZQ - Z) / Z)
    # 3Q = 6 pi^2 R/s^2 + 4 c0/(pi s^3)
    note('3Q zero-mode form (rel)', (6 * pi ** 2 * R[0] / s ** 2 + 4 * c0[0] / (pi * s ** 3) - 3 * Q) / Q)
    if d == '1':
        note('d=1: R(1/2) - Gamma(1/4)^4/(4pi^3)', R[0] - mp.gamma(0.25) ** 4 / (4 * pi ** 3))
        note('d=1: Z - (4pi^2/3) R\'\'', Z - 4 * pi ** 2 / 3 * R[2])
        lg2 = mp.mpf(5) / 2 * mp.psi(1, 0.25) - mp.psi(1, 0.75) / 2 - pi ** 2
        note('d=1: (5/2)psi1(1/4)-(1/2)psi1(3/4)-pi^2 - (pi^2+24G)', lg2 - (pi ** 2 + 24 * G))
        Mrel = 8 * pi ** 3 * s ** 3 * R[0] / (c * (1 + c) ** 3)
        note('d=1: Mh - 8pi^3 s^3 R/(c(1+c)^3) (rel)', (M[0] - Mrel) / M[0])
    if d == '3':
        c0x = -mp.gamma(0.25) ** 10 / (2 ** (mp.mpf(15) / 2) * pi ** (mp.mpf(5) / 2))
        note('d=3: c0hat(3/2) - closed (rel)', (c0[0] - c0x) / c0x)
        Z3 = 4 * pi ** 2 / 3 * R[2] + mp.sqrt(2) * (4 * pi + 32 * G / pi) * c0x
        note('d=3: Z - [(4pi^2/3)R\'\' + sqrt2(4pi+32G/pi)c0] (rel)', (Z3 - Z) / Z)
        Z3b = 4 * pi ** 2 / 3 * R[2] - (4 * G + pi ** 2 / 2) * mp.gamma(0.25) ** 10 / (16 * pi ** (mp.mpf(7) / 2))
        note('d=3: Z - C63d formula (rel)', (Z3b - Z) / Z)
        note("d=3: R'(3/2) - [-pi R + Gamma(1/4)^10/(64 pi^(9/2))] (rel)",
             (R[1] - (-pi * R[0] + mp.gamma(0.25) ** 10 / (64 * pi ** (mp.mpf(9) / 2)))) / R[1])
for k, v in worst.items():
    print('%-70s %s' % (k, mp.nstr(v, 3)))
