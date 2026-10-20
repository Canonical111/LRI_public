#!/usr/bin/env python3
"""Summarise results/*.json: print a table and write results/summary.json (machine-readable)."""
import glob
import json
import os
import sys

import mpmath as mp

mp.mp.dps = 60
here = os.path.dirname(os.path.abspath(__file__))
R = {}
for fn in sorted(glob.glob(os.path.join(here, 'results', '*.json'))):
    d = json.load(open(fn))
    if isinstance(d, dict) and 'modes' in d:
        R[os.path.basename(fn)[:-5]] = d


def modes(d):
    return {int(k): mp.mpmathify(v) for k, v in d['modes'].items()}


def e(x):
    return mp.nstr(x, 2) if x != 0 else '0'


SUMMARY = {}


def row(key, d, ref=None):
    m = modes(d)
    r = d['r']
    sc = max(abs(v) for v in m.values())
    low = max(abs(m[k]) for k in m if abs(k) < r - 1)
    tm, tp = abs(m[-(r - 1)]) / sc, abs(m[r - 1]) / sc
    bm = abs(m[-r]) / sc if -r in m else None
    bp = abs(m[r]) / sc if r in m else None
    asym = abs(abs(m[r - 2]) - abs(m[-(r - 2)])) / sc if r >= 3 else 0
    est = ''
    if ref is not None:
        mr = modes(ref)
        est = e(max(abs(m[k] - mr[k]) for k in m if k in mr) / sc)
    cc = d['condC']
    SUMMARY[key] = dict(r=r, d=d['d'], top_minus=e(tm), top_plus=e(tp), beyond_minus=e(bm) if bm is not None else None,
                        beyond_plus=e(bp) if bp is not None else None, max_lower_over_max=e(low / sc),
                        diff_vs_fine=est or None, inside_C=cc['inside'], balance_defects=d['balance_defects'],
                        cfg=d['cfg'], wall_s=d['wall_s'])
    return ('| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
        key, r, d['d'], mp.nstr(mp.mpmathify(d['G']), 5), '%s > %s' % (cc['alpha'][:6], cc['bound'][:6]),
        d['min_Re_g'], ','.join(x for x in d['balance_defects']), e(tm), e(tp),
        (e(bm) + ', ' + e(bp)) if bm is not None else '-', e(low / sc), e(asym), est), tm, tp)


def main():
    lines = ['| run | r | d | G | alpha > bound (C) | min Re g | (B) defects | c_-(r-1)/max | c_+(r-1)/max | c_-r, c_+r /max | max lower/max | ||c_{r-2}|-|c_{2-r}||/max | diff vs finer run |',
             '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for key, d in R.items():
        if key.endswith('_fine') or key.endswith('_imag'):
            continue
        ref = R.get(key + '_fine')
        lines.append(row(key, d, ref)[0])
    for key, d in R.items():
        if key.endswith('_fine') or '_imag' in key:
            lines.append(row(key, d)[0])
    txt = '\n'.join(lines)
    print(txt)
    with open(os.path.join(here, 'results', 'summary.json'), 'w') as f:
        json.dump(SUMMARY, f, indent=1)


if __name__ == '__main__' and len(sys.argv) == 1:
    main()


def controls():
    """per-factor imbalance: c_{+-(r-1)}(eps)/eps -> const (linearity); continuation vs plain near the boundary."""
    out = {}
    for base in ('A1', 'A2'):
        rows = []
        for key, d in R.items():
            if not key.startswith('CI_%s_' % base):
                continue
            eps = key.split('_', 2)[2]
            epsv = mp.mpmathify(eps.replace('p', '+').replace('m', '-')) if 'j' not in eps else \
                mp.mpc(*[mp.mpf(x) for x in eps.replace('j', '').replace('p', ' ').split()])
            m = modes(d)
            r = d['r']
            sc = max(abs(v) for v in m.values())
            rows.append((abs(epsv), eps, m[-(r - 1)] / epsv, m[r - 1] / epsv, abs(m[-(r - 1)]) / sc, abs(m[r - 1]) / sc,
                         abs(m[-r]) / sc, abs(m[r]) / sc))
        rows.sort(key=lambda x: -x[0])
        if not rows:
            continue
        print('\nimbalance control on %s: beta_1 += eps, beta_2 -= eps' % base)
        print('eps | c_-(r-1)/eps | c_+(r-1)/eps | |c_-(r-1)|/max | |c_+(r-1)|/max | |c_-r|,|c_+r| /max')
        ref = rows[-1]
        tab = []
        for x in rows:
            print('%s | %s | %s | %s | %s | %s, %s' % (x[1], mp.nstr(x[2], 10), mp.nstr(x[3], 10), mp.nstr(x[4], 3),
                                                      mp.nstr(x[5], 3), mp.nstr(x[6], 2), mp.nstr(x[7], 2)))
            tab.append(dict(eps=x[1], cminus_over_eps=mp.nstr(x[2], 15), cplus_over_eps=mp.nstr(x[3], 15),
                            top_minus_rel=mp.nstr(x[4], 4), top_plus_rel=mp.nstr(x[5], 4),
                            beyond_rel=[mp.nstr(x[6], 3), mp.nstr(x[7], 3)],
                            dev_from_smallest_eps_minus=mp.nstr(abs(x[2] - ref[2]) / abs(ref[2]), 3),
                            dev_from_smallest_eps_plus=mp.nstr(abs(x[3] - ref[3]) / abs(ref[3]), 3)))
        out['imbalance_' + base] = tab
    # continuation vs plain inside (C) near the boundary
    if 'I1_cont' in R and 'I1_plain' in R:
        a, b = modes(R['I1_cont']), modes(R['I1_plain'])
        sc = max(abs(v) for v in a.values())
        dev = max(abs(a[k] - b[k]) for k in a if k in b) / sc
        print('\nI1 (inside, 2alpha-d=0.1): continued-corner vs plain evaluation, max mode deviation / max = %s' % mp.nstr(dev, 3))
        out['I1_cont_vs_plain'] = mp.nstr(dev, 3)
    for k in ('O1_plainD26', 'O1_plainD36'):
        if k in R:
            print('%s (outside, no continuation): max|c| = %s' % (k, R[k]['scale_max_abs_c']))
            out[k + '_max_abs_c'] = R[k]['scale_max_abs_c']
    with open(os.path.join(here, 'results', 'summary_controls.json'), 'w') as f:
        json.dump(out, f, indent=1)


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'controls':
    controls()
