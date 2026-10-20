#!/usr/bin/env python3
"""Collect the per-task result files into results/indep_results.json and do the
weak-coupling C2 fits.  Usage: python3 analyze.py results/raw_runs  (directory
holding the per-task JSON files copied from the cluster)."""
import glob
import json
import os
import sys
from fractions import Fraction

import numpy as np

here = os.path.dirname(os.path.abspath(__file__))
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "results", "raw_runs")

TARGETS = [0.249, 0.2, 0.1, 0.05, 0.025, 0.01]
WEAK = [0.249975, 0.24995, 0.2499, 0.2498, 0.2497, 0.2495, 0.2493, 0.249, 0.2485, 0.248, 0.247, 0.246, 0.244, 0.242, 0.24]
PROMPT_WEAK = [0.2499, 0.2498, 0.2495, 0.249]


def C2_exact(N):
    tot = Fraction(34, 81)
    v = Fraction(1)
    for n in range(1, N + 1):
        v = v * (Fraction(1, 2) + n - 1) / n
        if n % 2 == 0 and n >= 2:
            tot += v * (Fraction(2, 81) / (n - Fraction(1, 2)) + Fraction(2, 9) / n
                        + Fraction(2, 9) / (n + Fraction(1, 2)) + Fraction(2, 81) / (n + 1))
    return tot


recs = []
for f in sorted(glob.glob(os.path.join(src, "*.json"))):
    for x in json.load(open(f)):
        x["_file"] = os.path.basename(f)
        recs.append(x)

failed = [x for x in recs if "failed" in x]
ok = [x for x in recs if "Delta_eps" in x]


def pick(d, N, presc, need_verified=True):
    c = [x for x in ok if abs(x["delta"] - d) < 1e-12 and x["N"] == N and x["presc"] == presc
         and (x.get("grid_check") is not None or not need_verified)]
    return c[-1] if c else None


def err_est(x):
    """Numerical error estimate for Delta_eps: max of grid-check tuned shifts,
    tuning residual (Jacobian-scaled ~ |F|) and eigen residual."""
    e = 0.0
    gc = x.get("grid_check") or {}
    for k in ("fine", "wide"):
        if k in gc:
            e = max(e, abs(gc[k]["dDelta_eps_tuned_lin"]), abs(gc[k]["max_dlevel_rel"]))
    e = max(e, max(abs(t) for t in x["tuning_residuals"]))
    return e


def slim(x):
    out = dict(delta=x["delta"], N=x["N"], prescription=x["presc"], g=x["g"], r=x["r"], A=x["A"],
               Delta_eps=x["Delta_eps"], E_even_rel=x["E_even"], E_odd_rel=x["E_odd"],
               E_even_abs=x["E_even_abs"], E_odd_abs=x["E_odd_abs"],
               tuning_residuals=x["tuning_residuals"], grid=x["grid"], grid_check=x.get("grid_check"),
               refine_hist=[dict(h=r["h"], Q=r["Q"]) for r in x.get("refine_hist", [])],
               eig_resid=x["eig_resid"], edge_density=x["edge_density"], wall_time=x["wall_time"],
               numerical_error_estimate=err_est(x), host=x.get("host"), stats=x["stats"],
               newton_iterations=len(x["newton_hist"]), guess=x.get("guess"), source=x["_file"],
               code_version=x.get("code_version", "indep_ht v1 (2026-10-08): same physics/solver; grid chosen by "
                                                  "1D-eigenvalue convergence, grid_tol 1e-11"))
    if "Ev" in x:
        out["window_Ev"] = x["Ev"]
        out["window_fixed_point_iterations"] = x.get("fp_iters")
    if "consistency_E0_minus_Evcut" in x:
        out["consistency_E0_minus_Evcut"] = x["consistency_E0_minus_Evcut"]
    if "grid_warning" in x:
        out["grid_warning"] = x["grid_warning"]
    return out


table = []
for presc, Ns, ds in (("raw", (12, 16, 20), TARGETS), ("consistent", (12, 16, 20), TARGETS),
                      ("literal", (12,), (0.2, 0.1))):
    for d in ds:
        for N in Ns:
            x = pick(d, N, presc)
            table.append(slim(x) if x else dict(delta=d, N=N, prescription=presc, missing=True))
