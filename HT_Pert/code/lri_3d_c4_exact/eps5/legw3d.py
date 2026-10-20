#!/usr/bin/env python3
"""S(L): response of C_5 to (1/2) X inserted at eps^3 (= response of C_4 to (1/2) X at eps^2), 3D model, so that the
Wcs window (WINDOW_SPEC 2.5a: D^(3) += (delta^(3)(L)/2) X_0) shifts C_5 by delta^(3)(L) S(L).  Port of the 2D nm_legw.py.

X = M'^{+-}_nu: every term of M' (>= 1 chi leg) weighted by s x (sum of the levels of its chi legs), s = +1 for hops
(one creator, one annihilator: chi -> chi, Z <-> chi), s = -1 for pairs (two creators or two annihilators).
A bundle's level is the sum of its lines' levels, so the weight is applied by multiplying the level array of each
bundle incident to the M' vertex by its level.  For a Z-chi vertex the hop/pair type depends on the zero-mode step
(Z created: delta rises by 1; Z annihilated: falls by 1) and on whether the chi line is absorbed or emitted.
Words (as dchi3d.py, D -> (1/2) X): eps^3: 2 g1 <V R D> (shifts r3, g3, not C3); eps^4:
g1^2 <V R D R V> + 2 g1 [g1 <V R V R D> - g1 V_pp <V R^2 D> - (1/4) <V R (P-p) R D>] + 2 g1 (dr3 <V R M> + dg3 <V R V>).
Output also by M' type (zchi_hop, zchi_pair, hop, pair_c, pair_a).
usage: python3 legw3d.py --Lmax 400 --out ../results/legw_L400.npz"""
import argparse
import os
import sys
from fractions import Fraction as Fr
from math import factorial

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import c4lib3d as lib  # noqa: E402

G = 1.0 / 3.0
TYPES = ("zchi_hop", "zchi_pair", "hop", "pair_c", "pair_a")


def vertex_type(n, K, mv, deltas):
    """M' vertex type and sign for one zero-mode key."""
    nin = sum(v for (i, j), v in n.items() if j == mv)
    nout = sum(v for (i, j), v in n.items() if i == mv)
    if nin + nout == 2:
        if nin == 1:
            return "hop", 1
        return ("pair_c", -1) if nout == 2 else ("pair_a", -1)
    if nin + nout != 1:
        return None, 0
    db = deltas[mv - 1] if mv > 0 else 0
    da = deltas[mv] if mv < K - 1 else 0
    created = (da - db) == 1
    if (nin == 1 and created) or (nout == 1 and not created):
        return "zchi_hop", 1
    return "zchi_pair", -1


def chain_X(basis, kinds, slice_ops, mv, ps=(0, 1, 2, 3)):
    """<p| ... |p> with vertex mv = (1/2) X (an M vertex with >= 1 chi leg).  Returns {type: Lin}."""
    K = len(kinds)
    S = basis.L // 2
    out = {t: lib.Lin() for t in TYPES}
    for n in lib.patterns(kinds):
        legs = lib.legs_of(n, K)
        if legs[mv] == 0:
            continue
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
                ok, fac = True, Fr(1)
                for s_ in range(K - 1):
                    if nsl[s_] == 0 and deltas[s_] == 0:
                        ok = False
                        break
                    fac *= Fr(deltas[s_] + nsl[s_]) ** slice_ops[s_][1]
                if not ok or fac == 0:
                    continue
                typ, sgn = vertex_type(n, K, mv, deltas)
                if typ is None:
                    continue
                keyamp.setdefault((deltas, typ), {}).setdefault(p, Fr(0))
                keyamp[(deltas, typ)][p] += combf * vc * amp * fac * sgn * Fr(1, 2)
        keyamp = {k: d for k, d in keyamp.items() if any(v != 0 for v in d.values())}
        if not keyamp:
            continue
        Ss = [S if nsl[s_] > 0 else 0 for s_ in range(K - 1)]
        # level-weighted density: sum over bundles incident to mv
        full = np.zeros(tuple([S + 1] * (K - 1)))
        lev = np.arange(basis.L + 1, dtype=float)[:, None]
        for e in [e for e in lib.pairs_of(K) if mv in e and n[e] > 0]:
            betas = {f: basis.bundle(n[f], 0, 0) for f in lib.pairs_of(K)}
            betas[e] = betas[e] * lev
            lib.density_add(basis, K, betas, S, full)
        R = np.ascontiguousarray(full[tuple(slice(0, x + 1) for x in Ss)])
        keys = list(keyamp)
        Gs = [np.array([lib.slice_G(k[0][s_], nsl[s_], slice_ops[s_][0], Ss[s_] + 1) for k in keys])
              for s_ in range(K - 1)]
        sh = lib.shell_sums(R, Gs, S)
        cum = np.cumsum(sh, axis=1)
        for t, k in enumerate(keys):
            out[k[1]].add([keyamp[k].get(p, Fr(0)) for p in range(4)], cum[t])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    B = lib.Basis(a.Lmax)
    S = a.Lmax // 2
    PI, R_OF, G_OF = lib.PI, lib.R_OF, lib.G_OF
    Vpp = lambda p: Fr(p * (p - 1), 2)
    z = lambda v: v if v is not None else np.zeros(S + 1)
    VV_R = lib.chain_entries(B, "VV", [(1, 0)])
    MV_R = lib.chain_entries(B, "MV", [(1, 0)])
    res = {}
    for t in TYPES + ("total",):
        res[t] = np.zeros(S + 1)
    parts = {}
    VRD = chain_X(B, "MV", [(1, 0)], 0)
    VRDRV = chain_X(B, "VMV", [(1, 0), (1, 0)], 1)
    VRVRD = chain_X(B, "MVV", [(1, 0), (1, 0)], 0)
    VR2D = chain_X(B, "MV", [(2, 0)], 0)
    VRPRD = chain_X(B, "MV", [(2, 1)], 0)
    for t in TYPES:
        dX3 = VRD[t].scale(2 * G)
        dr3, dg3 = z(dX3.proj(R_OF)), z(dX3.proj(G_OF))
        dX4 = (VRDRV[t].scale(G * G) + VRVRD[t].scale(2 * G * G) + VR2D[t].pfac(lambda p: -Vpp(p)).scale(2 * G * G)
               + VRPRD[t].scale(-0.5 * G) + MV_R.scale(2 * G * dr3) + VV_R.scale(2 * G * dg3))
        res[t] = z(dX4.proj(PI))
        res["total"] += res[t]
        parts[t + "_dC3"] = z(dX3.proj(PI))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    np.savez(a.out, L=2 * np.arange(S + 1), S=res["total"], **{f"S_{t}": res[t] for t in TYPES}, **parts)
    print("max |dC3| over types (must vanish): %.1e" % max(np.max(np.abs(v)) for v in parts.values()))
    for j in list(range(0, S + 1, max(1, S // 12))):
        print(f"L={2 * j:5d} S={res['total'][j]:+.10f} " + " ".join(f"{t}={res[t][j]:+.6f}" for t in TYPES))


if __name__ == "__main__":
    main()
