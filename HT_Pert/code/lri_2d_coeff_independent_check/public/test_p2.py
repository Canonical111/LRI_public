#!/usr/bin/env python3
"""Fast tests of lri_2d_coeff_independent_check: rerun every code of the snapshot at small cutoff and compare with the
shipped outputs (exact equality for the exact-rational codes, stated tolerances for the float64 codes).

Run from HT_Pert/code/lri_2d_coeff_independent_check (make -f public.mk test). The codes write next to themselves or to
--out, so everything runs in a scratch copy .work/tree (the shipped tree is never written). A few minutes on one node.
  t.rs_exact     rs_exact/ref_fraction.py L = 4, raw / consistent / literal  == results/<scheme>_L4.json (exact)
  t.low_orders   continuum/exact_low_orders.py L = 2..30                     vs continuum/exact_C2_C3.csv (abs 1e-13)
  t.c4           c4_exact/c4_compute.py Lmax = 30                            vs c4_exact/results/c4_L2000.npz (rel 1e-11)
  t.windows      c4_exact/windows.py, residual_log/offdiag_window.py, nm_window.py, nm_legw.py (small Lmax)
                                                                             vs the shipped L <= 20000/8000/1000 shifts (abs 1e-12)
  t.tagchan      residual_log/large_L/tagchan.py Lmax = 100                 vs large_L/results/tag3_L16000.npz (abs 1e-11)
  t.c5           large_L/lib/prod5.py (production engine) Lmax = 12, every scheme; raw C2..C5 vs c5_L300.npz (rel 1e-11),
                 Wc - raw vs results/eps5/dC5_L1000_all.npz (abs 1e-11); large_L/lib_opt/prod5.py vs lib (norm-rel 1e-11)
  t.ce_wc        residual_log/ce_wc/ce_run.py L = 4, schemes Wcs and Wc      == ce_wc/out_wcs, out_local (every value, exact)
  t.cauchy       cauchy/tests.py (self-tests of the Cauchy solver; needs python-flint, FAIL with an install hint without it)
usage: python3 public/test_p2.py [--workers N] [--only NAME[,NAME]]"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import re

import numpy as np

PKG = Path(__file__).resolve().parent.parent
ROWS = []


def check(name, ok, detail):
    ROWS.append((name, "PASS" if ok is True else ("SKIP" if ok is None else "FAIL"), detail))
    print(f"{ROWS[-1][1]}  {name}  {detail}", flush=True)


def run(cmd, cwd, env=None):
    # one thread per process: the codes start their own worker pools (numba would otherwise use every core per worker)
    e = dict(os.environ, OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", OMP_NUM_THREADS="1", NUMBA_NUM_THREADS="1",
             ENGINE_THREADS="1", **(env or {}))
    r = subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-3000:], file=sys.stderr)
    return r.returncode == 0


def t_rs(T, out):
    ok, det = True, []
    for s in ("raw", "consistent", "literal"):
        f = out / f"rs_{s}_L4.json"
        if not run([sys.executable, "ref_fraction.py", "--L", "4", "--scheme", s, "--out", str(f)], T / "rs_exact"):
            return check("t.rs_exact", False, f"{s}: run failed")
        a, b = json.load(open(f)), json.load(open(T / "rs_exact" / "results" / f"{s}_L4.json"))
        same = all(a[k] == b[k] for k in ("C", "r", "g", "E", "vacua"))
        ok &= same
        det.append(f"{s} {'==' if same else '!='}")
    check("t.rs_exact", ok, "L = 4 exact rationals: " + ", ".join(det))


def t_low(T, out):
    Ls = ",".join(str(x) for x in range(2, 31, 2))
    f = out / "low.csv"
    if not run([sys.executable, "exact_low_orders.py", "--L", Ls, "--out", str(f)], T / "continuum"):
        return check("t.low_orders", False, "run failed")
    # under numpy >= 2 the verbatim script writes repr(np.float64(x)) = "np.float64(x)" into the csv: strip the wrapper
    num = lambda v: float(re.sub(r"^np\.float64\((.*)\)$", r"\1", v.strip()))
    new = {int(num(r["L"])): r for r in csv.DictReader(open(f))}
    ref = {int(r["L"]): r for r in csv.DictReader(open(T / "continuum" / "exact_C2_C3.csv"))}
    d = max(abs(num(new[L][k]) - float(ref[L][k])) for L in new for k in ("C2", "C3", "r2", "g2"))
    check("t.low_orders", d <= 1e-13 and len(new) == 15, f"C2, C3, r2, g2 at L = 2..30: max |diff| {d:.1e} (tol 1e-13)")


def t_c4(T, out):
    f = out / "c4_L30.npz"
    if not run([sys.executable, "c4_compute.py", "--Lmax", "30", "--out", str(f)], T / "c4_exact"):
        return check("t.c4", False, "run failed")
    a, b = np.load(f), np.load(T / "c4_exact" / "results" / "c4_L2000.npz")
    m = len(a["L"])
    d = max(float(np.max(np.abs(a[k] / b[k][:m] - 1))) for k in ("C4raw", "C4cons", "C4corr", "C2", "C3"))
    check("t.c4", d <= 1e-11, f"C2, C3, C4 raw/consistent/zero-mode at L <= 30: max rel {d:.1e} (tol 1e-11)")


def t_windows(T, out):
    jobs = [("c4_exact", "windows.py", "400", "windows_L20000.npz", T / "c4_exact" / "results", ("Delta_cons", "Delta_zm")),
            ("residual_log", "offdiag_window.py", "200", "offdiag_L20000.npz", T / "residual_log" / "results", ("off",)),
            ("residual_log", "nm_window.py", "200", "nm_L8000.npz", T / "residual_log" / "results", ("dC4",)),
            ("residual_log", "nm_legw.py", "100", "legw_L1000.npz", T / "residual_log" / "results" / "legw", ("S",))]
    det, ok = [], True
    for d, script, Lmax, ref, rdir, keys in jobs:
        f = out / f"{script}.npz"
        if not run([sys.executable, script, "--Lmax", Lmax, "--out", str(f)], T / d):
            return check("t.windows", False, f"{script}: run failed")
        a, b = np.load(f), np.load(rdir / ref)
        m = len(a["L"])
        diff = max(float(np.max(np.abs(a[k] - b[k][:m]))) for k in keys)
        ok &= diff <= 1e-12
        det.append(f"{script} (Lmax {Lmax}) {diff:.0e}")
    check("t.windows", ok, "max |diff| vs shipped: " + ", ".join(det) + " (tol 1e-12)")


def t_tag(T, out):
    f = out / "tag100.npz"
    if not run([sys.executable, "tagchan.py", "--Lmax", "100", "--out", str(f)], T / "residual_log" / "large_L"):
        return check("t.tagchan", False, "run failed")
    a, b = np.load(f), np.load(T / "residual_log" / "large_L" / "results" / "tag3_L16000.npz")
    m = len(a["L"])
    d = float(np.max(np.abs(a["delta3"] - b["delta3"][:m])))
    check("t.tagchan", d <= 1e-11, f"delta^(3)(L), L <= 100: max |diff| {d:.1e} (tol 1e-11; runs to different Lmax differ by <= 1e-11, fits/delta3_fits.txt)")


def t_c5(T, out, workers):
    env = {"RS_EXACT_DIR": str(T / "rs_exact"), "NUMBA_CACHE_DIR": str(out / "numba")}
    res = {}
    for lib in ("lib", "lib_opt"):
        f = out / f"c5_{lib}_L12.npz"
        if not run([sys.executable, "prod5.py", "--Lmax", "12", "--workers", str(workers), "--cache", str(out / f"cache_{lib}"),
                    "--out", str(f)], T / "residual_log" / "large_L" / lib, env):
            return check("t.c5", False, f"{lib}: run failed")
        res[lib] = np.load(f)
    a = res["lib"]
    b = np.load(T / "residual_log" / "large_L" / "results" / "c5_L300.npz")
    s = np.load(T / "residual_log" / "results" / "eps5" / "dC5_L1000_all.npz")
    m = len(a["L"])
    draw = max(float(np.max(np.abs(a[f"raw_C{k}"][1:] / b[f"raw_C{k}"][1:m] - 1))) for k in (2, 3, 4, 5))
    dwc = float(np.max(np.abs((a["Wc_C5"] - a["raw_C5"]) - s["Wc_dC5"][:m])))
    # lib_opt accumulates in parallel (order not fixed): compare norm-relative per output array, as its regression did
    dopt = max(float(np.max(np.abs(res["lib_opt"][k] - a[k])) / max(float(np.max(np.abs(a[k]))), 1e-300))
               for k in a.files if k != "L")
    elem = sorted((float(np.max(np.abs(res["lib_opt"][k][1:] / a[k][1:] - 1))), k) for k in a.files
                  if k != "L" and np.all(a[k][1:] != 0))[-1]
    check("t.c5", draw <= 1e-11 and dwc <= 1e-11 and dopt <= 1e-11,
          f"L <= 12: raw C2..C5 vs c5_L300.npz max rel {draw:.1e}; Wc shift vs dC5_L1000_all.npz max abs {dwc:.1e}; "
          f"lib_opt vs lib max norm-relative {dopt:.1e} over every scheme array (largest elementwise {elem[0]:.1e} in {elem[1]}) "
          f"(tol 1e-11, 1e-11, 1e-11)")


def t_ce(T, out, workers):
    det, ok = [], True
    for scheme, extra, ref, key in (("Wcs", ["--delta3=-15071/1105920"], "out_wcs/wcs_L4.json", "Wcs"),
                                    ("Wc", [], "out_local/wcA_L4.json", "Wc")):
        f = out / f"ce_{scheme}_L4.json"
        if not run([sys.executable, "ce_run.py", "--L", "4", "--schemes", scheme, "--desc", "odd:all,even:1-2",
                    "--procs", str(workers), "--out", str(f)] + extra, T / "residual_log" / "ce_wc"):
            return check("t.ce_wc", False, f"{scheme}: run failed")
        a = json.load(open(f))["schemes"][scheme]["values"]
        b = json.load(open(T / "residual_log" / "ce_wc" / ref))["schemes"][key]["values"]
        same = sum(a.get(k) == v for k, v in b.items())
        ok &= same == len(b)
        det.append(f"{scheme} {same}/{len(b)} values equal")
    check("t.ce_wc", ok, "L = 4 exact rationals: " + ", ".join(det))


def t_cauchy(T, out):
    # python-flint is REQUIRED: the Cauchy solver is one of the two clean-room solvers of the cited check (HT_Pert note, Sec. 4.2)
    try:
        import flint
    except ImportError:
        return check("t.cauchy", False, "python-flint is not installed: install python-flint (pip install python-flint; "
                     "required for cauchy/, see public/requirements.txt)")
    import time
    t0 = time.time()
    ok = run([sys.executable, "tests.py"], T / "cauchy")
    check("t.cauchy", ok, f"cauchy/tests.py (python-flint {flint.__version__}): two-point function, operators vs brute force, "
                          f"Hellmann-Feynman derivatives at 256 bits, numpy backend; {time.time() - t0:.0f} s")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    W = PKG / ".work"
    T = W / "tree"
    out = W / "test_out"
    shutil.rmtree(T, ignore_errors=True)
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(PKG, T, ignore=shutil.ignore_patterns(".work", "public", "docs"))
    out.mkdir(parents=True)
    tests = {"rs_exact": lambda: t_rs(T, out), "low_orders": lambda: t_low(T, out), "c4": lambda: t_c4(T, out),
             "windows": lambda: t_windows(T, out), "tagchan": lambda: t_tag(T, out), "c5": lambda: t_c5(T, out, a.workers),
             "ce_wc": lambda: t_ce(T, out, a.workers), "cauchy": lambda: t_cauchy(T, out)}
    sel = [x for x in a.only.split(",") if x] or list(tests)
    for k in sel:
        try:
            tests[k]()
        except Exception as e:  # a crashing test is a FAIL, the others still run
            check(f"t.{k}", False, f"exception {type(e).__name__}: {e}")
    nf = sum(r[1] == "FAIL" for r in ROWS)
    print(f"\n{sum(r[1] == 'PASS' for r in ROWS)} PASS, {sum(r[1] == 'SKIP' for r in ROWS)} SKIP, {nf} FAIL")
    sys.exit(1 if nf else 0)


if __name__ == "__main__":
    main()
