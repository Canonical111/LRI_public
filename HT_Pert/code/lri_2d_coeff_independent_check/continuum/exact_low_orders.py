#!/usr/bin/env python3
"""Exact finite-cutoff C_2(L), C_3(L) of the 2D LRI Hamiltonian truncation (SPEC.md), derived independently.

Derivation (written for this check; no solver code was read):
  * Fock space = zero mode (0,0) (oscillator a, Z = a + a^dagger, weight w_00 = 1 at every eps) times the nonzero
    modes chi (weights w_ab = (x)_a (x)_b / (a! b!), x = 1/2 - eps/4).  :phi^4: = sum_m C(4,m) :Z^{4-m}: :chi^m:, so
    V = sum_m [C(4,m)/12] :Z^{4-m}: (x) X_m and M = sum_m C(2,m) :Z^{2-m}: (x) X_m with X_m = < :chi^m: >_theta.
  * Rayleigh-Schroedinger with R = Q_p/(E0_p - H0), H0 = N + P/2, H = H0 + eps H1 + eps^2 H2 + ...:
      H1 = -P/4 + g1 V,  H2 = r2 M + g2 V + g1 V',  (r1 = 0, g1 = 1/3; V' = dV/deps through w_ab only)
      E2_p = 2p r2 + g2 p(p-1)/2 + g1^2 <V R V>
      E3_p = [r3, g3 terms] + 2 g1 r2 <V R M> + 2 g1 g2 <V R V> + 2 g1^2 <V R V'>
             + g1^3 (<V R V R V> - V_pp <V R^2 V>) - (g1^2/4) <V R (P - p) R V>.
  * Tuning E_1 - E_0 = x, E_3 - E_0 = 2 - x order by order; the observable is
      C_n = Pi[E_n],  Pi[f] = f(2) - f(1) - (f(3) - f(0))/3   (n >= 2),
    because the r_n, g_n terms (2p r_n + p(p-1)/2 g_n) and the targets are polynomials of degree <= 2 in p,
    which Pi annihilates.  Every chi-sector matrix element is evaluated by Wick contraction of the normal-ordered
    vertices: lines between vertices i<j carry sum_mode w_mode, theta averages impose J conservation at each
    vertex, and each energy denominator depends on the zero-mode number and the lines crossing that time slice.
    The level cutoff N <= L acts on every intermediate state (zero modes have level 0).
  * Pi kills every term whose zero-mode polynomial degree in p is <= 2; for C_3 only diagrams with at most three
    chi lines survive (the code nevertheless keeps all two-vertex bundles m <= 4 in the tuning pieces).

Usage:  python3 exact_low_orders.py [--check] [--L 2,4,...] [--out exact_C2_C3.csv]
"""
import argparse
import csv
import math
import os
import sys
from math import comb, factorial

import numpy as np
from scipy.signal import fftconvolve
from scipy.special import digamma, gammaln

HERE = os.path.dirname(os.path.abspath(__file__))
G1 = 1.0 / 3.0
NZ = 24  # zero-mode Fock truncation (exact: p <= 3 plus at most three vertices)


# ----------------------------------------------------------------------------- zero mode
def zero_mode_ops():
    a = np.zeros((NZ, NZ))
    for n in range(1, NZ):
        a[n - 1, n] = math.sqrt(n)
    ad = a.T.copy()
    ops = {}
    for k in range(0, 5):
        op = np.zeros((NZ, NZ))
        for j in range(k + 1):
            op += comb(k, j) * np.linalg.matrix_power(ad, j) @ np.linalg.matrix_power(a, k - j)
        ops[k] = op
    return ops


ZOP = zero_mode_ops()


def zop(kind, m):
    """Zero-mode operator (with coefficient) of vertex `kind` carrying m chi legs."""
    if kind == "V":
        return (comb(4, m) / 12.0) * ZOP[4 - m] if m <= 4 else None
    if kind == "M":
        return (comb(2, m) * 1.0) * ZOP[2 - m] if m <= 2 else None
    raise ValueError(kind)


