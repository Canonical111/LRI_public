#!/usr/bin/env python3
"""A8 exploration: C5 extrapolation with the top log fixed by the exponentiated lower-order tail.

Hypothesis (H): the Λ^{-1/2} tail of the gap expansion is Λ^{-1/2} exp(-w1 ε log Λ) S(ε, Λ) with no log Λ at the top
power of S, w1 = 7/2 (weight of the joint thermal model, analyze_joint.py).  At order ε^n the top term is
c_{n} Λ^{-1/2} log^{n-2} Λ and (H) gives
    c_{n} = -(w1/(n-2)) c_{n-1}      (n = 3, 4, 5).
Step 1 (tests of H; the exact limits C2, C3, C4 are known): fixed-intercept fits of the pinned C4P L2000 result,
    C2(Λ) - C2 = Σ c_jk Λ^{-j/2} log^k Λ  (top column (1,0)), C3(Λ) - C3 (top (1,1)), C4Dconn(Λ) - C4 (top (1,2)),
even Λ in [lo, 2000]; C2 and C3 have no window correction (the Dconn window starts at ε⁴).
Step 2: c13 = -(w1/3) c12^(C4).
Step 3: free-intercept fits of C5Dconn(Λ) - c13 Λ^{-1/2} log³ Λ (C5 L500 result, even Λ in [lo, 500]), at c13 and at
c13 ± dc13 for the sensitivity dA/dc13.  The known five-loop C5 is printed only next to the final table.
Least squares as fits_c5_1d.py (mpmath, column scaling, QR), at 50 digits; the condition number is taken from R.

usage: python3 fits/constrained_c5.py --c4npz <C4P c4_1d_L2000.npz> --c5npz <c5_1d_L500.npz> --out <json> [--procs N]"""
import argparse
import json
import math
import os
import sys
from multiprocessing import Pool

import mpmath as mp
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fits_c5_1d as F  # noqa: E402

DPS = 50
W1 = mp.mpf(7) / 2

LOW_BASES = {   # fixed-intercept tail bases per order (first column = top term)
    2: {"a": [(1, 0), (2, 0), (3, 0), (4, 0)],
        "b": [(1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (4, 0)],
        "c": [(1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (4, 0), (4, 1), (5, 0)]},
    3: {"a": [(1, 1), (1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (4, 0)],
        "b": [(1, 1), (1, 0), (2, 0), (2, 1), (2, 2), (3, 0), (3, 1), (4, 0)],
        "c": [(1, 1), (1, 0), (2, 0), (2, 1), (2, 2), (3, 0), (3, 1), (3, 2), (4, 0), (4, 1)]},
    4: {"a": [(1, 2), (1, 1), (1, 0), (2, 0), (2, 1), (2, 2), (3, 0), (3, 1), (4, 0)],
        "b": [(1, 2), (1, 1), (1, 0), (2, 0), (2, 1), (2, 2), (2, 3), (3, 0), (3, 1), (4, 0)],
        "c": [(1, 2), (1, 1), (1, 0), (2, 0), (2, 1), (2, 2), (2, 3), (3, 0), (3, 1), (3, 2), (4, 0), (4, 1)]},
}
LOW_LOS = (100, 200, 300, 400, 600)
C5_BASES = {    # free intercept + these columns; (1,3) is fixed by c13
    "K1": [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2), (3, 0), (3, 1), (4, 0)],
    "K2": [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2), (2, 3), (3, 0), (3, 1), (4, 0)],
    "K3": [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2), (2, 3), (3, 0), (3, 1), (3, 2), (4, 0)],
}
C5_LOS = (80, 120, 160, 200)
COND_MAX = 1e12   # step 1: fits used for the top coefficients (above, the lo-to-lo drift exceeds the spread)
COND_MAX5 = 1e14  # step 3: fits used for the quoted A


def lsq(rows, b):
    mp.mp.dps = DPS
    A = mp.matrix(rows)
    m, n = A.rows, A.cols
    s = [mp.sqrt(mp.fsum(A[i, j] ** 2 for i in range(m))) for j in range(n)]
    for i in range(m):
        for j in range(n):
            A[i, j] /= s[j]
    Q, R = mp.qr(A)
    x = mp.lu_solve(R[:n, :n], (Q.T * b)[:n])
    sv = mp.svd_r(R[:n, :n], compute_uv=False)
    coef = [x[j] / s[j] for j in range(n)]
    res = max(abs(mp.fsum(A[i, j] * x[j] for j in range(n)) - b[i]) for i in range(m))
    return coef, float(max(sv) / min(sv)), float(res)


