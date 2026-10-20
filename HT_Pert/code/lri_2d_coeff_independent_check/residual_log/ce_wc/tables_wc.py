#!/usr/bin/env python3
"""Tables from the exact CE runs of scheme Wc (outer-referenced auxiliary windows) and its diagnostics, next to the
complete_exact W results: C_n (n <= 8) and the descendant residuals R_n = [E_desc - E_prim - 2a]^(n).
usage: python3 tables_wc.py ce_wc/out_local  (directory with wcA_L*.json, wcD_L*.json, wc14_L14.json, wc16_L16.json)"""
import glob
import json
import os
import sys
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
CE = os.path.join(HERE, "..", "..", "complete_exact", "results")


def load_dir(d):
    out = {}
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        j = json.load(open(f))
        L = j["meta"]["args"]["L"]
        for s, v in j["schemes"].items():
            out.setdefault(s, {})[L] = v["values"]
    return out


def resid(v, dn):
    a = int(dn[-1])
    prim = 1 if dn.startswith("odd") else 2
    if f"Ed|{dn}|0" not in v:
        return None
    return [float(Fr(v[f"Ed|{dn}|{i}"]) - Fr(v[f"E|{prim}|{i}"]) - (2 * a if i == 0 else 0)) for i in range(9)]


def main():
    data = load_dir(sys.argv[1])
    # complete_exact W for comparison
    W = {}
    for f in glob.glob(os.path.join(CE, "complete_L*.json")):
        j = json.load(open(f))
        W[j["L"]] = j
    lines = ["# scheme Wc (WINDOW_SPEC 2026-10-09: auxiliary windows referenced to the outer cutoff) -- exact rationals",
             "# from the residual_log copy of complete_exact (ce_wc/); W = ../complete_exact (spec W)."]
    for s in sorted(data):
        Ls = sorted(data[s])
        lines.append(f"\n== {s}: C_n")
        for L in Ls:
            v = data[s][L]
            C = [float(Fr(v[f"C|{i}"])) for i in range(9)]
            lines.append(f"  L={L:2d} " + " ".join(f"C{n}={C[n]:+.10g}" for n in range(4, 9)))
        for dn in ("odd1", "odd2", "even1", "even2"):
            rows = []
            for L in Ls:
                R = resid(data[s][L], dn)
                if R is not None:
                    rows.append((L, R))
            if not rows:
                continue
            lines.append(f"-- {s} {dn}: R_2, R_3, R_4 by L")
            for L, R in rows:
                lines.append(f"  L={L:2d}  R2={R[2]:+.6f}  R3={R[3]:+.6f}  R4={R[4]:+.6f}")
    txt = "\n".join(lines)
    print(txt)
    open(os.path.join(HERE, "..", "results", "eps5", "ce_wc_tables.txt"), "w").write(txt + "\n")


if __name__ == "__main__":
    main()
