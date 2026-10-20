#!/usr/bin/env python3
"""GFF-only CB8 residual for Figure 05 (2026-10-13). Writes fig05_gff_only_inputs.json next to this file.

Curve: CB8 of the GFF series C_0..C_8 alone, resummed directly in eps = 1 - 4 Delta_sigma (candidate action
A_eps, N=8, b_L=3, alpha=0, no short-range input). This is the pipeline's 'direct' mode, column direct_L8 of
update_2026-10-12/pipeline_K8/results/curve_K.csv, which Figure 01 draws as direct_CB8
(update_2026-10-12/pipeline_K8/plot_data_1d_K8.json).
Residual: direct_CB8 - CB8_K8, with CB8_K8 taken from update_2026-10-12/fig05_K8_inputs.json (the Figure 05
baseline) on its 1004-point grid.
Checks: identical grid; fig05 CB8_K8 equals the pipeline's endpoint_v_K8_L8; plot_data direct_CB8 equals
direct_L8; independent re-evaluation of the curve at all 1004 points with the 'eps' variant of
update_2026-10-12/gff_only_v.py.
The validated inputs are only read. Run from anywhere: python3 update_2026-10-13/prepare_fig05_gff_only.py
2026-10-13 (C8(1) final): inputs and output follow the C8(1) switch (update_2026-10-13/C8_1_ext/c8_1_switch.py; the
GFF-only CB8 uses C8 too): with LRI_C8_1=final it reads C8_1_ext/{fig05_K8_inputs.json, pipeline_K8/} and writes
C8_1_ext/fig05_gff_only_inputs.json; the file next to this script (previous C8) is not overwritten.
"""
import csv, hashlib, json, sys
from pathlib import Path
import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent; PKG = HERE.parent; U12 = PKG/'update_2026-10-12'
sys.path.insert(0, str(HERE/'C8_1_ext'))
import c8_1_switch as SW
ROOT = SW.out_root()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
FRAME = (-35.0, 40.0)   # Figure 05 vertical range, units of 1e-3

src = {'fig05': ROOT/'fig05_K8_inputs.json', 'curve_K': ROOT/'pipeline_K8'/'results'/'curve_K.csv',
       'plot_data': ROOT/'pipeline_K8'/'plot_data_1d_K8.json', 'gff_only_v': U12/'gff_only_v.py',
       'sr_endpoint': U12/'sr_endpoint.py', 'evidence': PKG/'baseline'/'inputs'/'evidence.json',
       'c8_switch': SW.EXT/'c8_1_switch.py', 'c8_override': SW.OVERRIDE}
before = {k: sha(p) for k, p in src.items()}

f5 = json.loads(src['fig05'].read_text())['curve']
cc = list(csv.DictReader(src['curve_K'].open()))
pd = json.loads(src['plot_data'].read_text())['curve']
assert len(f5) == len(cc) == len(pd) == 1004, (len(f5), len(cc), len(pd))
xs = np.array([r['Delta_sigma'] for r in f5])
direct = np.array([float(r['direct_L8']) for r in cc])
k8 = np.array([r['CB8_K8'] for r in f5])
checks = {
    'grid_fig05_vs_curve_K_max_abs': float(np.max(np.abs(xs-np.array([float(r['Delta_sigma']) for r in cc])))),
    'grid_fig05_vs_plot_data_max_abs': float(np.max(np.abs(xs-np.array([float(r['x']) for r in pd])))),
    'fig05_CB8_K8_vs_curve_K_endpoint_v_K8_L8_max_abs': float(np.max(np.abs(k8-np.array([float(r['endpoint_v_K8_L8']) for r in cc])))),
    'plot_data_direct_CB8_vs_curve_K_direct_L8_max_abs': float(np.max(np.abs(direct-np.array([float(r['direct_CB8']) for r in pd]))))}
