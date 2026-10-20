#!/usr/bin/env python3
"""A3: diagram sums (assemble5) vs an independent brute-force float64 Rayleigh-Schroedinger solver at every quarter
cutoff cut4 = 4..cut4max (PLAN A3).  Reference: vendor/brute_rs_cut4.py (verbatim copy of
lri_1d_c4_exact/vendor/brute_rs_cut4.py = lri_hpc_Hamitonian/reference/check_lri_hamiltonian.py with the cutoff
generalised to an integer cut4), run as FockSpace(cut4, pmax=11, degree=5) with the direct order-5 recursion
initial_wavefunctions(order=5) (not the quotient route).  pmax = 11 is required and sufficient at eps^5: psi^(4) is
needed on P <= 3 + 4, which needs psi^(3) on P <= 11; pmax <= 10 is silently wrong (measured at cut4 = 48: pmax 10
misses the exact rational C5 by 94 %, pmax 11 and 15 agree with it to 1.5e-15).
Compared at each cutoff (28 numbers):
  E_p^(k), p = 0..3, k = 2..5   engine value X_p^(k) + 2p r_k + p(p-1)/2 g_k  (<p|M_0|p> = 2p, <p|V_0|p> = p(p-1)/2)
  r_k, g_k, C_k = E_2^(k) - E_0^(k), k = 2..5.
Engine: res = assemble5.compute(Lmax, verbose=False), Lmax = ceil(cut4max/4), quarter-grid arrays r2..r5, g2..g5,
C2..C5 of shape (4 Lmax + 1,) and X2..X5 of shape (4, 4 Lmax + 1) (INTERFACES.md); the shapes (and cut4, if present)
are checked.  Gate: relative deviation <= 1e-11, with an absolute floor: orders k <= 4 as C4P (absolute <= 1e-12 where
|brute value| < 0.1); order k = 5 absolute <= 1e-11 where |brute value| < 1 (PLAN deviation, logged: the float64
assembly at eps^5 has an absolute error of a few 1e-12 set by terms of size 10..1000 -- measured 3e-13..5e-12 for g5,
C5, E_p^(5) at cut4 = 4..20 -- so values that happen to be small, e.g. |E_3^(5)| = 0.144 at cut4 = 4, show a
relative error of 1e-11 without any defect; the exact-rational gates A1/A2 pass at <= 3.6e-13).  A non-finite value
on either side fails; the comparison count must be 28 per cutoff.
usage: python3 validate/v3_brute.py [--cut4max 64]"""
import argparse
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "vendor"))
import brute_rs_cut4 as brute          # noqa: E402

PMAX = 11          # particle cap of the brute space; <= 10 is wrong at eps^5 (see docstring)
KS = (2, 3, 4, 5)
PS = (0, 1, 2, 3)
NPER = 28          # 16 E_p^(k) + 12 (r_k, g_k, C_k)
GATE = 1e-11


def ndev(v, ref, k=4):
    """Normalised deviation (in units where the gate is 1e-11): relative where |ref| >= floor, otherwise absolute
    scaled to the gate (floor 0.1 with absolute 1e-12 for k <= 4; floor 1 with absolute 1e-11 for k = 5);
    non-finite values (either side) give inf."""
    if not (math.isfinite(v) and math.isfinite(ref)):
        return math.inf
    if k >= 5:
        return abs(v - ref) / max(abs(ref), 1.0)
    return abs(v - ref) / abs(ref) if abs(ref) >= 0.1 else abs(v - ref) / 1e-12 * 1e-11


def worse(a, b):
    """max of two deviations; a NaN (never produced by ndev) counts as inf."""
    if not (a == a and b == b):
        return math.inf
    return max(a, b)


def engine_grid_problems(res, Lmax):
    """Shapes of the engine arrays on the quarter grid cut4 = 0..4 Lmax; returns a list of problems."""
    nc = 4 * Lmax + 1
    bad = []
    if "cut4" in res and not np.array_equal(np.asarray(res["cut4"]), np.arange(nc)):
        bad.append("cut4 != 0..4 Lmax")
    for k in KS:
        for nm in ("r", "g", "C"):
            key = f"{nm}{k}"
            if key not in res or np.shape(res[key]) != (nc,):
                bad.append(f"{key} missing or shape != ({nc},)")
        if f"X{k}" not in res or np.shape(res[f"X{k}"]) != (4, nc):
            bad.append(f"X{k} missing or shape != (4, {nc})")
    return bad


