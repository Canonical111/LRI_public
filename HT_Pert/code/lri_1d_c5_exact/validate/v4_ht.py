#!/usr/bin/env python3
"""A4: diagram-sum C2..C5 vs the HT campaign data (float64) and Dconn C5 vs the S10 full-model data (PLAN A4).
  raw   : inputs/ht_data.json "raw" (C0..C8, even Lambda = 2..92) and "thermal_d7" (C0..C7, even Lambda = 2..118),
          both the plain truncated Hamiltonian.  Compared: the quarter-grid C2..C5 at cut4 = 4 Lambda, and the even-grid
          fit target even_C5raw.  Gate |Delta C5| <= 1e-9 (expected <= 3e-11; above 1e-10 the line is marked
          INVESTIGATE), |Delta C2|, |Delta C3|, |Delta C4| <= 1e-11.
  Dconn : even_C5Dconn vs inputs/s10_dconn_C5.json (S10 full-model Dconn C5, even Lambda = 2..72): |Delta| <= 1e-9.
  npz   : quarter grid cut4 = 0..4 Lmax, even grid even_L = 2, 4, .., Lmax, and even_C5raw == C5[4 Lambda] (<= 1e-12
          absolute at every even Lambda, so that the raw fit target is the validated array).
Every reference cutoff must be covered by the result (else FAIL; A4 is run on a result with Lmax >= 118); the
reference grids are asserted; a non-finite value fails.  (raw and thermal_d7 themselves differ by up to 2.1e-11 in C5
and 1.0e-12 in C4.)
usage: python3 validate/v4_ht.py results/<sha12>/c5_1d_L160.npz"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
HT = os.path.join(HERE, "..", "inputs", "ht_data.json")            # copies, sha256 in inputs/MANIFEST.txt
S10 = os.path.join(HERE, "..", "inputs", "s10_dconn_C5.json")
REF_GRID = {"raw": list(range(2, 93, 2)), "thermal_d7": list(range(2, 119, 2)), "s10": list(range(2, 73, 2))}
TOL = {2: 1e-11, 3: 1e-11, 4: 1e-11, 5: 1e-9}
TOL_S10 = 1e-9
FLAG_C5 = 1e-10


def dev(v, ref):
    """|v - ref|; inf if either side is non-finite."""
    v, ref = float(v), float(ref)
    return abs(v - ref) if math.isfinite(v) and math.isfinite(ref) else math.inf


def upd(worst, key, d, L):
    """keep the largest deviation and its cutoff (the first cutoff while everything is 0)."""
    if worst[key][1] is None or not d <= worst[key][0]:
        worst[key] = (d, L)


def main():
    path = sys.argv[1]
    d = np.load(path)
    ht = json.load(open(HT))
    s10 = json.load(open(S10))
    ok = True
    nc = len(d["cut4"])
    Lmax = (nc - 1) // 4
    if nc != 4 * Lmax + 1 or not np.array_equal(d["cut4"], np.arange(nc)) \
            or not np.array_equal(d["even_L"], np.arange(2, Lmax + 1, 2)):
        print("FAIL: result grid is not cut4 = 0..4 Lmax with even_L = 2..Lmax")
        sys.exit(1)
    eL = d["even_L"].tolist()
    ev_raw = dict(zip(eL, d["even_C5raw"].tolist()))
    ev_dc = dict(zip(eL, d["even_C5Dconn"].tolist()))
    print(f"# {path}: Lmax = {Lmax}")

    # npz consistency: the raw fit target is the quarter-grid C5 at integer even cutoffs
    worst = {"cons": (0.0, None)}
    for L in eL:
        upd(worst, "cons", dev(ev_raw[L], d["C5"][4 * L]), L)
    print(f"even_C5raw vs C5[4L] (L = 2..{Lmax}): max |d| {worst['cons'][0]:.1e} at L={worst['cons'][1]}")
    ok &= bool(worst["cons"][0] <= 1e-12)

    for src in ("raw", "thermal_d7"):
        Ls = sorted(int(k) for k in ht[src])
        if Ls != REF_GRID[src]:
            print(f"FAIL: unexpected {src} reference grid"); ok = False; continue
        if 4 * Ls[-1] >= nc:
            print(f"{src}: result does not cover L = {Ls[-1]} (Lmax {Lmax})"); ok = False
        Ls = [L for L in Ls if 4 * L < nc]
        if not Ls:
            continue
        worst = {k: (0.0, None) for k in (2, 3, 4, 5, "even5")}
        for L in Ls:
            ref = ht[src][str(L)]
            for k in (2, 3, 4, 5):
                upd(worst, k, dev(d[f"C{k}"][4 * L], ref[k]), L)
            upd(worst, "even5", dev(ev_raw[L], ref[5]), L)
        good = all(worst[k][0] <= TOL[k] for k in (2, 3, 4, 5)) and worst["even5"][0] <= TOL[5]
        flag = max(worst[5][0], worst["even5"][0]) > FLAG_C5
        print(f"{src:10s} L={Ls[0]}..{Ls[-1]} ({len(Ls)} cutoffs): "
              + "  ".join(f"C{k}: max|d| {worst[k][0]:.1e} at L={worst[k][1]}" for k in (2, 3, 4, 5))
              + f"  even_C5raw: max|d| {worst['even5'][0]:.1e} at L={worst['even5'][1]}"
              + ("  INVESTIGATE (> 1e-10)" if flag else ""))
        ok &= bool(good)

    Ls = sorted(int(k) for k in s10)
    if Ls != REF_GRID["s10"]:
        print("FAIL: unexpected s10_dconn_C5 reference grid"); ok = False
    else:
        if Ls[-1] > Lmax:
            print(f"s10: result does not cover L = {Ls[-1]} (Lmax {Lmax})"); ok = False
        Ls = [L for L in Ls if L <= Lmax]
        if Ls:
            worst = {"dc": (0.0, None)}
            for L in Ls:
                upd(worst, "dc", dev(ev_dc[L], s10[str(L)]["C5"]), L)
            print(f"{'s10 Dconn':10s} L={Ls[0]}..{Ls[-1]} ({len(Ls)} cutoffs): even_C5Dconn max|d| "
                  f"{worst['dc'][0]:.1e} at L={worst['dc'][1]}")
            ok &= bool(worst["dc"][0] <= TOL_S10)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
