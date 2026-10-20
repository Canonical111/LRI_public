#!/usr/bin/env python3
"""Public replay of lri_C6_d3_complete_update: the d=3 power-sector compensation of C6(3) and the d=3 finite-scheme
inputs (coverage, Gamma jets, two-loop jets, Lagrange extraction).

Added for the public release (2026-10-13); not part of the research bundle. Run from the package folder:

    python3 public/replay.py --tier test     # about 10 s: checksums, the seven light audit scripts, record checks
    python3 public/replay.py --tier replay   # about 2 min: also the three graph-recursion audits power_ms_d3.py
                                             # (75, 90, 65 working digits) and analyze_power.py on their output

The original scripts are run unchanged, with the commands of README.md, in a copy of the package under --work
(default .work/). In the replay tier the three audits overwrite the copy's records/power_ms_d3_{complete,shifted,
arbitrary_masters}.json, so that analyze_power.py, check_core_propagation.py and check_coverage.py then read the
reruns. Everything is compared with the shipped records in records/ and with the numbers that the condensed note
quotes (--results, default ../../results/C6_3/power_compensation_quoted.json). Writes <work>/REPLAY.md and exits 1
on any FAIL. The first-full-C6(3) sampling run of this package (33.50 +- 0.6, superseded) is not part of the release.
"""
import re
import sys
from pathlib import Path

import mpmath as mp
import sympy as sp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replaylib import (PKG, Report, agrees_to_shown, check_bundle_sums, check_own_list, common_args, load,  # noqa: E402
                       make_work, max_leaf_difference, parse_num, py, real, rounds_to, run, short, strip_keys)

LIGHT = [  # (script, expected stdout fragment, record it writes)
    ('check_mom_d3.py', '256 passed', 'mom_lagrange_d3_checks.json'),
    ('check_unknown_core.py', "'physical_unknown_combination': '0'", 'unknown_core_cancellation.json'),
    ('power_assembly_polynomial.py', None, 'power_assembly_polynomial.json'),
    ('check_gamma_d3.py', 'Gamma checks: 25 passed', 'gamma_checks.json'),
    ('two_loop_d3.py', None, 'two_loop_d3.json'),
]
POWER_RECORDS = {'complete': 'power_ms_d3_complete.json', 'shifted': 'power_ms_d3_shifted.json',
                 'arbitrary_masters': 'power_ms_d3_arbitrary_masters.json'}


def consts():
    mp.mp.dps = 110
    q = mp.mpf(3) / 4
    A = mp.digamma(2 * q) + mp.digamma(1) - 2 * mp.digamma(q)
    N = mp.digamma(-q) + mp.digamma(3 * q) - mp.digamma(1) - mp.digamma(2 * q)
    M = mp.gamma(-q) * mp.gamma(2 * q) ** 2 / mp.gamma(3 * q)
    return A, N, M


