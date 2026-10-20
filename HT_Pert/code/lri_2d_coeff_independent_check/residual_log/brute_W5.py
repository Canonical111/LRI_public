#!/usr/bin/env python3
"""Brute-force exact (Fraction) Rayleigh-Schroedinger through eps^5 for the window variants of eps5/schemeW.py:
    W2  : D_2 = DZ2 + DM2
    W3m : W2 + D_3 = DM3 = (1/4){Dc1^(3), M'_0} + (1/4){Dc1^(2), M'_1}
    W3e : W3m + DZ3diag (D_3 += E_z^(3)(L) - E_z^(3)(L-N) on the diagonal, z' = z)
    Wb  : W3m + Bloch DZ3 (scheme W of WINDOW_SPEC, partners projected out)
    Wc  : Wb with the auxiliary-channel windows referenced to the outer cutoff L (2026-10-09 correction: the channel
          at cutoff l carries D^M with Delta c_1 measured from c_1(L), i.e. it is the cluster inside a state with
          spectator level L - l)
built as explicit operators (monomial similarity frame of ../rs_exact/ref_fraction.py, imported read-only).
Self-consistency: the auxiliary channels (z, l), l = 0..L, are advanced to order 3 with their own D_2,l, so that
c1^(3)(l) = E_1^(3)(l) - E_0^(3)(l) and E_z^(3)(l) include the eps^2 windows (degenerate partners of z >= 5 are
dropped from psi_2: they do not enter E^(3)).  Primaries p = 0..3 at L to order 5.
usage: python3 brute_W5.py --L 4 [--variants W2,W3m,W3e] [--out x.json]"""
import argparse
import json
import os
import sys
import time
from fractions import Fraction as Fr
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("RS_EXACT_DIR", os.path.join(HERE, "..", "rs_exact")))
import ref_fraction as rf  # noqa: E402

ORD = 5
rf.ORD = ORD
ZMAX = 11
G1 = Fr(1, 3)


def build_Mprime_poly(sp, ctup):
    """S^-1 M' S as column lists (row, eps-polynomial), M' = M minus its pure zero-mode part."""
    cols = []
    for i, s in enumerate(sp.states):
        occ = dict(s)
        N = sp.level[i]
        P = sp.P[i]
        acc = {}
        for kc in range(3):
            ka = 2 - kc
            if P - ka + kc > sp.Pmax or ka > P:
                continue
            base = Fr(comb(2, kc))
            occ_modes = list(occ.keys())

            def ann_rec(t, cnt, coef, wpoly, Jann, levann):
                if len(t) == ka:
                    budget = sp.L - (N - levann)
                    for (lc, ct) in ctup[kc].get(Jann, ()):
                        if lc > budget:
                            continue
                        if all(m == 0 for m in t) and all(m == 0 for m in ct):
                            continue
                        new = dict(cnt)
                        for m in ct:
                            new[m] = new.get(m, 0) + 1
                        tgt = tuple(sorted((m, c) for m, c in new.items() if c))
                        j = sp.index.get(tgt)
                        if j is None:
                            continue
                        val = [coef * a for a in wpoly]
                        acc[j] = [x + y for x, y in zip(acc[j], val)] if j in acc else val
                    return
                for m in occ_modes:
                    c = cnt.get(m, 0)
                    if c == 0:
                        continue
                    cnt2 = dict(cnt)
                    cnt2[m] = c - 1
                    t.append(m)
                    ann_rec(t, cnt2, coef * c, rf.poly_mul(wpoly, sp.w[m]), Jann + sp.J[m], levann + sp.lev[m])
                    t.pop()

            ann_rec([], dict(occ), base, [Fr(1)] + [Fr(0)] * ORD, 0, 0)
        cols.append([(j, pol) for j, pol in acc.items() if any(pol)])
    return cols


