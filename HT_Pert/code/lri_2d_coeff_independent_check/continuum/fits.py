#!/usr/bin/env python3
"""Cutoff extrapolation of the 2D HT coefficients C_n(L), n = 3..8, raw and consistent schemes.

Fit families (all linear least squares in the coefficients, columns scaled to unit norm, float64 QR):
  tower(j1, j2): C_inf + sum_{j<=j1} a_j l^j / L + sum_{j<=j2} b_j l^j / L^2,   l = log L.
      This is the structure of the exact C_2(L) (j1 = 0, power series in 1/L) and of the exact C_3(L)
      (j1 = 1, j2 = 1 or 2; exact_low_orders.py) -- the expected tail at order n is l^{<= n-2}/L + l^{..}/L^2.
  fixed:  the same towers with C_inf fixed to the continuum reference (one parameter fewer); the ratio of its
      maximum residual to the free fit's tells whether the reference is compatible with the tail family.
  power:  C_inf + a L^{-p} (+ b L^{-p-1}), p free (nonlinear, scanned): an effective-exponent diagnostic.
  joint:  single leading L^{-1} channel (as in the 1D joint model): Y_n = C_n(L) + sum_j e_j(l) T_{n-j}(L)
      with T_k = C_k(L) - C_k(inf) and e_j = [eps^j] exp(l sum_k omega_k eps^k); used for n = 4 with the exact T_2,
      T_3, omega_1 fixed (3.5 = phi^6 one-loop value; 4.5 = value measured from the exact C_3 tail) and omega_2 free.
Windows: L_min <= L <= L_max with L_max = 30 (and 28, 26 for stability), L_min = 6..20.
Calibration: every family is also applied to C_3 restricted to L <= 30 (whose exact limit is known), and to the
exact C_3(L) of exact_low_orders.py on wider windows.

Writes fits_all.csv (every fit) and prints the summary tables used in REPORT.md.
"""
import csv
import itertools
import math
import os

import numpy as np

import reference

HERE = os.path.dirname(os.path.abspath(__file__))
REF = reference.load()


def load_ht():
    data = {}
    with open(os.path.join(HERE, "ht_coefficients.csv")) as fh:
        for r in csv.DictReader(fh):
            data.setdefault(r["scheme"], {})[int(r["L"])] = [float(r[f"C{n}"]) for n in range(9)]
    return data


def load_exact():
    out = {}
    path = os.path.join(HERE, "exact_C2_C3.csv")
    if os.path.exists(path):
        with open(path) as fh:
            for r in csv.DictReader(fh):
                out[int(r["L"])] = (float(r["C2"]), float(r["C3"]))
    return out


def lsq(X, y):
    s = np.linalg.norm(X, axis=0)
    s[s == 0] = 1.0
    Xs = X / s
    coef, *_ = np.linalg.lstsq(Xs, y, rcond=None)
    sv = np.linalg.svd(Xs, compute_uv=False)
    cond = sv[0] / sv[-1] if sv[-1] > 0 else np.inf
    coef = coef / s
    res = y - X @ coef
    return coef, float(np.max(np.abs(res))), float(cond)


def tower_cols(L, j1, j2):
    l = np.log(L)
    cols, names = [], []
    for j in range(j1 + 1):
        cols.append(l ** j / L)
        names.append(f"l{j}/L")
    for j in range(j2 + 1):
        cols.append(l ** j / L ** 2)
        names.append(f"l{j}/L2")
    return cols, names


def fit_tower(L, y, j1, j2, cinf=None):
    cols, names = tower_cols(L, j1, j2)
    if cinf is None:
        X = np.column_stack([np.ones_like(L)] + cols)
        coef, mr, cond = lsq(X, y)
        return coef[0], coef[1:], mr, cond
    X = np.column_stack(cols)
    coef, mr, cond = lsq(X, y - cinf)
    return cinf, coef, mr, cond


def fit_power(L, y, extra=False):
    best = None
    for p in np.linspace(0.05, 3.0, 591):
        cols = [np.ones_like(L), L ** -p] + ([L ** (-p - 1)] if extra else [])
        coef, mr, cond = lsq(np.column_stack(cols), y)
        if best is None or mr < best[2]:
            best = (coef[0], p, mr)
    # refine
    c0, p0, _ = best
    for p in np.linspace(p0 - 0.005, p0 + 0.005, 101):
        cols = [np.ones_like(L), L ** -p] + ([L ** (-p - 1)] if extra else [])
        coef, mr, cond = lsq(np.column_stack(cols), y)
        if mr < best[2]:
            best = (coef[0], p, mr)
    return best


