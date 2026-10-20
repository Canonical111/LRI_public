#!/usr/bin/env python3
"""Spectator (zero-mode-linked) window shifts of C_4 that the 'consistent' scheme does not correct.

Mechanism.  An intermediate state s = |p'> (x) |chi_s> at level N_s in the cutoff-L space can host second-order
bubbles attached to its zero modes only up to level L - N_s, while the counterterms r, g are tuned on the
level-0 references (bubbles up to L).  The 'consistent' D_L(N) = E_v(L) - E_v(L-N) restores the p'-INDEPENDENT
(vacuum) part of this deficit.  The p'-dependent part, at order eps^2,
    D'(p', N) = g1^2 [ e~_{p'}(L) - e~_{p'}(L - N) ],   e~_{p'}(l) = <p'|V R V|p'>_l - <0|V R V|0>_l,
is left in place.  In 2D the mass-type (three-chi-line) bubble has a CONSTANT density per level (the mass
divergence is linear, r_2 ~ 0.0236 L), so D' ~ sigma_1 p' N does not decay with L.  (In 1D this density decays like
level^{-1/2}, which is why the 1D Dconn correction was complete.)

This script evaluates, exactly, the shift that a zero-mode-dependent window correction would add at eps^4:
    dC_4^{zm}(L) = Pi[ g1^2 sum_s |<s|V|p>|^2 D'(p'_s, N_s) / den_s^2 ]
(the same structure as the exactly verified raw->consistent shift Delta C_4, with D_2 replaced by D'), and its
decomposition by the number m of chi particles in s.  It is a diagnostic of the regulator, not a claim about
which correction is the right one; see REPORT.md Sec. 6.
Writes zero_mode_window.csv.
"""
import csv
import math
import os

import numpy as np

import exact_low_orders as ex

HERE = os.path.dirname(os.path.abspath(__file__))
G1 = 1.0 / 3.0


def second_order_all_cutoffs(c, Lmax, pmax=8):
    """e[p][l] = <p|V R V|p> at cutoff l (l = 0..Lmax), split by chi-number m (e_m[p][m][l])."""
    lv = np.arange(Lmax + 1)
    e_m = np.zeros((pmax + 1, 5, Lmax + 1))
    for p in range(pmax + 1):
        for m in range(0, 5):
            Z = ex.zop("V", m)
            for p1 in range(ex.NZ):
                amp2 = Z[p1, p] ** 2
                if amp2 == 0.0:
                    continue
                if m == 0:
                    if p1 == p:
                        continue
                    e_m[p, 0, :] += -amp2 * c[0][0] / ((p1 - p) / 2.0)
                    continue
                den = (p1 - p) / 2.0 + m / 2.0 + lv
                term = np.zeros(Lmax + 1)
                mask = c[m] != 0
                term[mask] = -math.factorial(m) * amp2 * c[m][mask] / den[mask]
                e_m[p, m, :] += np.cumsum(term)
    return e_m


def main():
    out = []
    Ls = [30, 60, 100, 200, 400, 800, 1200, 1600]
    print(" L      dC4zm(total)    m=1          m=2          m=3        | Delta C4 (vacuum window, for scale)")
    for L in Ls:
        W, dW = ex.weights(L)
        c, dc, c1J = ex.bundles(L, W, dW)
        e_m = second_order_all_cutoffs(c, L)
        e = e_m.sum(axis=1)  # e[p][l]
        etil = e - e[0][None, :]
        lv = np.arange(L + 1)
        parts = {}
        for mm in (1, 2, 3, 4):
            Ep = {}
            for p in range(4):
                Z = ex.zop("V", mm)
                tot = 0.0
                for p1 in range(ex.NZ):
                    amp2 = Z[p1, p] ** 2
                    if amp2 == 0.0:
                        continue
                    den = (p1 - p) / 2.0 + mm / 2.0 + lv
                    Dp = G1 ** 2 * (etil[p1, L] - etil[p1, L - lv])  # D'(p', N) for N = 0..L
                    mask = c[mm] != 0
                    tot += math.factorial(mm) * amp2 * math.fsum(c[mm][mask] * Dp[mask] / den[mask] ** 2)
                Ep[p] = G1 ** 2 * tot
            parts[mm] = ex.Pi(Ep)
        # vacuum window (consistent - raw) for scale, same formula with D_2 = E_v(L) - E_v(L-N)
        Ep = {}
        for p in range(4):
            tot = 0.0
            for mm in (1, 2, 3, 4):
                Z = ex.zop("V", mm)
                for p1 in range(ex.NZ):
                    amp2 = Z[p1, p] ** 2
                    if amp2 == 0.0:
                        continue
                    den = (p1 - p) / 2.0 + mm / 2.0 + lv
                    Dv = G1 ** 2 * (e[0, L] - e[0, L - lv])
                    mask = c[mm] != 0
                    tot += math.factorial(mm) * amp2 * math.fsum(c[mm][mask] * Dv[mask] / den[mask] ** 2)
            Ep[p] = G1 ** 2 * tot
        dvac = ex.Pi(Ep)
        total = sum(parts.values())
        print(f"{L:4d}  {total:+.8f}  {parts[1]:+.8f}  {parts[2]:+.8f}  {parts[3]:+.8f}  (m=4 {parts[4]:+.1e}) | {dvac:+.8f}")
        out.append(dict(L=L, dC4_zm=total, m1=parts[1], m2=parts[2], m3=parts[3], m4=parts[4], dC4_vacuum=dvac,
                        r2_slope_check=G1 ** 2 * (etil[1, L] - etil[1, L - 2]) / 2))
    with open(os.path.join(HERE, "zero_mode_window.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)


if __name__ == "__main__":
    main()
