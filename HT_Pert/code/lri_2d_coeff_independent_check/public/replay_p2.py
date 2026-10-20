#!/usr/bin/env python3
"""Replay every quoted d = 2 perturbative-HT number from the shipped records (no solver run).

Run from HT_Pert/code/lri_2d_coeff_independent_check (make -f public.mk replay). Inputs, all relative to that folder:
  rs_exact/results, cauchy/results, continuum/, c4_exact/results, complete_exact/results, residual_log/...  (this package)
  ../../data/HT_2d/prod/{check_small_symmetry,prod1_symmetry,prod2_expanse}/d8/*.json   (production records)
Every check recomputes its number from those files (fits, differences, exact-rational comparisons) and compares it
with the value quoted in the HT_Pert note (Sec. 4 and Appendices A to C: the paper's macros \\HTp*Two*, \\HTpTwo*,
\\HTnpDtwoCfourLog under their paper names and values, and the note-only macros \\NTwo*); the paper (Sec. 3.1, Table 2)
prints C2 to C5 and their deviations. Check names (p2.*) are those of results_map.md. Prints one line per
check and a summary; exit status 1 on any FAIL.

Tolerances: the inputs are exact rationals or float64 data accurate to ~1e-12; the fits are column-scaled float64
least squares, reproducible to far better than the digits quoted. A quoted value is checked at the digits it is
quoted with ("2 significant digits" means the recomputed value rounds to the quoted one), a bound by the inequality.
Needs numpy and mpmath (mpmath only for the C2 digits and the Cauchy comparison).
"""
import argparse
import csv
import glob
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from fractions import Fraction as Fr
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parent.parent
ROWS = []
NOTES = []


def check(name, ok, value, expected, tol):
    ROWS.append((name, "PASS" if ok else "FAIL", str(value), str(expected), str(tol)))


def sig(v, n=2):
    return float(f"{v:.{n}g}")


def rounds_to(v, quoted, ndp):
    """v rounded to ndp decimals equals the quoted number (half-way cases accepted either way)."""
    return abs(v - quoted) <= 0.5 * 10.0 ** (-ndp) * (1 + 1e-9)


# ----------------------------------------------------------------------------------------------- fit helpers
def cols_named(L, names):
    l = np.log(L)
    out = []
    for n in names:
        if n == "1":
            out.append(np.ones_like(L))
        elif n == "l":
            out.append(l)
        elif n == "L":
            out.append(L)
        elif "/" not in n:  # "l2", "l3": powers of ln L
            out.append(l ** int(n[1:]))
        else:
            num, den = n.split("/")
            k = 0 if num == "1" else (1 if num == "l" else int(num[1:]))
            j = int(den[1:]) if len(den) > 1 else 1
            out.append(l ** k / L ** j)
    return np.column_stack(out)


def lsq(L, y, names, Lmin, Lmax=None, fixed=None):
    """Column-scaled float64 least squares (the protocol of fitlib.py in the snapshot)."""
    sel = (L >= Lmin) & ((L <= Lmax) if Lmax else True)
    Ls, ys = L[sel].astype(float), y[sel].astype(float).copy()
    if fixed:
        for n, v in fixed.items():
            ys -= v * cols_named(Ls, [n])[:, 0]
    X = cols_named(Ls, names)
    sc = np.abs(X).max(axis=0)
    c, *_ = np.linalg.lstsq(X / sc, ys, rcond=None)
    c = c / sc
    return dict(zip(names, c)), float(np.abs(ys - X @ c).max())


def tower(k1, k2, k3=None):
    nm = lambda k, d: ("1" if k == 0 else ("l" if k == 1 else f"l{k}")) + d
    out = [nm(k, "/L") for k in range(k1 + 1)] + [nm(k, "/L2") for k in range(k2 + 1)]
    if k3 is not None:
        out += [nm(k, "/L3") for k in range(k3 + 1)]
    return out


# C5 refit protocol (residual_log/fits/parent_check_largeL/refit_c5_300.py): [1, ln^k L/L (k <= k1), ln^k L/L^2 (k <= k2)]
def c5cols(L, k1, k2, log):
    c = [np.ones_like(L)] + [np.log(L) ** k / L for k in range(k1 + 1)] + [np.log(L) ** k / L ** 2 for k in range(k2 + 1)]
    if log:
        c.append(np.log(L))
    return np.column_stack(c)


def c5fit(L, y, lo, hi, k1, k2, log):
    m = (L >= lo) & (L <= hi)
    A = c5cols(L[m], k1, k2, log)
    sc = np.abs(A).max(0)
    return np.linalg.lstsq(A / sc, y[m], rcond=None)[0] / sc


LMIN5, K25 = (30, 40, 60, 80, 100), (0, 1, 2)


def c5blind(L, y, hi, k1, log):
    m = L > hi
    e = [np.abs(c5cols(L[m], k1, k2, log) @ c5fit(L, y, lo, hi, k1, k2, log) - y[m]).max() for lo in LMIN5 for k2 in K25]
    return float(np.median(e))


# ----------------------------------------------------------------------------------------------- loaders
def refs():
    out = {}
    with open(PKG / "continuum" / "reference_values.csv") as fh:
        for r in csv.DictReader(fh):
            out[int(r["n"])] = float(r["C_n(2)"])
    return out


def prod_record(prod, scheme, L):
    for sub in ("check_small_symmetry", "prod1_symmetry", "prod2_expanse"):
        p = prod / sub / "d8" / f"{scheme}_L{L}.json"
        if p.exists():
            return json.loads(p.read_bytes())["payload"]["result"], sub
    return None, None


def ce_load(pattern, scheme):
    out = {}
    for f in glob.glob(str(PKG / "residual_log" / "ce_wc" / pattern)):
        j = json.load(open(f))
        if scheme not in j["schemes"]:
            continue
        L = j["meta"]["args"]["L"]
        out.setdefault(L, {}).update({k: Fr(x) for k, x in j["schemes"][scheme]["values"].items() if x is not None})
        out[L].setdefault("_bad", set()).update(j["schemes"][scheme]["bad"])
        if j["meta"]["args"].get("delta3"):
            out[L]["_delta3"] = Fr(j["meta"]["args"]["delta3"])
    return out


def Rdesc(v, dn, n):
    prim = 1 if dn.startswith("odd") else 2
    k = f"Ed|{dn}|{n}"
    if k not in v or k in v["_bad"]:
        return None
    return float(v[k] - v[f"E|{prim}|{n}"])


def w_aa(a):
    return (math.gamma(a + 0.5) / math.gamma(0.5) / math.factorial(a)) ** 2


# ----------------------------------------------------------------------------------------------- checks
def snapshot_integrity():
    lst = PKG / "public" / "SNAPSHOT.sha256"
    scr = PKG / "public" / "SCRUBBED.txt"
    scrubbed = set()
    if scr.exists():
        scrubbed = {x.split("  ", 1)[-1].strip() for x in scr.read_text().splitlines() if x.strip() and not x.startswith("#")}
    n = bad = miss = ns = 0
    for line in lst.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        h, rel = line.split("  ", 1)
        p = PKG / rel
        n += 1
        if not p.is_file():
            miss += 1
            NOTES.append(f"snapshot: missing {rel}")
            continue
        if rel in scrubbed:
            ns += 1
            continue
        if hashlib.sha256(p.read_bytes()).hexdigest() != h:
            bad += 1
            NOTES.append(f"snapshot: sha256 differs {rel}")
    check("p2.snapshot", bad == 0 and miss == 0, f"{n} files listed, {bad} differ, {miss} missing, {ns} scrubbed (exist)",
          "every snapshot file present and byte-identical (scrubbed files: present)", "sha256")


