#!/usr/bin/env python3
"""Stage 6: assemble plot_data_1d_K8.json for plot_lri_comparisons.wl (figures 01-04) from the pipeline results.

Pure bookkeeping (column selection, differences are left to the plot script except where noted); no numerics.
Tables:
  curve      1004 rows (curve grid): CB8 for K=4..8 and the GFF-only CB8, K=8 and K=4 core bands, K=5..8 envelope.
  ablation   502 rows (archived ablation grid): CB n=6,7,8 x b=0,2,3,4 for K=4 and 8; PB with the archived shapes
             [4/2] (n=6), [5/2] (n=7), [5/3] (n=8), b=3, wherever admissible (K=4..7 for [5/3]; none at K=8);
             endpoint-epsilon CB8 and PB[5/3] (b=3) where admissible (K=4, 6, 7).
  references 49 rows: refreshed 43 + 6 literature MC, residuals vs the K=8 baseline and vs the K=4 CB8.
  held_out   b=3 selected rows (pre-committed rule) for the direct series and the endpoint-v construction at K=4, 8.
  precision  order-8 coefficient-allowance budget on the curve grid, K=4 and K=8.
  c9         dense hypothetical-C9 responses, K=4 and K=8 (endpoint v, b=3).
2026-10-13: reads cbk.RES and writes cbk.PLOT_DATA of the C8(1) switch (final: update_2026-10-13/C8_1_ext/pipeline_K8/);
meta gains 'C8_1' (value, SE, allowance and its percentage, for the figure captions) and the admissible N=8 PB shapes.
"""
import csv, json, hashlib
from pathlib import Path
import cbk

HERE = Path(__file__).resolve().parent; R = cbk.RES
def rows(name):
    return list(csv.DictReader((R/name).open()))
f = float
curve_in = rows('curve_K.csv'); abl_in = rows('ablation_K.csv')
adm = json.loads((R/'pade_admissibility_K.json').read_text())
def admissible(mode, K, n, b, L, M):
    m = [d for d in adm if d['mode'] == mode and d['K'] == K and d['order'] == n and d['b'] == b and d['L'] == L and d['M'] == M]
    assert len(m) == 1
    return m[0]['admissible']

curve = []
for r in curve_in:
    curve.append({'x': f(r['Delta_sigma']), **{'CB8_K%d' % K: f(r['endpoint_v_K%d_L8' % K]) for K in (4, 5, 6, 7, 8)},
                  'direct_CB8': f(r['direct_L8']), 'direct_CB3': f(r['direct_L3']), 'env_lo': f(r['envelope_K5_8_min']), 'env_hi': f(r['envelope_K5_8_max']),
                  'core_lo_K4': f(r['endpoint_v_K4_core_min']), 'core_hi_K4': f(r['endpoint_v_K4_core_max']),
                  'core_lo_K8': f(r['endpoint_v_K8_core_min']), 'core_hi_K8': f(r['endpoint_v_K8_core_max'])})

pb_cols = {}
for K in (4, 5, 6, 7, 8):
    for n, (L, M) in ((6, (4, 2)), (7, (5, 2)), (8, (5, 3))):
        ok = admissible('endpoint_v', K, n, 3, L, M)
        key = 'endpoint_v_K%d_PB_%d%d_n%d_b3' % (K, L, M, n)
        assert ok == (key in abl_in[0]), key
        if ok:
            pb_cols['PB%d%d_n%d_K%d' % (L, M, n, K)] = key
eps_cols = {}
for K in (4, 5, 6, 7, 8):
    key = 'endpoint_epsilon_K%d_PB_53_n8_b3' % K
    if admissible('endpoint_epsilon', K, 8, 3, 5, 3):
        eps_cols['eps_PB53_n8_K%d' % K] = key; eps_cols['eps_CB_n8_K%d' % K] = 'endpoint_epsilon_K%d_CB_n8_b3' % K
assert 'PB53_n8_K8' not in pb_cols                       # no K=8 PB[5/3]: never substituted
ablation = []
for r in abl_in:
    row = {'x': f(r['Delta_sigma'])}
    for K in (4, 8):
        for n in (6, 7, 8):
            for b in (0, 2, 3, 4):
                row['CB_n%d_b%d_K%d' % (n, b, K)] = f(r['endpoint_v_K%d_CB_n%d_b%d' % (K, n, b)])
    for K in (5, 6, 7):
        row['CB_n8_b3_K%d' % K] = f(r['endpoint_v_K%d_CB_n8_b3' % K])
    for k, src in {**pb_cols, **eps_cols}.items():
        row[k] = f(r[src])
    ablation.append(row)

refs = []
for r in rows('comparison_points_K.csv'):
    refs.append({k: r[k] for k in ('method', 'x', 'y', 'error', 'stat', 'status', 'source')} |
                {'method_minus_K8': f(r['method_minus_K8']), 'method_minus_K4': f(r['method_minus_K4']),
                 'displayed': r['displayed'] == 'True'})
