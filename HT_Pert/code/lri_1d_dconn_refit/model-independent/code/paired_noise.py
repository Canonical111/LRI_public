#!/usr/bin/env python3
"""refit72: paired comparison of two grid runs on IDENTICAL configurations (primary family dconn E full wf), to separate
the effect of the S10 noise on individual fits from its effect on the selection.  usage: paired_noise.py GRID_A GRID_B"""
import sys, json
import numpy as np
REF = {4: 45.42488010356, 5: -731.13947662454, 6: 14331.68703277, 7: -322550.0, 8: 8066723.0}
def idx(p):
    G = json.load(open(p)); out = {}
    for res in G['results']:
        c = res['cfg']
        for r in res['rows']:
            if r['kind'] == 'dconn' and r['mode'] == 'E' and r['level'] == 'full' and r['om'] == 'wf':
                out[(c['tails'], c['lead'], c['lo'], c['hi'], r['n'])] = r['c']
    return out
A, B = idx(sys.argv[1]), idx(sys.argv[2])
for hi in (60, 72, 92, 118):
    for n in range(4, 9):
        keys = [k for k in A if k[3] == hi and k[4] == n and k in B]
        if not keys:
            continue
        d = np.array([A[k] - B[k] for k in keys])
        print('hi%-3d C%d  N %4d  median diff %+.4g  p10..p90 [%+.3g, %+.3g]  rel med %+.2e' % (hi, n, len(keys), np.median(d), *np.percentile(d, [10, 90]), np.median(d) / abs(REF[n])))
    keys8 = [k[:4] for k in A if k[3] == hi and k[4] == 8 and k in B and all((k[:4] + (j,)) in A and (k[:4] + (j,)) in B for j in range(4, 8))]
    if keys8:
        def cal(D, k): return D[k + (8,)] * (1 - np.mean([(D[k + (j,)] - REF[j]) / abs(REF[j]) for j in range(4, 8)]))
        d = np.array([cal(A, k) - cal(B, k) for k in keys8])
        print('hi%-3d C8cal N %4d  median diff %+.4g  p10..p90 [%+.3g, %+.3g]' % (hi, len(keys8), np.median(d), *np.percentile(d, [10, 90])))
