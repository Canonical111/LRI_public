#!/usr/bin/env python3
"""Regression: ce_run.py raw / consistent / zeromode results vs ../rs_exact/results and ../zeromode_exact/results
(exact string equality of C, r, g, E_p; zeromode also every E_z(l) in the oracle table, consistent the vacua).
usage: python3 compare_regression.py out.json [more.json ...]"""
import json, os, sys
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
RS = os.path.join(HERE, "..", "rs_exact", "results")
ZM = os.path.join(HERE, "..", "zeromode_exact", "results")
ZMRAW = os.path.join(HERE, "..", "zeromode_exact", "raw_out")


def load_ref(scheme, L):
    if scheme in ("raw", "consistent"):
        f = os.path.join(RS, f"{scheme}_L{L}.json")
        if not os.path.exists(f):
            return None
        d = json.load(open(f))
        out = {}
        for k in ("C", "r", "g"):
            for i, v in enumerate(d[k]):
                out[f"{k}|{i}"] = v
        for p, row in enumerate(d["E"]):
            for i, v in enumerate(row):
                out[f"E|{p}|{i}"] = v
        if scheme == "consistent":
            for l, row in d["vacua"].items():
                if int(l) == L:
                    continue
                for i, v in enumerate(row):
                    out[f"Ez|0,{l}|{i}"] = v
        return out
    if scheme == "zeromode":
        f = os.path.join(ZM, f"zeromode_L{L}.json")
        if os.path.exists(f):
            d = json.load(open(f))
            out = {}
            for k in ("C", "r", "g"):
                for i, v in enumerate(d[k]):
                    out[f"{k}|{i}"] = v
            for p, row in enumerate(d["E"]):
                for i, v in enumerate(row):
                    out[f"E|{p}|{i}"] = v
            for zl, row in d["E_z"].items():
                z, l = map(int, zl.split(","))
                if l == L and z <= 3:
                    continue
                for i, v in enumerate(row):
                    out[f"Ez|{zl}|{i}"] = v
            return out
        f = os.path.join(ZMRAW, f"zm_L{L}.json")
        if os.path.exists(f):
            d = json.load(open(f))["variants"]["zeromode"]["values"]
            return {k.replace("Ez|", "Ez|"): v for k, v in d.items()}
    return None


def main():
    worst = 0
    for fn in sys.argv[1:]:
        d = json.load(open(fn))
        L = d["meta"]["L"]
        for scheme, blk in d["schemes"].items():
            base = scheme.replace("_garbage", "")
            ref = load_ref(base, L)
            if ref is None:
                print(f"L={L} {scheme}: no reference")
                continue
            vals = blk["values"]
            nk, nbad = 0, 0
            for k, v in ref.items():
                if k not in vals:
                    continue
                nk += 1
                if Fr(vals[k]) != Fr(v):
                    nbad += 1
                    if nbad <= 5:
                        print(f"   MISMATCH L={L} {scheme} {k}: {vals[k]} vs {v}")
            print(f"L={L} {scheme}: {nk} quantities compared with reference, {nbad} mismatches; "
                  f"reconstruction failures {len(blk['bad'])}")
            worst = max(worst, nbad)
    print("ALL IDENTICAL" if worst == 0 else "MISMATCHES FOUND")


if __name__ == "__main__":
    main()
