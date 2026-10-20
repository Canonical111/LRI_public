#!/usr/bin/env python3
"""refit72: per-configuration C8 table of the calibrated set (primary family) for one run; used to compare the noisy
exact-46..72 run with the smoothed (s46) run.  usage: percfg.py RUNDIR [HI ...]"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('MI_LIGHT', '1')
his = [int(x) for x in sys.argv[2:]] or [72, 92]
sys.argv = sys.argv[:2]
import analyze_core as an
out = {}
for hi in his:
    fam = ('dconn', 'E', 'full', 'wf', hi)
    s, sel = an.c8_family(fam); fl = an.floors(fam)
    rows = []
    for key in sorted(sel['adq']):
        F = an.R[fam][key]
        b = [an.bias(fam, key, j) for j in range(4, 8)]
        rows.append(dict(key=key, cal=key in sel['cal'], c8=F[8]['c'], c8cal=F[8]['c'] * (1 - sum(b) / 4), b=[x * 1e3 for x in b],
                         gain=F[8]['gain'], mr_over_floor=F[8]['maxres'] / fl[8]))
    out[hi] = dict(floors=fl, rows=rows, summary={q: s.get(q) for q in ('uncal_median', 'cal_median', 'N_adequate', 'N_cal')})
    print('hi', hi, 'floors', {n: '%.2e' % v for n, v in fl.items()}, out[hi]['summary'])
    for r in rows:
        print('  %-28s %s c8 %9.0f cal %9.0f b %s gain %6.0f res/floor %.1f' % (str(r['key']), 'CAL' if r['cal'] else '   ', r['c8'], r['c8cal'],
              ' '.join('%+.2f' % x for x in r['b']), r['gain'], r['mr_over_floor']))
