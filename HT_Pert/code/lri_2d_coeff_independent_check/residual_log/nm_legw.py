#!/usr/bin/env python3
"""Response of C_{k+2} to the leg-weighted, crossing-signed mass operator X inserted at eps^k (k = 2 -> C_4, k = 3 -> C_5;
the chain formula is the same, nm_window.py):

    X = M'^{+-}_nu :  every term of M' (at least one chi leg) weighted by  s * (sum of the levels of its chi legs),
                      s = +1 for hop terms (one creator, one annihilator), s = -1 for pair terms (two creators or two
                      annihilators); zero-mode legs have level 0.

The slice-resolved eps^3 window of WINDOW_SPEC Sec. 2.5a is D^M,(3) + (delta^(3)(L)/2) X_0, so its effect on C_5 is
delta^(3)(L) * S(L) with S(L) = [response of C_5 to (1/2) X at eps^3] = [response of C_4 to (1/2) X at eps^2].
Leg levels are bundle levels (holomorphic + antiholomorphic), implemented by weighting the bundle series u -> u v(u)
in the holomorphic factor (x2 for the antiholomorphic factor).  Types reported separately:
zchi_hop, zchi_pair, hop (chi-chi), pair_c, pair_a.
usage: python3 nm_legw.py --Lmax 400 --out results/legw_L400.npz"""
import argparse
import itertools
import os
from fractions import Fraction as Fr
from math import comb, factorial

import numpy as np

import c4lib as lib

g1 = 1.0 / 3.0
KX = 0.5           # D = (delta/2) X per unit delta
TYPES = ("zchi_hop", "zchi_pair", "hop", "pair_c", "pair_a")


def density_w(K, n, ser, Ns, bw):
    """sum_k c_k * 2 * rho_k^{(bw weighted)} rho_k: the J-projected density weighted by the level of bundle bw."""
    prs = lib.pairs_of(K)
    R = np.zeros(tuple(x + 1 for x in Ns))
    ranges = [range(n[b] + 1) for b in prs]
    for ks in itertools.product(*ranges):
        c = 1
        for b, kb in zip(prs, ks):
            c *= comb(n[b], kb) * (-1) ** (n[b] - kb)
        arr = {b: ser.v[kb] for b, kb in zip(prs, ks)}
        rho = lib.build_rho(K, arr, Ns)
        arr2 = dict(arr)
        arr2[bw] = ser.v[ks[prs.index(bw)]] * np.arange(ser.N + 1)
        rhow = lib.build_rho(K, arr2, Ns)
        R += 2.0 * c * rhow * rho
    lib._mask_infeasible(R, n, K, Ns)
    return R


def chain_pattern_legw(kinds, slice_ops, n, N, ser, mvert, ps=(0, 1, 2, 3)):
    """Contribution of pattern n to <p| X_K s ... s X_1 |p> with the M vertex `mvert` replaced by its X-weighted
    version.  Returns {type: {p: array}} or None."""
    K = len(kinds)
    legs = lib.legs_of(n, K)
    if legs[mvert] == 0:
        return None
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
    mb = [(b, v) for b, v in n.items() if v and mvert in b]
    created = sum(v for b, v in mb if b[0] == mvert)          # chi legs created at the M vertex
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
            if legs[mvert] == 2:
                typ = "hop" if created == 1 else ("pair_c" if created == 2 else "pair_a")
            else:
                zb = p + (deltas[mvert - 1] if mvert > 0 else 0)
                za = p + (deltas[mvert] if mvert < K - 1 else 0)
                zc = za - zb                                      # +1: zero mode created, -1: absorbed
                hop = (created == 1 and zc == -1) or (created == 0 and zc == +1)
                typ = "zchi_hop" if hop else "zchi_pair"
            keyamp.setdefault((typ, deltas), {}).setdefault(p, Fr(0))
            keyamp[(typ, deltas)][p] += combf * vc * amp * fac
    keyamp = {k: d for k, d in keyamp.items() if any(v != 0 for v in d.values())}
    if not keyamp:
        return None
    Ns = [N if nsl[s_] > 0 else 0 for s_ in range(K - 1)]
    R = None
    for b, v in mb:
        Rb = density_w(K, n, ser, Ns, b)
        R = Rb if R is None else R + Rb
    keys = list(keyamp)
    Gs = []
    for s_ in range(K - 1):
        pw = slice_ops[s_][0]
        Gs.append(np.array([lib.slice_G((k[1][s_] + nsl[s_]) / 2.0, pw, nsl[s_], Ns[s_] + 1) for k in keys]))
    sh = lib.shell_sums(R, Gs, N)
    cum = np.cumsum(sh, axis=1)
    res = {t: {p: np.zeros(N + 1) for p in ps} for t in TYPES}
    for t, k in enumerate(keys):
        sign = 1.0 if k[0] in ("hop", "zchi_hop") else -1.0
        for p, a in keyamp[k].items():
            res[k[0]][p] += sign * float(a) * cum[t]
    return res