weak = []
for presc in ("raw", "consistent"):
    for N in (0, 2, 4, 8, 12, 16):
        for d in WEAK:
            x = pick(d, N, presc)
            if x:
                weak.append(slim(x))


def fit(ds, De, free=True, order=3):
    """Uniform-weight least squares in Delta_eps space (the numerical noise is
    ~uniform in Delta_eps), in the scaled variable t = eps/max(eps).
    free:  Delta = c0 + c1 eps + C2 eps^2 + ... + C_order eps^order.
    fixed: Delta - 1/2 + eps/6 = C2 eps^2 + ... + C_order eps^order."""
    eps = 1 - 4 * np.array(ds)
    De = np.array(De)
    sc = eps.max()
    t = eps / sc
    if free:
        A = np.vstack([t ** k for k in range(order + 1)]).T
        c, *_ = np.linalg.lstsq(A, De, rcond=None)
        rms = float(np.sqrt(np.mean((A @ c - De) ** 2)))
        return c / sc ** np.arange(order + 1), rms
    z = De - 0.5 + eps / 6
    A = np.vstack([t ** k for k in range(2, order + 1)]).T
    c, *_ = np.linalg.lstsq(A, z, rcond=None)
    rms = float(np.sqrt(np.mean((A @ c - z) ** 2)))
    return c / sc ** np.arange(2, order + 1), rms


c2rows = []
for presc in ("raw", "consistent"):
    for N in (0, 2, 4, 8, 12, 16):
        pts = {}
        for x in weak:
            if x["prescription"] == presc and x["N"] == N:
                pts[round(x["delta"], 10)] = x["Delta_eps"]
        pts = sorted(pts.items())
        if len(pts) < 4:
            continue
        dd, De = map(np.array, zip(*pts))
        eps = 1 - 4 * dd
        ex = float(C2_exact(N))
        row = dict(presc=presc, N=N, C2_exact=ex, C2_exact_fraction=str(C2_exact(N)), npts=len(pts),
                   deltas=dd.tolist(), Delta_eps=De.tolist())
        sel = [(d, e) for d, e in pts if any(abs(d - p) < 1e-12 for p in PROMPT_WEAK)]
        if len(sel) == 4:
            d4, e4 = zip(*sel)
            c, rms = fit(d4, e4, free=True, order=3)
            row["prompt4_free"] = dict(c0=c[0], c1=c[1], C2=c[2], C3=c[3], C2_minus_exact=c[2] - ex)
            c, rms = fit(d4, e4, free=False, order=3)
            row["prompt4_fixed"] = dict(C2=c[0], C3=c[1], C2_minus_exact=c[0] - ex)
        m = eps < 0.0101
        for order in (5, 6, 7):
            c, rms = fit(dd[m], De[m], free=False, order=order)
            row["small_eps_fixed_o%d" % order] = dict(C2=c[0], C2_minus_exact=c[0] - ex, coefs=c.tolist(), rms=rms,
                                                      npts=int(m.sum()), eps_max=float(eps[m].max()))
        c, rms = fit(dd[m], De[m], free=True, order=6)
        row["small_eps_free_o6"] = dict(c0=c[0], c1=c[1], C2=c[2], C2_minus_exact=c[2] - ex, coefs=c.tolist(), rms=rms)
        c2rows.append(row)

retune = []
for f in sorted(glob.glob(os.path.join(here, "results", "retune_check", "*.json"))):
    retune.append(json.load(open(f)))

out = dict(full_retune_grid_checks=retune, description="Independent HT check of the d=1 LRI (indep_ht.py). Energies relative to E_even0.",
           conventions=dict(H="H_z = delta p^2/4 + A q^2 + g q^4/12 (+const), A = delta/4 + r - g/2",
                            sector="reflection-even", window="D(N) = Ev(cut) - Ev(cut-N)"),
           points=table, weak_coupling_points=weak, C2_fits=c2rows,
           failed=[dict(delta=x["delta"], N=x["N"], presc=x["presc"], failed=x["failed"]) for x in failed])
