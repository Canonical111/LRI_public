import sys; sys.dont_write_bytecode=True
import numpy as np, json
from myfit import *
L, C = rows()
T = {int(k): v for k, v in json.load(open(RC + '/dC_reconciled.json')).items()}
w = {int(k): v for k, v in json.load(open(EXT + '/extended_summary.json'))['gap_reference']['extended'].items()}
col = lambda key: np.array([T[int(l)][key] for l in L])
f4 = col('dC4_g2D'); s4 = col('shift4'); g5 = col('dC5_g2D'); bub = col('dC5_bubble'); d5 = col('dC5_Dconn')
def mk(a4, a5):
    X = C.copy(); X[:, 4] += a4; X[:, 5] += a5; return X
sets = {'raw': C, 'g2D(pkg)': mk(f4, g5), 'g2D3W': mk(f4, g5 + bub), 'Dconn': mk(f4 + s4, d5)}
VAR = {'E+h,zh': BASES['E'] + [(0.5, 0), (0.5, 1)], 'B+zh': BASES['B'] + [(0.5, 1)], 'D+zh': BASES['D'] + [(0.5, 1)], 'F+zh': BASES['F'] + [(0.5, 1)],
       'E+zh': BASES['E'] + [(0.5, 1)], 'B+zh,L^-2.5': BASES['B'] + [(0.5, 1), (2.5, 0)], 'E (ref)': BASES['E'], 'E+z2/L,z3/L': BASES['E'] + [(1, 2), (1, 3)]}
for lo in (30, 40, 50, 60):
    m = L >= lo
    for name, tb in VAR.items():
        s = f'lo={lo} {name:12s}'
        for k, D in sets.items():
            lim, info = fit(L[m], D[m], tb, tb, w)
            s += f' | {k}: C4 {lim[4]-EX4:+.4f} C5 {lim[5]-EX5:+.3f}'
        lim, info = fit(L[m], sets['Dconn'][m], tb, tb, w)
        s += f' | res4 {info[4][0]:.1e} res5 {info[5][0]:.1e} gain5 {info[5][1]:.1e}'
        print(s)
# coefficient sizes for E+h,zh at lo=40 (C5 fit)
m = L >= 40; tb = VAR['E+h,zh']; D = sets['Dconn'][m]; LL = L[m]
x = D[:, 2] - C2INF
lim = {2: C2INF, 3: C3INF}
for k in (4, 5):
    e = ecoef(LL, w, k - 2)
    y = D[:, k] + sum(e[j] * (D[:, k - j] - lim[k - j]) for j in range(1, k - 1))
    X = np.column_stack([np.ones_like(LL), x] + [LL ** (-p) * np.log(LL) ** j for p, j in tb])
    p, res, gain = solve(X, y); lim[k] = p[0]
    contrib = {('1',): p[0], ('x',): p[1] * x[-1]}
    print(f'k={k} params:', ' '.join(f'{nm}={v:.4g}' for nm, v in zip(['c', 'x'] + [f'L^-{a}z^{b}' for a, b in tb], p)))
    print('   term values at L=118:', ' '.join(f'{v:.3g}' for v in (X[-1] * p)))
