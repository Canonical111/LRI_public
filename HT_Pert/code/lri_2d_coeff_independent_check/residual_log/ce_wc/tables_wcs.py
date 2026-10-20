#!/usr/bin/env python3
"""Tables for scheme Wcs (Wc + slice-resolved eps^3 self-window, WINDOW_SPEC Sec. 2.5a) next to Wc.
usage: python3 tables_wcs.py out_wcs out_local [out_diag]"""
import glob
import json
import os
import sys
from fractions import Fraction as Fr


def load_dirs(ds):
    out = {}
    for d in ds:
        for f in sorted(glob.glob(os.path.join(d, "*.json"))):
            j = json.load(open(f))
            L = j["meta"]["args"]["L"]
            for s, v in j["schemes"].items():
                if s.startswith("_"):
                    continue
                out.setdefault(s, {}).setdefault(L, {}).update({k: x for k, x in v["values"].items() if x is not None})
    return out


def resid(v, dn, n):
    a = int(dn[-1])
    prim = 1 if dn.startswith("odd") else 2
    k = f"Ed|{dn}|{n}"
    if k not in v or f"E|{prim}|{n}" not in v:
        return None
    return float(Fr(v[k]) - Fr(v[f"E|{prim}|{n}"]) - (2 * a if n == 0 else 0))


def main():
    data = load_dirs(sys.argv[1:])
    Ls = sorted(set(data.get("Wcs", {})))
    print("# C_n: Wcs vs Wc (C_0..C_4 identical; C_5 shift = delta^(3)(L) S(L), nm_legw.py)")
    for L in Ls:
        s, w = data["Wcs"][L], data.get("Wc", {}).get(L)
        row = f"L={L:2d}  C4={float(Fr(s['C|4'])):+.9f}"
        if w:
            row += f" (Wc {float(Fr(w['C|4'])):+.9f})"
        for n in (5, 6, 7, 8):
            row += f"  C{n}={float(Fr(s[f'C|{n}'])):+.6f}"
            if w and f"C|{n}" in w:
                row += f" (Wc {float(Fr(w[f'C|{n}'])):+.6f})"
        print(row)
    for dn in ("odd1", "odd2", "odd3", "even1", "even2"):
        print(f"# {dn}: R_2, R_3, R_4  Wcs  [Wc]")
        for L in Ls:
            s, w = data["Wcs"][L], data.get("Wc", {}).get(L, {})
            r = [resid(s, dn, n) for n in (2, 3, 4)]
            if r[0] is None:
                continue
            rw = [resid(w, dn, n) for n in (2, 3, 4)] if w else [None] * 3
            fmt = lambda x: "    n/a   " if x is None else f"{x:+.6f}"
            print(f"  L={L:2d}  R2={fmt(r[0])} R3={fmt(r[1])} R4={fmt(r[2])}   [R3={fmt(rw[1])} R4={fmt(rw[2])}]")


if __name__ == "__main__":
    main()
