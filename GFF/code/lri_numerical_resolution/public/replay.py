#!/usr/bin/env python3
"""Public replay of lri_numerical_resolution (written for the public edition, 2026-10-13).

  --mode test    exact algebra and saved-data reassembly (seconds)
  --mode replay  test + fresh 80-digit reference (K, L, P4, P5, closed-form C5), lower-loop controls,
                 graph regeneration with input hashes, sector/group audit, unlabelled class audit (~25 s)

Every original script runs unchanged in a fresh copy of the package under .work/pkg (they write their
records in place). Each regenerated record is compared with the shipped one, and every number that the
note and the package README quote is compared with C5_1_quoted.json. PASS/FAIL table: stdout and
.work/VERIFY_<mode>.md; exit status 1 on any FAIL.
"""
import argparse
import sys
from fractions import Fraction
from pathlib import Path

import mpmath as mp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replaylib import (PKG, QUOTED_DEFAULT, Table, check_manifest, check_quoted, fresh_copy, load,  # noqa: E402
                       quoted_table, record_row, run)

NOT_EXPORTED = ['long_range_ising_complete.tex', 'long_range_ising_complete.pdf', 'previous/', 'additions/',
                'source_diff.patch', 'build_note.py', 'make_readme.py', 'conversation_progress.md',
                'verification/records/logs/', 'verification/records/note_integrity.json',
                'verification/records/pdf_preflight.json', 'verification/records/clean_package_audit.json']
SHIPPED = PKG / 'verification' / 'records'
RTOL80 = 1e-55   # records written at 80 working digits (65 printed); leaves 10 digits for library changes


