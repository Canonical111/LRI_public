#!/usr/bin/env python3
"""Public replay of lri_d3_reduction_update: the d=3 half-shift determinant reduction of the primitive periods.

Added for the public release (2026-10-13); not part of the research bundle. Run from the package folder:

    python3 public/replay.py --tier test     # about 5 s: checksums, check_exact.py rerun, record checks
    python3 public/replay.py --tier replay   # about 4 min on one core: also verify_d3.py and check_spectral.py

The package's TeX/PDF note revisions (merged into the condensed note, Sections 17-19) and its superseded history/
drafts are not shipped. public/dropped_paths.txt names them; the checksum lists keep their lines, and only these files
may be absent.

The original scripts are run unchanged, with the commands of README_d3_reduction.md, in a copy of the package under
--work (default .work/). Their records are compared with the shipped records in verification/general_d3/, and the
shipped and rerun records with the numbers that the condensed note quotes (--results, default
../../results/closed_forms_3/d3_specialization_quoted.json). Writes <work>/REPLAY.md and exits 1 on any FAIL.
"""
import sys
from pathlib import Path

import mpmath as mp
import sympy as sp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replaylib import (PKG, Report, about, agrees_to_shown, check_bundle_sums, check_own_list, common_args, load,  # noqa: E402
                       make_work, max_leaf_difference, parse_num, py, real, rounds_to, run, short, strip_keys)

REC = 'verification/general_d3'


