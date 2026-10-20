#!/usr/bin/env python3
r"""Replay of the S10 complete-window coefficients of the d = 1 frozen-cutoff HT (HT_Pert/code/lri_d1_full_coefficient_flow
and data/HT_1d/s10_production).

Recomputes every quoted number of the package from the shipped records, without a production rerun, and prints a
table id | verdict | what | quoted | computed (exit status 1 on any FAIL; also written to <work>/replay_<pkg>.txt).
Rows (ids as in results_map.md and quoted_lri_d1_full_coefficient_flow.json):
  s10.manifest  MANIFEST.sha256 (85 entries) verifies; files in public/SCRUBBED.txt are reported as scrubbed
  s10.code      code/ragged_quotient.py has sha256 854fc763..., the provenance.code_sha256 of all 14 production records
  s10.records   data/HT_1d/s10_production/dconn_L{46..72}_d8.json: 14 records, scheme dconn, degree 8, cutoff = file
                name, finite C with C0 = 1/2 and C1 = -1/6, production stack Python 3.11.4 / numpy 1.24.3 / scipy 1.10.1
                with 63-bit long double, no state-guard overflow
  s10.winlam    \HTpWinLamEight: the largest cutoff with the complete Dconn window computed through eps^8, with every even
                cutoff below it present (archive results/new_coefficients L = 2..44 plus production 46..72); exact
  s10.csv       public/make_dconn_minus_raw.py regenerates dconn_minus_raw_L46_72.csv from the 14 records and the raw
                coefficients of data/HT_1d/c8/extrapolation/data.json byte for byte (sha256 3105e037...); exact
  s10.dC678     dC6, dC7, dC8 at L = 72 from the regenerated table, rounded to the quoted decimals
  s10.match     \HTpSTenMatch: max over L = 46..72 of |(C4 - raw4) - dC4| and |(C5 - raw5) - dC5|, dC4, dC5 the exact
                eps^4/eps^5 windows of code/lri_hpc_Hamitonian/analysis/eps5_window/reconcile/dC_reconciled.json
                (sha256 0250b341...), rounded to one significant figure; C0..C3 unchanged by the window (reported)
SKIP: a cross-folder input (data.json of the C8 data set, dC_reconciled.json of lri_hpc_Hamitonian) is absent.
usage: python3 public/replay_s10.py [--data ../../data/HT_1d] [--ham ../lri_hpc_Hamitonian] [--work .work]"""
import argparse
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from make_dconn_minus_raw import table  # noqa: E402

NAME = "lri_d1_full_coefficient_flow"
CODE_SHA = "854fc763a914497b7f7c9c19d3d14572113989f58ee67662860f01a7f227f5ca"
CSV_SHA = "3105e0375f71bd276ce559c33ed8e021d63665892b3df536845c9fa12e1fb3e6"
DATA_SHA = "ccc77dfa1e7d3955f3b8f22b2ea3b99ba649976605c5bac6bae39b5f2ad92faa"
RECON_SHA = "0250b341048a2da66e313edb7225233b972b25db185f03491aebc6c7483fadd8"
LS = list(range(46, 73, 2))
QUOTED = {
    "s10.manifest": "85 entries",
    "s10.code": CODE_SHA[:12],
    "s10.records": "14 records, L = 46..72",
    "s10.winlam": "72",
    "s10.csv": "sha256 " + CSV_SHA[:12],
    "s10.dC678": "+1.1717361, -1.828185, -8.5641",
    "s10.match": r"2\times10^{-11}",
}
ROWS = []


def row(rid, verdict, what, computed):
    ROWS.append((rid, verdict, what, QUOTED[rid], computed))


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def scrubbed():
    p = os.path.join(HERE, "SCRUBBED.txt")
    if not os.path.exists(p):
        return set()
    return {ln.strip() for ln in open(p) if ln.strip() and not ln.startswith("#")}