def exact_checks(rep, label, rec, q):
    """Exact records: Lagrange extraction, unknown-core cancellation, delta R and the lower power pieces."""
    m = load(rec / 'mom_lagrange_d3_checks.json')
    lq = q['lagrange']
    rep.check(f'{label}: fixed-point substitution = bivariate Lagrange inversion (d3six:lagrange)',
              m['all_passed'] is True and m['exact_rational_checks'] == lq['exact_rational_checks'] and
              m['constant_MS_sixth_assembly_checks'] == lq['constant_MS_sixth_assembly_checks'],
              f"{m['exact_rational_checks']} checks, {m['constant_MS_sixth_assembly_checks']} MS assembly",
              f"{lq['exact_rational_checks']}, {lq['constant_MS_sixth_assembly_checks']}", 'exact',
              f'{label}: mom_lagrange_d3_checks.json')
    u = load(rec / 'unknown_core_cancellation.json')
    A, F0, F1 = sp.symbols('A F0 F1')
    cq = q['core']
    ok = all(sp.simplify(sp.sympify(u[k]) - sp.sympify(cq[r])) == 0 for k, r in
             [('r5_unknown', 'r_L5G086'), ('r6_332_unknown', 'r_L6G332'), ('r6_333_unknown', 'r_L6G333')])
    comb = sp.expand(sp.Rational(9, 2) * (sp.sympify(u['r6_332_unknown']) + sp.sympify(u['r6_333_unknown']))
                     - sp.Rational(15, 2) * A * sp.sympify(u['r5_unknown']))
    rep.check(f'{label}: unknown core jets cancel exactly (d3six:coreResidues, d3six:unknownCancellation)',
              ok and comb == 0 and u['physical_unknown_combination'] == '0',
              f"r5={u['r5_unknown']}; r332={u['r6_332_unknown']}; r333={u['r6_333_unknown']}; combination {comb}",
              cq['physical_combination'], 'exact (SymPy)', f'{label}: unknown_core_cancellation.json')
    p = load(rec / 'power_assembly_polynomial.json')
    Asym, R, M, N, Q, P, U, V = sp.symbols('A R M N Q P U V')
    loc = dict(A=Asym, R=R, M=M, N=N, Q=Q, P=P, U=U, V=V)
    d = sp.expand(sp.sympify(p['delta_lower_R'], locals=loc) - sp.sympify(q['delta_R']['expression'], locals=loc))
    rep.check(f'{label}: lower-order assembly difference delta R = d3six:deltaR', d == 0, f'difference {d}',
              q['delta_R']['expression'][:60] + '...', 'exact (SymPy)', f'{label}: power_assembly_polynomial.json')
    lq_ = q['lower_power']
    ok = all(sp.expand(sp.sympify(p[f'{k}_power'], locals=loc) - sp.sympify(lq_[f'{k}p'], locals=loc)) == 0
             for k in ('b3', 'c3', 'b4', 'c4'))
    rep.check(f'{label}: b3^p, c3^p, b4^p, c4^p used in the assembly = d3six:lowerPower', ok,
              f"{p['b3_power']}; {p['c3_power']}; {p['b4_power']}; {p['c4_power']}",
              'M; M/3; -11AM/2-3MN/2; -7AM/6-MN/2', 'exact (SymPy)', f'{label}: power_assembly_polynomial.json')


def jet_checks(rep, label, rec, q):
    g = load(rec / 'gamma_checks.json')
    gq = q['gamma_jets']
    ok_r, got = rounds_to(real(g['max_error']), gq['max_error'])
    rep.check(f'{label}: 20 Gamma log jets and 5 normalizations, 65-digit Cauchy check (d3six:GammaJets)',
              len(g['checks']) == gq['checks'] and g['working_dps'] == gq['dps'] and ok_r and
              max(mp.mpf(c['absolute_error']) for c in g['checks']) < mp.mpf('1e-57'),
              f"{len(g['checks'])} checks, max {got}", f"{gq['checks']}, {gq['max_error']}", gq['tolerance'],
              f'{label}: gamma_checks.json')
    t = load(rec / 'two_loop_d3.json')
    tq = q['two_loop']
    rn = [[r['radius'], r['nodes']] for r in t['records']]
    ok = t['dps'] == tq['dps'] and rn == tq['radii_nodes']
    worst = mp.mpf(0)
    for r in t['records']:
        for got_s, shown in zip(r['b2_jets'], tq['b2_jets']):
            o, tol = agrees_to_shown(mp.mpf(got_s), shown)
            ok = ok and o
            worst = max(worst, abs(mp.mpf(got_s) - mp.mpf(shown)))
    ok = ok and mp.mpf(t['max_difference']) < mp.mpf('1e-50')
    rep.check(f'{label}: two-loop beta jets b_(2,0..4) = d3six:twoLoopValues, both radii', ok,
              f"max |jet - shown| {short(worst, 2)}; radii differ by {short(t['max_difference'], 3)}",
              ', '.join(tq['b2_jets']), tq['tolerance'], f'{label}: two_loop_d3.json')