def record_checks(rep, label, rec, q):
    """Checks of one set of records (shipped or rerun) against the note's quoted numbers."""
    pv = load(rec / 'period_values.json')
    run90 = [r for r in pv['runs'] if r['dps'] == 90][0]
    run55 = [r for r in pv['runs'] if r['dps'] == 55][0]
    v = run90['values']
    src = f'{label}: {REC}/period_values.json (90 digits)'

    # Q3, P4(3), P5(3) against the 33 decimals shown in the note
    for key, name in [('Q3', 'Q_3'), ('P4_3', 'P_4(3)'), ('P5_3', 'P_5(3)')]:
        val = real(v[key])
        ok, tol = agrees_to_shown(val, q['periods'][key])
        rep.check(f'{label}: {name} = note value', ok and abs(parse_num(v[key]).imag) == 0, short(val, 36),
                  q['periods'][key], f'{short(tol, 1)} (one unit in the last shown digit)', src)

    # the boxed formulas of the note, evaluated with the recorded components and the Gamma forms of a3*b3 and b4
    def boxed():
        mp.mp.dps = 100
        pi, rt = mp.pi, mp.sqrt(2)
        g = mp.gamma(mp.mpf(1) / 4)
        amp = v['amplitudes']
        h3 = -real(v['Xi3_0']) / (2 * rt * pi ** mp.mpf(1.5))                       # td:zeroSamples
        q3 = 4 * pi ** 2 * h3 - g ** 10 / (48 * pi ** mp.mpf(3.5))                    # td:Qanswer
        b4 = g ** 6 / (16 * pi ** mp.mpf(2.5))                                        # td:P4data (Dougall form)
        p4 = 2 * pi * real(v['Xi4_0']) - 10 * pi * real(v['Xi4_1_8']) + (14 * rt - 20) * pi * real(amp['a4']) * b4
        e0, ep, em = [real(x) for x in v['reduced_polynomial_samples']]                # td:sevenE
        p5 = 4 * rt * pi ** mp.mpf(1.5) * (-35 * e0 + (22 + 13 / rt) * ep + (22 - 13 / rt) * em) \
            - 448 * pi ** mp.mpf(1.5) * (2 * real(amp['bb']) - real(amp['aa']))     # td:P5answer
        for key, eq, got in [('Q3', 'td:Qanswer with td:zeroSamples', q3), ('P4_3', 'td:P4answer, b_4 in Gamma form', p4),
                             ('P5_3', 'td:P5answer', p5)]:
            d = abs(got - real(v[key]))
            rep.check(f'{label}: boxed formula {eq} reproduces {key}', d < mp.mpf('1e-75'), short(d, 3), '0',
                      '1e-75 (90-digit record; Gamma forms exact)', src)
    rep.guard(f'{label}: boxed formulas', boxed, src)

    # Dixon and Rogers-Dougall evaluations of the ordinary amplitudes
    for key, what in [('gamma_product_error', 'a_3 b_3 = Gamma(1/4)^10/(16 sqrt2 pi^4) (Dixon)'),
                      ('Dougall_b4_error', 'b_4 = Gamma(1/4)^6/(16 pi^(5/2)) (Rogers-Dougall)')]:
        e = abs(parse_num(run90[key]))
        rep.check(f'{label}: td:gammaAmplitudes {what}', e < mp.mpf(q['gamma_amplitudes']['bound_at_90_digits']),
                  short(e, 3), '0', q['gamma_amplitudes']['bound_at_90_digits'], src)

    # changed precision 55 -> 90 digits
    d = max(abs(parse_num(run90['values'][k]) - parse_num(run55['values'][k])) for k in ('Q3', 'P4_3', 'P5_3'))
    rep.check(f'{label}: formula values at 55 and 90 working digits agree', d < mp.mpf('1e-48'), short(d, 3),
              'record: 1.6e-49 (P5_3)', '1e-48', src)

    # formula (90 digits) minus fresh Gamma-kernel integration (60 digits): 'about 1e-51, 1e-52, 1e-53'
    fs = load(rec / 'fresh_spectral.json')
    row60 = [r for r in fs['rows'] if r['dps'] == 60][0]
    cs = load(rec / 'comparison_summary.json') if (rec / 'comparison_summary.json').exists() else None
    for key in ('Q3', 'P4_3', 'P5_3'):
        mp.mp.dps = 100
        r = real(v[key]) - mp.mpf(row60[key])
        k = q['spectral_residuals']['about_power_of_ten'][key]
        rep.check(f'{label}: {key} formula minus fresh spectral is about 1e{k}', about(r, k), short(r, 3),
                  f'about 1e{k}', q['spectral_residuals']['tolerance'],
                  f'{label}: period_values.json (90) - fresh_spectral.json (60)')
        if cs is not None:
            rec_r = [c for c in cs['comparisons'] if c['spectral_dps'] == 60][0]['formula_minus_fresh_spectral'][key]
            rel = abs(r - mp.mpf(rec_r)) / abs(mp.mpf(rec_r))
            rep.check(f'{label}: {key} residual equals comparison_summary.json', rel < mp.mpf('1e-20'), short(r, 6),
                      short(rec_r, 6), '1e-20 relative (difference of two stored values)', 'comparison_summary.json')
    row45 = [r for r in fs['rows'] if r['dps'] == 45][0]
    d = max(abs(mp.mpf(row45[k]) - mp.mpf(row60[k])) for k in ('Q3', 'P4_3', 'P5_3'))
    rep.check(f'{label}: fresh spectral at 45 and 60 working digits agree', d < mp.mpf('1e-40'), short(d, 3), '',
              '1e-40 (the 45-digit run limits)', f'{label}: fresh_spectral.json')

    # identities at 75 digits and literal ordinary hypergeometric calls at 40 digits
    idt = load(rec / 'identities.json')
    mx = max(abs(parse_num(p['residual'])) for p in idt['projections'])
    rep.check(f'{label}: half-shift projections (td:determinants) at off-grid complex t', mx < mp.mpf('1e-60'), short(mx, 3),
              '0', '1e-60 at 75 working digits', f'{label}: identities.json')
    mx = max(abs(parse_num(p['residual'])) for p in idt['mode_checks'])
    rep.check(f'{label}: finite-mode identities (td:momentModes) at complex u', mx < mp.mpf('1e-60'), short(mx, 3), '0',
              '1e-60 at 75 working digits', f'{label}: identities.json')
    ca = idt['complex_alternatives']
    mx = max(abs(parse_num(ca[k])) for k in ('P4_difference', 'P5_difference', 'Xi4_one_Horn_error', 'Xi7_one_Horn_error'))
    rep.check(f'{label}: complex-node variants equal the real-node P_4(3), P_5(3)', mx < mp.mpf('1e-60'), short(mx, 3), '0',
              '1e-60 at 75 working digits', f'{label}: identities.json')
    lit = load(rec / 'literal_hypergeometric.json')
    mx = max(abs(parse_num(c['residual'])) for c in lit['checks'])
    rep.check(f'{label}: six literal mpmath.hyper calls equal the accelerated moments', mx < mp.mpf('1e-35'), short(mx, 3),
              '0', '1e-35 at 40 working digits', f'{label}: literal_hypergeometric.json')


