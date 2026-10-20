"""Skeptic test: corrected (Dconn_full) data, C5 intercept with lim4 free vs fixed to exact C4 (and vs fixed C4 +/- 0.01).
Shows how the joint-model e1 coupling transmits any remaining C4 extrapolation bias into C5."""
import sys, json
sys.dont_write_bytecode = True
import numpy as np
EXT = '<PROJECT>/lri_hpc_Hamitonian/analysis/extended'
AN = '<PROJECT>/lri_hpc_Hamitonian/analysis'
sys.path.insert(0, EXT); sys.path.insert(0, AN)
from analyze_joint import MODELS, load
from diagnose_systematic import thermal_fit, const_terms
R = '<TMP>/scratchpad/eps5/reconcile'
EX4, EX5 = 45.42488010356, -731.13947662454
T = {int(k): v for k, v in json.load(open(R + '/dC_reconciled.json')).items()}
th = load(['thermal_new.json', 'prior_c7/C7_completed_runs.json', 'C7_extension.json'])
L = np.array([r['cutoff'] for r in th], float); C = np.array([r['C'][:6] for r in th])
ex = json.load(open(EXT + '/extended_summary.json'))
w = {int(k): v for k, v in ex['gap_reference']['extended'].items()}
col = lambda k: np.array([T[int(l)][k] for l in L])
X = C.copy(); X[:, 4] += col('dC4_g2D') + col('shift4'); X[:, 5] += col('dC5_Dconn')
out = []
for lo in (40, 60, 70):
    m = (L >= lo) & (L <= 118)
    for name in ('A', 'B', 'D', 'E', 'F'):
        lim, d = thermal_fit(L[m], X[m], w, const_terms(name), maxorder=5)
        limx, dx = thermal_fit(L[m], X[m], w, const_terms(name), fixed={4: EX4}, maxorder=5)
        limp, _ = thermal_fit(L[m], X[m], w, const_terms(name), fixed={4: lim[4] + 0.001}, maxorder=5)
        slope = (limp[5] - lim[5]) / 0.001
        out.append(dict(lo=lo, b=name, C4=lim[4], C5=lim[5], C5_fixC4=limx[5], dC5_dlim4=slope,
                        res5=d[5]['max_residual'], res5_fix=dx[5]['max_residual'], res4_fix=dx[4]['max_residual'], res4=d[4]['max_residual']))
        o = out[-1]
        print(f"lo={lo} {name}: C4 miss {o['C4']-EX4:+.4f} C5 miss {o['C5']-EX5:+.3f} | C4:=exact -> C5 miss {o['C5_fixC4']-EX5:+.3f} "
              f"(dC5/dlim4 = {slope:+.1f}); res4 {o['res4']:.1e}->{o['res4_fix']:.1e}, res5 {o['res5']:.1e}->{o['res5_fix']:.1e}")
json.dump(out, open('fixc4.json', 'w'), indent=1)