def sig1(x):
    """x rounded to one significant figure, written as numbers.tex writes it (m\\times10^{e})."""
    e = math.floor(math.log10(abs(x)))
    m = round(x / 10 ** e)
    if m == 10:
        m, e = 1, e + 1
    return rf"{m}\times10^{{{e}}}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(PKG, "..", "..", "data", "HT_1d"))
    ap.add_argument("--ham", default=os.path.join(PKG, "..", "lri_hpc_Hamitonian"))
    ap.add_argument("--work", default=os.path.join(PKG, ".work"))
    a = ap.parse_args()
    P = os.path.join(a.data, "s10_production")
    DJ = os.path.join(a.data, "c8", "extrapolation", "data.json")
    RJ = os.path.join(a.ham, "analysis", "eps5_window", "reconcile", "dC_reconciled.json")
    scr = scrubbed()

    # s10.manifest
    rows = [ln for ln in open(os.path.join(PKG, "MANIFEST.sha256")).read().splitlines() if ln.strip()]
    bad, sc = [], []
    for ln in rows:
        exp, rel = ln.split("  ", 1)
        p = os.path.join(PKG, rel)
        if not os.path.isfile(p):
            bad.append(rel)
        elif sha(p) != exp:
            (sc if rel in scr and rel != "code/ragged_quotient.py" else bad).append(rel)
    row("s10.manifest", "PASS" if len(rows) == 85 and not bad else "FAIL",
        "MANIFEST.sha256 of the package at fec60a2 verifies (SCRUBBED.txt honoured)",
        f"{len(rows)} entries, {len(rows) - len(bad) - len(sc)} match, scrubbed {sc}, bad {bad}")

    # s10.code
    code = sha(os.path.join(PKG, "code", "ragged_quotient.py"))
    recs = {L: json.load(open(os.path.join(P, f"dconn_L{L}_d8.json"))) for L in LS
            if os.path.exists(os.path.join(P, f"dconn_L{L}_d8.json"))}
    prov = sorted({r["provenance"]["code_sha256"] for r in recs.values()})
    row("s10.code", "PASS" if code == CODE_SHA and prov == [CODE_SHA] else "FAIL",
        "shipped production solver = the solver of every production record (provenance.code_sha256)",
        f"code/ragged_quotient.py {code[:12]}; records {[x[:12] for x in prov]}")

    # s10.records
    probs = []
    for L in LS:
        r = recs.get(L)
        if r is None:
            probs.append(f"L{L} missing")
            continue
        pv = r["provenance"]
        good = (r["cutoff"] == L and r["scheme"] == "dconn" and r["degree"] == 8 and len(r["C"]) == 9
                and all(math.isfinite(x) for x in r["C"]) and r["C"][0] == 0.5 and abs(r["C"][1] + 1 / 6) < 1e-12
                and (pv["python"], pv["numpy"], pv["scipy"]) == ("3.11.4", "1.24.3", "1.10.1")
                and pv["longdouble_mantissa_bits"] == 63 and r["basis_dimension"] <= pv["max_states"])
        if not good:
            probs.append(f"L{L}")
    jobs = sorted({r["provenance"]["slurm_job_id"] for r in recs.values()})
    states = recs[72]["basis_dimension"] if 72 in recs else None
    row("s10.records", "PASS" if not probs else "FAIL", "14 production records (symmetry defq, Dconn, degree 8)",
        f"{len(recs)} records, problems {probs}; jobs {jobs}; L=72: {states} states, "
        f"{recs[72]['seconds'] / 3600:.1f} h, {recs[72]['maxrss_kib'] / 2 ** 20:.1f} GiB" if 72 in recs else "L72 missing")

    # s10.winlam
    arch = {L for L in range(2, 45, 2)
            if os.path.exists(os.path.join(PKG, "results", "new_coefficients", f"dconn_L{L}_d8.json"))}
    have = arch | set(recs)
    top = max(have) if have else None
    complete = top is not None and all(L in have for L in range(2, top + 1, 2))
    got = str(top)
    row("s10.winlam", "PASS" if complete and got == QUOTED["s10.winlam"] else "FAIL",
        r"\HTpWinLamEight: complete Dconn C2..C8 at every even cutoff up to", f"{got} (archive {len(arch)} cutoffs "
        f"2..44, production {len(recs)}; no gap: {complete})")

    # s10.csv, s10.dC678
    if not os.path.exists(DJ):
        row("s10.csv", "SKIP", "dconn_minus_raw_L46_72.csv regenerated byte for byte", f"{DJ} absent")
        row("s10.dC678", "SKIP", "dC6, dC7, dC8 at L = 72", "needs the regenerated table")
    else:
        t = table(a.data)
        os.makedirs(a.work, exist_ok=True)
        open(os.path.join(a.work, "dconn_minus_raw_L46_72.csv"), "w").write(t)
        ts = hashlib.sha256(t.encode()).hexdigest()
        shipped = sha(os.path.join(P, "dconn_minus_raw_L46_72.csv"))
        ok = ts == CSV_SHA == shipped and sha(DJ) == DATA_SHA
        row("s10.csv", "PASS" if ok else "FAIL", "dconn_minus_raw_L46_72.csv regenerated from records + data.json raw",
            f"regenerated {ts[:12]}, shipped {shipped[:12]}, data.json {sha(DJ)[:12]}")
        last = t.strip().splitlines()[-1].split(",")
        vals = [float(x) for x in last[1:]]
        got = f"{vals[0]:+.7f}, {vals[1]:+.6f}, {vals[2]:+.4f}"
        row("s10.dC678", "PASS" if last[0] == "72" and got == QUOTED["s10.dC678"] else "FAIL",
            "dC6, dC7, dC8 at L = 72 (rounded to the quoted decimals)",
            f"{got} (full: {', '.join(repr(v) for v in vals)})")

    # s10.match
    if not (os.path.exists(DJ) and os.path.exists(RJ)):
        row("s10.match", "SKIP", r"\HTpSTenMatch: S10 dC4, dC5 vs the reconciled windows, L = 46..72",
            f"absent: {[p for p in (DJ, RJ) if not os.path.exists(p)]}")
    else:
        raw = json.load(open(DJ))["raw"]
        rc = json.load(open(RJ))
        m4 = max(abs(recs[L]["C"][4] - raw[str(L)][4] - rc[str(L)]["dC4_Dconn"]) for L in LS)
        m5 = max(abs(recs[L]["C"][5] - raw[str(L)][5] - rc[str(L)]["dC5_Dconn"]) for L in LS)
        m03 = max(abs(recs[L]["C"][k] - raw[str(L)][k]) for L in LS for k in range(4))
        got = sig1(max(m4, m5))
        ok = got == QUOTED["s10.match"] and sha(RJ) == RECON_SHA
        row("s10.match", "PASS" if ok else "FAIL", r"\HTpSTenMatch: S10 dC4, dC5 vs the reconciled windows, L = 46..72",
            f"{got} (max |d dC4| {m4:.2e}, max |d dC5| {m5:.2e}; C0..C3 unchanged to {m03:.1e}; "
            f"dC_reconciled.json {sha(RJ)[:12]})")

    w = max(len(r[0]) for r in ROWS)
    lines = [f"{'id':{w}s}  verdict  what | quoted | computed"]
    lines += [f"{rid:{w}s}  {v:7s}  {what} | {q} | {c}" for rid, v, what, q, c in ROWS]
    cnt = {v: sum(r[1] == v for r in ROWS) for v in ("PASS", "FAIL", "INFO", "SKIP")}
    lines.append(f"# {cnt['PASS']} PASS, {cnt['FAIL']} FAIL, {cnt['INFO']} INFO, {cnt['SKIP']} SKIP")
    txt = "\n".join(lines)
    print(txt)
    os.makedirs(a.work, exist_ok=True)
    open(os.path.join(a.work, f"replay_{NAME}.txt"), "w").write(txt + "\n")
    sys.exit(1 if cnt["FAIL"] else 0)


if __name__ == "__main__":
    main()