def exact_checks(rep, label, rec, q):
    ex = load(rec / 'exact_algebra.json')
    w = ex['residue_weights_without_pi']
    ok = all([sp.simplify(sp.sympify(a) - sp.sympify(b)) == 0 and len(w[r]) == len(q['residue_weights'][r])
              for r in ('3', '4', '7') for a, b in zip(w[r], q['residue_weights'][r])])
    rep.check(f'{label}: residue weights = td:residueWeights', ok, '; '.join(','.join(w[r]) for r in ('3', '4', '7'))[:120],
              'note eq. td:residueWeights', 'exact (SymPy)', f'{label}: {REC}/exact_algebra.json')
    names = {c['name']: c['residual'] for c in ex['symbolic_checks']}
    for name, eq in q['exact_identities']['note_eqs'].items():
        rep.check(f'{label}: exact identity "{name}" ({eq})', names.get(name) == '0', names.get(name, 'missing'), '0',
                  'exact (SymPy)', f'{label}: exact_algebra.json')
    cnt = q['exact_identities']['package_readme_counts']
    got = (len(ex['symbolic_checks']), ex['horn_coefficient_checks'], ex['horn_arrays'])
    rep.check(f'{label}: exact checks all passed, counts as in the package README', ex['all_passed'] is True and
              all(c['residual'] == '0' for c in ex['symbolic_checks']) and got == (cnt['symbolic_checks'],
              cnt['horn_coefficient_checks'], cnt['horn_arrays']), f'{got}', f"({cnt['symbolic_checks']}, "
              f"{cnt['horn_coefficient_checks']}, {cnt['horn_arrays']})", 'exact', f'{label}: exact_algebra.json')
    ha = load(rec / 'horn_arrays.json')['arrays']
    nodes = {r: [a['t'] for a in ha if a['r'] == int(r)] for r in ('3', '4', '7')}
    args = {r: [a['arguments'] for a in ha if a['r'] == int(r)] for r in ('3', '4', '7')}
    ok = all(nodes[r] == q['horn_nodes'][r] for r in nodes) and \
        all(all(x == q['horn_nodes']['arguments'][r] for x in args[r]) for r in args) and \
        all(a['all_parameters_positive_rational'] for a in ha) and \
        all(sp.Rational(p['a']) > 0 for a in ha for p in a['upper'] + a['lower'])
    rep.check(f'{label}: two-variable Horn values 1, 2, 5 at the note nodes, positive rational rows', ok,
              '; '.join(f"r={r}: {','.join(nodes[r])}" for r in nodes), 'td:Hbase, td:Hseven, td:fiveHornNodes',
              'exact', f'{label}: horn_arrays.json')