assert checks['grid_fig05_vs_curve_K_max_abs'] == 0 and checks['grid_fig05_vs_plot_data_max_abs'] == 0, checks
assert checks['fig05_CB8_K8_vs_curve_K_endpoint_v_K8_L8_max_abs'] < 1e-12, checks
assert checks['plot_data_direct_CB8_vs_curve_K_direct_L8_max_abs'] == 0, checks

# independent evaluation: gff_only_v.py, variant 'eps' (direct CB in eps, action A), N=8, b=3, alpha=0
sys.path.insert(0, str(U12))
print('--- gff_only_v.py import (prints its own 12-point table) ---', flush=True)
import gff_only_v as G
print('--- end of gff_only_v.py table ---', flush=True)
indep = np.asarray(G.curve('eps', xs, order=8, b=3, alpha=0), dtype=float)
checks['gff_only_v_eps_vs_direct_L8_max_abs'] = float(np.max(np.abs(indep-direct)))
assert checks['gff_only_v_eps_vs_direct_L8_max_abs'] < 1e-12, checks
# 2026-10-13: the CB3 curve of Figure 01 (C_0..C_3 only) against gff_only_v.py curve('eps', x, order=3)
cb3 = np.array([float(r['direct_CB3']) for r in pd])
checks['gff_only_v_eps_order3_vs_plot_data_direct_CB3_max_abs'] = float(np.max(np.abs(np.asarray(G.curve('eps', xs, order=3, b=3, alpha=0), dtype=float)-cb3)))
assert checks['gff_only_v_eps_order3_vs_plot_data_direct_CB3_max_abs'] < 1e-12, checks

res = direct-k8
y = 1e3*res
inside = y >= FRAME[0]
first = int(np.argmax(inside)); assert inside[first:].all() and not inside[:first].any(), 'frame entry is not a single crossing'
assert np.all(y <= 1e-9), 'GFF-only CB8 above the K=8 baseline somewhere'
x0, x1, y0, y1 = xs[first-1], xs[first], y[first-1], y[first]
out = {'created': '2026-10-13', 'generator': 'update_2026-10-13/prepare_fig05_gff_only.py', 'C8_switch': SW.describe(),
       'curve_definition': 'CB8 of the GFF series C_0..C_8 alone, directly in eps = 1 - 4 Delta_sigma (candidate action A_eps), '
                           'N=8, b_L=3, alpha=0, no short-range input; pipeline direct mode (curve_K.csv direct_L8)',
       'baseline': 'CB8_K8 of %s (endpoint-v CB8, N=8, b_L=3, alpha=0, short-range series through C^SR_8)' % src['fig05'].relative_to(PKG),
       'sources': [{'file': str(p.relative_to(PKG)), 'sha256': before[k]} for k, p in src.items()],
       'checks': checks,
       'figure05_frame_1e3': list(FRAME),
       'residual_1e3_at_Delta_sigma_0': float(y[0]),
       'residual_1e3_max': float(np.max(y)),
       'first_grid_point_inside_frame': float(x1),
       'frame_crossing_Delta_sigma_linear_interpolation': float(x0+(FRAME[0]-y0)/(y1-y0)*(x1-x0)),
       'points_below_frame': int(first),
       'curve': [{'Delta_sigma': float(x), 'direct_CB8': float(d), 'direct_CB8_minus_K8': float(r)}
                 for x, d, r in zip(xs, direct, res)]}
assert {k: sha(p) for k, p in src.items()} == before, 'an input changed during the run'
target = ROOT/'fig05_gff_only_inputs.json'
target.write_text(json.dumps(out, indent=1)+'\n')
print('checks', json.dumps(checks))
print('residual at 0 (1e-3):', round(out['residual_1e3_at_Delta_sigma_0'], 3), '| enters the frame at Delta_sigma =',
      round(out['frame_crossing_Delta_sigma_linear_interpolation'], 5), '| points below frame:', first)
print('wrote', target, 'sha256', sha(target))
