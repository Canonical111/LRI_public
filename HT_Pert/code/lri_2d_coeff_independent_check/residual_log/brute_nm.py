#!/usr/bin/env python3
"""Brute-force exact (Fraction) validation of nm_window.py: full Rayleigh-Schroedinger in the truncated Fock space
(../rs_exact/ref_fraction.py, imported READ-ONLY) with the extra order-eps^2 operator

    D_chi = kappa {N, M'},   kappa = -g1^2/(3 pi) -> here kappa = 1 (the shift is linear in kappa at eps^4),

M' = M minus its pure zero-mode part (:Z^2:).  D_chi is off-diagonal and does not vanish on |p> (M' A^dag A^dag), so
it is added to W_2 as a general matrix (similarity frame: S^{-1}{N,M'}S = {N, S^{-1}M'S}, N diagonal).
Prints dC_n = C_n(raw + D_chi) - C_n(raw) for n <= 4 per unit kappa; compare with nm_window.py dC4 / kappa.
usage: python3 brute_nm.py --L 6"""
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

ORD = 4
rf.ORD = ORD


def build_Mprime(sp, ctup):
    """eps^0 part of S^{-1} M' S as column lists (row, value): <:phi^2:>_theta without the all-zero-mode terms."""
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

            def ann_rec(t, cnt, coef, wprod, Jann, levann):
                if len(t) == ka:
                    budget = sp.L - (N - levann)
                    for (lc, ct) in ctup[kc].get(Jann, ()):
                        if lc > budget:
                            continue
                        if all(m == 0 for m in t) and all(m == 0 for m in ct):
                            continue          # pure zero-mode term (:Z^2:) excluded
                        new = dict(cnt)
                        for m in ct:
                            new[m] = new.get(m, 0) + 1
                        tgt = tuple(sorted((m, c) for m, c in new.items() if c))
                        j = sp.index.get(tgt)
                        if j is None:
                            continue
                        acc[j] = acc.get(j, 0) + coef * wprod
                    return
                for m in occ_modes:
                    c = cnt.get(m, 0)
                    if c == 0:
                        continue
                    cnt2 = dict(cnt)
                    cnt2[m] = c - 1
                    t.append(m)
                    ann_rec(t, cnt2, coef * c, wprod * sp.w[m][0], Jann + sp.J[m], levann + sp.lev[m])
                    t.pop()

            ann_rec([], dict(occ), base, Fr(1), 0, 0)
        cols.append([(j, v) for j, v in acc.items() if v])
    return cols


class DChannel(rf.Channel):
    def __init__(self, *a, Dcols=None, kappa=Fr(0), **kw):
        super().__init__(*a, **kw)
        self.Dcols = Dcols
        self.kappa = kappa

    def rhs_without_new(self, n, r, g):
        out = super().rhs_without_new(n, r, g)
        if n >= 2 and self.kappa:
            sp = self.sp
            for c, v in self.psi[n - 2].items():
                for (row, val) in self.Dcols[c]:
                    if self.allowed[row]:
                        out[row] = out.get(row, 0) + self.kappa * (sp.level[row] + sp.level[c]) * val * v
        return out


def run(L, K=8, verbose=True):
    t0 = time.time()
    spaces, ops, Dc = {}, {}, {}
    for par in (0, 1):
        sp = rf.Space(L, par, 3 + K)
        ctup = rf.ordered_creation_tuples(sp, 4)
        ops[par] = {"M": rf.build_vertex(sp, 2, Fr(1), ctup), "V": rf.build_vertex(sp, 4, Fr(1, 12), ctup)}
        Dc[par] = build_Mprime(sp, ctup)
        spaces[par] = sp
        if verbose:
            print(f"# L={L} parity={par}: {len(sp.states)} states t={time.time() - t0:.1f}s", flush=True)
    zero = lambda k, N: 0
    out = {}
    for name, kap in (("raw", Fr(0)), ("raw+D", Fr(1))):
        ch = {p: DChannel(f"{name}p{p}", spaces[p % 2], ops[p % 2], p, L, K, zero, Dcols=Dc[p % 2], kappa=kap)
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
        out[name] = dict(C=C, r=list(r), g=list(g))
        if verbose:
            print(f"# {name}: C = {[float(c) for c in C]}  t={time.time() - t0:.1f}s", flush=True)
    d = {k: [out["raw+D"][k][n] - out["raw"][k][n] for n in range(ORD + 1)] for k in ("C", "r", "g")}
    return {"L": L, "dC": [str(x) for x in d["C"]], "dC_float": [float(x) for x in d["C"]],
            "dg3_float": float(d["g"][3]), "dr3_float": float(d["r"][3])}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = run(a.L)
    print(json.dumps(res))
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(res, fh, indent=1)
