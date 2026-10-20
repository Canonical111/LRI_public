#!/usr/bin/env python3
"""Review check E (foundation-rigor): the unbalanced-kernel control of the Remark after Theorem 6
(d=1, sigma=0.2, g'=0.25 instead of g=0.3, r=4).  Prints the true Fourier coefficients gamma_{+-3}
(node factor removed; reflection forces |gamma_3| = |gamma_-3|) and the RAW DFT outputs
N^{-1} sum_j X_j e^{-2 pi i m j/N} at 7 nodes of height eta, which reproduce the quoted 0.13 / 0.020."""
import numpy as np
from brute_xi import Brute, summarize
for gp in (0.25, None):
    B = Brute(4, 1.0, 0.4, 400, 200000, gp)
    for eta, tau0 in ((0.06, 0.0137), (1 / (32 * np.pi), -0.125), (0.05, -0.125)):
        ts = B.nodes(eta=eta, tau0=tau0, Nn=7)
        gam, X, ts = B.modes(ts)
        raw = {m: np.sum(X * np.exp(-2j * np.pi * m * np.arange(7) / 7)) / 7 for m in range(-3, 4)}
        print("g'=%s eta=%.4f: |gamma_+3|=%.4g |gamma_-3|=%.4g (max|gamma| %.4g)   raw DFT |.|_{+3}=%.4g |.|_{-3}=%.4g"
              % (gp, eta, abs(gam[3]), abs(gam[-3]), max(abs(v) for v in gam.values()), abs(raw[3]), abs(raw[-3])))
    print('   17-node summary:', summarize(4, B.modes()[0], B.sig))
