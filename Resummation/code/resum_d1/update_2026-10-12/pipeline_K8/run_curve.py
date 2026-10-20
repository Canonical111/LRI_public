#!/usr/bin/env python3
"""Stage 1: CB curves, prescription bands and coefficient responses for K = 4..8 (analogue of lri_curve/calculate.py).

For every K and both endpoint modes (endpoint_v, endpoint_epsilon) and for the K-independent direct series:
  orders 6,7,8 x b 0..6 x alpha -2..2 (wide scan), core band = orders 6-8 x b 2,3,4 x alpha -1,0,1,
  b=3, alpha=0 curves L6, L7, L8, action variations a/a_inst = 0.8, 0.9, 1.1, 1.2,
  unit responses to the coefficient allowances (C6 4.9e-7, C7 41, C8 33000) and their absolute sum.
Envelope = union of the endpoint_v core bands for K = 5..8 (sensitivity, not a confidence interval).
Validation: formal series checks, GL-240 vs adaptive and GL-120 at 6 points, 65-digit integrals at 2 points,
K=4 regression against the archived curve table inputs/curve.csv (all CB columns).
Outputs in results/: curve_K.csv, key_points_K.csv, parameter_scan_K.csv, curve_validation.json, curve_metadata.json.
No HT, NRG or MC value is read.
2026-10-13: C8 and its allowance from the C8(1) switch (cbk.py); outputs in cbk.RES. New column direct_L3: CB3 of the
GFF series through C_3 only (direct, b=3, alpha=0; Figure 01 left panel). With LRI_C8_1=previous the K=4
regression covers every archived CB column as before; with LRI_C8_1=final the archived table (previous C8) is matched
exactly by the C8-independent columns (orders 6, 7 and the C6/C7 responses) and by the C8 response rescaled by the
allowance ratio, and the change of every C8-dependent column is reported (curve_validation.json).
"""
import csv, json, math, sys, time
from pathlib import Path
import numpy as np
import mpmath as mp
import cbk

HERE = Path(__file__).resolve().parent; OUT = cbk.RES; OUT.mkdir(parents=True, exist_ok=True)
ARCH = HERE/'inputs/archived_curve.csv'
t0 = time.time()
print('Started; A_epsilon =', mp.nstr(cbk.ACTION, 22), flush=True)
print('C =', [mp.nstr(c, 17) for c in cbk.C], flush=True)
print('C^SR =', [mp.nstr(cbk.CSR[k], 17) for k in range(9)], flush=True)
print('C8 switch:', json.dumps(cbk.SW.describe()), flush=True)
X = cbk.X; XKEY = cbk.XKEY
bgrid = [0, 1, 2, 3, 4, 5, 6]; agrid = [-2, -1, 0, 1, 2]
curves = {}; params = []; validation = []; summary = {}
jobs = [('direct', None)]+[(m, K) for K in cbk.KS for m in ('endpoint_epsilon', 'endpoint_v')]
for mode, K in jobs:
    Kc = 4 if K is None else K
    tag = mode if K is None else '%s_K%d' % (mode, K)
    core, wide = [], []
    for b in bgrid:
        for alpha in agrid:
            for order in (6, 7, 8):
                vals = cbk.dimension(mode, order, b, alpha, x=X, K=Kc)
                wide.append(vals)
                if b in (2, 3, 4) and alpha in (-1, 0, 1):
                    core.append(vals)
                params.append({'mode': mode, 'K': K if K is not None else '', 'order': order, 'b': b, 'alpha': alpha,
                               **{'x_'+str(x): float(vals[np.searchsorted(X, x)]) for x in XKEY}})
                if b == 3 and alpha == 0:
                    curves[tag+'_L'+str(order)] = vals
    curves[tag+'_core_min'] = np.min(core, 0); curves[tag+'_core_max'] = np.max(core, 0)
    curves[tag+'_wide_min'] = np.min(wide, 0); curves[tag+'_wide_max'] = np.max(wide, 0)
    for fac in (.8, .9, 1.1, 1.2):
        curves[tag+'_a_factor_'+str(fac)] = cbk.dimension(mode, 8, afactor=fac, x=X, K=Kc)
    shifts = []
    for k, allowance in cbk.ALLOWANCES:
        c = cbk.C.copy(); c[k] += allowance
        dy = cbk.dimension(mode, 8, c=c, x=X, K=Kc)-curves[tag+'_L8']
        curves[tag+'_shift_C'+str(k)] = dy; shifts.append(abs(dy))
    curves[tag+'_input_allowance_sum'] = np.sum(shifts, 0)
    # formal and quadrature validation at the b=3, alpha=0 baseline
    cs = cbk.series(mode, 8, K=Kc); A = cbk.pref(mode); p = cbk.polynomial(cs, 3, 0, A)
    err = cbk.formal_check(cs, 3, 0, A, p); assert err < 1e-48, (tag, err)
    fac = (lambda x: 1.) if mode == 'direct' else (lambda x: (4*x)**cbk.power(Kc))
    for x in (0, .025, .1, .2, .249, .25):
        arg = float(cbk.argument(mode, x))
        ad, aderr = cbk.adaptive_integral(p, 3, 0, A, arg)
        gl = float(cbk.integral_grid(p, 3, 0, A, [arg])[0]); gl120 = float(cbk.integral_grid(p, 3, 0, A, [arg], 120)[0])
        validation.append({'curve': tag, 'x': x, 'formal_relative': err,
                           'GL240_minus_adaptive_dimension': fac(x)*(gl-ad),
                           'GL240_minus_GL120_dimension': fac(x)*(gl-gl120), 'adaptive_error_dimension': fac(x)*aderr})
        assert abs(fac(x)*(gl-ad)) < 2e-9, (tag, x, gl-ad)
    for x in (0, .1):
        arg = float(cbk.argument(mode, x))
        value = cbk.mp_integral(p, 3, 0, A, arg); value64 = cbk.integral_grid(p, 3, 0, A, [arg])[0]
        e = float(fac(x)*abs(value-value64))
        validation.append({'curve': tag, 'x': x, 'mp65_remainder': mp.nstr(value, 40), 'mp65_check_dimension_error': e})
        assert e < 2e-9, (tag, x, e)
    yy = curves[tag+'_L8']; i = int(np.argmin(yy))
    summary[tag] = {'minimum_grid_x': float(X[i]), 'minimum_grid_y': float(yy[i]), 'at_zero': float(yy[0]),
                    'at_gaussian': float(yy[-1]), 'core_width_at_0.1': float((curves[tag+'_core_max']-curves[tag+'_core_min'])[np.searchsorted(X, .1)])}
    print('Completed', tag, summary[tag], '%.1fs' % (time.time()-t0), flush=True)

