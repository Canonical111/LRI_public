#!/usr/bin/env python3
"""Replay of the analytic d = 2 power-sector compensation and of the finite-scheme audits (note Secs 24.1-24.3 and 25.1-25.3).

Run from the package folder (GFF/code/lri_C6_d2_complete_update) as `make -f public.mk replay`. Nothing is integrated and no
counterterm is recomputed: the delivered scripts in reproduction/ are rerun on the saved counterterms and inputs, in a
writable copy (public/out/work/; they write next to themselves), and every output is compared field by field with the
published record. Then every number the note quotes from these records is checked at the digits it prints, and the
compensation is tied to the C6(2) and C7(2) results.

Inputs (relative to the package folder):
  reproduction/                                  delivered scripts, saved counterterms (position_kite_leaf_ms_*.json), the
                                                 classified graph inventory, the exact Gamma sector (sp_exact.json), the
                                                 two-loop reference; bound by SHA256SUMS.json
  ../../results/C6_2/power_compensation/         expected records (same relative paths as in the package; also bound by
                                                 the package's SHA256SUMS.json)
  ../../results/C6_2/C6_result.json              the C6(2) production result (optional cross-check)
  ../../results/C7_2/C7_result.json              the C7(2) production result with the explicitly integrated power sector
                                                 (optional cross-check)
  ../LRI_C6_D2_HPC/                              the C6(2) package: inputs/two_loop.json and the byte copies of the power
                                                 records in reference/ (optional cross-check)
A missing optional input gives a SKIP row, not a FAIL.

What is rerun (each a few seconds or less; about 10 s in all on macOS):
  power_cancellation.py and --high   Delta_p = C6^full - C6^power-free from the two Cauchy settings of the saved counterterms
  audit_analytic_extension.py        2699 pole coefficients of the two settings, root discrepancy, sunset contractions
  check_gamma_coverage.py            exact Gamma sector (symbolic) against its 90-digit evaluation; sector values
  klt_checks.py                      Selberg, completion and changed-tail checks of the split-contour kite formula
  fresh_two_loop_mom.py              the two-loop finite-MOM jets b_{2,j}, c_{2,j} from two fresh Cauchy contours (65 digits)
  check_mom_lagrange.py              192 exact-rational fixed-point/Lagrange checks
Records only (their reruns need files not shipped): forest_exact_checks.json (532/383 monomials) and kernel_map_checks.json
(493 kernels); these identities are also exercised by GFF/code/LRI_C7_D2_HPC, which regenerates all 492 kernels of loops 3-6.

Tolerances. The scripts are deterministic mpmath/sympy/Fraction computations at 45-90 digits. With mpmath 1.2.1 / sympy
1.11.1 / networkx 2.8.4 (Python 3.10.11) and mpmath 1.3.0 / sympy 1.12 / networkx 2.8.8 (Python 3.10.12) every regenerated
field is string-identical to the delivered record, except wall-clock `seconds` and the prose `scope` of the 32-node
power_cancellation.json (written by an earlier version of the script; ignored); so were the reruns on symmetry (Python
3.12.9, mpmath 1.3.0, sympy 1.14.0, networkx 3.7). Other versions, the pure-Python mpmath backend (no gmpy2) and the
Python hash seed may change last digits: audit_analytic_extension.py sums over a set, so its two contribution totals
differ by one unit in the 63rd digit for some PYTHONHASHSEED values. String identity is the first test. A value field that
differs passes when |new - recorded| <= 10^-(dps - 10) x the magnitude of its record entry (the largest |value| of the
graph, loop or record it belongs to), dps being the record's working precision. Diagnostic fields, which measure the
disagreement of two routes or are rounding residuals (Delta_p, root and route discrepancies, KLT errors; DIAG in
public/common.py), pass when the new value is at most max(100 x recorded, 1e-40, the note's bound: 1e-30 for Delta_p).
Rows report the values and the largest scaled difference.
Quoted numbers are compared after half-even rounding to the digits the note prints.
"""
import argparse, json, sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PKG, ROWS, compare_json, dec, load, quoted, report, row, run, sha, skip, sums_check, workcopy  # noqa: E402