def main(argv=None):
    mp.mp.dps = 100
    a = common_args(argv, '../../results/closed_forms_3')
    q = load(a.results / 'd3_specialization_quoted.json')
    rep = Report(f'Replay of lri_d3_reduction_update (tier {a.tier})', a.work)
    shipped = PKG / REC

    # 1. integrity
    rep.guard('bundle checksums', lambda: check_bundle_sums(rep))
    rep.guard('archive_manifest.json', lambda: check_own_list(
        rep, 'archive_manifest.json', [(f['path'], f['sha256']) for f in load(PKG / 'archive_manifest.json')['files']],
        strict=True))

    # 2. shipped records against the note
    rep.guard('shipped exact records', lambda: exact_checks(rep, 'shipped', shipped, q))
    rep.guard('shipped numeric records', lambda: record_checks(rep, 'shipped', shipped, q))

    def table1():
        cs = load(shipped / 'comparison_summary.json')['coefficient_assembly_using_new_periods']
        for k in ('C2', 'C3', 'C4'):
            ok, tol = agrees_to_shown(mp.mpf(cs[k]), q['section1_table_d3'][k])
            rep.check(f'shipped: {k}(3) of comparison_summary.json = Section 1 table', ok, short(cs[k], 16),
                      q['section1_table_d3'][k], 'one unit in the last shown digit; record only (assembly script not '
                      'in the package; the table entries belong to the general-d rows)', 'comparison_summary.json')
    rep.guard('Section 1 table', table1)

    # 3. reruns in a work copy
    work = make_work(a.work)
    logs = a.work / 'logs'
    ok, _ = run(rep, 'check_exact.py', [py(), 'code/general_d3/check_exact.py'], work, logs,
                expect='25 symbolic checks; 288 rational Horn coefficients; all passed.')
    if ok:
        for f in ('exact_algebra.json', 'horn_arrays.json'):
            rep.check(f'rerun {f} identical to the shipped record (parsed JSON)', load(work / REC / f) == load(shipped / f),
                      'equal' if load(work / REC / f) == load(shipped / f) else 'differs', f'{REC}/{f}', 'exact', 'rerun')
        rep.guard('rerun exact records', lambda: exact_checks(rep, 'rerun', work / REC, q))

    if a.tier == 'replay':
        ok1, _ = run(rep, 'verify_d3.py', [py(), 'code/general_d3/verify_d3.py'], work, logs)
        ok2, _ = run(rep, 'check_spectral.py', [py(), 'code/general_d3/check_spectral.py'], work, logs)
        if ok1:
            for f, skip, tol in [('period_values.json', ('/seconds',), '1e-45'),
                                 ('identities.json', (), '1e-65'),
                                 ('literal_hypergeometric.json', ('/seconds',), '1e-35')]:
                def cmp(f=f, skip=skip, tol=tol):
                    d, n = max_leaf_difference(strip_keys(load(work / REC / f), ['seconds']),
                                               strip_keys(load(shipped / f), ['seconds']), skip)
                    rep.check(f'rerun {f} equals the shipped record', d is not None and d < mp.mpf(tol),
                              f'max |diff| {short(d, 3)} over {n} numbers' if d is not None else f'structure differs {n}',
                              f'{REC}/{f}', f'{tol} absolute (same code and mpmath; observed bitwise equal)', 'rerun')
                rep.guard(f'compare {f}', cmp)
        if ok2:
            def cmp_fs():
                d, n = max_leaf_difference(strip_keys(load(work / REC / 'fresh_spectral.json'), ['seconds']),
                                           strip_keys(load(shipped / 'fresh_spectral.json'), ['seconds']))
                rep.check('rerun fresh_spectral.json equals the shipped record', d is not None and d < mp.mpf('1e-40'),
                          f'max |diff| {short(d, 3)} over {n} numbers', f'{REC}/fresh_spectral.json',
                          '1e-40 absolute (45-digit row limits; observed bitwise equal)', 'rerun')
            rep.guard('compare fresh_spectral.json', cmp_fs)
        if ok1 and ok2:
            # comparison_summary.json is not written by any shipped script: the rerun is checked against the note
            rerun_rec = work / REC
            (rerun_rec / 'comparison_summary.json').unlink(missing_ok=True)
            rep.guard('rerun numeric records', lambda: record_checks(rep, 'rerun', rerun_rec, q))
    else:
        rep.add('verify_d3.py, check_spectral.py reruns', 'SKIP', 'tier test', '', '', 'run make -f public.mk replay')
    return rep.write()


if __name__ == '__main__':
    sys.exit(main())
