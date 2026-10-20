#!/usr/bin/env python3
"""A6d / A6e: overlap of C5 results.

A6d (two C5 results with different Lmax): both files must have the prescribed quarter grid (cut4 = 0..4 Lmax), the
validity mask (valid = cut4 >= 3; r2..r5, g2..g5, C2..C5 finite where valid and NaN elsewhere; X2..X5 of shape
(4, nc) with X_p finite for cut4 >= p and NaN for cut4 < p), the even grid even_L = 2, 4, .., Lmax and finite
even-grid arrays (EVEN below).  Then plain maxima of |Delta| over every common valid cutoff (cut4 = 3..) for r_k, g_k,
C_k (k = 2..5) and over every common even Lambda for the even-grid pieces are printed; gate: max |Delta C5| <= 1e-10
on the quarter grid, and the two fit targets even_C5raw and even_C5Dconn <= 1e-10 on the common even grid.
A6e (--c4ref RESULT): C2, C3, C4 of a C5 result vs the C4P production result (default C4NPZ below, overridable by
--c4npz; its sha256 must equal C4NPZ_SHA256) on the common valid quarter grid: max |Delta| <= 1e-12 absolute
(r2..r4, g2..g4 and the C4P-compatible even arrays even_C4raw, even_C4Dconn, even_shift4 are reported).
Prints the sha256 of both files (recorded in the gate record).
usage: python3 validate/v6_overlap.py results/<sha12>/c5_1d_L160.npz results/<sha12>/c5_1d_L240.npz
       python3 validate/v6_overlap.py --c4ref results/<sha12>/c5_1d_L160.npz [--c4npz PATH]"""
import argparse
import hashlib
import sys

import numpy as np

C4NPZ = "<PROJECT>/lri_1d_c4_exact/results/a8b57b2e8475/c4_1d_L2000.npz"
C4NPZ_SHA256 = "62720cf5ac097f5e7f93250bc38e592c4de269b703abb5dd2544fb53994b51d2"
KS = (2, 3, 4, 5)
TUNED = [f"{n}{k}" for k in KS for n in ("r", "g", "C")]
EVEN = ("even_C5raw", "even_C5Dconn", "even_dC5_Dconn", "even_dC5_g2D", "even_dC5_bubble", "even_dC5_rows4",
        "even_dC5_rows5", "even_T1", "even_T2", "even_T3", "even_T4", "even_A4", "even_B4", "even_B5", "even_dR4",
        "even_dR5", "even_fast_g2D", "even_C4raw", "even_C4Dconn", "even_shift4")
GATE_EVEN = ("even_C5raw", "even_C5Dconn")
TOL_A6D = 1e-10
TOL_A6E = 1e-12


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def grid_problems(d, tuned=TUNED, xs=tuple(f"X{k}" for k in KS), even=EVEN):
    """Grid, mask and finiteness problems of a result file (empty list = fine)."""
    bad = []
    for k in ("cut4", "valid", "even_L") + tuple(tuned) + tuple(xs) + tuple(even):
        if k not in d.files:
            bad.append(f"{k} missing")
    if bad:
        return bad
    nc = len(d["cut4"])
    Lmax = (nc - 1) // 4
    cut4 = np.arange(nc)
    if nc != 4 * Lmax + 1 or not np.array_equal(d["cut4"], cut4):
        bad.append("cut4 != 0..4 Lmax")
    valid = cut4 >= 3
    if not np.array_equal(d["valid"], valid):
        bad.append("valid != (cut4 >= 3)")
    if not np.array_equal(d["even_L"], np.arange(2, Lmax + 1, 2)):
        bad.append("even_L != 2..Lmax")
    for k in tuned:
        v = d[k]
        if v.shape != (nc,) or not np.all(np.isfinite(v[valid])) or not np.all(np.isnan(v[~valid])):
            bad.append(f"{k}: shape, finiteness on valid or NaN mask")
    for k in xs:
        X = d[k]
        if X.shape != (4, nc):
            bad.append(f"{k}: shape {X.shape}")
            continue
        for p in range(4):
            if not np.all(np.isfinite(X[p, cut4 >= p])) or not np.all(np.isnan(X[p, cut4 < p])):
                bad.append(f"{k}[{p}]: finiteness for cut4 >= {p} or NaN mask")
    for k in even:
        if d[k].shape != d["even_L"].shape or not np.all(np.isfinite(d[k])):
            bad.append(f"{k}: shape or non-finite")
    return bad


