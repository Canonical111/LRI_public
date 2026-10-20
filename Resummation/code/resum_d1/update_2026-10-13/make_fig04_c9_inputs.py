#!/usr/bin/env python3
"""Figure 04 right-panel input with the K=8 row referenced to C9 predicted by CB from the K=8 baseline (2026-10-13).

Reads update_2026-10-12/pipeline_K8/results/c9cb8_sensitivity_dense_K.csv and c9cb8_validation.json (written by
run_c9_cbK8ref.py) and writes fig04_c9_inputs.json next to this file, with rows in the format of the 'c9' block of
plot_data_1d_K8.json (K, x, shift_if_ref, resp_1pct, resp_5pct, C9_implied_by_CB8) plus C9_reference.
Checks: the K=4 rows equal the 'c9' rows of plot_data_1d_K8.json (archived reference, unchanged lower row) to
1e-13; the K=8 grid equals that of plot_data_1d_K8.json; the K=8 shift vanishes identically.
plot_data_1d_K8.json is only read.
2026-10-13 (C8(1) final): inputs and output follow the C8(1) switch (update_2026-10-13/C8_1_ext/c8_1_switch.py): with
LRI_C8_1=final it reads C8_1_ext/pipeline_K8/ and writes C8_1_ext/fig04_c9_inputs.json; the file next to this script
(2026-10-13, previous C8) is not overwritten. The K=4 rows keep the archived C9_ref (-2.190506633e8).
"""
import csv, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; PKG = HERE.parent
sys.path.insert(0, str(HERE/'C8_1_ext'))
import c8_1_switch as SW
P8 = SW.out_root()/'pipeline_K8'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
src = {'dense': P8/'results'/'c9cb8_sensitivity_dense_K.csv', 'validation': P8/'results'/'c9cb8_validation.json',
       'predictions': P8/'results'/'c9cb8_predictions.json', 'plot_data': P8/'plot_data_1d_K8.json'}
val = json.loads(src['validation'].read_text()); pre = json.loads(src['predictions'].read_text())
old = json.loads(src['plot_data'].read_text())['c9']
f = float
rows = [{'K': int(r['K']), 'x': f(r['Delta_sigma']), 'shift_if_ref': f(r['change_if_C9_equals_reference']),
         'resp_1pct': f(r['change_for_1percent_of_reference']), 'resp_5pct': f(r['change_for_5percent_of_reference']),
         'C9_implied_by_CB8': f(r['C9_implied_by_CB8']), 'C9_reference': f(r['C9_reference'])}
        for r in csv.DictReader(src['dense'].open()) if r['mode'] == 'endpoint_v' and r['K'] in ('4', '8')]
assert len(rows) == len(old) == 2008
dev4 = 0.
for a, b in zip(old, rows):
    assert a['K'] == b['K'] and a['x'] == b['x'], (a['K'], a['x'], b['K'], b['x'])
    if a['K'] == 4:
        dev4 = max(dev4, *(abs(a[k]-b[k]) for k in ('shift_if_ref', 'resp_1pct', 'resp_5pct')),
                   abs(a['C9_implied_by_CB8']/b['C9_implied_by_CB8']-1))
assert dev4 < 1e-13, dev4
assert all(r['shift_if_ref'] == 0 for r in rows if r['K'] == 8)
c9k8 = float(val['C9_reference']['8']); c9k4 = float(val['C9_reference']['4'])
assert all(r['C9_reference'] == c9k8 and r['C9_implied_by_CB8'] == c9k8 for r in rows if r['K'] == 8)
assert all(r['C9_reference'] == c9k4 for r in rows if r['K'] == 4)
out = {'meta': {'created': '2026-10-13', 'generator': 'update_2026-10-13/make_fig04_c9_inputs.py', 'C8_switch': SW.describe(),
                'C9_reference': val['C9_reference'], 'C9_reference_method': val['C9_reference_method'],
                'C9_implied_by_CB8': {'4': pre['C9_CB8_K4'], '8': pre['C9_CB8_K8']},
                'note': 'Scenario inputs, not calculated coefficients. At K=8 the reference equals the C9 implied by the plotted '
                        'CB8, so the CB8 -> CB9 shift vanishes identically; K=4 rows are those of plot_data_1d_K8.json.',
                'K4_rows_vs_plot_data_1d_K8_max_abs': dev4,
                'sources': [{'file': str(p.relative_to(PKG)), 'sha256': sha(p)} for p in src.values()]},
       'c9': rows}
(SW.out_root()/'fig04_c9_inputs.json').write_text(json.dumps(out, indent=0)+'\n')
print('wrote fig04_c9_inputs.json; C9_ref K=8', val['C9_reference']['8'], 'K=4', val['C9_reference']['4'], '; K=4 rows max dev', dev4)
