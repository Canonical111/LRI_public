#!/usr/bin/env python3
"""Compare the diagram-sum coefficients with the lri_3d_hpc package (reference L = 0..14, campaign L = 16..20).

usage: python3 validate_pkg.py RESULT.npz [--skip4]"""
import argparse
import glob
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..", "lri_3d_hpc", "results", "reference_coefficients_L14.json")
CAMP = os.path.join(HERE, "..", "results_expanse_2026-10", "results")


def load_package():
    data = {}
    for r in json.load(open(PKG))["results"]:
        data[(r["scheme"], r["cutoff"])] = r
    for f in sorted(glob.glob(os.path.join(CAMP, "L*", "c*_*.json"))):
        r = json.load(open(f))["result"]
        key = (r["scheme"], r["cutoff"])
        if key not in data:
            data[key] = r
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("npz")
    ap.add_argument("--skip4", action="store_true")
    args = ap.parse_args()
    res = np.load(args.npz)
    pkg = load_package()
    Lmax = int(res["L"][-1])
    idx = {int(L): j for j, L in enumerate(res["L"])}
    rows = []
    worst = {}
    for (scheme, L), r in sorted(pkg.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if L > Lmax:
            continue
        Lc = L
        L = idx[Lc]
        C = [float(x) for x in r["C"]]
        rr = [float(x) for x in r["r"]]
        gg = [float(x) for x in r["g"]]
        E = {p: [float(x) for x in r["energies_by_seed"][str(p)]] for p in range(4)}
        mine = {"C2": res["C2"][L], "C3": res["C3"][L], "r2": res["r2"][L], "g2": res["g2"][L],
                "r3": res["r3"][L], "g3": res["g3"][L]}
        theirs = {"C2": C[2], "C3": C[3], "r2": rr[2], "g2": gg[2], "r3": rr[3], "g3": gg[3]}
        for p in range(4):
            for n, (Xn, rn, gn) in ((2, ("X2", "r2", "g2")), (3, ("X3", "r3", "g3"))):
                mine[f"E{p}^{n}"] = res[Xn][p][L] + 2 * p * res[rn][L] + p * (p - 1) / 2 * res[gn][L]
                theirs[f"E{p}^{n}"] = E[p][n]
        if not args.skip4:
            mine["C4"] = res["C4raw" if scheme == "raw" else "C4cons"][L]
            theirs["C4"] = C[4]
        for k in mine:
            d = abs(mine[k] - theirs[k]) / max(1.0, abs(theirs[k]))
            worst[(scheme, k)] = max(worst.get((scheme, k), 0.0), d)
        rows.append((scheme, Lc, mine.get("C4", np.nan), theirs.get("C4", np.nan),
                     max(abs(mine[k] - theirs[k]) / max(1.0, abs(theirs[k])) for k in mine)))
    for row in rows:
        print("%-10s L=%2d C4 mine=%.15f pkg=%.15f  worst scaled dev %.2e" % row)
    print("worst scaled deviation per quantity:")
    for k, v in sorted(worst.items()):
        print("  %-10s %-6s %.2e" % (k[0], k[1], v))


if __name__ == "__main__":
    main()
