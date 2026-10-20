#!/usr/bin/env python3
"""Replay every d = 2 finite-coupling HT number of the paper and the HT note from the shipped records (no production rerun).

Run from HT/code/lri_2d_window_hpc (make -f public.mk replay). Inputs, relative to that folder:
  ../../data/HT_2d/prod1/chains/<chain>/L<N>_z<nz>.json   production records (self-hashed, verbatim)
  ../../results/HT_2d/prod1/{points,nested}.csv           tables collected from them (cluster/expanse/collect.py)
  ../../results/HT_2d/prod1/largest_N.csv                 Delta_E at the largest cutoff per Delta_sigma (Fig. cmp2d3d, Table num2)
  ../../results/HT_2d/valley_N24/prod_x*_L24_t*.json      the N = 24 valley scan (public/scan_valley.py)
  ../../data/HT_2d/pert_crosscheck/consistent_C0_C8.csv   consistent-scheme C0..C8(N) extract (perturbative package)

Prints one PASS/FAIL row per check and exits 1 on any FAIL. Result names (d2.*) are those of results_map.md and the note.
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG / "code"))
from ht2d import hpc  # noqa: E402  (stdlib-only at import time: digest, validate_record, source_hash)

ROWS = []
NOTES = []


def check(name, ok, value, expected, tol):
    ROWS.append((name, "PASS" if ok else "FAIL", value, expected, tol))


def sig2(v):
    """v rounded to two significant digits."""
    return float(f"{v:.2g}")


def fmt(v):
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def load_records(root):
    """All final records chains/<chain>/L<N>_z<nz>.json (checkpoints, claims and logs are not records)."""
    recs = {}
    for p in sorted(glob.glob(str(root / "chains" / "*" / "*.json"))):
        m = re.search(r"/([^/]+)/L(\d+)_z(\d+)\.json$", p)
        if m:
            recs[(m.group(1), int(m.group(2)), int(m.group(3)))] = (p, Path(p).read_bytes())
    return recs


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ht", default=str(PKG.parent.parent), help="the HT folder (default: ../..)")
    a = ap.parse_args()
    HT = Path(a.ht).resolve()
    DATA = HT / "data" / "HT_2d"
    RES = HT / "results" / "HT_2d"

    # ---------------------------------------------------------------- records
    recs = load_records(DATA / "prod1")
    check("d2.records.count", len(recs) == 348, len(recs), 348, "exact")
    src = hpc.source_hash()
    bad_gate, bad_src, bad_bytes = [], [], []
    R = {}
    for key, (p, raw) in recs.items():
        row = json.loads(raw)
        try:
            hpc.validate_record(row, row["request_digest"])  # checksum + tuning, eigenvector and window gates
        except ValueError as exc:
            bad_gate.append(f"{key}: {exc}")
        if row["configuration"]["source_sha256"] != src:
            bad_src.append(key)
        if raw != hpc.canonical_json(row) + b"\n":
            bad_bytes.append(key)
        R[key] = row
    check("d2.records.gates", not bad_gate, len(bad_gate), 0, "self-hash and production gates (hpc.validate_record)")
    check("d2.records.source", not bad_src, f"{len(R) - len(bad_src)}/{len(R)} bound to {src[:12]}", "all",
          "configuration.source_sha256 == source_hash() of this code")
    check("d2.records.canonical", not bad_bytes, len(bad_bytes), 0, "bytes == canonical_json(record)")
    for b in bad_gate[:5]:
        NOTES.append("gate: " + b)

    # ------------------------------------------------- collected tables (points.csv, nested.csv)
    P = list(csv.DictReader(open(RES / "prod1" / "points.csv")))
    mism = 0
    for r in P:
        rec = R.get((r["chain"], int(r["L"]), int(r["nz"])))
        if rec is None:
            mism += 1
            continue
        same = (float(r["Delta_thermal"]) == rec["Delta_thermal"] and float(r["theta0"]) == rec["theta"][0]
                and float(r["theta1"]) == rec["theta"][1] and float(r["tuning_residual"]) == rec["tuning_residual"]
                and json.loads(r["even_gaps"]) == rec["even_gaps"] and json.loads(r["odd_gaps"]) == rec["odd_gaps"])
        mism += not same
    check("d2.points", mism == 0 and len(P) == len(R), f"{len(P) - mism}/{len(P)} rows", f"{len(R)} rows",
          "exact (float repr)")

    d20, d12 = 0.0, 0.0
    for (c, L, nz), rec in R.items():
        if c.startswith("x") and nz in (12, 20) and (c, L, 16) in R:
            d = abs(rec["Delta_thermal"] - R[(c, L, 16)]["Delta_thermal"])
            if nz == 20:
                d20 = max(d20, d)
            else:
                d12 = max(d12, d)
    check("d2.nz.z20", d20 <= 1.0e-10, d20, "<= 1e-10 (9.4e-11)", "max |Delta(nz20)-Delta(nz16)|, all chains and N")
    check("d2.nz.z12", d12 <= 6e-7, d12, "<= 6e-7 (5.2e-7)", "max |Delta(nz12)-Delta(nz16)|")
    nested = list(csv.DictReader(open(RES / "prod1" / "nested.csv")))
    nmax = max(abs(float(r["dDelta_thermal"])) for r in nested if r["chain"].startswith("x") and r["nz"] == "20")
    check("d2.nested.csv", nmax == d20, nmax, d20, "exact: nested.csv nz20 column vs records")

    # ------------------------------------------------- finite-N behaviour (HT note; the paper prints only N_max since 827a27bf)
    seq = defaultdict(dict)
    for (c, L, nz), rec in R.items():
        if c.startswith("x") and nz == 16:
            seq[rec["delta"]][L] = rec["Delta_thermal"]
    X = sorted(seq)
    steps = {x: [seq[x][b] - seq[x][a] for a, b in zip(sorted(seq[x]), sorted(seq[x])[1:])] for x in X}
    Lmax = {x: max(seq[x]) for x in X}
    check("d2.chains", len(X) == 13, len(X), 13, "Delta_sigma = 0.125 ... 0.495")
    ok = all(Lmax[x] == (22 if x in (0.125, 0.126) else 24) for x in X) and all(min(seq[x]) == 8 for x in X)
    check("d2.Nmax", ok, f"N=8..{max(Lmax.values())}; 22 at 0.125, 0.126", "24 (22 at 0.125, 0.126)", "exact")

    conv = max(abs(steps[x][-1]) for x in X if x >= 0.45)
    check("d2.conv_step", conv <= 2.6e-6 and sig2(conv) >= 2.5e-6, conv, "<= 2.6e-6 (note)",
          "bound; largest step 2.54e-6 at 0.45")

    mono = [x for x in X if 0.25 <= x <= 0.4]
    mono_ok = all(all(s > 0 for s in steps[x]) for x in mono)
    check("d2.mono.rises", mono_ok and len(mono) == 4, "monotone rise at " + ",".join(f"{x:g}" for x in mono),
          "0.25-0.4 rise", "every step > 0")
    last = [steps[x][-1] for x in mono]
    check("d2.mono_steps", abs(min(last) - 0.6e-4) < 0.05e-4 and abs(max(last) - 4.3e-4) < 0.05e-4,
          f"{min(last):.3e} .. {max(last):.3e}", "(0.6-4.3)e-4", "2 significant digits")
    shrink = {}
    for x in mono:
        s = steps[x]
        g = (s[-1] / s[-5]) ** 0.25  # geometric mean of the last four step ratios
        shrink[x] = 100 * (1 - g)
    lo, hi = min(shrink.values()), max(shrink.values())
    check("d2.mono_shrink", round(lo) == 8 and round(hi) == 16, f"{lo:.1f} .. {hi:.1f} %", "8 to 16 % (note)",
          "nearest integer; 1 - geometric mean of the last four step ratios")

    conv_sh = {x: 100 * (1 - (steps[x][-1] / steps[x][-5]) ** 0.25) for x in X if x >= 0.45}
    check("d2.conv_shrink", all(17.5 <= v <= 22.5 for v in conv_sh.values()),
          ", ".join(f"{v:.1f}% ({x:g})" for x, v in sorted(conv_sh.items())), "18-22 % (note)", "rounded to integers")

    refs = {}
    for (c, L, nz), rec in R.items():
        if c.startswith("ref"):
            x = rec["delta"]
            refs[x] = rec["Delta_thermal"] - seq[x].get(L, math.nan)
    check("d2.refs", len(refs) == 3 and all(abs(v) <= 1e-9 for v in refs.values()),
          "; ".join(f"{x:g}: {v:+.1e}" for x, v in sorted(refs.items())), "<= 1e-9 (note)",
          "reference (32 moving states/parity, 256 oscillators) - nz16, N = 14")

    cond = {}
    for L in (12, 22):
        h = R.get(("x0.125", L, 16), {}).get("history", [])
        c = [e["jacobian_condition"] for e in h if isinstance(e.get("jacobian_condition"), (int, float))]
        cond[L] = c[-1] if c else math.nan
    check("d2.cond", round(cond[12]) == 84 and round(cond[22]) == 888, f"{cond[12]:.1f} (N=12), {cond[22]:.1f} (N=22)",
          "84, 888 (note)", "nearest integer; last Newton step of the record, Delta_sigma = 0.125")

    s02 = steps[0.2]
    check("d2.nonmono_0.2", any(s > 0 for s in s02) and any(s < 0 for s in s02),
          f"signs {''.join('+' if s > 0 else '-' for s in s02)}", "not monotone", "sign change")

    fall = [x for x in X if x <= 0.175]
    fall_ok = all(all(s < 0 for s in steps[x][1:]) for x in fall) and all(abs(steps[x][-1]) >= abs(steps[x][-2]) for x in fall)
    check("d2.fall", fall_ok, "falls from N=10 on; last step >= previous at " + ",".join(f"{x:g}" for x in fall),
          "0.125-0.175: falls, steps do not shrink", "signs and |last| >= |previous|")
    check("d2.fall_small", sig2(abs(steps[0.175][-1])) == 1.0e-3, abs(steps[0.175][-1]), "1.0e-3 (0.175, N 22->24)",
          "2 significant digits")
    check("d2.fall_large", sig2(abs(steps[0.125][-1])) == 2.0e-2, abs(steps[0.125][-1]), "2.0e-2 (0.125, N 20->22)",
          "2 significant digits")

    # ------------------------------------------------- Delta_E at the largest cutoff (comparison figure)
    F = list(csv.DictReader(open(RES / "prod1" / "largest_N.csv")))
    fig_ok = len(F) == 13 and all(float(r["Delta_E"]) == seq.get(float(r["Delta_sigma"]), {}).get(int(r["N"]))
                                  and int(r["N"]) == Lmax.get(float(r["Delta_sigma"])) for r in F)
    check("d2.largest_N", fig_ok, f"{len(F)} rows", "13 rows == records", "exact")
    # the HT column of the paper's Table tab:num2 (827a27bf): largest_N rounded once to five decimals, [..] at N = 22
    from decimal import ROUND_HALF_UP, Decimal
    NUM2 = {"0.125": "[0.94003]", "0.126": "[0.94568]", "0.135": "0.96203", "0.15": "0.99023", "0.175": "0.99972",
            "0.2": "0.99530", "0.25": "0.97771", "0.3": "0.96349", "0.35": "0.95782", "0.4": "0.96179",
            "0.45": "0.97528", "0.475": "0.98581", "0.495": "0.99678"}
    got = {}
    for r in F:
        v = str(Decimal(r["Delta_E"]).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP))
        got[r["Delta_sigma"]] = f"[{v}]" if r["N"] == "22" else v
    bad = [k for k in NUM2 if got.get(k) != NUM2[k]]
    check("d2.num2", len(got) == 13 and not bad, f"{13 - len(bad)}/13 cells" + (f"; differ at {','.join(bad)}" if bad else ""),
          "13 HT cells of Table num2", "exact after rounding to 5 decimals")

    # ------------------------------------------------- N = 24 valley scan (no root at 0.125, 0.126; fold)
    import numpy as np
    V = {}
    for p in sorted(glob.glob(str(RES / "valley_N24" / "prod_x*_L24_t*.json"))):
        d = json.load(open(p))
        rows = [r for r in d["rows"] if not r.get("summary")]
        summ = [r for r in d["rows"] if r.get("summary")]
        x = d["x"]
        for r in rows:  # f1, f2 recomputed from the stored energies
            f1 = r["E_odd"][0] - r["E_even"][0] - x
            f2 = r["E_odd"][1] - r["E_even"][0] - (2 - x)
            if abs(f1 - r["f1"]) > 1e-12 or abs(f2 - r["f2"]) > 1e-12:
                NOTES.append(f"valley {p}: stored f1/f2 differ from the energies")
        V.setdefault(x, []).append((summ[0]["theta0"], summ[0]["f1_on_curve"], summ[0]["f2"], rows[-1]["f1"]))
    check("d2.valley.files", sorted(V) == [0.125, 0.126] and all(len(v) == 6 for v in V.values()),
          {k: len(v) for k, v in V.items()}, "6 theta0 per Delta_sigma", "exact")
    best = {}
    for p in sorted(glob.glob(str(RES / "valley_N24" / "prod_x*_L24_t*.json"))):
        d = json.load(open(p))
        r0 = d["rows"][0]
        if r0["theta"][0] not in (12.5, 13.25, 14.3, 14.8, 15.5):
            best[d["x"]] = max(abs(r0["f1"]), abs(r0["f2"]))
    check("d2.valley.best", sig2(best.get(0.125, 0)) == 2.9e-3 and sig2(best.get(0.126, 0)) == 2.0e-3,
          "; ".join(f"{x:g}: {v:.4g}" for x, v in sorted(best.items())), "2.93e-3, 1.99e-3 (stalled Newton floor)",
          "2 significant digits; first evaluation at the best Newton point")
    curve_ok = all(abs(f2) <= 1e-9 and f1 == f1last for v in V.values() for _, f1, f2, f1last in v)
    check("d2.valley.on_curve", curve_ok, max(abs(f2) for v in V.values() for _, _, f2, _ in v), "<= 1e-9",
          "|f2| at the recorded point")
    minf1 = min(f1 for v in V.values() for _, f1, _, _ in v)
    check("d2.no_root", minf1 > 0, minf1, "f1 > 0 on f2 = 0 at every theta0", "no sign change")
    mins = {}
    for x, v in sorted(V.items()):
        v = sorted(v)
        t = np.array([a for a, _, _, _ in v])
        f = np.array([b for _, b, _, _ in v])
        c = np.polyfit(t, f, 4)
        tt = np.linspace(t.min(), t.max(), 200001)
        ff = np.polyval(c, tt)
        k = int(np.argmin(ff))
        mins[x] = (tt[k], ff[k])
    exp = {0.125: (14.03, 2.686e-3), 0.126: (14.06, 1.556e-3)}
    ok = all(abs(mins[x][1] - exp[x][1]) < 1e-6 and abs(mins[x][0] - exp[x][0]) < 0.01 for x in exp)
    check("d2.valley.min", ok, "; ".join(f"{x:g}: {mins[x][1]:.4g} at {mins[x][0]:.2f}" for x in sorted(mins)),
          "2.686e-3 at 14.03; 1.556e-3 at 14.06", "1e-6 (min), 0.01 (theta0)")
    slope = (mins[0.126][1] - mins[0.125][1]) / 0.001
    xfold = 0.126 - mins[0.126][1] / slope
    check("d2.fold", abs(xfold - 0.1274) < 5e-5, xfold, "0.1274", "5e-5 (linear in Delta_sigma, saddle-node)")

    # ------------------------------------------------- weak coupling = consistent scheme in eps
    from scipy.interpolate import pade
    C = {}
    for r in csv.DictReader(open(DATA / "pert_crosscheck" / "consistent_C0_C8.csv")):
        C[int(r["N"])] = [float(r[f"C{k}"]) for k in range(9)]
    worst = {}
    for x, tol in ((0.495, 1e-11), (0.475, 1e-7)):
        eps = 2 - 4 * x
        w = 0.0
        for L in range(8, 25, 2):
            p_, q_ = pade(C[L], 4)
            w = max(w, abs(seq[x][L] - p_(eps) / q_(eps)) if L in seq.get(x, {}) else math.inf)
        worst[x] = w
        check(f"d2.pert_consistent.{x:g}", w <= tol, w, f"<= {tol:g}", "|Delta(N) - Pade[4/4] of consistent C0..C8(N)|, N=8..24")

    # ------------------------------------------------- report
    w = max(len(r[0]) for r in ROWS)
    print(f"{'check':<{w}}  result  value  |  expected  |  tolerance")
    for name, res, val, expv, tol in ROWS:
        print(f"{name:<{w}}  {res:6}  {fmt(val)}  |  {expv}  |  {tol}")
    for n in NOTES:
        print("NOTE", n)
    nfail = sum(r[1] == "FAIL" for r in ROWS)
    print(f"{len(ROWS) - nfail} PASS, {nfail} FAIL")
    out = PKG / ".public_out"
    out.mkdir(exist_ok=True)
    (out / "replay_d2.json").write_text(json.dumps(
        {"rows": [dict(zip(("name", "result", "value", "expected", "tolerance"), map(str, r))) for r in ROWS],
         "notes": NOTES}, indent=1))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
