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
for base in ('A', 'B', 'C', 'D', 'E', 'F'):
    tk = lambda k, b=base: MODELS[b] + [(0.5, 0), (0.5, 1)]
    s = f'{base}+L^-1/2,zL^-1/2:'
    for lo in (30, 40, 50, 60, 70):
        m = (L >= lo) & (L <= 118)
        try:
            lr, dr = thermal_fit(L[m], C[m], w, tk, maxorder=5); lc, dc = thermal_fit(L[m], X[m], w, tk, maxorder=5)
        except ValueError:
            continue
        s += f" lo={lo}: raw {lr[5]-EX5:+.3f} corr {lc[5]-EX5:+.3f} (C4 {lc[4]-EX4:+.4f}, r5 {dc[5]['max_residual']:.0e}, g {dc[5]['intercept_gain_l1']:.0e});"
    print(s)
