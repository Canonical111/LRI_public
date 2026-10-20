#!/usr/bin/env python3
"""Validation of the eps^5 diagram sums (prod5.py output):
  (a) raw and consistent C2..C5 against the package (reference L = 0..14, campaign L = 16..20);
  (b) every window scheme (W2, W3m, Wb, Wc, Zb) against the brute force on the package operators (brute3d_W5.py).
usage: python3 validate5.py ../results/c5_L12.npz [brute_dir]"""
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..", "..", "lri_3d_hpc", "results", "reference_coefficients_L14.json")
CAMP = os.path.join(HERE, "..", "..", "results_expanse_2026-10", "results")


def package():
    d = {}
    for r in json.load(open(PKG))["results"]:
        d[(r["scheme"], r["cutoff"])] = [float(x) for x in r["C"]]
    for f in glob.glob(os.path.join(CAMP, "L*", "c*_*.json")):
        r = json.load(open(f))["result"]
        d.setdefault((r["scheme"], r["cutoff"]), [float(x) for x in r["C"]])
    return d


def main():
    z = np.load(sys.argv[1])
    bdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "results", "brute")
    pk = package()
    Ls = [int(x) for x in z["L"]]
    print("(a) package comparison: max scaled deviation |mine - pkg| / max(1, |pkg|)")
    worst = {}
    for scheme, tag in (("raw", "raw"), ("consistent", "consistent")):
        for j, L in enumerate(Ls):
            if (scheme, L) not in pk:
                continue
            for n in range(2, 6):
                mine = z[f"{tag}_C{n}"][j]
                d = abs(mine - pk[(scheme, L)][n]) / max(1, abs(pk[(scheme, L)][n]))
                worst[(scheme, n)] = max(worst.get((scheme, n), 0), d)
            print(f"  {scheme:10s} L={L:2d} C5 mine {z[tag + '_C5'][j]:+.14f} pkg {pk[(scheme, L)][5]:+.14f}")
    for k, v in sorted(worst.items()):
        print(f"  worst {k[0]:10s} C{k[1]}: {v:.2e}")
    print("(b) brute force (package operators + explicit windows)")
    wb = {}
    for f in sorted(glob.glob(os.path.join(bdir, "brute_L*.json"))):
        d = json.load(open(f))
        L = d["L"]
        if L not in Ls:
            continue
        j = Ls.index(L)
        for var, r in d["results"].items():
            if f"{var}_C5" not in z.files:
                continue
            for n in range(2, 6):
                dv = abs(z[f"{var}_C{n}"][j] - r["C"][n])
                wb[(var, n)] = max(wb.get((var, n), 0), dv)
            print(f"  {var:4s} L={L:2d} C4 {z[var + '_C4'][j]:+.13f} vs {r['C'][4]:+.13f}   "
                  f"C5 {z[var + '_C5'][j]:+.13f} vs {r['C'][5]:+.13f}")
    for k, v in sorted(wb.items()):
        print(f"  worst |diff| {k[0]:4s} C{k[1]}: {v:.2e}")


if __name__ == "__main__":
    main()
