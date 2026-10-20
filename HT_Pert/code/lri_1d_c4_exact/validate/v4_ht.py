#!/usr/bin/env python3
"""A4: diagram-sum C2, C3, C4 vs the HT campaign data (float64): data.json "raw" (Lambda <= 92) and "thermal_d7"
(Lambda <= 118).  Reports max |Delta| per coefficient and source; gate |Delta C4| <= 1e-8.
usage: python3 validate/v4_ht.py results/c4_1d_L400.npz"""
import json
import os
import sys

import numpy as np

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "inputs", "ht_data.json")  # copy, see MANIFEST


def main():
    d = np.load(sys.argv[1])
    ht = json.load(open(DATA))
    ok = True
    for src in ("raw", "thermal_d7"):
        Ls = sorted(int(k) for k in ht[src])
        if 4 * Ls[-1] >= len(d["C4"]):
            print(f"{src}: result does not cover L = {Ls[-1]}"); ok = False
        Ls = [L for L in Ls if 4 * L < len(d["C4"])]
        worst = {k: (0.0, None) for k in (2, 3, 4)}
        for L in Ls:
            for k in (2, 3, 4):
                v = d[f"C{k}"][4 * L]
                dv = abs(v - ht[src][str(L)][k]) if np.isfinite(v) else np.inf   # non-finite fails
                if not dv <= worst[k][0]:
                    worst[k] = (dv, L)
        print(f"{src:10s} L={Ls[0]}..{Ls[-1]} ({len(Ls)} cutoffs): "
              + "  ".join(f"C{k}: max|d| {worst[k][0]:.1e} at L={worst[k][1]}" for k in (2, 3, 4)))
        ok &= bool(worst[4][0] <= 1e-8)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
