#!/usr/bin/env python3
"""Fresh S10 runs with the shipped production solver, compared with the archived records by the package's own gate.

--set small     (make test)  code/ragged_quotient.py --cutoffs 2 4 8 12 16 20 24 --degree 8 --scheme dconn, one
                process; seconds, < 1 GB.
--set validate  (make smoke) the cluster validation of the production snapshot (slurm/validate.slurm, job 571525 on
                symmetry): Dconn L = 40, 42, 44 and raw L = 44, degree 8, --batch 1, one process each; about 10 min on
                one core, 2.4 GiB.
Then code/compare_archive.py --new-dir <out> (results/new_coefficients as archive): C, r, g, energies and vacuum-grid
coefficients within rtol 1e-10 relative to max(1, |archived|), basis/edge/storage counts exact. The comparison is
written to <work>/fresh_<set>/compare.json. Exit status 1 unless every record passes.
usage: python3 public/fresh_s10.py [--set small|validate] [--work .work]"""
import argparse
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
SETS = {"small": [("dconn", [2, 4, 8, 12, 16, 20, 24], [])],
        "validate": [("dconn", [40], ["--batch", "1"]), ("dconn", [42], ["--batch", "1"]),
                     ("dconn", [44], ["--batch", "1"]), ("raw", [44], ["--batch", "1"])]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=sorted(SETS), default="small")
    ap.add_argument("--work", default=os.path.join(PKG, ".work"))
    a = ap.parse_args()
    out = os.path.abspath(os.path.join(a.work, f"fresh_{a.set}"))
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", OMP_NUM_THREADS="1",
               PYTHONDONTWRITEBYTECODE="1")
    t0 = time.time()
    for scheme, cuts, extra in SETS[a.set]:
        cmd = [sys.executable, "code/ragged_quotient.py", "--cutoffs", *map(str, cuts), "--degree", "8",
               "--scheme", scheme, "--out", out, *extra]
        r = subprocess.run(cmd, cwd=PKG, env=env, capture_output=True, text=True)
        print(f"$ {' '.join(cmd[1:])}  -> exit {r.returncode} ({time.time() - t0:.0f} s)")
        if r.returncode:
            print(r.stdout[-2000:], r.stderr[-2000:])
            print(f"fresh_s10 {a.set} FAIL")
            sys.exit(1)
    r = subprocess.run([sys.executable, "code/compare_archive.py", "--new-dir", out, "--out",
                        os.path.join(out, "compare.json")], cwd=PKG, env=env, capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode:
        print(r.stderr[-2000:])
    print(f"fresh_s10 {a.set} {'PASS' if r.returncode == 0 else 'FAIL'} ({time.time() - t0:.0f} s)")
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
