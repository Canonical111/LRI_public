#!/usr/bin/env python3
"""eps^4 shift of C_4 from the leading-order chi-attached sunset window

    D_chi = -(g1^2/(3 pi)) {N, M'},   M' = M - :Z^2:  (the parts of M = <:phi^2:> with at least one chi leg),

inserted into H at order eps^2 (README Sec. 4).  Matrix elements: D(s -> s') = -(2 g1^2/(3 pi)) (sigma_s + sigma_s') M'_{s's},
sigma = level/2.  It is symmetric, vanishes on level-0 diagonals, but connects |p> to two-quantum states (M' A^dag A^dag).
Through eps^4 it enters (non-symmetric RS collected at eps^4, README Sec. 4.2):
    dX3[p] = 2 g1 <V R D>_p                                                           (changes r3, g3; C3 unchanged)
    dX4[p] = g1^2 <V R D R V> + 2 g1 [ g1 <V R V R D> - g1 V_pp <V R^2 D> - (1/4) <V R (P-p) R D> ]
and dC4 = Pi[dX4] + 2 g1 dg3 Pi[<V R V>]   (r3 drops out of C4; <W2 R D>, <D R D> are killed by Pi).
Chains are evaluated with the c4lib machinery; the {N, .} weight is an extra factor sigma on the slices adjacent to M.
usage: python3 nm_window.py --Lmax 400 --out results/nm_L400.npz"""
import argparse
import os
from fractions import Fraction as Fr
from math import factorial

import numpy as np

import c4lib as lib

g1 = 1.0 / 3.0
KAPPA = -2.0 * g1 ** 2 / (3.0 * np.pi)     # D(s->s') = KAPPA * (sigma_s + sigma_s') * M'_{s's}


def chain_pattern_w(kinds, slice_ops, n, N, ser, wslice, ps=(0, 1, 2, 3)):
    """c4lib.chain_pattern with the slice factor of slice `wslice` multiplied by sigma (= level/2)."""
    K = len(kinds)
    legs = lib.legs_of(n, K)
    nsl = lib.slice_counts(n, K)
    zl = [lib.MAXLEGS[kinds[i]] - legs[i] for i in range(K)]
    combf = Fr(1)
    for i in range(K):
        combf *= factorial(legs[i])
    for b, v in n.items():
        combf /= factorial(v)
    vc = Fr(1)
    for i in range(K):
        vc *= lib.vcoef(kinds[i], legs[i])
    keyamp = {}
    for p in ps:
        for rs, amp in lib.zero_mode_paths(p, zl):
            deltas = tuple(r - p for r in rs)
            ok = True
            fac = Fr(1)
            for s_ in range(K - 1):
                if nsl[s_] == 0 and deltas[s_] == 0:
                    ok = False
                    break
                pw, q = slice_ops[s_]
                fac *= Fr(deltas[s_] + nsl[s_]) ** q * (-1) ** pw
            if not ok or fac == 0:
                continue
            keyamp.setdefault(deltas, {}).setdefault(p, Fr(0))
            keyamp[deltas][p] += combf * vc * amp * fac
    keyamp = {k: d for k, d in keyamp.items() if any(v != 0 for v in d.values())}
    if not keyamp:
        return None
    Ns = [N if nsl[s_] > 0 else 0 for s_ in range(K - 1)]
    if nsl[wslice] == 0:
        return None          # weight sigma = 0 on a level-0 slice
    R = lib.density(K, n, ser, Ns)
    keys = list(keyamp)
    Gs = []
    for s_ in range(K - 1):
        pw = slice_ops[s_][0]
        G = np.array([lib.slice_G((k[s_] + nsl[s_]) / 2.0, pw, nsl[s_], Ns[s_] + 1) for k in keys])
        if s_ == wslice:
            G = G * np.arange(Ns[s_] + 1)[None, :]
        Gs.append(G)
    sh = lib.shell_sums(R, Gs, N)
    cum = np.cumsum(sh, axis=1)
    res = {p: np.zeros(N + 1) for p in ps}
    for t, k in enumerate(keys):
        for p, a in keyamp[k].items():
            res[p] += float(a) * cum[t]
    return res


def chain_w(kinds, slice_ops, N, ser, mvert, wslices, ps=(0, 1, 2, 3)):
    """sum over line patterns with >= 1 chi leg on the M vertex `mvert`, weight sum_{s in wslices} sigma_s."""
    res = {p: np.zeros(N + 1) for p in ps}
    K = len(kinds)
    for n in lib.patterns(kinds):
        if lib.legs_of(n, K)[mvert] == 0:
            continue
        for ws in wslices:
            r = chain_pattern_w(kinds, slice_ops, n, N, ser, ws, ps)
            if r is None:
                continue
            for p in ps:
                res[p] += r[p]
    return res


def Pi(f):
    return f[2] - f[1] - (f[3] - f[0]) / 3.0


def compute(Lmax):
    N = Lmax // 2
    ser = lib.Series(N)
    P = (0, 1, 2, 3)
    Vpp = {p: p * (p - 1) / 2.0 for p in P}
    # D-weighted chains (M = D's operator, acting first unless stated)
    MV_R = chain_w(["M", "V"], [(1, 0)], N, ser, 0, [0])
    MV_R2 = chain_w(["M", "V"], [(2, 0)], N, ser, 0, [0])
    MV_PR2 = chain_w(["M", "V"], [(2, 1)], N, ser, 0, [0])
    MVV_RR = chain_w(["M", "V", "V"], [(1, 0), (1, 0)], N, ser, 0, [0])
    VMV_RR = chain_w(["V", "M", "V"], [(1, 0), (1, 0)], N, ser, 1, [0, 1])
    VV_R = lib.chain2(["V", "V"], [0, 0], (1, 0), N, ser, P)
    dX3 = {p: 2 * g1 * KAPPA * MV_R[p] for p in P}
    dr3 = -(dX3[1] - dX3[0]) / 2.0
    dg3 = -(dX3[3] - dX3[0] + 6.0 * dr3) / 3.0
    dX4 = {p: KAPPA * (g1 ** 2 * VMV_RR[p]
                       + 2 * g1 * (g1 * MVV_RR[p] - g1 * Vpp[p] * MV_R2[p] - 0.25 * MV_PR2[p])) for p in P}
    direct = Pi(dX4)
    via_g3 = 2 * g1 * dg3 * Pi(VV_R)
    return dict(L=2 * np.arange(N + 1), dC4=direct + via_g3, direct=direct, via_g3=via_g3, dg3=dg3, dr3=dr3,
                dC3=Pi(dX3), mid=Pi({p: KAPPA * g1 ** 2 * VMV_RR[p] for p in P}),
                ends=Pi({p: KAPPA * 2 * g1 * (g1 * MVV_RR[p] - g1 * Vpp[p] * MV_R2[p] - 0.25 * MV_PR2[p])
                         for p in P}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, default=200)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r = compute(a.Lmax)
    for L in (2, 4, 10, 20, 50, 100, 200, 400, 1000, 2000):
        if L <= a.Lmax:
            i = L // 2
            print(f"L={L:5d} dC4={r['dC4'][i]:+.10f} direct={r['direct'][i]:+.10f} (mid {r['mid'][i]:+.8f} "
                  f"ends {r['ends'][i]:+.8f}) via_g3={r['via_g3'][i]:+.10f} dg3={r['dg3'][i]:+.8f} "
                  f"dC3={r['dC3'][i]:+.1e}", flush=True)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        np.savez(a.out, **r)


if __name__ == "__main__":
    main()