def build_prime_poly(sp, ctup, kpow, prefactor):
    """S^-1 O' S as column lists (row, eps-polynomial) for O = prefactor <:phi^kpow:>_theta, O' = O minus its pure
    zero-mode part (every term with at least one ladder operator on a non-zero mode).  kpow = 2, prefactor 1 is M'."""
    cols = []
    for i, s in enumerate(sp.states):
        occ = dict(s)
        N = sp.level[i]
        P = sp.P[i]
        acc = {}
        for kc in range(kpow + 1):
            ka = kpow - kc
            if P - ka + kc > sp.Pmax or ka > P:
                continue
            base = Fr(comb(kpow, kc)) * prefactor
            occ_modes = list(occ.keys())

            def ann_rec(t, cnt, coef, wpoly, Jann, levann):
                if len(t) == ka:
                    budget = sp.L - (N - levann)
                    for (lc, ct) in ctup[kc].get(Jann, ()):
                        if lc > budget:
                            continue
                        if all(m == 0 for m in t) and all(m == 0 for m in ct):
                            continue
                        new = dict(cnt)
                        for m in ct:
                            new[m] = new.get(m, 0) + 1
                        tgt = tuple(sorted((m, c) for m, c in new.items() if c))
                        j = sp.index.get(tgt)
                        if j is None:
                            continue
                        val = [coef * a for a in wpoly]
                        acc[j] = [x + y for x, y in zip(acc[j], val)] if j in acc else val
                    return
                for m in occ_modes:
                    c = cnt.get(m, 0)
                    if c == 0:
                        continue
                    cnt2 = dict(cnt)
                    cnt2[m] = c - 1
                    t.append(m)
                    ann_rec(t, cnt2, coef * c, rf.poly_mul(wpoly, sp.w[m]), Jann + sp.J[m], levann + sp.lev[m])
                    t.pop()

            ann_rec([], dict(occ), base, [Fr(1)] + [Fr(0)] * ORD, 0, 0)
        cols.append([(j, pol) for j, pol in acc.items() if any(pol)])
    return cols


