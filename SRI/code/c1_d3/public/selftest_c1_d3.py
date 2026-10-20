#!/usr/bin/env python3
"""Fast test of c1_d3 (new tool, 2026-10-15). Run from code/c1_d3/:  python3 public/selftest_c1_d3.py [--work DIR]

1. public/SNAPSHOT.sha256 (the dated snapshot of the shipped production files) and the authors' delivery list
   SHA256SUMS (subset mode: public/NOT_SHIPPED.txt; a file passes if it equals its pin, the re-pinned sha256 of
   RE-PINNED.json if the package has one, or is listed in public/SCRUBBED.txt, written by the repository's scrub).
2. In a copy under <work>/test/run: the package's smoke profile, code/workflow/reproduce.py smoke --from-scratch
   (block recurrences, the retained 60-primary functional and its closed-form block checks); a0, b0 and
   C1 = a0/b0 must equal outputs/reference/precision/analysis_results.json within 5e-10 (the package's own tolerance).
3. In the same copy: code/workflow/check_revision_guards.py (the ratio guards under python -O, an isolated smoke run,
   a partial run reported cleanly as incomplete); exit 0.
About 1 min on one core.
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c1d3_common as C  # noqa: E402
L = C.L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=str(C.PKG/'.work'))
    a = ap.parse_args()
    work = Path(a.work).resolve()/'test'
    T = L.Table('c1_d3 test')
    C.check_snapshot(T)
    C.check_delivery_list(T)
    run = C.work_copy(work/'run')
    out = run/'outputs'/'smoke_test'
    rc, log, dt = C.run(['code/workflow/reproduce.py', 'smoke', '--from-scratch', '--output', out], run, work/'tmp',
                        work/'smoke.log')
    T.check('smoke profile', rc == 0, 'exit %d, %.0f s' % (rc, dt), 'exit 0', 'verbatim reproduce.py smoke --from-scratch')
    ref = json.loads((C.PKG/'outputs/reference/precision/analysis_results.json').read_text())['central']
    if rc == 0:
        got = json.loads((out/'precision/diagnostics_results.json').read_text())['central']
        for k, name in (('a', 'a0'), ('b', 'b0'), ('C1', 'C1')):
            d = abs(got[k] - ref[k])
            T.check('retained ' + name, d <= 5e-10, '%.15g (|diff| %.1e)' % (got[k], d), '%.15g' % ref[k],
                    'smoke rerun vs outputs/reference/precision/analysis_results.json, 5e-10')
        diag =json.loads((out/'precision/diagnostics_results.json').read_text()).get('validation', {})
        T.check('block closed-form checks', bool(diag) and max(diag.values()) < 1e-12,
                ', '.join('%s %.1e' % kv for kv in diag.items()), '< 1e-12',
                'radial blocks vs the diagonal 3F2 form and the independent z-series (run_diagnostics.py)')
    rc, log, dt = C.run(['code/workflow/check_revision_guards.py'], run, work/'tmp', work/'guards.log')
    T.check('revision guards', rc == 0, 'exit %d, %.0f s' % (rc, dt), 'exit 0',
            'verbatim check_revision_guards.py in the copy (python -O ratio guards, isolated smoke, partial-run report)')
    return T.report(work/'test_c1_d3.txt')


if __name__ == '__main__':
    sys.exit(main())
