#!/usr/bin/env python3
"""Deliverable tables.
C4W_by_L.csv: every even L <= 2000: C4 raw / consistent / corrected (../c4_exact), the off-diagonal zero-mode window
shift (offdiag_window.py), the chi-sunset window shift (nm_window.py), C4_fullzm = corrected + off, C4_W = fullzm + chi.
window_shifts_by_L.csv: every even L <= 8000: off (and its m=2 x sunset part), chi (direct, via g3)."""
import csv
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REF = 5.048868431354847
c = np.load(os.path.join(HERE, "..", "c4_exact", "results", "c4_L2000.npz"))
o = np.load(os.path.join(HERE, "results", "offdiag_L20000.npz"))
n = np.load(os.path.join(HERE, "results", "nm_L8000.npz"))
K = len(c["L"])
with open(os.path.join(HERE, "C4W_by_L.csv"), "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["L", "C4_raw", "C4_consistent", "C4_corrected_zm_diag", "dC4_zm_offdiag", "C4_full_zm",
                "dC4_chi", "C4_W", "C4_W_minus_continuum"])
    for i in range(K):
        fz = c["C4corr"][i] + o["off"][i]
        W = fz + n["dC4"][i]
        w.writerow([int(c["L"][i])] + [f"{x:.14f}" for x in (c["C4raw"][i], c["C4cons"][i], c["C4corr"][i],
                                                             o["off"][i], fz, n["dC4"][i], W, W - REF)])
Kn = len(n["L"])
with open(os.path.join(HERE, "window_shifts_by_L.csv"), "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["L", "dC4_zm_offdiag", "dC4_zm_offdiag_m2xsunset", "dC4_zm_diag_plus_vacuum", "dC4_chi",
                "dC4_chi_direct", "dC4_chi_via_g3", "dg3_chi"])
    for i in range(Kn):
        w.writerow([int(n["L"][i])] + [f"{x:.15e}" for x in (o["off"][i], o["off_m2_m3"][i], o["diag"][i],
                                                             n["dC4"][i], n["direct"][i], n["via_g3"][i],
                                                             n["dg3"][i])])
print("wrote C4W_by_L.csv", K, "rows; window_shifts_by_L.csv", Kn, "rows")
