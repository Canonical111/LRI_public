#!/usr/bin/env python3
"""C2, C3 of the d = 1 frozen-cutoff HT by a rule fixed before fitting (HT1dPert, 2026-10-14).

Data: exact C2(Λ), C3(Λ) of the truncated Hamiltonian at even Λ (lri_1d_c4_exact production result c4_1d_L2000.npz,
sha256 62720cf5...; equal to the HT solver's values to 1e-12 at Λ <= 118).
Rule (fixed before any fit was run):
  windows: even Λ in [lo, hi], lo in {16, 24, 32} for hi in {98, 118}; lo in {100, 200, 400} for hi = 2000
  C2: C2(Λ) = A + Σ_{j=1..J} a_j Λ^{-j/2}, J in {6, 8}
  C3: C3(Λ) = A + Σ c_jk Λ^{-j/2} log^k Λ over the basis L1 = {(1,0),(1,1),(2,0),(2,1),(3,0),(3,1),(4,0)} and
      L1x = L1 + {(4,1),(5,0)}
  estimator: median of the 6 intercepts (2 bases x 3 lo); uncertainty: half the range of the 6.
  Least squares in mpmath at 50 digits with column scaling (as fits_c5_1d.py).
The exact C2 = (π + 4 log 2)/9 and C3 are printed only after the table.
usage: python3 public/c2c3_rule.py --npz ../../data/HT_1d/exact_c4/a8b57b2e8475/c4_1d_L2000.npz [--hi 2000] [--json OUT]"""
import argparse
import math
from multiprocessing import Pool

import mpmath as mp
import numpy as np

C2_EXACT = (math.pi + 4 * math.log(2)) / 9
C3_EXACT = -3.71985632290183342249
C2B = {"P6": [(j, 0) for j in range(1, 7)], "P8": [(j, 0) for j in range(1, 9)]}
L1 = [(1, 0), (1, 1), (2, 0), (2, 1), (3, 0), (3, 1), (4, 0)]
C3B = {"L1": L1, "L1x": L1 + [(4, 1), (5, 0)]}
WIN = {98: (16, 24, 32), 118: (16, 24, 32), 2000: (100, 200, 400)}


def fit(t):
    order, bname, cols, lo, hi, Ls, ys = t
    mp.mp.dps = 50
    sel = [(L, y) for L, y in zip(Ls, ys) if lo <= L <= hi]
    A = mp.matrix([[mp.mpf(1)] + [mp.power(L, -mp.mpf(j) / 2) * mp.log(L) ** k for j, k in cols] for L, _ in sel])
    b = mp.matrix([mp.mpf(y) for _, y in sel])
    m, n = A.rows, A.cols
    s = [mp.sqrt(mp.fsum(A[i, j] ** 2 for i in range(m))) for j in range(n)]
    for i in range(m):
        for j in range(n):
            A[i, j] /= s[j]
    Q, R = mp.qr(A)
    x = mp.lu_solve(R[:n, :n], (Q.T * b)[:n])
    sv = mp.svd_r(R[:n, :n], compute_uv=False)
    return dict(order=order, basis=bname, lo=lo, hi=hi, n=m, A=float(x[0] / s[0]), cond=float(max(sv) / min(sv)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--hi", type=int, default=None, help="only this upper cutoff (98, 118 or 2000); default all")
    ap.add_argument("--json", default=None, help="write the fits and the per-window estimates to this file")
    a = ap.parse_args()
    d = np.load(a.npz)
    L = d["even_L"].astype(int)
    ys = {2: d["C2"][4 * L], 3: d["C3"][4 * L]}
    tasks = []
    for hi, los in WIN.items():
        if a.hi is not None and hi != a.hi:
            continue
        for order, B in ((2, C2B), (3, C3B)):
            for bname, cols in B.items():
                for lo in los:
                    tasks.append((order, bname, cols, lo, hi, L.tolist(), [float(v) for v in ys[order]]))
    with Pool(a.procs) as p:
        res = p.map(fit, tasks)
    for r in res:
        print(f"C{r['order']} {r['basis']:4s} lo={r['lo']:4d} hi={r['hi']:5d} n={r['n']:5d} cond={r['cond']:.1e} A={r['A']:.15f}")
    print()
    summary = []
    for hi in sorted({r["hi"] for r in res}):
        for order in (2, 3):
            v = np.array([r["A"] for r in res if r["order"] == order and r["hi"] == hi])
            med, half = float(np.median(v)), float((v.max() - v.min()) / 2)
            ex = C2_EXACT if order == 2 else C3_EXACT
            summary.append(dict(order=order, hi=hi, median=med, half_range=half, n=int(len(v))))
            print(f"C{order} hi={hi:5d}: median {med:.13f} +- {half:.2e} (half-range of 6)   "
                  f"[exact {ex:.13f}: median - exact = {med - ex:+.2e}, rel {abs(med / ex - 1):.1e}]")
    if a.json:
        import json
        json.dump(dict(fits=res, summary=summary), open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
