#!/usr/bin/env python3
"""Test of the all-orders form of the chi mass window at eps^4:
    D^M = (1/4){Dc1(L, N), M'},  Dc1(L, N) = c1(L) - c1(L - N),  c1 = E_1 - E_0 (full phi self-energy, all bubble types)
vs the verified sunset-slope form -(g1^2/(3 pi)){N, M'}.  At eps^2, c1 = 2 r2 + g1^2 (e_1 - e_0); the r2 part cancels in
the window.  Per-cutoff evaluation (the weight depends on L explicitly).  usage: python3 nm_window_c1.py 50 100 200 400"""
import sys
import numpy as np
import c4lib as lib
import nm_window as nw
import nm_window_exact as nwe
import descendant_e2 as de

if __name__ == "__main__":
    lin = np.load("results/nm_L400.npz")
    for L in [int(x) for x in sys.argv[1:]]:
        M = L // 2
        ser = lib.Series(M)
        R = {m: lib.two_vertex_density(m, 0, 0, ser) for m in range(1, 5)}
        ed = de.e_diff(M, ser, R)                      # e_1(l) - e_0(l), l = 2*index
        f = np.array([0.25 * nw.g1 ** 2 * (ed[M] - ed[M - s]) for s in range(M + 1)])   # (1/4) Dc1(L, 2 sigma)
        wt = f / nw.KAPPA                               # replaces sigma in the linear form
        def cpT(kinds, slice_ops, n, N_, ser_, wslice, ps=(0, 1, 2, 3)):
            return nwe._cpT(kinds, slice_ops, n, N_, ser_, wslice, wt, ps)
        saved = nw.chain_pattern_w
        nw.chain_pattern_w = cpT
        try:
            r = nw.compute(L)
        finally:
            nw.chain_pattern_w = saved
        d = r["dC4"][M]
        print(f"L={L:5d} c1-window dC4={d:+.10f}  linear={lin['dC4'][M]:+.10f}  diff={d - lin['dC4'][M]:+.3e}", flush=True)
