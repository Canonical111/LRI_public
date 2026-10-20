#!/usr/bin/env python3
"""Replay (and test) of lri_general_periodization_update: finite periodization of the primitive sector and the d=2
factorization of P4(2), P5(2) into the d=1 hypergeometric values (note Sections 15.1-15.5).

Run from the package folder (GFF/code/lri_general_periodization_update) as `make -f public.mk replay` or
`make -f public.mk test` (= replay plus --full). Nothing shipped is modified: the delivered scripts write their records in
place (into verification/general_periodization/), so they run in a fresh copy of the package under public/out/work/.

replay (about 10 s, one core):
  1. integrity: public/SOURCE_SHA256SUMS (the 24 shipped source files, hashes from the bundle MANIFEST.json; complete) and
     archive_manifest.json (all 205 files of the delivered package; ignore-missing: 182 of them are not shipped, being
     byte-identical copies of the closed and special-functions exports, history, or note snapshots).
  2. reruns check_exact_algebra.py (SymPy), the d=2 chain check_two_dimensional.py (55 digits) -> check_d2_control.py
     (70 digits, other tails and grid) -> check_d2_inherited_periods.py (60 digits, literal mpmath.hyper of the d=1 values;
     each script reads the previous record), horn_templates.py and check_horn_templates.py, and compares with the delivered
     records.
  3. recomputes the numbers the note and the paper quote from this package (expected.json 'values': P4(2), P5(2), the B7
     vector) and cross-checks the d=2 closed forms owned by closed_forms_2 (C4(2), C5(2), L2) with these P4(2), P5(2).
test (--full, about 1 min): additionally check_wheel_periodization.py (35-digit Barnes integrals) and
  check_p5_periodization.py (double-precision Gamma-ratio sampling against spectral quadrature).

Tolerances. SymPy and mpmath outputs are deterministic: compared exactly after dropping timing keys. numpy outputs
(p5_periodization.json): values relative 1e-8, differences and residuals absolute 1e-6 (they are differences of
double-precision quadratures, about 1e-9 to 1e-7 in size). Quoted numbers at the printed digits (P4(2) to 50 digits).
Cross-checks of the closed forms: rounded to the printed digits of their owners' values.
Checked: the delivered records (made on Linux with Python 3.13.5, numpy 2.3.5, scipy 1.17.0, sympy 1.14.0,
mpmath 1.3.0) were reproduced on macOS arm64 with Python 3.10.12, numpy 1.24.4, scipy 1.11.1, sympy 1.12,
mpmath 1.3.0 (gmpy2 backend), and the replay also with Python 3.10.11, numpy 1.23.5, scipy 1.10.0, sympy 1.11.1,
mpmath 1.2.1: all exact-tier records identical; float tier within 1.9e-10 relative and 4.5e-8 absolute.
"""
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (PKG, row, load, verify_sums, verify_hashes, work_copy, run, cmp_exact, cmp_float, quoted, close,
                    report)  # noqa: E402

GP = 'code/general_periodization'
VR = 'verification/general_periodization'
REC = PKG / VR


