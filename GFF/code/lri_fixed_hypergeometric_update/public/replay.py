#!/usr/bin/env python3
"""Public replay of lri_fixed_hypergeometric_update (written for the public edition, 2026-10-13).

  --mode test    checksum manifest; exact Barnes-kernel identity of Section 10; the d = 1 closed forms of
                 Section 1.1 at 70 digits (C2..C5, K, L, P4, P5 from literal mpmath calls); the original
                 verifier at its minimum 40 digits (~3 s)
  --mode replay  test + the original verifier at the recorded 100 digits with its 125-digit control,
                 compared field by field with verification/fixed_hypergeometric_checks.json (~6 s)

The original verifier runs unchanged in a fresh copy of the package under .work/pkg. PASS/FAIL table:
stdout and .work/VERIFY_<mode>.md; exit status 1 on any FAIL.
"""
import argparse
import sys
from pathlib import Path

import mpmath as mp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replaylib import (PKG, QUOTED_DEFAULT, Table, check_manifest, check_quoted, fresh_copy, load,  # noqa: E402
                       quoted_table, record_row, run)

HERE = Path(__file__).resolve().parent
NOT_EXPORTED = ['additions/', 'changes.diff', 'changes_fixed_hypergeometric.diff', 'code/evaluate_P5_further.py',
                'code/evaluate_P5_meijer.py', 'code/P5FixedHypergeometric.wl', 'code/P5Hypergeometric.wl',
                'code/verify_hypergeometric.py', 'conversation_progress.md', 'fixed_hypergeometric_main.tex',
                'fixed_hypergeometric_proof.tex', 'history/', 'hypergeometric_additions.tex',
                'long_range_ising_complete.pdf', 'long_range_ising_complete.tex', 'previous/']
