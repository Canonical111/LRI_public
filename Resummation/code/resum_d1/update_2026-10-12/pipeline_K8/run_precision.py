#!/usr/bin/env python3
"""Stage 4: C8 precision budget for K = 4..8 (analogue of reproduction/c8_precision/assess.py).

Rescales the unit coefficient responses of stage 1 (order 8) and stage 3 (order 9, C9 fixed at the reference):
sum of absolute responses to the allowances (C6 4.9e-7, C7 41, C8 33000) before and after dividing the C8 allowance
by ten, and the floor with C8 exact. Not a confidence interval. K=4 is regressed against inputs/archived_precision.csv.
Outputs in results/: precision_budget_K.csv, precision_summary.json.
2026-10-13: allowances from the C8(1) switch (cbk.py; final: C8 17000, previous: 33000); inputs and outputs in cbk.RES.
With LRI_C8_1=final the archived K=4 table is matched by the C6/C7 components and by the C8 component rescaled by the
allowance ratio; the sums are compared and their changes reported.
"""
import csv, json, hashlib
from pathlib import Path
import numpy as np
import cbk

HERE = Path(__file__).resolve().parent; OUT = cbk.RES
ALLOW8 = float(cbk.C8IN['allowance']); RATIO = ALLOW8/cbk.ALLOWANCE_C8_PREVIOUS
print('C8 switch:', json.dumps(cbk.SW.describe()), flush=True)
src8 = OUT/'curve_K.csv'; src9 = OUT/'c9_inherited_K.csv'; src9d = OUT/'c9_inherited_dense_K.csv'
curve = list(csv.DictReader(src8.open()))
rows = []
def entry(order, K, x, c6, c7, c8, conv):
    old = c6+c7+c8; new = c6+c7+c8/10
    return {'order': order, 'K': K, 'Delta_sigma': x, 'C6_component': c6, 'C7_component': c7, 'C8_component_before': c8,
            'C8_component_after': c8/10, 'sum_before': old, 'sum_after': new, 'reduction_factor': old/new if new else None,
            'floor_with_C8_exact': c6+c7, 'convention': conv}
for K in (4, 5, 6, 7, 8):
    for r in curve:
        c6, c7, c8 = [abs(float(r['endpoint_v_K%d_shift_C%d' % (K, k)])) for k in (6, 7, 8)]
        rows.append(entry(8, K, float(r['Delta_sigma']), c6, c7, c8, 'sum of absolute allowance responses, not 1 sigma'))
    for grid, src in (('14', src9), ('dense', src9d)):
        byx = {}
        for r in csv.DictReader(src.open()):
            if r['mode'] != 'endpoint_v' or r['K'] != str(K):
                continue
            byx.setdefault(float(r['Delta_sigma']), {})[int(r['varied_coefficient'])] = abs(float(r['order9_dimension_shift']))
        for x, cs in sorted(byx.items()):
            e = entry(9, K, x, cs[6], cs[7], cs[8], 'C9 held fixed at the reference; C9 uncertainty excluded; absolute response sum')
            e['grid'] = grid; rows.append(e)
for r in rows:
    r.setdefault('grid', 'dense')

# K=4 regression against the archived precision table (order 8 dense, order 9 at 14 points)
arch = list(csv.DictReader((HERE/'inputs/archived_precision.csv').open()))
a8 = [a for a in arch if a['order'] == '8']; a9 = [a for a in arch if a['order'] == '9']
n8 = [r for r in rows if r['K'] == 4 and r['order'] == 8]          # same 1004-point grid, same order (it has near-duplicate x)
assert len(a8) == len(n8) == 1004 and all(float(a['Delta_sigma']) == r['Delta_sigma'] for a, r in zip(a8, n8))
pairs = list(zip(a8, n8))
for a in a9:
    m = [r for r in rows if r['K'] == 4 and r['order'] == 9 and r['grid'] == '14' and abs(r['Delta_sigma']-float(a['Delta_sigma'])) < 1e-15]
    assert len(m) == 1, a
    pairs.append((a, m[0]))
if cbk.MODE == 'previous':
    worst = max(abs(r[col]-float(a[col])) for a, r in pairs
                for col in ('C6_component', 'C7_component', 'C8_component_before', 'sum_before', 'sum_after', 'floor_with_C8_exact'))
    changes = {}
else:      # C8 component rescales with the allowance; the sums change
    worst = max(max(max(abs(r[col]-float(a[col])) for col in ('C6_component', 'C7_component', 'floor_with_C8_exact')),
                    abs(r['C8_component_before']-RATIO*float(a['C8_component_before']))) for a, r in pairs)
    changes = {col: max(abs(r[col]-float(a[col])) for a, r in pairs) for col in ('C8_component_before', 'sum_before', 'sum_after')}
    print('K=4 changes vs archived (allowance %g -> %g):' % (cbk.ALLOWANCE_C8_PREVIOUS, ALLOW8), changes, flush=True)
print('K=4 precision regression: %d archived rows, max |diff| %.3e' % (len(arch), worst), flush=True)
assert worst < 1e-12

with (OUT/'precision_budget_K.csv').open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def at(K, order, x, grid='dense'):
    return next(r for r in rows if r['K'] == K and r['order'] == order and r['grid'] == grid and abs(r['Delta_sigma']-x) < 1e-12)
summary = {'C8_switch': cbk.SW.describe(), 'C8_allowance_before': int(ALLOW8), 'C8_allowance_after': ALLOW8/10, 'C7_allowance_unchanged': 41, 'C6_allowance': 4.9e-7,
           'prescription': 'endpoint-v conformal Borel, b=3, alpha=0, short-range series through C^SR_K',
           'interpretation': 'Coefficient sensitivity only; does not reduce prescription or K dependence; not a probability interval.',
           'K4_regression_max_abs': worst, 'K4_changes_vs_archived': changes,
           'key_points': {str(K): {str(x): {k: at(K, 8, x)[k] for k in ('sum_before', 'sum_after', 'floor_with_C8_exact', 'reduction_factor')}
                                    for x in (.025, .05, .1, .125, .15, .2)} for K in (4, 8)},
           'order9_key_points': {str(K): {str(x): {k: at(K, 9, x, '14')[k] for k in ('C8_component_before', 'sum_before', 'sum_after')}
                                           for x in (.05, .1, .15)} for K in (4, 8)},
           'order8_peak_before': {str(K): max((r for r in rows if r['K'] == K and r['order'] == 8), key=lambda r: r['sum_before']) for K in (4, 8)},
           'order8_peak_after': {str(K): max((r for r in rows if r['K'] == K and r['order'] == 8), key=lambda r: r['sum_after']) for K in (4, 8)},
           'sources': [{'path': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in (src8, src9, src9d)]}
(OUT/'precision_summary.json').write_text(json.dumps(summary, indent=1))
for K in (4, 8):
    r = at(K, 8, .1)
    print('K=%d x=0.1: before %.4e after %.4e floor %.4e factor %.3f' % (K, r['sum_before'], r['sum_after'], r['floor_with_C8_exact'], r['reduction_factor']), flush=True)
    r9 = at(K, 9, .1, '14')
    print('       order 9 at x=0.1: C8 component %.4e (order 8: %.4e)' % (r9['C8_component_before'], at(K, 8, .1)['C8_component_before']), flush=True)
print('FINISHED stage 4 (precision); all checks passed', flush=True)
