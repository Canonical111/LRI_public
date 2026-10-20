#!/usr/bin/env python3
"""smoke_compare.py NEW_DIR SHIPPED_DIR TASK [TASK ...]: a fresh run_check.py output against the shipped one and the
production record. Tolerances hold across CPU vendors and BLAS builds (the shipped runs were AMD EPYC, symmetry)."""
import json
import sys
from pathlib import Path

import numpy as np


def main(new, old, tasks):
    bad = n = 0
    for t in tasks:
        a = json.load(open(Path(new) / f"{t}.json"))
        b = json.load(open(Path(old) / f"{t}.json"))
        rec = a["records"]["16"]
        rows = [
            ("levels vs shipped output", max(np.abs(np.subtract(a["indep"]["even"], b["indep"]["even"])).max(),
                                             np.abs(np.subtract(a["indep"]["odd"], b["indep"]["odd"])).max()), 1e-10),
            ("Delta_E vs production record", a["indep"]["even"][1] - rec["Delta_thermal"], 1e-11),
            ("record sha256 as shipped", 0.0 if rec["record_sha256"] == b["records"]["16"]["record_sha256"] else 1.0, 0.0),
        ]
        for name, d, tol in rows:
            ok = abs(d) <= tol
            bad += not ok
            n += 1
            print(f"{t:34s} {name:30s} {'PASS' if ok else 'FAIL'}  {d:+.3e}  (tol {tol:g})")
    print(f"{n - bad} PASS, {bad} FAIL")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3:]))
