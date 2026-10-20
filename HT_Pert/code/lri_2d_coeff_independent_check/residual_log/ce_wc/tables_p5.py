#!/usr/bin/env python3
"""Phase 5 tables (README Sec. 12): the eps^4 leg window calibrated on a chi line (scheme Wcs4chi, ce_wc scheme key
'Wcs4' in out_wcs4c/) next to Wc, Wcs and the proxy transcription Wcs4 (out_wcs4/).  Exact rationals; floats printed.
  * invariance: C_0..C_5, r_1..r_4, g_1..g_4 and R_2, R_3 of every descendant identical to Wcs (exact comparison);
  * R_4, R_5 of chi_11, chi_22, chi_33 and of the phi^2 descendants; budget-free R_4 from ../results/tag/;
  * C_6..C_8.
usage: python3 tables_p5.py   (run from residual_log/ce_wc)"""
import glob
import json
import os
import sys
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import delta4chi as d4c  # noqa: E402


def load(d, scheme):
    out = {}
    for f in glob.glob(os.path.join(HERE, d, "*.json")):
        j = json.load(open(f))
        if scheme in j.get("schemes", {}):
            out.setdefault(j["meta"]["args"]["L"], {}).update(
                {k: v for k, v in j["schemes"][scheme]["values"].items() if v is not None})
    return out


def R(v, dn, n):
    a = int(dn[-1])
    prim = 1 if dn.startswith("odd") else 2
    k = f"Ed|{dn}|{n}"
    if v is None or v.get(k) is None or v.get(f"E|{prim}|{n}") is None:
        return None
    return Fr(v[k]) - Fr(v[f"E|{prim}|{n}"]) - (2 * a if n == 0 else 0)


def f(x, w=10, p=6):
    return " " * (w - 3) + "n/a" if x is None else f"{float(x):+{w}.{p}f}"


def main():
    S = {"Wc": load("out_local", "Wc"), "Wcs": load("out_wcs", "Wcs"), "Wcs4": load("out_wcs4", "Wcs4"),
         "Wcs4chi": load("out_wcs4c", "Wcs4"), "B": load("out_wcs4x", "Wcs4X"), "Ball": load("out_wcs4x", "Wcs4Xall")}
    for L, v in load("out_diag", "Wc").items():          # odd3 of Wc lives in out_diag
        S["Wc"].setdefault(L, {}).update({k: x for k, x in v.items() if k not in S["Wc"].get(L, {})})
    Ls = sorted(S["Wcs4chi"])
    for name in ("Wcs4chi", "B", "Ball"):
      print(f"# invariance of {name} against Wcs (exact): C_0..C_5, r_1..r_4, g_1..g_4, R_2, R_3 (all descendants)")
      for L in sorted(S[name]):
        a, b = S[name][L], S["Wcs"].get(L)
        if b is None:
            continue
        keys = [f"C|{n}" for n in range(6)] + [f"r|{n}" for n in range(1, 5)] + [f"g|{n}" for n in range(1, 5)]
        keys += [k for k in a if k.startswith("Ed|") and int(k.split("|")[2]) <= 3]
        keys += [f"E|{p}|{n}" for p in range(4) for n in range(5)]
        diff = [k for k in keys if k in b and Fr(a[k]) != Fr(b[k])]
        r5 = f"r_5: {float(Fr(a['r|5'])):+.6f} [Wcs {float(Fr(b['r|5'])):+.6f}]  g_5: {float(Fr(a['g|5'])):+.6f} " \
             f"[Wcs {float(Fr(b['g|5'])):+.6f}]" if "r|5" in a and "r|5" in b else ""
        print(f"    L={L:2d}: {len([k for k in keys if k in b])} quantities compared, {len(diff)} differ {diff[:4]};  {r5}")
    for dn in ("odd1", "odd2", "odd3", "even1", "even2"):
        a_ = int(dn[-1])
        print(f"# {dn}: R_4 in A (leg only) | B (cc) | B (all) | Wcs4 (proxy) | Wcs (= Wc for odd) | budget-free;"
              f"  R_5 A | B(cc) | B(all) [Wcs]")
        for L in Ls:
            v = S["Wcs4chi"][L]
            r4 = R(v, dn, 4)
            if r4 is None:
                continue
            bf = d4c.bf_R4(L, a_) if dn.startswith("odd") else None
            print(f"  L={L:2d}  {f(r4)} | {f(R(S['B'].get(L), dn, 4))} | {f(R(S['Ball'].get(L), dn, 4))} | "
                  f"{f(R(S['Wcs4'].get(L), dn, 4))} | {f(R(S['Wcs'].get(L), dn, 4))} | {f(bf)}"
                  f"   R_5 {f(R(v, dn, 5))} | {f(R(S['B'].get(L), dn, 5))} | {f(R(S['Ball'].get(L), dn, 5))} "
                  f"[{f(R(S['Wcs'].get(L), dn, 5))}]")
    print("# C_6, C_7, C_8:  Wc | Wcs | Wcs4 (proxy) | A (leg only) | B (cc) | B (all)")
    for L in sorted(set(S["Wc"]) | set(S["Wcs"])):
        row = f"  L={L:2d}"
        for n in (6, 7, 8):
            vals = [S[k].get(L, {}).get(f"C|{n}") for k in ("Wc", "Wcs", "Wcs4", "Wcs4chi", "B", "Ball")]
            row += "   C" + str(n) + ": " + " | ".join("n/a" if x is None else f"{float(Fr(x)):.6f}" for x in vals)
        print(row)


if __name__ == "__main__":
    main()
