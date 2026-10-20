#!/usr/bin/env python3
"""Compare assembled raw C_2..C_5 (and r, g) of a lib_opt run with a reference production npz, every common L.
usage: python3 compare_c5.py new.npz ref.npz [label]"""
import sys
import numpy as np
a, b = np.load(sys.argv[1]), np.load(sys.argv[2])
lab = sys.argv[3] if len(sys.argv) > 3 else ""
n = min(len(a["L"]), len(b["L"]))
assert np.array_equal(a["L"][:n], b["L"][:n])
out = [f"# compare_c5 {lab}: {sys.argv[1]} vs {sys.argv[2]}, L = 2..{int(a['L'][n - 1])}"]
for k in ("raw_C2", "raw_C3", "raw_C4", "raw_C5", "raw_r5", "raw_g5"):
    x, y = a[k][1:n], b[k][1:n]
    rel = np.abs(x - y) / np.maximum(np.abs(y), 1e-300)
    i = int(np.argmax(rel))
    out.append(f"  {k}: max relative difference {rel.max():.2e} (at L = {int(a['L'][1 + i])}); max absolute {np.abs(x - y).max():.2e}")
L = a["L"][:n]
for Lv in (10, 20, 40, 60, 100, 150, 200, 300):
    if Lv <= L[-1]:
        i = Lv // 2
        out.append(f"  L={Lv:3d}: C_5 new {a['raw_C5'][i]:+.15f}  ref {b['raw_C5'][i]:+.15f}  rel {abs(a['raw_C5'][i]-b['raw_C5'][i])/abs(b['raw_C5'][i]):.1e}")
print("\n".join(out))
