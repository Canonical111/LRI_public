#!/usr/bin/env python3
"""Write C4_by_L.csv from the largest results/c4_L*.npz: every even L, columns
L, C4_raw, C4_consistent, C4_corrected, C2, C3, Delta_cons (= consistent - raw), Delta_zm (= corrected - consistent).
Float64; absolute accuracy ~1e-11 (README Sec. 5)."""
import csv
import glob
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
files = [f for f in glob.glob(os.path.join(HERE, "results", "c4_L*.npz")) if "local" not in f]
big = max(files, key=lambda f: int(os.path.basename(f)[4:].split(".")[0]))
d = np.load(big)
with open(os.path.join(HERE, "C4_by_L.csv"), "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["L", "C4_raw", "C4_consistent", "C4_corrected", "C2", "C3", "Delta_cons", "Delta_zm"])
    for i, L in enumerate(d["L"]):
        w.writerow([int(L)] + [repr(float(x)) for x in (d["C4raw"][i], d["C4cons"][i], d["C4corr"][i], d["C2"][i],
                                                        d["C3"][i], d["C4cons"][i] - d["C4raw"][i],
                                                        d["C4corr"][i] - d["C4cons"][i])])
print("wrote C4_by_L.csv from", os.path.basename(big), "rows:", len(d["L"]))