def coverage_checks(rep, label, rec, q):
    cv = load(rec / 'graph_coverage.json')
    cq = q['coverage']
    rows = {str(r['L']): r for r in cv['rows']}
    aud = {L: rows[L]['power_audited'] for L in ('3', '4', '5', '6')}
    ker = {L: rows[L].get('retained_finite_kernels') for L in ('2', '3', '4', '5', '6')}
    r6 = rows['6']
    ok = cv['all_checks_passed'] is True and aud == cq['power_classes_audited'] and ker == cq['retained_finite_kernels'] \
        and r6['zero_target_power_classes'] == cq['zero_target_power_classes_L6'] and r6['all_classes'] == \
        cq['all_classes_L6'] and r6['power_classes'] == cq['power_classes_L6'] and \
        r6['all_classes'] - r6['power_classes'] == cq['power_free_classes_L6'] and \
        all(rows[L]['power_audited'] == rows[L]['power_classes'] for L in ('3', '4', '5'))
    rep.check(f'{label}: full coverage of the power target and of the power-free kernels', ok,
              f"audited {aud}; L6 {r6['all_classes']} classes, {r6['power_classes']} power, "
              f"{r6['zero_target_power_classes']} zero weight; kernels {ker}",
              'loops 3,4,5: 1,5,31; L6: 121 + 52 zero, 660 = 487 + 173; kernels 1,5,16,76,395', 'exact',
              f'{label}: graph_coverage.json')


def core_checks(rep, label, rec, q):
    A, N, M = consts()
    c = load(rec / 'core_propagation_checks.json')
    mx = max(abs(mp.mpf(x['difference'])) for x in c['checks'])
    rep.check(f'{label}: trial core assignments (0,0), (101,-37) change the three residues as predicted',
              mx < mp.mpf(q['core']['trial_residue_bound']) and sorted(x['id'] for x in c['checks']) ==
              ['L5G086', 'L6G332', 'L6G333'], short(mx, 3), f"< {q['core']['trial_residue_bound']}",
              'the note states the bound', f'{label}: core_propagation_checks.json')
    d1 = abs(mp.mpf(c['chain_constant']) - M) + abs(M + 16 * mp.pi / 15)
    d2 = abs(mp.mpf(c['chain_linear']) - mp.mpf(7) / 4 * M * (A + N))
    d3 = abs(mp.mpf(c['core_pole_jet']['-2']) - 8) + abs(mp.mpf(c['core_pole_jet']['-1']) - 2 * A)
    d4 = abs(A - (2 + 4 * mp.log(2) - mp.pi)) + abs(N - (mp.mpf(62) / 15 - mp.pi - 4 * mp.log(2)))
    rep.check(f'{label}: C(0)=M_3=-16pi/15, C\'(0)=7/4 M_3 (A+N), core poles 8/z^2+2A/z (d3six:sunset, chainJet, coreJet)',
              max(d1, d2, d3, d4) < mp.mpf('1e-70'), short(max(d1, d2, d3, d4), 3), '0',
              '1e-70 (75 working digits)', f'{label}: core_propagation_checks.json')


