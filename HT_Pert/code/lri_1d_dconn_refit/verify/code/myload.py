"""Verifier (hi72) own loader. Independent of delta/joint/MI code.
raw C0..C7: thermal_d7 (L=2..118); raw C8: lri_c8 'raw' (L=2..92); lri_c8 lower orders kept separately.
dC4,dC5: dC_reconciled.json (exact, every even L to 128).
dC6..dC8: S10 dconn - old raw at L<=44 (whole_model_coefficients.csv) and S10 production CSV at 46..72.
S10 full C per L: archive csv (L<=44) + s10_production/dconn_L*_d8.json (46..72).
"""
import json, csv, math, glob, os
import numpy as np
R = '<PROJECT>'
DJ = R + '/lri_ht_c8_symmetry/results/2026-10_symmetry/extrapolation/data.json'
RC = R + '/lri_hpc_Hamitonian/analysis/eps5_window/reconcile/dC_reconciled.json'
S10 = R + '/lri_1d_coefficient_flow_review/lri_d1_full_coefficient_flow/results/whole_model_coefficients.csv'
S10P = R + '/lri_1d_coefficient_flow_review/s10_production'
D7 = R + '/lri_hpc_Hamitonian/analysis/eh_review/physics-impact/d7_all.json'
REF = {4: 45.42488010356, 5: -731.13947662454, 6: 14331.68703277, 7: -322550.0, 8: 8066723.0}
SCR = '<TMP>/scratchpad/dconn_refit72'


def load():
    d = json.load(open(DJ))
    th = {int(k): np.array(v, float) for k, v in d['thermal_d7'].items()}
    c8 = {int(k): np.array(v, float) for k, v in d['raw'].items()}
    vac = {int(k): np.array(v, float) for k, v in d['vacuum_only'].items()}
    rc = {int(k): v for k, v in json.load(open(RC)).items()}
    s10C = {}; dC678 = {}
    for r in csv.DictReader(open(S10)):
        if r['scheme'] != 'dconn':
            continue
        L = int(r['Lambda'])
        s10C[L] = np.array([float(r['C%d' % k]) for k in range(9)])
        dC678[L] = {k: float(r['dconn_minus_raw_C%d' % k]) for k in (4, 5, 6, 7, 8)}
    for r in csv.DictReader(open(S10P + '/dconn_minus_raw_L46_72.csv')):
        L = int(r['L'])
        dC678[L] = {k: float(r['dC%d' % k]) for k in (6, 7, 8)}
    for p in glob.glob(S10P + '/dconn_L*_d8.json'):
        a = json.load(open(p))
        s10C[int(a['cutoff'])] = np.array(a['C'], float)
    return dict(th=th, c8=c8, vac=vac, rc=rc, s10C=s10C, dC678=dC678)


def fd_noise(y, orders=range(3, 12)):
    y = np.asarray(y, float); out = {}
    for k in orders:
        if len(y) - k < 3:
            break
        dd = np.diff(y, k)
        out[k] = math.sqrt(np.mean(dd ** 2)) / math.sqrt(math.comb(2 * k, k))
    return out
