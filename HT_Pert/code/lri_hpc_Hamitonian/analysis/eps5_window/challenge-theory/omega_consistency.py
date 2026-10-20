"""Skeptic test: the joint model's gap input omega comes from the RAW phi^6 gap, which carries its own frozen-cutoff
window artifacts (omega2_raw = -5A + 1/54 exactly; omega3_raw includes the eps^3 window of the a0^6 state).
The thermal data are now window-corrected (Dconn).  Sensitivity of corrected C4/C5 to using window-free omega."""
import sys, json, math
sys.dont_write_bytecode = True
import numpy as np
EXT = '<PROJECT>/lri_hpc_Hamitonian/analysis/extended'
AN = '<PROJECT>/lri_hpc_Hamitonian/analysis'
sys.path.insert(0, EXT); sys.path.insert(0, AN)
from analyze_joint import MODELS, load, A
from diagnose_systematic import thermal_fit, const_terms
R = '<TMP>/scratchpad/eps5/reconcile'
EX4, EX5 = 45.42488010356, -731.13947662454
T = {int(k): v for k, v in json.load(open(R + '/dC_reconciled.json')).items()}
th = load(['thermal_new.json', 'prior_c7/C7_completed_runs.json', 'C7_extension.json'])
L = np.array([r['cutoff'] for r in th], float); C = np.array([r['C'][:6] for r in th])
ex = json.load(open(EXT + '/extended_summary.json'))
w0 = {int(k): v for k, v in ex['gap_reference']['extended'].items()}
print('omega2 used =', w0[2], ' -5A + 1/54 =', -5 * A + 1 / 54, ' -5A =', -5 * A)
col = lambda k: np.array([T[int(l)][k] for l in L])
X = C.copy(); X[:, 4] += col('dC4_g2D') + col('shift4'); X[:, 5] += col('dC5_Dconn')
cases = {'campaign (raw omega)': {}, 'omega2=-5A': {2: -5 * A}, 'omega2=-5A, omega3-0.146': {2: -5 * A, 3: w0[3] - 0.14603},
         'omega3-0.146 only': {3: w0[3] - 0.14603}, 'omega3-1.0': {3: w0[3] - 1.0}}
res = []
for lo in (40, 60, 70):
    m = (L >= lo) & (L <= 118)
    for name in ('A', 'B', 'D', 'E', 'F'):
        line = f'lo={lo} {name}:'
        for lab, dw in cases.items():
            w = dict(w0); w.update(dw)
            lim, d = thermal_fit(L[m], X[m], w, const_terms(name), maxorder=5)
            res.append(dict(lo=lo, b=name, case=lab, C4=lim[4], C5=lim[5], res4=d[4]['max_residual'], res5=d[5]['max_residual']))
            line += f" | {lab}: C4 {lim[4]-EX4:+.4f} C5 {lim[5]-EX5:+.3f} (r4 {d[4]['max_residual']:.0e}, r5 {d[5]['max_residual']:.0e})"
        print(line)
json.dump(res, open('omega_consistency.json', 'w'), indent=1)
