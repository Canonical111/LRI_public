"""Own linked joint fitter with the lens's diagnostics: whitened rms (erms, residual/wrel) and the gradient noise
'stat' (SIGRAW white noise per C_k(L), propagated through the sequential chain; low/top windows keyed separately)."""
import numpy as np
from flint import arb
from mylsq import solve
from myjoint import C2X, C3X, GAPS, terms, eser
SIGRAW = {2: 6.5e-15, 3: 8.4e-14, 4: 2.9e-13, 5: 3.3e-12, 6: 1.25e-11, 7: 1.4e-10, 8: 1.4e-8}

def fit2(L, C, lo, hi, base, mode, shift, gap, hi_low=None, wrel=None, weighted=False, maxorder=8):
    w = dict(GAPS[gap]); lim = {2: C2X, 3: C3X}; out = {}; grad = {}
    for n in range(4, maxorder + 1):
        uselow = hi_low is not None and n <= 7
        top = hi_low if uselow else hi
        idx = [i for i in range(len(L)) if lo <= L[i] <= top]
        tag = 'low' if uselow else 'top'
        z = [arb(float(L[i])) + arb(shift) for i in idx]; l = [x.log() for x in z]
        Ca = {k: [arb(float(C[i, k])) for i in idx] for k in range(2, n + 1)}
        T2 = [Ca[2][r] - C2X for r in range(len(idx))]
        free = (n == 8) or (mode == 'free' and 5 <= n <= 7)
        wn = dict(w)
        if free: wn[n - 2] = 0.
        e = eser(l, wn, n - 2)
        y = [Ca[n][r] + sum((e[j][r] * (Ca[n - j][r] - lim[n - j]) for j in range(1, n - 1)), arb(0)) for r in range(len(idx))]
        cols = [[arb(1)] * len(idx), T2] + [[z[r] ** arb(-p) * l[r] ** q for r in range(len(idx))] for p, q in terms(base, mode, n)]
        if free: cols.append([l[r] * T2[r] for r in range(len(idx))])
        if len(idx) <= len(cols): raise ValueError('few')
        wv = np.asarray(wrel[n])[idx] if wrel is not None else np.ones(len(idx))
        r = solve(cols, y, (1.0 / wv) if weighted else None, want_pinv0=True)
        lim[n] = arb(r['coef'][0].mid())
        if free and n < 8: w[n - 2] = -float(r['coef'][-1].mid())
        res = r['res']; row = r['p0']
        ef = [[float(e[j][q].mid()) for q in range(len(idx))] for j in range(n - 1)]
        g = {}
        def add(k, key, v):
            g.setdefault(k, {}); g[k][key] = g[k].get(key, 0.) + v
        for q, i in enumerate(idx):
            add(n, (tag, L[i]), row[q])
            for j in range(1, n - 1): add(n - j, (tag, L[i]), row[q] * ef[j][q])
        for j in range(1, n - 1):
            if n - j >= 4:
                s = float(np.dot(row, ef[j]))
                for k, dd in grad[n - j].items():
                    for key, v in dd.items(): add(k, key, -s * v)
        grad[n] = g
        stat = float(np.sqrt(sum(SIGRAW[k] ** 2 * sum(v * v for v in dd.values()) for k, dd in g.items())))
        out[n] = dict(p0=row, idx=idx, lim=float(lim[n].mid()), rms=float(np.sqrt(np.mean(res ** 2))), erms=float(np.sqrt(np.mean((res / wv) ** 2))),
                      stat=stat, npts=len(idx), ncol=len(cols))
    return out
