"""Summarize independent-check outputs: python summarize.py OUT_DIR"""
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np

out = sys.argv[1]
R = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(out, "*.json")))]
errs = sorted(glob.glob(os.path.join(out, "*.err")))
print(f"{len(R)} results, {len(errs)} failures")
for e in errs:
    print("  FAILED", os.path.basename(e), open(e).read().strip().splitlines()[-1])


def diffs(o, rec):
    de = np.array(o["even"][:5]) - np.array(rec["even"][:5])
    do = np.array(o["odd"][:5]) - np.array(rec["odd"][:5])
    ev = max(abs(o["Ev"][k] - v) for k, v in rec["Ev"].items())
    return de, do, ev


print("\n== fixed couplings (production theta), independent K=(24,24) unless noted; differences vs nz16 record ==")
print(f"{'x':>6} {'L':>3} {'K':>6} {'DeltaE indep':>16} {'dDeltaE(z16)':>13} {'dDE(z12)':>10} {'dDE(z20)':>10} "
      f"{'sig res':>9} {'shad res':>9} {'max even':>9} {'max odd':>9} {'max Ev':>9} {'J1/J2':>9} {'sec':>6}")
fixed = sorted([r for r in R if r["task"]["kind"] == "fixed"],
               key=lambda r: (r["task"]["x"], r["task"]["L"], r["task"]["K"][0], r["task"]["M"]))
worst = defaultdict(float)
for r in fixed:
    t, o, recs = r["task"], r["indep"], r["records"]
    rec = recs["16"]
    de, do, ev = diffs(o, rec)
    x = float(t["x"])
    jd = []
    for J in t["J"]:
        for par in (0, 1):
            mine = np.array(o[f"J{J}_{par}"])
            theirs = np.array(rec["angular"][str(J)][str(par)])
            n = min(len(mine), len(theirs))
            jd.append(np.abs(mine[:n] - theirs[:n]).max())
    dz = {nz: (o["even"][1] - recs[nz]["Delta_thermal"]) if nz in recs else float("nan") for nz in ("12", "20")}
    tag = f"{t['K'][0]}" + ("" if t["M"] == 400 else f"/M{t['M']}")
    print(f"{x:6.3f} {t['L']:3d} {tag:>6} {o['even'][1]:16.12f} {o['even'][1]-rec['Delta_thermal']:+13.2e} "
          f"{dz['12']:+10.1e} {dz['20']:+10.1e} {o['odd'][0]-x:+9.1e} {o['odd'][1]-(2-x):+9.1e} "
          f"{np.abs(de).max():9.1e} {np.abs(do).max():9.1e} {ev:9.1e} {(max(jd) if jd else float('nan')):9.1e} "
          f"{r['seconds']:6.0f}")
    worst[("dDE", t["L"], x < 0.16)] = max(worst[("dDE", t["L"], x < 0.16)], abs(o["even"][1] - rec["Delta_thermal"]))

print("\n== local-basis convergence of the independent solver (Delta_E differences between K) ==")
byxl = defaultdict(dict)
for r in fixed:
    t = r["task"]
    if t["M"] == 400:
        byxl[(t["x"], t["L"])][t["K"][0]] = r["indep"]["even"][1]
for (xs, L), d in sorted(byxl.items()):
    if len(d) > 1:
        ks = sorted(d)
        print(f"x={xs} L={L}: " + "  ".join(f"K{k}-K{ks[-1]}={d[k]-d[ks[-1]]:+.1e}" for k in ks[:-1]))

print("\n== independent re-tuning from shifted seeds (theta_rec + (0.05,-0.05)) ==")
print(f"{'x':>6} {'L':>3} {'DeltaE tuned':>16} {'minus z16 record':>17} {'|dtheta|':>9} {'|R|':>8} {'its':>4} {'sec':>6}")
for r in sorted([r for r in R if r["task"]["kind"] == "tune"], key=lambda r: (r["task"]["x"], r["task"]["L"])):
    t, o, rec = r["task"], r["indep"], r["records"]["16"]
    dth = np.abs(np.array(r["theta_tuned"]) - np.array(rec["theta"])).max()
    print(f"{float(t['x']):6.3f} {t['L']:3d} {o['even'][1]:16.12f} {o['even'][1]-rec['Delta_thermal']:+17.2e} "
          f"{dth:9.1e} {np.abs(r['tune_residual']).max():8.1e} {len(r['tune_history'])-1:4d} {r['seconds']:6.0f}")
