#!/usr/bin/env python3
"""Two-vertex quantities to very large L, cancellation-free: C_2(L), the vacuum energy E_v^(2)(l) = g1^2 e(l),
and the consistent-window shift Delta_cons(L) = C4cons(L) - C4raw(L).

Exact Pi-projection per zero-mode key (README Sec. 2.6): every final quantity is
    sum_{lines m, zero-mode shift delta} Pi_p[A_{m,delta}(p)] * (level sum)
with the Pi-weights exact rationals, so the p-independent vacuum bubble (~l^3) never enters C_2 or Delta_cons.
Line densities from the Gegenbauer recurrence (no mode tables): a bath line at level N between two points is
C_N^(x)(t) (N >= 1), x = 3/4; a bundle of m lines is the m-th power (series in r) at Gauss-Legendre nodes.

usage: python3 windows3d.py --Lmax 2000 --out results/windows_L2000.npz
"""
import argparse
import math
import os
import time
from fractions import Fraction as Fr

import numpy as np

import c4lib3d as lib

X = 0.75


def gegenbauer_nodes(Lmax, t):
    """C[N, q] = C_N^(x)(t_q), N = 0..Lmax."""
    C = np.zeros((Lmax + 1, len(t)))
    C[0] = 1.0
    C[1] = 2 * X * t
    for N in range(2, Lmax + 1):
        C[N] = (2 * t * (N + X - 1) * C[N - 1] - (N + 2 * X - 2) * C[N - 2]) / N
    return C


def bundle_l0(Lmax, mmax=4, exact=True):
    """rho[m][N] = int dt/2 (C(r,t) - 1)^m at r^N, m = 0..mmax.  exact=True: closed form
    (1/2) int dt (1 - 2rt + r^2)^(-k x) = [(1+r)^a - (1-r)^a] / (4 r (1 - k x)), a = 2 - 2 k x, summed with the binomial
    expansion of (G - 1)^m in mpmath (correctly rounded); exact=False: Gegenbauer recurrence + quadrature (loses
    ~N^(5/4) eps to the oscillatory angular integral)."""
    if exact:
        import mpmath as mp
        mp.mp.dps = 40
        x = mp.mpf(3) / 4
        rho = [np.zeros(Lmax + 1) for _ in range(mmax + 1)]
        rho[0][0] = 1.0
        ck = {}
        for k in range(1, mmax + 1):
            a = 2 - 2 * k * x
            c = [mp.mpf(0)] * (Lmax + 1)
            b = mp.binomial(a, 1)                     # binom(a, j), j = N + 1, updated by the ratio (a - j)/(j + 1)
            j = 1
            for N in range(0, Lmax + 1):
                if N % 2 == 0:
                    c[N] = 2 * b / (4 * (1 - k * x))
                b = b * (a - j) / (j + 1)
                j += 1
            ck[k] = c
        for m in range(1, mmax + 1):
            for N in range(0, Lmax + 1, 2):
                v = sum(mp.binomial(m, k) * (-1) ** (m - k) * ck[k][N] for k in range(1, m + 1))
                if N == 0:
                    v += (-1) ** m
                rho[m][N] = float(v)
            rho[m][:m] = 0.0
        return rho
    Q = Lmax // 2 + 2
    t, w = np.polynomial.legendre.leggauss(Q)
    line = gegenbauer_nodes(Lmax, t)
    line[0] = 0.0
    rho = [np.zeros(Lmax + 1) for _ in range(mmax + 1)]
    rho[0][0] = 1.0
    B = line.copy()
    rho[1] = B @ (w / 2)
    for m in range(2, mmax + 1):
        B = lib.conv_rows(B, line)
        rho[m] = B @ (w / 2)
        rho[m][:m] = 0.0
    for m in range(1, mmax + 1):
        rho[m][1::2] = 0.0                    # odd total level vanishes by parity (exactly)
    return rho


