#!/usr/bin/env python3
"""Phase 5 (README Sec. 12): markdown tables from the exact results (ce_wc out_* dirs, results/tag/).
usage: python3 p5_report.py"""
import glob
import json
import os
import sys
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "ce_wc"))
import delta4chi as d4c  # noqa: E402
from tables_p5 import load, R  # noqa: E402

os.chdir(os.path.join(HERE, "ce_wc"))
S = {"Wc": load("out_local", "Wc"), "Wcs": load("out_wcs", "Wcs"), "Wcs4": load("out_wcs4", "Wcs4"),
     "A": load("out_wcs4c", "Wcs4"), "B": load("out_wcs4x", "Wcs4X"), "Ball": load("out_wcs4x", "Wcs4Xall")}
for L, v in load("out_diag", "Wc").items():
    S["Wc"].setdefault(L, {}).update({k: x for k, x in v.items() if k not in S["Wc"].get(L, {})})
os.chdir(HERE)


def fmt(x, p=4):
    return "" if x is None else f"{float(x):+.{p}f}"


# X table
print("| L | X_2(L,2) | X_3(L,2) | X_4(L,2) | X_4(L,4) | X_4(L,6) | X_4(L,L) |")
print("|---|---|---|---|---|---|---|")
for f in sorted(glob.glob(os.path.join(HERE, "results", "tag", "spec4_L*_a1.json")),
                key=lambda s: int(os.path.basename(s).split("_L")[1].split("_")[0])):
    j = json.load(open(f))
    L = j["L"]
    g = lambda N, n: Fr(j["spec"][f"{N}_{n}"]["X"]) if f"{N}_{n}" in j["spec"] else None
    print(f"| {L} | {fmt(g(2, 2))} | {fmt(g(2, 3))} | {fmt(g(2, 4))} | {fmt(g(4, 4))} | {fmt(g(6, 4))} | {fmt(g(L, 4), 3)} |")
print()
# delta table
print("| L | delta^(3) | delta4chi_A | X_4(L,2) | delta4chi (Wcs4chi) | proxy delta^(4) |")
print("|---|---|---|---|---|---|")
prox = {}
for f in glob.glob(os.path.join(HERE, "results", "tag", "tag4d4_L*_a1.json")):
    j = json.load(open(f))
    prox[j["L"]] = Fr(j["delta4"])
x4 = {}
for f in glob.glob(os.path.join(HERE, "ce_wc", "x4", "x4_L*.json")):
    L = int(os.path.basename(f)[4:-5])
    x4[L] = Fr(json.load(open(f))["2"])
for L, d3, d4, bf, rw in d4c.table(1):
    print(f"| {L} | {fmt(d3, 5)} | {fmt(d4, 5)} | {fmt(x4.get(L), 5)} | "
          f"{fmt(d4 - x4[L] / 4, 5) if L in x4 else ''} | {fmt(prox.get(L), 5)} |")
print()
# T4 table
for dn in ("odd1", "odd2", "odd3"):
    a = int(dn[-1])
    print(f"chi_{a}{a}:")
    print("| L | Wcs (= Wc) | Wcs4 (proxy) | A (leg only) | **Wcs4chi** | Wcs4chi 'all' | budget-free |")
    print("|---|---|---|---|---|---|---|")
    for L in sorted(set(S["A"]) | set(S["B"])):
        vals = [R(S[k].get(L), dn, 4) for k in ("Wcs", "Wcs4", "A", "B", "Ball")]
        if all(v is None for v in vals):
            continue
        print(f"| {L} | " + " | ".join(fmt(v) for v in vals) + f" | {fmt(d4c.bf_R4(L, a))} |")
    print()
print("phi^2 descendant (level 2) R_4:")
print("| L | Wcs | A | Wcs4chi | Wcs4chi 'all' |")
print("|---|---|---|---|---|")
for L in sorted(S["A"]):
    print(f"| {L} | " + " | ".join(fmt(R(S[k].get(L), 'even1', 4)) for k in ("Wcs", "A", "B", "Ball")) + " |")
print()
print("| L | Wc | Wcs | Wcs4 (proxy) | A | **Wcs4chi** | Wcs4chi 'all' |")
print("|---|---|---|---|---|---|---|")
for L in sorted(set(S["Wc"]) | set(S["Wcs"])):
    if L < 2:
        continue
    vals = [S[k].get(L, {}).get("C|6") for k in ("Wc", "Wcs", "Wcs4", "A", "B", "Ball")]
    print(f"| {L} | " + " | ".join("" if x is None else f"{float(Fr(x)):.5f}" for x in vals) + " |")
print()
print("R_5(chi_11):", ", ".join(f"{L}: {float(R(S['A'][L], 'odd1', 5)):.4f}" for L in sorted(S["A"])))
