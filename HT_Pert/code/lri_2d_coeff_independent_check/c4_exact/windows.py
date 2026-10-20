#!/usr/bin/env python3
"""Exact window shifts of C_4 for very large L (two-vertex sums only), cancellation-free:
    Delta_cons(L) = C4_cons - C4_raw = Pi[ g1^2 <V R D_cons R V> ],   D_cons(N) = g1^2 [e_0(L) - e_0(L-N)]
    Delta_zm(L)   = C4_corr - C4_cons = Pi[ g1^2 <V R (D_corr - D_cons) R V> ],
    D_corr(z, N) = g1^2 [e_z(L) - e_z(L-N)],   e_z(l) = <z|V R V|z>_l,   Pi f = f(2) - f(1) - (f(3) - f(0))/3.
Both sides are written as sums over the chi number m and zero-mode shift delta of the outer state and m', delta'
of the inner bubble:  <p|V R D R V|p> = sum c_m Q_{m,delta}(p) c_m' [Q_{m',delta'}(z) - ...] W(L), with the exact
zero-mode polynomials Q_{m,delta}(z) = |<z+delta| :Z^{4-m}: |z>|^2 and single-signed level sums
    W_{m delta; m' delta'}(L) = sum_sigma h_{m,delta}(sigma) [s_{m',delta'}(L) - s_{m',delta'}(L - 2 sigma)].
Pi acts on the p-dependence only, so it is applied in exact rational arithmetic BEFORE multiplying by W: the large
p-polynomial pieces of degree <= 2 (vacuum and mass divergences, ~L^2) never enter the floating-point sum.
usage: python3 windows.py --Lmax 20000 --out results/windows_L20000.npz"""
import argparse
from fractions import Fraction as Fr
from math import comb, factorial

import numpy as np

import c4lib as lib

G1 = Fr(1, 3)
PIW = (Fr(1, 3), Fr(-1), Fr(1), Fr(-1, 3))      # C = sum_p PIW[p] F(p)


def ff(x, n):
    r = 1
    for i in range(n):
        r *= (x - i)
    return r


def Q(m, d, z):
    """|<z+d| :Z^k: |z>|^2, k = 4 - m (exact integer; 0 outside the allowed range)."""
    k = 4 - m
    if (d + k) % 2 or abs(d) > k or z < 0 or z + d < 0:
        return 0
    j = (d + k) // 2
    return comb(k, j) ** 2 * ff(z, k - j) * ff(z + d, j)


def cm(m):
    return Fr(comb(4, m), 12) ** 2 * factorial(m)


def level_sums(N, ser):
    """h[(m,d)](sigma) = R_m(sigma)/den^2 (outer, R^2 = +1/den^2) and ds[(m,d)](sigma) = R_m(sigma)*(-1/den)
    (inner bubble increments), den = (d + m)/2 + 2 sigma; m = 1..4."""
    h, ds = {}, {}
    for m in range(1, 5):
        Rm = lib.two_vertex_density(m, 0, 0, ser)
        for d in range(-(4 - m), 4 - m + 1, 2):
            g1 = lib.slice_G((d + m) / 2.0, 1, m, N + 1)
            g2 = lib.slice_G((d + m) / 2.0, 2, m, N + 1)
            h[(m, d)] = Rm * g2
            ds[(m, d)] = -Rm * g1
    return h, ds


def windows(Lmax, decompose=True):
    N = Lmax // 2
    ser = lib.Series(N, kmax=4)
    h, ds = level_sums(N, ser)
    keys = sorted(h)
    res = {"L": 2 * np.arange(N + 1), "Delta_cons": np.zeros(N + 1), "Delta_zm": np.zeros(N + 1)}
    for m in range(1, 5):
        res[f"Delta_zm_m{m}"] = np.zeros(N + 1)
    for (m, d) in keys:
        for (m2, d2) in keys:
            pz = sum(PIW[p] * Q(m, d, p) * (Q(m2, d2, p + d) - Q(m2, d2, 0)) for p in range(4))
            pc = sum(PIW[p] * Q(m, d, p) * Q(m2, d2, 0) for p in range(4))
            if pz == 0 and pc == 0:
                continue
            W = lib.window_sum(h[(m, d)], ds[(m2, d2)])
            pref = G1 ** 4 * cm(m) * cm(m2)
            if pz:
                v = float(pref * pz) * W
                res["Delta_zm"] += v
                res[f"Delta_zm_m{m}"] += v
            if pc:
                res["Delta_cons"] += float(pref * pc) * W
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, default=4000)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r = windows(a.Lmax)
    for L in (30, 100, 1000, 1600, 4000, 10000, 20000, 40000, 100000):
        if L <= a.Lmax:
            i = L // 2
            print(f"L={L:6d} Delta_cons={r['Delta_cons'][i]:+.12f} Delta_zm={r['Delta_zm'][i]:+.12f} "
                  + " ".join(f"m{m}={r[f'Delta_zm_m{m}'][i]:+.10f}" for m in range(1, 5)), flush=True)
    if a.out:
        np.savez(a.out, **r)


if __name__ == "__main__":
    main()
