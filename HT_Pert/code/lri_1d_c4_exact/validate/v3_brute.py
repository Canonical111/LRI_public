#!/usr/bin/env python3
"""A3: diagram sums vs an independent brute-force float64 Rayleigh-Schroedinger solver (vendor/brute_rs_cut4.py =
lri_hpc_Hamitonian/reference/check_lri_hamiltonian.py with the cutoff generalised to an integer cut4, RS order 4)
at every quarter cutoff cut4 = 4..cut4max: E_p^(k) (p = 0..3, k = 2, 3, 4), r_k, g_k, C_k (k <= 4).
Gate: relative deviation <= 1e-11, or absolute <= 1e-12 where |value| < 0.1.
usage: python3 validate/v3_brute.py [--cut4max 48]"""
import argparse
import os
import sys
import time

import math

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "vendor"))
import brute_rs_cut4 as brute          # noqa: E402
import c4_compute1d as cc              # noqa: E402



def ndev(v, ref):
    """Normalised deviation: relative where |ref| >= 0.1, absolute/1e-12 scaled to the 1e-11 gate otherwise;
    non-finite values (either side) give inf."""
    if not (math.isfinite(v) and math.isfinite(ref)):
        return math.inf
    return abs(v - ref) / abs(ref) if abs(ref) >= 0.1 else abs(v - ref) / 1e-12 * 1e-11


def worse(a, b):
    return b if not b <= a else a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cut4max", type=int, default=48)
    a = ap.parse_args()
    Lmax = (a.cut4max + 3) // 4
    res = cc.compute(Lmax, verbose=False)
    worst = 0.0
    nchk = 0
    print(f"{'cut4':>4} {'dim':>8} {'worst E_p^(k)':>14} {'worst r,g,C':>12} {'sec':>6}")
    for c in range(4, a.cut4max + 1):
        t0 = time.time()
        sp = brute.FockSpace(c, pmax=15, degree=5)
        psi, E, r, g = brute.initial_wavefunctions(sp, order=4)
        we = 0.0
        for k in (2, 3, 4):
            rk, gk = res[f"r{k}"][c], res[f"g{k}"][c]
            for p in range(4):
                mine = res[f"X{k}"][p][c] + 2 * p * rk + p * (p - 1) / 2 * gk
                we = worse(we, ndev(mine, E[p, k]))
                nchk += 1
        wc = 0.0
        for k in (2, 3, 4):
            for name, ref in (("r", r[k]), ("g", g[k]), ("C", E[2, k] - E[0, k])):
                v = res[f"{name}{k}"][c]
                wc = worse(wc, ndev(v, ref))
                nchk += 1
        worst = worse(worse(worst, we), wc)
        print(f"{c:4d} {sp.dim:8d} {we:14.2e} {wc:12.2e} {time.time() - t0:6.1f}", flush=True)
    print(f"# {nchk} comparisons, worst normalised deviation {worst:.2e} (gate 1e-11): "
          f"{'PASS' if worst <= 1e-11 else 'FAIL'}")
    sys.exit(0 if worst <= 1e-11 and nchk == 21 * (a.cut4max - 3) else 1)


if __name__ == "__main__":
    main()
