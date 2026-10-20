#!/usr/bin/env python3
"""Scheme W of WINDOW_SPEC.md at eps^4 (D^zm full Bloch window + D^M = (1/4){Dc1, M'} with the exact c1 window),
from the large-L codes: C4_W(L) = C4corr + off + dC4[c1 form], every even L up to Lmax (per-L evaluation of the
c1-window chain sums).  Also dr3, dg3 of D^M (scheme W changes r3, g3; C3 unchanged).
usage: python3 w_spec_small_L.py 40 > results/w_spec_small_L.txt"""
import sys
import numpy as np
import c4lib as lib
import nm_window as nw
import nm_window_exact as nwe
import descendant_e2 as de

Lmax = int(sys.argv[1]) if len(sys.argv) > 1 else 40
c = np.load("../c4_exact/results/c4_L2000.npz")
o = np.load("results/offdiag_L20000.npz")
print("L, C4_W_spec, dC4_DM_c1, dr3_DM, dg3_DM, C4_corr, dC4_offdiag")
for L in range(2, Lmax + 1, 2):
    M = L // 2
    ser = lib.Series(M)
    R = {m: lib.two_vertex_density(m, 0, 0, ser) for m in range(1, 5)}
    ed = de.e_diff(M, ser, R)
    f = np.array([0.25 * nw.g1 ** 2 * (ed[M] - ed[M - s]) for s in range(M + 1)])
    wt = f / nw.KAPPA
    saved = nw.chain_pattern_w
    nw.chain_pattern_w = lambda kinds, so, n, N_, ser_, ws, ps=(0, 1, 2, 3): nwe._cpT(kinds, so, n, N_, ser_, ws, wt, ps)
    try:
        r = nw.compute(L)
    finally:
        nw.chain_pattern_w = saved
    W = c["C4corr"][M] + o["off"][M] + r["dC4"][M]
    print(f"{L}, {W:.15f}, {r['dC4'][M]:.15e}, {r['dr3'][M]:.15e}, {r['dg3'][M]:.15e}, {c['C4corr'][M]:.15f}, "
          f"{o['off'][M]:.15e}", flush=True)
