#!/usr/bin/env python3
"""Refresh the 1d reference table of the resummation package (2026-10-12).

Input  : ../inputs/references.csv (frozen 2026-10-07 table: 13 HT, 13 NRG, 17 MC rows), unchanged.
Sources: HT = density-basis campaign dens_v1 to N=40 (lri_dressed_phi4_hpc_loop/analysis/dens_v1_extrapolation.json),
         statuses from lri_dressed_phi4_hpc/HPC_CAMPAIGN_REPORT.md Sec. 8 addendum (final at Delta_sigma >= 0.1 at the
         fit half-spread; 0.075 with an extra one-sided -5e-4; 0.05 unstable; <= 0.025 no continuum limit).
         The frozen table used the earlier 'old_window' extrapolations (identical for Delta_sigma >= 0.15).
         NRG rows: unchanged values; rows at Delta_sigma >= 0.225 flagged (truncation bias near s=1/2, 4x the quoted
         error at 0.249 and 0.24 against HT and the epsilon series; paper Sec. nrg).
         MC rows: unchanged (MC package 2026-10-07 is current).
Output : references_refreshed.csv (same columns + 'refresh_note').
"""
import csv, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
AGENT = HERE.parent.parent
old = list(csv.DictReader(open(HERE.parent/'inputs/references.csv')))
ext = {round(r['delta'], 6): r for r in json.load(open(AGENT/'lri_dressed_phi4_hpc_loop/analysis/dens_v1_extrapolation.json'))}
rows, seen = [], set()
for r in old:
    r = dict(r); x = round(float(r['x']), 6); r['refresh_note'] = ''
    if r['method'] == 'HT':
        key = ('HT', x)
        if key in seen:            # the frozen table repeats the 0.249 and 0.24 rows; keep one copy
            continue
        seen.add(key)
        e = ext.get(x)
        if e is None:              # Delta_sigma = 0.001: not in dens_v1; keep the frozen row, marked
            r['status'] = 'no_limit'; r['refresh_note'] = 'not in dens_v1; frozen value kept, no continuum limit'
        else:
            f = e['fit']; nmax = e['cuts'][-1]; vmax = e['values'][-1]
            old_y = float(r['y'])
            if x >= 0.1:
                r['y'], r['error'], r['status'] = f['D_inf'], f['spread_half'], 'final'
                r['error_kind'] = 'half-spread of accepted fits (model spread, not a standard deviation)'
            elif abs(x-0.075) < 1e-9:
                r['y'], r['error'], r['status'] = f['D_inf'], f['spread_half'], 'one_sided'
                r['error_kind'] = 'half-spread of accepted fits; extra one-sided -5e-4 (limit more likely lower)'
            elif abs(x-0.05) < 1e-9:
                r['y'], r['error'], r['status'] = vmax, '', 'unstable'
                r['error_kind'] = 'no value quoted: fit forms give 0.6220-0.6225 (upper estimate) or down to 0.618; y = N=40 value'
            else:
                r['y'], r['error'], r['status'] = vmax, '', 'no_limit'
                r['error_kind'] = 'no continuum limit (window model drifts); y = finite-cutoff N=40 value'
            r['refresh_note'] = f'dens_v1 N<={nmax}; frozen value {old_y:.8f}; change {float(r["y"])-old_y:+.2e}'
        r['source'] = 'dens_v1_extrapolation.json + HPC_CAMPAIGN_REPORT.md Sec. 8'
        r['endpoint_CB8'] = ''; r['method_minus_endpoint_CB8'] = ''   # recomputed by sr_endpoint.py
    elif r['method'] == 'NRG' and x >= 0.225 - 1e-9:
        r['status'] = 'flagged'; r['refresh_note'] = 'NRG truncation bias near s=1/2 (4x quoted error at 0.249, 0.24)'
    rows.append(r)
fields = list(old[0].keys()) + ['refresh_note']
with open(HERE/'references_refreshed.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
print(len(old), 'frozen rows ->', len(rows), 'refreshed rows')
for r in rows:
    if r['method'] == 'HT' or r['status'] == 'flagged':
        print(r['method'], r['x'], round(float(r['y']), 8), r['status'], r['refresh_note'])
