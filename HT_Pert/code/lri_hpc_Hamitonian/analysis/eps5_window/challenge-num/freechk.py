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
rng = np.random.default_rng(3)
for lo in (40, 50, 60, 70):
    m = L >= lo
    for b in ('A', 'B', 'D'):
        lr, ir, _ = fitfree(L[m], C[m], BASES[b], w0)
        lf, inf_, wf = fitfree(L[m], Cf[m], BASES[b], w0)
        print(f'lo={lo} {b}+free: raw C5 {lr[5]:.3f} corr {lf[5]:.3f} miss {lf[5]-EX5:+.3f} res5 {inf_[5][0]:.1e} gain {inf_[5][1]:.1e} w3 fitted {wf[3]:.1f} (gap ref {w0[3]:.1f})')
# noise test with realistic relative noise 5e-14 for E+h,zh and E at lo=40,50,60
for lo in (30, 40, 50, 60):
    m = L >= lo
    for name, tb in (('E', BASES['E']), ('E+h,zh', BASES['E'] + [(0.5, 0), (0.5, 1)])):
        base = fit(L[m], Cf[m], tb, tb, w0)[0]
        sc = []
        for t in range(60):
            D = Cf.copy(); D[:, 4:6] += rng.normal(0, 1, (len(L), 2)) * 5e-14 * np.abs(Cf[:, 4:6])
            sc.append(fit(L[m], D[m], tb, tb, w0)[0][5] - base[5])
        print(f'lo={lo} {name}: C5 miss {base[5]-EX5:+.4f}  C4 miss {base[4]-EX4:+.5f}  noise sd (5e-14 rel) {np.std(sc):.4f}')
