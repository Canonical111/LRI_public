#!/usr/bin/env python3
"""Large-L extrapolation of the fully window-corrected C_4^W(L) = C4corr + off + dC4chi (L <= 2000) and of its
pieces; writes fits/fits_final.txt.  Protocol (same spirit as ../c4_exact/fits_c4.py): tower models in 1/L with
log powers, fit windows Lmin in {200, 300, 400, 600}; models with an extra free ln L term are reported separately
as a test of log-freeness.  Quoted value = median of the stable no-log set, uncertainty = half the full spread."""
import os
import numpy as np
import fitlib as F

HERE = os.path.dirname(os.path.abspath(__file__))
REF = 5.048868431354847
c = np.load(os.path.join(HERE, "..", "c4_exact", "results", "c4_L2000.npz"))
o = np.load(os.path.join(HERE, "results", "offdiag_L20000.npz"))
n8 = np.load(os.path.join(HERE, "results", "nm_L8000.npz"))
L = c["L"].astype(float)
K = len(L)
series = {"C4W = corr+off+chi": c["C4corr"] + o["off"][:K] + n8["dC4"][:K],
          "C4corr+off": c["C4corr"] + o["off"][:K]}
towers = {"T22": ["1/L", "l/L", "l2/L", "1/L2", "l/L2", "l2/L2"],
          "T22+l3/L": ["1/L", "l/L", "l2/L", "l3/L", "1/L2", "l/L2", "l2/L2"],
          "T23": ["1/L", "l/L", "l2/L", "1/L2", "l/L2", "l2/L2", "l3/L2"],
          "T33": ["1/L", "l/L", "l2/L", "l3/L", "1/L2", "l/L2", "l2/L2", "l3/L2"]}
lines = [f"# C4 reference (continuum) = {REF}", "# data: ../c4_exact/results/c4_L2000.npz, results/offdiag_L20000.npz, "
         "results/nm_L8000.npz; every even L <= 2000"]
summary = {}
for sname, y in series.items():
    lines.append(f"\n== {sname}")
    stable = []
    for tn, t in towers.items():
        for withlog in (False, True):
            row = []
            for Lmin in (200, 300, 400, 600):
                names = ["1"] + (["l"] if withlog else []) + t
                cc, res, nn = F.fit(L, y, names, Lmin)
                row.append(f"{Lmin}:A={cc['1']:.8f}" + (f"[b={cc['l']:+.1e}]" if withlog else "")
                           + f"(c_l2/L={cc['l2/L']:+.3f}) r{res:.0e}")
                if not withlog and Lmin in (200, 300, 400) and tn in ("T22", "T22+l3/L", "T23"):
                    stable.append(cc["1"])
            lines.append(f"  {tn:9s} {'log  ' if withlog else 'nolog'} " + "  ".join(row))
    st = np.array(stable)
    med, half = float(np.median(st)), float((st.max() - st.min()) / 2)
    summary[sname] = (med, half, len(st))
    lines.append(f"  stable no-log set (T22, T22+l3/L, T23 x Lmin 200/300/400): A = {med:.8f} +- {half:.1e} "
                 f"({len(st)} fits);  A - ref = {med - REF:+.2e}")
# chi window alone, L <= 8000
Lx = n8["L"].astype(float)
lines.append("\n== dC4chi alone (results/nm_L8000.npz, L <= 8000)")
vals = []
for t in (["1/L", "l/L", "l2/L", "1/L2", "l/L2"], ["1/L", "l/L", "l2/L", "l3/L", "1/L2", "l/L2", "l2/L2"]):
    for Lmin in (400, 1000, 2000):
        cc, res, nn = F.fit(Lx, n8["dC4"], ["1"] + t, Lmin)
        vals.append(cc["1"])
        lines.append(f"  {len(t)} terms Lmin={Lmin}: A={cc['1']:.10f} res={res:.0e}")
lines.append(f"  dC4chi(inf) = {np.median(vals):.10f} +- {(max(vals) - min(vals)) / 2:.1e}")
a_off = summary["C4corr+off"][0]
lines.append(f"\n== combination of separately extrapolated pieces: (C4corr+off)(inf) + dC4chi(inf) = "
             f"{a_off + np.median(vals):.8f}  (ref {REF:.8f}, diff {a_off + np.median(vals) - REF:+.1e})")
txt = "\n".join(lines)
os.makedirs(os.path.join(HERE, "fits"), exist_ok=True)
open(os.path.join(HERE, "fits", "fits_final.txt"), "w").write(txt + "\n")
print(txt)
