#!/usr/bin/env python3
"""Assemble C_2(L), C_3(L), C_4(L) (raw / consistent) of the 3D model for every even L <= L_max.

usage: python3 c4_compute3d.py --Lmax 20 [--max-lines4 5] [--out results/c4_L20.npz]

Formulas: README Sec. 2 (fourth-order RS with eps-dependent vertices, as in the 2D project, with
x0 = 3/4 and 3D partial-wave densities)."""
import argparse
import os
import time

import numpy as np

import c4lib3d as lib

g1 = 1.0 / 3.0


def coeffs(F):
    """Order n >= 2 (x_n = 0): E_p = F(p) + 2p r + p(p-1)/2 g;  E1 - E0 = 0, E3 - E0 = 0."""
    r = -(F[1] - F[0]) / 2.0
    g = -(F[3] - F[0] + 6.0 * r) / 3.0
    C = F[2] - F[0] + 4.0 * r + g
    return r, g, C


def window_sum(h, de):
    """out[L] = sum_{N=1}^{L} h[N] (e(L) - e(L-N)), e(M) = sum_{j<=M} de[j] (no large cancellation)."""
    n = len(h) - 1
    out = np.zeros(n + 1)
    for L in range(1, n + 1):
        S = 0.0
        acc = 0.0
        for N in range(1, L + 1):
            S += de[L - N + 1]
            acc += h[N] * S
        out[L] = acc
    return out


try:
    from numba import njit
    window_sum = njit(cache=True)(window_sum)
except Exception:  # pragma: no cover
    pass


