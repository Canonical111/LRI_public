#!/usr/bin/env python3
"""Fragment check 5: the numerical confirmation table of gdk:numerics, recomputed from the stored values.
Relative deviations are all taken against the 100-digit position-space (MB) values."""
import json, os
import mpmath as mp
mp.mp.dps = 120
HERE = os.path.dirname(os.path.abspath(__file__))
KG = os.path.abspath(os.path.join(HERE, '..', '..'))
ROOT = os.path.abspath(os.path.join(KG, '..'))
MB = json.load(open(os.path.join(KG, 'position_space', 'K_d_values_mb_D100.json')))['values']
REF = json.load(open(os.path.join(ROOT, 'references', 'reference_values.json')))['values']
RC = json.load(open(os.path.join(KG, 'refcheck', 'refcheck_values.json')))['values']
RP = json.load(open(os.path.join(KG, 'R_part', 'R_part_results.json')))
H5 = RP['5_K_d_from_tau_jet']['values']
LAU = RP['6_laurent_of_tR']['values']
K3 = mp.mpf(json.load(open(os.path.join(ROOT, '..', 'LRI_C5_d3', 'wf_K3', 'K3_value.json')))['K3'])
H3 = {}
for ds in ['0.8', '1.25', '2.75']:
    H3[ds] = json.load(open(os.path.join(KG, 'note_fragment', 'topmode', 'results', 'kjet3_B_d%s.json' % ds)))
G, z3, L2, pi = mp.catalan, mp.zeta(3), mp.log(2), mp.pi
exact = {'1': 128*G**2 + 24*pi**2*G - 4*pi**3*L2 - 28*(pi + 4*L2)*z3,
         '2': 32*G**2 - 28*z3*L2, '3': K3}

def psi(m, z): return mp.psi(m, z)
def s3(q):
    xs = []
    for h in range(1, 5):
        x = psi(h-1, 1) - (-1)**h*psi(h-1, 2*q)
        if h % 2: x -= mp.mpf(2)**(3-h)*psi(h-1, q)
        xs.append(x)
    x1, x2, x3, x4 = xs
    return (x1**4 + 6*x1**2*x2 + 4*x1*x3 + 3*x2**2 + x4)/24      # E_4 of fp:BellFinite

rows = []
fmt = lambda x: mp.nstr(x, 2, min_fixed=0, max_fixed=0)
for ds in ['0.8', '1', '1.25', '1.5', '2', '2.5', '2.75', '3']:
    q = mp.mpf(ds)/4
    K = mp.mpf(MB[ds]['K'])
    row = {'d': ds, 'K_MB_40': mp.nstr(K, 40, strip_zeros=False)}
    kd = 'd=' + ds
    if kd in REF:
        row['ref'] = fmt((mp.mpf(REF[kd]['K']['value']) - K)/K)
    if kd in RC:
        row['A'] = fmt((mp.mpf(RC[kd]['K']['value']) - K)/K)
    # full-precision (67-68 digit) production values; R_part_results.json rounds K_d_settingB to 47 digits
    K5 = mp.mpf(json.load(open(os.path.join(KG, 'R_part', 'prod', 'prod_B_d%s.json' % ds)))['K_d'])
    row['H5'] = fmt((K5 - K)/K)
    row['H5_vs_exact'] = fmt((K5 - exact[ds])/exact[ds]) if ds in exact else None
    if ds in H3:
        row['H3_minus_H5'] = fmt((mp.mpf(H3[ds]['K_d']) - K5)/K)
    row['H5_F2'] = H5[kd]['tE2_minus_1p5psi2']
    if ds in H3:
        row['H3'] = fmt((mp.mpf(H3[ds]['K_d']) - K)/K)
        row['H3_F2'] = H3[ds]['tE2_minus_1p5psi2']
    if ds in exact:
        row['MB_vs_exact'] = fmt((K - exact[ds])/exact[ds])
    U = psi(2, q)
    elem = U/8*(psi(0, 1) + psi(0, 2*q) + 4*psi(0, q))
    r3 = s3(q) + 4*(K - elem)
    row['r3_from_MB_30'] = mp.nstr(r3, 30)
    row['r3_Rpart_dev'] = fmt(mp.mpf(LAU[kd]['tau^3']) - r3)
    row['s3_30'] = mp.nstr(s3(q), 30)
    row['elem_30'] = mp.nstr(elem, 30)
    rows.append(row)
    print(row)
json.dump(rows, open(os.path.join(HERE, 'table.json'), 'w'), indent=1)
