#!/usr/bin/env python3
"""Large-L C_5 in scheme Wcs = Wc + slice-resolved eps^3 self-window (WINDOW_SPEC Sec. 2.5a):
    C_5^Wcs(L) = C_5^Wc(L) + delta^(3)(L) S(L),
S(L) = C_5 response to (1/2) X at eps^3 (nm_legw.py, exact chain sums, L <= 400; it converges, no ln L),
delta^(3)(L) exact (delta3.py, tagged phi channel) for L <= Lex (<= 16) and, beyond, a model
delta(L) = d_inf + b/L + c/L^2 fitted to the exact values L = 8..Lex (variants: also + e lnL/L^2; d_inf varied).
Same convergent-ansatz protocol as extrap_wc.py (towers t2..t6, Lmin 30..80, median and half range).
usage: python3 extrap_wcs.py ../results/eps5/c5_L200.npz ../results/eps5/dC5_L1000_all.npz ../results/legw/legw_L400.npz ../results/tag

[2026-10-14] Superseded: the towers here stop at ln^2 L / L (C_5 needs ln^3 L / L), and the delta models beyond L = 16 are
wrong (delta_inf = -4/(81 pi), non-monotone delta(L)). Use large_L/c5_fits.py (README Sec. 12.9, large_L/README.md)."""
import glob
import json
import os
import sys
from fractions import Fraction as Fr

import numpy as np

import fitx as F

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import delta3 as d3  # noqa: E402

REF5 = -38.833645896225360553
TOW = {"t2": ["1/L", "l/L", "l2/L"], "t3": ["1/L", "l/L", "l2/L", "1/L2"], "t4": ["1/L", "l/L", "l2/L", "l3/L", "1/L2"],
       "t5": ["1/L", "l/L", "l2/L", "1/L2", "l/L2"], "t6": ["1/L", "l/L", "l2/L", "l3/L", "1/L2", "l/L2"]}


def extrap(L, y):
    A = []
    for tn, t in TOW.items():
        for Lmin in (30, 40, 60, 80):
            cc, res, nn = F.fit(L, y, ["1"] + t, Lmin)
            A.append(cc["1"])
    A = np.array(A)
    return float(np.median(A)), float((A.max() - A.min()) / 2)


def main():
    p = np.load(sys.argv[1]); d = np.load(sys.argv[2]); s = np.load(sys.argv[3]); tagdir = sys.argv[4]
    L = p["L"].astype(float); n = len(L)
    c5wc = p["raw_C5"] + d["Wc_dC5"][:n]
    S = s["S"][:n]
    assert np.all(s["L"][:n] == p["L"])
    dex = {}
    for f in glob.glob(os.path.join(tagdir, "tag_L*_a1_phi2_2_real.json")):
        j = json.load(open(f))
        dex[j["L"]] = float(d3.delta_from(j, 1))
    Lex = sorted(dex)
    print("exact delta^(3)(L):", ", ".join(f"{l}: {dex[l]:+.7f}" for l in Lex))
    xs = np.array([l for l in Lex if l >= 8], float)
    ys = np.array([dex[int(l)] for l in xs])
    models = {}
    X = np.vstack([np.ones_like(xs), 1 / xs, 1 / xs ** 2]).T
    models["d+b/L+c/L2"] = np.linalg.lstsq(X, ys, rcond=None)[0]
    if len(xs) >= 4:
        X2 = np.vstack([np.ones_like(xs), 1 / xs, 1 / xs ** 2, np.log(xs) / xs ** 2]).T
        models["d+b/L+c/L2+e lnL/L2"] = np.linalg.lstsq(X2, ys, rcond=None)[0]
    X3 = np.vstack([np.ones_like(xs), np.log(xs) / xs, 1 / xs]).T
    models["d+e lnL/L+b/L"] = np.linalg.lstsq(X3, ys, rcond=None)[0]
    out = []
    A0, h0 = extrap(L, c5wc)
    out.append(f"C5^Wc  (reference)            A = {A0:.5f} +- {h0:.2e}   (A - exact = {A0 - REF5:+.3e})")
    Sfit = np.polyfit  # noqa
    for name, co in models.items():
        def dmod(x):
            if name == "d+b/L+c/L2":
                return co[0] + co[1] / x + co[2] / x ** 2
            if name == "d+b/L+c/L2+e lnL/L2":
                return co[0] + co[1] / x + co[2] / x ** 2 + co[3] * np.log(x) / x ** 2
            return co[0] + co[1] * np.log(x) / x + co[2] / x
        dl = np.array([dex[int(l)] if int(l) in dex else (dmod(l) if l > 0 else 0.0) for l in L])
        y = c5wc + dl * S
        A, h = extrap(L, y)
        mono = "" if co[0] <= dex[Lex[-1]] else "  [NOT monotone: delta_inf above the last exact delta]"
        out.append(f"C5^Wcs delta model {name:22s}: delta_inf = {co[0]:+.6f}  delta(200) = {dmod(200.0):+.6f}  "
                   f"A = {A:.5f} +- {h:.2e}   (A - exact = {A - REF5:+.3e});  shift of the limit {A - A0:+.5f}{mono}")
    # S(L) limit (convergent fits)
    ls = s["L"].astype(float)
    m = ls >= 80
    x = ls[m]
    Xs = np.vstack([np.ones_like(x), 1 / x, np.log(x) / x, 1 / x ** 2, np.log(x) / x ** 2]).T
    Sinf = np.linalg.lstsq(Xs, s["S"][m], rcond=None)[0][0]
    out.append(f"S(inf) = {Sinf:.6f}  (S(200) = {s['S'][100]:.6f}, S(400) = {s['S'][200]:.6f})")
    txt = "\n".join(out)
    print(txt)
    note = ("# [2026-10-14] Superseded protocol; see large_L/README.md Sec. 5 and large_L/fits/c5_fits.txt "
            "(C_5^Wcs(inf) = -38.839 +- 0.028 with the ln^3 L / L tail; delta_inf = -4/(81 pi)).\n")
    open(os.path.join(HERE, "..", "fits", "extrap_wcs_c5.txt"), "w").write(
        note + "exact delta^(3)(L): " + ", ".join(f"{l}: {dex[l]:+.9f}" for l in Lex) + "\n" + txt + "\n")


if __name__ == "__main__":
    main()