def power_checks(rep, label, rec, q, records_dir):
    """Corrections (analyze_power.py output) and the per-graph power records."""
    A, N, M = consts()
    pq = q['power_correction']
    for name, run_ in pq['runs'].items():
        cr = load(rec / ('correction_' + POWER_RECORDS[name]))
        ok_s, got = rounds_to(real(cr['power_correction_C6']), run_['sum'])
        rep.check(f'{label}: power correction sum, {name} run ({run_["dps"]} digits, core {run_["core"]})',
                  ok_s and [cr['core_finite_jet'], cr['core_linear_jet']] == run_['core'], got, run_['sum'],
                  'rounds to the three digits shown', f'{label}: correction_{POWER_RECORDS[name]}')
        hi, lo = real(cr['higher_contribution']), real(cr['lower_difference'])
        aux = cr['auxiliary_power_sums']
        b3, c3, b4, c4 = (real(aux['3']['b']), real(aux['3']['c']), real(aux['4']['b']), real(aux['4']['c']))
        d = max(abs(b3 - M), abs(c3 - M / 3), abs(b4 - (-mp.mpf(11) / 2 * A * M - mp.mpf(3) / 2 * M * N)),
                abs(c4 - (-mp.mpf(7) / 6 * A * M - M * N / 2)))
        rep.check(f'{label}: graph recursion reproduces b3^p, c3^p, b4^p, c4^p, {name} run (d3six:lowerPower)',
                  d < mp.mpf('1e-60'), short(d, 3), '0', '1e-60', f'{label}: correction_{POWER_RECORDS[name]}')
        if name == 'shifted':
            for val, shown, what in [(hi, pq['higher_90'], 'Delta_p,higher'), (lo, pq['lower_90'], 'Delta_p,lower')]:
                ok, tol = agrees_to_shown(val, shown)
                rep.check(f'{label}: {what} at 90 digits = d3six:powerNumbers', ok, short(val, 33), shown,
                          f'{short(tol, 1)} (one unit in the last shown digit)',
                          f'{label}: correction_{POWER_RECORDS[name]}')
    # per-graph records: completeness of the audited power target, sunset contractions
    s = load(records_dir / POWER_RECORDS['shifted'])
    loops = {r['L']: r for r in s['loops']}
    pw = {str(L): sum(g['power'] for g in loops[L]['done']) for L in (3, 4, 5, 6)}
    failed = sorted(f['id'] for r in s['loops'] for f in r['failed'])
    failed_power = [f['id'] for r in s['loops'] for f in r['failed'] if f['power']]
    rep.check(f'{label}: graph recursion closes every power graph; only two non-power L4 graphs rejected',
              pw == q['coverage']['power_classes_audited'] and not failed_power and
              failed == q['coverage']['rejected_non_power_L4'], f'power done {pw}; rejected {failed}',
              f"{q['coverage']['power_classes_audited']}; {q['coverage']['rejected_non_power_L4']}", 'exact',
              f'{label}: {POWER_RECORDS["shifted"]}')
    P4 = mp.mpf(re.search(r"POWER_P4','([0-9.]+)'", (PKG / 'code/power_ms_d3.py').read_text()).group(1))
    byid = {g['id']: g for r in s['loops'] for g in r['done']}
    d = max(max(abs(real(byid[i]['b']) - (-4 * M * P4)), abs(real(byid[i]['c']))) for i in q['sunset']['graphs'])
    rep.check(f'{label}: sunset graphs L6G106, L6G117 each give -4 M_3 P_4(3) to b_6 and 0 to c_6', d < mp.mpf('1e-60'),
              short(d, 3), '0', q['sunset']['tolerance'], f'{label}: {POWER_RECORDS["shifted"]}')


