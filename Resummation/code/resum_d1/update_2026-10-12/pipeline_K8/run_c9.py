#!/usr/bin/env python3
"""Stage 3: hypothetical C9 sensitivity for K = 4..8 (analogue of reproduction/c9_value/assess.py). NOT a C9 calculation.

For each K: C9 implied by the order-8 CB approximant (b = 0,2,3,4) and by every admissible PB shape ([4/4], [5/3],
[3/5]) of the same series; the fixed-prescription kernel dF/dC9 (b=3, alpha=0); the CB8 -> CB9 shift if C9 equals
the reference; responses to 1% and 5% of |C9_ref|; inherited sensitivity to the C6, C7, C8 allowances at order 9.
Reference C9_ref = archived hypothetical value, the order-8 endpoint_v PB[5/3], b=3 prediction of the K=4
construction (-2.190506633e8; recomputed here for K=4 and regressed). It is kept fixed for every K: PB[5/3] is not
admissible at K=8 and no K=8 PB is substituted. Evaluated on the archived 14 points and on the dense 1004 grid.
Outputs in results/: c9_predictions_K.csv, c9_sensitivity_K.csv (14 pts), c9_sensitivity_dense_K.csv,
c9_inherited_K.csv (14 pts), c9_inherited_dense_K.csv, c9_validation.json.
2026-10-13: C8 and its allowance from the C8(1) switch (cbk.py); outputs in cbk.RES. With LRI_C8_1=final the reference
C9_ref stays the archived scenario value -2.190506633e8 (the K=4 PB[5/3] prediction computed with the PREVIOUS C8(1));
it is not recomputed. The K=4 PB[5/3] prediction with the active C8 is recorded alongside. C8-independent archived
columns (kernel, responses to 1%/5% of C9_ref) are regressed; the C8-dependent ones are compared and reported.
"""
import csv, json, math, time
from pathlib import Path
import numpy as np
import mpmath as mp
from scipy.integrate import quad
import cbk

HERE = Path(__file__).resolve().parent; OUT = cbk.RES; OUT.mkdir(parents=True, exist_ok=True)
t0 = time.time()
print('C8 switch:', json.dumps(cbk.SW.describe()), flush=True)
XS = np.array([0, .001, .01, .025, .05, .075, .1, .125, .15, .175, .2, .225, .24, .25])
jobs = [('direct', None)]+[(m, K) for K in cbk.KS for m in ('endpoint_epsilon', 'endpoint_v')]


def cb_prediction(mode, b, K):
    c0 = cbk.series(mode, 9, cbk.C+[mp.mpf(0)], K); c1 = cbk.series(mode, 9, cbk.C+[mp.mpf(1)], K)
    p0 = cbk.polynomial(c0, b, 0, cbk.pref(mode)); p1 = cbk.polynomial(c1, b, 0, cbk.pref(mode))
    d = p1[9]-p0[9]; pred = -p0[9]/d
    p8 = cbk.polynomial(cbk.series(mode, 8, K=K), b, 0, cbk.pref(mode))      # independent re-expansion
    c_est = [v*mp.gamma(k+b+1) for k, v in enumerate(cbk.compose(p8, cbk.wseries(cbk.pref(mode), 9), 9))]
    check = cbk.original_coefficient(c_est, mode, 9, K)
    assert abs((check-pred)/pred) < mp.mpf('1e-45'), (mode, b, K)
    return pred, d


predictions = []
for mode, K in jobs:
    Kc = 4 if K is None else K
    for b in (0, 2, 3, 4):
        pred, d = cb_prediction(mode, b, Kc)
        predictions.append({'method': 'CB', 'mode': mode, 'K': '' if K is None else K, 'b': b, 'shape': 'w^8',
                            'admissible': True, 'C9_prediction': float(pred)})
        c = cbk.series(mode, 8, K=Kc)
        for m in (4, 3, 5):
            p, q = mp.pade([v/mp.gamma(k+b+1) for k, v in enumerate(c)], 8-m, m)
            roots = np.roots([float(v) for v in q[::-1]])
            ok = not any(z.real > 0 and abs(z.imag) < 1e-8*max(1, abs(z)) for z in roots)
            row = {'method': 'PB', 'mode': mode, 'K': '' if K is None else K, 'b': b, 'shape': '[%d/%d]' % (8-m, m),
                   'admissible': ok, 'C9_prediction': None}
            if ok:
                cs = [v*mp.gamma(k+b+1) for k, v in enumerate(cbk.rational_series(p, q, 9))]
                row['C9_prediction'] = float(cbk.original_coefficient(cs, mode, 9, Kc))
            predictions.append(row)