os.makedirs(os.path.join(here, "results"), exist_ok=True)
with open(os.path.join(here, "results", "indep_results.json"), "w") as fh:
    json.dump(out, fh, indent=1)

print("%-10s %-6s %3s %16s %18s %18s %9s %8s" % ("presc", "delta", "N", "Delta_eps", "g", "r", "err", "wall"))
for x in table:
    if x.get("missing"):
        print("%-10s %-6g %3d   MISSING" % (x["prescription"], x["delta"], x["N"]))
        continue
    print("%-10s %-6g %3d %16.12f %18.10g %18.10g %9.1e %8.0f" % (
        x["prescription"], x["delta"], x["N"], x["Delta_eps"], x["g"], x["r"], x["numerical_error_estimate"],
        x["wall_time"]))
print()
for r in c2rows:
    s = "%-10s N=%2d C2_exact=%.10f" % (r["presc"], r["N"], r["C2_exact"])
    if "prompt4_free" in r:
        p = r["prompt4_free"]
        s += " | 4pt free: c0-1/2=%.1e c1+1/6=%.1e C2 %+.1e" % (p["c0"] - 0.5, p["c1"] + 1 / 6, p["C2_minus_exact"])
        s += " | 4pt fixed C2 %+.1e" % r["prompt4_fixed"]["C2_minus_exact"]
    for o in (5, 6, 7):
        s += " | o%d %.10f (%+.1e)" % (o, r["small_eps_fixed_o%d" % o]["C2"], r["small_eps_fixed_o%d" % o]["C2_minus_exact"])
    p = r["small_eps_free_o6"]
    s += " | free o6: c0-1/2=%.1e c1+1/6=%.1e C2 %+.1e" % (p["c0"] - 0.5, p["c1"] + 1 / 6, p["C2_minus_exact"])
    print(s)
if failed:
    print("\nFAILED points:")
    for x in failed:
        print(x["delta"], x["N"], x["presc"], x["failed"])

# ---------------------------------------------------------------- markdown tables
md = []
md.append("| δ | N | prescription | Δ_ε | g | r | E_even2 | E_even3 | E_odd2 | E_odd3 | max\\|F\\| | grid check | est. error | wall [s] |")
md.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for x in table:
    if x.get("missing"):
        md.append("| %g | %d | %s | MISSING | | | | | | | | | | |" % (x["delta"], x["N"], x["prescription"]))
        continue
    gc = x.get("grid_check") or {}
    gcm = max([abs(gc[k]["dDelta_eps_tuned_lin"]) for k in gc] + [0.0])
    md.append("| %g | %d | %s | %.10f | %.10g | %.10g | %.8f | %.8f | %.8f | %.8f | %.1e | %.1e | %.0e | %.0f |" % (
        x["delta"], x["N"], x["prescription"], x["Delta_eps"], x["g"], x["r"], x["E_even_rel"][2], x["E_even_rel"][3],
        x["E_odd_rel"][2], x["E_odd_rel"][3], max(abs(t) for t in x["tuning_residuals"]), gcm,
        max(x["numerical_error_estimate"], 1e-12), x["wall_time"]))
md.append("")
md.append("| prescription | N | C2 exact | C2 fit (o6, ε≤0.008) | fit − exact | o5 − exact | o7 − exact | 4-pt free fit − exact | 4-pt: c0−1/2 | 4-pt: c1+1/6 |")
md.append("|---|---|---|---|---|---|---|---|---|---|")
for r in c2rows:
    p4 = r.get("prompt4_free", {})
    md.append("| %s | %d | %.10f | %.10f | %+.1e | %+.1e | %+.1e | %+.1e | %+.1e | %+.1e |" % (
        r["presc"], r["N"], r["C2_exact"], r["small_eps_fixed_o6"]["C2"], r["small_eps_fixed_o6"]["C2_minus_exact"],
        r["small_eps_fixed_o5"]["C2_minus_exact"], r["small_eps_fixed_o7"]["C2_minus_exact"],
        p4.get("C2_minus_exact", float("nan")), p4.get("c0", float("nan")) - 0.5, p4.get("c1", float("nan")) + 1 / 6))
with open(os.path.join(here, "results", "tables.md"), "w") as fh:
    fh.write("\n".join(md) + "\n")
