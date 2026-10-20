import sys; sys.dont_write_bytecode=True
import numpy as np, json
from myfit import *
L, C = rows()
T = {int(k): v for k, v in json.load(open(RC + '/dC_reconciled.json')).items()}
w = {int(k): v for k, v in json.load(open(EXT + '/extended_summary.json'))['gap_reference']['extended'].items()}
col = lambda key: np.array([T[int(l)][key] for l in L])
d4 = col('dC4_Dconn'); d5 = col('dC5_Dconn')
Cf = C.copy(); Cf[:, 4] += d4; Cf[:, 5] += d5
rng = np.random.default_rng(1)
VAR = {'E': BASES['E'], 'E+h': BASES['E'] + [(0.5, 0)], 'E+h,zh': BASES['E'] + [(0.5, 0), (0.5, 1)],
       'D+h': BASES['D'] + [(0.5, 0)], 'D+h,zh': BASES['D'] + [(0.5, 0), (0.5, 1)], 'A+h': BASES['A'] + [(0.5, 0)],
       'E+z2/L': BASES['E'] + [(1, 2)], 'E+z2/L,z3/L': BASES['E'] + [(1, 2), (1, 3)]}
for lo in (30, 40, 50, 60):
    m = L >= lo
    for name, tb in VAR.items():
        out = []
        for lab, D in (('raw', C), ('corr', Cf)):
            lim, info = fit(L[m], D[m], tb, tb, w)
            out.append((lim[4], lim[5], info[4][0], info[5][0], info[5][1]))
        # noise test: perturb C5 by gaussian noise of size = raw res5/2 (relative noise model 1e-13*|C5| as alt)
        sc = []
        for t in range(30):
            D = Cf.copy(); D[:, 5] += rng.normal(0, 1, len(L)) * 2e-13 * np.abs(Cf[:, 5]); D[:, 4] += rng.normal(0, 1, len(L)) * 2e-13 * np.abs(Cf[:, 4])
            sc.append(fit(L[m], D[m], tb, tb, w)[0][5])
        r, c = out
        print(f'lo={lo} {name:12s} C4 raw {r[0]:.5f} corr {c[0]:.5f} (miss {c[0]-EX4:+.5f}, res4 {c[2]:.1e}) | C5 raw {r[1]:.3f} corr {c[1]:.3f} miss {c[1]-EX5:+.3f} res5 {c[3]:.1e} gain {c[4]:.1e} noise(2e-13 rel) sd {np.std(sc):.3f}')
