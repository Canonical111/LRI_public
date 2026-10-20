#!/usr/bin/env python3
"""The d = 1 closed forms exactly as printed in note Section 1.1 (new check for the public edition, 2026-10-13).

Evaluates, with literal mpmath calls and no stored value: the reflected-quarter polygamma basis at q = 1/4,
Q = Gamma(1/4)^4/pi, F+- = 4F3(1), B+-, P4 = 13 B- - 3 B+, the five values Y_r (four 9F8(-1), Y_2 also as
the 8F7(-1) of eq. P5FixedY2), P5 = 16 pi^(3/2)[-35 X0 + (22 sqrt2 - 13) X+ + (22 sqrt2 + 13) X-],
C2, C3, 648 C4, 46656 C5 of Section 1.1, and the two master reductions K, L of Section 4 (eq. KLpsiReflected),
then the unreduced Section 4 formula (eq. full) with these K and L as a cross-check of the substitution.
Usage: sec11_closed_forms.py OUT.json [--digits 70]. About 1 s on one core.
"""
import argparse
import json
import time
from pathlib import Path

import mpmath as mp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=Path)
    ap.add_argument('--digits', type=int, default=70)
    a = ap.parse_args()
    t0 = time.time()
    mp.mp.dps = a.digits
    q, qb, h = mp.mpf(1) / 4, mp.mpf(3) / 4, mp.mpf(1) / 2
    pA = mp.digamma(2 * q) + mp.digamma(1) - 2 * mp.digamma(q)
    pD = mp.digamma(qb) - mp.digamma(q)
    T, Tb = mp.polygamma(1, q), mp.polygamma(1, qb)
    U, Ub = mp.polygamma(2, q), mp.polygamma(2, qb)
    G4 = mp.gamma(q) ** 4
    Q = G4 / mp.pi
    Fm = mp.hyper([q, q, h, h], [qb, qb, 1], 1)
    Fp = mp.hyper([qb, qb, h, h], [5 * q, 5 * q, 1], 1)
    Bm, Bp = G4 * Fm, 64 * mp.pi ** 4 / G4 * Fp
    P4 = 13 * Bm - 3 * Bp

    def Y(r):
        v = mp.mpf(r) / 8
        a_, b_ = mp.mpf(r + 2) / 8, mp.mpf(r + 6) / 8
        return v * (mp.gamma(a_) / mp.gamma(b_)) ** 7 * mp.hyper([1, 1 + v] + [a_] * 7, [v] + [b_] * 7, -1)

    y = {r: Y(r) for r in (1, 2, 3, 5, 7)}
    y2_8f7 = mp.pi ** mp.mpf(3.5) / 4 * mp.hyper([mp.mpf(5) / 4] + [h] * 7, [q] + [1] * 6, -1)
    c8, s8 = mp.cos(mp.pi / 8), mp.sin(mp.pi / 8)
    X0, Xp, Xm = y[2], c8 ** 7 * y[3] - s8 ** 7 * y[5], c8 ** 7 * y[1] + s8 ** 7 * y[7]
    P5 = 16 * mp.pi ** mp.mpf(1.5) * (-35 * X0 + (22 * mp.sqrt(2) - 13) * Xp + (22 * mp.sqrt(2) + 13) * Xm)
    C2 = pA / 9
    C3 = (pA ** 2 + (T + Tb) / 6 - 8 * Q) / 108
    C4 = (16 * P4 - pA ** 3 - pA / 2 * (T + Tb) - 8 * pA * Q + (365 * U - 6 * Ub) / 14) / 648
    C5 = (-1536 * P5 + 96 * (7 * pA - pD) * P4 + 384 * pD * Bm - 1728 * Q ** 2
          + 16 * Q * (45 * pA ** 2 + 383 * T - 64 * Tb) - 768 * T * (3 * T - Tb)
          - 15 * pA ** 4 - 15 * pA ** 2 * (T + Tb) - 6 * pA / 7 * (431 * U + 18 * Ub)
          - mp.mpf(83) / 4 * (T + Tb) ** 2) / 46656
    K = (T * (3 * T - Tb) + pA * U) / 2
    L = -(3 * pA - pD) / 6 * P4 - 2 * pD / 3 * Bm
    # Section 4, eq. (full): A = pi + 4 log 2, H = 2 pi^2/3 + 8 Catalan
    A, H = mp.pi + 4 * mp.log(2), 2 * mp.pi ** 2 / 3 + 8 * mp.catalan
    C5_full = (-1536 * (P5 + K) + 384 * A * P4 - 576 * L - 1728 * Q ** 2 + 48 * Q * (15 * A ** 2 + 149 * H + 7 * mp.pi ** 2)
               - 15 * A ** 4 - 30 * A ** 2 * mp.pi ** 2 - 828 * A * mp.pi ** 3 - 21456 * A * mp.zeta(3) - 83 * mp.pi ** 4) / 46656
    s = lambda x: mp.nstr(x, a.digits - 5)
    out = dict(working_digits=a.digits, stored_values_used=False,
               C2=s(C2), C3=s(C3), C4=s(C4), C5=s(C5), K=s(K), L=s(L), P4=s(P4), P5=s(P5),
               Y={str(r): s(v) for r, v in y.items()}, Y2_9F8_minus_8F7=s(y[2] - y2_8f7),
               dictionary_residuals=dict(pA_minus_A=s(pA - A), pD_minus_pi=s(pD - mp.pi),
                                         T_minus_Tb_minus_16G=s(T - Tb - 16 * mp.catalan),
                                         U_plus_Ub_plus_112zeta3=s(U + Ub + 112 * mp.zeta(3))),
               C5_sec4_full_minus_sec11=s(C5_full - C5), elapsed_seconds=time.time() - t0)
    a.out.write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