def compute(Lmax, max_lines4=5, verbose=True, skip4=False, basis=None, chain4=None):
    t0 = time.time()
    B = basis if basis is not None else lib.Basis(Lmax)
    N = Lmax // 2                      # arrays are indexed by sigma = L/2
    P = (0, 1, 2, 3)
    Vpp = {p: p * (p - 1) / 2.0 for p in P}

    def log(msg):
        if verbose:
            print(f"[{time.time() - t0:8.1f}s] {msg}", flush=True)

    def c(kinds, ops, derivs=None, ps=P, **kw):
        return lib.chain(B, kinds, ops, ps=ps, derivs=derivs, **kw)

    VV_R = c("VV", [(1, 0)])
    VV_R2 = c("VV", [(2, 0)])
    VV_R3 = c("VV", [(3, 0)])
    VV_PR2 = c("VV", [(2, 1)])
    VV_PR3 = c("VV", [(3, 1)])
    VV_P2R3 = c("VV", [(3, 2)])
    MV_R = c("MV", [(1, 0)])
    MM_R = c("MM", [(1, 0)])
    MV_R2 = c("MV", [(2, 0)])
    MV_PR2 = c("MV", [(2, 1)])
    V1V_R = c("VV", [(1, 0)], [1, 0])        # <V R V1>
    V1V_R2 = c("VV", [(2, 0)], [1, 0])
    V1V_PR2 = c("VV", [(2, 1)], [1, 0])
    V2V_R = c("VV", [(1, 0)], [2, 0])        # <V R V2>
    V1V1_R = c("VV", [(1, 0)], [1, 1])       # <V1 R V1>
    M1V_R = c("MV", [(1, 0)], [1, 0])        # <V R M1>
    MV1_R = c("MV", [(1, 0)], [0, 1])        # <V1 R M>
    log("two-vertex pieces done")

    VVV_RR = c("VVV", [(1, 0), (1, 0)])
    VVV_R2R = c("VVV", [(2, 0), (1, 0)])
    VVV_RR2 = c("VVV", [(1, 0), (2, 0)])
    VVV_PR2R = c("VVV", [(2, 1), (1, 0)])
    VVV_RPR2 = c("VVV", [(1, 0), (2, 1)])
    MVV_RR = c("MVV", [(1, 0), (1, 0)])
    VMV_RR = c("VMV", [(1, 0), (1, 0)])
    V1VV_RR = c("VVV", [(1, 0), (1, 0)], [1, 0, 0])
    VV1V_RR = c("VVV", [(1, 0), (1, 0)], [0, 1, 0])
    log("three-vertex pieces done")

    if skip4:
        T4 = {p: np.zeros(N + 1) for p in P}
    elif chain4 is not None:
        T4 = chain4(B)
    else:
        T4 = c("VVVV", [(1, 0)] * 3, max_lines=max_lines4, mirror=True)
    log("four-vertex chain done")

    F2 = {p: g1 ** 2 * VV_R[p] for p in P}
    r2, g2, C2 = coeffs(F2)
    F3 = {p: 2 * g1 * (r2 * MV_R[p] + g2 * VV_R[p] + g1 * V1V_R[p])
          + g1 ** 3 * (VVV_RR[p] - Vpp[p] * VV_R2[p]) - g1 ** 2 / 4.0 * VV_PR2[p] for p in P}
    r3, g3, C3 = coeffs(F3)

    X4 = {}
    parts = {}
    for p in P:
        a = 2 * g1 * (r3 * MV_R[p] + g3 * VV_R[p] + g2 * V1V_R[p] + g1 * V2V_R[p] + r2 * M1V_R[p])
        b = (r2 ** 2 * MM_R[p] + g2 ** 2 * VV_R[p] + g1 ** 2 * V1V1_R[p] + 2 * r2 * g2 * MV_R[p]
             + 2 * r2 * g1 * MV1_R[p] + 2 * g2 * g1 * V1V_R[p])
        cc = 2 * g1 * (r2 * (g1 * MVV_RR[p] - g1 * Vpp[p] * MV_R2[p] - 0.25 * MV_PR2[p])
                       + g2 * (g1 * VVV_RR[p] - g1 * Vpp[p] * VV_R2[p] - 0.25 * VV_PR2[p])
                       + g1 * (g1 * V1VV_RR[p] - g1 * Vpp[p] * V1V_R2[p] - 0.25 * V1V_PR2[p]))
        d = g1 ** 2 * (r2 * (VMV_RR[p] - 2 * p * VV_R2[p]) + g2 * (VVV_RR[p] - Vpp[p] * VV_R2[p])
                       + g1 * VV1V_RR[p])
        e = (g1 ** 4 * (T4[p] - Vpp[p] * (VVV_R2R[p] + VVV_RR2[p]) + Vpp[p] ** 2 * VV_R3[p])
             - g1 ** 3 / 4.0 * (VVV_PR2R[p] + VVV_RPR2[p] - 2 * Vpp[p] * VV_PR3[p])
             + g1 ** 2 / 16.0 * VV_P2R3[p])
        f = -g1 ** 4 * VV_R[p] * VV_R2[p]
        X4[p] = a + b + cc + d + e + f
        parts[p] = dict(a=a, b=b, c=cc, d=d, e=e, f=f)
    r4, g4, C4raw = coeffs(X4)

    # consistent window at order eps^2: D2(N) = g1^2 [e(L) - e(L-N)], e(l) = <0|V R V|0>_l
    wcol = []
    lib.chain(B, "VV", [(2, 0)], ps=P, collect=wcol)
    de = lib.chain(B, "VV", [(1, 0)], ps=(0,), shells=True)[0]      # e(l) increments per level
    Dcons = {p: np.zeros(N + 1) for p in P}
    for (n, k, p, amp, sh) in wcol:
        if n[(0, 1)] == 0:
            continue                                                 # intermediate at level 0: D = 0
        Dcons[p] += float(amp) * g1 ** 2 * window_sum(sh, de)
    X4c = {p: X4[p] + g1 ** 2 * Dcons[p] for p in P}
    _, _, C4cons = coeffs(X4c)
    log("assembled")
    Ls = 2 * np.arange(N + 1)
    return dict(L=Ls, C2=C2, C3=C3, C4raw=C4raw, C4cons=C4cons, r2=r2, g2=g2, r3=r3, g3=g3,
                r4raw=r4, g4raw=g4, X2=np.array([F2[p] for p in P]), X3=np.array([F3[p] for p in P]),
                X4=np.array([X4[p] for p in P]), X4cons=np.array([X4c[p] for p in P]),
                Ev2=g1 ** 2 * VV_R[0], Dcons=np.array([Dcons[p] for p in P]), parts=parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, default=20)
    ap.add_argument("--max-lines4", type=int, default=5)
    ap.add_argument("--skip4", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    res = compute(args.Lmax, max_lines4=args.max_lines4, skip4=args.skip4)
    for j, i in enumerate(res["L"]):
        print(f"L={i:4d} C2={res['C2'][j]:.15f} C3={res['C3'][j]:.15f} C4raw={res['C4raw'][j]:.13f} "
              f"C4cons={res['C4cons'][j]:.13f}")
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        np.savez(args.out, **{k: v for k, v in res.items() if k != "parts"})


if __name__ == "__main__":
    main()


def compute_exact(Lmax, max_lines4=5, verbose=True, basis=None, T4lin=None, skip4=False):
    """Same as compute(), but every Pi / tuning projection acts on exact zero-mode amplitudes before the float
    level sums are combined (no p-independent cancellation)."""
    from fractions import Fraction as Fr
    t0 = time.time()
    B = basis if basis is not None else lib.Basis(Lmax)
    S = Lmax // 2
    PI, R_OF, G_OF = lib.PI, lib.R_OF, lib.G_OF
    Vpp = lambda p: Fr(p * (p - 1), 2)

    def log(msg):
        if verbose:
            print(f"[{time.time() - t0:8.1f}s] {msg}", flush=True)

    def c(kinds, ops, derivs=None, **kw):
        return lib.chain_entries(B, kinds, ops, derivs=derivs, **kw)

    VV_R = c("VV", [(1, 0)])
    VV_R2 = c("VV", [(2, 0)])
    VV_R3 = c("VV", [(3, 0)])
    VV_PR2 = c("VV", [(2, 1)])
    VV_PR3 = c("VV", [(3, 1)])
    VV_P2R3 = c("VV", [(3, 2)])
    MV_R = c("MV", [(1, 0)])
    MM_R = c("MM", [(1, 0)])
    MV_R2 = c("MV", [(2, 0)])
    MV_PR2 = c("MV", [(2, 1)])
    V1V_R = c("VV", [(1, 0)], [1, 0])
    V1V_R2 = c("VV", [(2, 0)], [1, 0])
    V1V_PR2 = c("VV", [(2, 1)], [1, 0])
    V2V_R = c("VV", [(1, 0)], [2, 0])
    V1V1_R = c("VV", [(1, 0)], [1, 1])
    M1V_R = c("MV", [(1, 0)], [1, 0])
    MV1_R = c("MV", [(1, 0)], [0, 1])
    log("two-vertex pieces done")
    VVV_RR = c("VVV", [(1, 0), (1, 0)], mirror=True)
    VVV_R2R = c("VVV", [(2, 0), (1, 0)])
    VVV_RR2 = c("VVV", [(1, 0), (2, 0)])
    VVV_PR2R = c("VVV", [(2, 1), (1, 0)])
    VVV_RPR2 = c("VVV", [(1, 0), (2, 1)])
    MVV_RR = c("MVV", [(1, 0), (1, 0)])
    VMV_RR = c("VMV", [(1, 0), (1, 0)])
    V1VV_RR = c("VVV", [(1, 0), (1, 0)], [1, 0, 0])
    VV1V_RR = c("VVV", [(1, 0), (1, 0)], [0, 1, 0])
    log("three-vertex pieces done")
    if T4lin is not None:
        T4 = T4lin
    elif skip4:
        T4 = lib.Lin()
    else:
        T4 = c("VVVV", [(1, 0)] * 3, max_lines=max_lines4, mirror=True)
    log("four-vertex chain ready")
    g1 = Fr(1, 3)
    X2 = VV_R.scale(float(g1 ** 2))
    r2, g2, C2 = X2.proj(R_OF), X2.proj(G_OF), X2.proj(PI)
    X3 = (MV_R.scale(2 * float(g1) * r2) + VV_R.scale(2 * float(g1) * g2) + V1V_R.scale(float(2 * g1 * g1))
          + VVV_RR.scale(float(g1 ** 3)) + VV_R2.pfac(Vpp).scale(-float(g1 ** 3)) + VV_PR2.scale(-float(g1 ** 2) / 4))
    r3, g3, C3 = X3.proj(R_OF), X3.proj(G_OF), X3.proj(PI)
    G = float(g1)
    a = (MV_R.scale(2 * G * r3) + VV_R.scale(2 * G * g3) + V1V_R.scale(2 * G * g2) + V2V_R.scale(2 * G * G)
         + M1V_R.scale(2 * G * r2))
    b = (MM_R.scale(r2 * r2) + VV_R.scale(g2 * g2) + V1V1_R.scale(G * G) + MV_R.scale(2 * r2 * g2)
         + MV1_R.scale(2 * r2 * G) + V1V_R.scale(2 * g2 * G))
    cc = ((MVV_RR.scale(G) + MV_R2.pfac(Vpp).scale(-G) + MV_PR2.scale(-0.25)).scale(2 * G * r2)
          + (VVV_RR.scale(G) + VV_R2.pfac(Vpp).scale(-G) + VV_PR2.scale(-0.25)).scale(2 * G * g2)
          + (V1VV_RR.scale(G) + V1V_R2.pfac(Vpp).scale(-G) + V1V_PR2.scale(-0.25)).scale(2 * G * G))
    d = ((VMV_RR + VV_R2.pfac(lambda p: -2 * p)).scale(G * G * r2)
         + (VVV_RR + VV_R2.pfac(lambda p: -Vpp(p))).scale(G * G * g2) + VV1V_RR.scale(G ** 3))
    e = ((T4 + VVV_R2R.pfac(lambda p: -Vpp(p)) + VVV_RR2.pfac(lambda p: -Vpp(p))
          + VV_R3.pfac(lambda p: Vpp(p) ** 2)).scale(G ** 4)
         + (VVV_PR2R + VVV_RPR2 + VV_PR3.pfac(lambda p: -2 * Vpp(p))).scale(-G ** 3 / 4)
         + VV_P2R3.scale(G * G / 16))
    f = VV_R.times(VV_R2).scale(-G ** 4)
    X4 = a + b + cc + d + e + f
    C4raw = X4.proj(PI)
    parts = {k: v.proj(PI) for k, v in dict(a=a, b=b, c=cc, d=d, e=e, f=f).items()}
    # window, exact Pi per key
    wcol = []
    lib.chain(B, "VV", [(2, 0)], ps=(0, 1, 2, 3), collect=wcol)
    de = lib.chain(B, "VV", [(1, 0)], ps=(0,), shells=True)[0]
    Wl = lib.Lin()
    acc = {}
    for (n, k, p, amp, sh) in wcol:
        if n[(0, 1)] == 0:
            continue
        key = (n[(0, 1)], k)
        acc.setdefault(key, [None, [Fr(0)] * 4])
        acc[key][0] = sh
        acc[key][1][p] += amp
    for key, (sh, amps) in acc.items():
        Wl.add(amps, window_sum(sh, de))
    Dc = Wl.scale(G ** 4)
    C4cons = C4raw + Dc.proj(PI)
    log("assembled (exact projections)")
    return dict(L=2 * np.arange(S + 1), C2=C2, C3=C3, C4raw=C4raw, C4cons=C4cons, r2=r2, g2=g2, r3=r3, g3=g3,
                Dcons=Dc.proj(PI), Ev2=float(g1 ** 2) * VV_R.at(0),
                X2=np.array([X2.at(p) for p in range(4)]), X3=np.array([X3.at(p) for p in range(4)]),
                parts=parts)