def main(argv=None):
    mp.mp.dps = 110
    a = common_args(argv, '../../results/C6_3')
    q = load(a.results / 'power_compensation_quoted.json')
    rep = Report(f'Replay of lri_C6_d3_complete_update (tier {a.tier})', a.work)
    rec = PKG / 'records'

    rep.guard('bundle checksums', lambda: check_bundle_sums(rep, complete=False))
    rep.guard('file_checksums.json', lambda: check_own_list(
        rep, 'verification/file_checksums.json', list(load(PKG / 'verification/file_checksums.json').items())))

    def inputs():
        src = (PKG / 'code/power_ms_d3.py').read_text() + (PKG / 'code/analyze_power.py').read_text()
        for key, pat in [('Q3', r"POWER_Q','([0-9.]+)'"), ('P4_3', r"POWER_P4','([0-9.]+)'")]:
            vals = set(re.findall(pat, src))
            ok = len(vals) == 1 and agrees_to_shown(mp.mpf(vals.pop() if len(vals) == 1 else 0),
                                                    q['master_inputs'][key])[0]
            rep.check(f'audit input {key} (code default) = the value of the section Three dimensions', ok,
                      ', '.join(sorted(set(re.findall(pat, src)))), q['master_inputs'][key],
                      'one unit in the last shown digit', 'code/power_ms_d3.py, code/analyze_power.py')
    rep.guard('master inputs', inputs)

    for lab, fn in [('exact', exact_checks), ('jets', jet_checks), ('coverage', coverage_checks), ('core', core_checks)]:
        rep.guard(f'shipped {lab}', lambda fn=fn: fn(rep, 'shipped', rec, q))
    rep.guard('shipped power', lambda: power_checks(rep, 'shipped', rec, q, rec))

    work = make_work(a.work)
    logs = a.work / 'logs'
    wrec = work / 'records'
    ran = {}
    if a.tier == 'replay':
        for name, run_ in q['power_correction']['runs'].items():
            env = dict(run_['env'], POWER_OUTPUT=POWER_RECORDS[name])
            ok, _ = run(rep, f'power_ms_d3.py ({name})', [py(), 'code/power_ms_d3.py'], work, logs, env=env)
            if ok:
                def cmp(name=name):
                    new, old = load(wrec / POWER_RECORDS[name]), load(rec / POWER_RECORDS[name])
                    gn = {g['id']: g for r in new['loops'] for g in r['done']}
                    go = {g['id']: g for r in old['loops'] for g in r['done']}
                    same_ids = set(gn) == set(go) and [sorted(f['id'] for f in r['failed']) for r in new['loops']] == \
                        [sorted(f['id'] for f in r['failed']) for r in old['loops']]
                    d, n = max_leaf_difference({k: {f: gn[k][f] for f in ('b', 'c', 'ct')} for k in gn},
                                               {k: {f: go[k][f] for f in ('b', 'c', 'ct')} for k in go}) \
                        if same_ids else (None, 'graph sets differ')
                    tol = mp.mpf(10) ** (-(old['dps'] - 10))
                    rep.check(f'rerun {POWER_RECORDS[name]} equals the shipped record (all graphs, b, c, poles)',
                              d is not None and d < tol, f'max |diff| {short(d, 3)} over {n} numbers', f'records/{POWER_RECORDS[name]}',
                              f'{short(tol, 1)} = 10^-(dps-10) (same code and mpmath; observed bitwise equal)', 'rerun')
                rep.guard(f'compare {name}', cmp)
            pe = {k: v for k, v in run_['env'].items() if k in ('POWER_Q', 'POWER_P4')}
            ok2, _ = run(rep, f'analyze_power.py ({name})', [py(), 'code/analyze_power.py', POWER_RECORDS[name]], work, logs,
                         env=pe)
            ran[name] = ok and ok2
            if ok and ok2:
                def cmpc(name=name):
                    f = 'correction_' + POWER_RECORDS[name]
                    d, n = max_leaf_difference(load(wrec / f), load(rec / f))
                    tol = mp.mpf(10) ** (-(q['power_correction']['runs'][name]['dps'] - 10))
                    rep.check(f'rerun {f} equals the shipped record', d is not None and d < tol,
                              f'max |diff| {short(d, 3)} over {n} numbers', f'records/{f}', f'{short(tol, 1)}', 'rerun')
                rep.guard(f'compare correction {name}', cmpc)

    for script, expect, out in LIGHT + [('check_core_propagation.py', '"id": "L6G333"', 'core_propagation_checks.json'),
                                        ('check_coverage.py', None, 'graph_coverage.json')]:
        ok, _ = run(rep, script, [py(), f'code/{script}'], work, logs, expect=expect)
        if ok:
            def cmp(out=out):
                new, old = strip_keys(load(wrec / out), ['seconds']), strip_keys(load(rec / out), ['seconds'])
                if new == old:
                    rep.check(f'rerun {out} identical to the shipped record (parsed JSON)', True, 'equal',
                              f'records/{out}', 'exact', 'rerun')
                    return
                d, n = max_leaf_difference(new, old)
                rep.check(f'rerun {out} equals the shipped record', d is not None and d < mp.mpf('1e-55'),
                          f'max |diff| {short(d, 3)} over {n} numbers', f'records/{out}', '1e-55 absolute', 'rerun')
            rep.guard(f'compare {out}', cmp)

    label = 'rerun'
    for lab, fn in [('exact', exact_checks), ('jets', jet_checks), ('coverage', coverage_checks), ('core', core_checks)]:
        rep.guard(f'rerun {lab}', lambda fn=fn: fn(rep, label, wrec, q))
    if a.tier == 'replay' and all(ran.get(k) for k in POWER_RECORDS):
        rep.guard('rerun power', lambda: power_checks(rep, label, wrec, q, wrec))
    elif a.tier != 'replay':
        rep.add('power_ms_d3.py and analyze_power.py reruns (75, 90, 65 digits)', 'SKIP', 'tier test', '', '',
                'run make -f public.mk replay')
    return rep.write()


if __name__ == '__main__':
    sys.exit(main())