def impl_agreement(prod):
    """\\HTpTwoImplAgree: clean-room exact RS vs the production solver (compare_with_package.py, relative paths)."""
    def err(a, b):
        return max(abs(x - y) / max(1, abs(y)) for x, y in zip(a, b))
    ex = lambda v: [float(Fr(z)) for z in v]
    worst, npair = 0.0, 0
    for f in sorted(glob.glob(str(PKG / "rs_exact" / "results" / "*.json"))):
        d = json.load(open(f))
        s, L = d["scheme"], int(d["L"])
        p, _ = prod_record(prod, s, L)
        if p is None:
            continue
        e = [err(p["C"], ex(d["C"])), err(p["r"], ex(d["r"])), err(p["g"], ex(d["g"])),
             max(err(pe, ex(de)) for pe, de in zip(p["energies"], d["E"]))]
        grids = list(range(0, L + 1, 2)) if s != "raw" else [L]
        if len(p["vacuum_coefficients"]) != len(grids):
            e.append(float("inf"))
        else:
            e.append(max(err(row, ex(d["vacua"][str(l)])) for row, l in zip(p["vacuum_coefficients"], grids)))
        worst = max(worst, max(e))
        npair += 1
    check("p2.impl_agree", npair == 25 and 3.8e-13 <= worst <= 3.9e-13 and sig(worst, 1) == 4e-13,
          f"{npair} (scheme, L) pairs; worst scaled difference {worst:.3e}", "25 pairs; 3.86e-13 (quoted 4e-13)",
          "1 significant digit; value in [3.8, 3.9]e-13")
    Ls = sorted({int(json.load(open(f))["L"]) for f in glob.glob(str(PKG / "rs_exact" / "results" / "*.json"))})
    check("p2.rs_lmax", Ls == list(range(0, 19, 2)), f"L = {Ls[0]}..{Ls[-1]} ({len(Ls)} values)", "L = 0..18 (\\NTwoRSLmax)", "exact")


def cauchy_agreement(prod):
    from mpmath import mp, mpf
    mp.dps = 60
    def scaled(a, b):
        return max(abs(mpf(x) - mpf(y)) / max(1, abs(mpf(y))) for x, y in zip(a, b))
    cv = lambda v: [mpf(e["value"]) if isinstance(e, dict) else mpf(e) for e in v]
    worst_cr, worst_cp, n, Ls = mpf(0), mpf(0), 0, set()
    for f in sorted(glob.glob(str(PKG / "cauchy" / "results" / "*.json"))):
        c = json.load(open(f))
        s, L = c["scheme"], int(c["L"])
        Ls.add(L)
        r = json.load(open(PKG / "rs_exact" / "results" / f"{s}_L{L}.json"))
        ex = lambda v: [mpf(Fr(z).numerator) / Fr(z).denominator for z in v]
        d = [scaled(cv(c["C"]), ex(r["C"])), scaled(cv(c["r"]), ex(r["r"])), scaled(cv(c["g"]), ex(r["g"])),
             max(scaled(cv(c["E"][str(p)]), ex(r["E"][p])) for p in range(4))]
        worst_cr = max(worst_cr, max(d))
        n += 1
        p, _ = prod_record(prod, s, L)
        if p:
            worst_cp = max(worst_cp, scaled([mpf(x) for x in p["C"]], cv(c["C"])))
    wcr, wcp = float(worst_cr), float(worst_cp)
    check("p2.cauchy_vs_rs", n == 15 and wcr <= 5e-46 and sig(wcr, 1) == 5e-46, f"{n} cases; worst {wcr:.2e}",
          "15 cases; 4.76e-46 (\\NTwoCauchyAgree 5e-46)", "1 significant digit")
    check("p2.pkg_vs_cauchy", sig(wcp, 2) == 1.6e-14, f"worst C difference {wcp:.2e}", "1.56e-14 (\\NTwoPkgCauchy 1.6e-14)",
          "2 significant digits")
    check("p2.cauchy_lmax", sorted(Ls) == [0, 2, 4, 6, 8], f"L = {sorted(Ls)}", "L = 0..8 (\\NTwoCauchyLmax)", "exact")


