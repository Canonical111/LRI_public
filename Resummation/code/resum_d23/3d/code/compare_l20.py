#!/usr/bin/env python3
"""Evaluate the frozen Borel prescriptions at each supplied HT abscissa.

Run under Slurm. No fit, interpolation, extrapolation, or HT solve is performed.
"""
import csv
import hashlib
import json
import os
from pathlib import Path
import numpy as np
import mpmath as mp
import calculate as c

R = Path(__file__).resolve().parents[1]
I = R / "inputs/ht_l20"
index = json.loads((I / "index.json").read_text())
records = index["records"]
table = {}
steps = {}
for line in (I / "l20_results/L14_L20_table.txt").read_text().splitlines():
    fields = line.split()
    try:
        x = float(fields[0])
    except (ValueError, IndexError):
        continue
    table[x] = [float(v) for v in fields[1:5]]
    steps[x] = [float(v) for v in fields[5:8]]
assert len(records) == len(table) == 15
for rec in records:
    j = json.loads((I / rec["source"]).read_text())
    assert hashlib.sha256((I / rec["source"]).read_bytes()).hexdigest() == rec["sha256"]
    assert j["accepted"] and j["spacetime_dimension"] == 3 and j["bath_cut"] == 20
    x = j["delta"]  # The HT schema uses delta for Delta_sigma, not delta_SR.
    assert abs(j["s"] - (3 - 2*x)) < 1e-12
    assert abs(j["epsilon"] - (3 - 4*x)) < 1e-12
    assert max(abs(j["Delta_sigma_measured"]-x), abs(j["Delta_shadow_measured"]-(3-x))) < 1e-8
    assert abs(j["Delta_thermal"] - table[x][3]) <= 5.1e-9
xs = np.array([r["delta"] for r in records])
assert np.all(np.diff(xs) > 0)
cb = c.cb("slope", 8, x=xs)
cb120 = c.cb("slope", 8, x=xs, nquad=120)
assert np.max(np.abs(cb-cb120)) < 2e-10
pb4, poles4 = c.pb("slope", 8, b=4, x=xs)
pb0, poles0 = c.pb("slope", 8, b=0, x=xs)
assert pb4 is None and pb0 is not None
pb4old,_ = c.pb("slope",7,b=4,x=xs)
assert pb4old is not None
scan = [c.cb("slope", n, b, a, x=xs)
        for n in c.P["core_scan"]["orders"]
        for b in c.P["core_scan"]["b"]
        for a in c.P["core_scan"]["alpha"]]
lo, hi = np.min(scan, axis=0), np.max(scan, axis=0)
central_slope = c.CSR
sr = []
for v in ("0.269", "0.276"):
    c.CSR = mp.mpf(v)
    sr.append(c.cb("slope", 8, x=xs))
c.CSR = central_slope
rows = []
for i, rec in enumerate(records):
    x, ht = rec["delta"], rec["Delta_thermal"]
    l14, l16, l18, _ = table[x]
    row = dict(Delta_sigma=x, s=3-2*x, epsilon=3-4*x, delta_SR=x-float(c.S),
               HT_L14=l14, HT_L16=l16, HT_L18=l18, HT_L20=ht,
               CB8=cb[i], PB8_b4=None, PB7_b4=pb4old[i], PB8_b0=pb0[i],
               core_low=lo[i], core_high=hi[i],
               sri_low=min(v[i] for v in sr), sri_high=max(v[i] for v in sr),
               L20_minus_CB8=ht-cb[i], L20_minus_PB8_b0=ht-pb0[i],
               L20_minus_L18=steps[x][2],
               L18_minus_L16=steps[x][1], L16_minus_L14=steps[x][0],
               L20_minus_rounded_L18=ht-l18, accepted=rec["accepted"],
               eigenvector_residual=rec["max_eigenvector_residual"],
               tuning_residual=rec["tuning_residual"], source=rec["source"])
    rows.append(row)
with (R/"results/ht_l20_comparison.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
out = dict(date="2026-10-12", job_id=os.getenv("SLURM_JOB_ID"),
           records=rows, max_GL120_240_difference=float(np.max(np.abs(cb-cb120))),
           selected_PB_poles=[p for p in poles4+poles0 if p.get("selected")],
           max_abs_L20_minus_CB8=max(abs(r["L20_minus_CB8"]) for r in rows),
           max_target_tuning_residual=max(r["tuning_residual"] for r in records),
           comparisons_outside_core=sum(not r["core_low"] <= r["HT_L20"] <= r["core_high"] for r in rows),
           scope="Finite L=20 full-vacuum-window Hamiltonian, not a continuum extrapolation. "
                 "L14/L16/L18 are copied from the supplied eight-decimal table; cutoff steps are not error bars.",
           input_index_sha256=hashlib.sha256((I/"index.json").read_bytes()).hexdigest(),
           script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(R/"results/ht_l20_comparison.json").write_text(json.dumps(out, indent=2))
for r in rows:
    print("%.6f HT=%.12f CB=%.12f HT-CB=%+.9g L20-L18=%+.9g" %
          (r["Delta_sigma"], r["HT_L20"], r["CB8"], r["L20_minus_CB8"], r["L20_minus_L18"]), flush=True)
print("VALIDATION PASSED; job", out["job_id"], flush=True)