def two_vertex_keys(kinds, pw, q=0, ps=(0, 1, 2, 3)):
    """[(m, delta, {p: A})] for <p| X_1 (P-p)^q R^pw X_0 |p>, X_i in {V, M}."""
    out = []
    for m in range(0, min(lib.MAXLEGS[kinds[0]], lib.MAXLEGS[kinds[1]]) + 1):
        zl = [lib.MAXLEGS[kinds[0]] - m, lib.MAXLEGS[kinds[1]] - m]
        pref = lib.vcoef(kinds[0], m) * lib.vcoef(kinds[1], m) * math.factorial(m)
        amps = {}
        for p in ps:
            for rs, amp in lib.zero_mode_paths(p, zl):
                d = rs[0] - p
                if m == 0 and d == 0:
                    continue
                a = pref * amp * Fr(d + m) ** q
                if a:
                    amps.setdefault(d, {}).setdefault(p, Fr(0))
                    amps[d][p] += a
        for d, A in amps.items():
            out.append((m, d, A))
    return out


def Pi_exact(A):
    g = lambda p: A.get(p, Fr(0))
    return g(2) - g(1) - (g(3) - g(0)) / 3


def shells(rho_m, m, d, pw, S):
    """Per-sigma values rho_m(2 sigma) * (-1)^pw / den^pw, den = 2 sigma + x0 (d + m)."""
    return rho_m[0: 2 * S + 1: 2] * lib.slice_G(d, m, pw, S + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    t0 = time.time()
    S = args.Lmax // 2
    rho = bundle_l0(args.Lmax)
    print(f"[{time.time() - t0:.1f}s] densities", flush=True)
    g1 = Fr(1, 3)
    # C2 = Pi[g1^2 <VRV>]; e(l) = <0|VRV|0>_l
    C2 = np.zeros(S + 1)
    de = np.zeros(S + 1)
    for m, d, A in two_vertex_keys("VV", 1):
        sh = shells(rho[m], m, d, 1, S)
        w = Pi_exact(A) * g1 ** 2
        if w:
            C2 += float(w) * np.cumsum(sh)
        if 0 in A:
            de += float(A[0]) * sh
    e = np.cumsum(de)
    # Delta_cons = Pi[g1^2 <V R D2 R V>], D2(N) = g1^2 [e(L) - e(L-N)]
    from c4_compute3d import window_sum
    D = np.zeros(S + 1)
    for m, d, A in two_vertex_keys("VV", 2):
        if m == 0:
            continue
        w = Pi_exact(A) * g1 ** 4
        if w:
            h = shells(rho[m], m, d, 2, S)
            D += float(w) * window_sum(h, de)
    # zero-mode-aware window: D2(z, N) = g1^2 [e_z(L) - e_z(L - N)], z = p + delta (slice zero-mode number);
    # Delta_zm = C4corr - C4cons = sum over key pairs of exact Pi-weights times single-signed window sums
    zs = tuple(range(8))
    keysR = two_vertex_keys("VV", 1, ps=zs)                 # e_z(l) = sum_{m',d'} A_{m',d'}(z) s_{m',d'}(l)
    sR = {(m, d): shells(rho[m], m, d, 1, S) for m, d, _ in keysR}
    Dzm = np.zeros(S + 1)
    pis = {0: Fr(1, 3), 1: Fr(-1), 2: Fr(1), 3: Fr(-1, 3)}
    for m, d, A in two_vertex_keys("VV", 2):
        if m == 0:
            continue
        h = shells(rho[m], m, d, 2, S)
        for m2, d2, A2 in keysR:
            w = sum(pis[p] * A.get(p, Fr(0)) * (A2.get(p + d, Fr(0)) - A2.get(0, Fr(0))) for p in range(4))
            w *= g1 ** 4
            if w:
                Dzm += float(w) * window_sum(h, sR[(m2, d2)])
    ez = {z: np.cumsum(sum(float(A2.get(z, Fr(0))) * sR[(m2, d2)] for m2, d2, A2 in keysR)) for z in zs}
    print(f"[{time.time() - t0:.1f}s] done", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    np.savez(args.out, L=2 * np.arange(S + 1), C2=C2, e=e, Ev2=float(g1 ** 2) * e, Dcons=D, Dzm=Dzm,
             ez=np.array([ez[z] for z in zs]))
    for j in list(range(0, min(S, 20) + 1, 2)) + list(range(20, S + 1, max(1, S // 20))):
        print(f"L={2 * j:5d} C2={C2[j]:.15f} Ev2={float(g1 ** 2) * e[j]:.10e} Dcons={D[j]:.15f} Dzm={Dzm[j]:.15f}")


if __name__ == "__main__":
    main()