held = [h | {'b': int(h['b']), 'input_order': int(h['input_order']), 'predict_C': int(h['predict_C']),
             'absolute_relative_error': f(h['absolute_relative_error']), 'prediction': f(h['prediction']), 'actual': f(h['actual'])}
        for h in rows('held_out_K.csv')
        if h['b'] == '3' and h['selected'] == 'True' and (h['mode'] == 'direct' or (h['mode'] == 'endpoint_v' and h['K'] in ('4', '8')))]
assert len(held) == 18, len(held)
prec = [{'K': int(r['K']), 'x': f(r['Delta_sigma']), 'sum_before': f(r['sum_before']), 'sum_after': f(r['sum_after']),
         'floor_with_C8_exact': f(r['floor_with_C8_exact'])}
        for r in rows('precision_budget_K.csv') if r['order'] == '8' and r['K'] in ('4', '8')]
assert len(prec) == 2008
c9 = [{'K': int(r['K']), 'x': f(r['Delta_sigma']), 'shift_if_ref': f(r['change_if_C9_equals_reference']),
       'resp_1pct': f(r['change_for_1percent_of_reference']), 'resp_5pct': f(r['change_for_5percent_of_reference']),
       'C9_implied_by_CB8': f(r['C9_implied_by_CB8'])}
      for r in rows('c9_sensitivity_dense_K.csv') if r['mode'] == 'endpoint_v' and r['K'] in ('4', '8')]
assert len(c9) == 2008
c9meta = json.loads((R/'c9_validation.json').read_text())
sel = json.loads((R/'ablation_validation.json').read_text())['selected_PB']
out = {
    'meta': {
        'created': '2026-10-12' if cbk.MODE == 'previous' else '2026-10-13', 'generator': 'update_2026-10-12/pipeline_K8/make_plot_data.py',
        'C8_1': {'mode': cbk.MODE, 'C8': cbk.C8IN['C8'], 'sampling_se': cbk.C8IN['sampling_se'], 'allowance': cbk.C8IN['allowance'],
                 'allowance_percent': 100*cbk.C8IN['allowance']/float(cbk.C8IN['C8']), 'reported': cbk.C8IN['reported'],
                 'source': cbk.C8IN['source']},
        'PB_N8_b3_admissible_shapes_endpoint_v': {str(K): ['[%d/%d]' % (d['L'], d['M']) for d in adm if d['mode'] == 'endpoint_v' and d['K'] == K
                                                          and d['order'] == 8 and d['b'] == 3 and d['admissible']] for K in (4, 5, 6, 7, 8)},
        'baseline': 'endpoint-v CB8, N=8, b_L=3, alpha=0, short-range series imposed through C^SR_8 (K=8)',
        'archived_control': 'the same with C^SR_4 (K=4), reproduces the archived tables to <= 1e-15',
        'envelope': 'union of the core bands (N=6-8, b_L=2,3,4, alpha=-1,0,1) for K=5..8; sensitivity, not a confidence interval',
        'PB_shapes_shown': '[4/2] (N=6), [5/2] (N=7), [5/3] (N=8), b_L=3, only where admissible',
        'PB53_n8_admissible_K': sorted(int(k[-1]) for k in pb_cols if k.startswith('PB53_n8')),
        'PB_K8_N8_note': 'at K=8, N=8, b_L=3 only [3/5] is admissible among the near-diagonal candidates; not shown (no K=8 PB is substituted)',
        'PB_rule_selected_endpoint_v_b3': {k: v for k, v in sel.items() if k.startswith('endpoint_v_K') and k.endswith('b3')},
        'eps_PB53_n8_admissible_K': sorted(int(k[-1]) for k in eps_cols if k.startswith('eps_PB53')),
        'C9_reference': c9meta['reference_C9'], 'C9_reference_method': c9meta['reference_method'],
        'C9_implied_by_CB8': {str(K): next(r['C9_implied_by_CB8'] for r in c9 if r['K'] == K) for K in (4, 8)},
        'references': str(cbk.SW.references_csv().relative_to(cbk.SW.PKG)) + ' (43) + inputs/mc_literature.json (6); HT at x=0.001 not displayed',
        'sources': [{'file': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(R.glob('*.csv'))+sorted(R.glob('*.json'))]},
    'curve': curve, 'ablation': ablation, 'references': refs, 'held_out': held, 'precision': prec, 'c9': c9}
cbk.PLOT_DATA.write_text(json.dumps(out, indent=0))
print('wrote', cbk.PLOT_DATA)
print('curve', len(curve), 'ablation', len(ablation), 'references', len(refs), 'held_out', len(held), 'precision', len(prec), 'c9', len(c9))
print('PB columns', sorted(pb_cols), 'eps', sorted(eps_cols))
print('meta', {k: v for k, v in out['meta'].items() if k != 'sources'})
