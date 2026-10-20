#!/usr/bin/env python3
"""Replay of the exact finite-cutoff C5(Λ) of the d = 1 frozen-cutoff HT (HT_Pert/code/lri_1d_c5_exact).

Recomputes every quoted number of this package from the shipped records, without a production rerun, and prints a
PASS/FAIL table (exit status 1 on any FAIL).  Rows (ids as in results_map.md):
  x5.records      results data/HT_1d/exact_c5/<sha12>/c5_1d_L{80,160,240,320,400,500}.npz: gate records name the
                  production snapshot, bind each result's sha256, carry no FAIL line, and chain the rungs by A6d
                  (prev_sha256 = sha256 of the previous result); the A6e lines bind the exact-C4 result shipped in
                  data/HT_1d/exact_c4 (sha256 62720cf5...)
  x5.code         every file of the production snapshot manifest (in the result's provenance) is shipped with the same
                  sha256 (files listed in public/SCRUBBED.txt count as scrubbed)
  x5.frozen       the frozen blind-fit records fits/frozen/*.json match their .sha256 files
  x5.values       C5^raw, C5^Dconn and ΔC5 at Λ = 80..400 (from the L400 result) and 500 (L500), 12 decimals, as the
                  README table quotes them (the rungs agree to x5.overlap)
  x5.overlap      consecutive rungs agree on their common grid to <= 6e-12 (quarter-grid C2..C5 and even C5^Dconn)
  x5.blind        `fits_c5_1d.py check` reruns: frozen L320 vs L400 (partial), frozen L320 and L400 vs L500; every row's
                  blind max |d| and its location equal fits/blind_check_L320_to_400.txt and fits/blind_check_L500.txt
  x5.intercept    `fits_c5_1d.py compare` reruns of the four frozen records equal their published values (L320:
                  fits/blind_check_L320_to_400.txt; L400: QUOTED_L400 below)
  x5.explore      non-blind refits on Λ <= 500 (Dconn and raw, lo 80, 120, 160, 200): every intercept A equals
                  fits/explore/L500/explore_*_lo*.log (10 decimals, as printed)
  x5.tail         fixed-intercept tail fits (fits/tail_fixedA_c5.py, A = C5): coefficient lines equal
                  fits/explore/L500/tailA_{L2,M3,M3x}.log
  x5.constrained  fits/constrained_c5.py (log^3 coefficient fixed by the exponentiated C4 tail) rerun with the shipped
                  exact-C4 result: c2, c3, c4, c13 and every intercept of the table equal
                  fits/explore/constrained_L500/constrained_c5_v2.json to 1e-9 relative
  x5.crosscheck   the cited blind re-implementation and theory check (fits/explore/constrained_L500/xchk/): reports and
                  summary present; quoted C5 = -731.13 +- 0.10 (not recomputed here; see REPRODUCE)
  x5.c5           the paper's d = 1 HT C5 (\\HTpCfiveOne, \\HTpCfiveOneDev): median of the separately written constrained
                  fits (basis A, lower cutoffs 50, 60, 70, 80, Λ <= 500; xchk/cfit_blind/summary_c5.json) with the report's
                  uncertainty 0.10; deviation one digit
--quick skips x5.explore, x5.tail and x5.constrained (the mpmath refits: about 2 min, 2 min and 1 min on 64 cores).
usage: python3 public/replay_c5.py [--data ../../data/HT_1d] [--work .work] [--procs N] [--quick]"""
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
SNAP = "040d92b3bd1d4cfc7804f59b88a064e4963ed97e65c0b8420e97a7d2894959ed"
C4SNAP = "a8b57b2e84758a8ffcb71c41233e1e777e6ab46f3d14435d46acbf25765f8dc7"
C4SHA = "62720cf5ac097f5e7f93250bc38e592c4de269b703abb5dd2544fb53994b51d2"
RUNGS = (80, 160, 240, 320, 400, 500)
C5_EXACT = -731.1394766245398
QUOTED_C5 = {"value": "-731.13(10)", "dev": r"2\times10^{-5}"}   # \HTpCfiveOne, \HTpCfiveOneDev (paper, 2026-10-14)
QUOTED_VALUES = {   # Λ: (C5raw, C5Dconn, ΔC5), README.md table
    80: ("-392.135029408908", "-391.423086698222", "0.711942710687"),
    160: ("-446.373502055187", "-445.658818983761", "0.714683071426"),
    240: ("-474.776184815074", "-474.060258016439", "0.715926798635"),
    320: ("-493.541301984906", "-492.824626666496", "0.716675318410"),
    400: ("-507.336253034259", "-506.619063805112", "0.717189229147"),
    500: ("-520.488093345382", "-519.770442010804", "0.717651334579"),
}
QUOTED_L400 = {  # intercepts of the records frozen at Λ <= 400 (log none), as quoted
    ("Dconn", "L2", 80): "-730.8460638788",
    ("Dconn", "M3", 80): "-731.0822822059",
    ("raw", "L2", 80): "-731.5701104397",
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


def run(args, env=None):
    r = subprocess.run([sys.executable] + args, cwd=PKG, capture_output=True, text=True,
                       env=dict(os.environ, **(env or {})))
    if r.returncode:
        raise RuntimeError(f"{' '.join(args)} failed:\n{r.stderr[-2000:]}")
    return r.stdout


def runmany(jobs, env=None):
    """Run several python commands in parallel; returns their stdout in order."""
    ps = [subprocess.Popen([sys.executable] + j, cwd=PKG, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                           env=dict(os.environ, **(env or {}))) for j in jobs]
    outs = []
    for j, p in zip(jobs, ps):
        o, e = p.communicate()
        if p.returncode:
            raise RuntimeError(f"{' '.join(j)} failed:\n{e[-2000:]}")
        outs.append(o)
    return outs


BLIND = re.compile(r"^(\w+)\s+log=(\w+)\s+lo=\s*(\d+): blind max \|d\| ([0-9.e+-]+) at L=(\d+); d\(L=(\d+)\) ([0-9.e+-]+)")


def parse_blind_sections(path):
    """{frozen record name: {(basis, log, lo): (maxd, at, lastL, lastd)}} from a published blind-check file."""
    out, cur = {}, None
    for ln in open(path):
        m = re.match(r"^# blind check of (\S+)", ln)
        if m:
            cur = os.path.basename(m.group(1))
            out.setdefault(cur, {})
            continue
        if ln.startswith("$ ") or ln.startswith("# frozen record"):
            cur = None
            continue
        m = BLIND.match(ln)
        if m and cur:
            out[cur][(m.group(1), m.group(2), int(m.group(3)))] = m.group(4, 5, 6, 7)
    return out


def parse_blind(text):
    return {(m.group(1), m.group(2), int(m.group(3))): m.group(4, 5, 6, 7) for m in
            (BLIND.match(ln) for ln in text.split("\n")) if m}


COMPARE = re.compile(r"^(\w+)\s+log=(\w+)\s+lo=\s*(\d+): A = ([0-9.+-]+)")


def parse_compare_sections(path):
    out, cur = {}, None
    for ln in open(path):
        m = re.match(r"^# frozen record (\S+)", ln)
        if m:
            cur = os.path.basename(m.group(1))
            out.setdefault(cur, {})
            continue
        if ln.startswith("$ ") or ln.startswith("# blind check"):
            cur = None
            continue
        m = COMPARE.match(ln)
        if m and cur:
            out[cur][(m.group(1), m.group(2), int(m.group(3)))] = m.group(4)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(PKG, "..", "..", "data", "HT_1d"))
    ap.add_argument("--work", default=os.path.join(PKG, ".work"))
    ap.add_argument("--procs", type=int, default=os.cpu_count())
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    R = os.path.abspath(os.path.join(a.data, "exact_c5", SNAP[:12]))
    C4NPZ = os.path.abspath(os.path.join(a.data, "exact_c4", C4SNAP[:12], "c4_1d_L2000.npz"))
    npz = {L: os.path.join(R, f"c5_1d_L{L}.npz") for L in RUNGS}

    # x5.records
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
        a6e = [ln for ln in lines if ln.startswith("PASS A6e c4ref_sha256=")]
        if prev is not None:
            good = good and len(a6d) == 1 and f"prev_sha256={prev}" in a6d[0] and f"cur_sha256={h}" in a6d[0]
        if a6e:
            good = good and all(f"c4ref_sha256={C4SHA}" in x for x in a6e)
        ok = ok and good
        msgs.append(f"L{L} {h[:12]} {'ok' if good else 'BAD'}")
        prev = h
    c4ok = os.path.exists(C4NPZ) and sha(C4NPZ) == C4SHA
    lmax = int(np.load(npz[500])["even_L"][-1]) if os.path.exists(npz[500]) else -1
    ok = ok and lmax == 500
    msgs.append(f"largest cutoff {lmax} (\\NOneCfiveLmax 500)")
    row("x5.records", ok and c4ok, "; ".join(msgs) + f"; exact-C4 reference {'ok' if c4ok else 'MISSING/BAD'}")

    # x5.code
    prov = json.loads(str(np.load(npz[500])["provenance"]))
    man, scr = prov["snapshot_manifest"], scrubbed()
    bad = [k for k, v in man.items() if k not in scr and (not os.path.exists(os.path.join(PKG, k))
                                                          or sha(os.path.join(PKG, k)) != v)]
    row("x5.code", prov["snapshot_sha"] == SNAP and not bad,
        f"{len(man)} manifest files, {len([k for k in man if k in scr])} scrubbed, mismatched {bad}")

    # x5.frozen
    FZ = os.path.join(PKG, "fits", "frozen")
    fz = [f for f in sorted(os.listdir(FZ)) if f.endswith(".json")]
    badf = [f for f in fz if open(os.path.join(FZ, f + ".sha256")).read().split()[0] != sha(os.path.join(FZ, f))]
    row("x5.frozen", len(fz) == 4 and not badf, f"{len(fz)} records, bad {badf}")

    # x5.values
    bad = []
    for L, (qr, qd, qw) in QUOTED_VALUES.items():
        d = np.load(npz[400 if L <= 400 else 500])   # the README table quotes Λ <= 400 from the L400 result
        i = list(d["even_L"]).index(L)
        got = (f"{d['even_C5raw'][i]:.12f}", f"{d['even_C5Dconn'][i]:.12f}", f"{d['even_dC5_Dconn'][i]:.12f}")
        if got != (qr, qd, qw):
            bad.append((L, got))
    row("x5.values", not bad, f"6 cutoffs x (raw, Dconn, ΔC5) from the L400 (Λ <= 400) and L500 results; mismatches {bad}")

    # x5.overlap
    worst = 0.0
    for L0, L1 in zip(RUNGS, RUNGS[1:]):
        e, f = np.load(npz[L0]), np.load(npz[L1])
        n = len(e["even_L"])
        w = max(float(np.nanmax(np.abs(e[k] - f[k][:len(e[k])]))) for k in ("C2", "C3", "C4", "C5"))
        worst = max(worst, w, float(np.max(np.abs(e["even_C5Dconn"] - f["even_C5Dconn"][:n]))))
    row("x5.overlap", worst <= 6e-12, f"max |Δ| over consecutive rungs = {worst:.2e} (<= 6e-12)")

    # x5.blind
    pub = {}
    pub["L400"] = parse_blind_sections(os.path.join(PKG, "fits", "blind_check_L320_to_400.txt"))
    pub["L500"] = parse_blind_sections(os.path.join(PKG, "fits", "blind_check_L500.txt"))
    jobs, keys = [], []
    for tgt, rec, extra in [("L400", "frozen_L320_Dconn.json", ["--allow-partial"]),
                            ("L400", "frozen_L320_raw.json", ["--allow-partial"]),
                            ("L500", "frozen_L400_Dconn.json", []), ("L500", "frozen_L400_raw.json", []),
                            ("L500", "frozen_L320_Dconn.json", []), ("L500", "frozen_L320_raw.json", [])]:
        jobs.append(["fits/fits_c5_1d.py", "check", "--frozen", f"fits/frozen/{rec}", "--npz",
                     npz[int(tgt[1:])]] + extra)
        keys.append((tgt, rec))
    nrow, mism = 0, []
    for (tgt, rec), out in zip(keys, runmany(jobs)):
        got, exp = parse_blind(out), pub[tgt].get(rec, {})
        nrow += len(got)
        if not exp or got != exp:
            mism.append(f"{rec}->{tgt}")
    row("x5.blind", not mism, f"{nrow} rows rerun in 6 checks; differing sections {mism}")

    # x5.intercept
    pubc = parse_compare_sections(os.path.join(PKG, "fits", "blind_check_L320_to_400.txt"))
    recs = ["frozen_L320_Dconn.json", "frozen_L320_raw.json", "frozen_L400_Dconn.json", "frozen_L400_raw.json"]
    outs = runmany([["fits/fits_c5_1d.py", "compare", "--frozen", f"fits/frozen/{r}"] for r in recs])
    mism = []
    for r, out in zip(recs, outs):
        got = {(k[0], k[1], k[2]): v for k, v in
               ((tuple([m.group(1), m.group(2), int(m.group(3))]), m.group(4)) for m in
                (COMPARE.match(ln) for ln in out.split("\n")) if m)}
        if "L320" in r:
            if got != pubc.get(r):
                mism.append(r)
        else:
            sch = "Dconn" if "Dconn" in r else "raw"
            for (s, b, lo), v in QUOTED_L400.items():
                if s == sch and got.get((b, "none", lo)) != v:
                    mism.append(f"{r}:{b}/{lo}")
    row("x5.intercept", not mism, f"compare of 4 frozen records; mismatches {mism}; L400 Dconn L2/M3 lo 80 = "
        f"{QUOTED_L400[('Dconn', 'L2', 80)]} / {QUOTED_L400[('Dconn', 'M3', 80)]}")

    if a.quick:
        for rid in ("x5.explore", "x5.tail", "x5.constrained"):
            ROWS.append((rid, "SKIP", "--quick"))
    else:
        os.makedirs(a.work, exist_ok=True)
        # x5.explore
        jobs, keys = [], []
        for s in ("Dconn", "raw"):
            for lo in (80, 120, 160, 200):
                jobs.append(["fits/fits_c5_1d.py", "explore", "--npz", npz[500], "--hi", "500", "--lo", str(lo),
                             "--scheme", s, "--logs", "none,free"])
                keys.append(os.path.join(PKG, "fits", "explore", "L500", f"explore_{s}_lo{lo}.log"))
        pat = re.compile(r"^(\w+)\s+log=(\w+)\s+lo=\s*(\d+) .*A=([0-9.+-]+)")
        mism, nfit = [], 0
        for k, out in zip(keys, runmany(jobs, env={"OMP_NUM_THREADS": "1"})):
            got = [m.group(1, 2, 3, 4) for m in (pat.match(ln) for ln in out.split("\n")) if m]
            exp = [m.group(1, 2, 3, 4) for m in (pat.match(ln) for ln in open(k)) if m]
            nfit += len(got)
            if got != exp:
                mism.append(os.path.basename(k))
        row("x5.explore", not mism, f"{nfit} refits; differing logs {mism}")
        # x5.tail
        jobs, keys = [], []
        for b in ("L2", "M3", "M3x"):
            jobs.append(["fits/tail_fixedA_c5.py", "--npz", npz[500], "--bases", b, "--lo", "80,120,160,200"])
            keys.append(os.path.join(PKG, "fits", "explore", "L500", f"tailA_{b}.log"))
        mism = []
        for k, out in zip(keys, runmany(jobs, env={"OMP_NUM_THREADS": "1"})):
            got = [ln for ln in out.split("\n") if ln and not ln.startswith("#")]
            exp = [ln.rstrip("\n") for ln in open(k) if ln.strip() and not ln.startswith("#")]
            if got != exp:
                mism.append(os.path.basename(k))
        m3 = [ln for ln in open(keys[1]) if ln.startswith("M3 ")]
        c13 = [re.search(r"c13=([0-9.+-]+)", ln).group(1) for ln in m3]
        row("x5.tail", not mism, f"3 bases x 4 lo with profiles; differing logs {mism}; M3 c13 (lo 80..200) = {c13}")
        # x5.constrained
        out_json = os.path.join(os.path.abspath(a.work), "constrained_c5_replay.json")
        if os.path.exists(out_json):
            os.remove(out_json)
        run(["fits/constrained_c5.py", "--c4npz", C4NPZ, "--c5npz", npz[500], "--out", out_json,
             "--procs", str(a.procs)], env={"OMP_NUM_THREADS": "1"})
        g = json.load(open(out_json))
        e = json.load(open(os.path.join(PKG, "fits", "explore", "constrained_L500", "constrained_c5_v2.json")))

        def close(x, y):
            return abs(x - y) <= 1e-9 * max(1.0, abs(y))
        ok = (all(close(g[k][0], e[k][0]) for k in ("c2", "c3", "c4")) and close(g["c13"], e["c13"])
              and close(g["dc13"], e["dc13"]) and len(g["table"]) == len(e["table"])
              and all(close(x["A"], y["A"]) for x, y in zip(g["table"], e["table"])))
        sel = [x["A"] for x in g["table"] if x["cond"] <= g["cond_max5"]]
        r3 = abs(g["c3"][0] / (-3.5 * g["c2"][0]) - 1)
        r4 = abs(g["c4"][0] / (-1.75 * g["c3"][0]) - 1)
        m3, e3 = f"{r3:.0e}".split("e")
        t3, t4 = m3 + r"\times10^{" + str(int(e3)) + "}", f"{100 * r4:.1f}\\%"
        row("x5.toplog", t3 == r"5\times10^{-6}" and t4 == r"0.3\%",
            f"top-log relation c_n = -(7/2)/(n-2) c_(n-1) on the exact C2..C4 (fixed intercepts, cond <= 1e12): "
            f"|c3/(-3.5 c2) - 1| = {r3:.2e} -> {t3}; |c4/(-1.75 c3) - 1| = {r4:.2e} -> {t4} "
            f"(quoted 5\\times10^{{-6}}, 0.3\\%)")
        row("x5.constrained", ok, f"c3/(-3.5 c2) = {g['c3'][0] / (-3.5 * g['c2'][0]):.6f}, c13 = {g['c13']:.4f} "
            f"+- {g['dc13']:.4f}, A (cond <= 1e14) = {', '.join(f'{v:.4f}' for v in sel)}")

    # x5.crosscheck
    X = os.path.join(PKG, "fits", "explore", "constrained_L500", "xchk")
    need = ["REPORT_blind.md", "REPORT_theory.md", "cfit_blind/summary_c5.json", "cfit_blind/xfit.py"]
    have = all(os.path.exists(os.path.join(X, f)) for f in need)
    quoted = have and "−731.13 ± 0.10" in open(os.path.join(X, "REPORT_blind.md"), encoding="utf-8").read()
    row("x5.crosscheck", have and quoted, "cited checks present; blind re-implementation quotes C5 = -731.13 +- 0.10")

    # x5.c5: the paper's d = 1 HT C5 from the separately written constrained fit (cited check)
    sm = json.load(open(os.path.join(X, "cfit_blind", "summary_c5.json")))
    va = sorted(r["A"] for r in sm["rows"] if r["basis"] == "A[3,2,3]" and r["hi"] == 500 and r["lo"] in (50, 60, 70, 80))
    med = (va[1] + va[2]) / 2 if len(va) == 4 else float("nan")
    rep = open(os.path.join(X, "REPORT_blind.md"), encoding="utf-8").read()
    budget = "±0.08" in rep and "±0.004–0.02" in rep and "−731.13 ± 0.10" in rep
    import math
    dev = abs(med / C5_EXACT - 1)
    m, e = f"{dev:.0e}".split("e")
    txt = (f"{med:.2f}(10)", m + r"\times10^{" + str(int(e)) + "}")
    row("x5.c5", len(va) == 4 and budget and txt == (QUOTED_C5["value"], QUOTED_C5["dev"]),
        f"basis A, lo 50-80, Λ <= 500: {', '.join(f'{v:.4f}' for v in va)} -> median {med:.4f}; uncertainty 0.10 = the "
        f"report's budget (noise ±0.004-0.02, bases and truncation ±0.08): {txt[0]}, rel {txt[1]} "
        f"(quoted {QUOTED_C5['value']}, {QUOTED_C5['dev']})")

    w = max(len(r[0]) for r in ROWS)
    for rid, st, det in ROWS:
        print(f"{rid:{w}s}  {st:4s}  {det}")
    nf = sum(r[1] == "FAIL" for r in ROWS)
    print(f"# {len(ROWS)} rows, {nf} FAIL")
    sys.exit(1 if nf else 0)


if __name__ == "__main__":
    main()
