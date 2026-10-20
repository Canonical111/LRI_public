#!/usr/bin/env python3
"""Assemble C_2(L), C_3(L), C_4(L) (raw / consistent / corrected) for every even L <= L_max.

usage: python3 c4_compute.py --Lmax 40 [--full] [--max-lines4 5] [--out results/c4_L40.npz]

--full keeps every four-vertex line pattern (needed to reproduce the individual E_p^(4); C_4 only needs the
patterns with at most five chi lines, see README Sec. 3)."""
import argparse
import os
import time

import numpy as np

import c4lib as lib

g1 = 1.0 / 3.0


def coeffs(F):
    """Tuning at order n >= 2 (x_n = 0): E_p = F(p) + 2p r + p(p-1)/2 g;  E1 - E0 = 0, E3 - E0 = 0."""
    r = -(F[1] - F[0]) / 2.0
    g = -(F[3] - F[0] + 6.0 * r) / 3.0
    C = F[2] - F[0] + 4.0 * r + g
    return r, g, C


def compute(Lmax, full=False, max_lines4=5, verbose=True, skip4=False, chain_runner=None):
    """chain_runner(kinds, ops, dv, max_lines) -> {p: array}; default: serial lib.chain."""
    N = Lmax // 2
    t0 = time.time()
    ser = lib.Series(N)
    if chain_runner is None:
        chain_runner = lambda kinds, ops, dv, ml: lib.chain(kinds, ops, N, ser, (0, 1, 2, 3), deriv_vertex=dv,
                                                             max_lines=ml)
    P = (0, 1, 2, 3)
    Vpp = {p: p * (p - 1) / 2.0 for p in P}

    def log(msg):
        if verbose:
            print(f"[{time.time() - t0:8.1f}s] {msg}", flush=True)

    c2 = lambda kinds, d, op, ps=P: lib.chain2(kinds, d, op, N, ser, ps)
    VV_R = c2(["V", "V"], [0, 0], (1, 0), ps=tuple(range(8)))
    VV_R2 = c2(["V", "V"], [0, 0], (2, 0))
    VV_R3 = c2(["V", "V"], [0, 0], (3, 0))
    VV_PR2 = c2(["V", "V"], [0, 0], (2, 1))
    VV_PR3 = c2(["V", "V"], [0, 0], (3, 1))
    VV_P2R3 = c2(["V", "V"], [0, 0], (3, 2))
    MV_R = c2(["M", "V"], [0, 0], (1, 0))
    MM_R = c2(["M", "M"], [0, 0], (1, 0))
    MV_R2 = c2(["M", "V"], [0, 0], (2, 0))
    MV_PR2 = c2(["M", "V"], [0, 0], (2, 1))
    VdV_R = c2(["V", "V"], [1, 0], (1, 0))
    VdV_R2 = c2(["V", "V"], [1, 0], (2, 0))
    VdV_PR2 = c2(["V", "V"], [1, 0], (2, 1))
    VddV_R = c2(["V", "V"], [2, 0], (1, 0))
    VdVd_R = c2(["V", "V"], [1, 1], (1, 0))
    MdV_R = c2(["M", "V"], [1, 0], (1, 0))
    MVd_R = c2(["M", "V"], [0, 1], (1, 0))
    log("two-vertex pieces done")

    ch3 = lambda kinds, ops, dv=None: chain_runner(kinds, ops, dv, None)
    VVV_RR = ch3(["V", "V", "V"], [(1, 0), (1, 0)])
    VVV_R2R = ch3(["V", "V", "V"], [(2, 0), (1, 0)])
    VVV_RR2 = ch3(["V", "V", "V"], [(1, 0), (2, 0)])
    VVV_PR2R = ch3(["V", "V", "V"], [(2, 1), (1, 0)])
    VVV_RPR2 = ch3(["V", "V", "V"], [(1, 0), (2, 1)])
    MVV_RR = ch3(["M", "V", "V"], [(1, 0), (1, 0)])
    VMV_RR = ch3(["V", "M", "V"], [(1, 0), (1, 0)])
    dVVV_RR = ch3(["V", "V", "V"], [(1, 0), (1, 0)], dv=0)
    VdVV_RR = ch3(["V", "V", "V"], [(1, 0), (1, 0)], dv=1)
    log("three-vertex pieces done")

    if skip4:
        T4 = {p: np.zeros(N + 1) for p in P}
    else:
        T4 = chain_runner(["V"] * 4, [(1, 0)] * 3, None, None if full else max_lines4)
    log("four-vertex chain done")

    # ---------------------------------------------------------------- order 2, 3
    F2 = {p: g1 ** 2 * VV_R[p] for p in P}
    r2, g2, C2 = coeffs(F2)
    F3 = {p: 2 * g1 * (r2 * MV_R[p] + g2 * VV_R[p] + g1 * VdV_R[p])
          + g1 ** 3 * (VVV_RR[p] - Vpp[p] * VV_R2[p]) - g1 ** 2 / 4.0 * VV_PR2[p] for p in P}
    r3, g3, C3 = coeffs(F3)

    # ---------------------------------------------------------------- order 4 without window
    X4 = {}
    parts = {}
    for p in P:
        a = 2 * g1 * (r3 * MV_R[p] + g3 * VV_R[p] + g2 * VdV_R[p] + g1 / 2.0 * VddV_R[p] + r2 * MdV_R[p])
        b = (r2 ** 2 * MM_R[p] + g2 ** 2 * VV_R[p] + g1 ** 2 * VdVd_R[p] + 2 * r2 * g2 * MV_R[p]
             + 2 * r2 * g1 * MVd_R[p] + 2 * g2 * g1 * VdV_R[p])
        c = 2 * g1 * (r2 * (g1 * MVV_RR[p] - g1 * Vpp[p] * MV_R2[p] - 0.25 * MV_PR2[p])
                      + g2 * (g1 * VVV_RR[p] - g1 * Vpp[p] * VV_R2[p] - 0.25 * VV_PR2[p])
                      + g1 * (g1 * dVVV_RR[p] - g1 * Vpp[p] * VdV_R2[p] - 0.25 * VdV_PR2[p]))
        d = g1 ** 2 * (r2 * (VMV_RR[p] - 2 * p * VV_R2[p]) + g2 * (VVV_RR[p] - Vpp[p] * VV_R2[p])
                       + g1 * VdVV_RR[p])
        e = (g1 ** 4 * (T4[p] - Vpp[p] * (VVV_R2R[p] + VVV_RR2[p]) + Vpp[p] ** 2 * VV_R3[p])
             - g1 ** 3 / 4.0 * (VVV_PR2R[p] + VVV_RPR2[p] - 2 * Vpp[p] * VV_PR3[p])
             + g1 ** 2 / 16.0 * VV_P2R3[p])
        f = -g1 ** 4 * VV_R[p] * VV_R2[p]
        X4[p] = a + b + c + d + e + f
        parts[p] = dict(a=a, b=b, c=c, d=d, e=e, f=f)
    r4, g4, C4raw = coeffs(X4)

    # ---------------------------------------------------------------- order-eps^2 windows sandwiched
    _, wparts = lib.chain2(["V", "V"], [0, 0], (2, 0), N, ser, P, per_key=True)
    de = lib.chain2(["V", "V"], [0, 0], (1, 0), N, ser, tuple(range(8)), shells=True)  # e_z(l) increments

    def window_term(zfun):
        out = {p: np.zeros(N + 1) for p in P}
        for (p, m, dlt, amp, Rm) in wparts:
            if m == 0:
                continue  # intermediate at level 0: D = 0
            g = lib.slice_G((dlt + m) / 2.0, 2, m, N + 1)
            h = Rm * g                                  # sum_sigma h(sigma) [e(M) - e(M - sigma)]
            val = lib.window_sum(h, de[zfun(p, dlt)])
            out[p] += float(amp) * g1 ** 2 * val
        return out

    Dcons = window_term(lambda p, d: 0)
    Dcorr = window_term(lambda p, d: p + d)
    X4c = {p: X4[p] + g1 ** 2 * Dcons[p] for p in P}
    X4z = {p: X4[p] + g1 ** 2 * Dcorr[p] for p in P}
    _, _, C4cons = coeffs(X4c)
    _, _, C4corr = coeffs(X4z)
    log("assembled")
    L = 2 * np.arange(N + 1)
    return dict(L=L, C2=C2, C3=C3, C4raw=C4raw, C4cons=C4cons, C4corr=C4corr, r2=r2, g2=g2, r3=r3, g3=g3,
                r4raw=r4, g4raw=g4, X4=np.array([X4[p] for p in P]), X4cons=np.array([X4c[p] for p in P]),
                Ev2=g1 ** 2 * VV_R[0], Dcons=np.array([Dcons[p] for p in P]),
                Dcorr=np.array([Dcorr[p] for p in P]),
                parts={p: parts[p] for p in P})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, default=20)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--max-lines4", type=int, default=5)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    res = compute(args.Lmax, full=args.full, max_lines4=args.max_lines4)
    for i, L in enumerate(res["L"]):
        print(f"L={L:5d} C2={res['C2'][i]:.15f} C3={res['C3'][i]:.15f} C4raw={res['C4raw'][i]:.13f} "
              f"C4cons={res['C4cons'][i]:.13f} C4corr={res['C4corr'][i]:.13f}")
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        np.savez(args.out, **{k: v for k, v in res.items() if k != "parts"})


if __name__ == "__main__":
    main()
