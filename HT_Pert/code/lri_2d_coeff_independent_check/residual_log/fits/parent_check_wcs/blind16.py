"""Blind L=16 test of chi_aa Wcs R_3 models fitted to L=6..14 (free limit vs zero limit)."""
import glob, json, os, sys
from fractions import Fraction as Fr
import numpy as np
R = sys.argv[1]; out = {}
for f in glob.glob(os.path.join(R, "ce_wc/out_wcs/*.json")):
    j = json.load(open(f)); out[j["meta"]["args"]["L"]] = {k: Fr(x) for k, x in j["schemes"]["Wcs"]["values"].items() if x is not None}
models = [("a+b/L2", lambda L: [L**0, L**-2.]), ("a+b/L2+c/L3", lambda L: [L**0, L**-2., L**-3.]),
          ("a+b/L+c/L2", lambda L: [L**0, 1/L, L**-2.]), ("0: b/L2+c/L3", lambda L: [L**-2., L**-3.]),
          ("0: b/L+c/L2", lambda L: [1/L, L**-2.]), ("0: b/L+c/L2+d/L3", lambda L: [1/L, L**-2., L**-3.]),
          ("0: b/L2+c/L3+d/L4", lambda L: [L**-2., L**-3., L**-4.])]
for dn in ("odd1", "odd2", "odd3"):
    Ls = np.array([l for l in sorted(out) if l >= 6], float)
    y = np.array([float(out[int(l)][f"Ed|{dn}|3"] - out[int(l)]["E|1|3"]) for l in Ls])
    print(f"{dn}: R3(L=16) = {y[-1]:+.6f}")
    for lo in (6, 8):
        m = (Ls >= lo) & (Ls < 16)
        for name, c in models:
            A = np.column_stack(c(Ls[m]))
            if m.sum() < A.shape[1]: continue
            p = np.linalg.lstsq(A, y[m], rcond=None)[0]
            pred = float(np.column_stack(c(Ls[-1:])) @ p)
            lim = 0.0 if name.startswith("0:") else p[0]
            print(f"   Lmin={lo} {name:18s} limit {lim:+.6f}  predicts L=16 {pred:+.6f}  miss {pred - y[-1]:+.1e}")
