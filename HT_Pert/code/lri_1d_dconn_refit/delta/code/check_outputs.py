"""Consistency checks of the hi=72 outputs: corrected = raw + dC; exact flags; S10 Dconn reproduced at 46..72;
lens loaders run on the new files; MI explicit-member pick reproduces the floor-medoid file; roughness of the
assembled smooth sequences across the 72/74 seam."""
import sys, os, json
from math import comb
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'lens_compat'))
import numpy as np
O = os.path.join(HERE, '..', 'out'); T = 'delta_v1_hi72'
P = '<PROJECT>/lri_1d_coefficient_flow_review/s10_production'
SC = {L: json.load(open(P + '/dconn_L%d_d8.json' % L))['C'] for L in range(46, 73, 2)}

def sig(y):
    s = {kk: float(np.sqrt(np.mean(np.diff(y, kk) ** 2)) / np.sqrt(comb(2 * kk, kk))) for kk in range(3, min(len(y) - 3, 22))}
    return min(s.values())

for name in ('', '_medoid', '_floormean', '_floormedoid', '_floormean_s46'):
    d = json.load(open(f'{O}/{T}{name}_corrected.json'))
    S = d['sequences']; worst = 0.; nex = {}; s10dev = 0.; rough = {}
    for k in range(9):
        for r in S['C%d' % k]:
            worst = max(worst, abs(r['raw'] + r['dC'] - r['corrected']) / max(1, abs(r['corrected'])))
        nex[k] = (max(r['L'] for r in S['C%d' % k] if r['exact']), max(r['L'] for r in S['C%d' % k]))
        if k >= 6:
            for r in S['C%d' % k]:
                if r['L'] in SC and r['exact']:
                    # k<=7 raw is thermal_d7, so corrected - S10 = thermal_d7 - lri_c8 raw (<= 1.5e-9 at C7)
                    s10dev = max(s10dev, abs(r['corrected'] - SC[r['L']][k]) / abs(SC[r['L']][k]))
            Ls = [r['L'] for r in S['C%d' % k]]; dc = np.array([r['dC'] for r in S['C%d' % k]])
            w = [i for i, L in enumerate(Ls) if 60 <= L <= 90]
            rough[k] = sig(dc[w])
    print('%-16s max|raw+dC-corr|/|corr| %.1e; (last exact L, last L) %s; max rel |corr - S10 Dconn| at exact 46..72 %.1e; roughness dC6..8 over 60..90 %s' % (
        name or '(published)', worst, {k: nex[k] for k in (5, 6, 7, 8)}, s10dev, ' '.join('%.1e' % rough[k] for k in (6, 7, 8))))

# MI lens loader: default medoid rule and explicit floor-medoid pick
sm = json.load(open(f'{O}/{T}_smooth.json'))
fm = {k: sm['new']['dC%d' % k]['floormedoid_member']['member'] for k in (6, 7, 8)}
pick = 'k6:%d,k7:%d,k8:%d' % (fm[6], fm[7], fm[8])
os.environ['DCONN_CENTRAL'] = pick
import mi_common
mi_common.VAR_PATH = f'{O}/{T}_variants.json'
D = mi_common.load_corrected(f'{O}/{T}_corrected.json')
ref = json.load(open(f'{O}/{T}_floormedoid_corrected.json'))['sequences']
dev = max(abs(D['dC'][k][r['L']] - r['dC']) for k in (6, 7, 8) for r in ref['C%d' % k])
print('MI loader with DCONN_CENTRAL=%s reproduces the floor-medoid file: max |dC diff| %.1e; members %s' % (pick, dev, D['central_members']))
import joint_data
J = joint_data.load(corr=f'{O}/{T}_corrected.json', vfull=f'{O}/variants_full_hi72.json', with_perts=True)
print('joint loader OK: info', json.dumps(J['info']), 'n perts', len(J['perts']))
