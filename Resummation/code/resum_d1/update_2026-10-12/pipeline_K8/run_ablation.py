#!/usr/bin/env python3
"""Stage 2: matched CB / PB comparison, PB admissibility and held-out coefficient tests for K = 4..8
(analogue of reproduction/instanton_ablation/ablation.py; same pre-committed protocol, inputs/archived_ablation_protocol.json).

Matching: coefficients, truncation order, strong-endpoint input (now S_K), expansion variable, Borel-Leroy b.
CB: candidate A, alpha = 0. PB: A never used; near-diagonal candidates in the archived order; positive-real poles
rejected; selection = first admissible candidate (minimum |L-M|, tie -> higher numerator). No reference data used.
Held-out: predict C6 from C0..C5, C7 from C0..C6, C8 from C0..C7, for the direct GFF series (K-independent, as
archived) and, new, through the endpoint constructions with S_K (the approximant's implied next coefficient of H is
mapped back to C_{n+1}).
Outputs in results/: ablation_K.csv (grid of the archived ablation table), pade_admissibility_K.json,
held_out_K.csv, matched_comparison_K.csv, ablation_validation.json.
2026-10-13: C8 from the C8(1) switch (cbk.py); outputs in cbk.RES. With LRI_C8_1=final the archived K=4 table (previous
C8) must still be matched by the order-6 and order-7 columns and admissibility decisions, and by the held-out
predictions (they use C_0..C_n only); order-8 columns and decisions are compared and their changes reported.
"""
import csv, json, time
from pathlib import Path
import numpy as np
import mpmath as mp
import cbk

HERE = Path(__file__).resolve().parent; OUT = cbk.RES; OUT.mkdir(parents=True, exist_ok=True)
t0 = time.time()
print('C8 switch:', json.dumps(cbk.SW.describe()), flush=True)
X = cbk.X_ABL; BGRID = [0, 2, 3, 4]
assert len(X) == 502
curves = {}; decisions = []; selected = {}; validation = []
jobs = [('direct', None)]+[(m, K) for K in cbk.KS for m in ('endpoint_epsilon', 'endpoint_v')]
for mode, K in jobs:
    Kc = 4 if K is None else K; tag = mode if K is None else '%s_K%d' % (mode, K)
    for n in (6, 7, 8):
        for b in BGRID:
            curves['%s_CB_n%d_b%d' % (tag, n, b)] = cbk.dimension(mode, n, b=b, x=X, K=Kc)
            aps = []
            for m in cbk.denominator_degrees(n):
                ap = cbk.make_pb(cbk.series(mode, n, K=Kc), m, b)
                row = {'mode': mode, 'K': K, 'order': n, 'b': b, 'L': n-m, 'M': m, 'admissible': ap['allowed'],
                       'poles': [[float(z.real), float(z.imag)] for z in ap['roots']], 'formal': ap['formal']}
                if ap['allowed']:
                    pk = '%s_PB_%d%d_n%d_b%d' % (tag, n-m, m, n, b)
                    curves[pk] = cbk.pb_dimension(ap, mode, X, K=Kc); aps.append((ap, pk))
                    row['quadrature_GL_vs_adaptive'] = ap['laguerre_adaptive_max_remainder_difference']
                    row['adaptive_fallback'] = ap['adaptive_fallback']
                decisions.append(row)
            if aps:
                ap, pk = aps[0]; sk = '%s_PB_n%d_b%d' % (tag, n, b); curves[sk] = curves[pk]
                selected[(tag, n, b)] = '[%d/%d]' % (n-ap['m'], ap['m'])
                if n == 8 and b in (0, 3):
                    xx = .1; val = cbk.pb_mp_check(ap, mode, xx, K=Kc)
                    diff = float(abs(val-curves[sk][np.searchsorted(X, xx)]))
                    assert diff < 2e-8, (sk, diff)
                    validation.append({'curve': sk, 'shape': selected[(tag, n, b)], 'x': xx, 'mp65_error_dimension': diff})
            else:
                selected[(tag, n, b)] = None
            print('Completed', tag, n, b, 'PB admissible', [(v['n']-v['m'], v['m']) for v, k in aps],
                  '%.1fs' % (time.time()-t0), flush=True)

