#!/usr/bin/env python3
"""Run-time copy of the delta-stage code with its input paths pointed into the public tree.

The delta-stage scripts (delta/code, delta/lens_compat) ship verbatim; they name their inputs by absolute paths of the
authors' machine (or, after the public scrub, by placeholders). This tool copies them to <work>/rt/ (same relative
layout, so their own '../out' and '../lens_compat' references work) and rewrites only the path constants listed in
SUBS, matched by variable name (exactly one assignment each, else it stops). The shipped files are never modified.
<work>/rt/arch/ stands in for the run-1 folder that smooth_central.py and validate_hi72.py read (ARCH): it holds copies of
delta/archived_out_delta_v1/delta_v1_{corrected,variants}.json (byte-identical to the run-1 delta outputs) at
delta/out/ and of run1/joint/out/variants_full.json at joint/out/.
usage (library): from repoint import make_runtime; rt = make_runtime(work, htp_root[, data_root])"""
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)


def inputs(htp, data=None):
    """Absolute paths of the cross-package inputs in the public HT_Pert tree rooted at htp (data: the HT_1d data root,
    default <htp>/data/HT_1d)."""
    htp = os.path.abspath(htp)
    data = os.path.abspath(data) if data else os.path.join(htp, "data", "HT_1d")
    ham =os.path.join(htp, "code", "lri_hpc_Hamitonian", "analysis")
    return dict(
        DATA_JSON=os.path.join(data, "c8", "extrapolation", "data.json"),
        RECON_CSV=os.path.join(ham, "eps5_window", "reconcile", "dC_reconciled.csv"),
        RECON_JSON=os.path.join(ham, "eps5_window", "reconcile", "dC_reconciled.json"),
        S10_CSV=os.path.join(htp, "code", "lri_d1_full_coefficient_flow", "results", "whole_model_coefficients.csv"),
        D5_JSON=os.path.join(ham, "eh_review", "physics-impact", "d5_all.json"),
        D7_JSON=os.path.join(ham, "eh_review", "physics-impact", "d7_all.json"),
        PROD=os.path.join(data, "s10_production"),
        CSV=os.path.join(data, "s10_production", "dconn_minus_raw_L46_72.csv"),
        REFIT_RC=os.path.join(ham, "eps5_window", "reconcile", "refit_rc.json"),
        FREELEAD2=os.path.join(ham, "eps5_window", "challenge-theory", "freelead2.json"),
    )


def subst(src, name, value):
    new, n = re.subn(r"^(%s\s*=\s*)(['\"]).*?\2[ \t]*$" % re.escape(name), lambda m: m.group(1) + repr(value), src,
                     flags=re.M)
    if n != 1:
        raise SystemExit(f"repoint: expected one assignment of {name}, found {n}")
    return new


def make_runtime(work, htp, data=None):
    work = os.path.abspath(work)
    htp = os.path.abspath(htp)
    I = inputs(htp, data)
    rt = os.path.join(work, "rt")
    if os.path.exists(rt):
        shutil.rmtree(rt)
    for sub in ("delta/code", "delta/lens_compat"):
        shutil.copytree(os.path.join(PKG, sub), os.path.join(rt, sub),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    os.makedirs(os.path.join(rt, "delta", "out"))
    arch = os.path.join(rt, "arch")
    os.makedirs(os.path.join(arch, "delta", "out"))
    os.makedirs(os.path.join(arch, "joint", "out"))
    for f in ("delta_v1_corrected.json", "delta_v1_variants.json"):
        shutil.copy2(os.path.join(PKG, "delta", "archived_out_delta_v1", f), os.path.join(arch, "delta", "out", f))
    shutil.copy2(os.path.join(PKG, "run1", "joint", "out", "variants_full.json"),
                 os.path.join(arch, "joint", "out", "variants_full.json"))
    SUBS = {
        "delta/code/load.py": {k: I[k] for k in ("DATA_JSON", "RECON_CSV", "RECON_JSON", "S10_CSV", "D5_JSON", "D7_JSON")},
        "delta/code/check_inputs.py": {"P": I["PROD"]},
        "delta/code/check_outputs.py": {"P": I["PROD"]},
        "delta/code/smooth_central.py": {"ARCH": arch},
        "delta/code/validate_hi72.py": {"CSV": I["CSV"], "ARCH": arch},
        "delta/lens_compat/regen_variants.py": {"DELTA_CODE": os.path.join(rt, "delta", "code")},
    }
    for rel, subs in SUBS.items():
        p = os.path.join(rt, rel)
        s = open(p).read()
        for k, v in subs.items():
            s = subst(s, k, v)
        open(p, "w").write(s)
    return rt


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=os.path.join(PKG, ".work"))
    ap.add_argument("--htp", default=os.path.join(PKG, "..", ".."))
    ap.add_argument("--data", default=None)
    a = ap.parse_args()
    print(make_runtime(a.work, a.htp, a.data))
