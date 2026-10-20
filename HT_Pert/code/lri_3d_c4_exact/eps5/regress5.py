#!/usr/bin/env python3
"""Regression: compare two prod5 outputs (every key present in both: C_n, r_n, g_n of every scheme), report the
largest absolute deviation per scheme and order.  usage: python3 regress5.py new.npz ref.npz"""
import sys

import numpy as np


def main():
    a, b = np.load(sys.argv[1]), np.load(sys.argv[2])
    La, Lb = list(a["L"]), list(b["L"])
    common = [l for l in La if l in Lb]
    ia = [La.index(l) for l in common]
    ib = [Lb.index(l) for l in common]
    keys = sorted(k for k in set(a.files) & set(b.files) if k != "L")
    worst = 0.0
    rows = {}
    for k in keys:
        d = np.max(np.abs(a[k][ia] - b[k][ib]))
        rows[k] = d
        worst = max(worst, d)
    print(f"# {sys.argv[1]} vs {sys.argv[2]}: L = {int(common[0])}..{int(common[-1])} ({len(common)} values), "
          f"{len(keys)} arrays")
    for k in keys:
        if k.endswith("C5") or k.endswith("C4"):
            print(f"  {k:22s} max |diff| = {rows[k]:.2e}")
    print(f"# worst over all {len(keys)} arrays (C_n, r_n, g_n): {worst:.2e}")


if __name__ == "__main__":
    main()
