#!/usr/bin/env python3
"""Regenerate data/HT_1d/s10_production/dconn_minus_raw_L46_72.csv from the production records.

The table was written on 2026-10-08 by the coordinating Claude Code session with an inline command; no script was kept.
This script reproduces it byte for byte (sha256 3105e037...): for every even L = 46..72,
    dC_k(L) = C_k(L) [dconn_L<L>_d8.json, complete Dconn window, S10 solver]  -  raw_k(L) [data.json 'raw'],  k = 6, 7, 8,
with raw_k(L) the HT raw coefficients of the C8 campaign (data/HT_1d/c8/extrapolation/data.json, sha256 ccc77dfa...),
written as 'L,dC6,dC7,dC8' with Python's shortest round-trip float repr.
usage: python3 public/make_dconn_minus_raw.py [--data ../../data/HT_1d] [--out FILE]   (default: stdout)"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
LS = range(46, 73, 2)


def table(data):
    raw = json.load(open(os.path.join(data, "c8", "extrapolation", "data.json")))["raw"]
    out = "L,dC6,dC7,dC8\n"
    for L in LS:
        C = json.load(open(os.path.join(data, "s10_production", f"dconn_L{L}_d8.json")))["C"]
        r = raw[str(L)]
        out += "%d,%s\n" % (L, ",".join(repr(C[k] - r[k]) for k in (6, 7, 8)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(PKG, "..", "..", "data", "HT_1d"))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    t = table(a.data)
    if a.out:
        open(a.out, "w").write(t)
    else:
        sys.stdout.write(t)


if __name__ == "__main__":
    main()
