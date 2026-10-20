#!/usr/bin/env python3
"""Light refit of the joint lens: named key fits recomputed with the shipped scan code, compared with the shipped summaries.

The joint lens (joint/code: fitcore.py, 256-bit python-flint arb least squares; scan.py) ran 186,624 + 129,600 fits on
symmetry (jobs 572001/572002/572030/572031); the raw scan records are not in git. This check reruns 12 of them with the
unmodified scan.run() on the shipped corrected tables (delta/out/delta_v1_hi72_corrected.json and
variants_full_hi72.json, as DCONN_CORRECTED / DCONN_VARIANTS_FULL in joint/cluster/run_scan_shared.sbatch; run-1 tables
as DCONN_OLD_*): kind o7, hi = 118, gap 'ext', shift 0, for the bases and modes below, unweighted ('dconn') and weighted
('dconn_w'); the intercepts C4..C7 must equal key_fits_hi118 of joint/out/r72/summary.json and summary_dconn_w.json to
1e-9 relative (the production fits were reproduced bit for bit by the S1B verifier; 'bitwise' is reported when exact).
Needs python-flint (production: 0.9.0) and numpy. Run from the package folder:  python3 public/refit_keyfits.py"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
DOUT = os.path.join(PKG, "delta", "out")
os.environ.setdefault("DCONN_CORRECTED", os.path.join(DOUT, "delta_v1_hi72_corrected.json"))
os.environ.setdefault("DCONN_VARIANTS_FULL", os.path.join(DOUT, "variants_full_hi72.json"))
os.environ.setdefault("DCONN_OLD_CORRECTED", os.path.join(PKG, "delta", "archived_out_delta_v1", "delta_v1_corrected.json"))
os.environ.setdefault("DCONN_OLD_VARIANTS_FULL", os.path.join(PKG, "run1", "joint", "out", "variants_full.json"))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(PKG, "joint", "code"))
import scan  # noqa: E402  (the shipped joint lens; imports fitcore -> python-flint)

KEYS = [("A", "fixed", 16), ("B", "fixed", 60), ("E", "fixed", 60), ("Dj", "fixed", 60), ("E", "free", 40),
        ("B", "FL", 60)]
RTOL = 1e-9


def main():
    t0 = time.time()
    scan.init()
    worst, bad, n = 0.0, [], 0
    for ds, summ in (("dconn", "summary.json"), ("dconn_w", "summary_dconn_w.json")):
        S = json.load(open(os.path.join(PKG, "joint", "out", "r72", summ)))["key_fits_hi118"]
        for b, mode, lo in KEYS:
            rec = scan.run(dict(kind="o7", ds=ds, hi=118, low="same", lo=lo, base=b, mode=mode, sh=0.0, gap="ext"))
            ref = S[f"{b}_{mode}_lo{lo}"]
            devs = [abs(rec["lim"][k] - ref[f"C{k}"]) / abs(ref[f"C{k}"]) for k in (4, 5, 6, 7)]   # |C_k| >= 45
            worst = max(worst, max(devs))
            n += 1
            if max(devs) > RTOL:
                bad.append(f"{ds}:{b}_{mode}_lo{lo}")
            print(f"{ds:8s} {b:2s} {mode:5s} lo={lo:2d}  C4..C7 = " +
                  ", ".join(f"{rec['lim'][k]:.10g}" for k in (4, 5, 6, 7)) + f"  max rel dev {max(devs):.1e}")
    import flint
    print(f"{n} key fits, python-flint {flint.__version__}: max rel dev {worst:.1e} "
          f"({'bitwise' if worst == 0 else f'tolerance {RTOL:g}'}); differing {bad}; {time.time() - t0:.0f} s")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
