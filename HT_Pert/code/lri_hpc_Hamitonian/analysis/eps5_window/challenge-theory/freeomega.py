"""Fitted omega3 in the free-exponent variants (which land near/above exact C5) vs the gap input omega3 = 556.2."""
import sys, json
sys.dont_write_bytecode = True
import numpy as np
EXT = '<PROJECT>/lri_hpc_Hamitonian/analysis/extended'
sys.path.insert(0, EXT)
from analyze_joint import MODELS, load, ThermalModel
R = '<TMP>/scratchpad/eps5/reconcile'
EX5 = -731.13947662454
T = {int(k): v for k, v in json.load(open(R + '/dC_reconciled.json')).items()}
th = load(['thermal_new.json', 'prior_c7/C7_completed_runs.json', 'C7_extension.json'])
L = np.array([r['cutoff'] for r in th], float); C = np.array([r['C'][:6] for r in th])
ex = json.load(open(EXT + '/extended_summary.json'))
w0 = {int(k): v for k, v in ex['gap_reference']['extended'].items()}
col = lambda k: np.array([T[int(l)][k] for l in L])
X = C.copy(); X[:, 4] += col('dC4_g2D') + col('shift4'); X[:, 5] += col('dC5_Dconn')
for lo in (40, 60, 70):
    m = (L >= lo) & (L <= 118)
    for name in ('A', 'B', 'D', 'E'):
        try:
            tm = ThermalModel(MODELS[name], w0, free_exponents=True).fit(L[m], X[m], maxorder=5)
        except ValueError:
            continue
        print(f'lo={lo} {name}+free: C5 miss {tm.lim[5]-EX5:+.3f}  fitted omega3 = {tm.w[3]:.2f} (gap input {w0[3]:.2f})')
