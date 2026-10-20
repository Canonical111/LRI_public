#!/usr/bin/env python3
"""A5 (ii) on the full production range: the engine's cancellation-free Delta R4(L) equals the closed form
H_odd(L-1)/2916 at every even L <= Lmax (default 2000): <= 1e-14 relative.  Two-vertex sums only (no production
data needed); run by the pre-production validation job.
usage: python3 validate/v7_dR4.py [--Lmax 2000]"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import windows1d as wn   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, default=2000)
    a = ap.parse_args()
    dR = wn.delta_R4(a.Lmax)
    worst, wL = 0.0, None
    for L in range(2, a.Lmax + 1, 2):
        ref = wn.h_odd(L - 1) / 2916.0
        d = abs(dR[L] - ref) / ref if math.isfinite(dR[L]) else math.inf
        if not d <= worst:
            worst, wL = d, L
    ok = len(dR) == a.Lmax // 2 and worst <= 1e-14
    print(f"Delta R4 vs H_odd(L-1)/2916, even L = 2..{a.Lmax} ({len(dR)} cutoffs): max rel {worst:.2e} at L={wL}")
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
