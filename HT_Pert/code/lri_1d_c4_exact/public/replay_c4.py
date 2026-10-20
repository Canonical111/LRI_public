#!/usr/bin/env python3
"""Replay of the exact finite-cutoff C4(Λ) of the d = 1 frozen-cutoff HT (HT_Pert/code/lri_1d_c4_exact).

Recomputes every quoted number of this package from the shipped records, without a production rerun, and prints a
PASS/FAIL table (exit status 1 on any FAIL).  Rows (ids as in results_map.md):
  x4.records     the four production results data/HT_1d/exact_c4/<sha12>/c4_1d_L{200,400,1000,2000}.npz: each gate record
                 names the production snapshot, binds the result's sha256, has no FAIL line, and the A6d lines chain the
                 rungs (prev_sha256 = sha256 of the previous result)
  x4.code        every file of the production snapshot manifest (stored in the result's provenance) is shipped here with
                 the same sha256 (files listed in public/SCRUBBED.txt, if any, are counted as scrubbed)
  x4.frozen      the frozen blind-fit records fits/frozen/*.json match their .sha256 files
  x4.values      C4^Dconn and C4^raw at Λ = 1000 and 2000 (quoted to 10 decimals)
  x4.overlap     |C4(Λ)| of the L1000 and L2000 runs agree on their common grid to <= 1e-12 (C2..C4 quarter grid, Dconn)
  x4.blind       `fits_c4_1d.py check` of the records frozen at Λ <= 1000 against the L2000 result, rerun: every row's
                 blind max |d| equals fits/blind_check_L1000_to_2000.txt (3 significant digits, as printed)
  x4.intercept   `fits_c4_1d.py compare` of the frozen Dconn record: L2, lo 200 intercept 45.4249416926 (record value)
  x4.refit       non-blind refit on all data to Λ = 2000 (basis L2, log none, lo 200, 400, 600), rerun: intercepts equal
                 fits/explore/explore_L2000_coef.txt to 1e-9 relative (default skipped with --quick)
  x4.c4          the paper's d = 1 HT C4 (\\HTpCfourOne, \\HTpCfourOneDev): median ± half-range of the three L2 fits
                 (log none, lower cutoffs 100, 200, 300) of the record frozen at Λ <= 1000, PDG-rounded; deviation one digit
  x4.lexact      largest cutoff of the exact sums: 2000 (\HTpOneLexact)
  x4.c2, x4.c3   the paper's d = 1 HT values of C2 and C3 (\HTpCtwoOne, \HTpCthreeOne, \HTpCtwoOneDev, \HTpCthreeOneDev,
                 \HTCtwoDev, \HTCthreeDev): public/c2c3_rule.py (rule fixed before any fit: free intercept, two bases per
                 order, lo 100/200/400, median ± half-range of the 6 fits) rerun on the L2000 result at hi = 2000; the
                 median and half-range must equal the record public/c2c3_rule_574918.txt to 1e-12 relative, and the
                 PDG-rounded value(error) and the one-digit deviations must equal the macro text exactly. With --quick
                 the record is read instead of rerunning (12 mpmath fits, about 1 min on 8 cores).
usage: python3 public/replay_c4.py [--data ../../data/HT_1d] [--quick]"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
SNAP = "a8b57b2e84758a8ffcb71c41233e1e777e6ab46f3d14435d46acbf25765f8dc7"
RUNGS = (200, 400, 1000, 2000)
C2_EXACT = 0.6571312639810638          # (π + 4 log 2)/9
C3_EXACT = -3.71985632290183342249
QUOTED_C23_118 = {2: "0.657131272(35)", 3: "-3.71984(8)"}   # \\NOneCtwoSolver, \\NOneCthreeSolver (note)
QUOTED_C23 = {   # paper macros (numbers.tex, 2026-10-14)
    2: {"value": "0.657131263984(10)", "dev": r"4\times10^{-12}", "absdev": r"3\times10^{-12}"},
    3: {"value": "-3.7198563(10)", "dev": r"2\times10^{-8}", "absdev": r"6\times10^{-8}"},
}
C4_EXACT = 45.42488010356
QUOTED_C4 = {"value": "45.4249(9)", "dev": r"1\times10^{-6}"}   # \HTpCfourOne, \HTpCfourOneDev (paper, 2026-10-14)
QUOTED = {  # Λ: (C4Dconn, C4raw) as quoted (10 decimals)
    1000: ("37.8351012026", None),
    2000: ("39.4111422825", None),
}
ROWS = []


def row(rid, ok, detail):
    ROWS.append((rid, "PASS" if ok else "FAIL", detail))


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def scrubbed():
    p = os.path.join(HERE, "SCRUBBED.txt")
    if not os.path.exists(p):
        return set()
    return {ln.strip() for ln in open(p) if ln.strip() and not ln.startswith("#")}


def run(args):
    r = subprocess.run([sys.executable] + args, cwd=PKG, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{' '.join(args)} failed:\n{r.stderr[-2000:]}")
    return r.stdout


def pdg(value, err):
    """value(err) by the PDG rule: the three leading digits of err in 100-354 keep 2 significant digits, 355-949 keep 1,
    950-999 are rounded up to 1000 and keep 2."""
    import math
    e = math.floor(math.log10(err))
    d = round(err / 10 ** (e - 2))
    if d >= 950:                      # includes 1000 from rounding: err becomes 10^(e+1), two digits
        e, nd, mant = e + 1, 2, 10
    else:
        nd = 2 if d <= 354 else 1
        mant = None
    unit = e - nd + 1
    eu = mant if mant is not None else round(err / 10 ** unit)
    return f"{value:.{max(0, -unit)}f}({eu})"


def tex1(x):
    """one significant digit in TeX, e.g. 4\\times10^{-12}"""
    m, e = f"{abs(x):.0e}".split("e")
    return m + r"\times10^{" + str(int(e)) + "}"


def parse_blind(text):
    out = {}
    for m in re.finditer(r"^(\w+)\s+log=(\w+)\s+lo=\s*(\d+): blind max \|d\| ([0-9.e+-]+) at L=(\d+)", text, re.M):
        out[(m.group(1), m.group(2), int(m.group(3)))] = (m.group(4), int(m.group(5)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(PKG, "..", "..", "data", "HT_1d"))
    ap.add_argument("--quick", action="store_true", help="skip the refit (x4.refit), a few minutes of mpmath")
    a = ap.parse_args()
    R = os.path.join(a.data, "exact_c4", SNAP[:12])
    npz = {L: os.path.join(R, f"c4_1d_L{L}.npz") for L in RUNGS}

    # x4.records
    ok, prev, msgs = True, None, []
    for L in RUNGS:
        G = os.path.join(R, f"gates_L{L}.txt")
        if not (os.path.exists(npz[L]) and os.path.exists(G)):
            ok = False; msgs.append(f"L{L} missing"); continue
        lines = open(G).read().split("\n")
        h = sha(npz[L])
        res = [ln for ln in lines if ln.startswith("result ")]
        good = (f"snapshot_sha {SNAP}" in lines and len(res) == 1 and res[0].split()[-1] == h
                and not any(ln.startswith("FAIL") for ln in lines))
        a6d = [ln for ln in lines if ln.startswith("PASS A6d_")]
        if prev is not None:
            good = good and len(a6d) == 1 and f"prev_sha256={prev}" in a6d[0] and f"cur_sha256={h}" in a6d[0]
        ok = ok and good
        msgs.append(f"L{L} {h[:12]} {'ok' if good else 'BAD'}")
        prev = h
    row("x4.records", ok, "; ".join(msgs))

    # x4.code
    prov = json.loads(str(np.load(npz[2000])["provenance"]))
    man, scr = prov["snapshot_manifest"], scrubbed()
    bad = [k for k, v in man.items() if k not in scr and (not os.path.exists(os.path.join(PKG, k))
                                                          or sha(os.path.join(PKG, k)) != v)]
    row("x4.code", prov["snapshot_sha"] == SNAP and not bad,
        f"{len(man)} manifest files, {len([k for k in man if k in scr])} scrubbed, mismatched {bad}")

    # x4.frozen
    fz = [f for f in sorted(os.listdir(os.path.join(PKG, "fits", "frozen"))) if f.endswith(".json")]
    badf = [f for f in fz if open(os.path.join(PKG, "fits", "frozen", f + ".sha256")).read().split()[0]
            != sha(os.path.join(PKG, "fits", "frozen", f))]
    row("x4.frozen", fz and not badf, f"{len(fz)} records, bad {badf}")

    # x4.values
    msgs, ok = [], True
    for L, (qd, qr) in QUOTED.items():
        d = np.load(npz[2000])
        i = list(d["even_L"]).index(L)
        v = f"{d['even_C4Dconn'][i]:.10f}"
        ok = ok and v == qd
        msgs.append(f"C4Dconn({L}) = {v} (quoted {qd})")
    row("x4.values", ok, "; ".join(msgs))

    # x4.overlap
    e, d = np.load(npz[1000]), np.load(npz[2000])
    n = len(e["even_L"])
    worst = max(float(np.nanmax(np.abs(e[k] - d[k][:len(e[k])]))) for k in ("C2", "C3", "C4"))
    worst = max(worst, float(np.max(np.abs(e["even_C4Dconn"] - d["even_C4Dconn"][:n]))))
    row("x4.overlap", worst <= 1e-12, f"max |Δ| L1000 vs L2000 = {worst:.2e} (<= 1e-12)")

    # x4.blind
    got = {}
    for s in ("Dconn", "raw"):
        out = run(["fits/fits_c4_1d.py", "check", "--frozen", f"fits/frozen/frozen_L1000_{s}.json", "--npz", npz[2000]])
        got.update({(s,) + k: v for k, v in parse_blind(out).items()})
    pubs = parse_blind_by_scheme(os.path.join(PKG, "fits", "blind_check_L1000_to_2000.txt"))
    mism = [k for k in pubs if got.get(k) != pubs[k]]
    l2 = got.get(("Dconn", "L2", "none", 200))
    row("x4.blind", pubs and not mism, f"{len(got)} rows rerun, {len(mism)} differ from the published file; "
        f"Dconn L2 lo 200: {l2[0] if l2 else '?'} at L={l2[1] if l2 else '?'}")

    # x4.intercept
    out = run(["fits/fits_c4_1d.py", "compare", "--frozen", "fits/frozen/frozen_L1000_Dconn.json"])
    m = re.search(r"^L2\s+log=none\s+lo= 200: A = ([0-9.]+)", out, re.M)
    row("x4.intercept", bool(m) and m.group(1) == "45.4249416926", f"frozen L2 lo 200 A = {m.group(1) if m else '?'}")

    # x4.refit
    if a.quick:
        ROWS.append(("x4.refit", "SKIP", "--quick"))
    else:
        ref = {}
        for ln in open(os.path.join(PKG, "fits", "explore", "explore_L2000_coef.txt")):
            if ln.startswith("#") or not ln.strip():
                continue
            t = ln.split()
            ref[int(t[0])] = float(t[3])
        ok, msgs = True, []
        for lo in sorted(ref):
            out = run(["fits/fits_c4_1d.py", "explore", "--npz", npz[2000], "--hi", "2000", "--lo", str(lo),
                       "--scheme", "Dconn", "--logs", "none", "--bases", "L2"])
            mm = re.search(r"A=([0-9.]+)", out)
            A = float(mm.group(1)) if mm else float("nan")
            good = abs(A - ref[lo]) <= 1e-9 * abs(ref[lo])
            ok = ok and good
            msgs.append(f"lo {lo}: {A:.10f} vs {ref[lo]:.10f}")
        row("x4.refit", ok, "; ".join(msgs))

    # x4.c4: the paper's d = 1 HT C4 = median ± half-range of the three frozen L2 fits (log none, lo 100, 200, 300)
    P = json.load(open(os.path.join(PKG, "fits", "frozen", "frozen_L1000_Dconn.json")))
    l2 = sorted(float(r["coef"][0]) for r in P["fits"] if r["basis"] == "L2" and r["log"] == "none")
    med, half = l2[1], (l2[-1] - l2[0]) / 2
    txt = (pdg(med, half), tex1(med / C4_EXACT - 1))
    row("x4.c4", len(l2) == 3 and txt == (QUOTED_C4["value"], QUOTED_C4["dev"]),
        f"frozen L2 intercepts {', '.join(f'{v:.7f}' for v in l2)} -> median {med:.10f} +- {half:.3e} -> {txt[0]}, "
        f"rel {txt[1]} (quoted {QUOTED_C4['value']}, {QUOTED_C4['dev']})")

    # x4.lexact
    d2 = np.load(npz[2000])
    row("x4.lexact", int(d2["even_L"][-1]) == 2000, f"largest even cutoff {int(d2['even_L'][-1])} (\HTpOneLexact 2000)")

    # x4.c2, x4.c3
    fits, fits118 = {}, {}                                   # (order, basis, lo) -> A, from the record
    for ln in open(os.path.join(HERE, "c2c3_rule_574918.txt")):
        m = re.match(r"^C(\d) (\w+)\s+lo=\s*(\d+) hi=\s*(\d+) .* A=([-0-9.]+)$", ln.strip())
        if m and m.group(4) in ("2000", "118"):
            (fits if m.group(4) == "2000" else fits118)[(int(m.group(1)), m.group(2), int(m.group(3)))] = \
                float(m.group(5))
    if a.quick:
        got, got118, src = dict(fits), dict(fits118), "record public/c2c3_rule_574918.txt"
    else:
        import json as _j
        os.makedirs(os.path.join(PKG, ".work"), exist_ok=True)
        js = os.path.join(PKG, ".work", "c2c3_rule.json")
        run(["public/c2c3_rule.py", "--npz", npz[2000], "--json", js, "--procs", str(os.cpu_count() or 4)])
        allf = _j.load(open(js))["fits"]
        got = {(r["order"], r["basis"], r["lo"]): r["A"] for r in allf if r["hi"] == 2000}
        got118 = {(r["order"], r["basis"], r["lo"]): r["A"] for r in allf if r["hi"] == 118}
        src = "rerun of public/c2c3_rule.py"
    same = set(got) == set(fits) and len(fits) == 12 and all(
        abs(got[k] - fits[k]) <= 1e-12 * abs(fits[k]) for k in fits)
    for k, ex in ((2, C2_EXACT), (3, C3_EXACT)):
        v = np.array([got[x] for x in sorted(got) if x[0] == k])
        med, half = float(np.median(v)), float((v.max() - v.min()) / 2)
        q = QUOTED_C23[k]
        txt = (pdg(med, half), tex1(med / ex - 1), tex1(med - ex))
        ok = same and txt == (q["value"], q["dev"], q["absdev"])
        row(f"x4.c{k}", ok, f"{src} ({'6 fits equal the record' if same else 'FITS DIFFER from the record'}): "
            f"median {med:.15f} +- {half:.4e} -> {txt[0]}, rel {txt[1]}, abs {txt[2]} "
            f"(quoted {q['value']}, {q['dev']}, {q['absdev']})")

    # x4.c23solver: the same rule on the solver range, hi = 118 (note-only comparison values)
    same118 = set(got118) == set(fits118) and len(fits118) == 12 and all(
        abs(got118[k] - fits118[k]) <= 1e-12 * abs(fits118[k]) for k in fits118)
    txts = {}
    for k in (2, 3):
        v = np.array([got118[x] for x in sorted(got118) if x[0] == k])
        txts[k] = pdg(float(np.median(v)), float((v.max() - v.min()) / 2))
    row("x4.c23solver", same118 and txts[2] == QUOTED_C23_118[2] and txts[3] == QUOTED_C23_118[3],
        f"same rule on the solver range (hi 118, lo 16, 24, 32): C2 {txts[2]}, C3 {txts[3]} (quoted "
        f"{QUOTED_C23_118[2]}, {QUOTED_C23_118[3]}; 6 fits per order equal the record: {same118})")

    w = max(len(r[0]) for r in ROWS)
    for rid, st, det in ROWS:
        print(f"{rid:{w}s}  {st:4s}  {det}")
    nf = sum(r[1] == "FAIL" for r in ROWS)
    print(f"# {len(ROWS)} rows, {nf} FAIL")
    sys.exit(1 if nf else 0)


def parse_blind_by_scheme(path):
    out, scheme = {}, None
    for ln in open(path):
        if ln.startswith("## "):
            scheme = ln[3:].strip()
            continue
        m = re.match(r"^(\w+)\s+log=(\w+)\s+lo=\s*(\d+): blind max \|d\| ([0-9.e+-]+) at L=(\d+)", ln)
        if m and scheme:
            out[(scheme, m.group(1), m.group(2), int(m.group(3)))] = (m.group(4), int(m.group(5)))
    return out


if __name__ == "__main__":
    main()
