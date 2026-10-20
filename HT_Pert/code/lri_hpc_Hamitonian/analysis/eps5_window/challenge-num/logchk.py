import sys; sys.dont_write_bytecode=True
import numpy as np, json
from myfit import *
L, C = rows()
T = {int(k): v for k, v in json.load(open(RC + '/dC_reconciled.json')).items()}
w = {int(k): v for k, v in json.load(open(EXT + '/extended_summary.json'))['gap_reference']['extended'].items()}
col = lambda key: np.array([T[int(l)][key] for l in L])
z = np.log(L); a = 1/17496.; b5 = 5.5388e-4
d4 = col('dC4_Dconn'); d5 = col('dC5_Dconn')
# C4 residuals with log scanned: data C4 + d4 - c*a*z for c in (0 = full, 1 = MS, 2, -1); and raw
for lo in (40, 60, 70):
    m = L >= lo
    for b in ('A', 'D', 'E'):
        s = f'{b} lo={lo}: res4 raw {fit(L[m], C[m], BASES[b], BASES[b], w)[1][4][0]:.1e}'
        for c in (-1, 0, 1, 2):
            X = C.copy(); X[:, 4] += d4 - c * a * z; X[:, 5] += d5 - (b5 - 2 * a) * z * c
            lim, info = fit(L[m], X[m], BASES[b], BASES[b], w)
            s += f' | c={c}: C4 {lim[4]:.5f} res4 {info[4][0]:.1e} C5 {lim[5]:.3f} res5 {info[5][0]:.1e}'
        print(s)
