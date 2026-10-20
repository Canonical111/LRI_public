#!/usr/bin/env python3
r"""Replay of the d = 1 complete-window refits of C4..C8 (HT_Pert/code/lri_1d_dconn_refit).

Recomputes every quoted number of the package from the shipped refit outputs (no fit is rerun here; see test_refit.py for
the delta rebuild and the key-fit refit) and prints id | verdict | what | quoted | computed (exit status 1 on any FAIL;
also written to <work>/replay_lri_1d_dconn_refit.txt). Rows (ids as in results_map.md, quoted_lri_1d_dconn_refit.json):

  rf.inputs   record binding: the sha256 that the delta-stage outputs record for their inputs (data.json, dC_reconciled,
              the S10 archive table, d5_all, d7_all, the L = 46..72 dC table; derived_from of the four derived tables;
              the six tables bound by delta_v1_hi72_smooth.json; the frozen forecast's .sha256) equal the shipped files
  rf.blind    blind check of the delta-v1 continuation: the forecast frozen from L <= 44 (2026-10-08 08:35, before the
              production records existed) against the exact dC6..dC8 at L = 46..72: max |forecast - exact| / unc_typ,
              2 significant figures
  The C4 and C5 rows are solver-fit results quoted in the HT_Pert note only, as the note macros \NOneCfourSolver,
  \NOneCfourSolverDev, \NOneCfiveSolver, \NOneCfiveSolverDev (the paper's \HTpCfourOne and \HTpCfiveOne come from the
  exact sums, code/lri_1d_c4_exact row x4.c4 and code/lri_1d_c5_exact row x5.c5). Data sets: "fixed A-F" = the
  unweighted dataset dconn (r72_summary.json C_low.dconn_hi118.fixed_AF); "floor+stat" = the weighted dataset dconn_w
  (summary_dconn_w.json dconn_w_hi118_C<k>_floor_stat); "MI" = the model-independent lens (headline.json, final72.json).
  rf.C4       \NOneCfourSolver. Union of (a) pre-registered bases A-F with the complete window (refit_rc.json, column
              Dconn_full, cls 'pre', lo = 40..70, hi = 118; from code/lri_hpc_Hamitonian), (b) the joint lens's
              floor+stat ensemble median (dconn_w), (c) the model-independent lens's central value (headline.json C4
              cal_heldout_mean): "union of central values"; both ends rounded to 3 decimals (nearest; outward rounding
              gives the same)
  rf.C4dev    \NOneCfourSolverDev = max |end - C4| / C4 over the two unrounded ends, C4 = \CfourOne; 1 significant
              figure
  rf.C5       \NOneCfiveSolver. Union of (a) the freed-leading-tail family (i) (L^-1/2, L^-1/2 log L freed at orders 4
              and 5; freelead2.json, lo = 50..70, bases A-F; from code/lri_hpc_Hamitonian) and (b) the joint floor+stat
              ensemble 16-84 range (dconn_w); both ends rounded to 2 decimals (NEAREST; outward would give -731.36 to
              -730.96)
  rf.C5dev    \NOneCfiveSolverDev, as rf.C4dev with C5 = \CfiveOne
  rf.C6       \HTpCsixOne. Union of (a) fixed bases A-F, unweighted dconn (miss6 16-84 plus the reference 14331.68703277
              the lens subtracted), (b) the joint floor+stat 16-84 range (dconn_w), (c) the model-independent variant
              range (headline.json C6: uncal, uncal hi = 118, the calibration rules, l^2 T2 family; final72.json
              delta-free hi = 72 uncal and cal; the biased accelerators excluded as in the lens); both ends rounded to
              integers (nearest; outward identical)
  rf.C6dev    \HTpCsixOneDev, as rf.C4dev with C6 = \CsixOne
  rf.C7       \HTpCsevenOne. Union of (a) fixed A-F, unweighted dconn (miss7 16-84 plus -322550), (b) the joint floor+stat
              16-84 range (dconn_w), (c) the model-independent variant range (as for C6, accelerators included) widened
              by the stated delta-model error +-6; ends rounded OUTWARD to tens (as the macro comment states)
  rf.C7dev    \HTpCsevenOneDev = max |end - (-322550)| / 322550 over the unrounded ends; 1 significant figure
  rf.C7w      INFO (sensitivity, not quoted): the weighted fixed A-F (C_low.dconn_w_hi118.fixed_AF) in place of the
              unweighted one; its C6 and C7 16-84 ranges and the unions they would give (C7: -322 900 to -322 230)
  rf.C8       \HTpCeightOne: calibrated joint-lens estimator 'prior_crit_full_grid:sel67' (selection on |C6 rel| <= 1e-4
              and |C7 + 322550| <= 82, hi = 92, weighted fits; summary_dconn_w.json C8_calibrated), 5 significant
              figures
  rf.C8dev    \HTpCeightOneDev = |rf.C8 / 8059766.723129955 - 1| (the estimator behind \CeightOne); 1 significant figure
  rf.C8cal    \HTpCeightOneCalRange: INFO. A judgement of the S1B joint stage ('realistic calibrated range': spread over
              estimator, family, anchoring and hi choices), not a stored number; the stored span of the 16 calibrated
              estimators is printed
  rf.C8uncal  \HTpCeightOneUncal: union of the 16-84 ranges of the five prior-criterion families (2026-10-04 grid,
              full grid, all fixed, free omega, freed tail) for the r72 weighted data (the joint lens's primary
              dataset), rounded to 3 decimals (nearest), must equal the macro (author decision 2026-10-14: the macro
              was the run-1 value 8.047-8.072 and now follows the cited refit). Also printed: the r72 unweighted and
              s46 unions and run 1 (joint/archived_run1/summary.json, delta model hi = 44)
  rf.paired   window effects at orders 6-8: medians of the paired shifts (same fit configuration, new exact dC6..dC8 at
              L = 46..72 minus the run-1 continuation; r72_summary.json D_paired, unweighted): C6, C7 from o7 hi = 118,
              modes fixed and FL; C8 from o8 hi = 92 (windows 'th118' and 'same'), modes fixed and FL; rounded as quoted
  rf.noise    S10 noise at L = 46..72 (a caveat): rms of (exact - floor-mean curve) for dC6, dC7, dC8 from the shipped
              joint/code/data.py load() (noise_model.sigx), 3 significant figures; the weights wrel are printed
Cross-folder inputs (SKIP when absent): ../lri_hpc_Hamitonian/analysis/eps5_window/{reconcile/refit_rc.json,
challenge-theory/freelead2.json, reconcile/dC_reconciled.json}, ../lri_hpc_Hamitonian/analysis/eh_review/physics-impact/
{d5_all,d7_all}.json, ../../data/HT_1d/c8/extrapolation/data.json, ../../data/HT_1d/s10_production/,
../lri_d1_full_coefficient_flow/results/whole_model_coefficients.csv.
usage: python3 public/replay_refit.py [--htp ../..] [--data ../../data/HT_1d] [--work .work]"""
import argparse
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from repoint import inputs  # noqa: E402