def col(x, j, k):
    return mp.power(x, -mp.mpf(j) / 2) * mp.log(x) ** k


def job_low(t):
    order, bname, lo, Ls, ys, lim = t
    mp.mp.dps = DPS
    cols = LOW_BASES[order][bname]
    rows = [[col(mp.mpf(int(x)), j, k) for j, k in cols] for x in Ls]
    b = mp.matrix([mp.mpf(float(v)) - mp.mpf(lim) for v in ys])
    coef, cond, res = lsq(rows, b)
    return dict(order=order, basis=bname, lo=lo, n=len(Ls), top=mp.nstr(coef[0], 20), cond=cond, maxres=res,
                coef={f"{j},{k}": mp.nstr(c, 20) for (j, k), c in zip(cols, coef)})


def job_c5(t):
    bname, lo, Ls, ys, c13 = t
    mp.mp.dps = DPS
    cols = C5_BASES[bname]
    rows = [[mp.mpf(1)] + [col(mp.mpf(int(x)), j, k) for j, k in cols] for x in Ls]
    c13 = mp.mpf(c13)
    b = mp.matrix([mp.mpf(float(v)) - c13 * col(mp.mpf(int(x)), 1, 3) for x, v in zip(Ls, ys)])
    coef, cond, res = lsq(rows, b)
    return dict(basis=bname, lo=lo, n=len(Ls), c13=mp.nstr(c13, 20), A=mp.nstr(coef[0], 20), cond=cond, maxres=res,
                coef={f"{j},{k}": mp.nstr(c, 20) for (j, k), c in zip(cols, coef[1:])})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--c4npz", required=True)
    ap.add_argument("--c5npz", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--procs", type=int, default=os.cpu_count())
    a = ap.parse_args()
    if os.path.exists(a.out):
        raise SystemExit(f"{a.out} exists (records are never replaced)")
    if F.sha256_file(a.c4npz) != F.C4P_SHA256:
        raise SystemExit(f"{a.c4npz} is not the pinned C4P result {F.C4P_SHA256[:12]}")
    L5, y5, prov5 = F.load(a.c5npz, "Dconn")
    F.gate_check(a.c5npz, prov5)
    d4 = np.load(a.c4npz)
    L4 = d4["even_L"].astype(int)
    lim2, lim3, lim4 = F.known_limits()
    series = {2: (d4["C2"][4 * L4], lim2), 3: (d4["C3"][4 * L4], lim3), 4: (d4["even_C4Dconn"], lim4)}
    print(f"# constrained C5 fit: C4P {a.c4npz} (sha256 {F.C4P_SHA256[:16]}..), C5 {a.c5npz} "
          f"(sha256 {F.sha256_file(a.c5npz)[:16]}..); w1 = 7/2; limits C2 {lim2!r} C3 {lim3!r} C4 {lim4!r}", flush=True)

    tasks = []
    for order, (y, lim) in series.items():
        for bname in LOW_BASES[order]:
            for lo in LOW_LOS:
                m = L4 >= lo
                tasks.append((order, bname, lo, L4[m].tolist(), y[m].tolist(), repr(lim)))
    with Pool(a.procs) as pool:
        low = pool.map(job_low, tasks)
    print("\n# step 1: fixed-intercept top coefficients (Λ^{-1/2} log^{n-2} Λ), even Λ in [lo, 2000]")
    tops = {}
    for r in low:
        tops.setdefault(r["order"], []).append(r)
        print(f"C{r['order']} basis {r['basis']} lo={r['lo']:4d} n={r['n']:4d} cond={r['cond']:.1e} "
              f"maxres={r['maxres']:.1e} top={float(r['top']):+.8f}", flush=True)

    def summary(order):
        """Median, min, max of the top coefficient over the well-conditioned fits (cond <= COND_MAX)."""
        v = np.array([float(r["top"]) for r in tops[order] if r["cond"] <= COND_MAX])
        return float(np.median(v)), float(v.min()), float(v.max()), int(len(v))

    s2, s3, s4 = summary(2), summary(3), summary(4)
    print(f"\n# test of H over the fits with cond <= {COND_MAX:.0e}: c3 = -w1 c2, c4 = -(w1/2) c3 (median [min, max], count)")
    print(f"c2 = {s2[0]:+.8f} [{s2[1]:+.8f}, {s2[2]:+.8f}] ({s2[3]})")
    print(f"c3 = {s3[0]:+.8f} [{s3[1]:+.8f}, {s3[2]:+.8f}] ({s3[3]})   -w1 c2 = {-3.5 * s2[0]:+.8f}   "
          f"ratio {s3[0] / (-3.5 * s2[0]):.6f}")
    print(f"c4 = {s4[0]:+.8f} [{s4[1]:+.8f}, {s4[2]:+.8f}] ({s4[3]})   -(w1/2) c3 = {-1.75 * s3[0]:+.8f}   "
          f"ratio {s4[0] / (-1.75 * s3[0]):.6f}")
    c13_data = -(3.5 / 3) * s4[0]                      # H at order 5 only, c4 from the C4 data
    c13_chain = -(3.5 ** 3 / 6) * s2[0]                # H at orders 3, 4, 5 from c2
    c13 = c13_data
    dc13 = max((3.5 / 3) * (s4[2] - s4[1]) / 2, abs(c13_data - c13_chain))
    print(f"\n# step 2: c13 = -(w1/3) c4 = {c13_data:+.6f};  chain -(w1^3/6) c2 = {c13_chain:+.6f};  "
          f"dc13 = {dc13:.6f} (max of the c4 half-range and the data-chain difference)")

    tasks = []
    for bname in C5_BASES:
        for lo in C5_LOS:
            m = L5 >= lo
            for c in (c13 - dc13, c13, c13 + dc13):
                tasks.append((bname, lo, L5[m].tolist(), y5[m].tolist(), repr(c)))
    with Pool(a.procs) as pool:
        c5 = pool.map(job_c5, tasks)
    print("\n# step 3: free-intercept fits of C5Dconn(Λ) - c13 Λ^{-1/2} log³ Λ, even Λ in [lo, 500]")
    table = []
    for i in range(0, len(c5), 3):
        lo_, mid, hi_ = c5[i], c5[i + 1], c5[i + 2]
        A0 = float(mid["A"])
        dA = (float(hi_["A"]) - float(lo_["A"])) / (2 * dc13)
        table.append(dict(basis=mid["basis"], lo=mid["lo"], A=A0, dA_dc13=dA, cond=mid["cond"], maxres=mid["maxres"]))
        print(f"{mid['basis']} lo={mid['lo']:4d} n={mid['n']:4d} cond={mid['cond']:.1e} maxres={mid['maxres']:.1e}  "
              f"A = {A0:.6f}  (A at c13 -/+ dc13: {float(lo_['A']):.6f} / {float(hi_['A']):.6f})", flush=True)
    As = np.array([t["A"] for t in table if t["cond"] <= COND_MAX5])
    dAs = max(abs(t["dA_dc13"]) for t in table if t["cond"] <= COND_MAX5) * dc13
    print(f"\n# A over the fits with cond <= {COND_MAX5:.0e} ({len(As)}): median {np.median(As):.6f}, "
          f"range [{As.min():.6f}, {As.max():.6f}], half-range {(As.max() - As.min()) / 2:.4f}; "
          f"c13 uncertainty adds <= {dAs:.4f}")
    print(f"# known five-loop C5 = {F.C5_EXACT} (comparison only)")
    rec = dict(c4npz=os.path.abspath(a.c4npz), c4npz_sha256=F.C4P_SHA256, c5npz=os.path.abspath(a.c5npz),
               c5npz_sha256=F.sha256_file(a.c5npz), w1="7/2", dps=DPS, low=low, c2=s2, c3=s3, c4=s4, c13=c13,
               dc13=dc13, c13_chain=c13_chain, cond_max=COND_MAX, cond_max5=COND_MAX5, c5_fits=c5,
               table=table)
    with open(a.out, "x") as fh:
        json.dump(rec, fh, indent=1)
    print(f"# record {a.out}")


if __name__ == "__main__":
    main()