def case(audit, method, degree, cutoff):
    return next(c for c in audit['cases'] if c['method'] == method and c['degree'] == degree and c['cutoff'] == cutoff)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mode', choices=['test', 'replay'], default='replay')
    ap.add_argument('--work', type=Path, default=PKG / '.work')
    ap.add_argument('--quoted', type=Path, default=QUOTED_DEFAULT)
    a = ap.parse_args()
    work = a.work.resolve()
    T = Table(f'lri_numerical_resolution: make {a.mode}')
    q = quoted_table(a.quoted)
    W = fresh_copy(work)
    R, logs = W / 'verification' / 'records', work / 'logs'

    check_manifest(T, 'sha256_manifest.json', NOT_EXPORTED)

    # --- exact algebra: certificate, RG assembly, rational propagation identity
    run(T, 'symbolic_audit', ['verification/symbolic_audit.py'], W, logs, [R / 'symbolic_audit.json'])
    s = record_row(T, 'symbolic_audit', R / 'symbolic_audit.json', SHIPPED / 'symbolic_audit.json', 0, ())
    T.add('certificate b4, c4, D5 remainder and RG assembly = original C5 (exact SymPy)',
          s['all_exact'] is True and all(v == '0' for v in s['checks'].values()),
          ', '.join(f'{k}={v}' for k, v in s['checks'].items()), 'all 0', 'exact')
    check_quoted(T, q, 'classes_4loop_nonwheel', s['certificate_rows_4'], 'certificate four-loop rows')
    check_quoted(T, q, 'classes_5loop_certificate', s['certificate_rows_5'], 'certificate five-loop rows')

    run(T, 'exact_decimal_audit', ['verification/exact_decimal_audit.py'], W, logs, [R / 'exact_decimal_audit.json'])
    e = record_row(T, 'exact_decimal_audit', R / 'exact_decimal_audit.json', SHIPPED / 'exact_decimal_audit.json', 0, ())
    dH = Fraction(e[0]['dC5_dB5_simple']) / 3       # H = 3B - A: dC5/dB = 3 dC5/dH, dC5/dA = -dC5/dH
    ok = all(Fraction(x['dC5_dA5_simple']) == -dH and Fraction(x['dC5_dB5_simple']) == 3 * dH for x in e)
    check_quoted(T, q, 'graph_dC5_dH', dH if ok else None, 'exact sensitivity dC5/dH_{5,-1} (rational arithmetic)')

    # --- forward reassembly of the saved raw amplitudes with the saved reference (the bundle's c5 target)
    run(T, 'audit', ['verification/audit.py'], W, logs, [R / 'resolution_audit.json'])
    au = record_row(T, 'audit (saved reference)', R / 'resolution_audit.json', SHIPPED / 'resolution_audit.json', RTOL80)
    for deg in (22, 24):
        for cut in ('span', 'maxgap'):
            c = case(au, 'combined_simd', deg, cut)
            check_quoted(T, q, f'graph_{deg}_{cut}', c['C5'], f'graph control, degree {deg}, {cut}: C5')
            check_quoted(T, q, f'graph_{deg}_{cut}_resid', c['C5_minus_closed'], f'graph control, degree {deg}, {cut}: minus closed form')
            T.add(f'graph control degree {deg} {cut}: lower-loop degree', c['lower_degree'] == 32, c['lower_degree'],
                  q['graph_lower_degree']['quoted'], 'exact')
    dev = max(abs(mp.mpf(c['C5_minus_scalar_control'])) for c in au['cases'] if 'C5_minus_scalar_control' in c)
    check_quoted(T, q, 'graph_same_degree_full_vs_combined', dev, 'degree 18: combined-channel minus full two-channel control (max over cutoffs)')
    check_quoted(T, q, 'R_24_span', case(au, 'combined_simd', 24, 'span')['C5'])
    check_quoted(T, q, 'R_24_span_resid', case(au, 'combined_simd', 24, 'span')['C5_minus_closed'])
    check_quoted(T, q, 'R_24_maxgap', case(au, 'combined_simd', 24, 'maxgap')['C5'])
    check_quoted(T, q, 'R_24_maxgap_resid', case(au, 'combined_simd', 24, 'maxgap')['C5_minus_closed'])
    span = next(b for b in au['error_budgets'] if b['cutoff'] == 'span')
    check_quoted(T, q, 'R_old_printed_span', span['old_printed'])
    check_quoted(T, q, 'R_old_minus_closed', mp.mpf(span['old_printed']) - mp.mpf(span['reference']))
    T.add('signed error budget closes (span and maxgap)',
          all(abs(mp.mpf(b['budget_identity_residual'])) <= 1e-60 for b in au['error_budgets']),
          ', '.join(b['budget_identity_residual'] for b in au['error_budgets']), '0', '|r| <= 1e-60')
    for cut in ('span', 'maxgap'):
        check_quoted(T, q, 'R_scalar18_shift', case(au, 'scalar_extended', 18, cut)['same_degree_same_lower_precision_shift'],
                     f'degree-18 long-double control, {cut}: shift at fixed degree and lower inputs')

    if a.mode == 'replay':
        run(T, 'lower_controls', ['verification/lower_controls.py'], W, logs, [R / 'lower_controls.json'])
        record_row(T, 'lower_controls', R / 'lower_controls.json', SHIPPED / 'lower_controls.json', RTOL80)

        # fresh special-function reference at 80 digits (gamma quadrature for P5, 4F3(1) for P4, L)
        run(T, 'audit --refresh-reference', ['verification/audit.py', '--refresh-reference'], W, logs,
            [R / 'reference.json', R / 'resolution_audit.json'])
        ref = record_row(T, 'reference (recomputed)', R / 'reference.json', SHIPPED / 'reference.json', RTOL80, ())
        record_row(T, 'audit (fresh reference)', R / 'resolution_audit.json', SHIPPED / 'resolution_audit.json', RTOL80,
                   ('elapsed_seconds', 'reference_recomputed_during_this_audit'))
        T.add('certificate + RG assembly minus closed form (80 digits)', abs(mp.mpf(ref['assembly_minus_closed'])) <= 1e-70,
              ref['assembly_minus_closed'], '0', '|r| <= 1e-70')
        for qid in ('C5_1_table', 'C5_1_sec14', 'C5_1_sec20', 'C5_1_sec20_short', 'C5_1_sec27', 'R_C5_55'):
            check_quoted(T, q, qid, ref['C5'], 'C5(1) closed form', '(fresh 80-digit reference)')
        check_quoted(T, q, 'K', ref['K'], 'K (polygamma form)', '(fresh reference)')
        check_quoted(T, q, 'P4', ref['P4'], 'P4 = 13 B- - 3 B+ with mpmath 4F3(1)', '(fresh reference)')
        check_quoted(T, q, 'P5', ref['P5'], 'P5 by positive Gamma quadrature', '(fresh reference)')

        # graph inputs: regeneration, hashes, sectors and exponent groups
        run(T, 'regenerate_graph_audit', ['verification/regenerate_graph_audit.py'], W, logs, [R / 'graph_regeneration.json'])
        g = record_row(T, 'graph_regeneration', R / 'graph_regeneration.json', SHIPPED / 'graph_regeneration.json', 0)
        T.add('regenerated graph inputs match the executed-input SHA-256 hashes',
              g['regenerated_inputs_match_executed_input_hashes'] is True
              and load(W / 'verification/inputs/executed_graph_hashes.json')
              == {k: g[k] for k in ('full_graph_input_sha256', 'combined_graph_input_sha256')},
              g['full_graph_input_sha256'][:16] + '..., ' + g['combined_graph_input_sha256'][:16] + '...',
              'verification/inputs/executed_graph_hashes.json', 'sha256 exact')
        check_quoted(T, q, 'graph_ordered', g['ordered_graphs'], 'ordered graphs regenerated')
        check_quoted(T, q, 'R_nonzero_graphs', g['nonzero_combined_graphs'], 'graphs with nonzero 3w2-w4')
        run(T, 'enumeration_audit', ['verification/enumeration_audit.py'], W, logs, [R / 'enumeration_audit.json'])
        en = record_row(T, 'enumeration_audit', R / 'enumeration_audit.json', SHIPPED / 'enumeration_audit.json', 0)
        check_quoted(T, q, 'graph_zero_weight', en['zero_combined_graphs'], 'zero-weight ordered graphs')
        check_quoted(T, q, 'R_exponent_groups', en['combined_groups'], 'exponent groups of the combined channel')
        T.add('60 reversal-reduced sectors, 342 groups, no a=-2 derivative sector in the combined channel',
              (en['reversal_reduced_sectors'], en['all_groups'], en['nonzero_combined_derivative_sectors']) == (60, 342, 0),
              f"{en['reversal_reduced_sectors']}, {en['all_groups']}, {en['nonzero_combined_derivative_sectors']}",
              'README: 60, 342, 0', 'exact')

        # unlabelled classes (new public-edition check)
        out = work / 'graph_classes.json'
        run(T, 'public/graph_classes.py', [Path(__file__).resolve().parent / 'graph_classes.py', out], W, logs, [out])
        gc = load(out)
        four, five = gc['4'], gc['5']
        T.add('four loops: 27 classes = 26 certificate rows (words and RG weights exact) + the wheel',
              (four['classes'], four['certificate_rows'], four['certificate_rows_match_enumeration'],
               four['primitive_is_the_wheel'], len(four['remaining_classes'])) == (27, 26, True, True, 1),
              f"{four['classes']} classes, rows match {four['certificate_rows_match_enumeration']}, "
              f"remaining {four['primitive_words']}", '27 = 26 + 1', 'exact')
        check_quoted(T, q, 'classes_5loop', five['classes'], 'five-loop unlabelled classes')
        T.add('five-loop certificate rows: class index, edge word, omega_b, omega_c equal the enumeration',
              five['certificate_rows_match_enumeration'] is True and five['certificate_rows_with_zero_weight'] == 0,
              f"{five['certificate_rows']} rows, match {five['certificate_rows_match_enumeration']}, "
              f"zero-weight among them {five['certificate_rows_with_zero_weight']}", 'all', 'exact')
        check_quoted(T, q, 'classes_5loop_zero', five['zero_weight_classes'], 'classes with 3w2-w4 = 0')
        T.add('zero-weight classes contain exactly the 9540 zero-weight ordered graphs',
              five['zero_weight_labelled_graphs'] == int(q['graph_zero_weight']['quoted']),
              five['zero_weight_labelled_graphs'], q['graph_zero_weight']['quoted'], 'exact')
        check_quoted(T, q, 'classes_5loop_primitive', len(five['primitive_classes']),
                     f"primitive classes {five['primitive_classes']} (no proper subgraph with e = 2v-2)")
        check_quoted(T, q, 'classes_5loop_wheel', len(five['wheel_insertion_classes']), 'remaining nonprimitive classes')
        check_quoted(T, q, 'wheel_table', {k: [v[0], v[1], v[2]] for k, v in five['wheel_insertion_classes'].items()},
                     'Sec. 12 table rows (index: word, |Aut G|, d_G)')
        T.add('wheel structure: all six wheel-insertion classes, none of the 92 rows, none of the 3 primitives',
              five['wheel_insertions_have_wheel_structure'] is True and five['certificate_rows_with_wheel_structure'] == 0
              and five['primitive_classes_have_wheel_structure'] == 0,
              f"{five['wheel_insertions_have_wheel_structure']}, {five['certificate_rows_with_wheel_structure']}, "
              f"{five['primitive_classes_have_wheel_structure']}", 'True, 0, 0',
              'wheel subgraph, or a bubble whose contraction is the four-loop wheel')
        T.add('129 = 92 + 6 + 3 + 28 (disjoint)',
              five['classes'] == five['certificate_rows'] + len(five['wheel_insertion_classes'])
              + len(five['primitive_classes']) + five['zero_weight_classes'],
              f"{five['certificate_rows']} + {len(five['wheel_insertion_classes'])} + {len(five['primitive_classes'])}"
              f" + {five['zero_weight_classes']}", '129', 'exact')

    sys.exit(T.finish(work / f'VERIFY_{a.mode}.md'))


if __name__ == '__main__':
    main()
