#!/usr/bin/env python3
"""Fast unit tests of lri_1d_c5_exact in the public tree.

validate/test_core.py names the sibling package lri_1d_c4_exact by an absolute path of the authors' machine (its
regression test of orders 2-4 against C4 is skipped when that path is missing). This wrapper runs a run-time copy of it
in <work>/pubtests/ with that one line pointed at ../lri_1d_c4_exact, sets C4P_DIR for validate/test_kernel5.py (which
reads it), and requires that only the two slow tests (C5T_SLOW) are skipped.  The shipped files are not modified.
usage: python3 public/run_tests_c5.py [--work .work]"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=os.path.join(PKG, ".work"))
    a = ap.parse_args()
    c4p = os.path.abspath(os.path.join(PKG, "..", "lri_1d_c4_exact"))
    if not os.path.exists(os.path.join(c4p, "c4_compute1d.py")):
        sys.exit(f"FAIL: sibling package {c4p} missing")
    src = open(os.path.join(PKG, "validate", "test_core.py")).read()
    new, n = re.subn(r'^C4P = ".*"$', f"C4P = {c4p!r}", src, flags=re.M)
    if n != 1:
        sys.exit("FAIL: validate/test_core.py has no single C4P line")
    T = os.path.abspath(os.path.join(a.work, "pubtests"))
    os.makedirs(T, exist_ok=True)
    open(os.path.join(T, "test_core.py"), "w").write(new)
    env = dict(os.environ, C4P_DIR=c4p, PYTHONPATH=PKG + os.pathsep + os.environ.get("PYTHONPATH", ""))
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rs",
                        os.path.join(T, "test_core.py"), os.path.join(PKG, "validate", "test_kernel5.py")],
                       cwd=PKG, env=env, capture_output=True, text=True)
    print(r.stdout[-3000:], r.stderr[-2000:], sep="\n")
    m = re.search(r"(\d+) passed(?:, (\d+) skipped)?", r.stdout)
    skipped = int(m.group(2) or 0) if m else -1
    slow_only = all("C5T_SLOW" in ln for ln in r.stdout.split("\n") if ln.startswith("SKIPPED"))
    ok = r.returncode == 0 and m is not None and slow_only
    print(f"run_tests_c5  {'PASS' if ok else 'FAIL'}  {m.group(0) if m else 'no summary'}; "
          f"skipped tests are the C5T_SLOW ones only: {slow_only}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