ref_row = next(r for r in predictions if r['method'] == 'PB' and r['mode'] == 'endpoint_v' and r['K'] == 4 and r['b'] == 3 and r['shape'] == '[5/3]')
pb53_k4_active = mp.mpf(repr(ref_row['C9_prediction']))
if cbk.MODE == 'previous':
    ref = pb53_k4_active
    assert ref == mp.mpf(cbk.SW.C9_REF_ARCHIVED)
    REF_METHOD = 'order-8 endpoint_v Pade-Borel [5/3], b=3, short-range series through C^SR_4 (archived K=4 construction); kept fixed for all K'
else:
    ref = mp.mpf(cbk.SW.C9_REF_ARCHIVED)
    REF_METHOD = ('archived scenario value: order-8 endpoint_v Pade-Borel [5/3], b=3, K=4, computed with the PREVIOUS C8(1) = 8066723.342964563; '
                  'kept fixed for all K (not recomputed with the final C8(1))')
print('reference C9:', ref, '| K=4 endpoint_v PB[5/3], b=3, with the active C8:', pb53_k4_active, flush=True)

sens = {'14': [], 'dense': []}; inh = {'14': [], 'dense': []}; checks = []
for mode, K in jobs:
    Kc = 4 if K is None else K
    pred, d = cb_prediction(mode, 3, Kc)
    for grid, xs in (('14', XS), ('dense', cbk.X)):
        args = cbk.argument(mode, xs)
        kernel = cbk.integral_grid([mp.mpf(0)]*9+[d], 3, 0, cbk.pref(mode), args)
        if mode != 'direct':
            kernel = kernel*(4*xs)**cbk.power(Kc)
        old = cbk.dimension(mode, 8, b=3, x=xs, K=Kc)
        new = cbk.dimension(mode, 9, b=3, x=xs, c=cbk.C+[pred], K=Kc)
        test = cbk.dimension(mode, 9, b=3, x=xs, c=cbk.C+[pred+mp.mpf('1e7')], K=Kc)
        null_err = float(max(abs(new-old))); lin_err = float(max(abs(test-old-1e7*kernel)))
        assert null_err < 2e-13 and lin_err < 2e-13, (mode, K, null_err, lin_err)
        for i, xx in enumerate(xs):
            sens[grid].append({'mode': mode, 'K': '' if K is None else K, 'Delta_sigma': float(xx),
                'C9_implied_by_CB8': float(pred), 'd_Delta_epsilon_d_C9': float(kernel[i]),
                'change_for_C9_plus_1million': float(kernel[i]*1e6),
                'change_for_1percent_of_reference': float(kernel[i]*float(abs(ref))/100),
                'change_for_5percent_of_reference': float(kernel[i]*float(abs(ref))/20),
                'C9_absolute_tolerance_for_1e_4_curve': float(1e-4/abs(kernel[i])) if kernel[i] != 0 else None,
                'CB8': float(old[i]), 'CB9_if_C9_equals_reference': float(old[i]+kernel[i]*float(ref-pred)),
                'change_if_C9_equals_reference': float(kernel[i]*float(ref-pred))})
        now = cbk.dimension(mode, 9, b=3, x=xs, c=cbk.C+[ref], K=Kc)
        for k, allow in cbk.ALLOWANCES:
            c = cbk.C.copy(); c[k] += allow
            d8 = cbk.dimension(mode, 8, b=3, x=xs, c=c, K=Kc)-old
            d9 = cbk.dimension(mode, 9, b=3, x=xs, c=c+[ref], K=Kc)-now
            for i, xx in enumerate(xs):
                inh[grid].append({'mode': mode, 'K': '' if K is None else K, 'Delta_sigma': float(xx), 'varied_coefficient': k,
                    'allowance': float(allow), 'order8_dimension_shift': float(d8[i]), 'order9_dimension_shift': float(d9[i]),
                    'condition': 'C9 held fixed at the reference; no covariance model assumed'})
        if grid == '14':
            i = int(np.searchsorted(xs, .1)); arg = float(args[i])
            def f(t):
                z = arg*t/float(cbk.pref(mode)); w = z/(math.sqrt(1+z)+1)**2
                return math.exp(-t)*t**3*float(d)*w**9
            k_ad = quad(f, 0, np.inf, epsabs=1e-22, epsrel=1e-11, limit=300)[0]
            if mode != 'direct':
                k_ad *= (4*.1)**cbk.power(Kc)
            assert abs(k_ad/kernel[i]-1) < 1e-9
            checks.append({'mode': mode, 'K': K, 'null_innovation_max_error': null_err, 'linearity_max_error': lin_err,
                           'kernel_GL_vs_adaptive_relative': float(abs(k_ad/kernel[i]-1))})
    print('Completed', mode, K, 'C9 implied by CB8 =', mp.nstr(pred, 12), '%.1fs' % (time.time()-t0), flush=True)

