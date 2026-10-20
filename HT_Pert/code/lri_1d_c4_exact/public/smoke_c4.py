#!/usr/bin/env python3
"""Smoke rerun of the exact C4(Λ) production path at Λmax = 40 (all tasks, assembly) and comparison with the shipped
production result c4_1d_L200.npz on the common grid: |Δ| <= 1e-12 for C2..C4 (quarter grid) and C4^Dconn (even grid).
About 1 min on 4-16 cores.   usage: python3 public/smoke_c4.py [--data ../../data/HT_1d] [--work .work] [--workers 4]"""
import argparse
import os
import shutil
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
SNAP12 = "a8b57b2e8475"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(PKG, "..", "..", "data", "HT_1d"))
    ap.add_argument("--work", default=os.path.join(PKG, ".work"))
    ap.add_argument("--workers", type=int, default=min(16, os.cpu_count() or 4))
    ap.add_argument("--Lmax", type=int, default=40)
    a = ap.parse_args()
    W = os.path.abspath(os.path.join(a.work, "smoke_c4"))
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W)
    out = os.path.join(W, f"c4_1d_L{a.Lmax}.npz")
    # the driver refuses Python files outside its production snapshot (public/ is not part of it): run a copy of the
    # shipped package without public/, public.mk and run-time products
    src = os.path.join(W, "pkg")
    shutil.copytree(PKG, src, ignore=shutil.ignore_patterns("public", "public.mk", ".work", "__pycache__", "*.pyc"))
    for args in (["run", "--Lmax", str(a.Lmax), "--cache", W + "/cache", "--workers", str(a.workers)],
                 ["assemble", "--Lmax", str(a.Lmax), "--cache", W + "/cache", "--out", out]):
        subprocess.run([sys.executable, "c4_run1d.py"] + args, cwd=src, check=True)
    s, r = np.load(out), np.load(os.path.join(a.data, "exact_c4", SNAP12, "c4_1d_L200.npz"))
    worst = max(float(np.nanmax(np.abs(s[k] - r[k][:len(s[k])]))) for k in ("C2", "C3", "C4"))
    n = len(s["even_L"])
    worst = max(worst, float(np.max(np.abs(s["even_C4Dconn"] - r["even_C4Dconn"][:n]))))
    ok = worst <= 1e-12
    print(f"smoke_c4  {'PASS' if ok else 'FAIL'}  Λmax {a.Lmax} rerun vs shipped L200: max |Δ| = {worst:.2e} (<= 1e-12)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
