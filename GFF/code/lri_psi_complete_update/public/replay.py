#!/usr/bin/env python3
"""Public replay of lri_psi_complete_update (written for the public edition, 2026-10-13).

  --mode test    file hashes against the bundle manifest; exact SymPy certificate of the K proof and of the C0-C5 rewritings, 70-digit coefficient
                 values (C2..C5 at d = 1, K, P4, P5), 130-digit complex bilinear test (~2 s)
  --mode replay  test + the 110-digit endpoint-subtracted original master for K and the 75-digit
                 finite-parameter tests (~15 s)

Every original script runs unchanged in a fresh copy of the package under .work/pkg (they write their
records in place). PASS/FAIL table: stdout and .work/VERIFY_<mode>.md; exit status 1 on any FAIL.
Note: coefficient_values.py reuses the 240-digit 4F3(1) values in verification/wheel_inputs.json for P4
(the lri_numerical_resolution replay and lri_fixed_hypergeometric_update/public/sec11_closed_forms.py
recompute them); its P5 is a fresh Gamma quadrature.
"""
import argparse
import sys
from pathlib import Path

import mpmath as mp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replaylib import (PKG, QUOTED_DEFAULT, Table, as_num, check_quoted, check_sha256_list, fresh_copy,  # noqa: E402
                       quoted_table, record_row, run)

V = PKG / 'verification'
NOT_EXPORTED = ['long_range_ising_complete.tex', 'long_range_ising_complete.pdf', 'previous/', 'additions/',
                'source_diff.patch', 'update_note.py', 'CoefficientsPsi.wl', 'verification/pdf_checks.json',
                'verification/preservation_checks.json']


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mode', choices=['test', 'replay'], default='replay')
    ap.add_argument('--work', type=Path, default=PKG / '.work')
    ap.add_argument('--quoted', type=Path, default=QUOTED_DEFAULT)
    a = ap.parse_args()
    work = a.work.resolve()
    T = Table(f'lri_psi_complete_update: make {a.mode}')
    q = quoted_table(a.quoted)
    W = fresh_copy(work)
    WV, logs = W / 'verification', work / 'logs'

    check_sha256_list(T, Path(__file__).resolve().parent / 'bundle_sha256.txt', NOT_EXPORTED)

    run(T, 'symbolic_checks', ['verification/symbolic_checks.py'], W, logs, [WV / 'symbolic_checks.json'])
    s = record_row(T, 'symbolic_checks', WV / 'symbolic_checks.json', V / 'symbolic_checks.json', 0, ())
    T.add('K proof certificate, K and C0..C5 rewritings, reflected vs sparse bases (exact SymPy)',
          s['all_passed'] is True and all(s['checks'].values()), f"{sum(s['checks'].values())}/{len(s['checks'])} true",
          'all true', 'exact')

    run(T, 'coefficient_values', ['verification/coefficient_values.py'], W, logs, [WV / 'coefficient_values.json'])
    c = record_row(T, 'coefficient_values (70 digits)', WV / 'coefficient_values.json', V / 'coefficient_values.json', 1e-55)
    for i in (2, 3, 4):
        check_quoted(T, q, f'C{i}_1', c['C_psi'][f'C{i}'], f'C{i}(1), reflected-quarter form')
    for qid in ('C5_1_table', 'C5_1_sec14', 'C5_1_sec20', 'C5_1_sec20_short', 'C5_1_sec27', 'R_C5_psi'):
        check_quoted(T, q, qid, c['C_psi']['C5'], 'C5(1), reflected-quarter form')
    check_quoted(T, q, 'K', c['Kappa'], 'K = [psi1(1/4)(3psi1(1/4)-psi1(3/4)) + A psi2(1/4)]/2')
    check_quoted(T, q, 'P4', c['P4'], 'P4 = 13 B- - 3 B+ (240-digit 4F3 inputs reused)')
    check_quoted(T, q, 'P5', c['P5_fresh_gamma_moment'], 'P5, fresh Gamma moment at 70 digits')
    mx = max(abs(mp.mpf(v)) for v in c['original_minus_psi'].values())
    check_quoted(T, q, 'R_C0C5_max_resid', mx, 'largest original-minus-psi residual over C0..C5')

    run(T, 'complex_check', ['verification/complex_check.py'], W, logs, [WV / 'complex_bilinear_130.json'])
    cx = record_row(T, 'complex_check (130 digits)', WV / 'complex_bilinear_130.json', V / 'complex_bilinear_130.json', 1e-90)
    check_quoted(T, q, 'R_complex_130', abs(as_num(cx['residual'])), 'complex bilinear residual at t = 0.12+0.07i, 130 digits')

    if a.mode == 'replay':
        run(T, 'numerical_checks', ['verification/numerical_checks.py'], W, logs, [WV / 'numerical_checks.json'])
        n = record_row(T, 'numerical_checks (110/75/50 digits)', WV / 'numerical_checks.json', V / 'numerical_checks.json', 1e-45)
        check_quoted(T, q, 'K', n['Kappa_endpoint'], 'K from the endpoint-subtracted original master (110 digits)')
        check_quoted(T, q, 'R_K_endpoint_resid', n['Kappa_endpoint_minus_psi'], 'endpoint master minus polygamma value')
        check_quoted(T, q, 'R_bilinear_50', n['mpmath_direct_bilinear']['residual'], 'direct mpmath bilinear residual, 50 digits')
        T.add('elementary u and sigma integral coefficients (110 digits)',
              abs(mp.mpf(n['lower_u_residual'])) < 1e-100 and abs(mp.mpf(n['lower_sigma_residual'])) < 1e-100,
              f"{mp.nstr(mp.mpf(n['lower_u_residual']), 3)}, {mp.nstr(mp.mpf(n['lower_sigma_residual']), 3)}", '0', '< 1e-100')

    sys.exit(T.finish(work / f'VERIFY_{a.mode}.md'))


if __name__ == '__main__':
    main()
