#!/usr/bin/env python3
"""Diagnostic (exact Fractions): eps^2, eps^3 descendant residuals of chi_aa = A^dag_aa|0> in scheme Wc, with an
optional BUDGET-FREE external line: in the chi_aa channel, up to two quanta of mode (a,a) do not count towards the
level cutoff (states allowed iff level - 2a min(n_aa, 2) <= L), and the windows acting in the chi channel use the
same budget level.  Primaries and auxiliary channels are those of Wc (brute_desc.py).  With --bf the self-offsets of
the external line (its own level in its own self-energy, and as a spectator of other sub-processes) are absent; the
residual that remains is not a level-offset effect of the external line.
usage: python3 brute_desc_bf.py --L 6 --a 1 [--bf]"""
import argparse
import json
import os
import sys
import time
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brute_W5 as bw  # noqa: E402

rf = bw.rf
G1 = Fr(1, 3)


def run(L, a, bf, K=8, verbose=True, scheme="Wc"):
    rf.ORD = 5
    bw.ORD = 5
    t0 = time.time()
    spaces, ops, Mp = {}, {}, {}
    for par in (0, 1):
        sp = rf.Space(L, par, bw.ZMAX + K)
        ctup = rf.ordered_creation_tuples(sp, 4)
        ops[par] = {"M": rf.build_vertex(sp, 2, Fr(1), ctup), "V": rf.build_vertex(sp, 4, Fr(1, 12), ctup)}
        Mp[par] = bw.build_Mprime_poly(sp, ctup)
        spaces[par] = sp
    # chi channel space (extended when budget-free)
    Lx = L + (4 * a if bf else 0)
    if bf:
        spx = rf.Space(Lx, 1, bw.ZMAX + K)
        ctx = rf.ordered_creation_tuples(spx, 4)
        opsx = {"M": rf.build_vertex(spx, 2, Fr(1), ctx), "V": rf.build_vertex(spx, 4, Fr(1, 12), ctx)}
        Mpx = bw.build_Mprime_poly(spx, ctx)
    else:
        spx, opsx, Mpx = spaces[1], ops[1], Mp[1]
    maa = spx.midx[(a, a)]

    def blev_x(i):
        if not bf:
            return spx.level[i]
        n = dict(spx.states[i]).get(maa, 0)
        return spx.level[i] - 2 * a * min(n, 2)

    if verbose:
        print(f"# spaces built t={time.time() - t0:.1f}s (chi space L={Lx}, {len(spx.states)} states)", flush=True)
    ls = list(range(0, L + 1, 2))
    zero = lambda k, N: 0
    chi = spx.index[((maa, 1),)]
    r = [Fr(0)] * 6
    g = [Fr(0)] * 6
    g[1] = G1
    xser = [Fr(1, 2), Fr(-1, 4)] + [Fr(0)] * 4
    aux = {(z, l): bw.DChannel(f"z{z}l{l}", spaces[z % 2], ops[z % 2], z, l, K, zero, drop_degenerate=True,
                               bequation=False)
           for z in range(bw.ZMAX + 1) for l in ls}
    prim = {p: bw.DChannel(f"p{p}", spaces[p % 2], ops[p % 2], p, L, K, zero) for p in range(4)}
    ch = bw.DChannel("chi", spx, opsx, 1, Lx, K, zero, drop_degenerate=True, bequation=True)
    if bf:
        ch.allowed = [blev_x(i) <= L and spx.P[i] <= 1 + K for i in range(len(spx.states))]
    ch.ref = chi
    ch.E0ref = Fr(1, 2) + 2 * a
    ch.psi = [{chi: Fr(1)}]
    ch.E = [ch.E0ref]
    h = {}

    def tune(n):
        rhs0 = {p: prim[p].rhs_without_new(n, r, g) for p in range(4)}
        X = {p: rhs0[p].get(prim[p].ref, Fr(0)) for p in range(4)}
        r[n] = (xser[n] - X[1] + X[0]) / 2
        g[n] = (-xser[n] - X[3] + X[0] - 6 * r[n]) / 3
        for p in range(4):
            prim[p].finish_order(n, rhs0[p], r[n], g[n])

    for c_ in aux.values():
        c_.finish_order(1, c_.rhs_without_new(1, r, g), r[1], g[1])
    for (z, l), c_ in aux.items():
        rhs2 = c_.rhs_without_new(2, r, g)
        for zp in range(z % 2, bw.ZMAX + 1, 2):
            h[(zp, z, l)] = rhs2.get(spaces[z % 2].ref_index(zp), Fr(0))

    def c1_2(l):
        return h[(1, 1, l)] - h[(0, 0, l)]

    def make_D2(l, sp, cols, lev, lref):
        def apply(vec):
            o = {}
            for c, v in vec.items():
                N = lev(c)
                if N <= 0:
                    continue
                st = dict(sp.states[c])
                z = st.get(0, 0)
                if z <= bw.ZMAX:
                    for zp in range(z % 2, bw.ZMAX + 1, 2):
                        d = h[(zp, z, l)] - h[(zp, z, l - N)]
                        if d == 0:
                            continue
                        st2 = dict(st)
                        if zp:
                            st2[0] = zp
                        else:
                            st2.pop(0, None)
                        j = sp.index.get(tuple(sorted(st2.items())))
                        if j is not None:
                            o[j] = o.get(j, 0) + d * v
            for c, v in vec.items():
                N = lev(c)
                for (row, pol) in cols[c]:
                    Nr = lev(row)
                    if Nr > l:
                        continue
                    w = Fr(1, 4) * ((c1_2(lref) - c1_2(l - Nr)) + (c1_2(lref) - c1_2(l - N)))
                    if w and pol[0]:
                        o[row] = o.get(row, 0) + w * pol[0] * v
            return o
        return apply

    lev_std = lambda par: (lambda i: spaces[par].level[i])
    for p in range(4):
        prim[p].Dops = {2: make_D2(L, spaces[p % 2], Mp[p % 2], lev_std(p % 2), L)}
    ch.Dops = {2: make_D2(L, spx, Mpx, blev_x, L)}
    for n in (1, 2):
        tune(n)
        ch.finish_order(n, ch.rhs_without_new(n, r, g), r[n], g[n])
    for (z, l), c_ in aux.items():
        c_.Dops = {2: make_D2(l, spaces[z % 2], Mp[z % 2], lev_std(z % 2), L if scheme == "Wc" else l)}
        c_.finish_order(2, c_.rhs_without_new(2, r, g), r[2], g[2])
    for (z, l), c_ in aux.items():
        if z < 8:
            c_.finish_order(3, c_.rhs_without_new(3, r, g), Fr(0), Fr(0))
    h3 = {}
    for l in ls:
        for z in range(7):
            sp = spaces[z % 2]
            c_ = aux[(z, l)]
            idx = lambda zz: sp.ref_index(zz)
            X = {n_: {zz: c_.psi[n_].get(idx(zz), Fr(0)) for zz in range(z % 2, bw.ZMAX + 1, 2) if zz != z}
                 for n_ in (1, 2, 3)}

            def h1m(zp, zz):
                w = c_.matvec("V", 0, {idx(zz): Fr(1)})
                return G1 * w.get(idx(zp), Fr(0)) + (Fr(-zz, 4) if zp == zz else 0)
            for zp in range(z % 2, 7, 2):
                v = (Fr(z - zp, 2) * X[3][zp] + c_.E[1] * X[2][zp] + c_.E[2] * X[1][zp]) if zp != z else c_.E[3]
                for zz in range(z % 2, bw.ZMAX + 1, 2):
                    if zz == z:
                        continue
                    hz = h1m(zp, zz)
                    if hz:
                        v -= hz * X[2][zz]
                    if X[1][zz]:
                        v -= h[(zp, zz, l)] * X[1][zz]
                h3[(zp, z, l)] = v

    def c1_3(l):
        return aux[(1, l)].E[3] - aux[(0, l)].E[3]

    def make_D3(l, sp, cols, lev):
        def apply(vec):
            o = {}
            for c, v in vec.items():
                N = lev(c)
                if N <= 0:
                    continue
                z = dict(sp.states[c]).get(0, 0)
                if z <= 6:
                    st = dict(sp.states[c])
                    for zp in range(z % 2, 7, 2):
                        d = h3[(zp, z, l)] - h3[(zp, z, l - N)]
                        if d == 0:
                            continue
                        st2 = dict(st)
                        if zp:
                            st2[0] = zp
                        else:
                            st2.pop(0, None)
                        j = sp.index.get(tuple(sorted(st2.items())))
                        if j is not None:
                            o[j] = o.get(j, 0) + d * v
            for c, v in vec.items():
                N = lev(c)
                for (row, pol) in cols[c]:
                    Nr = lev(row)
                    if Nr > l:
                        continue
                    w3 = Fr(1, 4) * ((c1_3(l) - c1_3(l - Nr)) + (c1_3(l) - c1_3(l - N)))
                    w2 = Fr(1, 4) * ((c1_2(l) - c1_2(l - Nr)) + (c1_2(l) - c1_2(l - N)))
                    val = w3 * pol[0] + w2 * pol[1]
                    if val:
                        o[row] = o.get(row, 0) + val * v
            return o
        return apply

    for p in range(4):
        prim[p].Dops[3] = make_D3(L, spaces[p % 2], Mp[p % 2], lev_std(p % 2))
    ch.Dops[3] = make_D3(L, spx, Mpx, blev_x)
    tune(3)
    ch.finish_order(3, ch.rhs_without_new(3, r, g), r[3], g[3])
    R = [ch.E[n] - prim[1].E[n] for n in range(4)]
    R[0] -= 2 * a
    if verbose:
        print(f"# L={L} a={a} bf={bf}: R_2 = {float(R[2]):+.12f}  R_3 = {float(R[3]):+.12f}  t={time.time() - t0:.1f}s",
              flush=True)
    return {"L": L, "a": a, "bf": bf, "R": [str(x) for x in R], "R_float": [float(x) for x in R]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--a", type=int, default=1)
    ap.add_argument("--bf", action="store_true")
    ap.add_argument("--out", default=None)
    x = ap.parse_args()
    res = run(x.L, x.a, x.bf)
    if x.out:
        json.dump(res, open(x.out, "w"), indent=1)
