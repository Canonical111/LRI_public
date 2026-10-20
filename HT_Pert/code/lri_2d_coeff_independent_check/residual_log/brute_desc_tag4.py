#!/usr/bin/env python3
"""Scheme Wcs (WINDOW_SPEC Sec. 2.5a) in exact brute force with TAGGED descendant channels, through eps^4.

Same construction as brute_desc_tag.py (tagged external line of chi_aa, glued RS), plus:
  * delta^(3)(L) computed in the same run from the zero-mode-tagged phi channel (charges 2, 2);
  * D^(3) of the primaries and of the tagged chi channels includes (delta^(3)/2) X_0 (X = M'^{+-}_nu, leg levels =
    budget levels, i.e. a budget-free tag has leg level 0);
  * primaries and tagged chi channels are carried to eps^4.  No eps^4 window is included: for budget-free tags none
    acts on the reference at first order (D^zm and D^M vanish for budget level 0), so the budget-free R_4 is
    complete; the charged R_4 lacks <chi|D^(4)|chi> and must equal ce_wc scheme 'Wcs3' (D^(k >= 4) off).
R_n = [eps^n] (E(chi_aa) - E(phi) - 2a), n = 2, 3, 4.
usage: python3 brute_desc_tag4.py --L 6 --a 1 --nu 2,2 --nu 0,0 [--nodelta] [--out x.json]"""
import argparse
import json
import os
import sys
import time
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brute_W5 as bw  # noqa: E402
import brute_desc_tag as bt  # noqa: E402
import brute_legw as bl  # noqa: E402

rf = bw.rf
G1 = Fr(1, 3)