# 2026-10-13: CB3 of the GFF series alone (C_0..C_3, the three-loop coefficients known before this work), same direct
# epsilon prescription as direct_L8 (b=3, alpha=0, A_eps); independent of C8. Figure 01 left panel.
curves['direct_L3'] = cbk.dimension('direct', 3, 3, 0, x=X)
p3 = cbk.polynomial(cbk.series('direct', 3), 3, 0, cbk.ACTION); err3 = cbk.formal_check(cbk.series('direct', 3), 3, 0, cbk.ACTION, p3)
assert err3 < 1e-48
for x in (0, .0005, .05, .1, .15, .2, .249, .25):
    arg = float(cbk.argument('direct', x)); ad, aderr = cbk.adaptive_integral(p3, 3, 0, cbk.ACTION, arg)
    gl = float(cbk.integral_grid(p3, 3, 0, cbk.ACTION, [arg])[0])
    validation.append({'curve': 'direct_L3', 'x': x, 'formal_relative': err3, 'GL240_minus_adaptive_dimension': gl-ad})
    assert abs(gl-ad) < 2e-9, ('direct_L3', x, gl-ad)
mpv = cbk.mp_integral(p3, 3, 0, cbk.ACTION, float(cbk.argument('direct', .1)))
validation.append({'curve': 'direct_L3', 'x': .1, 'mp65_remainder': mp.nstr(mpv, 40),
                   'mp65_check_dimension_error': float(abs(mpv-curves['direct_L3'][np.searchsorted(X, .1)]))})
CB3_EXPECTED = {.0005: .4555, .05: .4590, .1: .4636, .15: .4700, .2: .4799, .249: .4993}   # coordinator's gff_only_v.py values
assert all(abs(curves['direct_L3'][np.searchsorted(X, xx)]-v) < 5e-5 for xx, v in CB3_EXPECTED.items())
print('CB3 (GFF only, C_0..C_3):', {xx: round(float(curves['direct_L3'][np.searchsorted(X, xx)]), 6) for xx in CB3_EXPECTED}, flush=True)

# K=5..8 envelope (endpoint_v core bands), as in update_2026-10-12/prepare_fig05_K8.py
curves['envelope_K5_8_min'] = np.min([curves['endpoint_v_K%d_core_min' % K] for K in (5, 6, 7, 8)], 0)
curves['envelope_K5_8_max'] = np.max([curves['endpoint_v_K%d_core_max' % K] for K in (5, 6, 7, 8)], 0)

