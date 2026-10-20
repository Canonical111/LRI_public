#!/usr/bin/env python3
"""Large-L extrapolation of C_5 in the corrected scheme Wc (and of C_4^W as the calibration of the same protocol):
C_5^Wc(L) = raw C_5(L) (prod5, L <= Lraw) + exact shift (delta5, L <= 1000).  Convergent ansatz A + tower (no L,
no ln^k L), towers t2..t6, Lmin 30..80; quoted: median and half range.  Also the free-log fits for the record.
usage: python3 extrap_wc.py ../results/eps5/c5_L160.npz ../results/eps5/dC5_L1000_all.npz"""
import os, sys
import numpy as np
import fitx as F
REF5, REF4 = -38.833645896225360553, 5.048868431354847
TOW = {"t2": ["1/L", "l/L", "l2/L"], "t3": ["1/L", "l/L", "l2/L", "1/L2"], "t4": ["1/L", "l/L", "l2/L", "l3/L", "1/L2"],
       "t5": ["1/L", "l/L", "l2/L", "1/L2", "l/L2"], "t6": ["1/L", "l/L", "l2/L", "l3/L", "1/L2", "l/L2"]}
p = np.load(sys.argv[1]); d = np.load(sys.argv[2])
L = p["L"].astype(float); n = len(L)
out = []
c4w = p["Wb_C4"] if "Wb_C4" in p.files else p["raw_C4"] + d["Wb_dC4"][:n]
for name, y, ref in (("C4^W (calibration)", c4w, REF4), ("C5^Wc", p["raw_C5"] + d["Wc_dC5"][:n], REF5),
                     ("C5^Zb", p["raw_C5"] + d["Zb_dC5"][:n], REF5), ("C5^consistent", p["raw_C5"] + d["consistent_dC5"][:n], REF5),
                     ("C5^Wb (spec W)", p["raw_C5"] + d["Wb_dC5"][:n], REF5)):
    A = []
    for tn, t in TOW.items():
        for Lmin in (30, 40, 60, 80):
            cc, res, nn = F.fit(L, y, ["1"] + t, Lmin)
            A.append(cc["1"])
    A = np.array(A)
    med, half = float(np.median(A)), float((A.max() - A.min()) / 2)
    out.append(f"{name:20s} L <= {int(L.max())}: A = {med:.5f} +- {half:.2e}   (A - exact = {med - ref:+.3e})")
txt = "\n".join(out)
print(txt)
tag = os.path.basename(sys.argv[1]).replace(".npz", "")
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fits", f"extrap_wc_{tag}.txt"), "w").write(txt + "\n")