# held-out coefficient predictions
holdout = []
def hrow(method, mode, K, n, b, approx, sel, pred):
    truth = cbk.C[n+1]
    return {'method': method, 'mode': mode, 'K': '' if K is None else K, 'input_order': n, 'predict_C': n+1, 'b': b,
            'approximant': approx, 'selected': sel, 'prediction': float(pred), 'actual': float(truth),
            'relative_error': float((pred-truth)/truth), 'absolute_relative_error': float(abs((pred-truth)/truth))}
for mode, K in jobs:
    Kc = 4 if K is None else K
    for n in (5, 6, 7):
        for b in BGRID:
            c = cbk.series(mode, n, cbk.C[:n+1], K=Kc); A = cbk.pref(mode); nn = n+1
            p = cbk.polynomial(c, b, 0, A)
            hpred = cbk.compose(p, cbk.wseries(A, nn), nn)[nn]*mp.gamma(nn+b+1)
            pred = cbk.original_coefficient(list(c)+[hpred], mode, nn, K=Kc)
            # consistency: the predicted C_{n+1} regenerates the implied H coefficient
            back = cbk.series(mode, nn, list(cbk.C[:nn])+[pred], K=Kc)[nn]
            assert abs(back-hpred) <= mp.mpf('1e-40')*(1+abs(hpred)), (mode, K, n, b)
            holdout.append(hrow('CB', mode, K, n, b, 'w polynomial', True, pred))
            first = True
            for m in cbk.denominator_degrees(n):
                ap = cbk.make_pb(c, m, b)
                if not ap['allowed']:
                    continue
                hpred = cbk.rational_series(ap['p'], ap['q'], nn)[nn]*mp.gamma(nn+b+1)
                pred = cbk.original_coefficient(list(c)+[hpred], mode, nn, K=Kc)
                holdout.append(hrow('PB', mode, K, n, b, '[%d/%d]' % (n-m, m), first, pred)); first = False

summary = []
XK = [0, .001, .01, .025, .05, .0625, .075, .1, .125, .15, .175, .2, .225, .24, .249, .25]
for mode, K in jobs:
    tag = mode if K is None else '%s_K%d' % (mode, K)
    for b in (0, 3):
        ck = '%s_CB_n8_b%d' % (tag, b); pk = '%s_PB_n8_b%d' % (tag, b)
        for xx in XK:
            i = np.searchsorted(X, xx)
            row = {'mode': mode, 'K': '' if K is None else K, 'b': b, 'Delta_sigma': xx, 'CB8': float(curves[ck][i]),
                   'PB8_selected': float(curves[pk][i]) if pk in curves else None,
                   'PB_degrees': selected[(tag, 8, b)] or 'none admissible',
                   'CB_minus_PB': float(curves[ck][i]-curves[pk][i]) if pk in curves else None}
            for method in ('CB', 'PB'):
                p6, p7, p8 = ('%s_%s_n%d_b%d' % (tag, method, nn, b) for nn in (6, 7, 8))
                row[method+'_L8_minus_L7'] = float(curves[p8][i]-curves[p7][i]) if p8 in curves and p7 in curves else None
                row[method+'_L7_minus_L6'] = float(curves[p7][i]-curves[p6][i]) if p7 in curves and p6 in curves else None
            summary.append(row)

# K=4 regression against the archived ablation table, admissibility and held-out tables
arch = list(csv.DictReader((HERE/'inputs/archived_ablation.csv').open()))
ax = np.array([float(r['Delta_sigma']) for r in arch]); assert np.max(abs(ax-X)) < 1e-15
reg = {}; reg8 = {}
for col in arch[0]:
    if col == 'Delta_sigma':
        continue
    mode = next(m for m in ('endpoint_epsilon', 'endpoint_v', 'direct') if col.startswith(m))
    new = col if mode == 'direct' else col.replace(mode, mode+'_K4', 1)
    target = reg if (cbk.MODE == 'previous' or '_n8_' not in col) else reg8
    if new not in curves:
        target[col] = 'missing'; continue
    target[col] = float(np.max(abs(curves[new]-np.array([float(r[col]) for r in arch]))))
