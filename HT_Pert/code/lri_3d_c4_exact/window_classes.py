#!/usr/bin/env python3
"""Class-resolved large-L forms of the exact window shifts (L <= 8000) and of r2(L); analytic identifications.
Output: fits/window_classes.txt"""
import math
import os

import numpy as np

import fitlib3d as F

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "results")
G72 = math.gamma(3.5)                       # Gamma(7/2) = 15 sqrt(pi)/8


def main():
    out = []
    P = lambda s="": (out.append(s), print(s))
    w = np.load(os.path.join(R, "windows_L8000.npz"))
    o = np.load(os.path.join(R, "offdiag_L8000.npz"))
    L = o["L"].astype(float)
    sub = F.tower([-0.5, -1, -1.5], {-0.5: 1, -1: 1})
    base = ["l1*L^0.5", "L^0.5", "l1*L^0", "1"] + sub                       # sunset-type classes
    lin = ["L^1", "l1*L^0.5", "L^0.5", "l1*L^0", "1"] + sub                 # 4 chi x 1-line bubble; Delta_zm
    vac = ["L^2", "L^1", "L^0.5", "l1*L^0", "1"] + F.tower([-0.5, -1, -1.5, -2])     # vacuum class
    pick = lambda k: vac if k in ("diag_m1_m4", "Delta_cons") else (lin if k in ("diag_m4_m1", "Delta_zm") else base)
    P("# C4 shift of each window class (outer chi lines m x inner bubble lines m'), fit 1600 <= L <= 8000")
    P("# columns: value at L = 8000, then coefficients of L^2, L, sqrt(L) ln L, sqrt(L), ln L, 1; max residual")
    P(f"{'class':14s} {'C4 shift(8000)':>15s} {'L^2':>11s} {'L':>11s} {'sqrtL lnL':>12s} {'sqrtL':>11s} "
      f"{'lnL':>10s} {'const':>10s} {'res':>6s}")
    for kind in ("diag", "off"):
        for m in range(1, 5):
            for m2 in range(1, 5):
                k = f"{kind}_m{m}_m{m2}"
                if k not in o or np.max(np.abs(o[k])) < 1e-12:
                    continue
                c, res, _ = F.fit(L, o[k], pick(k), 1600)
                for x in ("L^2", "L^1", "l1*L^0.5"):
                    c.setdefault(x, 0.0)
                P(f"{k:14s} {o[k][-1]:+15.6e} {c['L^2']:+11.4e} {c['L^1']:+11.4e} {c['l1*L^0.5']:+12.5e} "
                  f"{c['L^0.5']:+11.4e} {c['l1*L^0']:+10.2e} {c['1']:+10.2e} {res:6.0e}")
    P("\n# totals")
    for nm, y in (("Delta_cons", w["Dcons"]), ("Delta_zm", w["Dzm"]), ("Delta_off", o["off"])):
        c, res, _ = F.fit(L, y, pick(nm), 1600)
        for x in ("L^2", "L^1", "l1*L^0.5"):
            c.setdefault(x, 0.0)
        P(f"{nm:14s} {y[-1]:+15.6e} {c['L^2']:+11.6e} {c['L^1']:+11.6e} {c['l1*L^0.5']:+12.7e} {c['L^0.5']:+11.4e} "
          f"{c['l1*L^0']:+10.2e} {c['1']:+10.2e} {res:6.0e}")
    P("\n# analytic identifications (Sec. 5 of README)")
    P(f"  sqrt(L) ln L, Delta z = 0  (2 chi x zero-mode sunset): 6/(243 Gamma(7/2)) = {6 / (243 * G72):.10f}")
    P(f"  sqrt(L) ln L, Delta z = +-2 (2 chi x zero-mode sunset): 4/(243 Gamma(7/2)) = {4 / (243 * G72):.10f}")
    P(f"  sum = 10/(243 Gamma(7/2)) = 16/(729 sqrt(pi)) = {10 / (243 * G72):.10f}")
    d = np.load(os.path.join(R, "dchi_L1000.npz"))
    Ld = d["L"].astype(float)
    c, res, _ = F.fit(Ld, d["r2"], ["L^1.5", "L^1", "L^0.5", "l1*L^0", "1"] + F.tower([-0.5, -1]), 200, Lmax=980)
    P(f"  r2(L) = {c['L^1.5']:.10f} L^(3/2) + {c['L^0.5']:.6f} L^(1/2) + ... (L coefficient {c['L^1']:+.1e}); "
      f"6/(243 Gamma(7/2)) = {6 / (243 * G72):.10f}")
    c, res, _ = F.fit(Ld, d["dC4chi"], ["L^0.5", "l1*L^0", "1"] + F.tower([-0.5, -1]), 300, Lmax=980)
    P(f"  leading-order chi window: C4 shift = {c['L^0.5']:.6e} sqrt(L) + {c['1']:+.2e} + ... (ln L {c['l1*L^0']:+.1e})")
    os.makedirs(os.path.join(HERE, "fits"), exist_ok=True)
    with open(os.path.join(HERE, "fits", "window_classes.txt"), "w") as f:
        f.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
