#!/usr/bin/env python3
"""Large-L asymptotics of the exact C_2(L) and C_3(L) (exact_C2_C3.csv from exact_low_orders.py).

C_2: closed form (REPORT.md Sec. 2) evaluated with mpmath to L = 10^5; limit and 1/L^k tail coefficients.
C_3: exact float64 values to L = 600; limit and tail coefficients under several tail bases.
Also the exact raw-minus-consistent shift Delta C_4(L) (window term at eps^2) and its asymptotics.
Writes asymptotics_C2_C3.txt.
"""
import csv
import os

import numpy as np
from mpmath import mp, mpf, rf, factorial, log, pi, nsum, inf

import reference

HERE = os.path.dirname(os.path.abspath(__file__))
REF = reference.load()
mp.dps = 40
out_lines = []


def say(s=""):
    print(s)
    out_lines.append(s)


def w_aa(a):
    return (rf(mpf(1) / 2, a) / factorial(a)) ** 2


def c2_summand(a):
    return w_aa(a) * (mpf(2) / (2 * a - 1) + mpf(18) / (2 * a) + mpf(18) / (2 * a + 1) + mpf(2) / (2 * a + 2))


def dc4_summand(a, L):
    D = -mpf(2 * a) * (2 * L + 6 - 2 * a) / 864  # eps^2 window shift E_v(L) - E_v(L - 2a), E_v(l) = -(l+2)(l+4)/864
    B = mpf(2) / (2 * a - 1) ** 2 + mpf(18) / (2 * a) ** 2 + mpf(18) / (2 * a + 1) ** 2 + mpf(2) / (2 * a + 2) ** 2
    return -w_aa(a) * D * B / 81


def lsq(X, y):
    s = np.linalg.norm(X, axis=0)
    coef, *_ = np.linalg.lstsq(X / s, y, rcond=None)
    coef = coef / s
    return coef, float(np.max(np.abs(y - X @ coef)))


def main():
    # ------------------------------------------------------------------ C_2
    say("== C_2(L) = (1/81)[17 + sum_{a=1}^{L/2} w_aa (2/(2a-1) + 18/(2a) + 18/(2a+1) + 2/(2a+2))], w_aa = ((1/2)_a/a!)^2")
    c2inf = (17 + nsum(c2_summand, [1, inf])) / 81
    say(f"   C_2(inf) = {mp.nstr(c2inf, 35)}")
    say(f"   4 log2/9 = {mp.nstr(4 * log(2) / 9, 35)}   difference {mp.nstr(c2inf - 4 * log(2) / 9, 3)}")
    # tail coefficients from exact values at large L (mpmath partial sums)
    Ls = [2000, 4000, 8000, 16000, 32000]
    part = {}
    acc = mpf(17)
    a = 1
    for L in Ls:
        while a <= L // 2:
            acc += c2_summand(a)
            a += 1
        part[L] = acc / 81
    T = np.array([float((part[L] - c2inf) * L) for L in Ls])
    X = np.column_stack([np.ones(len(Ls)), [1.0 / L for L in Ls], [1.0 / L ** 2 for L in Ls]])
    coef, mr = lsq(X, T)
    say(f"   tail: C_2(L) - C_2(inf) = {coef[0]:.10f}/L + {coef[1]:.6f}/L^2 + ...   (-40/(81 pi) = {-40 / (81 * np.pi):.10f})")

    # ------------------------------------------------------------------ Delta C_4 (raw vs consistent)
    say("\n== Delta C_4(L) = C_4^cons - C_4^raw (exact, eps^2 window shift on single (a,a) states)")
    kappa = 2 * nsum(lambda a: w_aa(a) * 2 * a * (mpf(2) / (2 * a - 1) ** 2 + mpf(18) / (2 * a) ** 2
                                                   + mpf(18) / (2 * a + 1) ** 2 + mpf(2) / (2 * a + 2) ** 2),
                     [1, inf]) / (81 * 864)
    say(f"   slope kappa = lim Delta C_4/L = {mp.nstr(kappa, 15)}")
    lam = 40 / (81 * 864 * pi)
    say(f"   log coefficient -40/(81*864*pi) = {mp.nstr(-lam, 10)} (Delta C_4 = kappa L - {mp.nstr(lam, 6)} log L + const + o(1))")
    for L in (30, 100, 1000, 10000):
        v = sum(dc4_summand(a, L) for a in range(1, L // 2 + 1))
        say(f"   L={L:6d}: Delta C_4 = {mp.nstr(v, 12)}   kappa L - lam log L = {mp.nstr(kappa * L - lam * log(L), 12)}")

    # ------------------------------------------------------------------ C_3
    rows = list(csv.DictReader(open(os.path.join(HERE, "exact_C2_C3.csv"))))
    L = np.array([int(r["L"]) for r in rows], float)
    C3 = np.array([float(r["C3"]) for r in rows])
    l = np.log(L)
    say(f"\n== C_3(L) exact to L = {int(L.max())}: C_3(600) = {C3[-1]:.12f}, continuum {REF[3][0]:.12f}")
    bases = {
        "1, l/L, 1/L, l/L2, 1/L2": lambda: [np.ones_like(L), l / L, 1 / L, l / L ** 2, 1 / L ** 2],
        "+ l2/L2": lambda: [np.ones_like(L), l / L, 1 / L, l / L ** 2, 1 / L ** 2, l ** 2 / L ** 2],
        "+ 1/L3": lambda: [np.ones_like(L), l / L, 1 / L, l / L ** 2, 1 / L ** 2, 1 / L ** 3],
        "+ l2/L (test for log^2)": lambda: [np.ones_like(L), l / L, 1 / L, l / L ** 2, 1 / L ** 2, l ** 2 / L],
        "+ l2/L2 + l/L3 + 1/L3": lambda: [np.ones_like(L), l / L, 1 / L, l / L ** 2, 1 / L ** 2, l ** 2 / L ** 2,
                                          l / L ** 3, 1 / L ** 3],
    }
    A2 = -40 / (81 * np.pi)
    for name, cols in bases.items():
        for Lmin in (32, 64, 128):
            m = L >= Lmin
            X = np.column_stack([c[m] for c in cols()])
            coef, mr = lsq(X, C3[m])
            extra = f"  l2/L coef {coef[5]:+.2e}" if "log^2" in name else ""
            say(f"   [{name:26s}] L>={Lmin:3d}: C3inf {coef[0]:.10f} miss {coef[0] - REF[3][0]:+.1e}  "
                f"l/L {coef[1]:.5f} (omega1_eff = {-coef[1] / A2:.4f})  1/L {coef[2]:+.4f}  maxres {mr:.0e}{extra}")
    with open(os.path.join(HERE, "asymptotics_C2_C3.txt"), "w") as fh:
        fh.write("\n".join(out_lines) + "\n")


if __name__ == "__main__":
    main()
