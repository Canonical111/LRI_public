#!/usr/bin/env python3
"""Public replay of lri_d3_matrix_update: the rank-two (Jack alpha=2) identification of the d=3 Horn functions.

Added for the public release (2026-10-13); not part of the research bundle. Run from the package folder:

    python3 public/replay.py --tier test     # about 5 s: checksums, rank_two_checks.py rerun, record checks
    python3 public/replay.py --tier replay   # about 40 s: also recompute_d3_periods.py (100 working digits)
    python3 public/replay.py --tier search   # optional, about 1 min: the bounded scalar catalogue search

The original scripts are run unchanged, with the commands of README.md, in a copy of the package under --work
(default .work/). Their outputs are compared with the shipped records in verification/ and with the numbers that the
condensed note quotes (--results, default ../../results/closed_forms_3/d3_specialization_quoted.json).
Writes <work>/REPLAY.md and exits 1 on any FAIL.
"""
import sys
from pathlib import Path

import mpmath as mp
import sympy as sp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replaylib import (PKG, Report, agrees_to_shown, check_bundle_sums, common_args, load, make_work,  # noqa: E402
                       max_leaf_difference, parse_num, py, real, run, short, strip_keys)


def rank_two_checks(rep, label, rec, q):
    rq = q['rank_two']
    src = f'{label}: rank_two_checks.json'
    for key, eq in [('matrix_H3_local_coefficients', 'matrix 3F2^(alpha=2)(3/4,3/4,3/4;3/2,3/2;zI_2)'),
                    ('ordinary_3F2_local_coefficients', 'ordinary 3F2(3/4,3/4,3/4;3/2,3/2;z)')]:
        got = [sp.Rational(x) for x in rec[key]]
        ref = [sp.Rational(x) for x in rq[key]]
        rep.check(f'{label}: {eq} coefficients of z^0..z^3 = rt:scalarDistinction', got == ref,
                  ', '.join(map(str, got)), ', '.join(map(str, ref)), 'exact', src)
    cnt = rq['package_readme_counts']
    ex = rec['exact_checks']
    rep.check(f'{label}: exact coefficientwise checks, total as in the package README',
              rec['exact_checks_total'] == cnt['exact_checks_total'] == sum(ex.values()),
              f"{rec['exact_checks_total']} ({', '.join(f'{k} {v}' for k, v in ex.items())})",
              str(cnt['exact_checks_total']), 'exact', src)
    mx = max(max(abs(mp.mpf(r['difference'])), abs(mp.mpf(r['max_coefficient_difference'])))
             for r in rec['interior_checks'])
    rep.check(f'{label}: matrix-argument and Horn partial sums agree (r=3,4,7, total degree 90)',
              mx < mp.mpf(rq['interior_bound']) and rec['precision'] == cnt['interior_precision_digits']
              and len(rec['interior_checks']) == 4, short(mx, 3), '0',
              f"{rq['interior_bound']} at {cnt['interior_precision_digits']} working digits", src)
    d = rec['parameter_dictionary']
    dq = rq['dictionary']
    ok = all(d[k]['upper'] == dq[k]['upper'] and d[k]['lower'] == dq[k]['lower'] and
             d[k]['matrix_argument'] == dq[k]['matrix_argument'] and d[k]['Jack_alpha'] == dq['Jack_alpha'] and
             d[k]['matrix_size'] == dq['matrix_size'] for k in ('H3(0)', 'H4(0)', 'H4(1/8)'))
    h7 = [k for k in d if k.startswith('H7(')]
    ok = ok and len(h7) == 5 and all(len(d[k]) == 3 and all(t['matrix_argument'] == dq['H7_matrix_argument'] and
                                                              t['Jack_alpha'] == 2 for t in d[k]) for k in h7)
    rep.check(f'{label}: parameter dictionary = rt:Q3, rt:P4blocks; H_7 as three functions at -I_2', ok,
              'H3(0): 3F2; H4(0): 4F3; H4(1/8): 5F4; H7 at 5 nodes x 3 terms', dq['eq'], 'exact', src)


