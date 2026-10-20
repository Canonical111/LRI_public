#!/usr/bin/env python3
"""Replay the d = 2 independent-solver check from its shipped outputs (no rerun).

Run from HT/code/lri_2d_window_indep (make -f public.mk replay). Inputs, relative to that folder:
  ../../results/HT_2d/independent_check/out_sym/*.json   outputs of run_check.py (symmetry jobs 571680, 571811)
  ../../data/HT_2d/prod1/chains/x<ds>/L<N>_z<nz>.json    the production records they were compared with

Each output embeds the production values it was compared with and the production record_sha256; the replay checks that
binding against the shipped records and recomputes every agreement figure. Exit 1 on any FAIL.
Result names (i2.*) are those of results_map.md and the note.
"""
import argparse
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parent.parent
ROWS, NOTES = [], []


def check(name, ok, value, expected, tol):
    ROWS.append((name, "PASS" if ok else "FAIL", value, expected, tol))


def sig2(v):
    return float(f"{v:.2g}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ht", default=str(PKG.parent.parent), help="the HT folder (default: ../..)")
    a = ap.parse_args()
    HT = Path(a.ht).resolve()
    OUT = HT / "results" / "HT_2d" / "independent_check" / "out_sym"
    REC = HT / "data" / "HT_2d" / "prod1" / "chains"

    R = [json.load(open(p)) for p in sorted(glob.glob(str(OUT / "*.json")))]
    errs = glob.glob(str(OUT / "*.err"))
    nfix = sum(r["task"]["kind"] == "fixed" for r in R)
    check("i2.outputs", len(R) == 155 and not errs, f"{len(R)} outputs ({nfix} fixed, {len(R) - nfix} tune), "
          f"{len(errs)} failures", "155 (143 + 12), 0 failures", "exact")

    # binding to the production records
    nbind, bad = 0, []
    for r in R:
        t = r["task"]
        for nz, emb in r["records"].items():
            p = REC / f"x{t['x']}" / f"L{t['L']}_z{nz}.json"
            if not p.exists():
                bad.append(f"{t['id']} nz{nz}: no shipped record")
                continue
            rec = json.loads(p.read_bytes())
            same = (emb["record_sha256"] == rec["record_sha256"] and emb["Delta_thermal"] == rec["Delta_thermal"]
                    and emb["theta"] == rec["theta"] and emb["even"] == rec["even_gaps"] and emb["odd"] == rec["odd_gaps"])
            if same:
                nbind += 1
            else:
                bad.append(f"{t['id']} nz{nz}: differs from the shipped record")
    check("i2.bind", not bad, f"{nbind} comparisons bound", "every embedded production value == shipped record",
          "record_sha256, theta, gaps exact")
    NOTES.extend(bad[:5])

    # agreement at fixed (production) couplings
    dE = defaultdict(float)
    lev = defaultdict(float)
    for r in R:
        t, o = r["task"], r["indep"]
        rec = r["records"].get("16")
        if t["kind"] != "fixed" or rec is None:
            continue
        key = (t["L"], t["K"][0] >= 32)
        d = abs(o["even"][1] - rec["Delta_thermal"])
        lv = max(np.abs(np.array(o["even"][:5]) - np.array(rec["even"][:5])).max(),
                 np.abs(np.array(o["odd"][:5]) - np.array(rec["odd"][:5])).max(),
                 max(abs(o["Ev"][k] - v) for k, v in rec["Ev"].items()))
        dE[key] = max(dE[key], d)
        lev[key] = max(lev[key], lv)
    w1216 = max(dE[(12, True)], dE[(16, True)])
    check("i2.dE.N12_16", sig2(w1216) <= 1.4e-12, w1216, "1.4e-12", "2 significant digits; K >= 32, every Delta_sigma")
    l1216 = max(lev[(12, True)], lev[(16, True)])
    check("i2.levels.N12_16", l1216 <= 1e-11, l1216, "<= 1e-11", "five even, five odd levels and E_v(M), K >= 32")
    check("i2.dE.N18", dE[(18, True)] <= 5e-12, dE[(18, True)], "<= 5e-12", "K >= 32, Delta_sigma <= 0.15")
    check("i2.dE.N20", dE[(20, True)] <= 5e-11, dE[(20, True)], "<= 5e-11", "K = 32, Delta_sigma <= 0.175")
    L22 = {float(r["task"]["x"]): r["indep"]["even"][1] - r["records"]["16"]["Delta_thermal"]
           for r in R if r["task"]["kind"] == "fixed" and r["task"]["L"] == 22}
    check("i2.dE.N22", sig2(L22.get(0.125, 1)) == 4.4e-10 and sig2(L22.get(0.126, 1)) == 4.0e-10,
          "; ".join(f"{x:g}: {v:+.3e}" for x, v in sorted(L22.items())), "4.4e-10 (0.125), 4.0e-10 (0.126)",
          "2 significant digits; K = 32")
    k24 = {L: dE[(L, False)] for L in (8, 10, 12, 14, 16, 18, 20) if (L, False) in dE}
    NOTES.append("K = 24 (not converged at strong coupling), max |dDelta_E| by N: "
                 + ", ".join(f"{L}: {v:.1e}" for L, v in sorted(k24.items())))

    # independent re-tuning from shifted seeds
    tune = defaultdict(float)
    for r in R:
        if r["task"]["kind"] == "tune":
            L = r["task"]["L"]
            tune[L] = max(tune[L], abs(r["indep"]["even"][1] - r["records"]["16"]["Delta_thermal"]))
    check("i2.retune.N8_12", max(tune[8], tune[12]) <= 1e-10, max(tune[8], tune[12]), "<= 1e-10 (9e-11)",
          "independent root from theta + (0.05, -0.05), K = 24")
    check("i2.retune.N16", tune[16] <= 4e-8, tune[16], "<= 4e-8 (3.6e-8 at 0.125, K = 24 limited)", "K = 24")

    w = max(len(r[0]) for r in ROWS)
    print(f"{'check':<{w}}  result  value  |  expected  |  tolerance")
    for name, res, val, expv, tol in ROWS:
        print(f"{name:<{w}}  {res:6}  {val if not isinstance(val, float) else f'{val:.6g}'}  |  {expv}  |  {tol}")
    for n in NOTES:
        print("NOTE", n)
    nfail = sum(r[1] == "FAIL" for r in ROWS)
    print(f"{len(ROWS) - nfail} PASS, {nfail} FAIL")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
