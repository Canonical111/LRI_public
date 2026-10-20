#!/usr/bin/env python3
"""Variant of nm_window.py in which the chi-sunset window uses the exact removed sunset sum instead of its
asymptotic slope:  D(s -> s') = -(g1^2/3) [T_M(sigma_s) + T_M(sigma_s')] M'_{s's},
    T_M(sigma) = (1/2) sum_{d = -1, +1} sum_{M - sigma < sigma' <= M} R_3(sigma') / ((d + 3)/2 + 2 sigma')
(the two zero-mode sunset orderings averaged; T_M(sigma) -> (2/pi) sigma for M -> inf).  Because the weight depends
on M = L/2 explicitly, each cutoff is a separate evaluation.  usage: python3 nm_window_exact.py 100 200 400"""
import sys
import numpy as np
import c4lib as lib
import nm_window as nw


def chain_wfun(kinds, slice_ops, N, ser, mvert, wslices, wfun, ps=(0, 1, 2, 3)):
    res = {p: 0.0 for p in ps}
    K = len(kinds)
    old = lib.slice_G
    for n in lib.patterns(kinds):
        if lib.legs_of(n, K)[mvert] == 0:
            continue
        for ws in wslices:
            r = nw.chain_pattern_w(kinds, slice_ops, n, N, ser, ws, ps)
            if r is None:
                continue
            for p in ps:
                res[p] += r[p][N]
    return res


def compute_at(M):
    N = M
    ser = lib.Series(N)
    R3 = lib.two_vertex_density(3, 0, 0, ser)
    sig = np.arange(N + 1)
    inc = np.zeros(N + 1)
    for d in (-1, 1):
        den = (d + 3) / 2.0 + 2.0 * sig
        t = np.zeros(N + 1)
        t[2 * sig >= 3] = R3[2 * sig >= 3] / den[2 * sig >= 3]
        inc += 0.5 * t
    cum = np.concatenate([[0.0], np.cumsum(inc)])          # cum[k] = sum_{sigma' < k}
    T = np.array([cum[M + 1] - cum[M - s + 1] for s in range(N + 1)])   # sum over (M - s, M]
    # weight on a slice = T(sigma) * (pi/2) / sigma relative to the linear form -> implement by replacing the
    # sigma factor in nm_window.chain_pattern_w with T*(pi/2)
    orig = np.arange
    wt = T * (np.pi / 2.0)

    def chain_pattern_T(kinds, slice_ops, n, N_, ser_, wslice, ps=(0, 1, 2, 3)):
        return _cpT(kinds, slice_ops, n, N_, ser_, wslice, wt, ps)

    nw.chain_pattern_w_saved = nw.chain_pattern_w
    nw.chain_pattern_w = chain_pattern_T
    try:
        r = nw.compute(2 * M)
    finally:
        nw.chain_pattern_w = nw.chain_pattern_w_saved
    return {k: (v[M] if isinstance(v, np.ndarray) and v.ndim == 1 and len(v) == M + 1 else v) for k, v in r.items()}


def _cpT(kinds, slice_ops, n, N, ser, wslice, wt, ps):
    """copy of nm_window.chain_pattern_w with weight wt[sigma] instead of sigma (only the value at max cutoff
    N is used by the caller)."""
    from fractions import Fraction as Fr
    from math import factorial
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
    if not keyamp or nsl[wslice] == 0:
        return None
    Ns = [N if nsl[s_] > 0 else 0 for s_ in range(K - 1)]
    R = lib.density(K, n, ser, Ns)
    keys = list(keyamp)
    Gs = []
    for s_ in range(K - 1):
        pw = slice_ops[s_][0]
        G = np.array([lib.slice_G((k[s_] + nsl[s_]) / 2.0, pw, nsl[s_], Ns[s_] + 1) for k in keys])
        if s_ == wslice:
            G = G * wt[None, : Ns[s_] + 1]
        Gs.append(G)
    sh = lib.shell_sums(R, Gs, N)
    cum = np.cumsum(sh, axis=1)
    res = {p: np.zeros(N + 1) for p in ps}
    for t, k in enumerate(keys):
        for p, a in keyamp[k].items():
            res[p] += float(a) * cum[t]
    return res


if __name__ == "__main__":
    lin = np.load("results/nm_L400.npz")
    for L in [int(x) for x in sys.argv[1:]]:
        r = compute_at(L // 2)
        print(f"L={L:5d} exact-sum dC4={r['dC4']:+.10f}  linear dC4={lin['dC4'][L // 2]:+.10f}  "
              f"diff={r['dC4'] - lin['dC4'][L // 2]:+.3e}", flush=True)
