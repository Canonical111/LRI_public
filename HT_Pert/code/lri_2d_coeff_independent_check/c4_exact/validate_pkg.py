#!/usr/bin/env python3
"""Compare c4_compute with the production package (float64) for L = 2..34, raw and consistent:
C_2, C_3, C_4, r_2, r_3, g_2, g_3.  Also compare the exact raw->consistent shift Delta C_4 with
../continuum (zero_mode_window.csv column dC4_vacuum) and the zero-mode window shift dC4_zm.
usage: python3 validate_pkg.py [--Lmax 34]"""
import argparse
import csv
import glob
import json
import os

import numpy as np

import c4_compute as cc

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..", "..", "results")
CONT = os.path.join(HERE, "..", "continuum")


def load_pkg():
    out = {}
    for fn in glob.glob(os.path.join(PKG, "*", "d8", "*_L*.json")):
        base = os.path.basename(fn)[:-5]
        scheme, Ls = base.rsplit("_L", 1)
        with open(fn) as fh:
            d = json.load(fh)["payload"]["result"]
        out[(scheme, int(Ls))] = d
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, default=34)
    args = ap.parse_args()
    res = cc.compute(args.Lmax, verbose=False)
    pkg = load_pkg()
    worst = {}
    print(f"{'L':>3} {'C2':>8} {'C3':>8} {'C4raw':>8} {'C4cons':>8} {'r3':>8} {'g3':>8} | C4raw            C4cons")
    for i, L in enumerate(res["L"]):
        L = int(L)
        if ("raw", L) not in pkg:
            continue
        pr, pc = pkg[("raw", L)], pkg.get(("consistent", L))
        row = {}
        for k, mine, ref in [("C2", res["C2"][i], pr["C"][2]), ("C3", res["C3"][i], pr["C"][3]),
                             ("C4raw", res["C4raw"][i], pr["C"][4]), ("r3", res["r3"][i], pr["r"][3]),
                             ("g3", res["g3"][i], pr["g"][3])] + (
                [("C4cons", res["C4cons"][i], pc["C"][4])] if pc else []):
            row[k] = abs(mine - ref) / abs(ref)
            worst[k] = max(worst.get(k, 0), row[k])
        print(f"{L:3d} " + " ".join(f"{row.get(k, float('nan')):8.1e}" for k in
                                    ["C2", "C3", "C4raw", "C4cons", "r3", "g3"])
              + f" | {res['C4raw'][i]:.13f} {res['C4cons'][i]:.13f}")
    print("worst relative deviations vs package:", {k: f"{v:.1e}" for k, v in worst.items()})
    # Delta C4 (vacuum window) and zero-mode window shift vs continuum/zero_mode_window.csv
    with open(os.path.join(CONT, "zero_mode_window.csv")) as fh:
        zw = {int(r["L"]): r for r in csv.DictReader(fh)}
    with open(os.path.join(CONT, "zm_corrected_C4.csv")) as fh:
        zc = {int(r["L"]): r for r in csv.DictReader(fh)}
    for i, L in enumerate(res["L"]):
        L = int(L)
        dcons = res["C4cons"][i] - res["C4raw"][i]
        dcorr = res["C4corr"][i] - res["C4cons"][i]
        if L in zw:
            print(f"L={L}: Delta C4 (cons-raw) = {dcons:.15f}  continuum {float(zw[L]['dC4_vacuum']):.15f}"
                  f"  diff {dcons - float(zw[L]['dC4_vacuum']):+.1e}; corr-cons = {dcorr:.15f} continuum dC4_zm "
                  f"{float(zw[L]['dC4_zm']):.15f} diff {dcorr - float(zw[L]['dC4_zm']):+.1e}")
        if L in zc and L not in zw:
            print(f"L={L}: corr-cons = {dcorr:.15f}  continuum dC4_zm {float(zc[L]['dC4_zm']):.15f}"
                  f"  diff {dcorr - float(zc[L]['dC4_zm']):+.1e}")


if __name__ == "__main__":
    main()