def towers_for(n):
    """Tail families used at order n (the expected maximal log power at 1/L is n-2)."""
    fams = []
    jmax = max(1, n - 2)
    for j1 in range(0, jmax + 1):
        for j2 in range(-1, jmax + 1):
            fams.append((j1, j2))
    return fams


def run_free_and_fixed(series, n, scheme, label, Lmax_list=(30, 28, 26), Lmin_list=range(6, 22, 2)):
    rows = []
    for Lmax in Lmax_list:
        for Lmin in Lmin_list:
            Ls = np.array([L for L in sorted(series) if Lmin <= L <= Lmax], float)
            y = np.array([series[int(L)] for L in Ls])
            for (j1, j2) in towers_for(n):
                npar = 1 + (j1 + 1) + (j2 + 1)
                if len(Ls) < npar + 2:
                    continue
                cinf, coef, mr, cond = fit_tower(Ls, y, j1, j2)
                _, _, mr_fix, _ = fit_tower(Ls, y, j1, j2, cinf=REF[n][0])
                rows.append(dict(label=label, scheme=scheme, n=n, model=f"tower({j1},{j2})", Lmin=Lmin, Lmax=Lmax,
                                 npts=len(Ls), npar=npar, Cinf=cinf, ref=REF[n][0], miss=cinf - REF[n][0],
                                 relmiss=(cinf - REF[n][0]) / abs(REF[n][0]), maxres=mr, maxres_fixed=mr_fix,
                                 cond=cond, coefs=" ".join(f"{c:.6g}" for c in coef)))
    return rows


def summarize(rows, n, title, min_dof=2):
    """Median / range of C_inf over fits that have >= min_dof residual dof, by model."""
    print(f"\n== {title}: C_{n}, reference {REF[n][0]:.10g}")
    by = {}
    for r in rows:
        if r["npts"] - r["npar"] < min_dof:
            continue
        by.setdefault(r["model"], []).append(r)
    allv = []
    for m in sorted(by):
        v = np.array([r["Cinf"] for r in by[m] if r["Lmax"] == 30])
        if len(v) == 0:
            continue
        allv.extend(v)
        lmin16 = [r for r in by[m] if r["Lmax"] == 30 and r["Lmin"] == 16]
        s16 = (f"Lmin16: {lmin16[0]['Cinf']:.6g} (res {lmin16[0]['maxres']:.1e}, fixed/free "
               f"{lmin16[0]['maxres_fixed'] / max(lmin16[0]['maxres'], 1e-300):.1f})") if lmin16 else ""
        print(f"  {m:12s} Lmax30: median {np.median(v):.6g}  range [{v.min():.6g}, {v.max():.6g}]  "
              f"rel.miss(median) {(np.median(v) - REF[n][0]) / abs(REF[n][0]):+.3%}   {s16}")
    allv = np.array(allv)
    if len(allv):
        print(f"  ALL towers Lmax30: median {np.median(allv):.6g}, 10-90% [{np.percentile(allv, 10):.6g}, "
              f"{np.percentile(allv, 90):.6g}], rel.miss(median) {(np.median(allv) - REF[n][0]) / abs(REF[n][0]):+.3%}")
    return allv


def joint4(series4, T2, T3, omega1, Lmin, Lmax=30, sub=("l0/L2", "l1/L2")):
    """Y_4 = C_4 + omega1 l T_3 + (omega1^2 l^2/2) T_2 = C4inf + a/L - omega2 l T_2 + R."""
    Ls = np.array([L for L in sorted(series4) if Lmin <= L <= Lmax], float)
    l = np.log(Ls)
    t2 = np.array([T2[int(L)] for L in Ls])
    t3 = np.array([T3[int(L)] for L in Ls])
    y = np.array([series4[int(L)] for L in Ls]) + omega1 * l * t3 + 0.5 * omega1 ** 2 * l ** 2 * t2
    cols = [np.ones_like(Ls), 1 / Ls, l * t2]
    if "l0/L2" in sub:
        cols.append(1 / Ls ** 2)
    if "l1/L2" in sub:
        cols.append(l / Ls ** 2)
    if "l2/L2" in sub:
        cols.append(l ** 2 / Ls ** 2)
    coef, mr, cond = lsq(np.column_stack(cols), y)
    return coef[0], -coef[2], mr, len(Ls), len(cols)


