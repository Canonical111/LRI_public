#!/usr/bin/env python3
"""The package's own test suite (tests/run_all.py) on a run-time copy, with an order-insensitive comparison.

tests/run_all.py runs exact_stationarity.py, independent_coefficients.py (fresh full-order runs at L <= 28 against the
vendored ordinary and exact-Fraction references, about 1 min), forecast_replay.py and validate_saved.py. They rewrite
files under results/ that MANIFEST.sha256 binds (test_run.json with timings; code/analyze.py, called by
validate_saved.py, rewrites results/whole_model_coefficients.csv with rows in file-system order). So this wrapper
  1. copies the package to <work>/tree (the shipped files are never touched),
  2. runs tests/run_all.py there (single-threaded BLAS, MPLBACKEND=Agg),
  3. compares every file the suite rewrote with the shipped one:
       results/test_run.json   only the return codes (all 0) are compared; timings differ by construction;
       *.csv                   same set of lines (row order ignored); if not, the same rows keyed by (Lambda, scheme) with
                               numbers equal to 1e-12 relative to max(1, |shipped|), the timing columns ignored;
       *.json                  the same structure with numbers equal to 1e-12 relative to max(1, |shipped|) (absolute below
                               1); keys 'seconds' and 'maxrss_*' ignored;
     anything else rewritten or created under results/ is a FAIL.
Prints a table and PASS/FAIL (exit 1 on FAIL); the table also goes to <work>/run_tests_s10.txt.
usage: python3 public/run_tests_s10.py [--work .work]"""
import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
RTOL = 1e-12
IGNORE_KEYS = {"seconds", "maxrss_kib", "maxrss_MiB"}


def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def snapshot(root):
    out = {}
    for d, ds, fs in os.walk(root):
        ds[:] = [x for x in ds if x not in ("__pycache__", ".mplconfig")]
        for f in fs:
            p = os.path.join(d, f)
            out[os.path.relpath(p, root)] = sha(p)
    return out


def close(a, b):
    return abs(a - b) <= RTOL * max(1.0, abs(b))


def jcmp(a, b, path=""):
    """Return a list of differences between parsed JSON a (rerun) and b (shipped)."""
    if isinstance(b, dict):
        if not isinstance(a, dict) or set(a) != set(b):
            return [f"{path}: keys differ"]
        out = []
        for k in b:
            if k in IGNORE_KEYS:
                continue
            out += jcmp(a[k], b[k], f"{path}.{k}")
        return out
    if isinstance(b, list):
        if not isinstance(a, list) or len(a) != len(b):
            return [f"{path}: length differs"]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += jcmp(x, y, f"{path}[{i}]")
        return out
    if isinstance(b, bool) or b is None or isinstance(b, str):
        return [] if a == b else [f"{path}: {a!r} != {b!r}"]
    if isinstance(b, (int, float)) and isinstance(a, (int, float)) and not isinstance(a, bool):
        return [] if close(float(a), float(b)) else [f"{path}: {a!r} != {b!r}"]
    return [f"{path}: type differs"]


def num(x):
    try:
        return float(x)
    except ValueError:
        return None


def csvcmp(new, old):
    a, b = open(new).read().splitlines(), open(old).read().splitlines()
    if a[:1] == b[:1] and sorted(a) == sorted(b):
        return [], "same rows, row order " + ("identical" if a == b else "differs (file-system order)")
    ra = {(r["Lambda"], r["scheme"]): r for r in csv.DictReader(io.StringIO("\n".join(a)))}
    rb = {(r["Lambda"], r["scheme"]): r for r in csv.DictReader(io.StringIO("\n".join(b)))}
    if set(ra) != set(rb):
        return ["row keys differ"], ""
    bad = []
    for key, r in rb.items():
        for col, v in r.items():
            if col in ("seconds", "maxrss_MiB"):
                continue
            x, y = num(ra[key][col]), num(v)
            if (x is None) != (y is None) or (x is None and ra[key][col] != v) or (x is not None and not close(x, y)):
                bad.append(f"{key}:{col}")
    return bad, f"rows equal to {RTOL:g} relative"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=os.path.join(PKG, ".work"))
    a = ap.parse_args()
    work = os.path.abspath(a.work)
    T = os.path.join(work, "tree")
    if os.path.exists(T):
        shutil.rmtree(T)
    os.makedirs(work, exist_ok=True)

    def ign(d, names):
        return [n for n in names if os.path.join(os.path.abspath(d), n) == work or n in ("__pycache__", ".work")]
    shutil.copytree(PKG, T, ignore=ign)
    before = snapshot(T)
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", OMP_NUM_THREADS="1", MPLBACKEND="Agg",
               MPLCONFIGDIR=os.path.join(T, ".mplconfig"), PYTHONDONTWRITEBYTECODE="1")
    t0 = time.time()
    r = subprocess.run([sys.executable, "tests/run_all.py"], cwd=T, env=env, capture_output=True, text=True)
    dt = time.time() - t0
    after = snapshot(T)
    lines = [f"tests/run_all.py (copy in {os.path.relpath(T, PKG)}): exit {r.returncode}, {dt:.0f} s",
             *("  " + x for x in r.stdout.strip().splitlines())]
    ok = r.returncode == 0
    if not ok:
        lines.append(r.stderr[-3000:])
    changed = sorted(k for k in after if k in before and after[k] != before[k])
    created = sorted(k for k in after if k not in before)
    for rel in changed:
        new, old = os.path.join(T, rel), os.path.join(PKG, rel)
        if rel == "results/test_run.json":
            recs = json.load(open(new))
            good = len(recs) == 4 and all(x["returncode"] == 0 for x in recs)
            lines.append(f"  {rel}: rewritten (timings); {len(recs)} drivers, return codes all 0: {good}")
        elif rel.endswith(".csv"):
            bad, how = csvcmp(new, old)
            good = not bad
            lines.append(f"  {rel}: rewritten; {how if good else 'DIFFERS ' + str(bad[:5])}")
        elif rel.endswith(".json"):
            bad = jcmp(json.load(open(new)), json.load(open(old)))
            good = not bad
            lines.append(f"  {rel}: rewritten; " + (f"equal to {RTOL:g} relative" if good else f"DIFFERS {bad[:5]}"))
        else:
            good = False
            lines.append(f"  {rel}: rewritten, not a compared type")
        ok = ok and good
    for rel in created:
        good = not rel.startswith("results/")
        lines.append(f"  {rel}: created" + ("" if good else " under results/ (unexpected)"))
        ok = ok and good
    lines.append(f"unchanged files: {len(before) - len(changed)}; rewritten: {len(changed)}; created: {len(created)}")
    lines.append("run_tests_s10 " + ("PASS" if ok else "FAIL"))
    txt = "\n".join(lines)
    print(txt)
    open(os.path.join(work, "run_tests_s10.txt"), "w").write(txt + "\n")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