missing = [k for k, v in reg.items() if v == 'missing']
extra = [k for k in curves if ('_K4_' in k or k.startswith('direct')) and k.replace('_K4', '') not in arch[0]]
worst = max(v for v in reg.values() if v != 'missing')
print('K=4 ablation regression: %d columns, max |diff| %.3e, missing %s, extra %s' % (len(reg), worst, missing, extra), flush=True)
if reg8:
    print('K=4 order-8 columns (C8-dependent, %d): missing %s, max |new - archived| %.3e' % (len(reg8), [k for k, v in reg8.items() if v == 'missing'],
          max(v for v in reg8.values() if v != 'missing')), flush=True)
assert not missing and worst < 1e-11
arch_dec = json.loads((HERE/'inputs/archived_pade_admissibility.json').read_text())
newdec = {(d['mode'], d['order'], d['b'], d['L'], d['M']): d['admissible'] for d in decisions if d['K'] in (None, 4)}
dec_mismatch = [(d['mode'], d['order'], d['b'], d['L'], d['M']) for d in arch_dec
                if newdec.get((d['mode'], d['order'], d['b'], d['L'], d['M'])) != d['admissible']]
dec_changed_order8 = [m for m in dec_mismatch if m[1] == 8 and cbk.MODE != 'previous']
dec_mismatch = [m for m in dec_mismatch if m not in dec_changed_order8]
print('K=4 admissibility: mismatches %s; order-8 changes with the active C8 %s' % (dec_mismatch, dec_changed_order8), flush=True)
assert not dec_mismatch, dec_mismatch
arch_ho = list(csv.DictReader((HERE/'inputs/archived_held_out.csv').open()))
ho_reg = 0.
for r in arch_ho:
    m = [h for h in holdout if h['mode'] == 'direct' and h['method'] == r['method'] and h['input_order'] == int(r['input_order'])
         and h['b'] == int(r['b']) and h['approximant'] == r['approximant']]
    assert len(m) == 1 and str(m[0]['selected']) == r['selected'], r
    ho_reg = max(ho_reg, abs(m[0]['prediction']-float(r['prediction']))/abs(float(r['prediction'])))
print('held-out regression (direct, 30 archived rows): max relative |diff| %.3e' % ho_reg, flush=True)
assert ho_reg < 1e-12

def writecsv(name, rr):
    with (OUT/name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rr[0])); w.writeheader(); w.writerows(rr)
writecsv('ablation_K.csv', [{'Delta_sigma': float(x), **{k: float(v[i]) for k, v in curves.items()}} for i, x in enumerate(X)])
writecsv('held_out_K.csv', holdout); writecsv('matched_comparison_K.csv', summary)
(OUT/'pade_admissibility_K.json').write_text(json.dumps(decisions, indent=1))
(OUT/'ablation_validation.json').write_text(json.dumps({'C8_switch': cbk.SW.describe(),
    'mp65_checks': validation, 'K4_regression_vs_archived_ablation_csv': reg, 'K4_regression_max': worst,
    'K4_order8_columns_change_vs_archived': reg8, 'K4_order8_admissibility_changes_vs_archived': dec_changed_order8,
    'K4_admissibility_matches_archived': True, 'held_out_direct_regression_max_relative': ho_reg,
    'selected_PB': {'%s_n%d_b%d' % k: v for k, v in selected.items()},
    'max_PB_GL_vs_adaptive': max(d['quadrature_GL_vs_adaptive'] for d in decisions if 'quadrature_GL_vs_adaptive' in d),
    'adaptive_fallbacks': [d for d in decisions if d.get('adaptive_fallback')]}, indent=1, default=str))
print('SELECTED PB (endpoint_v, b=3):', {K: [selected[('endpoint_v_K%d' % K, n, 3)] for n in (6, 7, 8)] for K in cbk.KS}, flush=True)
print('HELD OUT b=3 selected:', flush=True)
for h in holdout:
    if h['b'] == 3 and h['selected'] and h['mode'] in ('direct', 'endpoint_v'):
        print(' ', h['method'], h['mode'], h['K'], 'C%d' % h['predict_C'], h['approximant'], '%.4f%%' % (100*h['absolute_relative_error']), flush=True)
print('FINISHED stage 2 (ablation) in %.1fs; all checks passed' % (time.time()-t0), flush=True)
