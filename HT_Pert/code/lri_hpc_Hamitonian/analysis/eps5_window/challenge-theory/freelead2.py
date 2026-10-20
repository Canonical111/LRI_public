"""Which added freedom drives the C5 shift?  (i) L^-1/2, L^-1/2 log L at k=4 and 5 (as freelead.py);
(ii) same at k=5 only (C4 fit pre-registered); (iii) only L^-1/2 log L at k=5.  Corrected (Dconn_full) data."""
import sys, json
sys.dont_write_bytecode = True
import numpy as np
EXT = '<PROJECT>/lri_hpc_Hamitonian/analysis/extended'
AN = '<PROJECT>/lri_hpc_Hamitonian/analysis'
sys.path.insert(0, EXT); sys.path.insert(0, AN)
from analyze_joint import MODELS, load
from diagnose_systematic import thermal_fit
R = '<TMP>/scratchpad/eps5/reconcile'
EX4, EX5 = 45.42488010356, -731.13947662454
T = {int(k): v for k, v in json.load(open(R + '/dC_reconciled.json')).items()}
th = load(['thermal_new.json', 'prior_c7/C7_completed_runs.json', 'C7_extension.json'])
L = np.array([r['cutoff'] for r in th], float); C = np.array([r['C'][:6] for r in th])
ex = json.load(open(EXT + '/extended_summary.json'))
w = {int(k): v for k, v in ex['gap_reference']['extended'].items()}
col = lambda k: np.array([T[int(l)][k] for l in L])
X = C.copy(); X[:, 4] += col('dC4_g2D') + col('shift4'); X[:, 5] += col('dC5_Dconn')
fam = {'(i) k4+k5: L^-1/2, zL^-1/2': lambda b: (lambda k: MODELS[b] + [(0.5, 0), (0.5, 1)]),
       '(ii) k5 only: L^-1/2, zL^-1/2': lambda b: (lambda k: MODELS[b] + ([(0.5, 0), (0.5, 1)] if k == 5 else [])),
       '(iii) k5 only: zL^-1/2': lambda b: (lambda k: MODELS[b] + ([(0.5, 1)] if k == 5 else []))}
res = []
for lab, mk in fam.items():
    for lo in (50, 60, 70):
        m = (L >= lo) & (L <= 118)
        line = f'{lab:32s} lo={lo}:'
        for b in 'ABCDEF':
            lim, d = thermal_fit(L[m], X[m], w, mk(b), maxorder=5)
            res.append(dict(fam=lab, lo=lo, b=b, C4=lim[4], C5=lim[5], res5=d[5]['max_residual'], gain=d[5]['intercept_gain_l1']))
            line += f" {b} {lim[5]-EX5:+.3f}({d[5]['max_residual']:.0e},g{d[5]['intercept_gain_l1']:.0e})"
        print(line)
json.dump(res, open('freelead2.json', 'w'), indent=1)
