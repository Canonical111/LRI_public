import sys; sys.dont_write_bytecode=True
import numpy as np, json
from myfit import *
L, C = rows()
T = {int(k): v for k, v in json.load(open(RC + '/dC_reconciled.json')).items()}
w0 = {int(k): v for k, v in json.load(open(EXT + '/extended_summary.json'))['gap_reference']['extended'].items()}
col = lambda key: np.array([T[int(l)][key] for l in L])
Cf = C.copy(); Cf[:, 4] += col('dC4_Dconn'); Cf[:, 5] += col('dC5_Dconn')
def fitfree(L, C, terms, w):
    w = dict(w); x = C[:, 2] - C2INF; lim = {2: C2INF, 3: C3INF}; info = {}
    for k in (4, 5):
        free = k >= 5
        if free: w[k - 2] = 0.
        e = ecoef(L, w, k - 2)
        y = C[:, k] + sum(e[j] * (C[:, k - j] - lim[k - j]) for j in range(1, k - 1))
        X = np.column_stack([np.ones_like(L), x] + [L ** (-p) * np.log(L) ** j for p, j in terms] + ([-np.log(L) * x] if free else []))
        p, res, gain = solve(X, y); lim[k] = p[0]; info[k] = (res, gain)
        if free: w[k - 2] = p[-1]
    return lim, info, w
res = json.load(open('scan.json'))
fl = [r for r in res if r['r5'] < 6e-11 and r['r4'] < 6e-12 and r['g5'] < 2e9]
has = lambda r: [0.5, 1] in r['ex']
for lab, sel in (('with L^-1/2 log L', [r for r in fl if has(r)]), ('without', [r for r in fl if not has(r)])):
    c5 = np.array([r['c5'] for r in sel]); c4 = np.array([r['c4'] for r in sel])
    print(f'{lab}: n={len(sel)} C5 miss {c5.min():+.3f}..{c5.max():+.3f} median {np.median(c5):+.3f}; C4 miss {c4.min():+.4f}..{c4.max():+.4f} median {np.median(c4):+.4f}')
for lo in (40, 50, 60):
    m = L >= lo
    lf, inf_, wf = fitfree(L[m], Cf[m], BASES['E'], w0)
    tb = BASES['E'] + [(0.5, 1)]
    x = Cf[m, 2] - C2INF; LL = L[m]
    lim = {2: C2INF, 3: C3INF}
    for k in (4, 5):
        e = ecoef(LL, w0, k - 2)
        y = Cf[m, k] + sum(e[j] * (Cf[m, k - j] - lim[k - j]) for j in range(1, k - 1))
        X = np.column_stack([np.ones_like(LL), x] + [LL ** (-p) * np.log(LL) ** j for p, j in tb])
        p, r_, g_ = solve(X, y); lim[k] = p[0]
        if k == 5: czh = p[-1]; r5 = r_
    print(f'lo={lo}: E+free_exp C5 miss {lf[5]-EX5:+.3f} (w3 fit {wf[3]:.0f}, res5 {inf_[5][0]:.1e}) | E+zh C5 miss {lim[5]-EX5:+.3f} res5 {r5:.1e}, zh coef {czh:.1f} -> implied w3 shift {czh/0.2795:+.0f} (w3_eff {w0[3]+czh/0.2795:.0f})')
