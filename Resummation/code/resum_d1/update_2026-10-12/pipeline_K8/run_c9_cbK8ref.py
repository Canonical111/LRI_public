#!/usr/bin/env python3
"""Stage 3b (2026-10-13): Figure 04 hypothetical-C9 sensitivity with the K=8 row referenced to C9 predicted by CB from
the K=8 baseline. Copy of the endpoint_v part of run_c9.py (unchanged machinery: cbk.py); run_c9.py and its tables
are not modified. NOT a C9 calculation: every C9 here is a prediction or a scenario input.

C9_CB8,K8: re-expand the K=8 baseline approximant (endpoint-v CB8, N=8, b_L=3, alpha=0, short-range series through
C^SR_8, action A_v = A_eps/2) to ninth order and convert back to the GFF epsilon coefficient C9 through the endpoint
construction (inverse of the S_K subtraction, of the (4x)^{(K+1)/2} prefactor and of eps = 2v - v^2). Two routes,
required to agree to 1e-45: (a) solve [w^9] of the order-9 Borel polynomial = 0 for C9 (it is linear in C9);
(b) compose the order-8 Borel polynomial with the inverse conformal map w(t) (Catalan series), multiply by
Gamma(k+b+1) and map back with cbk.original_coefficient.
Checks: K=4 reproduces the archived CB endpoint_v b=3 C9 prediction (inputs/archived_c9_predictions.csv) and both K
values reproduce results/c9_predictions_K.csv; the same re-expansion one order lower (C_0..C_7 -> C_8) reproduces
the held-out C8 CB predictions of results/held_out_K.csv (endpoint_v, b=0,2,3,4, K=4 and K=8; Figure 02 uses b=3).
Sensitivity (endpoint_v, b=3, alpha=0): K=8 with C9_ref = C9_CB8,K8; K=4 with the archived C9_ref
(-2.190506633e8, K=4 PB[5/3]), so the lower row of Figure 04 is unchanged (regressed against
c9_sensitivity_dense_K.csv). Since F9 - F8 = kernel(x) (C9_ref - C9_implied_by_F8), the K=8 CB8 -> CB9 shift is
identically zero by construction; only the responses to 1% and 5% of |C9_ref| carry information there.
Outputs in results/ (new names): c9cb8_predictions.json, c9cb8_sensitivity_K.csv (14 pts),
c9cb8_sensitivity_dense_K.csv, c9cb8_inherited_K.csv, c9cb8_inherited_dense_K.csv, c9cb8_validation.json.
Run from anywhere (seconds): python3 update_2026-10-12/pipeline_K8/run_c9_cbK8ref.py
2026-10-13 (C8(1) final): C8 from the C8(1) switch (cbk.py); reads and writes cbk.RES. With LRI_C8_1=final, C9_CB8,K8 is
recomputed with the final C8(1) and the K=4 row keeps the archived C9_ref (-2.190506633e8, from c9_validation.json of the
same run, pinned by run_c9.py); the K=4 CB C9 prediction then differs from the archived table (reported, not asserted).
"""
import csv, hashlib, json, math, sys, time
from pathlib import Path
import numpy as np
import mpmath as mp
from scipy.integrate import quad

sys.dont_write_bytecode = True
import cbk

HERE = Path(__file__).resolve().parent; OUT = cbk.RES
t0 = time.time()
print('C8 switch:', json.dumps(cbk.SW.describe()), flush=True)
XS = np.array([0, .001, .01, .025, .05, .075, .1, .125, .15, .175, .2, .225, .24, .25])
MODE, B = 'endpoint_v', 3
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inputs = {n: OUT/n for n in ('c9_predictions_K.csv', 'c9_sensitivity_K.csv', 'c9_sensitivity_dense_K.csv', 'c9_inherited_K.csv',
                             'c9_inherited_dense_K.csv', 'held_out_K.csv', 'c9_validation.json')}
inputs['archived_c9_predictions.csv'] = HERE/'inputs'/'archived_c9_predictions.csv'
before = {n: sha(p) for n, p in inputs.items()}