# K=4 regression against the archived c9 tables
regs = {}; changes = {}
ap = list(csv.DictReader((HERE/'inputs/archived_c9_predictions.csv').open()))
pkey = 'predictions' if cbk.MODE == 'previous' else 'predictions (C8-dependent: change, relative)'
regs[pkey] = 0.
for r in ap:
    m = [p for p in predictions if p['method'] == r['method'] and p['mode'] == r['mode'] and p['K'] in ('', 4) and p['b'] == int(r['b']) and p['shape'] == r['shape']]
    assert len(m) == 1 and m[0]['admissible'], r
    regs[pkey] = max(regs[pkey], abs(m[0]['C9_prediction']/float(r['C9_prediction'])-1))
if cbk.MODE != 'previous':
    changes[pkey] = regs.pop(pkey)
asens = list(csv.DictReader((HERE/'inputs/archived_c9.csv').open()))
regs['sensitivity'] = {}; changes['sensitivity'] = {}
RELATIVE = ('d_Delta_epsilon_d_C9', 'C9_implied_by_CB8')        # other columns: absolute differences in Delta_epsilon
C8DEP = ('CB8', 'change_if_C9_equals_PB_reference', 'CB9_if_C9_equals_PB_reference', 'C9_implied_by_CB8')
for col in ('d_Delta_epsilon_d_C9', 'change_for_1percent_of_reference', 'change_for_5percent_of_reference', 'CB8',
            'change_if_C9_equals_PB_reference', 'CB9_if_C9_equals_PB_reference', 'C9_implied_by_CB8'):
    newcol = col.replace('PB_reference', 'reference'); worst = 0.
    for r in asens:
        m = [s for s in sens['14'] if s['mode'] == r['mode'] and s['K'] in ('', 4) and abs(s['Delta_sigma']-float(r['Delta_sigma'])) < 1e-15]
        assert len(m) == 1
        a = float(r[col]); dv = abs(m[0][newcol]-a)
        if col in RELATIVE and a != 0:
            dv /= abs(a)
        worst = max(worst, dv)
    (changes if (cbk.MODE != 'previous' and col in C8DEP) else regs)['sensitivity'][col] = worst
print('K=4 regression:', {k: v for k, v in regs.items()}, flush=True)
if cbk.MODE != 'previous':
    print('K=4 C8-dependent changes vs archived:', changes, flush=True)
assert regs.get('predictions', 0.) < 1e-10 and max(regs['sensitivity'].values()) < 1e-11

def writecsv(name, rr):
    with (OUT/name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rr[0])); w.writeheader(); w.writerows(rr)
writecsv('c9_predictions_K.csv', predictions)
writecsv('c9_sensitivity_K.csv', sens['14']); writecsv('c9_sensitivity_dense_K.csv', sens['dense'])
writecsv('c9_inherited_K.csv', inh['14']); writecsv('c9_inherited_dense_K.csv', inh['dense'])
(OUT/'c9_validation.json').write_text(json.dumps({
    'note': 'All C9 values are predictions or scenarios, NOT a ninth-order graph calculation.',
    'C8_switch': cbk.SW.describe(), 'reference_C9': str(ref), 'reference_method': REF_METHOD,
    'K4_PB53_b3_C9_prediction_with_active_C8': str(pb53_k4_active), 'K4_changes_vs_archived': changes,
    'sensitivity_identity': 'At fixed A, b, alpha, K and endpoint prescription, F9 - F8 = kernel(x) (C9 - C9_implied_by_F8).',
    'checks': checks, 'K4_regression': regs}, indent=1, default=str))
print('C9 PREDICTIONS endpoint_v b=3:', flush=True)
for p in predictions:
    if p['mode'] == 'endpoint_v' and p['b'] == 3:
        print(' ', p['K'], p['method'], p['shape'], p['admissible'], p['C9_prediction'], flush=True)
for K in (4, 8):
    r = next(s for s in sens['14'] if s['mode'] == 'endpoint_v' and s['K'] == K and s['Delta_sigma'] == .1)
    print('K=%d x=0.1: kernel %.4e shift-if-ref %.4e 1%% %.4e 5%% %.4e' % (K, r['d_Delta_epsilon_d_C9'], r['change_if_C9_equals_reference'],
          r['change_for_1percent_of_reference'], r['change_for_5percent_of_reference']), flush=True)
print('FINISHED stage 3 (C9) in %.1fs; all checks passed' % (time.time()-t0), flush=True)
