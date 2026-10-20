"""Validate the eps^5 shifts (delta5) + exact raw C_n (rs_exact, L <= 18) against the independent exact implementation
../../complete_exact/results/complete_L*.json (L <= 16): scheme W (= our Wb), W2, raw, consistent, zeromode."""
import json, os, sys
from fractions import Fraction as Fr
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
RL = os.path.join(HERE, "..")
CE = os.path.join(RL, "..", "complete_exact", "results")
d = np.load(sys.argv[1])
worst, lines = {}, []
for L in range(2, 17, 2):
    f = os.path.join(CE, f"complete_L{L}.json")
    if not os.path.exists(f):
        continue
    c = json.load(open(f))
    i = L // 2
    raw = json.load(open(os.path.join(RL, f"rs_exact_results/raw_L{L}.json")))["C_float"]
    refs = {"Wb": c["C_float"]}
    if "W2" in c["alternatives"]:
        refs["W2"] = c["alternatives"]["W2"]["C_float"]
    for s in ("raw", "consistent", "zeromode"):
        o = c["other_schemes_C"][s]
        o = o.get("C_float", o.get("C")) if isinstance(o, dict) else o
        refs[s] = [float(Fr(x)) if isinstance(x, str) else float(x) for x in o]
    for s, ref in refs.items():
        for n in (3, 4, 5):
            v = raw[n] + (d[f"{s}_dC{n}"][i] if s != "raw" else 0.0)
            e = abs(v - ref[n]) / abs(ref[n])
            worst[(s, n)] = max(worst.get((s, n), 0.0), e)
    lines.append(f"L={L:2d}  W C5: complete_exact {c['C_float'][5]:+.13f}   ours (raw + Wb shift) {raw[5] + d['Wb_dC5'][i]:+.13f}")
for k, v in sorted(worst.items()):
    lines.append(f"worst rel. deviation {k[0]:10s} C{k[1]}: {v:.1e}   (ours 'Wb' = their W)")
print("\n".join(lines))
open(os.path.join(RL, "results", "eps5", "validation_vs_complete_exact.txt"), "w").write("\n".join(lines) + "\n")
