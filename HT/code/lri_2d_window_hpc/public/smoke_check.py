#!/usr/bin/env python3
"""Compare a smoke rerun with the shipped production record (tolerances hold across CPU vendors and BLAS builds).

  smoke_check.py NEW.json RECORD.json             point rerun: Delta_E and gaps to 1e-10, theta to 1e-8
  smoke_check.py --valley-seed RECORD.json        print "theta0 theta1+0.002" for public/scan_valley.py
  smoke_check.py --valley VALLEY.json RECORD.json valley rerun: theta1 on f2 = 0 back at the record to 1e-8, |f1| <= 1e-9
"""
import json
import sys


def load(p):
    return json.load(open(p))


def main(a):
    if a[0] == "--valley-seed":
        th = load(a[1])["theta"]
        print(repr(th[0]), repr(th[1] + 0.002))
        return 0
    rows = []
    if a[0] == "--valley":
        v, rec = load(a[1]), load(a[2])
        s = [r for r in v["rows"] if r.get("summary")][0]
        rows.append(("theta1 on f2=0 - record", s["theta1_on_f2_zero"] - rec["theta"][1], 1e-8))
        rows.append(("f1 on f2=0", s["f1_on_curve"], 1e-9))
        rows.append(("f2", s["f2"], 1e-9))
    else:
        new, rec = load(a[0]), load(a[1])
        rows.append(("Delta_E", new["Delta_thermal"] - rec["Delta_thermal"], 1e-10))
        rows.append(("even gaps", max(abs(u - w) for u, w in zip(new["even_gaps"], rec["even_gaps"])), 1e-10))
        rows.append(("odd gaps", max(abs(u - w) for u, w in zip(new["odd_gaps"], rec["odd_gaps"])), 1e-10))
        rows.append(("theta", max(abs(u - w) for u, w in zip(new["theta"], rec["theta"])), 1e-8))
        rows.append(("basis sha256", 0.0 if new["configuration"]["basis_sha256"] == rec["configuration"]["basis_sha256"]
                     else 1.0, 0.0))
    bad = 0
    for name, d, tol in rows:
        ok = abs(d) <= tol
        bad += not ok
        print(f"{name:26s} {'PASS' if ok else 'FAIL'}  {d:+.3e}  (tol {tol:g})")
    print(f"{len(rows) - bad} PASS, {bad} FAIL")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
