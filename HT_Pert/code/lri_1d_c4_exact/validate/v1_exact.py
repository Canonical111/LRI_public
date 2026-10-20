#!/usr/bin/env python3
"""A1 + A2: diagram sums vs exact rationals.
A1: inputs/exact_rational_validation.json (copy of lri_ht_c8_symmetry/lri_c8_hpc/inputs/...) (Lambda = 2, 4, 6, 8, 12): r2..r4, g2..g4,
    C2..C4 <= 1e-12 relative.
A2: inputs/exact5/* (copies of every exact5_c*.json of lri_hpc_Hamitonian/analysis/eps5_window/{B,reconcile/exactL2};
    12 distinct cut4):
    raw r2..r4, g2..g4, C2..C4 <= 1e-12 relative; Dconn C4 = raw + fast + shift4 at even integer cutoffs
    (cut4 = 8, 16, 24, 32, 48, 64) <= 1e-12 relative.
usage: python3 validate/v1_exact.py"""
import glob
import json
import os
import sys
from fractions import Fraction as F

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "vendor"))
import c4_compute1d as cc   # noqa: E402
import exact_fast           # noqa: E402
import windows1d as wn      # noqa: E402

INP = os.path.join(HERE, "..", "inputs")          # vendored copies, sha256 in inputs/MANIFEST.txt
A1 = os.path.join(INP, "exact_rational_validation.json")
A2 = sorted(glob.glob(os.path.join(INP, "exact5", "*_exact5_c*.json")))
TOL = 1e-12


def rel(a, b):
    b = float(b)
    return abs(a - b) / abs(b)


def main():
    res = cc.compute(17, verbose=False)
    dR4 = wn.delta_R4(16)
    worst = {}
    fails = 0

    def chk(tag, a, b):
        nonlocal fails
        d = rel(a, b) if np.isfinite(a) else np.inf          # a non-finite value is a failure, never skipped
        w = worst.get(tag, 0.0)
        worst[tag] = d if not d <= w else w
        if not d <= TOL:
            fails += 1
            print(f"FAIL {tag}: {a!r} vs {float(b)!r} rel {d:.2e}")

    for e in json.load(open(A1)):
        c = 4 * e["cutoff"]
        for k in (2, 3, 4):
            chk("A1 r", res[f"r{k}"][c], F(e["rational_r"][k]))
            chk("A1 g", res[f"g{k}"][c], F(e["rational_g"][k]))
            chk("A1 C", res[f"C{k}"][c], F(e["rational_C"][k]))
    cuts = set()
    for f in A2:
        d = json.load(open(f))
        c = d["cut4"]
        cuts.add(c)
        v = d["variants"]["raw"]
        for k in (2, 3, 4):
            for nm in ("r", "g", "C"):
                chk(f"A2 raw {nm}", res[f"{nm}{k}"][c], F(v[nm][k]))
        if c % 8 == 0:
            L = c // 4
            sh = -(res["vac_win4_chains"][c] + res["vac_win4_f"][c] + dR4[L]) / 3.0
            chk("A2 Dconn C4", res["C4"][c] + exact_fast.fast(L) + sh, F(d["variants"]["Dconn"]["C"][4]))
    print(f"A2 files: {len(A2)}, distinct cut4: {sorted(cuts)}")
    for k, v in sorted(worst.items()):
        print(f"  worst {k:12s} {v:.2e}")
    ok = fails == 0 and len(cuts) == 12
    print("PASS" if ok else f"FAIL ({fails} deviations > {TOL}, {len(cuts)} cutoffs)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
