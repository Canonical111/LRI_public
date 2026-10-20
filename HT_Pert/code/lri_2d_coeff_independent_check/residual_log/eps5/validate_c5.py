#!/usr/bin/env python3
"""Validation of the production C_n(L) (prod5.py npz) and of the scheme shifts (delta5.py npz):
  raw, consistent  vs ../rs_exact_results (exact, L <= 18) and the package outputs ../../../results/*/d8 (L <= 34);
  zeromode         vs ../zeromode_results (exact, L <= 18);
  W2, W3m, W3e, Wb vs ../brute/brute_W5_L*.json (exact rationals, L <= 8).
usage: python3 validate_c5.py ../results/eps5/c5_L160.npz ../results/eps5/dC5_L400.npz"""
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RL = os.path.join(HERE, "..")
PKG = os.path.normpath(os.path.join(RL, "..", "..", "results"))


def rel(a, b):
    return abs(a - b) / max(1.0, abs(b))


def main():
    prod = np.load(sys.argv[1])
    sh = np.load(sys.argv[2]) if len(sys.argv) > 2 else None
    lines = []
    worst = {}

    def upd(key, e):
        worst[key] = max(worst.get(key, 0.0), e)

    # rs_exact (exact rationals as floats)
    for L in range(2, 19, 2):
        i = L // 2
        for scheme, f in (("raw", f"rs_exact_results/raw_L{L}.json"), ("consistent", f"rs_exact_results/consistent_L{L}.json"),
                          ("zeromode", f"zeromode_results/zeromode_L{L}.json")):
            d = json.load(open(os.path.join(RL, f)))
            for n in range(2, 6):
                upd((scheme, "rs_exact/zeromode_exact", f"C{n}"), rel(prod[f"{scheme}_C{n}"][i], d["C_float"][n]))
            if sh is not None and scheme != "raw":
                upd((scheme, "shift vs exact", "C5"), rel(prod["raw_C5"][i] + sh[f"{scheme}_dC5"][i], d["C_float"][5]))
    # package outputs
    for f in sorted(glob.glob(os.path.join(PKG, "*", "d8", "*_L*.json"))):
        p = json.load(open(f))["payload"]
        sc, L = p["configuration"]["scheme"], p["configuration"]["L"]
        if sc not in ("raw", "consistent"):
            continue
        i = L // 2
        if i >= len(prod["L"]):
            continue
        C = p["result"]["C"]
        for n in range(2, 6):
            e = rel(prod[f"{sc}_C{n}"][i], C[n])
            upd((sc, "package d8 (L<=34)", f"C{n}"), e)
        lines.append(f"package {os.path.basename(os.path.dirname(os.path.dirname(f))):22s} {sc:10s} L={L:2d} "
                     f"C5 pkg={C[5]:+.12f} ours={prod[f'{sc}_C5'][i]:+.12f} diff={prod[f'{sc}_C5'][i] - C[5]:+.1e}")
    # brute force W variants
    for f in sorted(glob.glob(os.path.join(RL, "brute", "brute_W5_L*.json"))):
        b = json.load(open(f))
        L = b["L"]
        i = L // 2
        for v in ("W2", "W3m", "W3e", "Wb"):
            if v not in b:
                continue
            if sh is not None:
                upd((v, "brute_W5 (raw+shift)", "C5"), rel(prod["raw_C5"][i] + sh[f"{v}_dC5"][i], b[v]["C_float"][5]))
            if f"{v}_C5" in prod.files and v != "Wb":
                upd((v, "brute_W5 (prod5)", "C5"), rel(prod[f"{v}_C5"][i], b[v]["C_float"][5]))
    lines.append("")
    for k in sorted(worst):
        lines.append(f"worst rel. deviation {k[0]:10s} vs {k[1]:24s} {k[2]}: {worst[k]:.1e}")
    if sh is not None:
        for s in ("consistent", "zeromode", "W2", "W3m", "W3e", "W3x", "Wb", "consistent2", "zeromode2", "Z2", "Zb"):
            if f"{s}_C5" in prod.files:
                n = len(prod["L"])
                d = np.max(np.abs(prod[f"{s}_C5"] - prod["raw_C5"] - sh[f"{s}_dC5"][:n]))
                lines.append(f"prod5 {s:10s} vs raw + delta5 shift, all L <= {2 * (n - 1)}: max |diff| = {d:.1e}")
    txt = "\n".join(lines)
    print(txt)
    open(os.path.join(RL, "results", "eps5", "validation_c5.txt"), "w").write(txt + "\n")


if __name__ == "__main__":
    main()