def cb_predict(mode, b, K, n):
    """C_n implied by the order-(n-1) CB approximant built from C_0..C_{n-1} (alpha = 0); two routes."""
    known = list(cbk.C[:n])
    c0 = cbk.series(mode, n, known+[mp.mpf(0)], K); c1 = cbk.series(mode, n, known+[mp.mpf(1)], K)
    p0 = cbk.polynomial(c0, b, 0, cbk.pref(mode)); p1 = cbk.polynomial(c1, b, 0, cbk.pref(mode))
    d = p1[n]-p0[n]; pred = -p0[n]/d                                    # route (a)
    pm = cbk.polynomial(cbk.series(mode, n-1, known, K), b, 0, cbk.pref(mode))
    c_est = [v*mp.gamma(k+b+1) for k, v in enumerate(cbk.compose(pm, cbk.wseries(cbk.pref(mode), n), n))]
    other = cbk.original_coefficient(c_est, mode, n, K)                 # route (b)
    assert abs((other-pred)/pred) < mp.mpf('1e-45'), (mode, b, K, n)
    return pred, d, other


# ---- C9 predictions and checks ----
checks = {}
pred9 = {K: cb_predict(MODE, B, K, 9) for K in (4, 8)}
C9CB8 = pred9[8][0]
print('C9_CB8,K8 (endpoint_v CB8, b=3, alpha=0, K=8) =', mp.nstr(C9CB8, 20),
      '| route (b) =', mp.nstr(pred9[8][2], 20), flush=True)
arch = {(r['method'], r['mode'], r['b'], r['shape']): float(r['C9_prediction']) for r in csv.DictReader(inputs['archived_c9_predictions.csv'].open())}
a4 = arch[('CB', MODE, str(B), 'w^8')]
checks['K4_CB_C9_vs_archived_c9_predictions_rel' if cbk.MODE == 'previous' else 'K4_CB_C9_vs_archived_c9_predictions_change_C8_dependent'] = abs(float(pred9[4][0])/a4-1)
pipe = {(r['method'], r['mode'], r['K'], r['b'], r['shape']): r['C9_prediction'] for r in csv.DictReader(inputs['c9_predictions_K.csv'].open())}
for K in (4, 8):
    checks[f'K{K}_CB_C9_vs_pipeline_c9_predictions_K_rel'] = abs(float(pred9[K][0])/float(pipe[('CB', MODE, str(K), str(B), 'w^8')])-1)
    checks[f'K{K}_route_a_vs_route_b_rel'] = float(abs((pred9[K][2]-pred9[K][0])/pred9[K][0]))
held = list(csv.DictReader(inputs['held_out_K.csv'].open()))
held_rows = []
for K in (4, 8):
    for b in (0, 2, 3, 4):
        h = [r for r in held if r['method'] == 'CB' and r['mode'] == MODE and r['K'] == str(K) and r['b'] == str(b) and r['predict_C'] == '8']
        assert len(h) == 1, (K, b)
        p8 = cb_predict(MODE, b, K, 8)[0]
        rel = abs(float(p8)/float(h[0]['prediction'])-1)
        held_rows.append({'K': K, 'b': b, 'C8_reexpansion_order7': float(p8), 'held_out_K_csv': float(h[0]['prediction']), 'rel_diff': rel})
checks['order7_to_C8_vs_held_out_K_max_rel'] = max(r['rel_diff'] for r in held_rows)
print('checks', json.dumps(checks), flush=True)
assert cbk.MODE != 'previous' or checks['K4_CB_C9_vs_archived_c9_predictions_rel'] < 1e-12
assert all(v < 1e-12 for k, v in checks.items() if k.endswith('_rel'))
assert checks['order7_to_C8_vs_held_out_K_max_rel'] < 1e-12

# ---- sensitivity tables (endpoint_v, b=3): K=8 referenced to C9_CB8,K8; K=4 to the archived value ----
cval = json.loads(inputs['c9_validation.json'].read_text())
REF4 = mp.mpf(cval['reference_C9'])
assert abs(REF4/mp.mpf('-2.190506633e8')-1) < mp.mpf('1e-9')
refs = {4: (REF4, cval['reference_method']),
        8: (C9CB8, 'CB prediction of the K=8 baseline (endpoint-v CB8, N=8, b_L=3, alpha=0, C^SR_8): its own ninth-order re-expansion')}
