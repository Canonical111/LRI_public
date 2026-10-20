#!/usr/bin/env python3
"""eps^4 shift of C_4 from the FULL zero-mode window (including zero-mode-number-changing parts), 3D model,
cancellation-free, for large L.  Port of the 2D residual_log/offdiag_window.py (same zero-mode algebra; 3D
l = 0 bundle densities from windows3d.bundle_l0; den = x0 (delta + m) + N, x0 = 3/4, slice levels N = 2 sigma).

Nested insertion of the window part of the ket-referenced second-order zero-mode effective interaction
    D_l(z -> z') = g1^2 sum_{k: l - N < level(k) <= l} <z'|V|k><k|V|z> / (E_z - E_k)
into every outer state of chi level N:
    <p| V R D R V |p> = sum c_m c_m' A(p; path) sum_N rho_m(N)/(den_O(N, d1) den_O(N, d3)) [s(L) - s(L - N)],
    s = cumulative inner sum of -rho_m'(n)/den_B(n, dB).
'diag' (z' = z) must reproduce Delta_cons + Delta_zm of windows3d.py; 'off' is the new piece.
usage: python3 offdiag3d.py --Lmax 4000 --out results/offdiag_L4000.npz"""
import argparse
import os
from fractions import Fraction as Fr
from math import comb, factorial

import numpy as np

import c4lib3d as lib
from c4_compute3d import window_sum
from windows3d import bundle_l0

G1 = Fr(1, 3)
PIW = (Fr(1, 3), Fr(-1), Fr(1), Fr(-1, 3))
X0 = 0.75


def cm(m):
    return Fr(comb(4, m), 12) ** 2 * factorial(m)


def path_table():
    tab = {}
    for m in range(1, 5):
        for m2 in range(1, 5):
            zl = [4 - m, 4 - m2, 4 - m2, 4 - m]
            for p in range(4):
                for rs, amp in lib.zero_mode_paths(p, zl):
                    r1, r2, r3 = rs
                    key = (m, r1 - p, r3 - p, m2, r2 - r1)
                    tab[key] = tab.get(key, Fr(0)) + PIW[p] * G1 ** 4 * cm(m) * cm(m2) * amp
    return {k: v for k, v in tab.items() if v != 0}


def offdiag(Lmax):
    S = Lmax // 2
    rho = bundle_l0(Lmax)
    R = {m: rho[m][0: 2 * S + 1: 2] for m in range(1, 5)}
    lev = 2.0 * np.arange(S + 1)
    den = lambda m, d: X0 * (d + m) + lev
    tab = path_table()
    out = {"L": 2 * np.arange(S + 1)}
    names = ["full", "diag", "off"] + [f"off_m{m}_m{m2}" for m in range(1, 5) for m2 in range(1, 5)] \
        + [f"diag_m{m}_m{m2}" for m in range(1, 5) for m2 in range(1, 5)]
    for nm in names:
        out[nm] = np.zeros(S + 1)
    for dB in range(-8, 9, 1):
        out[f"off_dB{dB:+d}"] = np.zeros(S + 1)
    cache_h, cache_s = {}, {}
    for (m, d1, d3, m2, dB), coef in sorted(tab.items()):
        kh = (m, d1, d3)
        if kh not in cache_h:
            mask = lev >= m
            h = np.zeros(S + 1)
            h[mask] = R[m][mask] / (den(m, d1)[mask] * den(m, d3)[mask])
            cache_h[kh] = h
        ks = (m2, dB)
        if ks not in cache_s:
            mask = lev >= m2
            s = np.zeros(S + 1)
            s[mask] = -R[m2][mask] / den(m2, dB)[mask]
            cache_s[ks] = s
        W = window_sum(cache_h[kh], cache_s[ks])
        v = float(coef) * W
        out["full"] += v
        Delta = d3 - d1
        if Delta == 0:
            out["diag"] += v
            out[f"diag_m{m}_m{m2}"] += v
        else:
            out["off"] += v
            out[f"off_m{m}_m{m2}"] += v
            out[f"off_dB{Delta:+d}"] += v
    out["n_keys"] = np.array(len(tab))
    return out, tab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, default=400)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r, tab = offdiag(a.Lmax)
    print(f"{len(tab)} Pi-surviving (m, d1, d3, m', dB) keys")
    for L in (2, 4, 10, 20, 50, 100, 200, 400, 1000, 2000, 4000, 8000):
        if L <= a.Lmax:
            i = L // 2
            print(f"L={L:6d} full={r['full'][i]:+.12f} diag={r['diag'][i]:+.12f} off={r['off'][i]:+.12f} "
                  + " ".join(f"{k[4:]}={r[k][i]:+.6f}" for k in sorted(r) if k.startswith("off_m")
                             and abs(r[k][i]) > 1e-12), flush=True)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        np.savez(a.out, **r)


if __name__ == "__main__":
    main()