NAME = "lri_1d_dconn_refit"
REF = {4: 45.42488010356, 5: -731.13947662454, 6: 14331.68703275805, 7: -322550.0, 8: 8059766.723129955}
FITREF = {6: 14331.68703277, 7: -322550.0}      # joint/code/fitcore.py REF, subtracted in the stored misses
QUOTED = {
    "rf.inputs": "recorded sha256 = shipped files",
    "rf.blind": "0.099",
    "rf.C4": r"45.415\text{--}45.420",
    "rf.C4dev": r"2\times10^{-4}",
    "rf.C5": r"-731.36\text{ to }{-730.97}",
    "rf.C5dev": r"3\times10^{-4}",
    "rf.C6": r"14\,320\text{--}14\,342",
    "rf.C6dev": r"8\times10^{-4}",
    "rf.C7": r"-322\,890\text{ to }{-322\,230}",
    "rf.C7w": "not quoted (sensitivity: weighted fixed A-F)",
    "rf.C7dev": r"1\times10^{-3}",
    "rf.C8": r"8.0652\times10^{6}",
    "rf.C8dev": r"7\times10^{-4}",
    "rf.C8cal": r"8.061\text{--}8.067",
    "rf.C8uncal": r"8.045\text{--}8.073",
    "rf.paired": "C6 -0.01..-0.04; C7 +4..+19; C8 +17..+32 (fixed), -240..-490 (FL)",
    "rf.noise": "3.95e-10, 1.34e-8, 2.32e-7",
}
ROWS = []
FAMS5 = ("prior_crit_prior_grid", "prior_crit_full_grid", "prior_crit_fixed", "prior_crit_free", "prior_crit_FL")