def chain_legw(kinds, slice_ops, N, ser, mvert, ps=(0, 1, 2, 3)):
    res = {t: {p: np.zeros(N + 1) for p in ps} for t in TYPES}
    K = len(kinds)
    for n in lib.patterns(kinds):
        r = chain_pattern_legw(kinds, slice_ops, n, N, ser, mvert, ps)
        if r is None:
            continue
        for t in TYPES:
            for p in ps:
                res[t][p] += r[t][p]
    return res


def Pi(f):
    return f[2] - f[1] - (f[3] - f[0]) / 3.0


def compute(Lmax):
    N = Lmax // 2
    ser = lib.Series(N)
    P = (0, 1, 2, 3)
    Vpp = {p: p * (p - 1) / 2.0 for p in P}
    MV_R = chain_legw(["M", "V"], [(1, 0)], N, ser, 0)
    MV_R2 = chain_legw(["M", "V"], [(2, 0)], N, ser, 0)
    MV_PR2 = chain_legw(["M", "V"], [(2, 1)], N, ser, 0)
    MVV_RR = chain_legw(["M", "V", "V"], [(1, 0), (1, 0)], N, ser, 0)
    VMV_RR = chain_legw(["V", "M", "V"], [(1, 0), (1, 0)], N, ser, 1)
    VV_R = lib.chain2(["V", "V"], [0, 0], (1, 0), N, ser, P)
    out = {"L": 2 * np.arange(N + 1)}
    tot = np.zeros(N + 1)
    for t in TYPES:
        dX3 = {p: 2 * g1 * KX * MV_R[t][p] for p in P}
        dr3 = -(dX3[1] - dX3[0]) / 2.0
        dg3 = -(dX3[3] - dX3[0] + 6.0 * dr3) / 3.0
        dX4 = {p: KX * (g1 ** 2 * VMV_RR[t][p]
                        + 2 * g1 * (g1 * MVV_RR[t][p] - g1 * Vpp[p] * MV_R2[t][p] - 0.25 * MV_PR2[t][p])) for p in P}
        s = Pi(dX4) + 2 * g1 * dg3 * Pi(VV_R)
        out["S_" + t] = s
        out["dC3_" + t] = Pi(dX3)
        tot = tot + s
    out["S"] = tot
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, default=200)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r = compute(a.Lmax)
    for L in (2, 4, 6, 8, 10, 12, 14, 16, 20, 50, 100, 200, 400, 1000, 2000):
        if L <= a.Lmax:
            i = L // 2
            print(f"L={L:5d} S={r['S'][i]:+.10f}  " + "  ".join(f"{t}={r['S_' + t][i]:+.8f}" for t in TYPES), flush=True)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        np.savez(a.out, **r)


if __name__ == "__main__":
    main()