sens = {'14': [], 'dense': []}; inh = {'14': [], 'dense': []}; kchecks = []
for K in (4, 8):
    ref, refm = refs[K]
    pred, d, _ = pred9[K]
    for grid, xs in (('14', XS), ('dense', cbk.X)):
        args = cbk.argument(MODE, xs)
        kernel = cbk.integral_grid([mp.mpf(0)]*9+[d], B, 0, cbk.pref(MODE), args)*(4*xs)**cbk.power(K)
        old = cbk.dimension(MODE, 8, b=B, x=xs, K=K)
        new = cbk.dimension(MODE, 9, b=B, x=xs, c=cbk.C+[pred], K=K)
        test = cbk.dimension(MODE, 9, b=B, x=xs, c=cbk.C+[pred+mp.mpf('1e7')], K=K)
        null_err = float(max(abs(new-old))); lin_err = float(max(abs(test-old-1e7*kernel)))
        assert null_err < 2e-13 and lin_err < 2e-13, (K, null_err, lin_err)
        shift_ref = cbk.dimension(MODE, 9, b=B, x=xs, c=cbk.C+[ref], K=K)
        identity_err = float(max(abs(shift_ref-old-kernel*float(ref-pred))))
        assert identity_err < 2e-13, (K, identity_err)
        for i, xx in enumerate(xs):
            sens[grid].append({'mode': MODE, 'K': K, 'Delta_sigma': float(xx),
                'C9_implied_by_CB8': float(pred), 'C9_reference': float(ref), 'd_Delta_epsilon_d_C9': float(kernel[i]),
                'change_for_C9_plus_1million': float(kernel[i]*1e6),
                'change_for_1percent_of_reference': float(kernel[i]*float(abs(ref))/100),
                'change_for_5percent_of_reference': float(kernel[i]*float(abs(ref))/20),
                'C9_absolute_tolerance_for_1e_4_curve': float(1e-4/abs(kernel[i])) if kernel[i] != 0 else None,
                'CB8': float(old[i]), 'CB9_if_C9_equals_reference': float(old[i]+kernel[i]*float(ref-pred)),
                'change_if_C9_equals_reference': float(kernel[i]*float(ref-pred))})
        for k, allow in cbk.ALLOWANCES:
            c = cbk.C.copy(); c[k] += allow
            d8 = cbk.dimension(MODE, 8, b=B, x=xs, c=c, K=K)-old
            d9 = cbk.dimension(MODE, 9, b=B, x=xs, c=c+[ref], K=K)-shift_ref
            for i, xx in enumerate(xs):
                inh[grid].append({'mode': MODE, 'K': K, 'Delta_sigma': float(xx), 'varied_coefficient': k,
                    'allowance': float(allow), 'order8_dimension_shift': float(d8[i]), 'order9_dimension_shift': float(d9[i]),
                    'condition': 'C9 held fixed at the reference of this K; no covariance model assumed'})
        if grid == '14':
            i = int(np.searchsorted(xs, .1)); arg = float(args[i])
            def f(t):
                z = arg*t/float(cbk.pref(MODE)); w = z/(math.sqrt(1+z)+1)**2
                return math.exp(-t)*t**B*float(d)*w**9
            k_ad = quad(f, 0, np.inf, epsabs=1e-22, epsrel=1e-11, limit=300)[0]*(4*.1)**cbk.power(K)
            assert abs(k_ad/kernel[i]-1) < 1e-9
            kchecks.append({'K': K, 'null_innovation_max_error': null_err, 'linearity_max_error': lin_err,
                            'identity_F9_minus_F8_max_error': identity_err,
                            'kernel_GL_vs_adaptive_relative': float(abs(k_ad/kernel[i]-1))})
    print('Completed K=%d C9_ref=%s (%s) %.1fs' % (K, mp.nstr(ref, 12), refm[:40], time.time()-t0), flush=True)

