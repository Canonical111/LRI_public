"""Variant that frees the leading L^-1/2 and L^-1/2 log L tail at every order (reconciler's 'E+L^-0.5,zL^-0.5'):
C4 and C5 together, with C4 free and with C4 fixed to exact; plus the same for D and B bases."""
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
out = []
for base in ('B', 'D', 'E'):
    tk = lambda k, b=base: MODELS[b] + [(0.5, 0), (0.5, 1)]
    for lo in (30, 40, 50, 60, 70):
        m = (L >= lo) & (L <= 118)
        try:
            lim, d = thermal_fit(L[m], X[m], w, tk, maxorder=5)
            limx, dx = thermal_fit(L[m], X[m], w, tk, fixed={4: EX4}, maxorder=5)
        except ValueError:
            continue
        out.append(dict(base=base, lo=lo, C4=lim[4], C5=lim[5], C5fix=limx[5], res4=d[4]['max_residual'], res5=d[5]['max_residual'],
                        res4fix=dx[4]['max_residual'], gain5=d[5].get('intercept_gain_l1')))
        o = out[-1]
        print(f"{base}+L^-1/2,zL^-1/2 lo={lo}: C4 miss {o['C4']-EX4:+.4f} C5 miss {o['C5']-EX5:+.3f} | C4:=exact -> C5 miss {o['C5fix']-EX5:+.3f} "
              f"(res4 {o['res4']:.1e}->{o['res4fix']:.1e}, res5 {o['res5']:.1e}, gain5 {o['gain5']:.1e})")
json.dump(out, open('freelead.json', 'w'), indent=1)