def main():
    ht = load_ht()
    exact = load_exact()
    allrows = []

    # ---------------- calibration on C_3 (exact limit known) ----------------
    c3 = {L: v[3] for L, v in ht["consistent"].items()}
    rows = run_free_and_fixed(c3, 3, "both", "C3 data L<=30")
    allrows += rows
    summarize(rows, 3, "CALIBRATION, HT data L<=30")
    if exact:
        ex3 = {L: v[1] for L, v in exact.items()}
        for Lmax in (60, 120, 256, 600):
            rr = []
            for Lmin in (16, 24, 32, 48, 64):
                if Lmin >= Lmax / 2:
                    continue
                Ls = np.array([L for L in sorted(ex3) if Lmin <= L <= Lmax], float)
                y = np.array([ex3[int(L)] for L in Ls])
                for (j1, j2) in [(1, -1), (1, 0), (1, 1), (1, 2)]:
                    if len(Ls) < 4 + j1 + j2 + 1:
                        continue
                    cinf, coef, mr, cond = fit_tower(Ls, y, j1, j2)
                    rr.append(cinf)
                    allrows.append(dict(label=f"C3 exact L<={Lmax}", scheme="exact", n=3, model=f"tower({j1},{j2})",
                                        Lmin=Lmin, Lmax=Lmax, npts=len(Ls), npar=2 + j1 + j2 + 1, Cinf=cinf,
                                        ref=REF[3][0], miss=cinf - REF[3][0], relmiss=(cinf - REF[3][0]) / abs(REF[3][0]),
                                        maxres=mr, maxres_fixed=float("nan"), cond=cond,
                                        coefs=" ".join(f"{c:.6g}" for c in coef)))
            rr = np.array(rr)
            print(f"  exact C3, L<={Lmax}: towers (1,-1..2): range [{rr.min():.8f}, {rr.max():.8f}], "
                  f"max |miss| {np.max(np.abs(rr - REF[3][0])):.2e}")

    # ---------------- orders 4..8, both schemes ----------------
    for scheme in ("consistent", "raw"):
        for n in range(4, 9):
            series = {L: v[n] for L, v in ht[scheme].items()}
            rows = run_free_and_fixed(series, n, scheme, f"C{n} {scheme}")
            allrows += rows
            summarize(rows, n, f"{scheme}")
            for extra in (False, True):
                Ls = np.array([L for L in sorted(series) if 14 <= L <= 30], float)
                y = np.array([series[int(L)] for L in Ls])
                c, p, mr = fit_power(Ls, y, extra)
                print(f"  power{'+1' if extra else ''} (L 14-30): Cinf {c:.6g}, p {p:.3f}, maxres {mr:.1e}, "
                      f"rel.miss {(c - REF[n][0]) / abs(REF[n][0]):+.2%}")

    # ---------------- joint single-channel model at order 4 ----------------
    T2 = {L: v[2] - REF[2][0] for L, v in ht["consistent"].items()}
    T3 = {L: v[3] - REF[3][0] for L, v in ht["consistent"].items()}
    print("\n== joint single-channel model, order 4 (omega_2 free)")
    for scheme in ("consistent", "raw"):
        s4 = {L: v[4] for L, v in ht[scheme].items()}
        for om1 in (3.5, 4.5):
            for sub in (("l0/L2",), ("l0/L2", "l1/L2"), ("l0/L2", "l1/L2", "l2/L2")):
                vals = []
                for Lmin in range(8, 20, 2):
                    c4, om2, mr, npts, npar = joint4(s4, T2, T3, om1, Lmin, sub=sub)
                    vals.append((Lmin, c4, om2, mr))
                    allrows.append(dict(label="joint4", scheme=scheme, n=4, model=f"joint(om1={om1},{'+'.join(sub)})",
                                        Lmin=Lmin, Lmax=30, npts=npts, npar=npar, Cinf=c4, ref=REF[4][0],
                                        miss=c4 - REF[4][0], relmiss=(c4 - REF[4][0]) / abs(REF[4][0]), maxres=mr,
                                        maxres_fixed=float("nan"), cond=float("nan"), coefs=f"omega2={om2:.6g}"))
                txt = "  ".join(f"{Lmin}:{c4:.4f}(w2 {om2:.1f})" for Lmin, c4, om2, mr in vals)
                print(f"  {scheme:10s} om1={om1} R={'+'.join(sub):18s} {txt}")

    fields = ["label", "scheme", "n", "model", "Lmin", "Lmax", "npts", "npar", "Cinf", "ref", "miss", "relmiss",
              "maxres", "maxres_fixed", "cond", "coefs"]
    with open(os.path.join(HERE, "fits_all.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in allrows:
            w.writerow({k: (repr(v) if isinstance(v, float) else v) for k, v in r.items()})
    print(f"\nwrote fits_all.csv ({len(allrows)} fits)")


if __name__ == "__main__":
    main()