def _solve(A, b):
    """exact Gauss-Jordan."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = next(r for r in range(c, n) if M[r][c] != 0)
        M[c], M[p] = M[p], M[c]
        piv = M[c][c]
        M[c] = [v / piv for v in M[c]]
        for r in range(n):
            if r != c and M[r][c] != 0:
                f = M[r][c]
                M[r] = [a - f * bb for a, bb in zip(M[r], M[c])]
    return [M[i][n] for i in range(n)]


class DChannel(rf.Channel):
    """Channel with window operators D[k] (k = 2, 3) acting on psi_{n-k}; optional dropping of degenerate states."""

    def __init__(self, *a, Dops=None, drop_degenerate=False, bequation=True, **kw):
        super().__init__(*a, **kw)
        self.Dops = Dops or {}
        self.drop_degenerate = drop_degenerate
        self.bequation = bequation

    def rhs_without_new(self, n, r, g):
        out = super().rhs_without_new(n, r, g)
        for k, Dk in self.Dops.items():
            if n - k >= 0 and Dk is not None:
                for row, v in Dk(self.psi[n - k]).items():
                    if self.allowed[row]:
                        out[row] = out.get(row, 0) + v
        return out

    def b_equation(self, n, rhs):
        """Degenerate partners B (E0 = E0ref, != ref): solve (E^(1) - W_1^BB) psi_{n-1}^B = P_B rhs_n, add
        (W_1 - E^(1)) psi_{n-1}^B to rhs_n (../../zeromode_exact Sec. 5).  W_1 = -P/4 + g1 V_0 (frame)."""
        B = [i for i in range(len(self.sp.states)) if self.allowed[i] and i != self.ref
             and self.H0[i] == self.E0ref]
        if not B or n < 2:
            return rhs
        E1 = self.E[1]
        Bset = {b: k for k, b in enumerate(B)}
        nb = len(B)
        A = [[Fr(0)] * nb for _ in range(nb)]
        for c in B:
            col = {c: Fr(1)}
            w = self.matvec("V", 0, col)
            for r, v in w.items():
                if r in Bset:
                    A[Bset[r]][Bset[c]] -= Fr(1, 3) * v
            A[Bset[c]][Bset[c]] -= Fr(-self.sp.P[c], 4)
            A[Bset[c]][Bset[c]] += E1
        bvec = [rhs.get(b, Fr(0)) for b in B]
        x = _solve(A, bvec)
        xd = {B[k]: x[k] for k in range(nb) if x[k] != 0}
        if xd:
            add = self.matvec("V", 0, xd)
            for r, v in add.items():
                rhs[r] = rhs.get(r, 0) + Fr(1, 3) * v
            for r, v in xd.items():
                rhs[r] = rhs.get(r, 0) + (-Fr(self.sp.P[r], 4) - E1) * v
            for r, v in xd.items():
                self.psi[n - 1][r] = v
        for b in B:
            assert rhs.get(b, 0) == 0, "B part of rhs did not vanish"
        return rhs

    def finish_order(self, n, rhs0, rn, gn):
        rhs = dict(rhs0)
        if self.drop_degenerate and self.bequation:
            rhs = self.b_equation(n, rhs)
        for opname, c in (("M", rn), ("V", gn)):
            if c:
                for idx, v in self.matvec(opname, 0, {self.ref: Fr(1)}).items():
                    rhs[idx] = rhs.get(idx, 0) + c * v
        En = rhs.get(self.ref, Fr(0))
        psi = {}
        for idx, v in rhs.items():
            if idx == self.ref or v == 0:
                continue
            den = self.E0ref - self.H0[idx]
            if den == 0:
                if self.drop_degenerate:
                    continue
                raise ZeroDivisionError(f"degenerate state in channel {self.name}")
            psi[idx] = v / den
        self.E.append(En)
        self.psi.append(psi)
        return En


def run(L, variants, K=8, verbose=True):
    t0 = time.time()
    spaces, ops, Mp = {}, {}, {}
    for par in (0, 1):
        sp = rf.Space(L, par, ZMAX + K)
        ctup = rf.ordered_creation_tuples(sp, 4)
        ops[par] = {"M": rf.build_vertex(sp, 2, Fr(1), ctup), "V": rf.build_vertex(sp, 4, Fr(1, 12), ctup)}
        Mp[par] = build_Mprime_poly(sp, ctup)
        spaces[par] = sp
        if verbose:
            print(f"# L={L} parity={par}: {len(sp.states)} states t={time.time() - t0:.1f}s", flush=True)
    ls = list(range(0, L + 1, 2))
    zero = lambda k, N: 0
    out = {"L": L}
    for var in variants:
        r = [Fr(0)] * (ORD + 1)
        g = [Fr(0)] * (ORD + 1)
        g[1] = G1
        xser = [Fr(1, 2), Fr(-1, 4)] + [Fr(0)] * (ORD - 1)
        aux = {(z, l): DChannel(f"z{z}l{l}", spaces[z % 2], ops[z % 2], z, l, K, zero, drop_degenerate=True,
                                bequation=(var not in ("Wb", "Wc")))
               for z in range(ZMAX + 1) for l in ls}
        prim = {p: DChannel(f"p{p}", spaces[p % 2], ops[p % 2], p, L, K, zero) for p in range(4)}
        h = {}

        def tune(n):
            rhs0 = {p: prim[p].rhs_without_new(n, r, g) for p in range(4)}
            X = {p: rhs0[p].get(prim[p].ref, Fr(0)) for p in range(4)}
            r[n] = (xser[n] - X[1] + X[0]) / 2
            g[n] = (-xser[n] - X[3] + X[0] - 6 * r[n]) / 3
            for p in range(4):
                prim[p].finish_order(n, rhs0[p], r[n], g[n])

        # (a) aux order 1; order-2 rhs without windows -> h (zero-mode monomial projection).  D_2|z> has no P0
        #     component and the r2, g2 terms are added only in finish_order, so h needs neither.
        for chn in aux.values():
            chn.finish_order(1, chn.rhs_without_new(1, r, g), r[1], g[1])
        for (z, l), chn in aux.items():
            rhs2 = chn.rhs_without_new(2, r, g)
            for zp in range(z % 2, ZMAX + 1, 2):
                h[(zp, z, l)] = rhs2.get(spaces[z % 2].ref_index(zp), Fr(0))

        def c1_2(l):
            return h[(1, 1, l)] - h[(0, 0, l)]

        def make_D2(l, par):
            sp = spaces[par]
            cols = Mp[par]

            def apply(vec):
                o = {}
                for c, v in vec.items():
                    N = sp.level[c]
                    if N:
                        st = dict(sp.states[c])
                        z = st.get(0, 0)
                        if z <= ZMAX:
                            for zp in range(z % 2, ZMAX + 1, 2):
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
                    for (row, pol) in cols[c]:
                        if sp.level[row] > l:
                            continue
                        lr = L if var == "Wc" else l   # Wc: auxiliary windows referenced to the outer cutoff L
                        w = Fr(1, 4) * ((c1_2(lr) - c1_2(l - sp.level[row])) + (c1_2(lr) - c1_2(l - N)))
                        if w and pol[0]:
                            o[row] = o.get(row, 0) + w * pol[0] * v
                return o
            return apply

        # (b) primaries orders 1, 2 with D_2 from the start (DM2|p> enters psi_2; E_2 is window independent)
        for p in range(4):
            prim[p].Dops = {2: make_D2(L, p % 2)}
        for n in (1, 2):
            tune(n)
        # (c) aux: order 2 with their own D_2,l and r2, g2; then order 3 where needed (r3 = g3 = 0: the terms
        #     2z r3 + C(z,2) g3 are l independent and cancel in every window)
        need3 = {"W2": [], "W3m": [0, 1], "W3e": list(range(8)), "Wb": list(range(7)), "Wc": list(range(7))}[var]
        for (z, l), chn in aux.items():
            chn.Dops = {2: make_D2(l, z % 2)}
            chn.finish_order(2, chn.rhs_without_new(2, r, g), r[2], g[2])
        for (z, l), chn in aux.items():
            if z in need3:
                chn.finish_order(3, chn.rhs_without_new(3, r, g), Fr(0), Fr(0))

        def c1_3(l):
            return aux[(1, l)].E[3] - aux[(0, l)].E[3]

        h3 = {}
        if var in ("Wb", "Wc"):
            ZB = 6
            for l in ls:
                for z in range(ZB + 1):
                    sp = spaces[z % 2]
                    ch_ = aux[(z, l)]
                    idx = lambda zz: sp.ref_index(zz)
                    X = {n_: {zz: ch_.psi[n_].get(idx(zz), Fr(0)) for zz in range(z % 2, ZMAX + 1, 2) if zz != z}
                         for n_ in (1, 2, 3)}
                    E1u = ch_.E[1]
                    E2_ = ch_.E[2]
                    # h1 (monomial, level 0): W1 = -P/4 + g1 V0
                    def h1m(zp, zz):
                        col = {idx(zz): Fr(1)}
                        w = ch_.matvec("V", 0, col)
                        val = G1 * w.get(idx(zp), Fr(0))
                        if zp == zz:
                            val += Fr(-zz, 4)
                        return val
                    for zp in range(z % 2, ZB + 1, 2):
                        if zp != z:
                            v = Fr(z - zp, 2) * X[3][zp] + E1u * X[2][zp] + E2_ * X[1][zp]
                        else:
                            v = ch_.E[3]
                        for zz in range(z % 2, ZMAX + 1, 2):
                            if zz == z:
                                continue
                            hz = h1m(zp, zz)
                            if hz:
                                v -= hz * X[2][zz]
                            if X[1][zz]:
                                v -= h[(zp, zz, l)] * X[1][zz]
                        h3[(zp, z, l)] = v
            globals()["LAST_H3"] = h3
            globals()["LAST_X3"] = {(zp, z, l): aux[(z, l)].psi[3].get(spaces[z % 2].ref_index(zp), 0) for z in range(7) for zp in range(z % 2, 7, 2) for l in ls}
            globals()["LAST_RG"] = (list(r), list(g))

        def make_D3(l, par):
            sp = spaces[par]
            cols = Mp[par]

            def apply(vec):
                o = {}
                for c, v in vec.items():
                    N = sp.level[c]
                    if var in ("Wb", "Wc") and N:
                        st = dict(sp.states[c])
                        z = st.get(0, 0)
                        if z <= 6:
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
                    if var == "W3e" and N:
                        z = dict(sp.states[c]).get(0, 0)
                        if z <= 7:
                            d = aux[(z, l)].E[3] - aux[(z, l - N)].E[3]
                            if d:
                                o[c] = o.get(c, 0) + d * v
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

        if var in ("W3m", "W3e", "Wb", "Wc"):
            for p in range(4):
                prim[p].Dops[3] = make_D3(L, p % 2)
        for n in range(3, ORD + 1):
            tune(n)
        C = [prim[2].E[n] - prim[0].E[n] for n in range(ORD + 1)]
        out[var] = {"C": [str(c) for c in C], "C_float": [float(c) for c in C],
                    "r": [str(x) for x in r], "g": [str(x) for x in g],
                    "r_float": [float(x) for x in r], "g_float": [float(x) for x in g]}
        if verbose:
            print(f"# {var}: C = {[float(c) for c in C]}  t={time.time() - t0:.1f}s", flush=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--variants", default="W2,W3m,W3e,Wb")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = run(a.L, a.variants.split(","))
    print(json.dumps({k: (v["C_float"] if isinstance(v, dict) else v) for k, v in res.items()}))
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(res, fh, indent=1)