# ----------------------------------------------------------------------------- chi weights
def weights(L, x=0.5):
    """w[a,b] and dw/deps[a,b] for a+b <= L (x = 1/2 - eps/4, so d/deps = -(1/4) d/dx)."""
    a = np.arange(L + 1)
    lw = gammaln(x + a) - gammaln(x) - gammaln(a + 1.0)
    w1 = np.exp(lw)
    dlw = digamma(x + a) - digamma(x)
    W = np.outer(w1, w1)
    dW = -0.25 * W * (dlw[:, None] + dlw[None, :])
    lev = a[:, None] + a[None, :]
    W[lev > L] = 0.0
    dW[lev > L] = 0.0
    W[0, 0] = 0.0  # zero mode excluded from chi
    dW[0, 0] = 0.0
    return W, dW


def level_J_array(W, L):
    """c1[l, J+L] = sum over single nonzero modes with level l and angular momentum J."""
    c1 = np.zeros((L + 1, 2 * L + 1))
    for a in range(L + 1):
        for b in range(L + 1 - a):
            c1[a + b, a - b + L] += W[a, b]
    return c1


def bundles(L, W, dW):
    """J=0 bundle weights c_n(l) = [q^l z^0](W-1)^n, n = 0..4, and (1/2) d/deps c_n(l), n = 1..4."""
    c1 = level_J_array(W, L)
    d1 = level_J_array(dW, L)
    powers = {1: c1}
    dpowers = {1: d1}
    for n in range(2, 5):
        full = fftconvolve(powers[n - 1], c1)  # shape (2L+1, 4L+1) etc.
        # level index 0..L, J offset: powers[n-1] has J offset L, c1 has J offset L -> full offset 2L
        trimmed = full[: L + 1, L: 3 * L + 1]
        dfull = fftconvolve(dpowers[n - 1], c1) + fftconvolve(powers[n - 1], d1)
        powers[n] = trimmed
        dpowers[n] = dfull[: L + 1, L: 3 * L + 1]
    c = {0: np.eye(1, L + 1, 0).ravel()}
    dc = {0: np.zeros(L + 1)}
    for n in range(1, 5):
        c[n] = powers[n][:, L].copy()
        dc[n] = 0.5 * dpowers[n][:, L].copy()  # derivative acting on one vertex: sqrt(w) d sqrt(w) = dw/2
    # fft round-off cleanup: c_n(l) = 0 for l < n
    for n in range(1, 5):
        c[n][:n] = 0.0
        dc[n][:n] = 0.0
    return c, dc, c1


# ----------------------------------------------------------------------------- two-vertex pieces
def two_vertex(p, kind_left, kind_right, c, L, power, weight_pm=False, mlist=range(0, 5)):
    """sum_m m! sum_{p1} <p|Zl|p1><p1|Zr|p> sum_l c_m(l) f(den)  with  den = (p1-p)/2 + m/2 + l,
    f = den^-power (times (p1 - p + m) if weight_pm).  The intermediate state |p> (m=0, p1=p) is excluded."""
    tot = 0.0
    lv = np.arange(L + 1)
    for m in mlist:
        Zl = zop(kind_left, m)
        Zr = zop(kind_right, m)
        if Zl is None or Zr is None:
            continue
        cm = c[m] if isinstance(c, dict) else c(m)
        for p1 in range(NZ):
            amp = Zl[p, p1] * Zr[p1, p]
            if amp == 0.0:
                continue
            if m == 0:
                if p1 == p:
                    continue
                den = (p1 - p) / 2.0
                val = cm[0] / den ** power
                if weight_pm:
                    val *= (p1 - p)
            else:
                den = (p1 - p) / 2.0 + m / 2.0 + lv
                mask = cm != 0.0
                f = np.zeros(L + 1)
                f[mask] = cm[mask] / den[mask] ** power
                if weight_pm:
                    f *= (p1 - p + m)
                val = math.fsum(f)
            tot += factorial(m) * amp * val
    return tot