def run(L, a, nus, K=8, verbose=True, with_delta=True, delta4=False):
    rf.ORD = 5
    bw.ORD = 5
    t0 = time.time()
    spaces, ops, Mp, Xp = {}, {}, {}, {}
    for par in (0, 1):
        sp = rf.Space(L, par, bw.ZMAX + K)
        ctup = rf.ordered_creation_tuples(sp, 4)
        ops[par] = {"M": rf.build_vertex(sp, 2, Fr(1), ctup), "V": rf.build_vertex(sp, 4, Fr(1, 12), ctup)}
        Mp[par] = bw.build_Mprime_poly(sp, ctup)
        Xp[par] = bl.build_Xnu(sp, ctup, poly=True)
        spaces[par] = sp
    if verbose:
        print(f"# regular spaces built t={time.time() - t0:.1f}s", flush=True)
    ls = list(range(0, L + 1, 2))
    zero = lambda k, N: 0
    r = [Fr(0)] * 6
    g = [Fr(0)] * 6
    g[1] = G1
    xser = [Fr(1, 2), Fr(-1, 4)] + [Fr(0)] * 4
    aux = {(z, l): bw.DChannel(f"z{z}l{l}", spaces[z % 2], ops[z % 2], z, l, K, zero, drop_degenerate=True,
                               bequation=False)
           for z in range(bw.ZMAX + 1) for l in ls}
    prim = {p: bw.DChannel(f"p{p}", spaces[p % 2], ops[p % 2], p, L, K, zero) for p in range(4)}
    tags = {}
    for nu in nus:
        tsp = bt.TagSpace(L, a, nu[0], nu[1], 1 + K)
        tct = bt.tag_creation_tuples(tsp, 4)
        tops = {"M": bt.build_tag_op(tsp, tct, 2, Fr(1)), "V": bt.build_tag_op(tsp, tct, 4, Fr(1, 12))}
        tMp = bt.build_tag_op(tsp, tct, 2, Fr(1), prime=True)
        tX = bt.build_tag_op(tsp, tct, 2, Fr(1), prime=True, legw=True)
        tags[nu] = (tsp, tops, tMp, tX, bt.TagChannel(tsp, tops, a, K))
        if verbose:
            print(f"# tagged chi space nu={nu}: {len(tsp.states)} states, t={time.time() - t0:.1f}s", flush=True)
    psp = bt.TagSpace(L, 0, 2, 2, 1 + K, zero_like_tags=True)
    pct = bt.tag_creation_tuples(psp, 4)
    pops = {"M": bt.build_tag_op(psp, pct, 2, Fr(1)), "V": bt.build_tag_op(psp, pct, 4, Fr(1, 12))}
    pMp = bt.build_tag_op(psp, pct, 2, Fr(1), prime=True)
    pch = bt.TagChannel(psp, pops, 0, K)
    # zero-charge proxy (diagnostic for eps^4: equals the phi channel except that D^zm treats the tagged line as a
    # spectator instead of a zero mode)
    p0sp = bt.TagSpace(L, 0, 0, 0, 1 + K, zero_like_tags=True) if delta4 else None
    if delta4:
        p0ct = bt.tag_creation_tuples(p0sp, 4)
        p0ops = {"M": bt.build_tag_op(p0sp, p0ct, 2, Fr(1)), "V": bt.build_tag_op(p0sp, p0ct, 4, Fr(1, 12))}
        p0Mp = bt.build_tag_op(p0sp, p0ct, 2, Fr(1), prime=True)
        p0X = bt.build_tag_op(p0sp, p0ct, 2, Fr(1), prime=True, legw=True)
        p0ch = bt.TagChannel(p0sp, p0ops, 0, K)
    if verbose:
        print(f"# phi-tagged space (2,2): {len(psp.states)} states, t={time.time() - t0:.1f}s", flush=True)
    h = {}

    def tune_rhs(n):
        rhs0 = {p: prim[p].rhs_without_new(n, r, g) for p in range(4)}
        X = {p: rhs0[p].get(prim[p].ref, Fr(0)) for p in range(4)}
        r[n] = (xser[n] - X[1] + X[0]) / 2
        g[n] = (-xser[n] - X[3] + X[0] - 6 * r[n]) / 3
        return rhs0

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
    blev = lambda s_: (lambda i: s_.blevel[i])
    for p in range(4):
        prim[p].Dops = {2: make_D2(L, spaces[p % 2], Mp[p % 2], lev_std(p % 2), L)}
    for nu, (tsp, tops, tMp, tX, ch) in tags.items():
        ch.Dops = {2: make_D2(L, tsp, tMp, blev(tsp), L)}
    pch.Dops = {2: make_D2(L, psp, pMp, blev(psp), L)}
    if delta4:
        p0ch.Dops = {2: make_D2(L, p0sp, p0Mp, blev(p0sp), L)}
    for n in (1, 2):
        rhs0 = tune_rhs(n)
        for p in range(4):
            prim[p].finish_order(n, rhs0[p], r[n], g[n])
        for nu, (tsp, tops, tMp, tX, ch) in tags.items():
            ch.finish_order(n, ch.rhs_without_new(n, r, g), r[n], g[n])
        pch.finish_order(n, pch.rhs_without_new(n, r, g), r[n], g[n])
        if delta4:
            p0ch.finish_order(n, p0ch.rhs_without_new(n, r, g), r[n], g[n])
    for (z, l), c_ in aux.items():
        c_.Dops = {2: make_D2(l, spaces[z % 2], Mp[z % 2], lev_std(z % 2), L)}
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
            Xx = {n_: {zz: c_.psi[n_].get(idx(zz), Fr(0)) for zz in range(z % 2, bw.ZMAX + 1, 2) if zz != z}
                  for n_ in (1, 2, 3)}

            def h1m(zp, zz):
                w = c_.matvec("V", 0, {idx(zz): Fr(1)})
                return G1 * w.get(idx(zp), Fr(0)) + (Fr(-zz, 4) if zp == zz else 0)
            for zp in range(z % 2, 7, 2):
                v = (Fr(z - zp, 2) * Xx[3][zp] + c_.E[1] * Xx[2][zp] + c_.E[2] * Xx[1][zp]) if zp != z else c_.E[3]
                for zz in range(z % 2, bw.ZMAX + 1, 2):
                    if zz == z:
                        continue
                    hz = h1m(zp, zz)
                    if hz:
                        v -= hz * Xx[2][zz]
                    if Xx[1][zz]:
                        v -= h[(zp, zz, l)] * Xx[1][zz]
                h3[(zp, z, l)] = v

    def c1_3(l):
        return aux[(1, l)].E[3] - aux[(0, l)].E[3]

    dl = {"v": Fr(0)}

    def make_D3(l, sp, cols, lev, xcols):
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
            if dl["v"] and xcols is not None:
                hd = dl["v"] / 2
                for c, v in vec.items():
                    for (row, pol) in xcols[c]:
                        if pol[0]:
                            o[row] = o.get(row, 0) + hd * pol[0] * v
            return o
        return apply

    for p in range(4):
        prim[p].Dops[3] = make_D3(L, spaces[p % 2], Mp[p % 2], lev_std(p % 2), Xp[p % 2])
    for nu, (tsp, tops, tMp, tX, ch) in tags.items():
        ch.Dops[3] = make_D3(L, tsp, tMp, blev(tsp), tX)
    pch.Dops[3] = make_D3(L, psp, pMp, blev(psp), None)
    # order 3: r3, g3 (independent of the delta-term), then delta from the phi-tagged channel, then everything else
    rhs0 = tune_rhs(3)
    pch.finish_order(3, pch.rhs_without_new(3, r, g), r[3], g[3])
    if delta4:
        p0ch.Dops[3] = make_D3(L, p0sp, p0Mp, blev(p0sp), None)
        p0ch.finish_order(3, p0ch.rhs_without_new(3, r, g), r[3], g[3])
    # c1tag^(3)(L; 2, 2) on the window-function footing: E_tag^(3) - E_0^(3) - 2 r_3;
    # E_0^(3) including r_3, g_3: <0|M|0> = <0|V|0> = 0, so E_0^(3) = rhs0[0][ref]
    E03 = rhs0[0].get(prim[0].ref, Fr(0))
    c1tag3 = pch.E[3] - E03 - 2 * r[3]
    delta = (c1_3(L - 2) - c1tag3) / 4
    dl["v"] = delta if with_delta else Fr(0)
    if verbose:
        print(f"# delta^(3)(L={L}) = {delta} = {float(delta):+.12f} ({'used' if with_delta else 'NOT used'})", flush=True)
    for p in range(4):
        rr = dict(rhs0[p])
        if dl["v"]:
            hd = dl["v"] / 2
            for (row, pol) in Xp[p % 2][prim[p].ref]:
                if pol[0] and prim[p].allowed[row]:
                    rr[row] = rr.get(row, 0) + hd * pol[0]
        prim[p].finish_order(3, rr, r[3], g[3])
    res = {"L": L, "a": a, "delta3": str(delta), "with_delta": with_delta}
    for nu, (tsp, tops, tMp, tX, ch) in tags.items():
        ch.finish_order(3, ch.rhs_without_new(3, r, g), r[3], g[3])
    # order 4 (no eps^4 window: see the module docstring)
    rhs0 = tune_rhs(4)
    for p in range(4):
        prim[p].finish_order(4, rhs0[p], r[4], g[4])
    for nu, (tsp, tops, tMp, tX, ch) in tags.items():
        ch.finish_order(4, ch.rhs_without_new(4, r, g), r[4], g[4])
        R = [ch.E[n] - prim[1].E[n] for n in range(5)]
        R[0] -= 2 * a
        res[f"nu{nu[0]}_{nu[1]}"] = {"R": [str(x) for x in R], "R_float": [float(x) for x in R]}
        if verbose:
            print(f"# L={L} a={a} nu={nu}: R_2 = {float(R[2]):+.12f}  R_3 = {float(R[3]):+.12f}  "
                  f"R_4 = {float(R[4]):+.12f}  t={time.time() - t0:.1f}s", flush=True)
    res["C"] = [str(prim[2].E[n] - prim[0].E[n]) for n in range(5)]
    res["r"], res["g"] = [str(x) for x in r[:5]], [str(x) for x in g[:5]]
    if delta4:
        res.update(_delta4(L, a, r, g, aux, prim, spaces, Mp, Xp, ops, h, h3, c1_2, c1_3, dl, psp, pct, pMp, pch,
                            make_D2, verbose, (p0sp, p0ct, p0Mp, p0X, p0ch)))
    return res