def run_brute(c):
    """Brute-force order-5 RS at cut4 = c: (dimension, E[p, k], r[k], g[k]), k = 0..5."""
    sp = brute.FockSpace(c, pmax=PMAX, degree=5)
    _, E, r, g = brute.initial_wavefunctions(sp, order=5)
    return sp.dim, E, r, g


def compare_cutoff(res, c, E, r, g):
    """The NPER normalised deviations at cutoff c as [(label, deviation)]: 16 E_p^(k), then r_k, g_k, C_k."""
    out = []
    for k in KS:
        rk, gk = float(res[f"r{k}"][c]), float(res[f"g{k}"][c])
        for p in PS:
            mine = float(res[f"X{k}"][p][c]) + 2 * p * rk + p * (p - 1) / 2 * gk
            out.append((f"E_{p}^({k})", ndev(mine, float(E[p, k]), k)))
    for k in KS:
        for name, ref in (("r", r[k]), ("g", g[k]), ("C", E[2, k] - E[0, k])):
            out.append((f"{name}{k}", ndev(float(res[f"{name}{k}"][c]), float(ref), k)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cut4max", type=int, default=64)
    a = ap.parse_args()
    if a.cut4max < 4:
        raise SystemExit("--cut4max must be >= 4")
    import assemble5   # noqa: E402  (imported here so that the comparison helpers above load without the engine)
    Lmax = -(-a.cut4max // 4)
    t0 = time.time()
    res = assemble5.compute(Lmax, verbose=False)
    print(f"# engine assemble5.compute(Lmax={Lmax}) {time.time() - t0:.1f} s; brute pmax={PMAX}, order 5 (direct)")
    bad = engine_grid_problems(res, Lmax)
    for b in bad:
        print(f"engine grid: {b}")
    if bad:
        print("FAIL (engine arrays do not have the quarter-grid shapes)")
        sys.exit(1)
    worst, wloc, nchk, ncount_bad = 0.0, None, 0, 0
    per_label = {}
    print(f"{'cut4':>4} {'dim':>8} {'worst E_p^(k)':>14} {'worst r,g,C':>12} {'worst item':>10} {'sec':>6}")
    for c in range(4, a.cut4max + 1):
        t1 = time.time()
        dim, E, r, g = run_brute(c)
        devs = compare_cutoff(res, c, E, r, g)
        if len(devs) != NPER:
            ncount_bad += 1
        nchk += len(devs)
        we, wc = 0.0, 0.0
        for i, (lab, dv) in enumerate(devs):
            if i < 16:
                we = worse(we, dv)
            else:
                wc = worse(wc, dv)
            per_label[lab] = worse(per_label.get(lab, 0.0), dv)
        lab_c, dv_c = max(devs, key=lambda t: t[1])
        if not dv_c <= worst:
            worst, wloc = dv_c, (c, lab_c)
        print(f"{c:4d} {dim:8d} {we:14.2e} {wc:12.2e} {lab_c:>10} {time.time() - t1:6.1f}", flush=True)
    for k in KS:     # worst per quantity over all cutoffs (a label never compared shows as inf)
        print(f"# k={k}: " + "  ".join(f"{lab} {per_label.get(lab, math.inf):.1e}" for lab in
                                       [f"E_{p}^({k})" for p in PS] + [f"r{k}", f"g{k}", f"C{k}"]))
    nexp = NPER * (a.cut4max - 3)
    ok = worst <= GATE and nchk == nexp and ncount_bad == 0
    where = f" at cut4={wloc[0]} ({wloc[1]})" if wloc else ""
    print(f"# {nchk} comparisons (expected {nexp} = {NPER} x {a.cut4max - 3} cutoffs), worst normalised deviation "
          f"{worst:.2e}{where} (gate {GATE:.0e}): {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