def period_checks(rep, label, rec, q):
    v = rec['values']
    for key, name in [('Q3', 'Q_3'), ('P4_3', 'P_4(3)'), ('P5_3', 'P_5(3)')]:
        val = real(v[key])
        ok, tol = agrees_to_shown(val, q['periods'][key])
        rep.check(f'{label}: {name} at 100 working digits = note value', ok and parse_num(v[key]).imag == 0,
                  short(val, 36), q['periods'][key], f'{short(tol, 1)} (one unit in the last shown digit)',
                  f'{label}: fresh_primitive_values.json')


def main(argv=None):
    mp.mp.dps = 110
    a = common_args(argv, '../../results/closed_forms_3')
    tier = a.tier
    q = load(a.results / 'd3_specialization_quoted.json')
    rep = Report(f'Replay of lri_d3_matrix_update (tier {tier})', a.work)
    ver = PKG / 'verification'

    rep.guard('bundle checksums', lambda: check_bundle_sums(rep))
    work = make_work(a.work)
    logs = a.work / 'logs'

    if tier == 'search':
        ok, _ = run(rep, 'scalar_catalog_search.py', [py(), 'code/scalar_catalog_search.py'], work, logs)
        if ok:
            new, old = load(work / 'verification/scalar_catalog_search.json'), load(ver / 'scalar_catalog_search.json')
            rep.check('rerun catalogue search: same count, no target-bearing relation', new['count'] == old['count'] ==
                      6479 and new['matches'] == old['matches'] == [], f"{new['count']} entries, {len(new['matches'])} matches",
                      '6479 entries, 0 matches (package README)', 'exact; a finite search, not an independence proof',
                      'verification/scalar_catalog_search.json')
        return rep.write()

    rep.guard('shipped rank-two record', lambda: rank_two_checks(rep, 'shipped', load(ver / 'rank_two_checks.json'), q))
    rep.guard('shipped 100-digit values', lambda: period_checks(rep, 'shipped', load(ver / 'fresh_primitive_values.json'), q))

    out = work / 'verification/rank_two_checks_rerun.json'
    ok, _ = run(rep, 'rank_two_checks.py', [py(), 'code/rank_two_checks.py', 'verification/rank_two_checks_rerun.json'],
                work, logs)
    if ok:
        new, old = load(out), load(ver / 'rank_two_checks.json')
        exact_keys = [k for k in old if k not in ('elapsed_seconds', 'interior_checks')]
        same = all(new.get(k) == old[k] for k in exact_keys)
        rep.check('rerun rank_two_checks.json: exact fields identical to the shipped record', same,
                  'equal' if same else 'differs', 'verification/rank_two_checks.json', 'exact', 'rerun')

        def interior():
            d, n = max_leaf_difference(new['interior_checks'], old['interior_checks'])
            rep.check('rerun rank_two_checks.json: interior partial sums equal the shipped record',
                      d is not None and d < mp.mpf('1e-85'), f'max |diff| {short(d, 3)} over {n} numbers',
                      'verification/rank_two_checks.json', '1e-85 (90 working digits; observed bitwise equal)', 'rerun')
        rep.guard('rerun interior', interior)
        rep.guard('rerun rank-two record', lambda: rank_two_checks(rep, 'rerun', new, q))

    if tier == 'replay':
        ok, _ = run(rep, 'recompute_d3_periods.py', [py(), 'code/recompute_d3_periods.py'], work, logs)
        if ok:
            new = load(work / 'verification/fresh_primitive_values_rerun.json')
            old = load(ver / 'fresh_primitive_values.json')

            def cmp():
                d, n = max_leaf_difference(new['values'], old['values'])
                rep.check('rerun fresh_primitive_values: all values equal the shipped record',
                          d is not None and d < mp.mpf('1e-90'), f'max |diff| {short(d, 3)} over {n} numbers',
                          'verification/fresh_primitive_values.json',
                          '1e-90 (100 working digits; observed bitwise equal)', 'rerun')
            rep.guard('compare 100-digit values', cmp)
            rep.guard('rerun 100-digit values', lambda: period_checks(rep, 'rerun', new, q))
    else:
        rep.add('recompute_d3_periods.py rerun', 'SKIP', 'tier test', '', '', 'run make -f public.mk replay')
    return rep.write()


if __name__ == '__main__':
    sys.exit(main())
