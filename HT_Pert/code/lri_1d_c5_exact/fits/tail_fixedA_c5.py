#!/usr/bin/env python3
"""A8 exploration (not blind): tail of the exact C5Dconn(L) with the intercept fixed to the five-loop C5.

For each basis of fits_c5_1d.BASES (log option 'none') and each lo, fits
    C5Dconn(L) - A = sum_{(j,k)} c_jk L^{-j/2} log^k L,   even L in [lo, hi],
first with A = C5 (the known five-loop value) to measure the tail coefficients, then with A = C5 + delta for the
deltas of --scan to profile the max residual against the intercept (the data noise floor is ~1e-11, so the range of
delta with residuals at the floor is the intercept resolution of that basis and window).  Same mpmath least squares
as fits_c5_1d.py (60 digits, column scaling).

usage: python3 fits/tail_fixedA_c5.py --npz results/<sha12>/c5_1d_L400.npz --lo 80,120,160 --bases L2,M3,M3x"""
import argparse
import os
import sys

import mpmath as mp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fits_c5_1d as F  # noqa: E402

mp.mp.dps = 60


def fit_fixed(L, y, lo, hi, cols, A0):
    sel = [(int(a), float(b)) for a, b in zip(L, y) if lo <= a <= hi]
    Ls = [a for a, _ in sel]
    b = mp.matrix([mp.mpf(v) - A0 for _, v in sel])
    A = mp.matrix([[mp.power(x, -mp.mpf(j) / 2) * mp.log(x) ** k for j, k in cols] for x in Ls])
    coef, cond, rank = F.lstsq(A, b)
    res = A * mp.matrix(coef) - b
    return coef, float(cond), rank, float(max(abs(r) for r in res)), len(Ls)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True)
    ap.add_argument("--hi", type=int, default=None)
    ap.add_argument("--lo", default="80,120,160")
    ap.add_argument("--bases", default="L2,M3,M3x")
    ap.add_argument("--scan", default="-3,-1,-0.3,-0.1,-0.03,0.03,0.1,0.3,1,3")
    a = ap.parse_args()
    L, y, prov = F.load(a.npz, "Dconn")
    F.gate_check(a.npz, prov)
    hi = a.hi or int(L[-1])
    C5 = mp.mpf(F.C5_EXACT)
    print(f"# EXPLORATION (not blind): {a.npz} (sha256 {F.sha256_file(a.npz)[:16]}..) scheme Dconn, even L in [lo, {hi}],"
          f" A fixed to C5 = {F.C5_EXACT} (+ delta)")
    for name in a.bases.split(","):
        cols = F.BASES[name]
        for lo in [int(v) for v in a.lo.split(",")]:
            coef, cond, rank, mres, n = fit_fixed(L, y, lo, hi, cols, C5)
            lab = " ".join(f"c{j}{k}={mp.nstr(c, 10)}" for (j, k), c in zip(cols, coef) if j == 1)
            print(f"{name:4s} lo={lo:4d} n={n:4d} rank={rank:2d} cond={cond:.1e} maxres={mres:.1e}  {lab}", flush=True)
            print(f"     all: " + " ".join(f"({j},{k})={mp.nstr(c, 12)}" for (j, k), c in zip(cols, coef)), flush=True)
            prof = []
            for d in a.scan.split(","):
                prof.append(f"{d}:{fit_fixed(L, y, lo, hi, cols, C5 + mp.mpf(d))[3]:.1e}")
            print(f"     maxres(delta): " + " ".join(prof), flush=True)


if __name__ == "__main__":
    main()
