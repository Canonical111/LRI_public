#!/usr/bin/env python3
"""A6d: two production results with different Lmax agree at every common cutoff.  Both files must have the
prescribed quarter grid (cut4 = 0..4 Lmax), validity mask (cut4 >= 3) and even grid, and finite values on the valid
domain; then max |Delta C4| over every common valid cutoff <= 1e-11 (C2, C3, r4, g4, shift4, C4Dconn reported).
Prints the sha256 of both files (recorded in the gate record).
usage: python3 validate/v6_overlap.py results/c4_1d_L200.npz results/c4_1d_L400.npz"""
import hashlib
import sys

import numpy as np


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def grid_ok(d):
    nc = len(d["cut4"])
    Lmax = (nc - 1) // 4
    ok = np.array_equal(d["cut4"], np.arange(nc)) and np.array_equal(d["valid"], d["cut4"] >= 3)
    ok &= np.array_equal(d["even_L"], np.arange(2, Lmax + 1, 2))
    for k in ("C2", "C3", "C4", "r4", "g4"):
        ok &= d[k].shape == (nc,) and bool(np.all(np.isfinite(d[k][3:])))
    for k in ("even_shift4", "even_C4Dconn"):
        ok &= d[k].shape == d["even_L"].shape and bool(np.all(np.isfinite(d[k])))
    return bool(ok)


def main():
    a, b = np.load(sys.argv[1]), np.load(sys.argv[2])
    print(f"files: {sys.argv[1]} sha256 {sha(sys.argv[1])}\n       {sys.argv[2]} sha256 {sha(sys.argv[2])}")
    ok = grid_ok(a) and grid_ok(b)
    if not ok:
        print("grid/validity/finiteness check FAILED")
    n = min(len(a["C4"]), len(b["C4"]))
    for k in ("C2", "C3", "C4", "r4", "g4"):
        dv = float(np.max(np.abs(a[k][3:n] - b[k][3:n])))
        print(f"{k}: max |d| {dv:.2e} over cut4 = 3..{n - 1}")
        if k == "C4":
            ok &= dv <= 1e-11
    m = min(len(a["even_L"]), len(b["even_L"]))
    for k in ("even_shift4", "even_C4Dconn"):
        print(f"{k}: max |d| {np.max(np.abs(a[k][:m] - b[k][:m])):.2e} over L = 2..{a['even_L'][m - 1]}")
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
