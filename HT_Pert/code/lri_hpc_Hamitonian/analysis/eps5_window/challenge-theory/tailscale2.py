"""Scale argument in the joint model's own targets y_k = C_k(L) - off_k (e-series subtracted), corrected data,
with lim_j set to exact (C2,C3,C4) so that y_k(L) - exact_k is the tail the fit must extrapolate."""
import sys, json
sys.dont_write_bytecode = True
import numpy as np
EXT = '<PROJECT>/lri_hpc_Hamitonian/analysis/extended'
AN = '<PROJECT>/lri_hpc_Hamitonian/analysis'
sys.path.insert(0, EXT); sys.path.insert(0, AN)
from analyze_joint import load, C2, C3, eseries
R = '<TMP>/scratchpad/eps5/reconcile'
EX = {2: C2, 3: C3, 4: 45.42488010356, 5: -731.13947662454}
T = {int(k): v for k, v in json.load(open(R + '/dC_reconciled.json')).items()}
th = load(['thermal_new.json', 'prior_c7/C7_completed_runs.json', 'C7_extension.json'])
L = np.array([r['cutoff'] for r in th], float); C = np.array([r['C'][:6] for r in th])
col = lambda k: np.array([T[int(l)][k] for l in L])
X = C.copy(); X[:, 4] += col('dC4_Dconn'); X[:, 5] += col('dC5_Dconn')
ex = json.load(open(EXT + '/extended_summary.json'))
w = {int(k): v for k, v in ex['gap_reference']['extended'].items()}
print('omega', w)
for k in (3, 4, 5):
    e = eseries(L, w, k - 2)
    off = np.zeros(len(L))
    for j in range(1, k - 1):
        off -= e[j] * (X[:, k - j] - EX[k - j])
    y = X[:, k] - off
    for l in (40, 70, 118):
        i = int(np.where(L == l)[0][0])
        print(f'k={k} L={l}: C_k(L)-exact = {X[i,k]-EX[k]:+.4f}   y_k(L)-exact = {y[i]-EX[k]:+.5f}')
