#!/usr/bin/env python3
"""Sensitivity replay of c_1 in d = 3 (new tool, 2026-10-15). Run from code/c1_d3/:
    python3 public/replay_full_c1_d3.py [--work DIR] [--skip-boxes]

Reruns, with the package's verbatim scripts in a copy under <work>/replay_full/run, the review-revision diagnostics
that qualify the working range (not quoted numbers of the paper; the note and SRI/docs/c1_d3/REVIEWS.md cite them):
1. code/workflow/review_diagnostics.py on the shipped full run: the nominal LP excludes the central inputs (68 violated
   sigma^4 rows; minimum max-norm displacement 0.5735 box units = 1.147 quoted errors).
2. code/workflow/review_stress.py gaps: 11 gap/padding scenarios (ten updates each, reference level-40 basis); every
   status and envelope compared with the shipped outputs/review_validation/gaps/summary.json.
3. code/workflow/review_stress.py boxes: 8 rescaled input-error boxes (m = 0.5 .. 3; m <= 0.6 infeasible), with the
   input derivatives, denominator box and level-40 basis regenerated; compared with .../boxes/summary.json.
4. code/workflow/make_review_tables.py: the three sensitivity tables, compared with outputs/tables/review_*.csv.
About 25 min on one core (gaps 10 min, boxes 15 min).
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c1d3_common as C  # noqa: E402
L = C.L
ATOL = 2e-8        # the package's tolerance for envelope endpoints (verify.py)


def jl(p):
    return json.loads(Path(p).read_text())


def compare_cases(T, mode, shipped, rerun):
    a, b = jl(shipped)['cases'], jl(rerun)['cases']
    key = lambda c: (float(c['even_gap']), float(c['odd_gap']), float(c['padding']), float(c['multiplier']))
    A, B = {key(c): c for c in a}, {key(c): c for c in b}
    bad, worst = [], 0.0
    for k, c in A.items():
        d = B.get(k)
        if d is None or d['status'] != c['status']:
            bad.append('%s: %s -> %s' % (k, c['status'], d and d['status'])); continue
        if c['status'] == 'completed':
            e = max(abs(x - y) for x, y in zip(c['interval'], d['interval']))
            worst = max(worst, e)
            if e > ATOL:
                bad.append('%s: |diff| %.1e' % (k, e))
    stat = {}
    for c in b:
        stat[c['status']] = stat.get(c['status'], 0) + 1
    T.check('%s scenarios' % mode, len(A) == len(B) and not bad,
            '%d cases (%s); largest endpoint |diff| %.1e%s' % (len(B), ', '.join('%d %s' % (v, k) for k, v in sorted(stat.items())),
                                                               worst, '; differ: %s' % bad[:3] if bad else ''),
            'same status; endpoints within %g' % ATOL, 'review_stress.py %s vs shipped outputs/review_validation/%s/summary.json' % (mode, mode))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=str(C.PKG/'.work'))
    ap.add_argument('--skip-boxes', action='store_true')
    a = ap.parse_args()
    work = Path(a.work).resolve()/'replay_full'
    T = L.Table('c1_d3 replay-full')
    run = C.work_copy(work/'run')
    rv = C.PKG/'outputs'/'review_validation'

    out = work/'fixed_lp_diagnostics.json'
    rc, log, dt = C.run(['code/workflow/review_diagnostics.py', '--results', run/'outputs/reproduced', '--output', out],
                        run, work/'tmp', work/'review_diagnostics.log')
    T.check('review_diagnostics.py', rc == 0, 'exit %d, %.0f s' % (rc, dt), 'exit 0', 'verbatim, on the shipped full run (copy)')
    if rc == 0:
        s, r = jl(rv/'fixed_lp_diagnostics.json'), jl(out)
        T.check('central inputs infeasible in the nominal LP', r['central_violated_rows'] == s['central_violated_rows'] == 68
                and r['violations_by_correlator'] == s['violations_by_correlator'] and r['violating_row_indices'] == s['violating_row_indices'],
                '%d rows %s' % (r['central_violated_rows'], r['violations_by_correlator']), '68 rows, all sigma^4',
                'fixed nominal LP at the central input vector')
        d = abs(r['min_fixed_LP_maxnorm'] - s['min_fixed_LP_maxnorm'])
        T.check('minimum displacement', d <= 1e-8, '%.10f box units (|diff| %.1e)' % (r['min_fixed_LP_maxnorm'], d),
                '%.10f' % s['min_fixed_LP_maxnorm'], 'minimax LP (HiGHS, tolerances 1e-9); 1e-8')
        ok, how, bad = L.compare_json(rv/'fixed_lp_diagnostics.json', out, atol=1e-8, rtol=1e-8, ignore_keys=('witness',))
        T.check('fixed_lp_diagnostics.json', ok, how, 'atol/rtol 1e-8 (witness not compared: not unique)', 'rerun vs shipped')

    modes = ['gaps'] + ([] if a.skip_boxes else ['boxes'])
    for mode in modes:
        rc, log, dt = C.run(['code/workflow/review_stress.py', mode, '--iterations', 10], run, work/'tmp', work/('review_stress_%s.log' % mode))
        T.check('review_stress.py %s' % mode, rc == 0, 'exit %d, %.0f s' % (rc, dt), 'exit 0', 'verbatim, in the copy')
        if rc == 0:
            compare_cases(T, mode, rv/mode/'summary.json', run/'outputs/review_validation'/mode/'summary.json')
    if not a.skip_boxes:
        rc, log, dt = C.run(['code/workflow/make_review_tables.py'], run, work/'tmp', work/'make_review_tables.log')
        T.check('make_review_tables.py', rc == 0, 'exit %d' % rc, 'exit 0', 'verbatim, on the rerun summaries (note not updated)')
        if rc == 0:
            bad = []
            for t in ('review_box_sensitivity.csv', 'review_gap_sensitivity.csv', 'review_padding_sensitivity.csv'):
                ok, how, b = L.compare_csv(C.PKG/'outputs/tables'/t, run/'outputs/tables'/t, atol=ATOL, rtol=0)
                if not ok:
                    bad.append('%s: %s' % (t, how))
            T.check('sensitivity tables', not bad, '3 tables' + ('; differ: %s' % bad if bad else ', all within tolerance'),
                    'endpoints within %g' % ATOL, 'outputs/tables/review_*_sensitivity.csv rebuilt from the rerun')
    else:
        T.add('boxes scenarios', 'SKIP', '--skip-boxes', '', 'box scan not run')
    return T.report(work/'replay_full_c1_d3.txt')


if __name__ == '__main__':
    sys.exit(main())
