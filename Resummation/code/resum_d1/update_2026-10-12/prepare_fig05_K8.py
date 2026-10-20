#!/usr/bin/env python3
"""Inputs for Figure 05 with the K=8 baseline (endpoint-v CB8, b=3, alpha=0, short-range series through C^SR_8).
Writes fig05_K8_inputs.json: dense curves on the original 1004-point grid (inputs/plot_data.json 'curve' x values)
and every reference row (refreshed table + six literature MC) with its residual from the K=8 curve.
All residuals are Delta_E(method) - Delta_E(CB8, K=8). No reference value enters any curve.
2026-10-13: C8 from the C8(1) switch (sr_endpoint.py); writes <switch output root>/fig05_K8_inputs.json (final:
update_2026-10-13/C8_1_ext/fig05_K8_inputs.json); the 2026-10-12 file next to this script is not overwritten. The K=4
regression against the archived tables is done with the previous coefficients (code check); with LRI_C8_1=final the
change of the K=4 curves with the active C8 is recorded under 'K4_change_with_active_C8'.
"""
import json, csv
from pathlib import Path
import numpy as np
import sr_endpoint as S
HERE = Path(__file__).resolve().parent; PKG = HERE.parent
raw = json.loads((PKG/'inputs/plot_data.json').read_text())
xs = np.array([float(r['Delta_sigma']) for r in raw['curve']]); assert len(xs) == 1004
ref = S.cb(xs, 8)
grid = lambda K: [S.cb(xs, K, o, b, a) for o in (6, 7, 8) for b in (2, 3, 4) for a in (-1, 0, 1)]
cores = {K: grid(K) for K in (4, 5, 6, 7, 8)}
env_lo = np.min([np.min(cores[K], 0) for K in (5, 6, 7, 8)], 0)
env_hi = np.max([np.max(cores[K], 0) for K in (5, 6, 7, 8)], 0)
pb4, _ = S.pb(xs, 4)
# regression against the archived dense PB baseline and archived CB8
arch_pb = np.array([r['endpoint_PB8'] for r in json.loads((PKG/'dispersion/pb_dense_baseline.json').read_text())['rows']])
arch_cb = np.array([float(r['endpoint_v_L8']) for r in raw['curve']])
k4 = S.cb(xs, 4)
pb4prev, _ = S.pb(xs, 4, c=S.C_PREVIOUS); k4prev = S.cb(xs, 4, c=S.C_PREVIOUS)
reg = {'K4_PB8_vs_archived_dense_PB': float(np.max(abs(pb4prev-arch_pb))), 'K4_CB8_vs_archived_CB8': float(np.max(abs(k4prev-arch_cb)))}
assert reg['K4_PB8_vs_archived_dense_PB'] < 1e-11 and reg['K4_CB8_vs_archived_CB8'] < 1e-12, reg
if S.SW.MODE != 'previous':
    reg['K4_change_with_active_C8'] = {'PB8_minus_archived_dense_PB_max_abs': float(np.max(abs(pb4-arch_pb))),
                                       'CB8_minus_archived_CB8_max_abs': float(np.max(abs(k4-arch_cb)))}
curve = []
for i, x in enumerate(xs):
    curve.append({'Delta_sigma': float(x), 'CB8_K8': float(ref[i]),
                  'K4_CB8_minus_K8': float(k4[i]-ref[i]), 'K4_PB8_minus_K8': float(pb4[i]-ref[i]),
                  'env_lo_minus_K8': float(env_lo[i]-ref[i]), 'env_hi_minus_K8': float(env_hi[i]-ref[i]),
                  'K4_core_lo_minus_K8': float(np.min(cores[4], 0)[i]-ref[i]),
                  'K4_core_hi_minus_K8': float(np.max(cores[4], 0)[i]-ref[i])})
for K in (5, 6, 7):
    yk = S.cb(xs, K)
    for i in range(len(xs)): curve[i][f'K{K}_CB8_minus_K8'] = float(yk[i]-ref[i])
refs = []
for r in csv.DictReader(open(S.SW.references_csv())):   # NRG rev 2 with LRI_C8_1=final (2026-10-13)
    x = float(r['x']); k8 = float(S.cb(np.array([x]), 8)[0])
    refs.append({**{k: r[k] for k in ('method', 'x', 'y', 'error', 'stat', 'error_kind', 'status', 'source')},
                 'CB8_K8': k8, 'method_minus_K8': float(r['y'])-k8})
for r in json.loads((PKG/'inputs/mc_literature.json').read_text()):
    x = float(r['x']); k8 = float(S.cb(np.array([x]), 8)[0])
    refs.append({**{k: str(r.get(k, '')) for k in ('method', 'x', 'y', 'error', 'stat', 'error_kind', 'status', 'source')},
                 'CB8_K8': k8, 'method_minus_K8': float(r['y'])-k8})
ext = []
for r in refs:
    if r['method'] == 'HT' and abs(float(r['x'])-.001) < 1e-12: continue
    e = max(float(r['error'] or 0), float(r['stat'] or 0))
    ext += [1e3*(r['method_minus_K8']-e), 1e3*(r['method_minus_K8']+e)]
out = {'baseline': 'endpoint-v CB8, N=8, b_L=3, alpha=0, short-range series through C^SR_8',
       **({} if S.SW.MODE == 'previous' else {'C8_switch': S.SW.describe()}),
       'regression': reg, 'curve': curve, 'references': refs,
       'displayed_residual_range_1e3': [min(ext), max(ext)]}
target = S.SW.out_root()/'fig05_K8_inputs.json'
target.write_text(json.dumps(out, indent=1)); print('wrote', target)
print('regression', reg); print('refs', len(refs), 'display range (1e3 units)', [round(v, 2) for v in out['displayed_residual_range_1e3']])
