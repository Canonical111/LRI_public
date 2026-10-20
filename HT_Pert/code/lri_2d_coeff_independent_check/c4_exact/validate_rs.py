#!/usr/bin/env python3
"""Compare c4_compute (diagram sums) with the exact rationals of ../rs_exact/results (L = 0..18).

Checks, per L: r2, g2, r3, g3, C2, C3 (raw), C4 raw and consistent, and in --full mode also the individual
fourth-order energies X4_p = E_p^(4) - 2p r4 - p(p-1)/2 g4 (raw) and the vacuum series E_v^(2)(l).
usage: python3 validate_rs.py [--full] [--Lmax 18]"""
import argparse
import json
import os
from fractions import Fraction as Fr

import numpy as np

import c4_compute as cc

HERE = os.path.dirname(os.path.abspath(__file__))
RS = os.path.join(HERE, "..", "rs_exact", "results")


def load(scheme, L):
    fn = os.path.join(RS, f"{scheme}_L{L}.json")
    if not os.path.exists(fn):
        return None
    with open(fn) as fh:
        d = json.load(fh)
    F = lambda s: Fr(s)
    return dict(C=[F(c) for c in d["C"]], r=[F(c) for c in d["r"]], g=[F(c) for c in d["g"]],
                E=[[F(c) for c in row] for row in d["E"]], vac=d.get("vacua"))


def rel(a, b):
    b = float(b)
    return abs(a - b) / max(abs(b), 1e-300)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, default=18)
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()
    res = cc.compute(args.Lmax, full=args.full, verbose=False)
    worst = {}

    def upd(k, v):
        worst[k] = max(worst.get(k, 0.0), v)

    print(f"{'L':>3} {'r2':>8} {'g2':>8} {'r3':>8} {'g3':>8} {'C2':>8} {'C3':>8} {'C4raw':>8} {'C4cons':>8}"
          + (f" {'X4_p':>8} {'Ev2':>8}" if args.full else ""))
    for i, L in enumerate(res["L"]):
        raw = load("raw", int(L))
        con = load("consistent", int(L))
        if raw is None:
            continue
        row = dict(r2=rel(res["r2"][i], raw["r"][2]), g2=rel(res["g2"][i], raw["g"][2]),
                   r3=rel(res["r3"][i], raw["r"][3]), g3=rel(res["g3"][i], raw["g"][3]),
                   C2=rel(res["C2"][i], raw["C"][2]), C3=rel(res["C3"][i], raw["C"][3]),
                   C4raw=rel(res["C4raw"][i], raw["C"][4]))
        row["C4cons"] = rel(res["C4cons"][i], con["C"][4]) if con else float("nan")
        line = f"{int(L):3d} " + " ".join(f"{row[k]:8.1e}" for k in
                                         ["r2", "g2", "r3", "g3", "C2", "C3", "C4raw", "C4cons"])
        if args.full:
            x = 0.0
            for p in range(4):
                X4ex = raw["E"][p][4] - 2 * p * raw["r"][4] - Fr(p * (p - 1), 2) * raw["g"][4]
                x = max(x, rel(res["X4"][p][i], X4ex))
            row["X4"] = x
            ev = 0.0
            for l in range(0, int(L) + 1, 2):
                ex = Fr(-(l + 2) * (l + 4), 864)
                ev = max(ev, rel(res["Ev2"][l // 2], ex))
            row["Ev2"] = ev
            line += f" {row['X4']:8.1e} {row['Ev2']:8.1e}"
        for k, v in row.items():
            upd(k, v)
        print(line)
    print("worst relative deviations:", {k: f"{v:.1e}" for k, v in worst.items()})


if __name__ == "__main__":
    main()
