#!/usr/bin/env python3
"""Stage 5: comparison table and instanton-mismatch reuse check (analogue of lri_curve/compare.py's comparison table).

References: update_2026-10-12/references_refreshed.csv (43 rows: 13 HT with dens_v1 statuses, 13 NRG with rows at
Delta_sigma >= 0.225 flagged, 17 MC unchanged) plus the six literature MC rows of inputs/mc_literature.json.
Residuals are evaluated exactly at each x (not interpolated) against the K=8 baseline (endpoint-v CB8, b=3, alpha=0)
and against the archived K=4 CB8. References never enter a curve or select a prescription. HT at Delta_sigma=0.001
(no continuum limit) is kept in the table and flagged 'displayed = False', as in every display since 2026-10-12.
Mismatch: the ratio table of reproduction/instanton_mismatch depends only on C_2..C_8; verify that its hard-coded
coefficients equal the ones used here and recompute the ratio table from them.
Outputs in results/: comparison_points_K.csv, refs_validation.json, mismatch_check.json.
2026-10-13: C8 from the C8(1) switch (cbk.py); outputs in cbk.RES; the K=8 residuals are cross-checked against the
Figure 05 input of the same mode (cbk.FIG05, written by prepare_fig05_K8.py). The archived K=4 endpoint_CB8 column is
regressed with the previous coefficients (code check) and, with LRI_C8_1=final, the change of the K=4 CB8 is reported.
With LRI_C8_1=final the mismatch check uses the regenerated analysis (cbk.MISMATCH, written by
update_2026-10-13/C8_1_ext/instanton_mismatch/analyze.py) and reports the change against the archived ratio table.
"""
import csv, json, math, re
from pathlib import Path
import numpy as np
import mpmath as mp
import cbk

HERE = Path(__file__).resolve().parent; OUT = cbk.RES; OUT.mkdir(parents=True, exist_ok=True)
print('C8 switch:', json.dumps(cbk.SW.describe()), flush=True)
refs = list(csv.DictReader(cbk.SW.references_csv().open()))   # NRG rev 2 with LRI_C8_1=final (2026-10-13)
lit = json.loads((HERE/'inputs/mc_literature.json').read_text())
assert len(refs) == 43 and len(lit) == 6
rows = []
for r in refs+lit:
    x = float(r['x']); y = float(r['y'])
    k8 = float(cbk.dimension('endpoint_v', 8, x=np.array([x]), K=8)[0])
    k4 = float(cbk.dimension('endpoint_v', 8, x=np.array([x]), K=4)[0])
    rows.append({'method': r['method'], 'x': r['x'], 'y': r['y'], 'error': r.get('error', '') or '',
                 'stat': r.get('stat', '') or '', 'error_kind': r.get('error_kind', ''), 'status': r['status'],
                 'source': r.get('source', ''), 'refresh_note': r.get('refresh_note', ''),
                 'CB8_K8': k8, 'method_minus_K8': y-k8, 'CB8_K4': k4, 'method_minus_K4': y-k4,
                 'displayed': not (r['method'] == 'HT' and abs(x-.001) < 1e-12)})
counts = {}
for r in rows:
    counts[r['method']] = counts.get(r['method'], 0)+1
assert counts == {'HT': 13, 'NRG': 13, 'MC': 17, 'MC_literature': 6}, counts
# cross-checks: K=4 residual equals the archived/refreshed endpoint_CB8 column where present; K=8 equals fig05 inputs
k4prev = [float(cbk.dimension('endpoint_v', 8, x=np.array([float(o['x'])]), K=4, c=cbk.C_PREVIOUS)[0]) for o in refs]
k4dev = max(abs(v-float(o['endpoint_CB8'])) for v, o in zip(k4prev, refs) if o['endpoint_CB8'])
k4change = max(abs(r['CB8_K4']-float(o['endpoint_CB8'])) for r, o in zip(rows, refs) if o['endpoint_CB8'])
f5 = json.loads(cbk.FIG05.read_text())['references']
assert len(f5) == 49
k8dev = max(abs(r['method_minus_K8']-f['method_minus_K8']) for r, f in zip(rows, f5))
assert all(r['method'] == f['method'] and r['x'] == f['x'] for r, f in zip(rows, f5))
print('K4 CB8 (previous C8) at reference x vs archived endpoint_CB8: %.3e; K8 residuals vs fig05_K8_inputs: %.3e; '
      'K4 CB8 with the active C8 minus archived: %.3e' % (k4dev, k8dev, k4change), flush=True)
assert k4dev < 1e-12 and k8dev < 1e-12
with (OUT/'comparison_points_K.csv').open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
(OUT/'refs_validation.json').write_text(json.dumps({'C8_switch': cbk.SW.describe(), 'counts': counts, 'displayed': sum(r['displayed'] for r in rows),
    'K4_CB8_vs_archived_endpoint_CB8_max': k4dev, 'K8_residual_vs_fig05_K8_inputs_max': k8dev,
    'K4_CB8_active_C8_minus_archived_endpoint_CB8_max': k4change, 'fig05_input': str(cbk.FIG05.relative_to(cbk.PKG)),
    'statuses': sorted({(r['method'], r['status']) for r in rows})}, indent=1))

