#!/usr/bin/env python3
"""Does the C4 limit depend on the reference energy of the window bubble?  Recomputes the full zero-mode window
(offdiag_window.py) with the bubble denominator referenced to the ket (derived form), to the bra, and their average
(Hermitian form).  usage: python3 offdiag_hermitian_check.py 8000"""
import sys
import numpy as np
import c4lib as lib
import offdiag_window as ow
import fitlib as F

Lmax = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
N = Lmax // 2
ser = lib.Series(N, kmax=4)
R = {m: lib.two_vertex_density(m, 0, 0, ser) for m in range(1, 5)}
sig = np.arange(N + 1)
tab = ow.path_table()
res = {"ket": np.zeros(N + 1), "bra": np.zeros(N + 1), "sym": np.zeros(N + 1)}
for (m, d1, d3, m2, dB), coef in sorted(tab.items()):
    Delta = d3 - d1
    mask = 2 * sig >= m
    h = np.zeros(N + 1)
    h[mask] = R[m][mask] / (((d1 + m) / 2.0 + 2 * sig[mask]) * ((d3 + m) / 2.0 + 2 * sig[mask]))
    mk = 2 * sig >= m2
    sk = np.zeros(N + 1)
    sb = np.zeros(N + 1)
    sk[mk] = -R[m2][mk] / ((dB + m2) / 2.0 + 2 * sig[mk])             # ket: relative to the state before B1
    sb[mk] = -R[m2][mk] / ((dB - Delta + m2) / 2.0 + 2 * sig[mk])     # bra: relative to the state after B2
    Wk = lib.window_sum(h, sk)
    Wb = lib.window_sum(h, sb)
    res["ket"] += float(coef) * Wk
    res["bra"] += float(coef) * Wb
    res["sym"] += float(coef) * 0.5 * (Wk + Wb)
L = 2 * sig.astype(float)
for k in ("bra", "sym"):
    dlt = res[k] - res["ket"]
    c, r_, _ = F.fit(L, dlt, ["1", "l", "1/L", "l/L", "l2/L", "1/L2"], 1000)
    print(f"{k} - ket: L=100 {dlt[50]:+.3e}  L=1000 {dlt[500]:+.3e}  L={Lmax} {dlt[-1]:+.3e}   fit: const {c['1']:+.2e} "
          f"log {c['l']:+.2e}")