def row(rid, verdict, what, computed):
    ROWS.append((rid, verdict, what, QUOTED[rid], computed))


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def J(*p):
    return json.load(open(os.path.join(PKG, *p)))


def sig1(x):
    e = math.floor(math.log10(abs(x)))
    m = round(x / 10 ** e)
    if m == 10:
        m, e = 1, e + 1
    return rf"{m}\times10^{{{e}}}"


def pint(n):
    """integer with spaces as thousands separators (plain-text output)."""
    return f"{int(n):,}".replace(",", " ")


def tint(n):
    """integer with thin-space thousands separators as numbers.tex writes it (14\\,320, -322\\,890)."""
    s = f"{abs(int(n)):,}".replace(",", r"\,")
    return ("-" if n < 0 else "") + s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--htp", default=os.path.join(PKG, "..", ".."))
    ap.add_argument("--data", default=None, help="HT_1d data root (default <htp>/data/HT_1d)")
    ap.add_argument("--work", default=os.path.join(PKG, ".work"))
    a = ap.parse_args()
    a.htp = os.path.abspath(a.htp)       # the stage scripts run in other directories
    I = inputs(a.htp, a.data)
    S = J("joint", "out", "r72", "summary_dconn_w.json")
    R = J("joint", "out", "r72", "r72_summary.json")
    H = J("model-independent", "out", "headline.json")
    F = J("model-independent", "out", "final72.json")

    # rf.inputs
    D = os.path.join(PKG, "delta", "out")
    A1 = os.path.join(PKG, "delta", "archived_out_delta_v1")
    ext = {"data.json": I["DATA_JSON"], "dC_reconciled.json": I["RECON_JSON"],
           "whole_model_coefficients.csv": I["S10_CSV"], "d5_all.json": I["D5_JSON"], "d7_all.json": I["D7_JSON"],
           "dconn_minus_raw_L46_72.csv": I["CSV"]}
    got_sha = {k: (sha(p) if os.path.exists(p) else None) for k, p in ext.items()}
    nb, bad, skipped = 0, [], set()

    def bind(label, name, recorded, actual):
        nonlocal nb
        if actual is None:
            skipped.add(name)
        elif recorded != actual:
            bad.append(f"{label}:{name}")
        else:
            nb += 1
    base = "delta_v1_hi72_corrected.json"
    for f in [base] + [f"delta_v1_hi72_{x}_corrected.json" for x in ("medoid", "floormean", "floormedoid",
                                                                       "floormean_s46")]:
        d = json.load(open(os.path.join(D, f)))
        for p, h in d["sources"].items():
            bind(f, os.path.basename(p), h, got_sha.get(os.path.basename(p)))
        bind(f, "dconn_minus_raw_L46_72.csv", d["extra_dconn_csv"]["sha256"], got_sha["dconn_minus_raw_L46_72.csv"])
        if "derived_from" in d:
            bind(f, base, d["derived_from"]["sha256"], sha(os.path.join(D, base)))
    d = json.load(open(os.path.join(A1, "delta_v1_corrected.json")))
    for p, h in d["sources"].items():
        bind("delta_v1_corrected.json", os.path.basename(p), h, got_sha.get(os.path.basename(p)))
    sm = json.load(open(os.path.join(D, "delta_v1_hi72_smooth.json")))
    local = {"delta_v1_hi72_corrected.json": os.path.join(D, base),
             "delta_v1_hi72_variants.json": os.path.join(D, "delta_v1_hi72_variants.json"),
             "variants_full_hi72.json": os.path.join(D, "variants_full_hi72.json"),
             "delta_v1_corrected.json": os.path.join(A1, "delta_v1_corrected.json"),
             "delta_v1_variants.json": os.path.join(A1, "delta_v1_variants.json"),
             "variants_full.json": os.path.join(PKG, "run1", "joint", "out", "variants_full.json")}
    for p, h in sm["sha256"].items():
        bind("smooth.json", os.path.basename(p), h, sha(local[os.path.basename(p)]))
    ff = os.path.join(A1, "frozen_forecast_L46_72.json")
    bind("frozen_forecast", "frozen_forecast_L46_72.json", open(ff + ".sha256").read().split()[0], sha(ff))
    v = "FAIL" if bad else ("SKIP" if skipped else "PASS")
    row("rf.inputs", v, "input sha256 recorded by the delta-stage outputs equal the shipped files",
        f"{nb} bindings match; mismatched {bad}; inputs absent {sorted(skipped)}")

    # rf.blind
    if not os.path.exists(I["CSV"]):
        row("rf.blind", "SKIP", "frozen hi = 44 forecast vs exact dC6..dC8 at L = 46..72", f"{I['CSV']} absent")
    else:
        fz = json.load(open(ff))
        ex = {int(ln.split(",")[0]): [float(x) for x in ln.split(",")[1:]] for ln in open(I["CSV"]).read().split()[1:]}
        rt = re_ = 0.0
        for k in (6, 7, 8):
            for L, (c, u, ut) in fz["forecast"][f"dC{k}"].items():
                e = ex[int(L)][k - 6]
                rt, re_ = max(rt, abs(c - e) / ut), max(re_, abs(c - e) / u)
        got = f"{rt:.2g}"
        row("rf.blind", "PASS" if got == QUOTED["rf.blind"] and fz["created"] < "2026-10-08T08:59" else "FAIL",
            "frozen hi = 44 delta-v1 forecast vs exact dC6..dC8, L = 46..72: max |err| / unc_typ",
            f"{got} ({rt:.4f}; max |err| / envelope {re_:.3f}; 42 points; forecast created {fz['created']}, "
            f"made from: {fz['made_from']})")

    # rf.C4, rf.C4dev
    if not os.path.exists(I["REFIT_RC"]):
        row("rf.C4", "SKIP", r"\NOneCfourSolver union", f"{I['REFIT_RC']} absent")
        row("rf.C4dev", "SKIP", r"\NOneCfourSolverDev", "needs rf.C4")
    else:
        rc = json.load(open(I["REFIT_RC"]))["rows"]
        af = [r["Dconn_full"]["C4"] for r in rc if r["cls"] == "pre" and r["variant"] in "ABCDEF" and 40 <= r["lo"] <= 70]
        fs = S["dconn_w_hi118_C4_floor_stat"]["C"]["median"]
        mi = H["C4"]["cal_heldout_mean"]
        lo, hi = min(min(af), fs, mi), max(max(af), fs, mi)
        got = rf"{lo:.3f}\text{{--}}{hi:.3f}"
        outw = rf"{math.floor(lo * 1e3) / 1e3:.3f}\text{{--}}{math.ceil(hi * 1e3) / 1e3:.3f}"
        row("rf.C4", "PASS" if got == QUOTED["rf.C4"] == outw else "FAIL",
            r"\NOneCfourSolver (HT_Pert note): C4 with the complete window, union of central values",
            f"{got} (pre-registered A-F, Dconn_full {min(af):.5f}..{max(af):.5f}, {len(af)} fits; floor+stat (dconn_w) "
            f"median {fs:.6f} (n={S['dconn_w_hi118_C4_floor_stat']['C']['n']}); MI {mi:.5f}; union "
            f"{lo:.5f}..{hi:.5f}; nearest 3 decimals, outward {outw})")
        dev = max(abs(lo - REF[4]), abs(hi - REF[4])) / REF[4]
        row("rf.C4dev", "PASS" if sig1(dev) == QUOTED["rf.C4dev"] else "FAIL", r"\NOneCfourSolverDev vs \CfourOne",
            f"{sig1(dev)} ({dev:.3e}; misses {lo - REF[4]:+.5f}, {hi - REF[4]:+.5f})")

    # rf.C5, rf.C5dev
    if not os.path.exists(I["FREELEAD2"]):
        row("rf.C5", "SKIP", r"\NOneCfiveSolver union", f"{I['FREELEAD2']} absent")
        row("rf.C5dev", "SKIP", r"\NOneCfiveSolverDev", "needs rf.C5")
    else:
        fl = [r["C5"] for r in json.load(open(I["FREELEAD2"])) if r["fam"].startswith("(i)")]
        c = S["dconn_w_hi118_C5_floor_stat"]["C"]
        lo, hi = min(min(fl), c["p16"]), max(max(fl), c["p84"])
        got = rf"{lo:.2f}\text{{ to }}{{{hi:.2f}}}"
        outw = f"{math.floor(lo * 100) / 100:.2f}..{math.ceil(hi * 100) / 100:.2f}"
        row("rf.C5", "PASS" if got == QUOTED["rf.C5"] else "FAIL",
            r"\NOneCfiveSolver (HT_Pert note): C5, freed tails and floor ensemble",
            f"{got} (freed tail (i) {min(fl):.4f}..{max(fl):.4f}, {len(fl)} fits, misses {min(fl) - REF[5]:+.3f}.."
            f"{max(fl) - REF[5]:+.3f}; floor+stat (dconn_w) 16-84 {c['p16']:.4f}..{c['p84']:.4f} (n={c['n']}); union "
            f"{lo:.4f}..{hi:.4f}; nearest 2 decimals; outward would give {outw})")
        dev = max(abs(lo - REF[5]), abs(hi - REF[5])) / abs(REF[5])
        row("rf.C5dev", "PASS" if sig1(dev) == QUOTED["rf.C5dev"] else "FAIL", r"\NOneCfiveSolverDev vs \CfiveOne",
            f"{sig1(dev)} ({dev:.3e})")

    # rf.C6 .. rf.C7dev
    fa = R["C_low"]["dconn_hi118"]["fixed_AF"]           # fixed A-F: the UNWEIGHTED dataset dconn
    faw = R["C_low"]["dconn_w_hi118"]["fixed_AF"]        # weighted alternative, printed only (rf.C7w)
    alt = []
    for k in (6, 7):
        m = fa[f"miss{k}"]
        afr = (FITREF[k] + m["p16"], FITREF[k] + m["p84"])
        mw = faw[f"miss{k}"]
        afw = (FITREF[k] + mw["p16"], FITREF[k] + mw["p84"])
        c = S[f"dconn_w_hi118_C{k}_floor_stat"]["C"]
        h = H[f"C{k}"]
        mv = [h["uncal"], h["uncal_hi118"], h["cal_heldout_mean"], *h["cal_rules"].values(), h["full3"],
              F["delta_free_hi72"]["primary"][str(k)]["uncal"], F["delta_free_hi72"]["primary"][str(k)]["cal"]]
        if k == 7:
            mv += [h["neville_top92"], h["bst_top92"]]
            mir = (min(mv) - 6, max(mv) + 6)
        else:
            mir = (min(mv), max(mv))
        lo, hi = min(afr[0], c["p16"], mir[0]), max(afr[1], c["p84"], mir[1])
        low, hiw = min(afw[0], c["p16"], mir[0]), max(afw[1], c["p84"], mir[1])
        if k == 6:
            got = rf"{tint(round(lo))}\text{{--}}{tint(round(hi))}"
            note = "nearest integers (outward identical)"
            ok = got == QUOTED["rf.C6"] == rf"{tint(math.floor(lo))}\text{{--}}{tint(math.ceil(hi))}"
            alt.append(f"C6: weighted fixed A-F 16-84 {afw[0]:.2f}..{afw[1]:.2f}, union {low:.2f}..{hiw:.2f} -> "
                       f"{pint(round(low))}-{pint(round(hiw))} (nearest; quoted unchanged)")
        else:
            got = rf"{tint(math.floor(lo / 10) * 10)}\text{{ to }}{{{tint(math.ceil(hi / 10) * 10)}}}"
            note = "outward to tens"
            ok = got == QUOTED["rf.C7"]
            alt.append(f"C7: weighted fixed A-F 16-84 {afw[0]:.2f}..{afw[1]:.2f}, union {low:.2f}..{hiw:.2f} -> "
                       f"{pint(math.floor(low / 10) * 10)} to {pint(math.ceil(hiw / 10) * 10)} (outward to tens; the "
                       f"quoted range uses the unweighted fixed A-F)")
        row(f"rf.C{k}", "PASS" if ok else "FAIL", rf"\HTp{'Csix' if k == 6 else 'Cseven'}One: union of three lenses",
            f"{got} (fixed A-F, unweighted dconn (C_low.dconn_hi118), 16-84 {afr[0]:.2f}..{afr[1]:.2f} [miss median "
            f"{m['median']:+.2f}]; floor+stat (dconn_w) {c['p16']:.2f}..{c['p84']:.2f} (n={c['n']}, median "
            f"{c['median']:.2f}); MI{' (widened by +-6)' if k == 7 else ''} {mir[0]:.2f}..{mir[1]:.2f} (central "
            f"{h['cal_heldout_mean']:.2f}); union {lo:.2f}..{hi:.2f}; {note})")
        dev = max(abs(lo - REF[k]), abs(hi - REF[k])) / abs(REF[k])
        rid = f"rf.C{k}dev"
        row(rid, "PASS" if sig1(dev) == QUOTED[rid] else "FAIL",
            rf"\HTp{'Csix' if k == 6 else 'Cseven'}OneDev vs \C{'six' if k == 6 else 'seven'}One",
            f"{sig1(dev)} ({dev:.3e})")
        if k == 7:
            row("rf.C7w", "INFO", "sensitivity, not quoted: the weighted fixed A-F (C_low.dconn_w_hi118) in the C6, C7 "
                "unions", "; ".join(alt))

    # rf.C8, rf.C8dev, rf.C8cal, rf.C8uncal
    E = S["C8_calibrated"]["estimators"]
    v8 = E["prior_crit_full_grid:sel67"]["value"]
    got = rf"{v8 / 1e6:.4f}\times10^{{6}}"
    row("rf.C8", "PASS" if got == QUOTED["rf.C8"] else "FAIL", r"\HTpCeightOne: calibrated C8 (selection on C6, C7)",
        f"{got} ({v8:,.0f}; n = {E['prior_crit_full_grid:sel67']['n']} weighted fits)")
    dev = abs(v8 / REF[8] - 1)
    row("rf.C8dev", "PASS" if sig1(dev) == QUOTED["rf.C8dev"] else "FAIL", r"\HTpCeightOneDev vs 8059766.72",
        f"{sig1(dev)} ({dev:.3e})")
    vals = [x["value"] for x in E.values()]
    # the components the stage names for its 'realistic calibrated range' (estimator, family, anchoring, hi choices),
    # all stored for the weighted fits: r72_summary.json E_F_C8 and summary_dconn_w.json C8_hi_convergence
    EF = R["E_F_C8"]
    comp = {"16 estimators hi=92": (min(vals), max(vals)),
            "family selections FL/free": (EF["dconn_w_92"]["prior_crit_FL"]["cal"]["sel67"]["C8"],
                                          EF["dconn_w_92"]["prior_crit_free"]["cal"]["sel67"]["C8"]),
            "anchored on C4..C7": (EF["dconn_w_92"]["sel4567"]["prior_crit_full_grid"]["C8"]["median"],
                                   EF["dconn_w_92"]["sel4567"]["near3_8"]["C8"]["median"]),
            "hi=70/80 selections": tuple(S["C8_hi_convergence"][f"prior_crit_{g}_{h}"]["sel67"]
                                         for g in ("prior_grid", "full_grid", "fixed") for h in (70, 80)),
            "delta-free hi=72 estimators": (EF["dconn_w_72same"]["est_summary"]["min"],
                                            EF["dconn_w_72same"]["est_summary"]["max"])}
    allv = [x for v in comp.values() for x in v]
    rec = (math.floor(min(allv) / 1e3) / 1e3, math.ceil(max(allv) / 1e3) / 1e3)
    row("rf.C8cal", "INFO", r"\HTpCeightOneCalRange (x1e6): judgement of the joint stage",
        f"stored span of the {len(vals)} calibrated estimators {min(vals) / 1e6:.4f}..{max(vals) / 1e6:.4f} "
        f"(median {S['C8_calibrated']['median_of_estimators'] / 1e6:.4f}). Reconstruction (not the stage's own "
        f"computation): union of the stored components it names, "
        + "; ".join(f"{k} {min(v) / 1e6:.4f}..{max(v) / 1e6:.4f}" for k, v in comp.items())
        + f" = {min(allv) / 1e6:.4f}..{max(allv) / 1e6:.4f}, outward to 3 decimals {rec[0]:.3f}--{rec[1]:.3f}")
    U = S["C8_uncalibrated"]
    u72 = (min(U[f]["C8"]["p16"] for f in FAMS5), max(U[f]["C8"]["p84"] for f in FAMS5))
    run1 = os.path.join(PKG, "joint", "archived_run1", "summary.json")
    if os.path.exists(run1):
        U1 = json.load(open(run1))["C8_uncalibrated"]
        u1 = (min(U1[f]["C8"]["p16"] for f in FAMS5), max(U1[f]["C8"]["p84"] for f in FAMS5))
        s1 = (f"; run 1: {u1[0] / 1e6:.6f}..{u1[1] / 1e6:.6f} -> {u1[0] / 1e6:.3f}--{u1[1] / 1e6:.3f} (outward would "
              f"give {math.floor(u1[0] / 1e3) / 1e3:.3f}--{math.ceil(u1[1] / 1e3) / 1e3:.3f})")
    else:
        s1 = "; run-1 summary absent"
    other = []
    for lab, fn in (("r72 unweighted", "summary.json"), ("r72 s46", "summary_dconn_s46.json")):
        Ux = J("joint", "out", "r72", fn)["C8_uncalibrated"]
        ux = (min(Ux[f]["C8"]["p16"] for f in FAMS5), max(Ux[f]["C8"]["p84"] for f in FAMS5))
        other.append(f"{lab} {ux[0] / 1e6:.3f}--{ux[1] / 1e6:.3f}")
    got_u = rf"{u72[0] / 1e6:.3f}\text{{--}}{u72[1] / 1e6:.3f}"
    row("rf.C8uncal", "PASS" if got_u == QUOTED["rf.C8uncal"] else "FAIL",
        r"\HTpCeightOneUncal (x1e6): 16-84 across the uncalibrated tail families",
        f"union of the 16-84 ranges of the five prior-criterion families, rounded to 3 decimals (nearest): r72 weighted "
        f"(dconn_w, the joint lens's primary) "
        f"{u72[0] / 1e6:.4f}..{u72[1] / 1e6:.4f} -> {u72[0] / 1e6:.3f}--{u72[1] / 1e6:.3f}; {'; '.join(other)}{s1}; "
        f"quoted {QUOTED['rf.C8uncal']} = the r72 weighted union (until 2026-10-14 the macro held the run-1 value 8.047--8.072)")

    # rf.paired
    P = R["D_paired"]
    g = lambda key, k: P[f"dconn-dconn_old_{key}"][f"dC{k}"]["median"]  # noqa: E731
    c6 = (g("o7_118_same_fixed", 6), g("o7_118_same_FL", 6))
    c7 = (g("o7_118_same_fixed", 7), g("o7_118_same_FL", 7))
    c8f = (g("o8_92_th118_fixed", 8), g("o8_92_same_fixed", 8))
    c8l = (g("o8_92_same_FL", 8), g("o8_92_th118_FL", 8))
    r10 = lambda x: int(round(x / 10) * 10)  # noqa: E731
    got = (f"C6 {c6[0]:.2f}..{c6[1]:.2f}; C7 {c7[0]:+.0f}..{c7[1]:+.0f}; C8 {c8f[0]:+.0f}..{c8f[1]:+.0f} (fixed), "
           f"{r10(c8l[0]):+d}..{r10(c8l[1]):+d} (FL)")
    row("rf.paired", "PASS" if got == QUOTED["rf.paired"] else "FAIL",
        "paired shifts, exact dC6..dC8 at 46..72 minus the run-1 continuation (medians over identical fits)",
        f"{got} (raw: {c6[0]:.4f}, {c6[1]:.4f}; {c7[0]:.2f}, {c7[1]:.2f}; {c8f[0]:.1f}, {c8f[1]:.1f}; {c8l[0]:.1f}, "
        f"{c8l[1]:.1f})")

    # rf.noise
    os.environ["DCONN_CORRECTED"] = os.path.join(D, base)
    os.environ["DCONN_VARIANTS_FULL"] = os.path.join(D, "variants_full_hi72.json")
    sys.dont_write_bytecode = True
    sys.path.insert(0, os.path.join(PKG, "joint", "code"))
    from data import load  # noqa: E402  (the shipped joint-lens loader; numpy only)
    nm = load(with_perts=False)["noise_model"]
    sx = [nm["sigx"][k] for k in (6, 7, 8)]
    got = ", ".join(f"{x:.2e}".replace("e-0", "e-") for x in sx)
    wr = ", ".join("%.1f" % nm["wrel"][n] for n in (6, 7, 8))
    row("rf.noise", "PASS" if got == QUOTED["rf.noise"] else "FAIL",
        "S10 noise of dC6, dC7, dC8 at L = 46..72 (rms about the floor-mean curve)",
        f"{got} (fit-target weights wrel Y6..Y8 = {wr} x the quiet floor; cluster rows "
        f"{nm['cluster_L'][0]}..{nm['cluster_L'][-1]})")

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
