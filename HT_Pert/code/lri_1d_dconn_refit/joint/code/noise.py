#!/usr/bin/env python3
"""Model-free noise of the order-n fit targets Y_n(L) (and of the raw C_n) by k-th finite differences on the uniform even
grid (as linked-joint/noise.py): sigma_k = rms(D^k Y)/sqrt(binom(2k,k)); the minimum over k is the estimate.
Run on raw and on Dconn-corrected tables, over several ranges, incl. the exact-dC region (L<=44) and across the 44/46
seam where the delta-v1 model takes over."""
import sys, json
sys.dont_write_bytecode = True
from math import comb
import numpy as np
from data import load
import fitcore as F
D = load(with_perts=False); L = D['L']
out = {}
for ds in ('raw', 'dconn', 'dconn_s46', 'dconn_med', 'dconn_mean', 'dconn_model'):
    C = D[ds]
    r = F.fit(L, C, 40, 92, 'E', 0., F.OMEGA_EXT, hi_low=118)
    lim = {2: F.C2F, 3: F.C3F, **r['lim']}; om = r['omega']
    for rng in ((24, 70), (24, 44), (46, 72), (30, 92), (52, 92), (52, 118)):
        m = (L >= rng[0]) & (L <= rng[1]); a = L[m]; d = C[m]
        ell = np.log(a)
        e = [np.ones_like(ell)]
        for n in range(1, 7):
            e.append(ell / n * sum(j * om[j] * e[n - j] for j in range(1, n + 1)))
        res = {}
        for n in range(2, 9):
            if not np.all(np.isfinite(d[:, n])):
                continue
            Y = d[:, n].copy()
            for j in range(1, n - 1):
                Y += e[j] * (d[:, n - j] - lim[n - j])
            sig = {k: float(np.sqrt(np.mean(np.diff(Y, k) ** 2)) / np.sqrt(comb(2 * k, k))) for k in range(3, min(len(a) - 3, 26))}
            kmin = min(sig, key=sig.get)
            res[n] = dict(sigma=sig[kmin], k=kmin)
        out[f'{ds}_{rng[0]}_{rng[1]}'] = res
        print(f'{ds:5s} {rng}: ' + '  '.join(f"Y{n} {v['sigma']:.2e}(k{v['k']})" for n, v in res.items()))
json.dump(out, open('../out/noise.json', 'w'), indent=1)
