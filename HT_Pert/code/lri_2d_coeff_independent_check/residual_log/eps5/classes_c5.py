#!/usr/bin/env python3
"""Divergent content of every window class at eps^5 (and the eps^4 control) from the exact shifts:
  scheme shifts dC_n = C_n(scheme) - C_n(raw), L <= 1000 (delta5.py), fitted with a L + b2 ln^2 L + b1 ln L + c + tower;
  class differences (e.g. D^M,(2) = W2 - Z2) and the D^M,(2) split by M' leg type (Z-chi, chi-in-chi-out, pair creation,
  pair annihilation; DM_TYPES runs, L <= 600) and the min-side Z-chi variant (DM_ZCHI=min, L <= 600).
usage: python3 classes_c5.py  (reads ../results/eps5/*.npz, writes ../results/eps5/classes_c5.txt)"""
import os
import numpy as np
import fitx as F

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "..", "results", "eps5")
TOW = {"t1": ["1/L", "l/L"], "t2": ["1/L", "l/L", "l2/L"], "t3": ["1/L", "l/L", "l2/L", "1/L2"]}


def fitsum(L, y, lead, Lmins=(100, 150, 200)):
    vals = {k: [] for k in lead}
    for tn in TOW:
        for Lmin in Lmins:
            cc, r, nn = F.fit(L, y, lead + TOW[tn], Lmin)
            for k in lead:
                vals[k].append(cc[k])
    return " ".join(f"{k}={np.median(v):+.6f}({(max(v) - min(v)) / 2:.0e})" for k, v in vals.items())


full = np.load(os.path.join(R, "dC5_L1000.npz"))
L = full["L"].astype(float)
out = ["# eps^5 (C5) and eps^4 (C4) divergent content of the window shifts; fits a*L + b2*l2 + b1*l + c + tower",
       "# (C4: a*L + c + b1*l + tower for scheme shifts, c + b1*l + tower for class differences), Lmin 100..200, towers t1..t3; (spread) = half range over fits",
       "\n== scheme shifts dC = C(scheme) - C(raw), L <= 1000"]
for s in ["consistent2", "consistent", "zeromode2", "zeromode", "Z2", "Zb", "W2", "W3m", "W3e", "Wb", "W3x"]:
    out.append(f"  {s:11s} C5: {fitsum(L, full[s + '_dC5'], ['L', '1', 'l', 'l2'])}")
    out.append(f"  {'':11s} C4: {fitsum(L, full[s + '_dC4'], ['L', '1', 'l'])}")
out.append("\n== window classes (differences of shifts)")
for name, a, b in (("eps^3 vacuum window", "consistent", "consistent2"),
                   ("eps^2 z-dependent diagonal", "zeromode2", "consistent2"),
                   ("eps^3 eigenvalue-diagonal", "zeromode", "zeromode2"),
                   ("eps^2 off-diagonal Bloch", "Z2", "zeromode2"),
                   ("eps^3 Bloch (no D^M)", "Zb", "Z2"),
                   ("D^M,(2)", "W2", "Z2"),
                   ("D^M,(3)", "W3m", "W2"),
                   ("eps^3 Bloch (with D^M)", "Wb", "W3m"),
                   ("partner terms in E_z^(3)", "W3e", "W3x")):
    out.append(f"  {name:28s} = {a} - {b}:  C5: {fitsum(L, full[a + '_dC5'] - full[b + '_dC5'], ['L', '1', 'l', 'l2'])}")
    out.append(f"  {'':28s}   C4: {fitsum(L, full[a + '_dC4'] - full[b + '_dC4'], ['1', 'l'])}")
n6 = 301
L6 = L[:n6]
out.append("\n== D^M,(2) = W2 - Z2 split by M' leg type of the D^M vertex (L <= 600)")
tot = 0
for t, lab in (("zchi", "Z-chi (2<Z chi>)"), ("hop", "chi in, chi out"), ("pc", "pair creation"), ("pa", "pair annihilation")):
    d = np.load(os.path.join(R, f"dC5_dm_{t}_L600.npz"))
    y5, y4 = d["W2_dC5"] - d["Z2_dC5"], d["W2_dC4"] - d["Z2_dC4"]
    tot = tot + y5
    out.append(f"  {lab:20s} C5: {fitsum(L6, y5, ['L', '1', 'l', 'l2'])}")
    out.append(f"  {'':20s} C4: {fitsum(L6, y4, ['1', 'l'])}")
out.append(f"  additivity: max |sum of types - (W2 - Z2)| = {np.max(np.abs(tot - (full['W2_dC5'][:n6] - full['Z2_dC5'][:n6]))):.1e}")
z = np.load(os.path.join(R, "dC5_zmin_L600.npz"))
out.append("\n== min-side Z-chi variant of D^M (DM_ZCHI=min), L <= 600")
out.append(f"  D^M,(2) effect C5: {fitsum(L6, z['W2_dC5'] - full['Z2_dC5'][:n6], ['L', '1', 'l', 'l2'])}")
out.append(f"  D^M,(2) effect C4: {fitsum(L6, z['W2_dC4'] - full['Z2_dC4'][:n6], ['1', 'l'])}")
txt = "\n".join(out)
print(txt)
open(os.path.join(R, "classes_c5.txt"), "w").write(txt + "\n")
