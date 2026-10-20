#!/usr/bin/env python3
"""Assemble the direct finite-cutoff table from the Gauss runs.

Inputs : results/gauss_main.jsonl, results/gauss_n8.jsonl
Outputs: results/direct_table.json   {eps: {name: {...}}}
         results/direct_table.csv
         results/crossform_check.json   (form 0 vs form 1 for no-source moments)

Naming follows the spec (spec/out/raw_requirements.json): e.g. A7_v, EQ4_d,
Q4_vvd; suffix = 'v'*a + 'd'*b, 'base' for a=b=0.  Values are DERIVATIVES
d_v^a d_delta^b I = a! b! [z^a delta^b] I at v=1, delta=0 (v=1+z).

Error estimate: err = max(|I(N_hi) - I(N_prev)|, 2e-15*abs_integral), i.e. the
change between the two highest Gauss orders, which is a conservative
diagnostic (observed convergence is geometric, roughly a factor 10^3 per +8
points at eps=0.01), with a rounding floor.  It is not an interval bound.
"""
import glob
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'results')


def name_of(n, kind, E, a, b):
    suf = 'v' * a + 'd' * b
    return '%s%s%d_%s' % ('E' if E else '', kind, n, suf if suf else 'base')


def load(paths):
    rows = []
    for p in paths:
        if os.path.exists(p):
            with open(p) as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
    return rows


def eps_label(e):
    return '%.6g' % e


def main():
    rows = load(sorted(glob.glob(os.path.join(RES, 'gauss_*.jsonl'))))
    groups = defaultdict(list)
    for r in rows:
        groups[(r['n'], r['kind'], r['E'], r['form'], eps_label(r['eps']))].append(r)
    table = defaultdict(dict)
    form1_alt = defaultdict(dict)
    for (n, kind, E, form, el), rs in sorted(groups.items()):
        rs.sort(key=lambda r: r['N'])
        best = rs[-1]
        prev = rs[-2] if len(rs) >= 2 else None
        prev2 = rs[-3] if len(rs) >= 3 else None
        for key, (val, absval) in best['coef'].items():
            a, b = map(int, key.split(','))
            fac = math.factorial(a) * math.factorial(b)
            v = val * fac
            absint = absval * fac
            entry = dict(value=v, abs_integral=absint, N=[r['N'] for r in rs], form=form,
                         N0=best['N0'] if form == 1 else None, seconds=best['seconds'])
            if prev is not None and key in prev['coef']:
                d1 = abs(v - prev['coef'][key][0] * fac)
                entry['delta_last'] = d1
                if prev2 is not None and key in prev2['coef']:
                    entry['delta_prev'] = abs(prev['coef'][key][0] * fac - prev2['coef'][key][0] * fac)
                entry['err'] = max(d1, 2e-15 * absint)
            else:
                entry['err'] = None
            nm = name_of(n, kind, E, a, b)
            if form == 1 and not E:
                form1_alt[el][nm] = entry
            else:
                table[el][nm] = entry
    # cross-form comparison
    cross = []
    for el, d in form1_alt.items():
        for nm, e1 in d.items():
            e0 = table.get(el, {}).get(nm)
            if e0 is None:
                continue
            diff = e1['value'] - e0['value']
            cross.append(dict(eps=el, name=nm, form0=e0['value'], form1=e1['value'], diff=diff,
                              rel=diff / abs(e0['value']) if e0['value'] else None,
                              err0=e0['err']))
    with open(os.path.join(RES, 'direct_table.json'), 'w') as fh:
        json.dump(table, fh, indent=1, sort_keys=True)
    with open(os.path.join(RES, 'crossform_check.json'), 'w') as fh:
        json.dump(cross, fh, indent=1)
    with open(os.path.join(RES, 'direct_table.csv'), 'w') as fh:
        fh.write('eps,name,value,err_estimate,rel_err,abs_integral,N_list,form\n')
        for el in sorted(table, key=lambda s: -float(s)):
            for nm in sorted(table[el]):
                e = table[el][nm]
                rel = (e['err'] / abs(e['value'])) if (e['err'] is not None and e['value']) else ''
                fh.write('%s,%s,%.17g,%s,%s,%.6g,%s,%d\n' % (el, nm, e['value'],
                         '%.3g' % e['err'] if e['err'] is not None else '', '%.3g' % rel if rel != '' else '',
                         e['abs_integral'], '/'.join(map(str, e['N'])), e['form']))
    # pivot of the spec's raw moments (rows) x cutoffs (columns): value and err
    spec_path = os.path.join(HERE, '..', '..', 'spec', 'out', 'raw_requirements.json')
    if os.path.exists(spec_path):
        spec = json.load(open(spec_path))['total_safe']
        cols = sorted(table, key=lambda s: -float(s))
        with open(os.path.join(RES, 'spec_moments_by_eps.csv'), 'w') as fh:
            fh.write('name,' + ','.join('value@%s,err@%s' % (c, c) for c in cols) + '\n')
            for nm in sorted(spec, key=lambda x: (spec[x]['kinks'], x)):
                cells = []
                for c in cols:
                    e = table[c].get(nm)
                    cells += (['%.17g' % e['value'], '%.2g' % e['err'] if e['err'] is not None else ''] if e else ['', ''])
                fh.write(nm + ',' + ','.join(cells) + '\n')
    nent = sum(len(v) for v in table.values())
    print('table: %d entries over %d cutoffs; cross-form pairs: %d' % (nent, len(table), len(cross)))
    worst = max((abs(c['rel']) for c in cross if c['rel'] is not None), default=None)
    print('max |rel| form0 vs form1:', worst)


if __name__ == '__main__':
    main()