def report_grid(name, d, **kw):
    bad = grid_problems(d, **kw)
    for b in bad:
        print(f"{name}: {b}")
    return not bad


def overlap(a, b):
    ok = report_grid("A", a) and report_grid("B", b)
    if not ok:
        print("grid/validity/finiteness check FAILED")
        return False
    n = min(len(a["cut4"]), len(b["cut4"]))
    m = min(len(a["even_L"]), len(b["even_L"]))
    if n <= 3 or m < 1:
        print("no common valid cutoffs")
        return False
    for k in KS:
        dv = {nm: float(np.max(np.abs(a[f"{nm}{k}"][3:n] - b[f"{nm}{k}"][3:n]))) for nm in ("r", "g", "C")}
        print(f"k={k}: max |d| r{k} {dv['r']:.2e}  g{k} {dv['g']:.2e}  C{k} {dv['C']:.2e}   (cut4 = 3..{n - 1})")
        if k == 5:
            ok &= dv["C"] <= TOL_A6D
    print(f"even grid L = 2..{a['even_L'][m - 1]} ({m} cutoffs):")
    for k in EVEN:
        dv = float(np.max(np.abs(a[k][:m] - b[k][:m])))
        print(f"  {k:16s} max |d| {dv:.2e}" + ("   (gated)" if k in GATE_EVEN else ""))
        if k in GATE_EVEN:
            ok &= dv <= TOL_A6D
    return bool(ok)


def c4ref(a, c4):
    ok = report_grid("C5 result", a)
    ok &= report_grid("C4P", c4, tuned=[f"{n}{k}" for k in (2, 3, 4) for n in ("r", "g", "C")],
                      xs=("X2", "X3", "X4"), even=("even_C4raw", "even_C4Dconn", "even_shift4"))
    if not ok:
        print("grid/validity/finiteness check FAILED")
        return False
    n = min(len(a["cut4"]), len(c4["cut4"]))
    m = min(len(a["even_L"]), len(c4["even_L"]))
    if n <= 3 or m < 1:
        print("no common valid cutoffs")
        return False
    for k in (2, 3, 4):
        dv = {nm: float(np.max(np.abs(a[f"{nm}{k}"][3:n] - c4[f"{nm}{k}"][3:n]))) for nm in ("r", "g", "C")}
        print(f"k={k}: max |d| C{k} {dv['C']:.2e} (gated)   r{k} {dv['r']:.2e}  g{k} {dv['g']:.2e}   "
              f"(cut4 = 3..{n - 1})")
        ok &= dv["C"] <= TOL_A6E
    for k in ("even_C4raw", "even_C4Dconn", "even_shift4"):
        print(f"  {k:16s} max |d| {float(np.max(np.abs(a[k][:m] - c4[k][:m]))):.2e}   "
              f"(L = 2..{a['even_L'][m - 1]}, reported)")
    return bool(ok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--c4ref", default=None, help="C5 result to compare with the C4P production result (A6e)")
    ap.add_argument("--c4npz", default=C4NPZ)
    a = ap.parse_args()
    if a.c4ref:
        if a.files:
            raise SystemExit("--c4ref takes no positional files")
        h = sha(a.c4npz)
        print(f"files: {a.c4ref} sha256 {sha(a.c4ref)}\n       {a.c4npz} sha256 {h} (C4P production)")
        if h != C4NPZ_SHA256:
            print(f"FAIL: C4P result sha256 {h} != {C4NPZ_SHA256}")
            sys.exit(1)
        ok = c4ref(np.load(a.c4ref), np.load(a.c4npz))
        print(f"{'PASS' if ok else 'FAIL'} A6e (|Delta C2..C4| <= {TOL_A6E:.0e})")
    else:
        if len(a.files) != 2:
            raise SystemExit("usage: v6_overlap.py A.npz B.npz | --c4ref RESULT [--c4npz PATH]")
        print(f"files: {a.files[0]} sha256 {sha(a.files[0])}\n       {a.files[1]} sha256 {sha(a.files[1])}")
        ok = overlap(np.load(a.files[0]), np.load(a.files[1]))
        print(f"{'PASS' if ok else 'FAIL'} A6d (|Delta C5| <= {TOL_A6D:.0e})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