NOT_EXPORTED_VERIFICATION = 'verification/'          # everything there except the principal record
RECORD = PKG / 'verification' / 'fixed_hypergeometric_checks.json'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mode', choices=['test', 'replay'], default='replay')
    ap.add_argument('--work', type=Path, default=PKG / '.work')
    ap.add_argument('--quoted', type=Path, default=QUOTED_DEFAULT)
    a = ap.parse_args()
    work = a.work.resolve()
    T = Table(f'lri_fixed_hypergeometric_update: make {a.mode}')
    q = quoted_table(a.quoted)
    W = fresh_copy(work)
    logs = work / 'logs'

    shipped_verification = {'verification/fixed_hypergeometric_checks.json'}
    manifest_paths = [r['path'] for r in load(PKG / 'sha256_manifest.json')]
    skip = NOT_EXPORTED + [p for p in manifest_paths
                           if p.startswith(NOT_EXPORTED_VERIFICATION) and p not in shipped_verification]
    check_manifest(T, 'sha256_manifest.json', skip)

    out = work / 'kernel_identity.json'
    ok, _ = run(T, 'public/kernel_identity.py', [HERE / 'kernel_identity.py', out], W, logs, [out])
    k = load(out) if out.exists() else {'exact': False, 'difference': 'not run'}
    T.add('Section 10 Barnes kernel R(s) = S(s) - 16 sqrt2 csc[pi(s-1/4)] (eq. fp:eq:kernel), SymPy',
          k['exact'] is True, f"difference {k['difference']}", '0', 'exact, u = tan(pi s/2)')

    out = work / 'sec11_closed_forms.json'
    run(T, 'public/sec11_closed_forms.py', [HERE / 'sec11_closed_forms.py', out, '--digits', '70'], W, logs, [out])
    s = load(out)
    for i in (2, 3, 4):
        check_quoted(T, q, f'C{i}_1', s[f'C{i}'], f'C{i}(1) from the Section 1.1 formula', '(70 digits)')
    for qid in ('C5_1_table', 'C5_1_sec14', 'C5_1_sec20', 'C5_1_sec20_short', 'C5_1_sec27'):
        check_quoted(T, q, qid, s['C5'], 'C5(1) from the Section 1.1 formula with the five-value P5', '(70 digits)')
    check_quoted(T, q, 'K', s['K'], 'K, Section 4 polygamma reduction', '(70 digits)')
    check_quoted(T, q, 'P4', s['P4'], 'P4 = 13 B- - 3 B+, mpmath 4F3(1)', '(70 digits)')
    check_quoted(T, q, 'P5', s['P5'], 'P5, five fixed hypergeometric values', '(70 digits)')
    T.add('Y_2: 9F8(-1) form equals the 8F7(-1) of eq. P5FixedY2', abs(mp.mpf(s['Y2_9F8_minus_8F7'])) <= 1e-60,
          s['Y2_9F8_minus_8F7'], '0', '|d| <= 1e-60 (70 digits)')
    T.add('Section 4 unreduced C5 (with K, L reductions) equals the Section 1.1 form',
          abs(mp.mpf(s['C5_sec4_full_minus_sec11'])) <= 1e-60, s['C5_sec4_full_minus_sec11'], '0', '|d| <= 1e-60')
    T.add('quarter-argument dictionary: A, pi, 16G, -112 zeta(3)',
          all(abs(mp.mpf(v)) <= 1e-60 for v in s['dictionary_residuals'].values()),
          ', '.join(mp.nstr(mp.mpf(v), 3) for v in s['dictionary_residuals'].values()), '0', '|d| <= 1e-60')
    rec = load(RECORD)
    T.add('P5 (Section 1.1 evaluation) vs shipped 100-digit record', abs(mp.mpf(s['P5']) - mp.mpf(rec['P5_frozen'])) <= 1e-60,
          s['P5'][:40] + '...', rec['P5_frozen'][:40] + '...', '|d| <= 1e-60')

    if a.mode == 'test':
        out = work / 'fixed_40.json'
        run(T, 'verify_fixed_hypergeometric --digits 40', ['code/verify_fixed_hypergeometric.py', '--digits', '40',
                                                          '--output', out], W, logs, [out])
        f = load(out)
        T.add('40-digit run: Gamma quadrature minus five-value P5', abs(mp.mpf(f['gamma_minus_frozen'])) <= 1e-35,
              f['gamma_minus_frozen'], '0', '|d| <= 1e-35')
        check_quoted(T, q, 'P5', f['P5_frozen'][:36], 'P5 at 40 digits (first 35 digits)')
    else:
        out = work / 'fixed_hypergeometric_checks.json'
        run(T, 'verify_fixed_hypergeometric --digits 100', ['code/verify_fixed_hypergeometric.py', '--digits', '100',
                                                           '--output', out], W, logs, [out])
        f = record_row(T, 'fixed_hypergeometric_checks (100 + 125 digits)', out, RECORD, 1e-85,
                       ('elapsed_seconds', 'mpmath_version'))
        T.add('mpmath version of the run vs the record', True, f['mpmath_version'], rec['mpmath_version'],
              'information only')
        check_quoted(T, q, 'P5', f['P5_frozen'], 'P5, five-value form (100 digits)')
        check_quoted(T, q, 'P5', f['P5_gamma'], 'P5, positive Gamma quadrature (100 digits)')
        check_quoted(T, q, 'P5_gamma_minus_fixed_125', f['higher_precision_control']['gamma_minus_frozen'],
                     'Gamma integral minus five-value P5 at 125 digits')
        check_quoted(T, q, 'R_P5_gamma_minus_fixed_125', f['higher_precision_control']['gamma_minus_frozen'])
        check_quoted(T, q, 'R_P5_gamma_minus_fixed_100', f['gamma_minus_frozen'], 'Gamma integral minus five-value P5 at 100 digits')
        T.add('three-G Meijer combination, sixth-grid alternative, trigonometric identity at 5 points',
              abs(mp.mpf(f['three_G_combination_minus_frozen'])) <= 1e-90
              and abs(mp.mpf(f['alternative_sixth_grid_minus_eighth_grid'])) <= 1e-90
              and all(abs(mp.mpf(t['absolute_residual'])) <= 1e-90 for t in f['trigonometric_identity_checks'])
              and all(f['exact_symbolic_checks'].values()),
              f"{mp.nstr(mp.mpf(f['three_G_combination_minus_frozen']), 3)}, "
              f"{mp.nstr(mp.mpf(f['alternative_sixth_grid_minus_eighth_grid']), 3)}, max trig "
              f"{mp.nstr(max(abs(mp.mpf(t['absolute_residual'])) for t in f['trigonometric_identity_checks']), 3)}",
              '0', '|d| <= 1e-90 at 100 digits; symbolic checks exact')

    sys.exit(T.finish(work / f'VERIFY_{a.mode}.md'))


if __name__ == '__main__':
    main()
