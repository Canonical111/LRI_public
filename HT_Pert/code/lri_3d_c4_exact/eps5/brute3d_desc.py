#!/usr/bin/env python3
"""eps^n descendant identity (T2/T3 of the 2D project) in 3D, brute force on the package operators:
chi_11 = one bath quantum (n = 1, l = 0) at level 2 (the scalar descendant of phi), nondegenerate in its sector.
R_n(L) = [eps^n] (E(chi_11) - E(phi) - 2) must vanish in the continuum.  The channel is an outer channel at cutoff L
with the scheme's windows (brute3d_W5.Solver); Wcs adds (delta3/2) X_0 at eps^3 (delta3 from brute3d_tag.py).
usage: python3 brute3d_desc.py --L 8 --variants Wc,Wcs --delta3 x"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brute3d_W5 as bw  # noqa: E402

DT = bw.DT


class DescChan(bw.Chan):
    def __init__(self, bare, Nall, Pall, L, row):
        super().__init__(bare, Nall, Pall, L, 0)
        # reference: bath row `row` (one quantum, level 2), regular zero mode z = 0  (field parity = 1)
        self.field = 1
        lp = self.field ^ (self.P % 2)
        self.lp = lp
        self.zcol = lp[:, None] + 2 * np.arange(bw.NZ)[None, :]
        totalp = self.P[:, None] + self.zcol
        h0 = self.N[:, None] + DT(bw.X0) * totalp
        self.idx = (row, 0)                        # z = 0 is column 0 when lp(row) = 0 (P = 1, field 1)
        assert lp[row] == 0
        E0 = h0[self.idx]
        den = E0 - h0
        den[self.idx] = 1
        bad = np.abs(den) < 1e-9
        bad[self.idx] = False
        if np.any(bad):
            raise RuntimeError("descendant channel degenerate")
        self.den = den
        self.E = [E0] + [DT(0)] * bw.ORD
        v = np.zeros((self.nb, bw.NZ), dtype=DT)
        v[self.idx] = 1
        self.psi = [v]


def run(L, var, delta3=None, nmax=3):
    sol = bw.Solver(L, var, delta3 if var == "Wcs" else None)
    # find the bath row with one quantum (n=1, l=0): level 2, P = 1
    rows = [b for b in range(len(sol.Nall)) if sol.Nall[b] == 2 and sol.Pall[b] == 1]
    if len(rows) != 1:
        raise RuntimeError(f"expected one scalar one-quantum level-2 state, found {rows}")
    ch = DescChan(sol.bare, sol.Nall, sol.Pall, L, rows[0])
    # lock step: run the solver order by order, advancing the descendant channel with the same couplings/windows
    res = sol.run()                                   # couplings, windows, h, c1 for all orders
    bare = sol.bare
    # replay the descendant channel with the final couplings (they are order-by-order fixed numbers)
    for n in range(1, nmax + 1):
        # full diagonal <chi|H_n|chi> (M, V and the windows have diagonal elements on a bath quantum)
        ch.E[n] = sol.provisional(n, ch) + sol.apply(n, ch, ch.psi[0])[ch.idx]
        if n < nmax:
            ch.psi.append(sol.rhs(n, ch, with_dn=False) / ch.den)
            if n >= 2:
                d = sol.windows(n, ch, ch.psi[0])
                d[ch.idx] = 0
                ch.psi[n] = ch.psi[n] + d / ch.den
    Ephi = sol.prim[1].E
    Rn = [float(ch.E[n] - Ephi[n]) for n in range(nmax + 1)]
    Rn[0] -= 2.0
    return Rn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--variants", default="raw,Wc")
    ap.add_argument("--delta3", type=float, default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = {}
    for v in a.variants.split(","):
        Rn = run(a.L, v, a.delta3)
        res[v] = Rn
        print(f"L={a.L} {v:4s} R_1 = {Rn[1]:+.3e}  R_2 = {Rn[2]:+.12f}  R_3 = {Rn[3]:+.12f}", flush=True)
    if a.out:
        json.dump(dict(L=a.L, delta3=a.delta3, R=res), open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
