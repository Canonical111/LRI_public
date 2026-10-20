#!/usr/bin/env python3
"""Markdown summary of the GLS engine comparison and of the injection calibration (used for the README).

  python3 summarize_engine_comparison.py > ../results/engine_comparison_summary.md
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'results')
SPEC = os.path.join(HERE, '..', '..', 'spec', 'out', 'raw_requirements.json')


def g(x, f='%.1e'):
    return '-' if x is None else f % x


def main():
    spec = json.load(open(SPEC))['total_safe']
    five = sorted(n for n, v in spec.items() if v['kinks'] >= 5)
    print('#### Verdicts on the existing engine output\n')
    print('| engine file(s) | PASS | TENSION | OFFSET | MODEL-FAIL | INCONCLUSIVE | UNTESTABLE |')
    print('|---|---|---|---|---|---|---|')
    allres = {}
    for cfg in ('validation_c', 'validation_d', 'pilot5', 'merged'):
        p = os.path.join(RES, 'engine_comparison_%s_offsets.json' % cfg)
        if not os.path.exists(p):
            continue
        rs = json.load(open(p))
        allres[cfg] = {r['name']: r for r in rs}
        t = {}
        for r in rs:
            t[r['verdict']] = t.get(r['verdict'], []) + [r['name']]
        cells = []
        for v in ('PASS', 'TENSION', 'OFFSET', 'MODEL-FAIL', 'INCONCLUSIVE', 'UNTESTABLE'):
            names = t.get(v, [])
            cells.append('%d' % len(names) + (' (%s)' % ', '.join(names) if v in ('TENSION', 'OFFSET', 'MODEL-FAIL')
                                                and names else ''))
        print('| %s | %s |' % (cfg, ' | '.join(cells)))
    print()
    cal = json.load(open(os.path.join(RES, 'injection_calibration.json')))
    byname = {}
    for r in cal['results']:
        byname.setdefault(r['name'], {})[r['config']] = r
    proj = {r['name']: r for r in cal['projection_complete']}
    print('#### 5-8 kink spec moments: verdicts and injected-error thresholds\n')
    print('Thresholds: smallest injected |delta| (ladder 0.25..100 x D3, both signs) giving a non-PASS verdict '
          '(baseline PASS only) / a robust OFFSET; relative to |c| in brackets. "proj." = design estimate of the '
          '3-sigma size 3 sqrt(u^2 + e^2) for a complete series with K = 1 (negative powers and k = 1 exact, '
          'fixed tail k = 2, 3 with log degree J0-1, * = J0-2 where J0-1 leaves < 3 dof; no tail selection, '
          'no joint X2): an order-of-magnitude guide, not a bound.\n')
    print('| moment | production format (pilot5) | complete series (merged with validation runs) | K | '
          'c00: non-PASS / OFFSET | c01: non-PASS / OFFSET | proj. c00 / c01 (K=1) |')
    print('|---|---|---|---|---|---|---|')
    for nm in five:
        rr = byname.get(nm, {})
        p5 = rr.get('pilot5')
        mg = rr.get('merged')
        v5 = p5['baseline']['verdict'] if p5 else '-'
        if p5 and p5['baseline'].get('verdict_raw'):
            v5 += ' (raw %s)' % p5['baseline']['verdict_raw']
        if p5 and p5.get('structure_missing'):
            v5 += '; %d coeff. missing' % len(p5['structure_missing'])
        vm = mg['baseline']['verdict'] if mg else '-'
        if mg and mg.get('structure_missing') and vm in ('INCONCLUSIVE', 'UNTESTABLE'):
            vm += ' (no complete series exists)'
        cols = []
        for key in ('0,0', '0,1'):
            th = (mg or {}).get('thresholds', {}).get(key)
            if not th:
                cols.append('-')
                continue
            cv = abs(th['coef_value']) or 1.0

            def one(x):
                return 'none' if x is None else '%.1e (%.0e)' % (x, x / cv)
            np_ = one(th['nonpass'].get('threshold')) if th['nonpass'].get('note') is None else 'n/a'
            cols.append('%s / %s' % (np_, one(th['offset']['threshold'])))
        pr = proj.get(nm, {}).get('K1_dJ1')
        star = ''
        if not pr:
            pr = proj.get(nm, {}).get('K1_dJ2')
            star = '*' if pr else ''
        pj = '%s / %s%s' % (g(pr.get('detect3_0')) if pr else '-', g(pr.get('detect3_1')) if pr else '-', star)
        print('| %s | %s | %s | %s | %s | %s | %s |' % (nm, v5, vm, mg['K'] if mg else '-', cols[0], cols[1], pj))
    print()


if __name__ == '__main__':
    main()
