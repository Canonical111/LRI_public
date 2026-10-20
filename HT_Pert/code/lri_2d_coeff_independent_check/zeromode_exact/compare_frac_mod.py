#!/usr/bin/env python3
"""Exact comparison of zeromode_fraction.py output with a zeromode_modular.py output (variant zeromode).
usage: python3 compare_frac_mod.py frac.json mod.json [variant]"""
import json, sys
from fractions import Fraction as Fr
f = json.load(open(sys.argv[1]))
m = json.load(open(sys.argv[2]))["variants"][sys.argv[3] if len(sys.argv) > 3 else "zeromode"]["values"]
n = bad = 0
for k in ("C", "r", "g"):
    for i, v in enumerate(f[k]):
        n += 1; bad += Fr(v) != Fr(m[f"{k}|{i}"])
for p, row in enumerate(f["E"]):
    for i, v in enumerate(row):
        n += 1; bad += Fr(v) != Fr(m[f"E|{p}|{i}"])
for zl, row in f["Ez"].items():
    for i, v in enumerate(row):
        n += 1; bad += Fr(v) != Fr(m[f"Ez|{zl}|{i}"])
nm = sum(1 for k in m if k.startswith("Ez"))
print(f"L={f['L']}: compared {n} exact numbers (all C, r, g, E_p and {sum(len(r) for r in f['Ez'].values())} E_z(l) "
      f"coefficients; modular file has {nm}); mismatches: {bad}")
sys.exit(1 if bad else 0)
