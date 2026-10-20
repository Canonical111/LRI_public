#!/usr/bin/env python3
"""Fast test of lri_C6_d2_complete_update (`make -f public.mk test`, about 3 s): the shipped files against the package's own
SHA256SUMS.json, and three delivered checks rerun in a writable copy and compared with their published records:
fresh_two_loop_mom.py (two-loop finite-MOM jets, 65 digits), check_mom_lagrange.py (192 exact fixed-point identities) and
klt_checks.py (split-contour kite normalization). Tolerances as in replay.py."""
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import compare_json, load, report, row, run, sums_check, workcopy  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', default='../../results/C6_2/power_compensation')
    ap.add_argument('--out', default='public/out')
    a = ap.parse_args()
    R, out = Path(a.results), Path(a.out); logs = out / 'test_logs'; logs.mkdir(parents=True, exist_ok=True)
    sums_check(R)
    W = workcopy(out / 'test_work')
    for script, rec in (('fresh_two_loop_mom.py', 'fresh_two_loop_mom.json'), ('check_mom_lagrange.py', 'mom_lagrange_checks.json'),
                        ('klt_checks.py', 'klt_checks.json')):
        rc, t = run(script, W, log=logs / script.replace('.py', '.log'))
        row(f'run {script}', f'rc {rc}', 'rc 0', rc == 0, f'{t:.1f} s')
        if rc == 0: compare_json(f'{rec}: rerun vs published', load(W / rec), load(R / 'reproduction' / rec))
    return report(out, 'test')


if __name__ == '__main__':
    sys.exit(main())