def low_orders(prod, REF):
    rows = list(csv.DictReader(open(PKG / "continuum" / "exact_C2_C3.csv")))
    L = np.array([float(r["L"]) for r in rows])
    C2 = np.array([float(r["C2"]) for r in rows])
    C3 = np.array([float(r["C3"]) for r in rows])
    # exact C2(L), C3(L) code vs the production solver, L = 2..34 (both schemes; identical through eps^3)
    worst = 0.0
    nL = 0
    for Lv, c2, c3 in zip(L, C2, C3):
        if Lv > 34:
            continue
        for s in ("raw", "consistent"):
            p, _ = prod_record(prod, s, int(Lv))
            if p:
                worst = max(worst, abs(p["C"][2] - c2), abs(p["C"][3] - c3))
                nL += 1
    check("p2.low_agree", worst <= 4.5e-14 and sig(worst, 1) == 4e-14, f"max |diff| {worst:.2e} over {nL} records",
          "<= 4e-14 (\\NTwoLowAgree)", "1 significant digit")
    # C2(inf): closed form, 35 digits of 4 log2 / 9
    from mpmath import mp, mpf, rf, factorial, nsum, inf, log
    mp.dps = 50
    w = lambda a: (rf(mpf(1) / 2, a) / factorial(a)) ** 2
    summand = lambda a: w(a) * (2 / (2 * a - 1) + mpf(18) / (2 * a) + mpf(18) / (2 * a + 1) + mpf(2) / (2 * a + 2))
    c2inf = (17 + nsum(summand, [1, inf])) / 81
    target = 4 * log(2) / 9
    rel = abs(c2inf - target) / target
    digits = int(-mp.log10(rel)) if rel > 0 else 50
    check("p2.c2_digits", digits >= 35 and abs(float(c2inf) - 0.30806541358) < 5e-12,
          f"C2(inf) = {mp.nstr(c2inf, 36)}; agrees with 4 log2/9 to {digits} digits",
          "0.30806541358 (\\HTpCtwoTwo), 35 digits (\\HTpCtwoTwoDigits)", ">= 35 digits at 50-digit working precision")
    # the closed form is the HT C2(L): compare with the exact-code table at every tabulated L
    worst2 = 0.0
    for Lv, c2 in zip(L, C2):
        v = (17 + sum(summand(a) for a in range(1, int(Lv) // 2 + 1))) / 81
        worst2 = max(worst2, abs(float(v) - c2))
    check("p2.c2_closed_form", worst2 <= 1e-13, f"max |closed form - exact code| = {worst2:.1e} ({len(L)} L values)",
          "closed form = HT C2(L)", "<= 1e-13 (float64 sums of the exact code to L = 600)")
    # C3(inf): richest tail basis of continuum/asymptotics_C2_C3.py, Lmin 32/64/128
    names = ["1", "l/L", "1/L", "l/L2", "1/L2", "l2/L2", "l/L3", "1/L3"]
    lim, tail = [], []
    for Lmin in (32, 64, 128):
        c, _ = lsq(L, C3, names, Lmin)
        lim.append(c["1"])
        tail.append(c["l/L"])
    ok = all(abs(x - (-0.8748500)) <= 1e-7 for x in lim)
    check("p2.c3_limit", ok, "C3(inf) fits " + ", ".join(f"{x:.10f}" for x in lim), "-0.8748500(1) (\\HTpCthreeTwo)",
          "every fit within 1e-7 of -0.8748500")
    dev = abs(-0.8748500 - REF[3]) / abs(REF[3])
    check("p2.c3_dev", sig(dev, 1) == 1e-8, f"|C3 - exact|/|exact| = {dev:.2e}", "1e-8 (\\HTpCthreeTwoDev)", "1 significant digit")
    check("p2.c3_lmax", int(L.max()) == 600, f"exact C3(L) to L = {int(L.max())}", "600 (\\NTwoCthreeLmax)", "exact")
    check("p2.c3_tail", rounds_to(tail[1], 0.70734, 5) and abs(tail[1] - 4.5 * 40 / (81 * math.pi)) < 5e-5,
          f"ln L / L coefficient {tail[1]:.6f} (Lmin 64); (9/2) 40/(81 pi) = {4.5 * 40 / (81 * math.pi):.6f}",
          "0.70734 (\\NTwoCthreeTail)", "5 decimals")
    return dev


def c4_checks(prod, REF):
    d = np.load(PKG / "c4_exact" / "results" / "c4_L2000.npz")
    w = np.load(PKG / "c4_exact" / "results" / "windows_L20000.npz")
    L = d["L"].astype(float)
    Lw = w["L"].astype(float)
    check("p2.c4_lfour", int(L.max()) == 2000 and np.array_equal(d["L"], np.arange(0, 2001, 2)),
          f"exact C4(L), every even L <= {int(L.max())}", "2000 (\\HTpTwoLfour)", "exact")
    # window shift Delta_cons = kappa L + lambda ln L + c (fits_c4.py sec. 1)
    cd, _ = lsq(Lw, w["Delta_cons"], ["L", "l", "1"] + tower(2, 2), 2000)
    check("p2.c4_kappa", rounds_to(cd["L"] * 1e4, 2.2073, 4) and abs(cd["L"] - 2.20729299645267e-4) < 1e-14,
          f"kappa = {cd['L']:.12e} (analytic 2.20729299645267e-4)", "2.2073e-4 (\\NTwoKappa)", "4 decimals of 1e4 kappa")
    # stable set of fits_c4.py sec. 5: {log T22, log T22+l3/L} x {c2 free, c2 = -5/pi} x Lmin {200, 300, 400}
    LOGM = {"log T22": ["1", "l"] + tower(2, 2), "log T22+l3/L": ["1", "l", "l3/L"] + tower(2, 2)}
    C2TH = -5.0 / math.pi
    summ = {}
    for key in ("C4corr", "C4cons"):
        A, B = [], []
        for names in LOGM.values():
            for fixc2 in (False, True):
                nn = [x for x in names if not (fixc2 and x == "l2/L")]
                for Lmin in (200, 300, 400):
                    c, _ = lsq(L, d[key], nn, Lmin, None, {"l2/L": C2TH} if fixc2 else None)
                    A.append(c["1"])
                    B.append(c["l"])
        A, B = np.array(A), np.array(B)
        summ[key] = (np.median(A), (A.max() - A.min()) / 2, np.median(B), (B.max() - B.min()) / 2, len(A))
    Acons, dAcons, Bcons, dBcons, nf = summ["C4cons"]
    Acorr, dAcorr, Bcorr, dBcorr, _ = summ["C4corr"]
    th_cons = -365 / (4374 * math.pi)
    check("p2.c4_log_consistent", round(Bcons, 3) == -0.027 and abs(Bcons - th_cons) <= 5e-6 and rounds_to(Bcons, -0.026563, 6)
          and rounds_to(dBcons, 0.000042, 6),
          f"beta_cons = {Bcons:+.6f} +- {dBcons:.6f} ({nf} fits); -365/(4374 pi) = {th_cons:+.6f}",
          "-0.027 (\\HTnpDtwoCfourLog); -0.026563(42) (\\NTwoCfourConsB)", "3 decimals (\\HTnpDtwoCfourLog), 6 decimals (\\NTwoCfourConsB)")
    th_corr = -8 / (243 * math.pi)
    check("p2.c4_log_zm", rounds_to(Bcorr, -0.010480, 6) and rounds_to(dBcorr, 0.000042, 6) and abs(Bcorr - th_corr) <= 5e-6,
          f"beta_zm = {Bcorr:+.6f} +- {dBcorr:.6f}; -8/(243 pi) = {th_corr:+.6f}", "-0.010480(42) (\\NTwoCfourZmB)", "6 decimals")
    Braw = Bcons - cd["l"]
    Araw = Acons - cd["1"]
    check("p2.c4_log_raw", rounds_to(Braw, -0.026381, 6) and abs(Braw + 725 / (8748 * math.pi)) <= 5e-6,
          f"beta_raw = beta_cons - lambda = {Braw:+.6f}; -725/(8748 pi) = {-725 / (8748 * math.pi):+.6f}",
          "-0.026381 (\\NTwoCfourRawB)", "6 decimals")
    check("p2.c4_A_schemes", rounds_to(Acons, 5.0026, 4) and rounds_to(dAcons, 0.0005, 4) and rounds_to(Acorr, 5.0213, 4)
          and rounds_to(Araw, 5.0021, 4),
          f"A_cons = {Acons:.5f} +- {dAcons:.5f}, A_zm = {Acorr:.5f} +- {dAcorr:.5f}, A_raw = {Araw:.5f}",
          "5.0026(5), 5.0213(5), 5.0021 (\\NTwoCfourConsA, ZmA, RawA)", "4 decimals")
    # blind L = 2000 test of predictions recorded from L <= 1000 (fits/blind_predictions_L1200_2000.json)
    b = json.load(open(PKG / "c4_exact" / "fits" / "blind_predictions_L1200_2000.json"))
    logmax, nologmin, nologmin_all = 0.0, float("inf"), float("inf")
    for key, preds in b["pred"].items():
        for mname, pv in preds.items():
            for i, Lp in enumerate(b["L"]):                       # every predicted cutoff, L = 1200..2000
                dd = abs(pv[i] - d[key][int(Lp) // 2])
                if mname.startswith("log"):
                    logmax = max(logmax, dd)
                else:
                    nologmin_all = min(nologmin_all, dd)
                    if int(Lp) == 2000:
                        nologmin = min(nologmin, dd)
    check("p2.c4_blind", sig(logmax, 2) == 8.3e-8 and sig(nologmin, 2) == 4.1e-7,
          f"L = 1200..2000: log models miss by <= {logmax:.2e}; L = 2000: no-log models by >= {nologmin:.2e} "
          f"(over L = 1200..2000 by >= {nologmin_all:.1e})",
          "8.3e-8 (\\NTwoBlindLogMax, max over L = 1200..2000), 4.1e-7 (\\NTwoBlindNoLogMin, at L = 2000)",
          "2 significant digits")
    slope = (d["r2"][1000] - d["r2"][999]) / 2
    check("p2.r2_slope", rounds_to(slope, 0.0235785, 7) and abs(slope - 2 / (27 * math.pi)) < 1e-6,
          f"[r2(2000) - r2(1998)]/2 = {slope:.8f}; 2/(27 pi) = {2 / (27 * math.pi):.8f}",
          "0.0235785 (\\NTwoRtwoSlope; note: r_2 ~ 2L/(27 pi))", "7 decimals")
    # complete window W (residual_log/fits_final.py): C4W = C4corr + off-diagonal + chi-line shifts
    o = np.load(PKG / "residual_log" / "results" / "offdiag_L20000.npz")
    n8 = np.load(PKG / "residual_log" / "results" / "nm_L8000.npz")
    K = len(L)
    c4w = d["C4corr"] + o["off"][:K] + n8["dC4"][:K]
    c4zo = d["C4corr"] + o["off"][:K]
    tw = {"T22": tower(2, 2), "T22+l3/L": ["1/L", "l/L", "l2/L", "l3/L", "1/L2", "l/L2", "l2/L2"],
          "T23": ["1/L", "l/L", "l2/L", "1/L2", "l/L2", "l2/L2", "l3/L2"]}
    def stable(y):
        return np.array([lsq(L, y, ["1"] + t, Lmin)[0]["1"] for t in tw.values() for Lmin in (200, 300, 400)])
    st = stable(c4w)
    A4, dA4 = float(np.median(st)), float((st.max() - st.min()) / 2)
    check("p2.c4W_limit", rounds_to(A4, 5.0488682, 7) and dA4 <= 1e-6,
          f"C4^W(inf) = {A4:.8f} +- {dA4:.1e} (9 no-log fits); exact {REF[4]:.10f}", "5.0488682(10) (\\HTpCfourTwo)",
          "7 decimals; half spread <= 1e-6")
    check("p2.c4W_spread", sig(dA4, 1) == 6e-7, f"half spread {dA4:.2e}", "6e-7 (\\NTwoCfourWFitSpread)", "1 significant digit")
    dev4 = abs(5.0488682 - REF[4]) / REF[4]
    check("p2.c4_dev", sig(dev4, 1) == 5e-8, f"|5.0488682 - exact|/exact = {dev4:.2e}", "5e-8 (\\HTpCfourTwoDev)",
          "1 significant digit")
    blog = [abs(lsq(L, c4w, ["1", "l"] + t, Lmin)[0]["l"]) for t in tw.values() for Lmin in (200, 300)]
    check("p2.c4W_nolog", sig(max(blog), 2) == 3.5e-6, f"max |free ln L coefficient| = {max(blog):.2e} (3 towers x Lmin 200, 300)",
          "3.5e-6 (\\NTwoCfourWLogMax)", "2 significant digits")
    zo = stable(c4zo)
    check("p2.c4_zmoff", rounds_to(float(np.median(zo)), 5.0386139, 7),
          f"C4corr + off-diagonal: {np.median(zo):.8f}", "5.0386139 (\\NTwoCfourZmOff)", "7 decimals")
    Ln = n8["L"].astype(float)
    chi = [lsq(Ln, n8["dC4"], ["1"] + tower(1, 2), Lmin)[0]["1"] for Lmin in (400, 1000, 2000)]
    check("p2.c4_chi", all(rounds_to(x, 0.0102543, 7) for x in chi), "dC4_chi(inf) = " + ", ".join(f"{x:.10f}" for x in chi),
          "0.0102543 (\\NTwoCfourChi)", "7 decimals, Lmin 400/1000/2000")
    # check that the shipped table C4W_by_L.csv is this series
    rows = list(csv.DictReader(open(PKG / "residual_log" / "C4W_by_L.csv")))
    tab = np.array([float(r["C4_W"]) for r in rows])
    check("p2.c4W_table", len(tab) == K and np.abs(tab - c4w).max() <= 1e-13, f"max |C4W_by_L.csv - series| = {np.abs(tab - c4w).max():.1e}",
          "C4W_by_L.csv = C4corr + off + dC4_chi", "<= 1e-13")
    # agreement of the large-L C4 code with exact RS (L <= 18) and the package (L <= 34)
    worst = 0.0
    for f in glob.glob(str(PKG / "rs_exact" / "results" / "*.json")):
        r = json.load(open(f))
        if r["scheme"] in ("raw", "consistent") and int(r["L"]) >= 2:
            Lv = int(r["L"])
            v = d["C4raw" if r["scheme"] == "raw" else "C4cons"][Lv // 2]
            ex = float(Fr(r["C"][4]))
            worst = max(worst, abs(v - ex) / abs(ex))
    for Lv in range(2, 35, 2):
        for s, key in (("raw", "C4raw"), ("consistent", "C4cons")):
            p, _ = prod_record(prod, s, Lv)
            if p:
                worst = max(worst, abs(d[key][Lv // 2] - p["C"][4]) / abs(p["C"][4]))
    rec = (PKG / "c4_exact" / "validate_rs.txt").read_text()
    m = re.findall(r"worst relative deviations: \{[^}]*'C4raw': '([0-9.e-]+)', 'C4cons': '([0-9.e-]+)'\}", rec)
    recw = max(float(x) for x in m[-1]) if m else float("nan")
    check("p2.c4_agree", worst <= 1.1e-13 and recw == 1.1e-13,
          f"shipped c4_L2000.npz vs exact RS (L <= 18) and package (L <= 34): max rel {worst:.2e}; "
          f"recorded validation (c4_exact/validate_rs.txt, production pruning): {recw:.1e}",
          "1.1e-13 (\\NTwoCfourAgree)", "recomputed <= 1.1e-13; record = 1.1e-13")
    return dev4


def c5_checks(prod, REF):
    RL = PKG / "residual_log"
    p = np.load(RL / "large_L" / "results" / "c5_L300.npz")
    p2 = np.load(RL / "results" / "eps5" / "c5_L200.npz")
    dd = np.load(RL / "results" / "eps5" / "dC5_L1000_all.npz")
    s = np.load(RL / "results" / "legw" / "legw_L1000.npz")
    t = np.load(RL / "large_L" / "results" / "tag3_L16000.npz")
    L = p["L"].astype(float)
    n = len(L)
    check("p2.c5_lfive", int(L.max()) == 300 and np.array_equal(p["L"], np.arange(0, 301, 2)),
          f"exact raw C5(L), every even L <= {int(L.max())}", "300 (\\HTpTwoLfive)", "exact")
    n2 = len(p2["L"])
    rel = max(float(np.max(np.abs(p[k][1:n2] / p2[k][1:] - 1))) for k in ("raw_C5",))
    check("p2.c5_assembly", sig(rel, 2) == 7.6e-13, f"L <= 200 overlap with the production run: max rel diff (C5) {rel:.2e}",
          "7.6e-13 (\\NTwoOptAssembly)", "2 significant digits")
    worst = 0.0
    for Lv in range(2, 35, 2):
        q, _ = prod_record(prod, "raw", Lv)
        if q:
            for k in (2, 3, 4, 5):
                worst = max(worst, abs(p[f"raw_C{k}"][Lv // 2] - q["C"][k]) / abs(q["C"][k]))
    rec = (RL / "results" / "eps5" / "validation_c5.txt").read_text()
    recw = max(float(x) for x in re.findall(r"vs package d8 \(L<=34\)\s+C[2-5]: ([0-9.e-]+)", rec))
    check("p2.c5_agree", worst <= 2.2e-13 and recw == 2.2e-13,
          f"shipped c5_L300.npz raw C2..C5 vs package L <= 34: max rel {worst:.2e}; recorded validation "
          f"(results/eps5/validation_c5.txt, raw and consistent): {recw:.1e}", "2.2e-13 (\\NTwoCfiveAgree)",
          "recomputed <= 2.2e-13; record = 2.2e-13")
    for k in ("L",):
        assert np.array_equal(dd[k][:n], p[k]) and np.array_equal(s[k][:n], p[k]) and np.array_equal(t[k][:n], p[k])
    c5wc = p["raw_C5"] + dd["Wc_dC5"][:n]
    c5wcs = c5wc + t["delta3"][:n] * s["S"][:n]
    c4w = p["raw_C4"] + dd["Wb_dC4"][:n]
    EX5 = REF[5]
    A0 = np.array([c5fit(L, c5wcs, lo, 300, 3, k2, False)[0] for lo in LMIN5 for k2 in K25])
    med, hr = float(np.median(A0)), float((A0.max() - A0.min()) / 2)
    check("p2.c5_limit", rounds_to(med, -38.835, 3) and rounds_to(hr, 0.013, 3) and abs(med + 38.83544) < 5e-6,
          f"C5^Wcs(inf) = {med:.5f} +- {hr:.5f} (15 no-log fits, k1 = 3); exact {EX5:.7f}",
          "-38.835(13) (\\HTpCfiveTwo); median -38.83544, half range 0.01277", "3 decimals; median to 5e-6")
    dev5 = abs(med - EX5) / abs(EX5)
    check("p2.c5_dev", sig(dev5, 1) == 5e-5, f"|median - exact|/|exact| = {dev5:.2e}", "5e-5 (\\HTpCfiveTwoDev)", "1 significant digit")
    e0, e1 = c5blind(L, c5wcs, 200, 3, False), c5blind(L, c5wcs, 200, 3, True)
    e0b, e1b = c5blind(L, c5wcs, 200, 2, False), c5blind(L, c5wcs, 200, 2, True)
    check("p2.c5_blind", sig(e0, 2) == 4.3e-6 and sig(e1, 2) == 9.4e-6 and e0b > e1b,
          f"fit <= 200 -> 202..300, k1 = 3: no ln L {e0:.2e}, free ln L {e1:.2e} (k1 = 2: {e0b:.1e} vs {e1b:.1e})",
          "4.3e-6 (\\NTwoBlindNoLog), 9.4e-6 (\\NTwoBlindFreeLog)", "2 significant digits; k1 = 2 prefers a log")
    # tail-power selection (Table d2:tab:k1; large_L/fits/c5_fits300.txt sec. 1): no-log towers T(k1, 1..2), Lmin 40, 60, 80;
    # hold-out fit <= 240 -> 242..300 (median of the largest errors) and limit - exact from fits to L <= 300
    k1tab = {}
    for lab, yy, ref in (("C4W", c4w, REF[4]), ("C5Wcs", c5wcs, EX5)):
        for k1 in range(5):
            es, As = [], []
            for k2 in (1, 2):
                for lo in (40, 60, 80):
                    cc = c5fit(L, yy, lo, 240, k1, k2, False)
                    sel = L > 240
                    es.append(float(np.abs(c5cols(L[sel], k1, k2, False) @ cc - yy[sel]).max()))
                    As.append(float(c5fit(L, yy, lo, 300, k1, k2, False)[0] - ref))
            k1tab[(lab, k1)] = (float(np.median(es)), float(np.median(As)))
    A4 = np.array([c5fit(L, c5wcs, lo, 300, 4, k2, False)[0] for lo in LMIN5 for k2 in K25])
    m4, h4 = float(np.median(A4)), float((A4.max() - A4.min()) / 2)
    e4 = [sig(k1tab[("C4W", k)][0], 2) for k in range(5)]
    e5 = [sig(k1tab[("C5Wcs", k)][0], 2) for k in range(5)]
    a5 = [sig(k1tab[("C5Wcs", k)][1], 2) for k in range(5)]
    check("p2.c5_k1", e4 == [6.1e-4, 9.7e-6, 1.1e-7, 5.2e-8, 6.5e-8] and e5 == [1.2e-2, 3.5e-4, 5.3e-6, 3.7e-7, 5.7e-7]
          and a5 == [0.81, 0.16, 0.015, -0.003, 0.012] and rounds_to(m4, -38.8334, 4) and rounds_to(m4 - med, 0.002, 3)
          and rounds_to(h4, 0.050, 3) and rounds_to(hr, 0.013, 3) and rounds_to(k1tab[("C5Wcs", 4)][1] - k1tab[("C5Wcs", 3)][1], 0.015, 3),
          "k1 = 0..4: C4^W hold-out errors " + ", ".join(f"{x:.1e}" for x in e4) + "; C5^Wcs errors " + ", ".join(f"{x:.1e}" for x in e5)
          + ", limit - exact " + ", ".join(f"{x:+.3f}" for x in a5)
          + f"; 15 fits with k1 = 4: median {m4:.5f} (shift {m4 - med:+.4f} from k1 = 3), half range {h4:.4f} (k1 = 3: {hr:.4f});"
          f" Table k1 towers: k1 = 3 -> 4 moves the limit by {k1tab[('C5Wcs', 4)][1] - k1tab[('C5Wcs', 3)][1]:+.4f}",
          "Table d2:tab:k1; k1 = 4 (15 fits): -38.8334, shift +0.002 (\\NTwoCfiveKfourShift), half range 0.050"
          " (\\NTwoCfiveKfourHalf) vs 0.013; Table k1 shift +0.015 (\\NTwoCfiveKfourTab)", "2 significant digits; 3-4 decimals")
    bmed = {}
    for hi in (200, 240, 280, 300):
        B = np.array([c5fit(L, c5wcs, lo, hi, 3, k2, True)[-1] for lo in LMIN5 for k2 in K25])
        bmed[hi] = (float(np.median(B)), float(B.min()), float(B.max()))
    check("p2.c5_bdrift", rounds_to(bmed[200][0], -0.011, 3) and rounds_to(bmed[300][0], 0.004, 3)
          and abs(bmed[240][0] + 0.00423) < 5e-5 and abs(bmed[280][0] - 0.00295) < 5e-5,
          "free b median by Lmax 200/240/280/300: " + ", ".join(f"{bmed[h][0]:+.5f}" for h in (200, 240, 280, 300)),
          "-0.011 (\\NTwoBfreeTwoHundred), +0.004 (\\NTwoBfreeThreeHundred); -0.00423, +0.00295 at 240, 280", "3 decimals; 5e-5")
    check("p2.c5_bspread", round(bmed[300][1], 2) == -0.05 and round(bmed[300][2], 2) == 0.07,
          f"individual fits at Lmax 300: [{bmed[300][1]:+.4f}, {bmed[300][2]:+.4f}]", "-0.05 .. +0.07 (\\NTwoBfitMin, \\NTwoBfitMax)", "2 decimals")
    lnL = np.log(np.where(L > 0, L, 1.0))
    sh = {}
    for b in (-0.01, 0.01):
        sh[b] = float(np.median([c5fit(L, c5wcs - b * lnL, lo, 300, 3, k2, False)[0] for lo in LMIN5 for k2 in K25])) - med
    check("p2.c5_logshift", sig(abs(sh[-0.01]), 1) == 0.1 and sig(abs(sh[0.01]), 1) == 0.1 and sh[-0.01] > 0 > sh[0.01],
          f"limit shift for b = -0.01 / +0.01: {sh[-0.01]:+.4f} / {sh[0.01]:+.4f}", "0.1 (\\HTpCfiveTwoLog); +0.100 / -0.102",
          "1 significant digit")
    Awc = np.array([c5fit(L, c5wc, lo, 300, 3, k2, False)[0] for lo in LMIN5 for k2 in K25])
    check("p2.c5_wc", rounds_to(float(np.median(Awc)), -38.830, 3) and rounds_to(float((Awc.max() - Awc.min()) / 2), 0.013, 3)
          and abs(float(np.median(Awc)) + 38.8297) < 5e-5,
          f"C5^Wc(inf) = {np.median(Awc):.5f} +- {(Awc.max() - Awc.min()) / 2:.5f}", "-38.830(13) (\\NTwoCfiveWc); -38.8297",
          "3 decimals; 5e-5")
    dS = float(np.median(A0) - np.median(Awc))
    check("p2.c5_wcs_minus_wc", abs(dS - (-4 / (81 * math.pi)) * 0.367187) < 1e-3,
          f"limit(Wcs) - limit(Wc) = {dS:+.4f}", "about delta_inf S_inf = -0.0058", "1e-3")
    # null test: the same estimator on C4^W (no ln L), towers k1 = 2
    Bn = np.array([c5fit(L, c4w, lo, 300, 2, k2, True)[-1] for lo in LMIN5 for k2 in K25])
    An = np.array([c5fit(L, c4w, lo, 300, 2, k2, False)[0] for lo in LMIN5 for k2 in K25])
    check("p2.c5_null", sig(float(np.median(Bn)), 1) == 0.0005 and rounds_to(float(np.median(An)), 5.04868, 5),
          f"C4^W: free b median {np.median(Bn):+.5f}; no-log limit {np.median(An):.5f} +- {(An.max() - An.min()) / 2:.5f}",
          "+0.0005 (\\NTwoBnull); 5.04868", "1 significant digit; 5 decimals")
    # calibration of the large-L agent (large_L/c5_fits300.py sec. 2): 7.7 C4^W + 2 ln^3 L / L + beta ln L
    rows = list(csv.DictReader(open(RL / "C4W_by_L.csv")))
    L4 = np.array([float(r["L"]) for r in rows])
    c4cal = np.array([float(r["C4_W"]) for r in rows])
    m4 = (L4 >= 2) & (L4 <= 300)
    L4, c4cal = L4[m4], c4cal[m4]
    cal = {}
    for beta in (0.0, -0.01, -0.03):
        yy = 7.7 * c4cal + 2.0 * np.log(L4) ** 3 / L4 + beta * np.log(L4)
        cal[beta] = float(np.median([c5fit(L4, yy, lo, 300, 3, k2, True)[-1] for lo in (30, 40, 60, 80) for k2 in K25]))
    check("p2.c5_calibration", all(rounds_to(cal[b], v, 4) for b, v in ((0.0, -0.0036), (-0.01, -0.0136), (-0.03, -0.0336))),
          "estimator on 7.7 C4^W + 2 ln^3L/L + beta ln L, Lmax 300: " + ", ".join(f"beta {b:+.2f} -> {cal[b]:+.4f}" for b in cal),
          "-0.0036, -0.0136, -0.0336 (bias about -0.004)", "4 decimals")
    # the same calibration with the 15 fits of refit_c5_300 (Lmin 30..100), and the bias-corrected medians of b
    cal15 = float(np.median([c5fit(L4, 7.7 * c4cal + 2.0 * np.log(L4) ** 3 / L4, lo, 300, 3, k2, True)[-1]
                             for lo in LMIN5 for k2 in K25]))
    b15 = float(np.median([c5fit(L, c5wcs, lo, 300, 3, k2, True)[-1] for lo in LMIN5 for k2 in K25]))
    b12 = float(np.median([c5fit(L, c5wcs, lo, 300, 3, k2, True)[-1] for lo in (30, 40, 60, 80) for k2 in K25]))
    check("p2.c5_calibration15", rounds_to(cal15, -0.0038, 4) and rounds_to(b15 - cal15, 0.0078, 4)
          and rounds_to(b12 - cal[0.0], 0.0090, 4),
          f"15 fits: estimator reads {cal15:+.4f} on the synthetic series (b = 0); bias-corrected median b: "
          f"{b15 - cal15:+.4f} (15 fits), {b12 - cal[0.0]:+.4f} (12 fits)",
          "-0.0038 (bias about 0.004 in both sets, \\NTwoBbias); +0.0078 (\\NTwoBcorr), +0.0090", "4 decimals")
    # the large-L agent's own b drift (Lmin 30, 40, 60, 80): -0.0134 ... +0.0054
    bag = {hi: float(np.median([c5fit(L, c5wcs, lo, hi, 3, k2, True)[-1] for lo in (30, 40, 60, 80) for k2 in K25]))
           for hi in (200, 300)}
    check("p2.c5_bdrift_agent", rounds_to(bag[200], -0.0134, 4) and rounds_to(bag[300], 0.0054, 4),
          f"12-fit median b at Lmax 200 / 300: {bag[200]:+.4f} / {bag[300]:+.4f}", "-0.0134 / +0.0054 (c5_fits300.txt)", "4 decimals")
    # scheme W = Wb diverges linearly at eps^5
    # scheme W (= Wb) diverges linearly at eps^5: protocol of residual_log/eps5/classes_c5.py on the W shift (L <= 1000)
    Ld = dd["L"].astype(float)
    TOW = (["1/L", "l/L"], ["1/L", "l/L", "l2/L"], ["1/L", "l/L", "l2/L", "1/L2"])
    aW = float(np.median([lsq(Ld, dd["Wb_dC5"], ["L", "1", "l", "l2"] + t_, Lmin)[0]["L"] for t_ in TOW for Lmin in (100, 150, 200)]))
    raw_rec = "Raw carries +0.0004(4) L (profile fit, L <= 160)" in (RL / "WINDOW_SPEC.md").read_text()
    check("p2.c5_W_linear", rounds_to(aW, -0.002329, 6) and raw_rec and round(aW + 0.0004, 4) == -0.0019,
          f"linear coefficient of the W shift {aW:+.6f}; with raw C5's +0.0004(4) L (profile fit, L <= 160: "
          f"residual_log/WINDOW_SPEC.md{'' if raw_rec else ' [record string NOT FOUND]'}; HT_Pert note, App. B.3): {aW + 0.0004:+.4f}",
          "-0.0019 (\\NTwoCfiveWLin)", "6 decimals (shift); 4 decimals (sum)")
    # optimized-engine regression record (large_L/results/regression_opt.txt): worst per-task difference
    txt = (RL / "large_L" / "results" / "regression_opt.txt").read_text()
    vals = [float(x) for x in re.findall(r"\|\s*[\d.]+s\s+([0-9.]+e[-+]\d+)\s", txt)]
    mx = max(vals) if vals else float("nan")
    m2 = re.search(r"([0-9.]+e-16) \(norm-relative\)", txt)
    check("p2.c5_opt_regress", bool(vals) and mx <= 1e-12 and m2 is not None and sig(float(m2.group(1)), 2) == 7.3e-16,
          f"{len(vals)} per-task rows, worst {mx:.1e}; stated worst over 1448 tasks {m2.group(1) if m2 else '?'}",
          "7.3e-16 (\\NTwoOptRegress), requirement <= 1e-12", "record (cited check)")
    return c5wcs


def delta_checks():
    RL = PKG / "residual_log"
    t = np.load(RL / "large_L" / "results" / "tag3_L16000.npz")
    L = t["L"].astype(float)
    y = t["delta3"]
    D3 = -4.0 / (81.0 * math.pi)
    check("p2.delta_lmax", int(L.max()) == 16000, f"delta^(3)(L) to L = {int(L.max())}", "16000 (\\NTwoDeltaLmax)", "exact")
    # exact rationals: from the tagged-phi channel (results/tag) and the inputs of the Wcs runs (ce_wc/out_wcs meta)
    exact = {}
    for f in glob.glob(str(RL / "results" / "tag" / "tag_L*_a1_phi2_2_real.json")):
        dd = json.load(open(f))
        Lv = int(dd["L"])
        c13 = [Fr(x) for x in dd["c1_3"]]
        exact[Lv] = (c13[(Lv - 2) // 2] - (Fr(dd["phi2_2_real"]["c1tag"][3]) - 2 * Fr(dd["r"][3]))) / 4
    wcs = ce_load("out_wcs/*.json", "Wcs")
    same = all(wcs[Lv]["_delta3"] == v for Lv, v in exact.items() if Lv in wcs)
    for Lv in wcs:
        exact.setdefault(Lv, wcs[Lv]["_delta3"])
    diff = max(abs(float(y[Lv // 2]) - float(v)) for Lv, v in exact.items())
    check("p2.delta_rational", same and sig(diff, 1) == 4e-16 and sorted(exact) == list(range(2, 17, 2)),
          f"chain sums vs exact rationals, L = {min(exact)}..{max(exact)}: max |diff| {diff:.1e}; tagged-phi = Wcs inputs: {same}",
          "4e-16 (\\NTwoDeltaRational)", "1 significant digit")
    i0 = int(np.argmin(y[1:])) + 1
    check("p2.delta_min", int(L[i0]) == 34 and rounds_to(float(y[i0]), -0.0159046, 7), f"minimum delta = {y[i0]:.10f} at L = {int(L[i0])}",
          "-0.0159046 at L = 34 (\\NTwoDeltaMin, \\NTwoDeltaMinL)", "7 decimals")
    nm = ["1", "l/L", "1/L", "l/L2", "1/L2"]
    lims = [lsq(L, y, nm, Lmin, 16000)[0]["1"] - D3 for Lmin in (200, 400, 1000, 2000)]
    lims += [lsq(L, y, nm, 200, 4000)[0]["1"] - D3]
    mx = max(abs(x) for x in lims)
    check("p2.delta_limit", mx <= 7e-11, "free-limit fits (1, l/L, 1/L, l/L2, 1/L2; Lmin 200/400/1000/2000 to 16000, and 200..4000) minus (-4/(81 pi)): "
          + ", ".join(f"{x:+.1e}" for x in lims),
          "<= 7e-11 (\\NTwoDeltaIdent); limit -4/(81 pi)", "bound")
    co = [lsq(L, y, ["l/L", "1/L", "l/L2", "1/L2"], Lmin, 16000, {"1": D3})[0] for Lmin in (200, 1000)]
    check("p2.delta_lnL", all(abs(c["l/L"] + 1 / (54 * math.pi)) < 5e-7 for c in co) and all(rounds_to(c["1/L"], 0.01386, 5) for c in co),
          "limit fixed: ln L/L " + ", ".join(f"{c['l/L']:+.7f}" for c in co) + "; 1/L " + ", ".join(f"{c['1/L']:+.6f}" for c in co),
          f"-1/(54 pi) = {-1 / (54 * math.pi):+.7f}; 1/L 0.01386", "5e-7; 5 decimals")
    S = np.load(RL / "results" / "legw" / "legw_L1000.npz")
    Ls = S["L"].astype(float)
    sv = [lsq(Ls, S["S"], ["1", "1/L", "1/L2", "l/L", "l/L2"], Lmin)[0]["1"] for Lmin in (100, 200, 400)]
    bl = [abs(lsq(Ls, S["S"], ["l", "1", "1/L", "1/L2", "l/L", "l/L2"], Lmin)[0]["l"]) for Lmin in (100, 200, 400)]
    check("p2.S_limit", all(rounds_to(x, 0.367187, 6) for x in sv) and max(bl) < 1e-6,
          "S(inf) = " + ", ".join(f"{x:.8f}" for x in sv) + f"; max |free ln L coefficient| {max(bl):.1e}",
          "0.367187 (\\NTwoSinf), no ln L", "6 decimals; |b| < 1e-6")
    check("p2.delta_S", rounds_to(D3 * float(np.median(sv)), -0.005772, 6), f"delta_inf S_inf = {D3 * np.median(sv):+.7f}",
          "-0.005772 (\\NTwoDeltaS)", "6 decimals")
    check("p2.shift_lmax", int(S["L"].max()) == 1000 and int(np.load(RL / "results" / "eps5" / "dC5_L1000_all.npz")["L"].max()) == 1000,
          "S(L) and the C5 window shifts to L = 1000", "1000 (\\NTwoShiftLmax)", "exact")


def identity_checks():
    CE = PKG / "complete_exact" / "results"
    def r2(scheme, Lv, dn):
        j = json.load(open(CE / f"descendant_{scheme}_L{Lv}.json"))
        return float(Fr(j["descendants"][dn]["residual"][2]))
    rW = [r2("W", Lv, "odd1") * Lv for Lv in (12, 14, 16)]
    dec = all(abs(r2("W", 16, d)) < abs(r2("W", 12, d)) for d in ("odd1", "odd2", "odd3", "even1", "even2"))
    check("p2.ident2_W", round(rW[-1], 4) == 0.0114 and dec,
          f"W: L R_2(chi_11) = " + ", ".join(f"{x:.5f}" for x in rW) + f" (L = 12, 14, 16); all five spacings decrease: {dec}",
          "R_2 ~ 0.0114/L (\\NTwoRtwoWcoef): restored ([eps^2] v_n -> 0, note Sec. 4.6)", "4 decimals")
    rc = r2("consistent", 16, "odd1")
    check("p2.ident2_cons", round(rc, 4) == 0.0243, f"consistent: R_2(chi_11, L = 16) = {rc:.5f}", "0.0243 (\\NTwoRtwoCons)", "4 decimals")
    wcs = ce_load("out_wcs/*.json", "Wcs")
    wc = ce_load("out_local/*.json", "Wc")
    frac = {}
    for Lv in (14, 16):
        for a in (1, 2, 3):
            frac[(Lv, a)] = 1 - abs(Rdesc(wcs[Lv], f"odd{a}", 3)) / abs(Rdesc(wc[Lv], f"odd{a}", 3))
    mn = min(frac.values())
    check("p2.ident3_chi", mn >= 0.95, "removed fraction 1 - |R3^Wcs|/|R3^Wc|, chi_aa, a = 1..3, L = 14, 16: " +
          ", ".join(f"{v:.4f}" for v in frac.values()), "at least 95 % at L <= 16 (\\HTpTwoIdentThree)", ">= 0.95")
    ratio = [Rdesc(wc[16], f"odd{a}", 3) / (a * w_aa(a)) for a in (1, 2, 3)]
    check("p2.ident3_wc", round(sum(ratio) / 3, 3) == 0.063 and all(abs(x - 16 / (81 * math.pi)) < 1e-3 for x in ratio),
          "R3^Wc(chi_aa)/(a w_aa) at L = 16: " + ", ".join(f"{x:.5f}" for x in ratio) + f"; 16/(81 pi) = {16 / (81 * math.pi):.5f}",
          "0.063 (\\NTwoRthreeWcConst)", "mean to 3 decimals; each within 1e-3 of 16/(81 pi)")
    v1, v2 = Rdesc(wcs[16], "odd1", 3), Rdesc(wc[16], "odd1", 3)
    check("p2.ident3_L16", sig(v1, 2) == -1.6e-4 and round(v2, 4) == 0.0156,
          f"R3(chi_11, L = 16): Wcs {v1:+.3e}, Wc {v2:.5f}", "-1.6e-4 (\\NTwoRthreeWcsSixteen), 0.0156 (\\NTwoRthreeWcSixteen)",
          "2 significant digits; 4 decimals")
    e1, e2 = Rdesc(wcs[16], "even1", 3), Rdesc(wcs[16], "even2", 3)
    check("p2.ident3_phi2", round(e1, 3) == -0.057 and round(e2, 3) == -0.059,
          f"R3^Wcs, phi^2 descendants, L = 16: level 2 {e1:+.4f}, level 4 {e2:+.4f}", "-0.057, -0.059 (not settled)", "3 decimals")
    # eps^4: R_4(chi_11) grows like ln L in Wc and Wcs (identical through eps^4)
    Lr = np.array([Lv for Lv in sorted(wcs) if Lv >= 8], float)
    y4 = np.array([Rdesc(wcs[int(Lv)], "odd1", 4) for Lv in Lr])
    same4 = all(Rdesc(wcs[int(Lv)], "odd1", 4) == Rdesc(wc[int(Lv)], "odd1", 4) for Lv in Lr)
    slope = np.polyfit(np.log(Lr), y4, 1)[0]
    check("p2.eps4_R4slope", round(slope, 3) == 0.028 and same4, f"dR_4(chi_11)/d ln L = {slope:.4f} (L = 8..16); Wc = Wcs: {same4}",
          "0.028 (\\NTwoRfourSlope)", "3 decimals")
    # C6(16), every Wc-family scheme
    X = ce_load("out_wcs4x/*.json", "Wcs4X")
    Xa = ce_load("out_wcs4x/*.json", "Wcs4Xall")
    A = ce_load("out_wcs4c/*.json", "Wcs4")
    c6 = {nm: float(S[16]["C|6"]) for nm, S in (("Wc", wc), ("Wcs", wcs), ("Wcs4X", X), ("Wcs4Xall", Xa), ("A", A))}
    step = float(wcs[16]["C|6"] - wcs[14]["C|6"])
    check("p2.c6_L16", all(165.35 <= v <= 165.39 for v in c6.values()) and round(step, 1) == 7.5,
          "C6(16): " + ", ".join(f"{k} {v:.3f}" for k, v in c6.items()) + f"; C6(16) - C6(14) = {step:.2f} (Wcs)",
          "165.4 (165.35 to 165.39) (\\NTwoCsixSixteen), 7.5 (\\NTwoCsixStep); continuum 362.366", "range; 1 decimal")
    # C6 identity of App. C.5: variant A (out_wcs4c) and the proxy Wcs4 (out_wcs4) share D^(4) += (1/2)[d4 X_0 + delta3 X_1]
    # with different d4, so (C6^A - C6^proxy)/(d4_A - d4_proxy) must be the C5 response S(L) of legw_L1000.npz
    P = ce_load("out_wcs4/*.json", "Wcs4")
    d4 = {}
    for sub in ("out_wcs4c", "out_wcs4"):
        for f in glob.glob(str(PKG / "residual_log" / "ce_wc" / sub / "*.json")):
            g = json.load(open(f))["meta"]["args"]
            d4[(sub, g["L"])] = Fr(g["delta4"])
    sl = np.load(PKG / "residual_log" / "results" / "legw" / "legw_L1000.npz")
    Sl = {int(x): float(v) for x, v in zip(sl["L"], sl["S"])}
    worst, second = 0.0, []
    for Lv in sorted(P):
        Sx = (A[Lv]["C|6"] - P[Lv]["C|6"]) / (d4[("out_wcs4c", Lv)] - d4[("out_wcs4", Lv)])
        worst = max(worst, abs(float(Sx) - Sl[Lv]))
        second.append(float((A[Lv]["C|6"] - wcs[Lv]["C|6"]) - d4[("out_wcs4c", Lv)] * Sx))
    shA = {Lv: float(A[Lv]["C|6"] - wcs[Lv]["C|6"]) for Lv in (14, 16)}
    check("p2.c6_identity", sorted(P) == [6, 8, 10, 12, 14] and worst < 1e-12 and round(min(second), 4) == 0.0018
          and round(max(second), 4) == 0.0025 and round(shA[14], 4) == -0.0256 and round(shA[16], 4) == -0.0268,
          f"S(L) from variant A and proxy Wcs4, L = 6..14, vs legw S(L): max diff {worst:.1e}; delta3 S_1 = "
          + ", ".join(f"{x:+.5f}" for x in second) + f"; C6^A - C6^Wcs at L = 14, 16: {shA[14]:+.4f}, {shA[16]:+.4f}",
          "identity holds; delta3 S_1 = +0.0018 .. +0.0025; -0.0256, -0.0268", "1e-12; 4 decimals")


def eps4_window_checks():
    """Partial eps^4 chi-line window (Wcs4chi): rerun the shipped parent check verify_p5.py and read its output."""
    script = PKG / "residual_log" / "fits" / "parent_check_p5" / "verify_p5.py"
    out = subprocess.run([sys.executable, str(script), str(PKG / "residual_log")], capture_output=True, text=True)
    txt = out.stdout
    inv = re.findall(r"^Wcs4X\s+L=\s*\d+ C0-5,r,g<=4,E<=4 same: (\w+)\s+R2,R3 same: (\w+)", txt, re.M)
    okinv = out.returncode == 0 and len(inv) == 7 and all(a == "True" and b == "True" for a, b in inv)
    m11 = re.findall(r"^odd1 L=\s*\d+ .*\(==bf exactly\)", txt, re.M)
    g22 = re.search(r"^odd2 L=14 .*closed ([0-9.]+)", txt, re.M)
    g33 = re.search(r"^odd3 L=14 .*closed ([0-9.]+)", txt, re.M)
    ok = okinv and len(m11) == 7 and g22 and g33 and round(float(g22.group(1)) * 100) == 95 and round(float(g33.group(1)) * 100) == 90
    check("p2.eps4_chiwindow", bool(ok),
          f"invariances (C0..C5, r, g <= 4, E <= 4, R2, R3) exact at {len(inv)} L; R4(chi_11) = budget-free at {len(m11)} L; "
          f"gap closed at L = 14: chi_22 {g22.group(1) if g22 else '?'}, chi_33 {g33.group(1) if g33 else '?'}",
          "95 % (\\NTwoGapTwo), 90 % (\\NTwoGapThree); invariances exact", "nearest per cent")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--prod", default=str(PKG.parent.parent / "data" / "HT_2d" / "prod"), help="production records")
    ap.add_argument("--skip-snapshot", action="store_true", help="do not verify public/SNAPSHOT.sha256")
    a = ap.parse_args()
    prod = Path(a.prod)
    REF = refs()
    if not a.skip_snapshot:
        snapshot_integrity()
    impl_agreement(prod)
    cauchy_agreement(prod)
    dev3 = low_orders(prod, REF)
    dev4 = c4_checks(prod, REF)
    check("p2.low_dev", max(dev3, dev4) < 1e-7, f"C2: 35 digits; C3 {dev3:.1e}; C4 {dev4:.1e}", "all below 1e-7 (\\HTpTwoLowDev)", "bound")
    check("p2.lprod", all(prod_record(prod, s, 34)[0] is not None for s in ("raw", "consistent"))
          and not any(list((prod / sub / "d8").glob("*_L36.json")) for sub in ("prod1_symmetry", "prod2_expanse")),
          "production records to L = 34 (raw, consistent)", "34 (\\HTpTwoLprod)", "exact")
    c5_checks(prod, REF)
    delta_checks()
    identity_checks()
    eps4_window_checks()
    w = max(len(r[0]) for r in ROWS)
    for name, st, val, exp, tol in ROWS:
        print(f"{st}  {name:<{w}}  {val}\n      {'':<{w}}  expected: {exp}  [{tol}]")
    for nline in NOTES[:20]:
        print("NOTE", nline)
    nf = sum(r[1] == "FAIL" for r in ROWS)
    print(f"\n{len(ROWS) - nf}/{len(ROWS)} PASS" + (f", {nf} FAIL" if nf else ""))
    sys.exit(1 if nf else 0)


if __name__ == "__main__":
    main()
