#!/usr/bin/env python3
"""Fast tests of the d = 1 complete-window refits (HT_Pert/code/lri_1d_dconn_refit): the delta stage rebuilt from its
inputs and compared with the shipped outputs, and (optionally) a light refit of the joint lens's key fits.

Steps (all on a run-time copy made by public/repoint.py in <work>/rt; nothing shipped is modified):
  inputs      delta/code/check_inputs.py: the per-L production records minus raw equal the dC table, C0..C3 unchanged,
              dC4/dC5 against dC_reconciled.json (<= 2e-11), thermal_d7 vs lri_c8 raw (bounds below)
  build       delta/code/build_delta.py --extra-dconn <dC table> --tag delta_v1_hi72      (about 40 s)
  regen       delta/lens_compat/regen_variants.py (every kept fit on every even L <= 118)  (about 5 s)
  smooth      delta/code/smooth_central.py --tag delta_v1_hi72 (median, medoid, floor-mean, floor-medoid centrals and the
              four derived corrected tables)                                               (about 10 s)
  outputs     delta/code/check_outputs.py on the rebuilt files (exit 0)
  validate    delta/code/validate_hi72.py seq, hold, noise:6/7/8 (16 draws)               (about 1 min)
  compare     every rebuilt file against the shipped delta/out file of the same name: equal after removing the
              run-time fields (created, absolute paths; the sha256 of the inputs are compared by file name, the
              derived_from sha256 against the rebuilt base table). Verdict 'bitwise' when the numbers are identical,
              PASS within 1e-9 field-scaled (see SCALE below; mpmath 50-digit fits, so a difference would come from the
              float64 post-processing of another numpy), FAIL otherwise.
  mi_post     the model-independent lens's last two post-processing steps rerun from the shipped intermediate outputs
              on a copy of model-independent/{code,out} in <work>/rt_mi (the copy's headline.json and final72.json are
              deleted first): MI_PRIMARY=run2_fmedoid code/headline.py OUT (reads final_summary.json and
              run2_fmedoid/analysis.json), then code/final72.py OUT (reads compare72.json, headline.json,
              final_summary.json, members_subset.json, run2_k*_f*/analysis_light.json); both JSON files compared with
              the shipped ones, bitwise or within 1e-12 field-scaled (float64 post-processing only)    (seconds)
  keyfits     (only with --flint-py PY whose interpreter imports python-flint) public/refit_keyfits.py: 12 named key
              fits (hi = 118, ext gaps, shift 0) of the joint lens refitted with the shipped joint/code/scan.py run()
              on the shipped delta tables; C4..C7 against out/r72/summary.json (dconn) and summary_dconn_w.json
              (dconn_w) to 1e-9 relative. Without --flint-py: SKIP (reported, not a failure).
SCALE (the fallback tolerance; it is used only when a rebuild is not bitwise): a number b of the shipped file and its
rebuilt value a must satisfy |a - b| <= rtol * s, with s = max |x| over the numeric entries of the list that holds b
(an array such as dC_unc at all L, or one table column), or s = |b| for a number that is not in a list. There is no
absolute floor: small fields (dC_unc, noise sigx of 1e-10 .. 1e-3) are compared at their own scale, and an exact zero
field must stay exactly zero.
usage: python3 public/test_refit.py [--work .work] [--htp ../..] [--data ../../data/HT_1d] [--flint-py PY] [--no-validate]"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from repoint import make_runtime, inputs  # noqa: E402

TAG = "delta_v1_hi72"
RTOL = 1e-9
LINES = []


def log(s):
    print(s, flush=True)
    LINES.append(s)


def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def strip(d, kind):
    """Remove run-time fields; return (stripped copy, {basename: sha256} of recorded inputs)."""
    d = json.loads(json.dumps(d))
    rec = {}
    if kind == "corrected":
        d.pop("created", None)
        rec = {os.path.basename(k): v for k, v in d.pop("sources", {}).items()}
        x = d.get("extra_dconn_csv")
        if x:
            rec[os.path.basename(x.pop("path"))] = x["sha256"]
        if "derived_from" in d:
            d["derived_from"].pop("path")
            rec["derived_from"] = d["derived_from"].pop("sha256")
    elif kind == "smooth":
        d.pop("created", None)
        d.pop("inputs", None)
        d.pop("files", None)
        rec = {os.path.basename(k): v for k, v in d.pop("sha256", {}).items()}
    return d, rec


def isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def diff(a, b, path="", out=None, scale=None):
    """Max field-scaled deviation and structural differences of parsed JSON a (rebuilt) vs b (shipped).
    A number's deviation |a - b| is divided by the field scale s (SCALE in the module docstring): the largest finite
    |x| of the list that holds it, else |b|. s = 0 (an exact zero field) admits no deviation (reported as inf)."""
    out = out if out is not None else {"max": 0.0, "struct": []}
    if isinstance(b, dict):
        if not isinstance(a, dict) or set(a) != set(b):
            out["struct"].append(path or "/")
        else:
            for k in b:
                diff(a[k], b[k], f"{path}/{k}", out)
    elif isinstance(b, list):
        if not isinstance(a, list) or len(a) != len(b):
            out["struct"].append(path)
        else:
            fin = [abs(y) for y in b if isnum(y) and abs(y) != float("inf") and y == y]
            s = max(fin) if fin else None
            for i, (x, y) in enumerate(zip(a, b)):
                diff(x, y, f"{path}[{i}]", out, s)
    elif isnum(b):
        if not isnum(a):
            out["struct"].append(path)
        elif a != b:
            if b != b and a != a:          # NaN in both
                return out
            s = scale if scale is not None else abs(b)
            out["max"] = max(out["max"], abs(a - b) / s if s > 0 else float("inf"))
    elif a != b:
        out["struct"].append(path)
    return out


def verdict(a, b):
    d = diff(a, b)
    if d["struct"]:
        return False, f"structure differs at {d['struct'][:4]}"
    if d["max"] == 0:
        return True, "bitwise"
    return d["max"] <= RTOL, f"max field-scaled dev {d['max']:.1e} (tolerance {RTOL:g})"


def run(cmd, cwd, env, name):
    t = time.time()
    r = subprocess.run([sys.executable] + cmd, cwd=cwd, env=env, capture_output=True, text=True)
    log(f"  {name}: exit {r.returncode}, {time.time() - t:.0f} s")
    if r.returncode:
        log(r.stdout[-2000:] + r.stderr[-3000:])
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=os.path.join(PKG, ".work"))
    ap.add_argument("--htp", default=os.path.join(PKG, "..", ".."))
    ap.add_argument("--data", default=None, help="HT_1d data root (default <htp>/data/HT_1d)")
    ap.add_argument("--flint-py", default=None)
    ap.add_argument("--no-validate", action="store_true")
    a = ap.parse_args()
    a.htp = os.path.abspath(a.htp)       # the stage scripts run in other directories
    I = inputs(a.htp, a.data)
    miss = [k for k in ("DATA_JSON", "RECON_JSON", "S10_CSV", "D5_JSON", "D7_JSON", "CSV") if not os.path.exists(I[k])]
    if miss:
        log(f"test_refit FAIL: cross-package inputs absent: {[I[k] for k in miss]}")
        sys.exit(1)
    rt = make_runtime(a.work, a.htp, a.data)
    code, lens, out = (os.path.join(rt, "delta", x) for x in ("code", "lens_compat", "out"))
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", OMP_NUM_THREADS="1",
               PYTHONDONTWRITEBYTECODE="1", MPLBACKEND="Agg", HT_DATA_JSON=I["DATA_JSON"])
    ok = True
    log(f"runtime copy: {os.path.relpath(rt, PKG)}")

    # inputs
    r = run(["check_inputs.py"], code, env, "check_inputs.py")
    m = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else {}
    good = bool(m) and m["csv_vs_json"] == 0 and m["c03"] < 2e-13 and m["dC4"] < 1e-12 and m["dC5"] < 2e-11 \
        and m["th_vs_raw_rel"] < 1e-8
    log(f"inputs   {'PASS' if good else 'FAIL'}  {json.dumps(m)} (bounds: table = records - raw exactly, C0..C3 < 2e-13, "
        f"dC4 < 1e-12, dC5 < 2e-11, thermal_d7 vs lri_c8 raw < 1e-8 relative)")
    ok &= good

    # build, regen, smooth, outputs
    steps = [(["build_delta.py", "--extra-dconn", I["CSV"], "--tag", TAG], code, "build_delta.py"),
             (["regen_variants.py", "--extra-dconn", I["CSV"], "--published", os.path.join(out, f"{TAG}_variants.json"),
               "--out", os.path.join(out, "variants_full_hi72.json")], lens, "regen_variants.py"),
             (["smooth_central.py", "--tag", TAG], code, "smooth_central.py"),
             (["check_outputs.py"], code, "check_outputs.py")]
    if not a.no_validate:
        steps += [(["validate_hi72.py", "seq"], code, "validate_hi72.py seq"),
                  (["validate_hi72.py", "hold"], code, "validate_hi72.py hold")]
        steps += [(["validate_hi72.py", f"noise:{k}", "16"], code, f"validate_hi72.py noise:{k} 16") for k in (6, 7, 8)]
    for cmd, cwd, name in steps:
        r = run(cmd, cwd, env, name)
        ok &= r.returncode == 0
        if r.returncode:
            break
        if name == "check_outputs.py":
            for ln in r.stdout.strip().splitlines():
                log("    " + ln[:200])

    # compare
    S = os.path.join(PKG, "delta", "out")
    base_sha = sha(os.path.join(out, f"{TAG}_corrected.json")) if os.path.exists(os.path.join(out, f"{TAG}_corrected.json")) else None
    want = {"data.json": sha(I["DATA_JSON"]), "dC_reconciled.json": sha(I["RECON_JSON"]),
            "whole_model_coefficients.csv": sha(I["S10_CSV"]), "d5_all.json": sha(I["D5_JSON"]),
            "d7_all.json": sha(I["D7_JSON"]), "dconn_minus_raw_L46_72.csv": sha(I["CSV"])}
    files = [f"{TAG}_corrected.json", f"{TAG}_variants.json", f"{TAG}_dC_table.csv", "variants_full_hi72.json",
             f"{TAG}_smooth.json", f"{TAG}_smooth_table.csv"] + \
        [f"{TAG}_{x}_corrected.json" for x in ("medoid", "floormean", "floormedoid", "floormean_s46")]
    if not a.no_validate:
        files += [f"validation_hi72/validate_{x}.json" for x in ("seq", "hold", "noise6", "noise7", "noise8")]
    for f in files:
        new, old = os.path.join(out, f), os.path.join(S, f)
        if not os.path.exists(new):
            log(f"compare  FAIL  {f}: not rebuilt")
            ok = False
            continue
        if f.endswith(".csv"):
            good = open(new).read() == open(old).read()
            log(f"compare  {'PASS' if good else 'FAIL'}  {f}: {'bitwise' if good else 'text differs'}")
            ok &= good
            continue
        kind = "smooth" if f.endswith("_smooth.json") else "corrected" if f.endswith("_corrected.json") else "plain"
        jn, rn = strip(json.load(open(new)), kind)
        jo, ro = strip(json.load(open(old)), kind)
        good, how = verdict(jn, jo)
        extra = ""
        if kind == "corrected":
            # recorded input hashes: the shipped file's must equal the public inputs; the rebuilt one's likewise
            exp = {k: v for k, v in want.items() if k in ro}
            bind = all(ro.get(k) == v and rn.get(k) == v for k, v in exp.items())
            if "derived_from" in ro:
                bind &= ro["derived_from"] == sha(os.path.join(S, f"{TAG}_corrected.json")) and rn["derived_from"] == base_sha
            good &= bind
            extra = f"; recorded input sha256 {'match' if bind else 'DIFFER'} ({len(exp)} inputs" + \
                    (", derived_from" if "derived_from" in ro else "") + ")"
        if kind == "smooth":
            bind = all(rn.get(k) == ro.get(k) for k in ("delta_v1_corrected.json", "delta_v1_variants.json",
                                                        "variants_full.json"))
            good &= bind
            extra = f"; run-1 input sha256 {'match' if bind else 'DIFFER'}"
        log(f"compare  {'PASS' if good else 'FAIL'}  {f}: {how}{extra}")
        ok &= good

    # mi_post
    rtm = os.path.join(os.path.abspath(a.work), "rt_mi")
    if os.path.exists(rtm):
        shutil.rmtree(rtm)
    for sub in ("code", "out"):
        shutil.copytree(os.path.join(PKG, "model-independent", sub), os.path.join(rtm, sub),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    mo = os.path.join(rtm, "out")
    for f in ("headline.json", "final72.json"):
        os.remove(os.path.join(mo, f))
    menv = dict(env, MI_PRIMARY="run2_fmedoid")
    for cmd, name in ((["headline.py", mo], "headline.py"), (["final72.py", mo], "final72.py")):
        r = run(cmd, os.path.join(rtm, "code"), menv, f"model-independent/code/{name}")
        ok &= r.returncode == 0
    for f in ("headline.json", "final72.json"):
        new, old = os.path.join(mo, f), os.path.join(PKG, "model-independent", "out", f)
        if not os.path.exists(new):
            log(f"mi_post  FAIL  {f}: not rebuilt")
            ok = False
            continue
        if open(new, "rb").read() == open(old, "rb").read():
            good, how = True, "bitwise (identical bytes)"
        else:
            d = diff(json.load(open(new)), json.load(open(old)))
            good = not d["struct"] and d["max"] <= 1e-12
            how = f"structure {d['struct'][:4]}" if d["struct"] else \
                f"max field-scaled dev {d['max']:.1e} (tolerance 1e-12)"
        log(f"mi_post  {'PASS' if good else 'FAIL'}  model-independent/out/{f}: {how}")
        ok &= good

    # keyfits
    if a.flint_py:
        t = time.time()
        r = subprocess.run([a.flint_py, os.path.join(HERE, "refit_keyfits.py")], cwd=PKG, env=env, capture_output=True,
                           text=True)
        for ln in r.stdout.strip().splitlines():
            log("  " + ln)
        if r.returncode:
            log(r.stderr[-3000:])
        log(f"keyfits  {'PASS' if r.returncode == 0 else 'FAIL'}  ({time.time() - t:.0f} s)")
        ok &= r.returncode == 0
    else:
        log("keyfits  SKIP  no --flint-py interpreter given (python-flint needed; make -f public.mk test FLINT_PY=...)")
    log("test_refit " + ("PASS" if ok else "FAIL"))
    os.makedirs(a.work, exist_ok=True)
    open(os.path.join(a.work, "test_refit.txt"), "w").write("\n".join(LINES) + "\n")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
