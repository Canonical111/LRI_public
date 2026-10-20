#!/usr/bin/env python3
"""Which comparison data, if any, discriminate the K=4 and K=8 baselines (2026-10-14; replaces the 2026-10-13 version).

Change against update_2026-10-13/k4_vs_k8_discrimination.py: the author decided (2026-10-14) not to combine the HT
model dependence into one HT error. HT is therefore compared with its quoted error only (half-spread of the accepted
fits), and the dependence on the truncation prescription is shown separately, not added: the HT model-dependence
record gives the window-corrected limit, the limit of the raw (energy-basis) truncation and the largest tail-model
shift. A separation that is smaller than the raw-window difference is marked in the verdict.
Baselines: endpoint-v CB8 (N=8, b_L=3, alpha=0) with the short-range series through C^SR_4 (archived) and C^SR_8.
Data: update_2026-10-13/C8_1_ext/pipeline_K8/results/comparison_points_K.csv (CB8_K4, CB8_K8 exact at each point;
NRG rev 2) and the HT record model_dependence.json (HT folder, results/HT_1d/; path given with --ht).
Errors are model spreads (HT), linear sums (NRG, not s.d.) or stat (+) sys (MC); the ratios are descriptive.
Per point: sep = K4 - K8; z_K = (y - CB8_K)/err.
Verdict: 'not resolved' if |sep| < 2 err; 'K=8 only' / 'K=4 only' if that curve is within one error and the other more
than two errors away; 'neither (between|outside, nearer K=n)' if both are more than one error away; else 'both within
reach'. For HT the verdict gets ' (prescription >= sep)' when |window - raw| >= |sep|.
Output: update_2026-10-14/k4_vs_k8_discrimination.csv; a table on stdout.
Usage: python3 k4_vs_k8_discrimination.py [--ht model_dependence.json] [--out file.csv]
"""
import argparse, csv, json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
CP = PKG/'update_2026-10-13'/'C8_1_ext'/'pipeline_K8'/'results'/'comparison_points_K.csv'
ap = argparse.ArgumentParser()
ap.add_argument('--ht', default=str(PKG.parent/'<PAPER>'/'notes'/'public_repo'/'HT'/'d1'/'results_HT_1d'/'model_dependence.json'))
ap.add_argument('--out', default=str(HERE/'k4_vs_k8_discrimination.csv'))
a = ap.parse_args()

md = {round(r['delta'], 6): r for r in json.loads(Path(a.ht).read_text())}
assert sorted(md) == [0.075, 0.1, 0.125, 0.15, 0.175, 0.2], sorted(md)


def verdict(zk8, zk4):
    if abs(zk8 - zk4) < 2:                     # z_K8 - z_K4 = (K4 - K8)/err
        return 'not resolved'
    if abs(zk8) <= 1 and abs(zk4) > 2:
        return 'K=8 only'
    if abs(zk4) <= 1 and abs(zk8) > 2:
        return 'K=4 only'
    if abs(zk8) > 1 and abs(zk4) > 1:
        return 'neither (%s, nearer K=%d)' % ('between' if zk8 * zk4 < 0 else 'outside', 8 if abs(zk8) < abs(zk4) else 4)
    return 'both within reach'


rows = []
for r in csv.DictReader(CP.open()):
    m, x = r['method'], float(r['x']); y, k4, k8 = float(r['y']), float(r['CB8_K4']), float(r['CB8_K8'])
    err, kind, presc, tail = None, None, '', ''
    if m == 'NRG' and r['status'] == 'final':
        err, kind = float(r['error']), 'NRG total (linear sum)'
    elif m == 'HT' and r['status'] in ('final', 'one_sided'):
        err, kind = float(r['error']), 'HT half-spread of accepted fits'
        h = md.get(round(x, 6))
        if h:
            assert abs(h['window'] - y) < 1e-12, (x, h['window'], y)       # the record is the shipped HT value
            presc, tail = abs(h['window'] - h['raw']), abs(h['tail_shift'])
    elif m == 'MC' and r['status'].startswith('ACCEPTED'):
        err, kind = math.hypot(float(r['error']), float(r['stat'])), 'MC stat (+) sys'
    if err is None:
        continue
    zk8, zk4 = (y - k8)/err, (y - k4)/err
    v = verdict(zk8, zk4)
    if presc != '' and presc >= abs(k4 - k8):
        v += ' (prescription >= sep)'
    rows.append({'method': m, 'Delta_sigma': r['x'], 'K4_minus_K8': k4 - k8, 'y_minus_K8': y - k8, 'y_minus_K4': y - k4,
                 'error_kind': kind, 'error': err, 'sep_over_error': abs(k4 - k8)/err, 'z_K8': zk8, 'z_K4': zk4,
                 'HT_window_minus_raw': presc, 'HT_tail_shift': tail, 'verdict': v})
with open(a.out, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print('%-4s %6s %9s %9s %9s  %8s %7s %7s %9s  %s' % ('meth', 'Ds', 'K4-K8', 'y-K8', 'y-K4', 'err', 'z_K8', 'z_K4', 'win-raw', 'verdict'))
for r in rows:
    print('%-4s %6.4f %+9.2e %+9.2e %+9.2e  %8.1e %+7.2f %+7.2f %9s  %s' % (
        r['method'], float(r['Delta_sigma']), r['K4_minus_K8'], r['y_minus_K8'], r['y_minus_K4'], r['error'], r['z_K8'],
        r['z_K4'], '%.1e' % r['HT_window_minus_raw'] if r['HT_window_minus_raw'] != '' else '', r['verdict']))
print('wrote', a.out)