# ----------------------------------------------------------------------------- three-vertex piece
def three_vertex(p, c, c1J, L, max_lines=3):
    """<p| V R V R V |p> restricted to chi patterns with at most `max_lines` lines (exact modulo terms of degree
    <= 2 in p when max_lines = 3)."""
    total = 0.0
    lv = np.arange(L + 1)
    for n12 in range(0, max_lines + 1):
        for n13 in range(0, max_lines + 1 - n12):
            for n23 in range(0, max_lines + 1 - n12 - n13):
                m1, m2, m3 = n12 + n13, n12 + n23, n13 + n23
                if max(m1, m2, m3) > 4:
                    continue
                Z1, Z2, Z3 = zop("V", m1), zop("V", m2), zop("V", m3)
                combf = comb(m2, n23) * factorial(m1) // factorial(n13) * factorial(m3)
                ns1, ns2 = n12 + n13, n13 + n23  # chi lines in slices 1 and 2
                triangle = n12 > 0 and n13 > 0 and n23 > 0
                for p1 in range(NZ):
                    a1 = Z1[p1, p]
                    if a1 == 0.0:
                        continue
                    if ns1 == 0 and p1 == p:
                        continue
                    for p2 in range(NZ):
                        a2 = Z2[p2, p1]
                        if a2 == 0.0:
                            continue
                        if ns2 == 0 and p2 == p:
                            continue
                        a3 = Z3[p, p2]
                        if a3 == 0.0:
                            continue
                        amp = a1 * a2 * a3 * combf
                        al1 = (p1 - p) / 2.0 + ns1 / 2.0
                        al2 = (p2 - p) / 2.0 + ns2 / 2.0
                        if triangle:
                            S = triangle_sum(c1J, L, al1, al2)
                        else:
                            S = bundle_sum(c[n12], c[n13], c[n23], L, al1, al2)
                        total += amp * S
    return total


def bundle_sum(c12, c13, c23, L, al1, al2):
    """sum_{l12,l13,l23} c12 c13 c23 / ((al1 + l12 + l13)(al2 + l13 + l23)), l12+l13 <= L, l13+l23 <= L."""
    lv = np.arange(L + 1)
    s = lv[:, None]
    t = lv[None, :]
    valid = (s + t) <= L
    d1 = al1 + s + t
    d2 = al2 + s + t
    with np.errstate(divide="ignore", invalid="ignore"):
        K1 = np.where(valid, c12[None, :] / d1, 0.0)
        K2 = np.where(valid, c23[None, :] / d2, 0.0)
    K1[~np.isfinite(K1)] = 0.0
    K2[~np.isfinite(K2)] = 0.0
    # guard: a zero denominator with nonzero weight would be a degeneracy
    bad = valid & ((d1 == 0) & (c12[None, :] != 0) | (d2 == 0) & (c23[None, :] != 0))
    bad &= (c13[:, None] != 0)
    if bad.any():
        raise RuntimeError("zero energy denominator")
    A = K1.sum(axis=1)
    B = K2.sum(axis=1)
    return math.fsum(c13 * A * B)


def triangle_sum(c1J, L, al1, al2):
    """sum_J sum_{l12,l13,l23} w(l12,J) w(l13,-J) w(l23,J) / ((al1+l12+l13)(al2+l13+l23))."""
    lv = np.arange(L + 1)
    s = lv[:, None]
    t = lv[None, :]
    valid = (s + t) <= L
    # single lines have level >= 1, so s = 0 or t = 0 rows/columns carry zero weight; mask them before inverting
    live = valid & (s >= 1) & (t >= 1)
    d1 = al1 + s + t
    d2 = al2 + s + t
    if (live & ((d1 == 0) | (d2 == 0))).any():
        raise RuntimeError("zero energy denominator in triangle")
    inv1 = np.zeros_like(d1, dtype=float)
    inv2 = np.zeros_like(d2, dtype=float)
    inv1[live] = 1.0 / d1[live]
    inv2[live] = 1.0 / d2[live]
    A = inv1 @ c1J  # A[s, J] = sum_t w(t,J)/(al1+s+t)
    B = inv2 @ c1J
    wm = c1J[:, ::-1]  # w(s, -J)
    return math.fsum((wm * A * B).sum(axis=0))


