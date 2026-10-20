#!/usr/bin/env python3
"""Exact O(eps^2) descendant identity for single-particle descendants chi_aa = d^a dbar^a phi (J = 0):
    Delta_desc(a; L) = [E(chi_aa) - E(phi)]^(2) = 0 in the continuum (E(d^a dbar^a phi) - E(phi) = 2a exactly).

In the truncated theory (consistent or zero-mode window; for chi_aa, z = 0, so both windows restore exactly the
vacuum bubbles that coexist with chi_aa),
    Delta_desc = g1^2 [ N(a) + Z(a) - w_aa (e_1(L) - e_0(L)) ],     (r2 from E1 - E0 = x at eps^2)
with, for k = 1..4 chi legs per vertex (n = k - 1 internal chi lines, 4 - k zero modes created and destroyed),
    coef_k = [C(4,k)/12]^2 k^2 n! (4-k)!  (times w_aa),
    N_k(a) = sum_{sigma <= L/2}        R_n(sigma) / (2a - 1 - 2 sigma)        (external line absorbed at V1, re-emitted at V2)
    Z_k(a) = sum_{sigma <= L/2 - 2a}   R_n(sigma) / (-(2a + 2 + 2 sigma))     (exchange: V1 emits the new chi_aa, V2 absorbs the old)
The exchange ('Z') states contain the external quantum twice, so the level cutoff gives their bubbles only L - 4a.
For the zero mode the analogous Z-type intermediate states contain an extra zero mode, which costs no level.
usage: python3 descendant_e2.py"""
from fractions import Fraction as Fr
from math import comb, factorial

import numpy as np

import c4lib as lib
import windows as W

G1 = 1.0 / 3.0


def e_diff(N, ser, R):
    """e_1(L) - e_0(L) for every L = 2M (cumulative), from the exact zero-mode polynomials Q(m, d, z)."""
    sig = np.arange(N + 1)
    out = np.zeros(N + 1)
    for m in range(0, 5):
        cmv = Fr(comb(4, m), 12) ** 2 * factorial(m)
        for d in range(-(4 - m), 4 - m + 1, 2):
            q = W.Q(m, d, 1) - W.Q(m, d, 0)
            if q == 0:
                continue
            if m == 0:
                if d == 0:
                    continue
                out += float(cmv * q) * (-1.0 / (d / 2.0))
                continue
            den = (d + m) / 2.0 + 2.0 * sig
            t = np.zeros(N + 1)
            mask = 2 * sig >= m
            t[mask] = -R[m][mask] / den[mask]
            out += float(cmv * q) * np.cumsum(t)
    return out


def chi_terms(a, N, R):
    """N(a) + Z(a) for every L = 2M, split by k."""
    sig = np.arange(N + 1)
    parts = {}
    for k in range(1, 5):
        n = k - 1
        coef = float(Fr(comb(4, k), 12) ** 2 * k * k * factorial(n) * factorial(4 - k))
        if n == 0:
            Rn = np.zeros(N + 1)
            Rn[0] = 1.0
        else:
            Rn = R[n]
        mask = 2 * sig >= n
        tN = np.zeros(N + 1)
        tN[mask] = Rn[mask] / (2 * a - 1 - 2.0 * sig[mask])
        Ncum = np.cumsum(tN)
        tZ = np.zeros(N + 1)
        tZ[mask] = Rn[mask] / (-(2.0 * a + 2 + 2.0 * sig[mask]))
        Zc = np.cumsum(tZ)
        Zcum = np.zeros(N + 1)
        Mv = np.arange(N + 1)
        ok = Mv - 2 * a >= 0
        Zcum[ok] = Zc[Mv[ok] - 2 * a]
        parts[k] = coef * (Ncum + Zcum)
    return parts


def main(Lmax=20000):
    N = Lmax // 2
    ser = lib.Series(N, kmax=4)
    R = {m: lib.two_vertex_density(m, 0, 0, ser) for m in range(1, 5)}
    ed = e_diff(N, ser, R)
    print("Delta_desc(a; L) = [E(chi_aa) - E(phi)] at eps^2 (window-corrected); prediction of the Z-budget defect:"
          " (8a/(27 pi)) w_aa")
    for a in (1, 2, 3, 5, 10):
        w = float(Fr(1, 1)) * (ser.v[1][a] ** 2)
        parts = chi_terms(a, N, R)
        tot = sum(parts.values())
        dd = G1 ** 2 * w * (tot - ed)
        row = " ".join(f"L={2*M}:{dd[M]:+.8f}" for M in (10 * a, 100, 1000, 10000, N) if M <= N)
        print(f"a={a:3d} w_aa={w:.6f} pred={8*a/(27*np.pi)*w:+.8f}  {row}")


if __name__ == "__main__":
    main()