NESTED = 'lri_C6_d2_two_forest_update'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', default='../../results/C6_2/power_compensation')
    ap.add_argument('--c6', default='../../results/C6_2/C6_result.json')
    ap.add_argument('--c7', default='../../results/C7_2/C7_result.json')
    ap.add_argument('--hpc', default='../LRI_C6_D2_HPC')
    ap.add_argument('--out', default='public/out')
    a = ap.parse_args()
    R, out = Path(a.results), Path(a.out); logs = out / 'logs'; logs.mkdir(parents=True, exist_ok=True)
    import mpmath as mp, sympy as sp
    mp.mp.dps = 60
    A = 4 * mp.log(2)

    # 0. integrity
    sums_check(R)
    W = workcopy(out / 'work')

    # 1. the power-sector correction, two Cauchy settings (Sec 24.3)
    for args, name in (((), 'power_cancellation.json'), (('--high',), 'power_cancellation_high.json')):
        rc, t = run('power_cancellation.py', W, args, log=logs / name.replace('.json', '.log'))
        row(f'run power_cancellation.py {" ".join(args)}'.strip(), f'rc {rc}', 'rc 0', rc == 0, f'{t:.1f} s')
        if rc == 0:
            compare_json(f'{name}: rerun vs published', load(W / name), load(R / 'verification' / name),
                         ignore=('seconds', 'scope'))
    lo, hi = load(R / 'verification/power_cancellation.json'), load(R / 'verification/power_cancellation_high.json')
    au = load(R / 'verification/power_sector_audit.json')
    row('power_sector_audit: lower power sums = high setting (L=3,4,5)', 'equal', 'equal',
        au['complete_lower_power_sums'] == {k: hi['power_sector_sums'][k] for k in ('3', '4', '5')})
    row('power_sector_audit: higher/lower parts and Delta_p = high setting', 'equal', 'equal',
        (au['higher_part'], au['lower_part'], au['computed_delta_C6']) ==
        (hi['higher_piece'], hi['lower_difference'], hi['power_contribution_C6']))
    row('power_sector_audit: two settings = the two records', 'equal', 'equal',
        au['two_settings_delta_C6'] == [lo['power_contribution_C6'], hi['power_contribution_C6']])
    s3, s4, s5 = (hi['power_sector_sums'][k] for k in ('3', '4', '5'))
    for nm, got, want in (('b_3^p = -4', s3['b'], mp.mpf(-4)), ('c_3^p = -4/3', s3['c'], mp.mpf(-4) / 3),
                          ('b_4^p = 16A+24', s4['b'], 16 * A + 24), ('c_4^p = 8A/3+8', s4['c'], 8 * A / 3 + 8)):
        d = abs(mp.mpf(got) - want); row(f'Sec 24.3 {nm}', mp.nstr(mp.mpf(got), 20), mp.nstr(want, 20), d < mp.mpf('1e-40'), f'|diff| {mp.nstr(d, 3)}')
    quoted('Sec 24.3 b_5^p', s5['b'], '-1540.38932947914290838')
    quoted('Sec 24.3 c_5^p', s5['c'], '-251.621917341000466476')
    quoted('Sec 24.3 higher-order part / 2187', hi['higher_piece'], '1.535501191157190785360393154334')
    quoted('Sec 24.3 Delta_p, 32 nodes / 45 digits', lo['power_contribution_C6'], '-8.02e-34',
           'note fa71533 prints -8.03e-34 (record -8.0229e-34); erratum in note_changes.md')
    quoted('Sec 24.3 Delta_p, 48 nodes / 55 digits', hi['power_contribution_C6'], '6.91e-47')
    dmax = max(abs(dec(lo['power_contribution_C6'])), abs(dec(hi['power_contribution_C6'])))
    row('Delta_p negligible for C6(2) (|Delta_p| < 1e-30 in both settings)', f'{dmax:.2e}', '< 1e-30', dmax < Decimal('1e-30'))
    row('Sec 24.3 sunset insertions: 32 P4(2) to b6, zero to c6', hi['sunset_on_wheel_contribution'], '32*P4 to b6, zero to c6',
        hi['sunset_on_wheel_contribution'] == '32*P4 to b6, zero to c6')

    # 2. analytic extension audit (Sec 24.2)
    rc, t = run('audit_analytic_extension.py', W, log=logs / 'audit_analytic_extension.log')
    row('run audit_analytic_extension.py', f'rc {rc}', 'rc 0', rc == 0, f'{t:.1f} s')
    if rc == 0:
        compare_json('analytic_extension_audit.json: rerun vs published', load(W / 'analytic_extension_audit.json'),
                     load(R / 'verification/analytic_extension_audit.json'))
    X = load(R / 'verification/analytic_extension_audit.json')
    row('Sec 24.2 Cauchy settings (nodes, digits, radius)', str(X['Cauchy_runs']), "[[32, 45, '.02'], [48, 55, '.016']]",
        X['Cauchy_runs'] == [[32, 45, '.02'], [48, 55, '.016']])
    for f, n, dps, r in (('position_kite_leaf_ms_32_45_.02.json', 32, 45, '.02'), ('position_kite_leaf_ms_48_55_.016.json', 48, 55, '.016')):
        h = load(PKG / 'reproduction' / f)
        row(f'saved counterterms {f}: header', f"{h['nodes']}/{h['kite_dps']}/{h['radius']}", f'{n}/{dps}/{r}',
            (h['nodes'], h['kite_dps'], h['radius']) == (n, dps, r))
    row('Sec 24.2 pole coefficients compared', X['pole_coefficients_compared'], 2699, X['pole_coefficients_compared'] == 2699)
    quoted('Sec 24.2 max absolute discrepancy of the two settings', X['max_absolute_comparison'], '7.38e-30',
           'note fa71533 prints 7.39e-30; erratum in note_changes.md')
    quoted('Sec 24.2 max discrepancy between admissible roots', X['max_root_discrepancy'], '7.97e-45')
    sc = {s['id']: s for s in X['sunset_contractions']}
    row('Sec 24.3 sunset contractions L6G106, L6G117: 16 P4(2) to b6 each, 0 to c6', sorted(sc), "['L6G106', 'L6G117']",
        sorted(sc) == ['L6G106', 'L6G117'] and all(s['MS_b6'] == '16*P4(2)' and s['MS_c6'] == '0' for s in sc.values()))

    # 3. exact Gamma sector (Sec 24.1)
    gdir = W / NESTED / 'analytic/code'
    rc, t = run('check_gamma_coverage.py', gdir, log=logs / 'check_gamma_coverage.log')
    row('run check_gamma_coverage.py', f'rc {rc}', 'rc 0', rc == 0, f'{t:.1f} s')
    gref = R / 'reproduction' / NESTED / 'analytic/verification/gamma_and_coverage_checks.json'
    if rc == 0:
        compare_json('gamma_and_coverage_checks.json: rerun vs published', load(W / NESTED / 'analytic/verification/gamma_and_coverage_checks.json'), load(gref))
    ex = load(PKG / 'reproduction' / NESTED / 'analytic/verification/sp_exact.json')
    ell, z3, z5, z2 = sp.symbols('ell zeta3 zeta5 zeta2'); loc = dict(ell=ell, zeta3=z3, zeta5=z5, zeta2=z2)
    Lp = {x['loop']: x for x in ex['loops']}; P = lambda s: sp.expand(sp.sympify(s, locals=loc))
    cnt = [Lp[k]['count'] for k in range(1, 7)]
    row('Sec 24.1 closed Gamma-sector classes, loops 1-6', cnt, [1, 2, 6, 15, 47, 137], cnt == [1, 2, 6, 15, 47, 137])
    R_ = sp.Rational
    for nm, got, want in (('b_2 = -6A', P(Lp[2]['b']), -24 * ell), ('c_2 = -A', P(Lp[2]['c']), -4 * ell),
                          ('b_3^Gamma = 336 l^2 - 4', P(Lp[3]['b']), 336 * ell**2 - 4),
                          ('c_3^Gamma = 52 l^2 - 4/3', P(Lp[3]['c']), 52 * ell**2 - R_(4, 3)),
                          ('c_5^Gamma (two:c5Gamma)', P(Lp[5]['c']),
                           R_(12692, 3) * ell**4 - 208 * ell**2 + R_(1085, 4) * ell * z3 - R_(224, 3) * ell - R_(73, 6)),
                          ('2187 Xi_Gamma (two:GammaAnswer)', sp.expand(3 * P(Lp[6]['c']) - P(Lp[6]['b']) - 24 * ell * P(Lp[5]['c'])),
                           R_(5518904, 75) * ell**5 - R_(216256, 45) * ell**3 + R_(5763, 20) * ell**2 * z3 - 2784 * ell**2
                           + R_(6368, 15) * ell - 69 * z3 + R_(83397, 640) * z5)):
        row(f'Sec 24.1 {nm}', 'exact', 'exact', sp.expand(got - want) == 0)
    sub = {ell: sp.log(2), z3: sp.zeta(3), z5: sp.zeta(5), z2: sp.zeta(2)}
    v6 = sp.N((3 * P(Lp[6]['c']) - P(Lp[6]['b'])).subs(sub) / 2187, 45)
    xi = sp.N((3 * P(Lp[6]['c']) - P(Lp[6]['b']) - 24 * ell * P(Lp[5]['c'])).subs(sub) / 2187, 45)
    quoted('Sec 24.1 (3c_6^Gamma - b_6^Gamma)/2187', str(v6), '12.17588503555361667474529')
    quoted('Sec 24.1 Xi_Gamma', str(xi), '4.274679502470384138347130')
    gc = load(gref)
    row('Gamma values agree with the coverage record (40 digits)', 'equal', 'equal',
        abs(dec(gc['gamma_six_loop_only_value']) - dec(str(v6))) < Decimal('1e-40') and
        abs(dec(gc['gamma_physical_combination_value']) - dec(str(xi))) < Decimal('1e-40'))

    # 4. split-contour kite normalization (Sec 24.2)
    rc, t = run('klt_checks.py', W, log=logs / 'klt_checks.log')
    row('run klt_checks.py', f'rc {rc}', 'rc 0', rc == 0, f'{t:.1f} s')
    if rc == 0:
        compare_json('klt_checks.json: rerun vs published', load(W / 'klt_checks.json'), load(R / 'reproduction/klt_checks.json'))
    K = load(R / 'reproduction/klt_checks.json')['checks']; kinds = [c['kind'] for c in K]
    row('Sec 24.2 KLT tests: 3 symmetric (Selberg), 5 completion, changed tail', f"{kinds.count('Selberg')}/{kinds.count('S5')}/{kinds.count('tail')}",
        '3/5/2', (kinds.count('Selberg'), kinds.count('S5'), kinds.count('tail')) == (3, 5, 2))
    Q2 = mp.mpf(load(PKG / 'reproduction' / NESTED / 'verification/reference_periods.json')['Q2'])
    j1 = mp.mpf(str(dec(K[0]['value']))); row('Sec 24.2 all five powers one: J = 3 Q_2', mp.nstr(j1, 20), mp.nstr(3 * Q2, 20),
                                             K[0]['p'] == ['1.0'] * 5 and abs(j1 - 3 * Q2) < mp.mpf('1e-40'))
    emax = max(abs(dec(c.get('error', c.get('difference')))) for c in K)
    row('KLT checks: largest error', f'{emax:.2e}', '< 1e-42', emax < Decimal('1e-42'))

    # 5. two-loop finite-MOM jets (Sec 25.3)
    rc, t = run('fresh_two_loop_mom.py', W, log=logs / 'fresh_two_loop_mom.log')
    row('run fresh_two_loop_mom.py', f'rc {rc}', 'rc 0', rc == 0, f'{t:.1f} s')
    if rc == 0:
        compare_json('fresh_two_loop_mom.json: rerun vs published', load(W / 'fresh_two_loop_mom.json'), load(R / 'reproduction/fresh_two_loop_mom.json'))
    T = load(R / 'reproduction/fresh_two_loop_mom.json')
    row('Sec 25.3 two contours: radius/nodes, 65 digits', [(r['radius'], r['nodes']) for r in T['records']],
        "[('0.05', 64), ('0.08', 80)]", [(r['radius'], r['nodes']) for r in T['records']] == [('0.05', 64), ('0.08', 80)] and T['dps'] == 65)
    d = dec(T['largest_difference_vs_saved_input'])
    row('Sec 25.3 agreement with the saved input through z^4', f'{d:.3e}', '< 6.8e-61', d < Decimal('6.8e-61'))
    jets = T['records'][0]['b2_jets']
    for j, want in enumerate(('-16.63553233344', '29.02087369541', '-47.11795797162', '74.14063002868', '-114.64528966290')):
        quoted(f'Sec 25.3 b_(2,{j})', jets[j], want)

    # 6. fixed point and forest identities (Sec 25.1, 25.3)
    rc, t = run('check_mom_lagrange.py', W, log=logs / 'check_mom_lagrange.log')
    row('run check_mom_lagrange.py', f'rc {rc}', 'rc 0', rc == 0, f'{t:.1f} s')
    if rc == 0:
        compare_json('mom_lagrange_checks.json: rerun vs published', load(W / 'mom_lagrange_checks.json'), load(R / 'reproduction/mom_lagrange_checks.json'))
    Lg = load(R / 'reproduction/mom_lagrange_checks.json')
    row('Sec 25.3 fixed-point checks (all, of which constant-MS sixth order)', f"{Lg['exact_rational_checks']}/{Lg['constant_MS_sixth_assembly_checks']}",
        '192/24', (Lg['exact_rational_checks'], Lg['constant_MS_sixth_assembly_checks'], Lg['all_passed']) == (192, 24, True))
    Fx = load(R / 'reproduction' / NESTED / 'forest_exact_checks.json')['checks']; f6 = [c for c in Fx if c['L'] == 6][0]
    row('Sec 25.1 forest-to-RG identity at six loops: beta/mass monomials (record)', f"{f6['beta_monomials']}/{f6['gamma_monomials']}", '532/383',
        (f6['beta_monomials'], f6['gamma_monomials']) == (532, 383) and all(c['beta_difference_zero'] and c['gamma_difference_zero'] for c in Fx)
        and sorted(c['L'] for c in Fx) == [1, 2, 3, 4, 5, 6], 'all six loop orders vanish over the rationals')
    Km = load(R / 'reproduction/kernel_map_checks.json')
    per = [c['graphs'] for c in Km['checks']]
    row('Sec 25.2 nonzero finite kernels L=2..6 and the Kirchhoff check (record)', f"{per} = {Km['total']}", '[1, 5, 16, 76, 395] = 493',
        per == [1, 5, 16, 76, 395] and Km['total'] == 493 and all(c['all_exact_Kirchhoff_differences_zero'] for c in Km['checks']))

    # 7. ties to the other packages (optional inputs)
    hpc = Path(a.hpc)
    tl = hpc / 'inputs/two_loop.json'
    if tl.exists():
        B2 = load(tl)['B2']; rel = max(abs(float(jets[j]) - B2[j]) / abs(B2[j]) for j in range(5))
        row('C6(2) assembly input LRI_C6_D2_HPC/inputs/two_loop.json B2 = fresh jets', f'{rel:.1e}', '< 1e-15', rel < 1e-15)
    else: skip('C6(2) assembly input two_loop.json = fresh jets', f'{tl} not present')
    cp = hpc / 'reference/baseline_previous/baseline/lri_C6_d2_complete_update/verification'
    if cp.exists():
        names = ('power_cancellation.json', 'power_cancellation_high.json', 'power_sector_audit.json')
        same = [sha(cp / n) == sha(R / 'verification' / n) for n in names]
        row('LRI_C6_D2_HPC/reference copies of the power records are byte-identical', f'{sum(same)}/3', '3/3', all(same))
    else: skip('LRI_C6_D2_HPC/reference copies of the power records', f'{cp} not present')
    c6 = Path(a.c6)
    if not c6.exists(): c6 = c6.parent / 'run-20260928-m8192/C6_result.json'
    if c6.exists():
        r6 = load(c6); v = r6['C6'] + float(dec(hi['power_contribution_C6']))
        row('C6(2) with Delta_p added equals the published estimator (double precision)', f"{r6['C6']!r}", '362.36647176...',
            v == r6['C6'] and f"{r6['C6']:.8f}" == '362.36647176', 'the production assembles the power-free part; Delta_p is below its last bit')
    else: skip('C6(2) with Delta_p added', 'C6_result.json not present')
    c7 = Path(a.c7)
    if c7.exists():
        r7 = load(c7); pd, pe = r7['power_differences'][6], r7['power_difference_errors'][6]
        pull = (pd - float(dec(hi['power_contribution_C6']))) / pe
        row('C7(2) explicit power sector at order 6 vs analytic Delta_p (pull)', f'{pull:+.2f}', '|pull| < 3', abs(pull) < 3,
            f'measured ({pd * 1e4:.1f} +- {pe * 1e4:.1f})e-4, note Sec 28.7')
    else: skip('C7(2) explicit power sector at order 6', f'{c7} not present')

    return report(out, 'replay')


if __name__ == '__main__':
    sys.exit(main())
