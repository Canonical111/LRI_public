#!/usr/bin/env python3
"""Descendant identity in 3D (T2/T3 of the 2D project): R_n(L) = [eps^n](E(chi_11) - E(phi) - 2) for chi_11 = one
(n=1, l=0) bath quantum, by scheme (brute3d_desc: raw, W2, Wc, Wcs) and with the external legs tagged
(brute3d_tagchi, scheme Wc windows: nu = (0,0) budget-free, (2,2) = Wc, (2,0), (0,2) single leg).
Output: ../fits/t3_summary.txt"""
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import fitlib3d as F  # noqa: E402

R = os.path.join(HERE, "..", "results")
OUT = []


def P(s=""):
    OUT.append(s)
    print(s, flush=True)


def load():
    desc, tag, d3 = {}, {}, {}
    for f in glob.glob(os.path.join(R, "eps5", "desc_L*.json")) + glob.glob(os.path.join(R, "desc", "desc_L*.json")):
        r = json.load(open(f))
        desc[int(r["L"])] = r["R"]
    for f in glob.glob(os.path.join(R, "tagchi", "tagchi_L*.json")):
        r = json.load(open(f))
        tag[int(r["L"])] = r
    for f in glob.glob(os.path.join(R, "tag", "tag_L*.json")):
        r = json.load(open(f))
        if "delta3" in r:
            d3[int(r["L"])] = r["delta3"]
    return desc, tag, d3


def main():
    desc, tag, d3 = load()
    Ls = sorted(set(desc) | set(tag))
    P("== R_2, R_3 of chi_11 by scheme (exact brute force on the package operators)")
    P(f"   {'L':>3s} {'raw R3':>10s} {'W2 R3':>10s} {'Wc R2':>10s} {'Wc R3':>10s} {'Wcs R3':>10s} | tagged legs (Wc windows):"
      f" {'bf R2':>9s} {'bf R3':>9s} {'(2,0) R3':>9s} {'(0,2) R3':>9s} | {'leg=Wc-bf':>9s} {'-d3/2':>9s}")
    rows = []
    for L in Ls:
        d = desc.get(L, {})
        t = tag.get(L, {})
        g = lambda k, i: (d[k][i] if k in d else np.nan)
        h = lambda k, i: (t[k][i] if k in t else np.nan)
        leg = g("Wc", 3) - h("R_0_0", 3)
        rows.append((L, g("raw", 3), g("W2", 3), g("Wc", 2), g("Wc", 3), g("Wcs", 3), h("R_0_0", 2), h("R_0_0", 3),
                     h("R_2_0", 3), h("R_0_2", 3), leg, -d3.get(L, np.nan) / 2))
        P(f"   {L:3d} " + " ".join(f"{x:+10.6f}" for x in rows[-1][1:6]) + " |                            "
          + " ".join(f"{x:+9.6f}" for x in rows[-1][6:10]) + " | " + " ".join(f"{x:+9.6f}" for x in rows[-1][10:]))
    if tag:
        P("   check: tagged nu=(2,2) equals Wc (R_2, R_3): max diff "
          f"{max(abs(tag[L]['R_2_2'][n] - desc[L]['Wc'][n]) for L in tag if L in desc for n in (2, 3)):.1e}")
    A = np.array(rows, dtype=float)
    L = A[:, 0]
    P("\n== large-L fits (L >= 8): R = a + b L^-1/2 + c L^-1  (and a + b L^-1/2 + c L^-1 + d L^-3/2 when enough points)")
    cols = {"Wc R2": 3, "Wc R3": 4, "Wcs R3": 5, "bf R2": 6, "bf R3": 7, "leg": 10, "-d3/2": 11}
    for name, j in cols.items():
        y = A[:, j]
        ok = ~np.isnan(y) & (L >= 8)
        if ok.sum() < 4:
            continue
        out = []
        for names in (["1", "L^-0.5", "L^-1"], ["1", "L^-0.5", "L^-1", "L^-1.5"], ["L^0.5", "1", "L^-0.5"],
                      ["l1*L^0", "1", "L^-1"]):
            if ok.sum() < len(names) + 1:
                continue
            c, res, k = F.fit(L[ok], y[ok], names, 8)
            out.append("[" + " ".join(f"{a}={b:+.4f}" for a, b in c.items()) + f" res {res:.0e}]")
        P(f"   {name:7s} " + " ".join(out))
    with open(os.path.join(HERE, "..", "fits", "t3_summary.txt"), "w") as f:
        f.write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
