#!/usr/bin/env python3
"""Replace the 13 NRG rows of the 1d reference table with the revised NRG results (2026-10-13, local, seconds).

Input : update_2026-10-12/references_refreshed.csv (unchanged; still the table of LRI_C8_1=previous).
        <PAPER>/notes/public_repo/NRG/patches/results/ds13_final.json (NRG rev 2: settled late-window estimator,
        plateau or extrapolated; error 'total' = chain depth + K/n_b spread + Lambda, added linearly, not an s.d.).
Output: update_2026-10-13/references_nrg_rev2.csv (same columns), read by every stage with LRI_C8_1=final through
        C8_1_ext/c8_1_switch.py references_csv().
NRG rows: y = Delta_E; Delta_sigma <= 0.2: status 'final', error = total; Delta_sigma = 0.225, 0.24, 0.249: status
'not_converged' (not converged in chain depth), settled value, no error, not used in any comparison (author decision).
method_minus_endpoint_CB8 is recomputed from the archived endpoint_CB8 column. HT and MC rows are copied unchanged.
"""
import csv, hashlib, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
PKG = HERE.parent
SRC = PKG/'update_2026-10-12'/'references_refreshed.csv'
NRG = PKG.parent/'<PAPER>'/'notes'/'public_repo'/'NRG'/'patches'/'results'/'ds13_final.json'
OUT = HERE/'references_nrg_rev2.csv'

old = list(csv.DictReader(SRC.open()))
fields = list(old[0].keys())
nrg = {round(r['ds'], 6): r for r in json.loads(NRG.read_text())}
assert len(nrg) == 13
rows, changes = [], []
for r in old:
    r = dict(r)
    if r['method'] == 'NRG':
        x = round(float(r['x']), 6); n = nrg.pop(x)
        y = float(n['Delta_E'])
        if n['status'] == 'final':
            assert x <= 0.2 + 1e-12 and n['total'] is not None
            assert abs(n['total'] - (n['depth'] + n['keep_nb'] + n['Lambda'])) < 1e-15   # linear sum
            err, status = repr(float(n['total'])), 'final'
            kind = 'linear sum of chain-depth, K/n_b and Lambda errors (not a standard deviation)'
        else:
            assert n['status'] == 'not converged' and x >= 0.225 - 1e-12 and n['total'] is None
            assert n['Delta_E'] == n['settled']
            err, status = '', 'not_converged'
            kind = 'no error: settled late-window value, not converged in chain depth; not used in the comparison'
        note = 'NRG rev 2 (%s); previous %s(%s); change %+.2e' % (n['estimator'], r['y'], r['error'], y - float(r['y']))
        changes.append({'x': x, 'old': float(r['y']), 'old_error': float(r['error']), 'new': y,
                        'new_error': float(err) if err else None, 'status': status})
        r.update({'y': repr(y), 'error': err, 'stat': '', 'error_kind': kind, 'status': status,
                  'method_minus_endpoint_CB8': repr(y - float(r['endpoint_CB8'])) if r['endpoint_CB8'] else '',
                  'source': 'NRG ds13_final.json (rev 2, 2026-10-13)', 'refresh_note': note})
    rows.append(r)
assert not nrg, nrg
with OUT.open('w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)

# checks: non-NRG rows identical; the example quoted in the request
back = list(csv.DictReader(OUT.open()))
assert [r for r in back if r['method'] != 'NRG'] == [r for r in old if r['method'] != 'NRG']
ex = next(c for c in changes if c['x'] == 0.1)
assert round(ex['new'], 6) == 0.529608 and round(ex['new_error'], 6) == 3.3e-5 and ex['old'] == 0.52983
for c in changes:
    print('%6.3f  %.6f(%s) -> %.6f %s  %s' % (c['x'], c['old'], c['old_error'], c['new'],
          '(%.1e)' % c['new_error'] if c['new_error'] else '(no error)', c['status']))
fin = [c for c in changes if c['status'] == 'final']
print('final points: shift %.1e .. %.1e; error ratio old/new %.1f .. %.1f' % (
    min(c['new'] - c['old'] for c in fin), max(c['new'] - c['old'] for c in fin),
    min(c['old_error'] / c['new_error'] for c in fin), max(c['old_error'] / c['new_error'] for c in fin)))
print('ds13_final.json sha256', hashlib.sha256(NRG.read_bytes()).hexdigest())
print('wrote', OUT.relative_to(PKG), 'sha256', hashlib.sha256(OUT.read_bytes()).hexdigest())