# ----------------------------------------------------------------------------- assembly
def Pi(f):
    return f[2] - f[1] - (f[3] - f[0]) / 3.0


def compute(L):
    W, dW = weights(L)
    c, dc, c1J = bundles(L, W, dW)
    e = {p: two_vertex(p, "V", "V", c, L, 1) * -1.0 for p in range(4)}  # <V R V> (R = -1/den)
    C2 = G1 ** 2 * Pi(e)
    r2 = -G1 ** 2 * (e[1] - e[0]) / 2.0
    g2 = G1 ** 2 * ((e[1] - e[0]) - (e[3] - e[0]) / 3.0)
    E3 = {}
    for p in range(4):
        VRM = -two_vertex(p, "V", "M", c, L, 1)
        VRV = e[p]
        VRVp = -two_vertex(p, "V", "V", dc, L, 1, mlist=range(1, 5))
        VR2V = two_vertex(p, "V", "V", c, L, 2)
        VRPRV = two_vertex(p, "V", "V", c, L, 2, weight_pm=True)
        VRVRV = three_vertex(p, c, c1J, L)
        Vpp = p * (p - 1) / 2.0
        E3[p] = (2 * G1 * r2 * VRM + 2 * G1 * g2 * VRV + 2 * G1 ** 2 * VRVp
                 + G1 ** 3 * (VRVRV - Vpp * VR2V) - 0.25 * G1 ** 2 * VRPRV)
    C3 = Pi(E3)
    return C2, C3, r2, g2


def c2_shell(L):
    """Closed-form C_2(L) (Sec. 2 of REPORT.md)."""
    from mpmath import mp, mpf, rf, factorial as mfac
    mp.dps = 30
    s = mpf(17)
    for a in range(1, L // 2 + 1):
        w = (rf(mpf(1) / 2, a) / mfac(a)) ** 2
        s += w * (mpf(2) / (2 * a - 1) + mpf(18) / (2 * a) + mpf(18) / (2 * a + 1) + mpf(2) / (2 * a + 2))
    return float(s / 81)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", default="2,4,6,8,10,12,14,16,18,20,22,24,26,28,30")
    ap.add_argument("--check", action="store_true", help="compare with ht_coefficients.csv")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    Ls = [int(v) for v in args.L.split(",") if v]
    data = {}
    if args.check:
        with open(os.path.join(HERE, "ht_coefficients.csv")) as fh:
            for r in csv.DictReader(fh):
                if r["scheme"] == "raw":
                    data[int(r["L"])] = r
    rows = []
    for L in Ls:
        C2, C3, r2, g2 = compute(L)
        row = {"L": L, "C2": repr(C2), "C3": repr(C3), "r2": repr(r2), "g2": repr(g2)}
        msg = f"L={L:4d} C2={C2:.15f} C3={C3:.15f} r2={r2:.12f} g2={g2:.12f}"
        if L in data:
            d = data[L]
            msg += (f" | dC2={C2 - float(d['C2']):+.1e} dC3={C3 - float(d['C3']):+.1e}"
                    f" dr2={r2 - float(d['r2']):+.1e} dg2={g2 - float(d['g2']):+.1e}")
            msg += f" | shell C2 {C2 - c2_shell(L):+.1e}"
        print(msg, flush=True)
        rows.append(row)
    if args.out:
        with open(os.path.join(HERE, args.out), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["L", "C2", "C3", "r2", "g2"])
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