def _delta4(L, a, r, g, aux, prim, spaces, Mp, Xp, ops, h, h3, c1_2, c1_3, dl, psp, pct, pMp, pch, make_D2,
            verbose, p0=None):
    """delta^(4)(L) = (1/4)[c_1^(4)(L - 2) - c1tag^(4)(L; 2, 2)] (window footing, r_4 removed).
    Needs: auxiliary channels z = 0, 1 at l = L, L - 2 to order 4 (their psi_3 completed with r_3 M + g_3 V + D^(3),
    windows of rule Wc + the delta^(3) term), the Bloch h^(4)_00(l) (vacuum window of the charged tag at eps^4), and the
    phi-tagged channel to order 4 with D^(3) including the delta^(3) term on internal transitions."""
    lev_std = lambda par: (lambda i: spaces[par].level[i])
    blev = lambda s_: (lambda i: s_.blevel[i])

    def make_D3w(l, sp, cols, lev, xcols):
        # rule Wc: window differences referenced to the outer cutoff L
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
                        d = h3[(zp, z, L)] - h3[(zp, z, l - N)]
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
                    w3 = Fr(1, 4) * ((c1_3(L) - c1_3(l - Nr)) + (c1_3(L) - c1_3(l - N)))
                    w2 = Fr(1, 4) * ((c1_2(L) - c1_2(l - Nr)) + (c1_2(L) - c1_2(l - N)))
                    val = w3 * pol[0] + w2 * pol[1]
                    if val:
                        o[row] = o.get(row, 0) + val * v
            if dl["v"] and xcols is not None:
                hd = dl["v"] / 2
                for c, v in vec.items():
                    for (row, pol) in xcols[c]:
                        if pol[0]:
                            o[row] = o.get(row, 0) + hd * pol[0] * v
            return o
        return apply

    def complete_psi3(ch, extra):
        for row, v in extra.items():
            if not ch.allowed[row] or row == ch.ref or v == 0:
                continue
            den = ch.E0ref - ch.H0[row]
            if den == 0:
                continue
            ch.psi[3][row] = ch.psi[3].get(row, 0) + v / den

    def make_D2w(l, sp, cols, lev):
        # rule Wc at eps^2 including the zero-mode window: [h(L) - h(l - N)] and Delta c_1(L, .) (enters E^(4))
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
                        d = h[(zp, z, L)] - h[(zp, z, l - N)]
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
                    w = Fr(1, 4) * ((c1_2(L) - c1_2(l - Nr)) + (c1_2(L) - c1_2(l - N)))
                    if w and pol[0]:
                        o[row] = o.get(row, 0) + w * pol[0] * v
            return o
        return apply

    out = {}
    c14, h400 = {}, {}
    for l in (L, L - 2):
        for z in (0, 1):
            c_ = aux[(z, l)]
            sp = spaces[z % 2]
            c_.Dops = {2: make_D2w(l, sp, Mp[z % 2], lev_std(z % 2)),
                       3: make_D3w(l, sp, Mp[z % 2], lev_std(z % 2), Xp[z % 2])}
            # psi_3 anew (E^(3) kept: the window functions exclude r_3, g_3): full r_3, g_3, D^(2) and D^(3) of rule Wc
            rhs3 = c_.rhs_without_new(3, r, g)
            for opn, cf in (("M", r[3]), ("V", g[3])):
                for row, v in c_.matvec(opn, 0, c_.psi[0]).items():
                    rhs3[row] = rhs3.get(row, 0) + cf * v
            psi3 = {}
            for row, v in rhs3.items():
                if row == c_.ref or v == 0 or not c_.allowed[row]:
                    continue
                den = c_.E0ref - c_.H0[row]
                if den != 0:
                    psi3[row] = v / den
            c_.psi[3] = psi3
            c_.finish_order(4, c_.rhs_without_new(4, r, g), Fr(0), Fr(0))
        c14[l] = aux[(1, l)].E[4] - aux[(0, l)].E[4]
        # Bloch h^(4)_00(l) = E_0^(4) - sum_{z''} sum_m h^(m)_{0z''} X^(4-m)_{z''0}  (monomial frame), with the Bloch
        # h^(2)_{0z''} = rhs_2[0] (incl. r_2, g_2) + E^(1)_{z''} X^(1)_{0z''} - sum_y h^(1)_{0y} X^(1)_{yz''};
        # h^(3) of the code differs from Bloch by l-independent terms that multiply the l-independent X^(1)_{40}
        c0 = aux[(0, l)]
        sp = spaces[0]
        idx = sp.ref_index
        Xz = lambda n_, zz: c0.psi[n_].get(idx(zz), Fr(0))
        M0 = lambda zz: c0.matvec("M", 0, {idx(zz): Fr(1)}).get(idx(0), Fr(0))
        V0 = lambda zz: c0.matvec("V", 0, {idx(zz): Fr(1)}).get(idx(0), Fr(0))
        v = c0.E[4]
        for zz in range(2, bw.ZMAX + 1, 2):
            h1 = G1 * V0(zz)
            cz = aux[(zz, l)]
            X1c = lambda y: cz.psi[1].get(idx(y), Fr(0))
            h2 = h[(0, zz, l)] + r[2] * M0(zz) + g[2] * V0(zz) + cz.E[1] * X1c(0)
            for y in range(0, bw.ZMAX + 1, 2):
                if y != zz:
                    h2 -= G1 * V0(y) * X1c(y)
            h3f = (h3.get((0, zz, l), Fr(0)) + r[3] * M0(zz) + g[3] * V0(zz)) if zz <= 6 else None
            x1, x2, x3 = Xz(1, zz), Xz(2, zz), Xz(3, zz)
            if x1 and h3f is None:
                raise RuntimeError("h^(3) needed beyond z = 6")
            v -= h1 * x3 + h2 * x2 + (h3f * x1 if x1 else 0)
        h400[l] = v
    out["c1_4"] = {str(l): str(c14[l]) for l in c14}
    out["h4_00"] = {str(l): str(h400[l]) for l in h400}
    # phi-tagged channel to order 4
    pX = bt.build_tag_op(psp, pct, 2, Fr(1), prime=True, legw=True)
    pch.Dops[3] = make_D3w(L, psp, pMp, blev(psp), pX)
    if dl["v"]:
        ex = {}
        hd = dl["v"] / 2
        for (row, pol) in pX[pch.ref]:
            if pol[0] and row not in pch.model:
                ex[row] = ex.get(row, 0) + hd * pol[0]
        complete_psi3(pch, ex)
    rhs4 = pch.rhs_without_new(4, r, g)
    rhs4[pch.ref] = rhs4.get(pch.ref, Fr(0)) + (h400[L] - h400[L - 2])      # D^zm,(4) on |X_in> (budget level 2)
    pch.finish_order(4, rhs4, r[4], g[4])
    c1tag4 = pch.E[4] - prim[0].E[4] - 2 * r[4]
    if p0 is not None:
        p0sp, p0ct, p0Mp, p0X, p0ch = p0
        p0ch.Dops[3] = make_D3w(L, p0sp, p0Mp, blev(p0sp), p0X)
        if dl["v"]:
            ex = {}
            hd = dl["v"] / 2
            for (row, pol) in p0X[p0ch.ref]:
                if pol[0] and row not in p0ch.model:
                    ex[row] = ex.get(row, 0) + hd * pol[0]
            complete_psi3(p0ch, ex)
        p0ch.finish_order(4, p0ch.rhs_without_new(4, r, g), r[4], g[4])
        # zero charge: no D^zm,(4) on |X_in> (budget level 0).  c1tag^(4)(L; 0, 0) - c_1^(4)(L) (= 0 at eps^<=3):
        d00 = p0ch.E[4] - prim[0].E[4]
        out["c1tag4_00_minus_c1_4"] = str(d00)
        out["c1tag3_00_minus_c1_3"] = str(p0ch.E[3] - prim[0].E[3])
        if verbose:
            print(f"# zero-charge proxy: c1tag^(3)(L;0,0) - c_1^(3)(L) = {float(p0ch.E[3] - prim[0].E[3]):+.3e};  "
                  f"c1tag^(4)(L;0,0) - c_1^(4)(L) = {float(d00):+.12f}", flush=True)
    d4 = (c14[L - 2] - c1tag4) / 4
    out["delta4"] = str(d4)
    out["c1tag4"] = str(c1tag4)
    w = rf.poch_over_fact(a)
    w0, w1 = w[0] ** 2, 2 * w[0] * w[1]
    out["R4_correction_chi"] = str(4 * a * (w0 * d4 + w1 * Fr(dl["v"])))
    if verbose:
        print(f"# delta^(4)(L={L}) = {float(d4):+.12f};  c1_4(L-2) = {float(c14[L - 2]):+.10f}  c1tag'_4 = "
              f"{float(c1tag4):+.10f};  R_4 correction for chi_{a}{a}: {float(Fr(out['R4_correction_chi'])):+.10f}",
              flush=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--a", type=int, default=1)
    ap.add_argument("--nu", action="append", default=None)
    ap.add_argument("--nodelta", action="store_true")
    ap.add_argument("--delta4", action="store_true", help="also delta^(4)(L) (eps^4 leg window)")
    ap.add_argument("--out", default=None)
    x = ap.parse_args()
    nus = [tuple(int(t) for t in s.split(",")) for s in (x.nu or [f"{2 * x.a},{2 * x.a}", "0,0"])]
    res = run(x.L, x.a, nus, with_delta=not x.nodelta, delta4=x.delta4)
    if x.out:
        json.dump(res, open(x.out, "w"), indent=1)
