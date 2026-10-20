#!/usr/bin/env python3
"""Regeneration of the d = 2 power-sector counterterms from the classified graph inventory (note Secs 24.1-24.3).

Run from the package folder as `make -f public.mk regen` (warm: the shipped kite_cache/ supplies the 164 kite Taylor jets)
or `make -f public.mk regen-cold` (the kite jets are recomputed from the split-contour formula). In a writable copy under
public/out/regen/, the delivered scripts run in the order of the original calculation, each overwriting the record that the
next one reads, and every regenerated record is compared with the shipped one:

  1. sp_ms.py 90           Gamma-reducible graph sector, recursive MS counterterms at 90 digits      -> sp_ms_90.json
  2. sp_exact.py           the same sector in exact arithmetic (Q[log 2, zeta(2), zeta(3), zeta(5)]) -> sp_exact.json
  3. check_gamma_coverage.py  symbolic vs 90-digit, coverage                                        -> gamma_and_coverage_checks.json
  4. position_ms.py        coordinate-space Riesz/Selberg closure (compares with step 1)             -> position_ms_results.json
  5. position_kite_leaf_ms.py, KNODES/KDPS/KRAD = 32/45/.02 and 48/55/.016 (compares with step 4)
                           split-contour kite and scaleless-leaf extension; all power graphs     -> position_kite_leaf_ms_*.json
  6. power_cancellation.py [--high], audit_analytic_extension.py   (as in replay, on the regenerated counterterms)

Times on macOS (Python 3.10, mpmath 1.2.1), warm cache: steps 1-5 took 20 s, 80 s (recorded), 3 s, 30 s, 30 s + 35 s;
cold, step 5 additionally evaluates 82 kites per setting (16 or 24 contour nodes each). position_kite_leaf_ms.py uses a
4-process pool (fork). First cluster run (symmetry, AMD EPYC 7543, Python 3.12.9, mpmath 1.3.0, sympy 1.14.0, networkx 3.7): warm, every record string-identical; cold, the kite steps took
108 s (32/45) and 148 s (48/55), all 164 kite jets equal to the shipped ones, and three diagnostic fields moved at rounding
level (max_Gamma_discrepancy at loop 3 by 2.4e-59 and 2.7e-64, max_absolute_comparison by 7.0e-57 on 7.38e-30). Second
cluster run (symmetry, Intel Xeon Gold 6148, mpmath 1.3.0 without gmpy2), cold, 397 s: in addition the near-zero
counterterm combination of L5G121 (b ~ 3e-41, an exactly vanishing simple pole) moved by 6.7e-58 and 1.2e-62.
Tolerances (public/common.py): string identity first. Value fields (counterterms, Laurent coefficients, sums, jets) then
pass when |new - recorded| <= 10^-(dps - 10) x the magnitude of their record entry (largest |value| of the graph's
counterterm vector, the loop's totals, the record's top-level values); dps is the record's working precision (60 and 65
for the two kite settings, 70 position_ms, 90 sp_ms). Diagnostic fields (DIAG: route and root discrepancies,
symbolic-vs-numeric errors, Delta_p) pass within max(100 x recorded, 1e-40, the note's bound). Rows report how many fields
needed the tolerance and the largest scaled difference.
"""
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PKG, compare_json, load, report, row, run, sums_check, workcopy  # noqa: E402

NESTED = 'lri_C6_d2_two_forest_update'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', default='../../results/C6_2/power_compensation')
    ap.add_argument('--out', default='public/out')
    ap.add_argument('--cold', action='store_true', help='delete the kite cache in the copy and recompute the kite jets')
    a = ap.parse_args()
    R, out = Path(a.results), Path(a.out); logs = out / 'regen_logs'; logs.mkdir(parents=True, exist_ok=True)
    sums_check(R)
    W = workcopy(out / 'regen'); code = W / NESTED / 'analytic/code'; ver = W / NESTED / 'analytic/verification'
    S = PKG / 'reproduction'; SV = S / NESTED / 'analytic/verification'
    if a.cold:
        n = 0
        for p in (W / 'kite_cache').glob('*.json'): p.unlink(); n += 1
        row('cold start: kite cache entries removed', n, 164, n == 164)

    def step(label, script, cwd, args=(), env=None):
        rc, t = run(script, cwd, args, env=env, log=logs / (label.replace(' ', '_').replace('/', '_') + '.log'))
        row(f'run {label}', f'rc {rc}', 'rc 0', rc == 0, f'{t:.0f} s')
        return rc == 0

    if step('sp_ms.py 90', 'sp_ms.py', code, ('90',)):
        compare_json('sp_ms_90.json: regenerated vs shipped', load(ver / 'sp_ms_90.json'), load(SV / 'sp_ms_90.json'))
    if step('sp_exact.py', 'sp_exact.py', code):
        compare_json('sp_exact.json: regenerated vs shipped', load(ver / 'sp_exact.json'), load(SV / 'sp_exact.json'))
    if step('check_gamma_coverage.py', 'check_gamma_coverage.py', code):
        compare_json('gamma_and_coverage_checks.json: regenerated vs published', load(ver / 'gamma_and_coverage_checks.json'),
                     load(R / 'reproduction' / NESTED / 'analytic/verification/gamma_and_coverage_checks.json'))
    if step('position_ms.py', 'position_ms.py', W):
        compare_json('position_ms_results.json: regenerated vs shipped', load(W / 'position_ms_results.json'), load(S / 'position_ms_results.json'))
    for n, d, r in ((32, 45, '.02'), (48, 55, '.016')):
        f = f'position_kite_leaf_ms_{n}_{d}_{r}.json'
        if step(f'position_kite_leaf_ms.py {n}/{d}/{r}', 'position_kite_leaf_ms.py', W, env=dict(KNODES=str(n), KDPS=str(d), KRAD=r)):
            compare_json(f'{f}: regenerated vs shipped', load(W / f), load(S / f))
    if a.cold:
        new = {p.name: load(p) for p in (W / 'kite_cache').glob('*.json')}; bad = []
        for name, rec in new.items():
            old = S / 'kite_cache' / name
            if not old.exists() or load(old)['coefficients'] != rec['coefficients']: bad.append(name)
        row('kite cache: recomputed jets = shipped jets', f'{len(new) - len(bad)}/{len(new)}', '164/164', len(new) == 164 and not bad)
    for args, name in (((), 'power_cancellation.json'), (('--high',), 'power_cancellation_high.json')):
        if step(f'power_cancellation.py {" ".join(args)}'.strip(), 'power_cancellation.py', W, args):
            compare_json(f'{name}: from regenerated counterterms vs published', load(W / name), load(R / 'verification' / name),
                         ignore=('seconds', 'scope'))
    if step('audit_analytic_extension.py', 'audit_analytic_extension.py', W):
        compare_json('analytic_extension_audit.json: from regenerated counterterms vs published', load(W / 'analytic_extension_audit.json'),
                     load(R / 'verification/analytic_extension_audit.json'))
    return report(out, 'regen_cold' if a.cold else 'regen')


if __name__ == '__main__':
    sys.exit(main())