def replay(work, exp):
    verify_sums(PKG / 'public/SOURCE_SHA256SUMS')
    am = load(PKG / 'archive_manifest.json')
    verify_hashes('archive_manifest.json', {r['path']: r['sha256'] for r in am['files']}, PKG, ignore_missing=True)

    for s, outs in (('check_exact_algebra.py', ['exact_algebra.json']), ('check_two_dimensional.py', ['d2_factorization.json']),
                    ('check_d2_control.py', ['d2_control.json']), ('check_d2_inherited_periods.py', ['d2_inherited_periods.json']),
                    ('horn_templates.py', ['arrays/primitive_r3.json', 'arrays/primitive_r4.json', 'arrays/primitive_r7.json']),
                    ('check_horn_templates.py', ['horn_template_checks.json'])):
        run(work, f'{GP}/{s}', outputs=[f'{VR}/{o}' for o in outs])
        for o in outs: cmp_exact(f'{o}: recomputed = delivered', work / VR / o, REC / o)

    # --- quoted numbers
    d2, ea = load(REC / 'd2_inherited_periods.json'), load(REC / 'exact_algebra.json')
    for v in exp['values']:
        if v['package'] != PKG.name: continue
        if v['id'].startswith('P4(2)'): quoted(f'{v["id"]} ({v["note"] or v["paper"]})', d2['P4'], v['printed'], f'owner {v["owner"]}')
        elif v['id'].startswith('P5(2)'): quoted(f'{v["id"]} ({v["paper"]})', d2['P5'], v['printed'], f'owner {v["owner"]}')
        elif v['id'].startswith('B7'):
            want = [int(x) for x in v['printed'].split(',')]
            got = [int(x) for x in ea['B7_over_pi6']]
            row(f'{v["id"]} / pi^6 ({v["note"]})', got, want, got == want, f'owner {v["owner"]}')
    close('P4(2): quadratic in B-, B+ minus the independent 70-digit d=2 value', d2['P4_difference'], 0, 1e-55,
          note='package README: about 6e-59')
    close('P5(2): quadratic in the five Y values minus the independent 70-digit d=2 value', d2['P5_difference'], 0, 1e-55,
          note='package README: about 2e-58')
    for k in ('quadratic_basis_change_exact_zero',):
        row(f'd2_inherited_periods {k}', d2[k], True, d2[k] is True)
    for k in ('C5_nonprimitive_collection_zero', 'P4_elliptic_normalization_zero', 'P5_square_residue_zero'):
        row(f'exact_algebra {k}', ea[k], True, ea[k] is True)
    row('exact_algebra B4 / pi^3 at q=1/2', ea['B4_over_pi3'], ['0', '-4', '0', '-20'], ea['B4_over_pi3'] == ['0', '-4', '0', '-20'])

    # --- cross-checks: the d=2 closed forms (owned by closed_forms_2) evaluated with this package's P4(2), P5(2)
    import mpmath as mp
    mp.mp.dps = 60
    X = {c['id']: c for c in exp['cross_checks']}
    P4, P5 = mp.mpf(d2['P4']), mp.mpf(d2['P5'])
    a, G, z3 = mp.log(2), mp.catalan, mp.zeta(3)
    Q2 = mp.gamma(mp.mpf(1) / 4) ** 8 / (24 * mp.pi ** 4)
    C4 = (16 * P4 - 64 * a ** 3 - 32 * a * Q2 - 359 * z3) / 648
    C5 = (-32 * P5 + 56 * a * P4 - 36 * Q2 ** 2 + (240 * a ** 2 + 596 * G) * Q2 - 1024 * G ** 2 + 449 * z3 * a - 80 * a ** 4) / 972
    quoted(f'cross-check C4(2) closed form (gc:d2coefficients) with this P4(2) (owner {X["C4(2) closed form"]["owner"]})',
           mp.nstr(C4, 50), X['C4(2) closed form']['value'], X['C4(2) closed form']['source'])
    quoted(f'cross-check C5(2) closed form (gc:C5twoClosed) with this P4(2), P5(2) (owner {X["C5(2) closed form"]["owner"]})',
           mp.nstr(C5, 50), X['C5(2) closed form']['value'], X['C5(2) closed form']['source'])
    quoted(f'cross-check L2 = -2 log2 P4(2) (gc:L2closed; owner {X["L2"]["owner"]})', mp.nstr(-2 * a * P4, 55),
           X['L2']['value'], X['L2']['source'])


def full(work):
    for s, o, tier in (('check_wheel_periodization.py', 'wheel_periodization.json', cmp_exact),
                       ('check_p5_periodization.py', 'p5_periodization.json', cmp_float)):
        run(work, f'{GP}/{s}', outputs=[f'{VR}/{o}'])
        tier(f'{o}: recomputed vs delivered ({tier.__name__[4:]})', work / VR / o, REC / o)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--expected', type=Path, default=PKG / '../../results/closed_forms_general/C0_C5/expected.json')
    ap.add_argument('--out', type=Path, default=PKG / 'public/out')
    ap.add_argument('--full', action='store_true', help='also the remaining delivered checks (test)')
    a = ap.parse_args()
    exp, out = load(a.expected), a.out.resolve()
    replay(work_copy(out / 'work/replay/pkg'), exp)
    if a.full: full(work_copy(out / 'work/full/pkg'))
    return report(out, 'test' if a.full else 'replay')


if __name__ == '__main__':
    sys.exit(main())
