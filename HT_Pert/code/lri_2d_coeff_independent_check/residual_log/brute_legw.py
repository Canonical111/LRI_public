#!/usr/bin/env python3
"""Exact (Fraction) brute-force check of nm_legw.py: C_4 response to (1/2) X inserted at eps^2 in the raw truncated
Hamiltonian, X = M'^{+-}_nu (every M' term weighted by s * sum of chi-leg levels, s = +1 hop, -1 pair).
Also provides build_Xnu(sp, ctup, poly=False) for the other brute-force codes.
usage: python3 brute_legw.py --L 6"""
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


def build_Xnu(sp, ctup, poly=False, zero_like=None):
    """S^-1 X S as column lists (row, value) [eps^0] or (row, eps-poly) with poly=True.
    zero_like: set of mode indices treated as level-0 zero modes for the M' exclusion (default {0}).
    Leg level = sp.blev[m] if the space has budget levels (tagged spaces), else sp.lev[m]."""
    zl = zero_like if zero_like is not None else {0}
    levf = getattr(sp, "blev", sp.lev)
    nolev = getattr(sp, "nolev", set())
    cols = []
    for i, s in enumerate(sp.states):
        occ = dict(s)
        NB = sp.blevel[i] if hasattr(sp, "blevel") else sp.level[i]
        P = sp.P[i]
        acc = {}
        for kc in range(3):
            ka = 2 - kc
            if P - ka + kc > sp.Pmax or ka > P:
                continue
            base = Fr(comb(2, kc))
            sign = 1 if kc == 1 else -1
            occ_modes = [m for m in occ.keys() if m != getattr(sp, "oX", -1)]

            def ann_rec(t, cnt, coef, wpoly, Jann, levann):
                if len(t) == ka:
                    budget = sp.L - (NB - levann)
                    for (lc, ct) in ctup[kc].get(Jann, ()):
                        if lc > budget:
                            continue
                        if all(m in zl for m in t) and all(m in zl for m in ct):
                            continue
                        legl = sum(0 if (m in zl or m in nolev) else sp.lev[m] for m in list(t) + list(ct))
                        if legl == 0:
                            continue
                        new = dict(cnt)
                        for m in ct:
                            new[m] = new.get(m, 0) + 1
                        tgt = tuple(sorted((m, c) for m, c in new.items() if c))
                        j = sp.index.get(tgt)
                        if j is None:
                            continue
                        f = coef * sign * legl
                        val = [f * x for x in wpoly]
                        acc[j] = [x + y for x, y in zip(acc[j], val)] if j in acc else val
                    return
                for m in occ_modes:
                    c = cnt.get(m, 0)
                    if c == 0:
                        continue
                    cnt2 = dict(cnt)
                    cnt2[m] = c - 1
                    t.append(m)
                    ann_rec(t, cnt2, coef * c, rf.poly_mul(wpoly, sp.w[m]), Jann + sp.J[m], levann + levf[m])
                    t.pop()

            ann_rec([], dict(occ), base, [Fr(1)] + [Fr(0)] * rf.ORD, 0, 0)
        if poly:
            cols.append([(j, pol) for j, pol in acc.items() if any(pol)])
        else:
            cols.append([(j, pol[0]) for j, pol in acc.items() if pol[0]])
    return cols


class GChannel(rf.Channel):
    def __init__(self, *a, Dapply=None, Dorder=2, **kw):
        super().__init__(*a, **kw)
        self.Dapply, self.Dorder = Dapply, Dorder

    def rhs_without_new(self, n, r, g):
        out = super().rhs_without_new(n, r, g)
        k = self.Dorder
        if n >= k and self.Dapply is not None:
            for row, v in self.Dapply(self.psi[n - k]).items():
                if self.allowed[row]:
                    out[row] = out.get(row, 0) + v
        return out


def run(L, K=8, order=2, verbose=True):
    rf.ORD = 5
    ORD = order + 2
    t0 = time.time()
    spaces, ops, Xc = {}, {}, {}
    for par in (0, 1):
        sp = rf.Space(L, par, (6 if par == 0 else 7) + K)
        ctup = rf.ordered_creation_tuples(sp, 4)
        ops[par] = {"M": rf.build_vertex(sp, 2, Fr(1), ctup), "V": rf.build_vertex(sp, 4, Fr(1, 12), ctup)}
        Xc[par] = build_Xnu(sp, ctup)
        spaces[par] = sp
    zero = lambda k, N: 0

    def make_X(par):
        cols = Xc[par]

        def apply(vec):
            out = {}
            for c, v in vec.items():
                for (row, val) in cols[c]:
                    out[row] = out.get(row, 0) + Fr(1, 2) * val * v
            return out
        return apply

    res = {}
    for name, mk in (("raw", lambda par: None), ("X", make_X)):
        ch = {p: GChannel(f"{name}p{p}", spaces[p % 2], ops[p % 2], p, L, K, zero, Dapply=mk(p % 2), Dorder=order)
              for p in range(4)}
        r = [Fr(0)] * (ORD + 1)
        g = [Fr(0)] * (ORD + 1)
        xser = [Fr(1, 2), Fr(-1, 4)] + [Fr(0)] * (ORD - 1)
        C = [Fr(1)]
        for n in range(1, ORD + 1):
            rhs0 = {p: ch[p].rhs_without_new(n, r, g) for p in range(4)}
            X = {p: rhs0[p].get(ch[p].ref, Fr(0)) for p in range(4)}
            r[n] = (xser[n] - X[1] + X[0]) / 2
            g[n] = (-xser[n] - X[3] + X[0] - 6 * r[n]) / 3
            for p in range(4):
                ch[p].finish_order(n, rhs0[p], r[n], g[n])
            C.append(ch[2].E[n] - ch[0].E[n])
        res[name] = C
    d = res["X"][ORD] - res["raw"][ORD]
    if verbose:
        print(f"L={L} order={order}: dC_{ORD} per unit delta = {float(d):+.15f}  t={time.time() - t0:.1f}s", flush=True)
    return {"L": L, "order": order, "dC": str(d), "dC_float": float(d)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--order", type=int, default=2)
    a = ap.parse_args()
    run(a.L, order=a.order)
