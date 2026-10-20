#!/usr/bin/env python3
"""Closed form (exact Fractions) of the order-eps^4 difference zeromode - consistent, independent of the RS codes.

Second order.  W_1 = -P/4 + V_0/3 (r_1 = 0, g_1 = 1/3), and on zero-mode states <z|V_1|z> = 0 (w_00 = 1), so
    E_z^(2)(l) = 2 z r_2 + z(z-1)/2 g_2 + S_z(l),   S_z(l) = (1/9) sum_{s != z, s not in B} |<s|V_0|z>|^2/(z/2 - E_s).
Factorising phi = phi_0 + phi' (zero mode + the rest), V|z> = (1/12) sum_m C(4,m) :phi_0^{4-m}: [(phi'^-)^m]_theta |z>,
an intermediate state has q zero modes and m non-zero quanta at level N, energy (q + m)/2 + N, and
    S_z(l) = -(1/1296) sum_{m=0}^{4} C(4,m)^2 sum_q Zm(q|z) sum_{N <= l} F_m(N) / (N + (q - z + m)/2),  (m,q) != (0,z)
    Zm(q|z) = |<q|:phi_0^{4-m}:|z>|^2 = C(k,j)^2 z! q! / ((z-k+j)!)^2,  k = 4-m, q = z - k + 2j,
    F_m(N)  = m! [u^{N/2} v^{N/2}] ((1-u)^{-1/2}(1-v)^{-1/2} - 1)^m = m! sum_i C(m,i)(-1)^{m-i} ((i/2)_{N/2}/(N/2)!)^2.
(The degenerate partners B of z >= 5 never appear: V cannot connect |z> to them, so no zero denominator occurs.)

Zeromode vs consistent.  Both schemes coincide through eps^3 (D enters at eps^4).  At eps^4 the only difference
is the order-2 window on the intermediate states of <p|W_1 R D_2 R W_1|p>:
    D'(q, N) = D_zm^(2)(q, N) - D_cons^(2)(N) = [S_q(L) - S_0(L)] - [S_q(L-N) - S_0(L-N)]  (r_2, g_2 cancel),
    dE_p^(4) = (1/1296) sum_{m>=1} C(4,m)^2 sum_q Zm(q|p) sum_{N<=L} F_m(N) D'(q,N) / (N + (q-p+m)/2)^2,
    dr_4 = (dE_0 - dE_1)/2,  dg_4 = (dE_0 - dE_3 - 6 dr_4)/3,
    dC_4 = dE_2 - dE_1 - dE_3/3 + dE_0/3.
This is the construction of ../continuum/zero_mode_window.py (there in floating point, for large L), here exact.

usage: python3 closed_form_dC4.py --Ls 0,2,4,...  [--json out.json]
"""
from fractions import Fraction as Fr
from math import comb, factorial
import argparse, json


def poch_ratio(a, n):
    """(a)_n / n! exactly (a Fraction)."""
    v = Fr(1)
    for i in range(n):
        v *= (a + i) / Fr(i + 1)
    return v


def F(m, N):
    if N % 2:
        return Fr(0)
    n = N // 2
    s = Fr(0)
    for i in range(m + 1):
        s += comb(m, i) * (-1) ** (m - i) * poch_ratio(Fr(i, 2), n) ** 2
    return factorial(m) * s


def Zm(m, z):
    """dict q -> |<q|:phi_0^{4-m}:|z>|^2."""
    k = 4 - m
    out = {}
    for j in range(k + 1):
        if z - k + j < 0:
            continue
        q = z - k + 2 * j
        out[q] = out.get(q, Fr(0)) + Fr(comb(k, j) ** 2 * factorial(z) * factorial(q), factorial(z - k + j) ** 2)
    return out


def S(z, l):
    tot = Fr(0)
    for m in range(5):
        for q, a2 in Zm(m, z).items():
            for N in range(0, l + 1, 2):
                if m == 0 and N > 0:
                    break
                if m == 0 and q == z:
                    continue
                f = F(m, N)
                if f == 0:
                    continue
                den = N + Fr(q - z + m, 2)
                assert den != 0
                tot += comb(4, m) ** 2 * a2 * f / den
    return -tot / 1296


def dC4(L):
    Sc = {}

    def Sq(q, l):
        if (q, l) not in Sc:
            Sc[(q, l)] = S(q, l)
        return Sc[(q, l)]

    def Dp(q, N):
        return (Sq(q, L) - Sq(0, L)) - (Sq(q, L - N) - Sq(0, L - N))

    dE = {}
    for p in range(4):
        tot = Fr(0)
        for m in range(1, 5):
            for q, a2 in Zm(m, p).items():
                for N in range(2, L + 1, 2):
                    f = F(m, N)
                    if f == 0:
                        continue
                    den = N + Fr(q - p + m, 2)
                    tot += comb(4, m) ** 2 * a2 * f * Dp(q, N) / den ** 2
        dE[p] = tot / 1296
    dr = (dE[0] - dE[1]) / 2
    dg = (dE[0] - dE[3] - 6 * dr) / 3
    dc = dE[2] - dE[1] - dE[3] / 3 + dE[0] / 3
    C2 = (Sq(2, L) - Sq(0, L)) - (Sq(1, L) - Sq(0, L)) - (Sq(3, L) - Sq(0, L)) / 3
    return dict(L=L, dC4=dc, dr4=dr, dg4=dg, dE4=dE, C2=C2, S={q: Sq(q, L) for q in range(7)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Ls", default="0,2,4,6,8,10,12,14")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    out = []
    for L in [int(x) for x in a.Ls.split(",")]:
        d = dC4(L)
        print(f"L={L:3d}  dC4 = {float(d['dC4']):+.15f}  dr4 = {float(d['dr4']):+.12f}  dg4 = {float(d['dg4']):+.12f}"
              f"  C2 = {float(d['C2']):.15f}", flush=True)
        out.append({"L": L, "dC4": str(d["dC4"]), "dC4_float": float(d["dC4"]), "dr4": str(d["dr4"]),
                    "dg4": str(d["dg4"]), "dE4": {p: str(v) for p, v in d["dE4"].items()}, "C2": str(d["C2"]),
                    "S_q_L": {q: str(v) for q, v in d["S"].items()}})
    if a.json:
        with open(a.json, "w") as f:
            json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