# K=4 regression against the archived curve table (every CB column it has)
arch = list(csv.DictReader(ARCH.open()))
ax = np.array([float(r['Delta_sigma']) for r in arch]); assert np.max(abs(ax-X)) == 0
regression = {}; c8_change = {}
ratio = float(cbk.C8IN['allowance'])/cbk.ALLOWANCE_C8_PREVIOUS
for col in arch[0]:
    if col in ('Delta_sigma', 'epsilon') or 'PB' in col or col.startswith(('endpoint2', 'SRI8', 'archived', 'uniformized', 'strong')):
        continue
    mode = next(m for m in ('endpoint_epsilon', 'endpoint_v', 'direct') if col.startswith(m))
    new = col if mode == 'direct' else col.replace(mode, mode+'_K4', 1)
    a = np.array([float(r[col]) for r in arch])
    if cbk.MODE == 'previous' or col.endswith(('_L6', '_L7', '_shift_C6', '_shift_C7')):
        regression[col] = float(np.max(abs(curves[new]-a)))
    elif col.endswith('_shift_C8'):                      # linear response: rescales with the allowance
        regression[col+' (x allowance ratio)'] = float(np.max(abs(curves[new]-ratio*a)))
    else:                                                # depends on the C8 value or allowance: report the change
        c8_change[col] = float(np.max(abs(curves[new]-a)))
worst = max(regression.values())
print('K=4 regression vs archived curve.csv: %d columns, max |diff| = %.3e' % (len(regression), worst), flush=True)
if c8_change:
    print('K=4 C8-dependent columns (%d): max |new - archived| = %.3e' % (len(c8_change), max(c8_change.values())), flush=True)
assert worst < 1e-12, worst

rows = [{'Delta_sigma': float(x), 'epsilon': float(1-4*x), **{k: float(v[i]) for k, v in curves.items()}}
        for i, x in enumerate(X)]
def writecsv(name, rr):
    with (OUT/name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rr[0])); w.writeheader(); w.writerows(rr)
writecsv('curve_K.csv', rows)
writecsv('key_points_K.csv', [rows[np.searchsorted(X, x)] for x in XKEY])
writecsv('parameter_scan_K.csv', params)
(OUT/'curve_validation.json').write_text(json.dumps({'C8_switch': cbk.SW.describe(), 'quadrature': validation, 'K4_regression_vs_archived_curve_csv': regression,
    'K4_C8_dependent_columns_change_vs_archived': c8_change,
    'K4_regression_max': worst, 'max_GL240_minus_adaptive': max(abs(r['GL240_minus_adaptive_dimension']) for r in validation if 'GL240_minus_adaptive_dimension' in r),
    'max_mp65_check': max(r['mp65_check_dimension_error'] for r in validation if 'mp65_check_dimension_error' in r)}, indent=1))
(OUT/'curve_metadata.json').write_text(json.dumps({
    'coefficients': [str(c) for c in cbk.C], 'C_SR': {str(k): str(v) for k, v in cbk.CSR.items()},
    'A_epsilon': str(cbk.ACTION), 'A_v': str(cbk.ACTION/2), 'K_values': list(cbk.KS),
    'baseline': {'mode': 'endpoint_v', 'K': 8, 'order': 8, 'b': 3, 'alpha': 0, 'fitted_to_external_data': False},
    'archived_control': {'mode': 'endpoint_v', 'K': 4, 'order': 8, 'b': 3, 'alpha': 0},
    'core_scan': {'orders': [6, 7, 8], 'b': [2, 3, 4], 'alpha': [-1, 0, 1]},
    'wide_scan': {'orders': [6, 7, 8], 'b': bgrid, 'alpha': agrid},
    'envelope': 'union of the endpoint_v core bands for K=5..8; sensitivity range, not a confidence interval',
    'allowances': {str(k): str(a) for k, a in cbk.ALLOWANCES}, 'C8_switch': cbk.SW.describe(), 'summary': summary,
    'limitations': ['A is a candidate nearest singularity, not established.',
                    'C^SR_8 is numerical (independent value 242.83 shifts the K=8 curve by <= 3e-5).',
                    'Envelopes are sensitivity ranges, not confidence intervals.',
                    'b=3 is a chosen baseline, not a proven large-order exponent.',
                    'Coefficient allowances are empirical; summed absolute linear responses only.']}, indent=1))
print('KEY POINTS: x  CB8(K=8)  CB8(K=4)  env_lo  env_hi', flush=True)
for x in XKEY:
    i = np.searchsorted(X, x)
    print(x, *[round(float(curves[k][i]), 9) for k in ('endpoint_v_K8_L8', 'endpoint_v_K4_L8', 'envelope_K5_8_min', 'envelope_K5_8_max')], flush=True)
print('FINISHED stage 1 (curves) in %.1fs; all checks passed' % (time.time()-t0), flush=True)
