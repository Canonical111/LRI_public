#!/usr/bin/env python3
"""Markdown tables (README sec. 9) from results/zeromode_L<L>.json."""
import json, os, glob
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
files = sorted(glob.glob(os.path.join(HERE, "results", "zeromode_L*.json")),
               key=lambda f: int(os.path.basename(f)[10:-5]))
R = [json.load(open(f)) for f in files]

print("| L | scheme | C_2 | C_3 | C_4 | C_5 | C_6 | C_7 | C_8 |")
print("|---|---|---|---|---|---|---|---|---|")
for d in R:
    for name, C in (("zeromode", d["C_float"]), ("consistent", d["consistent"]["C_float"])):
        print(f"| {d['L']} | {name} | " + " | ".join(f"{c:.13g}" for c in C[2:]) + " |")
print()
print("| L | C_4(zm) - C_4(cons) | C_5 diff | C_6 diff | C_7 diff | C_8 diff | C_8 rel. diff |")
print("|---|---|---|---|---|---|---|")
for d in R:
    df = d["C_minus_consistent_float"]
    rel = df[8] / d["consistent"]["C_float"][8] if d["consistent"]["C_float"][8] else 0
    print(f"| {d['L']} | " + " | ".join(f"{x:+.10g}" for x in df[4:]) + f" | {rel:+.3f} |")
print()
print("| L | r_2 | r_3 | r_4 | r_5 | r_6 | r_7 | r_8 |")
print("|---|---|---|---|---|---|---|---|")
for d in R:
    print(f"| {d['L']} | " + " | ".join(f"{c:.10g}" for c in d["r_float"][2:]) + " |")
print()
print("| L | g_2 | g_3 | g_4 | g_5 | g_6 | g_7 | g_8 |")
print("|---|---|---|---|---|---|---|---|")
for d in R:
    print(f"| {d['L']} | " + " | ".join(f"{c:.10g}" for c in d["g_float"][2:]) + " |")
print()
print("Exact C_4 .. C_8 (rationals):")
for d in R:
    print(f"L = {d['L']}: max num+den digits {d['max_num_plus_den_digits']}")
    for n in range(4, 9):
        print(f"   C_{n} = {d['C'][n]}")
