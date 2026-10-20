#!/usr/bin/env python3
"""Print Markdown tables of C_2..C_8 (floats, 16 significant digits) and r, g from results/*.json,
exact rationals are in the JSON files."""
import json, os, sys, glob
from fractions import Fraction as Fr

here = os.path.dirname(os.path.abspath(__file__))
res = {}
for fn in glob.glob(os.path.join(here, "results", "*_L*.json")):
    d = json.load(open(fn))
    res[(d["scheme"], d["L"])] = d
Ls = sorted({L for (_, L) in res})
schemes = ["raw", "consistent", "literal"]


def f16(s):
    return f"{float(Fr(s)):.16g}"


out = []
for s in schemes:
    out.append(f"\n**{s}** (exact rationals in `results/{s}_L<L>.json`; floats below are the rationals rounded)\n")
    out.append("| L | " + " | ".join(f"C_{n}" for n in range(2, 9)) + " |")
    out.append("|---" * 8 + "|")
    for L in Ls:
        if (s, L) not in res:
            continue
        C = res[(s, L)]["C"]
        out.append(f"| {L} | " + " | ".join(f16(C[n]) for n in range(2, 9)) + " |")
out.append("\n**r_n, g_n (consistent scheme)**\n")
out.append("| L | " + " | ".join(f"r_{n}" for n in range(2, 9)) + " |")
out.append("|---" * 8 + "|")
for L in Ls:
    if ("consistent", L) in res:
        r = res[("consistent", L)]["r"]
        out.append(f"| {L} | " + " | ".join(f"{float(Fr(r[n])):.10g}" for n in range(2, 9)) + " |")
out.append("")
out.append("| L | " + " | ".join(f"g_{n}" for n in range(2, 9)) + " |")
out.append("|---" * 8 + "|")
for L in Ls:
    if ("consistent", L) in res:
        g = res[("consistent", L)]["g"]
        out.append(f"| {L} | " + " | ".join(f"{float(Fr(g[n])):.10g}" for n in range(2, 9)) + " |")
print("\n".join(out))



def first_diff(a, b):
    return next((n for n in range(9) if Fr(a[n]) != Fr(b[n])), None)


print("\n**First order at which the schemes differ** (C; r; g; E_0..E_3)\n")
print("| L | raw vs consistent | consistent vs literal |")
print("|---|---|---|")
for L in Ls:
    row = []
    for s1, s2 in (("raw", "consistent"), ("consistent", "literal")):
        if (s1, L) in res and (s2, L) in res:
            A, B = res[(s1, L)], res[(s2, L)]
            fd = [first_diff(A["C"], B["C"]), first_diff(A["r"], B["r"]), first_diff(A["g"], B["g"])] + \
                 [first_diff(A["E"][p], B["E"][p]) for p in range(4)]
            row.append("; ".join("none" if f is None else str(f) for f in fd))
        else:
            row.append("-")
    print(f"| {L} | " + " | ".join(row) + " |")
