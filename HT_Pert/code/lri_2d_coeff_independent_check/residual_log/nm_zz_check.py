#!/usr/bin/env python3
"""Is the exact zero-mode window replaceable by its leading form -(g1^2/(3 pi)){N, :Z^2:}?  Computes the C4 shift of
the leading form (M vertex with 0 chi legs, i.e. the zero-mode sunset part of {N, M}) and compares it with the exact
full zero-mode window shift (C4corr - C4cons) + off.  usage: python3 nm_zz_check.py 400"""
import sys
import numpy as np
import c4lib as lib
import nm_window as nw


def chain_zz(kinds, slice_ops, N, ser, mvert, wslices, ps=(0, 1, 2, 3)):
    res = {p: np.zeros(N + 1) for p in ps}
    K = len(kinds)
    for n in lib.patterns(kinds):
        if lib.legs_of(n, K)[mvert] != 0:
            continue
        for ws in wslices:
            r = nw.chain_pattern_w(kinds, slice_ops, n, N, ser, ws, ps)
            if r is not None:
                for p in ps:
                    res[p] += r[p]
    return res


Lmax = int(sys.argv[1]) if len(sys.argv) > 1 else 400
N = Lmax // 2
ser = lib.Series(N)
P = (0, 1, 2, 3)
VMV = chain_zz(["V", "M", "V"], [(1, 0), (1, 0)], N, ser, 1, [0, 1])
d = nw.Pi({p: nw.KAPPA * nw.g1 ** 2 * VMV[p] for p in P})
c = np.load("../c4_exact/results/c4_L2000.npz")
o = np.load("results/offdiag_L20000.npz")
ex = (c["C4corr"] - c["C4cons"])[:N + 1] + o["off"][:N + 1]
for L in (10, 50, 100, 200, 400, 1000, 2000):
    if L <= Lmax:
        i = L // 2
        print(f"L={L:5d} leading {{N,:Z^2:}} shift={d[i]:+.8f}  exact full zm window shift={ex[i]:+.8f}  "
              f"exact - leading={ex[i] - d[i]:+.8f}", flush=True)
np.savez(f"results/nm_zz_L{Lmax}.npz", L=2 * np.arange(N + 1), lead=d, exact=ex)
