"""Scale argument: remaining tail at L=118 (corrected data minus exact) vs remaining miss, for C3 (known), C4, C5."""
import sys, json
sys.dont_write_bytecode = True
import numpy as np
EXT = '<PROJECT>/lri_hpc_Hamitonian/analysis/extended'
AN = '<PROJECT>/lri_hpc_Hamitonian/analysis'
sys.path.insert(0, EXT); sys.path.insert(0, AN)
from analyze_joint import load, C2, C3
R = '<TMP>/scratchpad/eps5/reconcile'
EX4, EX5 = 45.42488010356, -731.13947662454
T = {int(k): v for k, v in json.load(open(R + '/dC_reconciled.json')).items()}
th = load(['thermal_new.json', 'prior_c7/C7_completed_runs.json', 'C7_extension.json'])
L = np.array([r['cutoff'] for r in th], float); C = np.array([r['C'][:6] for r in th])
print('C2,C3 exact', C2, C3)
for l in (16, 40, 60, 70, 118):
    i = int(np.where(L == l)[0][0])
    c4 = C[i, 4] + T[l]['dC4_Dconn']; c5 = C[i, 5] + T[l]['dC5_Dconn']
    print(f"L={l}: C3(L)-C3 = {C[i,3]-C3:+.5f}  C4corr(L)-EX4 = {c4-EX4:+.4f}  C5corr(L)-EX5 = {c5-EX5:+.3f}   raw C5(L)={C[i,5]:.3f}")
# local effective slope of C5corr vs L^-1/2 and log
for a, b in ((60, 118), (90, 118)):
    ia = int(np.where(L == a)[0][0]); ib = int(np.where(L == b)[0][0])
    ca = C[ia, 5] + T[a]['dC5_Dconn']; cb = C[ib, 5] + T[b]['dC5_Dconn']
    print(f'C5corr({a})={ca:.3f} C5corr({b})={cb:.3f}  naive L^-1/2 two-point limit = {(cb*np.sqrt(b)-ca*np.sqrt(a))/(np.sqrt(b)-np.sqrt(a)):.2f}')
