#!/usr/bin/env python3
"""Exact (Fraction) descendant-identity residuals through eps^3 for d dbar phi = chi_11 (level 2, P = 1):
    R_n(L) = [eps^n] ( E(chi_11) - E(phi) - 2 ),   phi = |1>,   n = 2, 3,
in the schemes raw, consistent, zeromode (state-diagonal), W2, W3m, Wb (WINDOW_SPEC components, Bloch DZ3 without
partner terms) W3e (= W3m + eigenvalue-diagonal D^zm,(3), E_z^(3)(L) - E_z^(3)(L-N), B-equation in the channels) and WbV = Wb + D^V,(2) (scheme W+V; D^V,(3) does not enter R_3: <chi|V'|chi> = <p|V'|p> = 0) -- all windows built as explicit operators exactly as in brute_W5.py.  chi_11 is degenerate with |5>
(G = -3/7); its channel uses the B-equation.  The windows act on chi_11 itself (level 2): <chi|D_k|chi> enters at eps^k.
usage: python3 brute_desc.py --L 8 [--schemes raw,consistent,zeromode,W2,W3m,Wb] [--out x.json]"""
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
ORD = 3


def run(L, schemes, K=8, verbose=True):
    rf.ORD = 5
    bw.ORD = 5
    t0 = time.time()
    spaces, ops, Mp, Vp = {}, {}, {}, {}
    for par in (0, 1):
        sp = rf.Space(L, par, bw.ZMAX + K)
        ctup = rf.ordered_creation_tuples(sp, 4)
        ops[par] = {"M": rf.build_vertex(sp, 2, Fr(1), ctup), "V": rf.build_vertex(sp, 4, Fr(1, 12), ctup)}
        Mp[par] = bw.build_Mprime_poly(sp, ctup)
        Vp[par] = bw.build_prime_poly(sp, ctup, 4, Fr(1, 12)) if any(x.endswith("V") for x in schemes) else None
        spaces[par] = sp
    ls = list(range(0, L + 1, 2))
    zero = lambda k, N: 0
    sp1 = spaces[1]
    chi = sp1.index[((sp1.midx[(1, 1)], 1),)]
    out = {"L": L}
    for scheme in schemes:
        r = [Fr(0)] * 6
        g = [Fr(0)] * 6
        g[1] = G1
        xser = [Fr(1, 2), Fr(-1, 4)] + [Fr(0)] * 4
        aux = {(z, l): bw.DChannel(f"z{z}l{l}", spaces[z % 2], ops[z % 2], z, l, K, zero, drop_degenerate=True,
                                   bequation=(scheme not in ("Wb", "WbV", "Wc")))
               for z in range(bw.ZMAX + 1) for l in ls}
        prim = {p: bw.DChannel(f"p{p}", spaces[p % 2], ops[p % 2], p, L, K, zero) for p in range(4)}
        ch = bw.DChannel("chi11", sp1, ops[1], 1, L, K, zero, drop_degenerate=True, bequation=True)
        ch.ref = chi
        ch.E0ref = Fr(5, 2)
        ch.psi = [{chi: Fr(1)}]
        ch.E = [Fr(5, 2)]
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
        Wsch = scheme.startswith("W")

        def c1_2(l):
            return h[(1, 1, l)] - h[(0, 0, l)]

        def c2_2(l):
            return h[(2, 2, l)] - 2 * h[(1, 1, l)] + h[(0, 0, l)]
        withV = scheme.endswith("V")

        def make_D2(l, par):
            sp = spaces[par]
            cols = Mp[par]

            def apply(vec):
                o = {}
                for c, v in vec.items():
                    N = sp.level[c]
                    if N == 0 or scheme == "raw":
                        continue
                    st = dict(sp.states[c])
                    z = st.get(0, 0)
                    if scheme == "consistent":
                        o[c] = o.get(c, 0) + (h[(0, 0, l)] - h[(0, 0, l - N)]) * v
                        continue
                    if scheme == "zeromode":
                        if z <= bw.ZMAX:
                            o[c] = o.get(c, 0) + (h[(z, z, l)] - h[(z, z, l - N)]) * v
                        continue
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
                    if not Wsch:
                        break
                    N = sp.level[c]
                    for (row, pol) in cols[c]:
                        if sp.level[row] > l:
                            continue
                        lr = L if scheme == "Wc" else l   # Wc: auxiliary windows referenced to the outer cutoff L
                        w = Fr(1, 4) * ((c1_2(lr) - c1_2(l - sp.level[row])) + (c1_2(lr) - c1_2(l - N)))
                        if w and pol[0]:
                            o[row] = o.get(row, 0) + w * pol[0] * v
                for c, v in vec.items():
                    if not withV:
                        break
                    N = sp.level[c]
                    for (row, pol) in Vp[par][c]:
                        if sp.level[row] > l:
                            continue
                        w = Fr(1, 2) * ((c2_2(l) - c2_2(l - sp.level[row])) + (c2_2(l) - c2_2(l - N)))
                        if w and pol[0]:
                            o[row] = o.get(row, 0) + w * pol[0] * v
                return o
            return apply

        for p in range(4):
            prim[p].Dops = {2: make_D2(L, p % 2)}
        ch.Dops = {2: make_D2(L, 1)}
        for n in (1, 2):
            tune(n)
            ch.finish_order(n, ch.rhs_without_new(n, r, g), r[n], g[n])
        # aux to order 3 with their own D_2,l (diagonal schemes: windows enter E_z at order >= 4, harmless)
        for (z, l), c_ in aux.items():
            c_.Dops = {2: make_D2(l, z % 2)}
            c_.finish_order(2, c_.rhs_without_new(2, r, g), r[2], g[2])
        need3 = list(range(8))
        for (z, l), c_ in aux.items():
            if z in need3:
                c_.finish_order(3, c_.rhs_without_new(3, r, g), Fr(0), Fr(0))
        # third-order windows
        h3 = {}
        if scheme in ("Wb", "WbV", "Wc"):
            for l in ls:
                for z in range(7):
                    sp = spaces[z % 2]
                    c_ = aux[(z, l)]
                    idx = lambda zz: sp.ref_index(zz)
                    X = {n_: {zz: c_.psi[n_].get(idx(zz), Fr(0)) for zz in range(z % 2, bw.ZMAX + 1, 2) if zz != z}
                         for n_ in (1, 2, 3)}

                    def h1m(zp, zz):
                        w = c_.matvec("V", 0, {idx(zz): Fr(1)})
                        val = G1 * w.get(idx(zp), Fr(0))
                        return val + (Fr(-zz, 4) if zp == zz else 0)
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

        def make_D3(l, par):
            sp = spaces[par]
            cols = Mp[par]

            def apply(vec):
                o = {}
                for c, v in vec.items():
                    N = sp.level[c]
                    if N == 0 or scheme in ("raw", "W2"):
                        continue
                    z = dict(sp.states[c]).get(0, 0)
                    if scheme == "consistent":
                        o[c] = o.get(c, 0) + (aux[(0, l)].E[3] - aux[(0, l - N)].E[3]) * v
                    elif scheme in ("zeromode", "W3e"):
                        if z <= 7:
                            o[c] = o.get(c, 0) + (aux[(z, l)].E[3] - aux[(z, l - N)].E[3]) * v
                    elif scheme in ("Wb", "WbV", "Wc") and z <= 6:
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
                if scheme in ("W3m", "W3e", "Wb", "WbV", "Wc"):
                    for c, v in vec.items():
                        N = sp.level[c]
                        for (row, pol) in cols[c]:
                            Nr = sp.level[row]
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
            prim[p].Dops[3] = make_D3(L, p % 2)
        ch.Dops[3] = make_D3(L, 1)
        tune(3)
        ch.finish_order(3, ch.rhs_without_new(3, r, g), r[3], g[3])
        R = [ch.E[n] - prim[1].E[n] for n in range(4)]
        R[0] -= 2
        out[scheme] = {"R": [str(x) for x in R], "R_float": [float(x) for x in R]}
        if verbose:
            print(f"# {scheme}: R_2 = {float(R[2]):+.12f}  R_3 = {float(R[3]):+.12f}  t={time.time() - t0:.1f}s", flush=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--schemes", default="raw,consistent,zeromode,W2,W3m,Wb")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = run(a.L, a.schemes.split(","))
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(res, fh, indent=1)
