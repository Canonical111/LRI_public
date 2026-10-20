#!/usr/bin/env python3
"""Exact eps^4 shift of C_4 from the FULL (zero-mode-number-changing) window, cancellation-free, for large L.

Mechanism (README Sec. 2).  For a two-component fourth-order process (outer bubble O = vertices O1, O2 with m chi
lines; inner bubble B = vertices B1, B2 with m' chi lines; the components share only the zero mode), the six time
orderings plus the RS unlinked terms cancel in the continuum (linked-cluster theorem; H0 is additive, so this
holds with zero-mode shifts as well, including Delta_B = -Delta_O != 0).  The level cutoff removes the region
a, b <= M < a + b from the four orderings in which both components are present in one slice, so the raw error
is exactly
    - sum_{window} [ 1/(e_O e_B (e_O + d)) + 1/(e_O e_B (e_B - d)) ]  x (zero-mode amplitude),   d = Delta_B / 2,
i.e. a NESTED insertion of the window part of the second-order zero-mode effective Hamiltonian
    D_l(z -> z') = g1^2 sum_{k : l - N < level(k) <= l} <z'|V|k><k|V|z> / (E_z - E_k)     (ket-referenced, Bloch)
into every outer state of level N.  The 'zeromode' scheme of ../zeromode_exact keeps only z' = z.  This script
evaluates the full D (all z' - z), its diagonal part (must reproduce ../c4_exact Dcorr exactly), and the
off-diagonal remainder, as double sums over the outer (m, delta1, delta3) and inner (m', dB) structures:
    <p| V R D R V |p> = sum c_m c_m' A(p; path) sum_a R_m(a)/(den_O(a,d1) den_O(a,d3)) [s(M) - s(M - a)],
    s = cumulative inner sum of -R_m'(b)/den_B(b, dB).
Pi (C = F(2) - F(1) - (F(3) - F(0))/3) is applied to the exact rational path amplitudes before any float sum.
usage: python3 offdiag_window.py --Lmax 20000 --out results/offdiag_L20000.npz"""
import argparse
import os
from fractions import Fraction as Fr
from math import comb, factorial

import numpy as np

import c4lib as lib

G1 = Fr(1, 3)
PIW = (Fr(1, 3), Fr(-1), Fr(1), Fr(-1, 3))      # C = sum_p PIW[p] F(p)


def cm(m):
    """vertex coefficients (C(4,m)/12)^2 times the Wick count m! of an m-line bundle."""
    return Fr(comb(4, m), 12) ** 2 * factorial(m)


def path_table():
    """Exact Pi-projected coefficients, key (m, d1, d3, m2, dB) -> Fraction, for the nested chain
    O1 (zlegs 4-m) B1 (4-m2) B2 (4-m2) O2 (4-m) on the closed zero-mode path p -> r1 -> r2 -> r3 -> p."""
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


def level_series(N, ser):
    R = {m: lib.two_vertex_density(m, 0, 0, ser) for m in range(1, 5)}
    sig = np.arange(N + 1)

    def den(m, d):
        x = (d + m) / 2.0 + 2.0 * sig
        return x

    return R, den, sig


def offdiag(Lmax):
    N = Lmax // 2
    ser = lib.Series(N, kmax=4)
    R, den, sig = level_series(N, ser)
    tab = path_table()
    out = {"L": 2 * np.arange(N + 1)}
    names = ["full", "diag", "off"] + [f"off_m{m}_m{m2}" for m in range(1, 5) for m2 in range(1, 5)] \
        + [f"diag_m{m}_m{m2}" for m in range(1, 5) for m2 in range(1, 5)]
    for nm in names:
        out[nm] = np.zeros(N + 1)
    for dB in range(-8, 9, 2):
        out[f"off_dB{dB:+d}"] = np.zeros(N + 1)
    cache_h, cache_s = {}, {}
    for (m, d1, d3, m2, dB), coef in sorted(tab.items()):
        kh = (m, d1, d3)
        if kh not in cache_h:
            mask = 2 * sig >= m
            h = np.zeros(N + 1)
            h[mask] = R[m][mask] / (den(m, d1)[mask] * den(m, d3)[mask])
            cache_h[kh] = h
        ks = (m2, dB)
        if ks not in cache_s:
            mask = 2 * sig >= m2
            s = np.zeros(N + 1)
            s[mask] = -R[m2][mask] / den(m2, dB)[mask]
            cache_s[ks] = s
        W = lib.window_sum(cache_h[kh], cache_s[ks])
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
    ap.add_argument("--Lmax", type=int, default=2000)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r, tab = offdiag(a.Lmax)
    print(f"{len(tab)} Pi-surviving (m, d1, d3, m', dB) keys")
    for L in (2, 4, 10, 18, 30, 100, 1000, 2000, 4000, 10000, 20000, 40000):
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