# ---- regressions against the stage-3 tables (same machinery) ----
regs = {}
for grid, name in (('14', 'c9_sensitivity_K.csv'), ('dense', 'c9_sensitivity_dense_K.csv')):
    old_rows = [r for r in csv.DictReader(inputs[name].open()) if r['mode'] == MODE and r['K'] in ('4', '8')]
    new_rows = sens[grid]; assert len(old_rows) == len(new_rows)
    w4 = w8k = w8r = 0.
    scale = float(abs(C9CB8)/abs(REF4))
    for a, b in zip(old_rows, new_rows):
        assert int(a['K']) == b['K'] and abs(float(a['Delta_sigma'])-b['Delta_sigma']) < 1e-15
        if b['K'] == 4:      # all columns of the K=4 rows unchanged
            for col in ('d_Delta_epsilon_d_C9', 'change_for_1percent_of_reference', 'change_for_5percent_of_reference', 'CB8',
                        'CB9_if_C9_equals_reference', 'change_if_C9_equals_reference', 'C9_implied_by_CB8'):
                w4 = max(w4, abs(float(a[col])-b[col])/(abs(float(a[col])) if col == 'C9_implied_by_CB8' else 1))
        else:                # K=8: kernel and CB8 unchanged; responses rescale by |C9_CB8,K8|/|C9_ref archived|
            w8k = max(w8k, abs(float(a['d_Delta_epsilon_d_C9'])-b['d_Delta_epsilon_d_C9']), abs(float(a['CB8'])-b['CB8']))
            w8r = max(w8r, abs(float(a['change_for_5percent_of_reference'])*scale-b['change_for_5percent_of_reference']),
                      abs(float(a['change_for_1percent_of_reference'])*scale-b['change_for_1percent_of_reference']))
    regs[grid] = {'K4_all_columns_max_abs': w4, 'K8_kernel_and_CB8_max_abs': w8k, 'K8_responses_vs_rescaled_old_max_abs': w8r}
    assert w4 < 1e-13 and w8k < 1e-13 and w8r < 1e-13, regs   # Mac ARM vs pi x86 floating-point noise ~1e-15
K8shift = max(abs(r['change_if_C9_equals_reference']) for r in sens['dense'] if r['K'] == 8)
assert K8shift == 0.0
print('regressions', json.dumps(regs), '| K=8 shift-if-reference max |.| =', K8shift, flush=True)

def writecsv(name, rr):
    with (OUT/name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rr[0])); w.writeheader(); w.writerows(rr)
writecsv('c9cb8_sensitivity_K.csv', sens['14']); writecsv('c9cb8_sensitivity_dense_K.csv', sens['dense'])
writecsv('c9cb8_inherited_K.csv', inh['14']); writecsv('c9cb8_inherited_dense_K.csv', inh['dense'])
(OUT/'c9cb8_predictions.json').write_text(json.dumps({
    'C9_CB8_K8': str(C9CB8), 'C9_CB8_K8_route_b': str(pred9[8][2]), 'C9_CB8_K4': str(pred9[4][0]),
    'definition': refs[8][1], 'held_out_order7_to_C8': held_rows}, indent=1)+'\n')
assert {n: sha(p) for n, p in inputs.items()} == before, 'a stage-3 table changed'
(OUT/'c9cb8_validation.json').write_text(json.dumps({
    'note': 'All C9 values are predictions or scenarios, NOT a ninth-order graph calculation.', 'C8_switch': cbk.SW.describe(),
    'C9_reference': {'8': str(C9CB8), '4': str(REF4)},
    'C9_reference_method': {'8': refs[8][1], '4': refs[4][1]},
    'sensitivity_identity': 'At fixed A, b, alpha, K and endpoint prescription, F9 - F8 = kernel(x) (C9 - C9_implied_by_F8); '
                            'with C9_ref = C9_implied_by_F8 at K=8 the shift vanishes identically.',
    'prediction_checks': checks, 'kernel_checks': kchecks, 'regressions_vs_stage3_tables': regs,
    'inputs_sha256': before, 'elapsed_seconds': round(time.time()-t0, 1)}, indent=1, default=str)+'\n')
print('FINISHED stage 3b in %.1fs; all checks passed' % (time.time()-t0), flush=True)
