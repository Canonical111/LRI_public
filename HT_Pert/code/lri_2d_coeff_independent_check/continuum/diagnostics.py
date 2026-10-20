#!/usr/bin/env python3
"""Calibrated consistency diagnostics for C_3..C_8 (raw and consistent).

1. Profile: for a tail family and window, the maximum residual as a function of a FIXED C_inf, normalised to the
   free-fit residual; reported are (a) the ratio at the continuum reference and (b) the C_inf interval with ratio <= 3.
2. Held-out prediction: fit L in [Lmin, 22], predict C_n(30); error relative to the actual change C_n(30) - C_n(22).
3. Effective-power fits C_inf + a L^-p + b L^-p-1 (also on C_3 as calibration).
4. Joint single-channel model at order 4 with omega_1 = 9/2 (measured exactly from C_3, asymptotics_C2_C3.py), C_inf
   free and fixed to the reference.
The same diagnostics on C_3 (L <= 30 data, exact limit known) calibrate what ratio/bias a CORRECT reference shows.
Writes diagnostics.txt.
"""
import os

import numpy as np

import fits
import reference

HERE = os.path.dirname(os.path.abspath(__file__))
REF = reference.load()
lines = []


def say(s=""):
    print(s)
    lines.append(s)


def tower(L, j1, j2):
    cols, _ = fits.tower_cols(L, j1, j2)
    return cols


def profile(L, y, j1, j2, ref):
    X = np.column_stack([np.ones_like(L)] + tower(L, j1, j2))
    coef, mr0, _ = fits.lsq(X, y)
    c0 = coef[0]

    def res(c):
        _, mr, _ = fits.lsq(np.column_stack(tower(L, j1, j2)), y - c)
        return mr / mr0

    r_ref = res(ref)
    span = max(abs(ref - c0), 0.02 * abs(ref)) * 3
    grid = np.linspace(c0 - span, c0 + span, 1201)
    ok = [c for c in grid if res(c) <= 3.0]
    return c0, r_ref, (min(ok), max(ok)) if ok else (np.nan, np.nan)


def main():
    ht = fits.load_ht()
    fams_by_n = {3: [(0, 0), (0, 1), (1, -1), (1, 0), (1, 1)],
                 4: [(1, 0), (1, 1), (2, -1), (2, 0), (2, 1)],
                 5: [(2, 0), (2, 1), (3, -1), (3, 0)],
                 6: [(3, -1), (3, 0), (2, 1)],
                 7: [(3, -1), (3, 0), (4, -1)],
                 8: [(3, -1), (3, 0), (4, -1)]}
    for n in range(3, 9):
        for scheme in (("consistent",) if n == 3 else ("consistent", "raw")):
            ser = {L: v[n] for L, v in ht[scheme].items()}
            ref = REF[n][0]
            say(f"\n== C_{n} {scheme} (reference {ref:.8g}; C_{n}(30) = {ser[30]:.8g}, reached {ser[30] / ref:.3f})")
            say(f"   {'family':12s} {'Lmin':>4s} {'C_inf(free)':>12s} {'rel.miss':>9s} {'ratio@ref':>9s}  "
                f"{'C_inf with ratio<=3':>26s} {'held-out err(30)':>16s}")
            for (j1, j2) in fams_by_n[n]:
                for Lmin in (10, 14):
                    L = np.array([x for x in sorted(ser) if Lmin <= x <= 30], float)
                    y = np.array([ser[int(x)] for x in L])
                    if len(L) < 3 + j1 + j2 + 2:
                        continue
                    c0, r_ref, (lo, hi) = profile(L, y, j1, j2, ref)
                    # held-out: fit [Lmin, 22], predict 30
                    Lh = L[L <= 22]
                    yh = y[L <= 22]
                    he = np.nan
                    if len(Lh) >= 3 + j1 + j2 + 1:
                        X = np.column_stack([np.ones_like(Lh)] + tower(Lh, j1, j2))
                        coef, _, _ = fits.lsq(X, yh)
                        pred = np.concatenate([[1.0], [c[0] for c in [np.atleast_1d(t) for t in tower(np.array([30.0]), j1, j2)]]]) @ coef
                        he = (pred - ser[30]) / (ser[30] - ser[22])
                    say(f"   tower({j1},{j2}) {Lmin:4d} {c0:12.6g} {(c0 - ref) / abs(ref):+9.2%} {r_ref:9.1f}  "
                        f"[{lo:11.6g}, {hi:11.6g}] {he:+16.2%}")
            Lp = np.array([x for x in sorted(ser) if 14 <= x <= 30], float)
            yp = np.array([ser[int(x)] for x in Lp])
            c, p, mr = fits.fit_power(Lp, yp, extra=True)
            say(f"   power C+aL^-p+bL^-p-1 (L 14-30): C_inf {c:.6g} ({(c - ref) / abs(ref):+.2%}), p = {p:.3f}")

    # joint single-channel model at order 4 with omega_1 = 9/2
    say("\n== joint single-channel model at order 4, omega_1 = 9/2, omega_2 free")
    T2 = {L: v[2] - REF[2][0] for L, v in ht["consistent"].items()}
    T3 = {L: v[3] - REF[3][0] for L, v in ht["consistent"].items()}
    for scheme in ("consistent", "raw"):
        for Rcols in (("1/L2",), ("1/L2", "l/L2")):
            for Lmin in (10, 12, 14, 16):
                L = np.array([x for x in sorted(ht[scheme]) if Lmin <= x <= 30], float)
                l = np.log(L)
                t2 = np.array([T2[int(x)] for x in L])
                t3 = np.array([T3[int(x)] for x in L])
                y = np.array([ht[scheme][int(x)][4] for x in L]) + 4.5 * l * t3 + 0.5 * 4.5 ** 2 * l ** 2 * t2
                tail = [1 / L, l * t2] + ([1 / L ** 2] if "1/L2" in Rcols else []) + ([l / L ** 2] if "l/L2" in Rcols else [])
                coef, mr, _ = fits.lsq(np.column_stack([np.ones_like(L)] + tail), y)
                _, mrf, _ = fits.lsq(np.column_stack(tail), y - REF[4][0])
                say(f"   {scheme:10s} R={'+'.join(Rcols):9s} Lmin {Lmin:2d}: C4inf {coef[0]:.4f} "
                    f"({(coef[0] - REF[4][0]) / REF[4][0]:+.2%}), omega_2 {-coef[2]:+.1f}, ratio@ref {mrf / mr:.1f}")
    with open(os.path.join(HERE, "diagnostics.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
