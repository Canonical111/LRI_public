#!/usr/bin/env python3
"""Compare the diagram-sum C_4 (raw, consistent, corrected) with the brute-force exact rationals of
brute_corrected.py (brute/brute_L*.json) and, if present, with ../zeromode_exact/results (another agent's
independent exact implementation of the zero-mode-aware scheme)."""
import glob
import json
import os
from fractions import Fraction as Fr

import c4_compute as cc

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    files = sorted(glob.glob(os.path.join(HERE, "brute", "brute_L*.json")),
                   key=lambda f: int(f.split("_L")[-1][:-5]))
    Lmax = max(int(f.split("_L")[-1][:-5]) for f in files)
    res = cc.compute(max(Lmax, 2), verbose=False)
    key = {"raw": "C4raw", "consistent": "C4cons", "corrected": "C4corr"}
    worst = {}
    for fn in files:
        d = json.load(open(fn))
        L = d["L"]
        line = f"L={L:3d}"
        for s, k in key.items():
            ex = Fr(d["C"][s][4])
            mine = res[k][L // 2]
            rel = abs(mine - float(ex)) / abs(float(ex))
            worst[s] = max(worst.get(s, 0), rel)
            line += f"  {s}: exact {float(ex):.15f} diagram {mine:.15f} rel {rel:.1e}"
        print(line)
    print("worst relative deviations vs brute force:", {s: f"{v:.1e}" for s, v in worst.items()})
    zdir = os.path.join(HERE, "..", "zeromode_exact", "results")
    zf = sorted(glob.glob(os.path.join(zdir, "**", "*.json"), recursive=True))
    zf = [f for f in zf if os.path.basename(f).startswith("zeromode_L")]
    print(f"zeromode_exact/results: {len(zf)} zeromode_L*.json files found")
    if zf:
        Lz = max(json.load(open(f))["L"] for f in zf)
        res2 = cc.compute(max(Lz, 2), verbose=False)
        wz = 0.0
        for fn in sorted(zf, key=lambda f: json.load(open(f))["L"]):
            d = json.load(open(fn))
            L = d["L"]
            ex = Fr(d["C"][4])
            mine = res2["C4corr"][L // 2]
            rel = abs(mine - float(ex)) / abs(float(ex))
            r3 = abs(res2["r3"][L // 2] - float(Fr(d["r"][3]))) / abs(float(Fr(d["r"][3])))
            wz = max(wz, rel)
            print(f"  L={L:3d} zeromode_exact C4 = {float(ex):.15f}  diagram corrected C4 = {mine:.15f}  rel {rel:.1e}"
                  f"  (r3 rel {r3:.1e})")
        print(f"worst relative deviation vs zeromode_exact (L <= {Lz}): {wz:.1e}")


if __name__ == "__main__":
    main()
