"""Final extrapolations with explicit tail forms (x = L^-1/2) + zero-constant hypothesis test."""
import json, math
import numpy as np
from analyze import load, prescriptions, BASES

D = load(); Ls = sorted(D)
P = {L: prescriptions(D[L]) for L in Ls}
sp = json.load(open('analysis_sp_table.json'))
def series(key, pres, k):
    if key.startswith('a'):
        n = int(key[1:]); Lk = sorted(int(L) for L in sp)
        return np.array(Lk, float), np.array([sp[str(L)][f'{pres}|{n}'][k] for L in Lk])
    Lk = [L for L in Ls if key in P[L][pres]]
    return np.array(Lk, float), np.array([P[L][pres][key][k] for L in Lk])

def fits(L, y, lmins=(16, 24, 32)):
    rows = []
    for bn, b in BASES.items():
        for lo in lmins:
            m = L >= lo
            X = np.array(b(L[m]**-.5, L[m])).T
            if m.sum() < X.shape[1] + 3: continue
            c = np.linalg.lstsq(X, y[m], rcond=None)[0]
            r1 = float(np.max(np.abs(X @ c - y[m])))
            # zero-constant hypothesis: same basis without the constant column
            X0 = X[:, 1:]; c0 = np.linalg.lstsq(X0, y[m], rcond=None)[0]
            r0 = float(np.max(np.abs(X0 @ c0 - y[m])))
            rows.append((bn, lo, c[0], r1, r0))
    return rows

W = {'dphi1': 1, 'dphi2': 1, 'dphi3': 1, 'dphi4': 1, 'd2phi': 1, 'd3phi': 2, 'P2N2desc': 1,
     'a4': 2, 'a5': 3, 'a6': 3}
out = {}
for key in ['dphi1', 'dphi2', 'd2phi', 'd3phi', 'a4', 'a5', 'a6', 'dphi3', 'dphi4', 'P2N2desc']:
    for k in (3, 4):
        for pres in ('raw', 'g2D', 'Dfull', 'Dconn'):
            L, y = series(key, pres, k)
            rows = fits(L, y)
            c = np.array([r[2] for r in rows])
            cen = np.mean([r[2] for r in rows if r[1] == 24 and r[0][0] in 'ab'])
            # hypothesis test summary (lmin=24, basis a): residual ratio
            ra = [r for r in rows if r[0][0] == 'a' and r[1] == 24][0]
            out[f'{key}|e{k}|{pres}'] = dict(W=W[key], Lmax=int(L[-1]), last=float(y[-1]), central=float(cen),
                                             lo=float(c.min()), hi=float(c.max()), sd=float(c.std()),
                                             res_with_const=ra[3], res_zero_const=ra[4])
            print(f'{key:8s} W={W[key]} e{k} {pres:6s} L={int(L[-1])}:{y[-1]:+.5f}  ->  {cen:+.5f} [{c.min():+.5f},{c.max():+.5f}] sd {c.std():.4f} | basis-a lmin24 maxres {ra[3]:.1e} vs const=0 {ra[4]:.1e}')
json.dump(out, open('final_fit.json', 'w'), indent=1)