# instanton mismatch: coefficients and ratio table
from fractions import Fraction
if cbk.MODE == 'previous':
    src = (HERE/'inputs/archived_mismatch_analyze.py').read_text()
    m = re.search(r'C = np\.array\(\[(.*?)\]\)', src, re.S)
    hard = [float(Fraction(v.strip())) if '/' in v else float(v) for v in m.group(1).replace('\n', ' ').split(',')]
    ratio_src = HERE/'inputs/archived_ratio_table.csv'
else:                                   # regenerated analysis with the active C8 (instanton_mismatch/analyze.py)
    hard = json.loads((cbk.MISMATCH/'analysis.json').read_text())['inputs']['C']
    ratio_src = cbk.MISMATCH/'ratio_table.csv'
cur = [float(c) for c in cbk.C]
coef_rel = [abs(a-b)/abs(b) for a, b in zip(hard, cur)]
a = float(1/cbk.ACTION)
C = np.array(cur); ns = np.arange(2, 9); ratios = -C[2:]/(ns*C[1:-1])
table = [{'n': int(n), 'C_n': C[n], 'ratio': r, 'b_effective': n*(r/a-1), 'corrected_b3': r/(1+3/n),
          'normalized_b3': abs(C[n])/(a**n*math.gamma(n+4))} for n, r in zip(ns, ratios)]
arch = list(csv.DictReader(ratio_src.open()))
tdev = max(abs(t[k]/float(r[k2])-1) for t, r in zip(table, arch)
           for k, k2 in (('ratio', 'ratio'), ('b_effective', 'b_effective'), ('corrected_b3', 'corrected_b3'), ('normalized_b3', 'normalized_b3')))
KI = 0.006246637286122374
note_C6_closed_form = 14331.68703275805
check = {'hard_coded_coefficients': hard, 'pipeline_coefficients': cur, 'max_relative_coefficient_difference': max(coef_rel),
         'ratio_table_recomputed_max_relative_difference': tdev,
         'C_n_over_KI_Gamma(n+4)(-1/A)^n': {str(t['n']): t['normalized_b3']/KI for t in table if t['n'] >= 3},
         'C8(1)': {'value': cur[8], 'status': 'final since 2026-10-03 (condensed note Sec. 1 table: (8.067 +- 0.033) x 10^6)'}
                  if cbk.MODE == 'previous' else
                  {'value': cur[8], 'status': 'FINAL 2026-10-13: (8.060 +- 0.017) x 10^6 (condensed note fa71533, Sec. 1 and 30); '
                                              'previous 8066723.342964563 (8.067 +- 0.033) x 10^6'},
         'mismatch_source': 'archived reproduction/instanton_mismatch (copied in inputs/)' if cbk.MODE == 'previous' else
                            str(cbk.MISMATCH.relative_to(cbk.PKG)) + ' (regenerated with the active C8)',
         'C6_closed_form_in_condensed_note': note_C6_closed_form,
         'C6_closed_form_minus_graph_sum_used': note_C6_closed_form-cur[6],
         'conclusion': (('Coefficients identical to the archived mismatch analysis to %.1e relative; the ratio table is reproduced to %.1e. '
                         'The mismatch ratios do not depend on K or on the resummation and are reused unchanged.') if cbk.MODE == 'previous' else
                        ('Coefficients identical to the regenerated mismatch analysis (final C8(1)) to %.1e relative; its ratio table is reproduced '
                         'to %.1e. The mismatch ratios do not depend on K or on the resummation; only n=8 changes with C8(1).')) % (max(coef_rel), tdev)}
if cbk.MODE != 'previous':
    old = list(csv.DictReader((HERE/'inputs/archived_ratio_table.csv').open()))
    check['n8_change_vs_archived_ratio_table'] = {k: {'archived': float(old[-1][k]), 'new': float(arch[-1][k])}
                                                  for k in ('C_n', 'ratio', 'b_effective', 'corrected_b3', 'normalized_b3')}
    check['n8_C_n_over_KI_archived'] = float(old[-1]['normalized_b3'])/KI
    check['rows_n2_to_n7_vs_archived_max_relative'] = max(abs(float(n[k])/float(o[k])-1) for o, n in zip(old[:-1], arch[:-1]) for k in o if k != 'n')
    assert check['rows_n2_to_n7_vs_archived_max_relative'] < 1e-13          # rows n=2..7 do not involve C8
(OUT/'mismatch_check.json').write_text(json.dumps(check, indent=1))
print('mismatch: max coefficient rel diff %.2e, ratio table rel diff %.2e; C8/[K_I...] at n=8 = %.4f' %
      (max(coef_rel), tdev, check['C_n_over_KI_Gamma(n+4)(-1/A)^n']['8']), flush=True)
assert max(coef_rel) < 1e-11 and tdev < 1e-9
print('FINISHED stage 5 (references, mismatch); all checks passed', flush=True)
