"""Table of the exact descendant residuals R_n(L) = [eps^n](E(chi_11) - E(phi) - 2), n = 2, 3 (brute_desc.py)."""
import glob, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "..", "brute")
rows = {}
for f in glob.glob(os.path.join(B, "brute_desc_L*.json")):
    d = json.load(open(f))
    L = d["L"]
    for s, v in d.items():
        if s in ("L", "_note"):
            continue
        rows.setdefault(s, {})[L] = v["R_float"]
order = ["raw", "consistent", "zeromode", "W2", "W3m", "W3e", "Wb", "WbV"]
Ls = sorted({L for s in rows for L in rows[s]})
out = ["# R_2 and R_3 of the chi_11 descendant identity (exact rationals -> float); Wb = scheme W (2026-10-09 spec)",
       "scheme      n  " + " ".join(f"L={L:<9d}" for L in Ls)]
for s in order:
    if s not in rows:
        continue
    for n in (2, 3):
        out.append(f"{s:10s}  {n}  " + " ".join(f"{rows[s][L][n]:+.6f}  " if L in rows[s] else " " * 11 for L in Ls))
txt = "\n".join(out)
print(txt)
open(os.path.join(HERE, "..", "results", "eps5", "descendant_eps3.txt"), "w").write(txt + "\n")
