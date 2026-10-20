#!/usr/bin/env python3
"""Replay of the d = 1 dual (s -> 1) series C^SR_1..C^SR_8 (new tool, 2026-10-15). Run from code/dual_d1/.

The package is a dated snapshot (2026-10-02 archive) of a computational compendium written by another AI system; its
scripts ship verbatim and run here unchanged on a re-pointed work copy (public/dual_lib.py: build_work).

--mode test     (seconds to a minute) A + B + C + D below and the compendium's default check (run_checks.py).
--mode replay   (a few minutes)       everything below except the items marked "full".
--mode full     (about 9 min)         replay + the compendium's tasks that need the hosted weight-6 C7 certificate or a
                                      C++/GMP compiler: reproduce.py --task certificates (complete), --task c8-numerical,
                                      --task c8-positive-check.

A. Snapshot: public/SNAPSHOT.sha256 (every shipped file, dated snapshot), and every shipped file against the
   compendium's own immutable list reproduction/MANIFEST.json; the restored lost file against its MANIFEST entry.
B. The paper's equations: the TeX of eq:sr-closed and eq:sr-C8 (../../results/quoted_numbers.json, copied from the
   paper) is parsed into exact rational coefficients of zeta products and compared EXACTLY with data/coefficients.json,
   with the compendium's closed forms (eq:thermal-main, eq:C8-candidate-main; public/compendium_extract.json, since the
   compendium's TeX source is not shipped), with the C8 record result.json, with the C6
   candidate the C6 input map uses (C6_candidate.expr) and with the C7 candidate string of verify_input_map.py.
C. Quoted numbers: the closed forms evaluated with mpmath at 50 digits (C3..C7; \\SRCthree..\\SRCseven) and the C8
   numerical record (\\SRCeight); \\SRorderword, \\SRorder, \\SRclosed from the registry; \\SRorderLit(word) and
   C1 = -2, C2 = 1/2 are literature values (INFO rows, cited); the d = 1 row of tab:sr (value and marker of each cell).
D. C8: the record C8 = Cfixed - P6/2 (result.json) recomputed exactly; its printing floor (half a unit in the last
   printed digit of every input, propagated exactly through the verbatim full_jacobian.py); the residual of the
   candidate formula against the record, which must not exceed that floor; the rational part pi_0 C8 = 88 from the
   record and from the exact rational full-Jacobian assembly of the 35 rational beta inputs.
E. The compendium's own tasks, verbatim, on the work copy (replay):
   run_checks.py; reproduce.py --task c8-saved (64-bucket P6 sum, decimal Jacobian, integer-relation recognition);
   reproduce.py --task c8-rational-algebra (reproduce_summary.py; regenerated coefficients.json, tables and
   summary_algebra.json compared with the shipped ones); the commands of reproduce.py --task certificates run one by
   one (D3 = C5 certificate, C6 certificate, C7 input map) plus the C6 input map and the C7 certificate at weights
   2..5 (its weight-6 file, 57 MB, is hosted: full); reproduce.py --task low-integrals.
Usage: python3 public/replay_dual_d1.py [--mode test|replay|full] [--work DIR]
"""
import argparse, json, os, sys, time
from decimal import Decimal, localcontext
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PKG.parent.parent/'verify'))
import dual_lib as D
import sri_lib as L

WORDS = {1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven', 8: 'eight', 9: 'nine'}
LIT = 'Benedetti:2024wgx, Benedetti:2025nzp'
MACRO = {3: '\\SRCthree', 4: '\\SRCfour', 5: '\\SRCfive', 6: '\\SRCsix', 7: '\\SRCseven', 8: '\\SRCeight'}
C8REC = 'data/archived/C8_zeta_candidate/result.json'
C8RAT = 'data/archived/C8_rational_completion/result.json'


def jload(p):
    return json.loads(Path(p).read_text())


def section_snapshot(T):
    L.verify_snapshot(PKG, T)
    man = jload(PKG/'reproduction/MANIFEST.json')['files']
    scrubbed, repinned = D.public_lists()
    present, bad, nsc, nrp = 0, [], 0, 0
    for r in man:
        p = PKG/r['path']
        if D.exact_exists(p):
            present += 1
            h = D.sha256(p)
            nsc += r['path'] in scrubbed
            nrp += h != r['sha256'] and repinned.get(r['path']) == h
            if not D.accepted(r['path'], r['sha256'], h, scrubbed, repinned):
                bad.append(r['path'])
    T.check('compendium MANIFEST (shipped part)', not bad and present > 0,
            '%d of %d listed files shipped (%d scrubbed: presence only; %d re-pinned), %d differ%s' % (
                present, len(man), nsc, nrp, len(bad), (': %s' % bad[:3]) if bad else ''),
            'every shipped file equal', 'sha256 of reproduction/MANIFEST.json (the 2026-10-02 archive\'s immutable list); '
            'public/SCRUBBED.txt: presence only; public/RE-PINNED.json: published sha256')
    absent = D.not_shipped()
    present_ns = [r for r in absent if os.path.lexists(PKG/r)]
    T.check('not shipped', not present_ns, '%d files absent%s' % (len(absent) - len(present_ns),
            '; present: %s' % present_ns if present_ns else ''), 'all absent',
            'public/NOT_SHIPPED.txt (the compendium\'s TeX source and the scripts that only build its notes, since 2026-10-17)')
    _, ex, badb = D.compendium_stand_in()
    rec = [r for r in man if r['path'] == ex['original']['path']]
    ok = not badb and rec and rec[0]['sha256'] == ex['original']['sha256']
    T.check('compendium extract', bool(ok), '%d blocks, %d lines; original sha256 %s...' % (
            len(ex['blocks']), sum(b['last_line'] - b['first_line'] + 1 for b in ex['blocks']), ex['original']['sha256'][:12]),
            'blocks equal their sha256; original = MANIFEST entry', 'public/compendium_extract.json: verbatim blocks of '
            'note/LRI_perturbation_compendium.tex (not shipped) at their original lines; its sha256 is the MANIFEST pin')
    lost = PKG/D.LOST['shipped_as']
    rec = [r for r in man if r['path'] == D.LOST['stored']]
    ok = lost.is_file() and rec and D.sha256(lost) == rec[0]['sha256'] == D.LOST['sha256']
    T.check('restored lost file', bool(ok), '%s (%s)' % (D.LOST['shipped_as'], open(lost).read().strip() if lost.is_file() else 'missing'),
            'sha256 of MANIFEST entry %s' % D.LOST['stored'], 'case-colliding file lost by the macOS copy, restored from the original archive')


def section_equations(T, Q, whole):
    eqs = {e['label']: e['tex'] for e in whole['equations']}
    P = D.tex_coefficients(eqs['eq:sr-closed'])
    P8 = D.tex_coefficients(eqs['eq:sr-C8'])
    T.check('eq:sr-closed parsed', sorted(P) == [3, 4, 5, 6, 7], 'C_%s' % ','.join(map(str, sorted(P))), 'C_3..C_7',
            'strict TeX parser (public/dual_lib.py)')
    T.check('eq:sr-C8 parsed', sorted(P8) == [8], 'C_%s' % ','.join(map(str, sorted(P8))), 'C_8', 'strict TeX parser')
    P.update(P8)
    co = {r['n']: r for r in jload(PKG/'data/coefficients.json')['coefficients']}
    for n in range(3, 9):
        js = D.py_poly(co[n]['expression'])
        same = D.to_pi(P[n]) == D.to_pi(js)
        T.check('C%d TeX = coefficients.json' % n, same, D.show(P[n]) if n < 6 else '%d terms, weight <= %d' % (len(P[n]), max(D.weight(m) for m in P[n])),
                co[n]['expression'][:40] + ('...' if len(co[n]['expression']) > 40 else ''),
                'exact: rational coefficients of pi^k x odd zetas (zeta(2k) = r_k pi^(2k)); paper TeX vs compendium registry')
        T.check('C%d rational part' % n, D.rational_part(P[n]) == F(co[n]['rational_part']), str(D.rational_part(P[n])),
                co[n]['rational_part'], 'exact (registry rational_part)')
    note = D.compendium_stand_in()[0]               # the compendium's TeX source, rebuilt from public/compendium_extract.json
    a = note[note.index('The coefficients with completed analytic reductions are'):]
    a = a[a.index('\\begin{align}'):a.index('\\end{align}') + len('\\end{align}')]
    N = D.tex_coefficients(a)
    b = note[note.index('\\boxed{\\begin{aligned}'):]
    b = b[:b.index('\\end{aligned}}') + len('\\end{aligned}}')]
    N.update(D.tex_coefficients(b))
    ok = all(D.to_pi(N[n]) == D.to_pi(P[n]) for n in range(3, 9)) and N[1] == {(): F(-2)} and N[2] == {(): F(1, 2)}
    T.check('paper TeX = compendium closed forms', ok, 'C1..C8 of eq:thermal-main, eq:C8-candidate-main', 'equal',
            'exact; the compendium\'s TeX blocks in public/compendium_extract.json (also C1 = -2, C2 = 1/2 there)')
    rec = jload(PKG/C8REC)
    basis = [D.py_poly(s) for s in rec['basis']]
    cand = {}
    for c, bpoly in zip(rec['candidate_coefficients'], basis):
        cand = D.padd(cand, {k: v*F(c) for k, v in bpoly.items()})
    T.check('C8 TeX = result.json candidate', D.to_pi(cand) == D.to_pi(P[8]), '%d coefficients' % len(basis), 'equal',
            'exact; %s candidate_coefficients x basis' % C8REC)
    c6 = D.py_poly((PKG/'data/archived/C6_closed_form/input_expressions/C6_candidate.expr').read_text())
    T.check('C6 TeX = C6_candidate.expr', D.to_pi(c6) == D.to_pi(P[6]), D.show(c6)[:50] + '...', 'equal',
            'exact; the candidate the C6 input map subtracts (the certificate proves the difference is zero)')
    src = (PKG/'code/archived/C7_closed_form_proof/code/verify_input_map.py').read_text()
    s7 = src.split("candidate='", 1)[1].split("'", 1)[0]
    T.check('C7 TeX = verify_input_map.py candidate', D.to_pi(D.py_poly(s7)) == D.to_pi(P[7]), s7[:40] + '...', 'equal',
            'exact; the closed form the C7 input map and certificate prove')
    return P, co


def section_quoted(T, Q, whole, P, co):
    import mpmath as mp
    mp.mp.dps = 50
    vals = {n: D.evaluate(P[n], mp) for n in P}
    for n in range(3, 9):
        d = abs(vals[n] - mp.mpf(co[n]['decimal']))
        T.check('C%d value (50 digits)' % n, d < mp.mpf('1e-46'), mp.nstr(vals[n], 20), co[n]['decimal'][:22],
                'mpmath 50 digits vs the 70-digit decimal of data/coefficients.json (|diff| < 1e-46: %s)' % mp.nstr(d, 3))
    for n in range(3, 8):
        T.quoted(Q[MACRO[n]], [float(vals[n])], 'closed form of eq:sr-closed at 50 digits')
    rec = jload(PKG/C8REC)
    c8 = Decimal(rec['C8_assembled_without_candidate'])
    T.quoted(Q['\\SRCeight'], [float(c8)], 'numerical record %s C8_assembled_without_candidate (= Cfixed - P6/2)' % C8REC)
    # the registry: orders reached, closed forms, literature
    status = {n: co[n]['status'] for n in co}
    top = max(n for n in co if co[n]['decimal'])
    closed = max(n for n in co if not status[n].startswith('numerically'))
    pub = [n for n in co if status[n] == 'published baseline']
    w = Q['\\SRorderword']
    T.add('\\SRorderword', 'PASS' if WORDS[top] == w['text'] else 'FAIL', '%s (C_1..C_%d in data/coefficients.json)' % (WORDS[top], top),
          w['text'], 'number word of the highest order reached')
    for m, v, rule in (('\\SRorder', top, 'highest order reached'),
                       ('\\SRclosed', closed, 'highest order whose registry status is not "numerically supported candidate"')):
        e = Q[m]
        T.add(m, 'INFO', '%d [%s]' % (v, 'equal' if str(v) == e['text'] else 'differs'), e['text'] + ' (note only)', rule)
    for m in ('\\SRorderLit', '\\SRorderLitword'):
        e = Q[m]
        v = len(pub)
        shown = WORDS[v] if m.endswith('word') else str(v)
        T.add(m, 'INFO', '%s [%s]' % (shown, 'consistent' if shown == e['text'] else 'differs'),
              e['text'] + ('' if e['status'] == 'printed' else ' (note only)'),
              'literature (%s), cited, not recomputed; registry rows marked "published baseline": n = %s' % (LIT, pub))
    lit = co[1]['expression'] == '-2' and co[2]['expression'] == '1/2'
    T.add('C1 = -2, C2 = 1/2', 'INFO', 'registry %s, %s [%s]' % (co[1]['expression'], co[2]['expression'], 'consistent' if lit else 'differs'),
          '-2, 1/2', 'literature (%s), cited, not recomputed' % LIT)
    # tab:sr, d = 1 row: cells and markers
    row = [r for r in whole['tab_sr'] if (r.get('d') == 1 or r['row'].startswith('$d=1$'))][0]['cells']
    want = {1: '\\ptPub{-2}', 2: '\\ptPub{1/2}'}
    for n in range(3, 8):
        want[n] = '\\ptClosed{%s}' % MACRO[n]
    want[8] = '\\ptConj{%s}' % MACRO[8]                                  # conjectured closed form (paper e0558b56)
    marker = {n: ('Pub' if status[n] == 'published baseline' else 'Closed' if status[n].startswith('analytic')
                  else 'Conj' if status[n].startswith('numerically supported') else 'Num') for n in co}
    ok = all(row[n-1] == want[n] and ('\\pt%s{' % marker[n]) in row[n-1] for n in range(1, 9))
    T.check('tab:sr d=1 row', ok, ' '.join(row[n-1].split('{')[0][3:] for n in range(1, 9)),
            'Pub Pub Closed x5 Conj', 'cell n holds the macro of C_n with the marker of its registry status '
            '(published / analytic reduction / numerically supported candidate = conjectured closed form; values checked '
            'in the \\SRC* rows)')
    return vals


def assemble_inputs(base):
    """The inputs of check_assembly.py (verbatim logic): {name: decimal string}, plus the P6 string."""
    inh = base/'C8_zeta_candidate/inherited'
    p8 = jload(inh/'F3_final_100.json')['values']
    f4 = jload(inh/'F4_data_100.json')['values']
    six = jload(inh/'six_new_inputs.json')['coefficients']
    uv = jload(inh/'U_record.json')['values']['U']
    s = {k[5:]: v for k, v in p8.items() if k.startswith('beta_')}
    s.update(six)
    s.update(U=uv, Kv=p8['Kv'], J9=f4['J9'], F1_known=p8['F1_known'],
             P6=jload(base/'C8_zeta_candidate/data/P6_eval100.json')['values']['P6'])
    return s


def c8_from(s, calculate):
    q = {k: F(v) for k, v in s.items() if k not in ('F1_known', 'P6')}
    q['Nd'] = F(s['F1_known']) - 4*F(s['P6'])
    return calculate(q)['C8']


def half_ulp(x):
    d = Decimal(x)
    return F(1, 2)*F(Decimal(1).scaleb(d.as_tuple().exponent))


def section_c8(T, Q, P, work_base):
    import importlib.util
    import mpmath as mp
    rec = jload(PKG/C8REC)
    with localcontext() as ctx:
        ctx.prec = 110
        again = Decimal(rec['Cfixed_inherited_numeric_assembly']) - Decimal(rec['P6_fresh'])/2
        T.check('C8 record = Cfixed - P6/2', abs(again - Decimal(rec['C8_assembled_without_candidate'])) < Decimal('1e-95'),
                str(again)[:40] + '...', rec['C8_assembled_without_candidate'][:40] + '...', 'Decimal, 110 digits (result.json)')
    st = jload(PKG/'data/current_status.json')['C8_numerical'].rstrip('.')
    with localcontext() as ctx:
        ctx.prec = 110
        rq = Decimal(rec['C8_assembled_without_candidate']).quantize(Decimal(st))
    T.check('C8 record vs registry string', str(rq) == st, '%s (record rounded to %d decimals)' % (rq, -Decimal(st).as_tuple().exponent),
            st + '...', 'data/current_status.json C8_numerical (the 31-digit value other folders quote) = the record rounded')
    spec = importlib.util.spec_from_file_location('fj', work_base/'C8_zeta_candidate/code/full_jacobian.py')
    fj = importlib.util.module_from_spec(spec); spec.loader.exec_module(fj)
    s = assemble_inputs(work_base)
    c8 = c8_from(s, fj.calculate)
    with localcontext() as ctx:
        ctx.prec = 110
        c8d = Decimal(c8.numerator)/Decimal(c8.denominator)
    T.check('C8 from its inputs', abs(c8d - Decimal(rec['C8_assembled_without_candidate'])) < Decimal('1e-95'),
            str(c8d)[:40] + '...', 'result.json record', 'verbatim full_jacobian.py (exact Fractions) on the inherited '
            'decimal inputs (as check_assembly.py)')
    floor = F(0)
    exact = [k for k in s if len(Decimal(s[k]).as_tuple().digits) < 20]     # exact rationals printed short (beta_c = -16.0)
    for k in s:
        if k in exact:
            continue
        t = dict(s); t[k] = F(s[k]) + half_ulp(s[k])                     # exact
        floor += abs(c8_from(t, fj.calculate) - c8)
    mp.mp.dps = 120
    cand = D.evaluate(P[8], mp)
    resid = mp.mpf(rec['C8_assembled_without_candidate']) - cand
    fl = mp.mpf(floor.numerator)/floor.denominator
    digits = float(-mp.log10(fl/abs(cand)))
    T.add('C8 record precision', 'INFO', 'printing floor %s (%d decimal inputs, %s exact; %.1f significant digits)' % (
          mp.nstr(fl, 3), len(s) - len(exact), ','.join(exact), digits),
          'about 85 digits (paper: eq:sr-C8 "agrees with the numerical value ... to about 85 digits")',
          'sum over the inputs of |dC8| for half a unit in the last printed digit (85-96 '
          'decimals), exact; inputs printed with < 20 digits are exact rationals; not an interval bound: the numerical '
          'integration error of the inputs is not certified')
    T.check('C8 candidate residual', abs(resid) <= fl, 'record - candidate = %s' % mp.nstr(resid, 4),
            '|residual| <= floor %s' % mp.nstr(fl, 3), 'eq:sr-C8 at 120 digits vs the record: the candidate matches every '
            'digit the record carries (recorded residual %s)' % rec['candidate_difference'][:8])
    T.check('C8 candidate value', abs(cand - mp.mpf(rec['candidate_value'])) < mp.mpf('1e-100'), mp.nstr(cand, 25),
            rec['candidate_value'][:27], 'eq:sr-C8 at 120 digits vs result.json candidate_value')
    # the SRI note (Sec. on C8): "a second evaluation of one input cross-checks about 57 decimal places" (the P6
    # cross-check); the paper quoted it until 1ab2ea1c and no longer does (e0558b56)
    ev = PKG/'data/archived/C8_P6_exact_sources/P6_full'
    p70, p100 = (jload(ev/f)['values']['P6'] for f in ('P6_eval70.json', 'P6_eval100.json'))
    with localcontext() as ctx:
        ctx.prec = 110
        dc8 = abs(Decimal(p70) - Decimal(p100))/2                            # C8 = Cfixed - P6/2
        places = round(-float(dc8.log10()))
    T.check('C8 cross-check (two P6 runs)', places == 57 and Decimal(p100) == Decimal(rec['P6_fresh']),
            '|dC8| = %.2e: %d decimal places' % (float(dc8), places), 'about 57 decimal places (SRI note)',
            'C8 from the 70- and the 100-digit evaluation of P6 (P6_eval70/100.json; the 100-digit one is the record\'s '
            'P6_fresh); places = round(-log10 |dC8|); only P6 is cross-checked, the other inputs are single records')
    # rational part 88
    r = jload(PKG/C8RAT)
    T.check('pi_0 C8 (TeX)', D.rational_part(P[8]) == 88, str(D.rational_part(P[8])), '88', 'rational part of eq:sr-C8')
    T.check('pi_0 C8 (record)', r['C8_weight_zero'] == '88' and r['T4_weight_zero'] == '11' and
            r['independent_trace']['C8_rational'] == '88', 'C8 %s, T4 %s' % (r['C8_weight_zero'], r['T4_weight_zero']), '88, 11',
            C8RAT)
    old = jload(PKG/'data/archived/C8_rational_completion/workspace/R8_work/prior_inputs/T4_rational_reduction.json')['old_rational_beta_inputs']
    coeff = dict(old)
    coeff.update(r['six_additional_inputs_freshly_rechecked'])
    coeff.update(r['new_four_beta_inputs'])
    j = fj.calculate({k: F(v) for k, v in coeff.items()})
    T.check('pi_0 C8 (exact assembly)', j['C8'] == 88 and [str(x) for x in j['trace']] == r['independent_trace']['trace'],
            'C8 %s, trace %s' % (j['C8'], [str(x) for x in j['trace']]), '88, %s' % r['independent_trace']['trace'],
            'verbatim full_jacobian.py on the 35 rational beta inputs (25 old: T4_rational_reduction.json; 10 new: %s)' % C8RAT)
    s1 = F(-111389, 24) + F(3, 4)*F(r['R_tail']) + F(1, 4)*F(r['R9'])
    u = r['new_four_beta_inputs']
    s2 = F(-8411, 6) + F(3, 4)*F(u['U']) + F(u['J9'])/4 + F(u['Nd'])/8 + F(u['Kv'])/32
    T.check('pi_0 C8 (two rational sums)', s1 == 88 and s2 == 88, '%s, %s' % (s1, s2), '88, 88',
            'the independent sums of run_checks.py with R_tail, R9, U, J9, Nd, Kv from %s' % C8RAT)


def run_task(T, name, cmd, cwd, logs, rule, env=None):
    rc, sec = D.run(cmd, cwd, logs/(name + '.txt'), env)
    tail = ''
    try:
        tail = [l for l in (logs/(name + '.txt')).read_text().splitlines() if l.strip()][-1][:70]
    except IndexError:
        pass
    T.check(name, rc == 0, 'exit %d, %.0f s; %s' % (rc, sec, tail), 'exit 0', rule)
    return rc == 0


def section_tasks(T, mode, work):
    comp = work/'compendium'
    logs = work/'logs'
    py = sys.executable
    rep = D.build_work(work)
    T.check('work copy', True, 'layout %d/%d, MANIFEST %d/%d, case-sensitive %s' % (
        rep['layout']['kept'], rep['layout']['virtual_paths'], rep['manifest']['kept'], rep['manifest']['files'], rep['case_sensitive']),
        'built', 'public/dual_lib.py build_work (copy restricted to the shipped files; originals unchanged)')
    run_task(T, 'run_checks.py', [py, 'run_checks.py'], comp, logs,
             'verbatim default check: shipped-file hashes, layout, rational sums 88, 64-bucket P6 sum, decimal Jacobian, P8/J9 maps')
    w = comp/'work'
    if mode == 'test':
        return comp
    run_task(T, 'reproduce.py c8-saved', [py, 'code/reproduce.py', '--task', 'c8-saved'], comp, logs,
             'verbatim: P6 exact sum, assembly, PSLQ recognition of the candidate (115 digits) and its 1e-80 test')
    for f, ref in (('exact_P6_replay.json', 'exact_P6_replay.json'), ('new_full_Jacobian.json', 'new_full_Jacobian.json'),
                   ('candidate_validation.json', 'candidate_validation.json')):
        ok, how, bad = L.compare_json(PKG/'outputs/archived/C8_zeta_candidate/verification'/ref, w/'C8_zeta_candidate/verification'/f,
                                      atol=0, rtol=0)
        T.check('regenerated ' + f, ok, how, 'identical', 'rerun vs outputs/archived/C8_zeta_candidate/verification/' + ref)
    run_task(T, 'reproduce.py c8-rational-algebra', [py, 'code/reproduce.py', '--task', 'c8-rational-algebra'], comp, logs,
             'verbatim reproduce_summary.py: invariants T1..T4, D1..D4, rational full Jacobian 88, C8 residual < 1e-80')
    for rel in ('data/coefficients.json', 'outputs/tables/invariants.json', 'outputs/verification/summary_algebra.json',
                'outputs/tables/thermal_coefficients.csv'):
        a, b = (PKG/rel).read_bytes(), (comp/rel).read_bytes()
        if a == b:
            T.check('regenerated ' + rel.split('/')[-1], True, 'byte-identical', 'identical', 'rerun vs shipped ' + rel)
            continue
        # another SymPy version may print the same expressions differently: compare them exactly as polynomials and
        # the 70-digit decimals to 1e-65
        how, ok = 'differs', False
        if rel.endswith('coefficients.json') or rel.endswith('invariants.json'):
            x, y = json.loads(a), json.loads(b)
            if rel.endswith('coefficients.json'):
                x = {r['n']: r for r in x['coefficients']}; y = {r['n']: r for r in y['coefficients']}
            ok = set(x) == set(y) and all(
                D.to_pi(D.py_poly(x[k]['expression'])) == D.to_pi(D.py_poly(y[k]['expression'])) and
                abs(Decimal(x[k]['decimal']) - Decimal(y[k]['decimal'])) < Decimal('1e-65') for k in x)
            how = 'printing differs; expressions exactly equal, decimals within 1e-65' if ok else 'expressions differ'
        elif rel.endswith('.csv'):
            import csv, io
            x = list(csv.DictReader(io.StringIO(a.decode()))); y = list(csv.DictReader(io.StringIO(b.decode())))
            ok = len(x) == len(y) and all(u['n'] == v['n'] and u['rational_part'] == v['rational_part'] and u['status'] == v['status']
                                          and abs(Decimal(u['decimal']) - Decimal(v['decimal'])) < Decimal('1e-65') for u, v in zip(x, y))
            how = 'printing differs; values within 1e-65' if ok else 'values differ'
        else:
            ok, how, bad = L.compare_json(PKG/rel, comp/rel, atol=0, rtol=0)
        T.check('regenerated ' + rel.split('/')[-1], ok, how, 'identical (or exactly equal up to SymPy printing)',
                'rerun vs shipped ' + rel)
    # certificates: the four commands of reproduce.py --task certificates (prepare baseline and c7-proof first)
    sys.path.insert(0, str(comp/'code'))
    import importlib
    pw = importlib.import_module('prepare_workflows')
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        pw.prepare('baseline'); pw.prepare('c7-proof')
    run_task(T, 'C5 (D3) certificate', [py, w/'D3_analytic_proof/verify_D3_proof_standalone.py'], w/'D3_analytic_proof', logs,
             'verbatim: 170 target words, 476 rows, exact zero residual (reproduce.py certificates, job 1)')
    run_task(T, 'C6 certificate', [py, w/'C6_closed_form/verify_C6_period_identity.py'], w/'C6_closed_form', logs,
             'verbatim: 1,945 words, 56,381 rows, exact zero residual (job 2)')
    if rep['case_sensitive'] and rep['restored']:
        cm = w/'C7_closed_form_proof/code'
        run_task(T, 'C7 input map', [py, cm/'verify_input_map.py', '--report', logs/'C7_input_map.json'], cm, logs,
                 'verbatim: 25 exact beta inputs -> 25,212-word target = assembled C7 minus the closed form (job 3)')
        ok, how, bad = L.compare_json(PKG/'outputs/verification/consolidation/C7_input_map.json', logs/'C7_input_map.json', ignore_keys=('seconds',))
        T.check('C7 input map report', ok, how, 'identical but seconds', 'vs outputs/verification/consolidation/C7_input_map.json')
        run_task(T, 'C6 input map', [py, cm/'verify_C6_input_map.py', '--root', w/'LRI_1d_complete', '--report', logs/'C6_input_map.json'],
                 cm, logs, 'verbatim: 16 beta inputs -> C6 trace; minus C6_candidate.expr = 1,945-word target = certificate targets')
        ok, how, bad = L.compare_json(PKG/'outputs/verification/consolidation/C6_input_map.json', logs/'C6_input_map.json', ignore_keys=('seconds',))
        T.check('C6 input map report', ok, how, 'identical but seconds', 'vs outputs/verification/consolidation/C6_input_map.json')
    else:
        for n in ('C7 input map', 'C6 input map'):
            T.add(n, 'SKIP', 'work directory is case-insensitive', 'case-sensitive work dir',
                  'needs a_check_symbolic.expr next to A_check_symbolic.expr; set WORK= to a case-sensitive directory')
    pf = w/'C7_closed_form_proof/proof'
    if mode != 'full':
        run_task(T, 'C7 certificate w2..w5', [py, pf/'verify_C7_certificate.py', '--prefix', pf/'C7', '--weights', '2', '3', '4', '5'],
                 pf, logs, 'verbatim verifier, weights 2..5 (weight 6, 57 MB, is hosted: replay-full)')
    run_task(T, 'reproduce.py low-integrals', [py, 'code/reproduce.py', '--task', 'low-integrals'], comp, logs,
             'verbatim: closed low-order one-dimensional integral representations at 60 digits')
    if mode == 'full':
        if not D.exact_exists(comp/'data/archived/C7_closed_form_proof/proof/C7.w6.certificate.txt'):
            T.add('reproduce.py certificates', 'FAIL', 'C7.w6.certificate.txt missing', 'hosted file present', 'run make fetch-data first')
        elif not (rep['case_sensitive'] and rep['restored']):
            T.add('reproduce.py certificates', 'SKIP', 'case-insensitive work directory', 'case-sensitive', 'C7 input map needs both a/A files')
        else:
            run_task(T, 'reproduce.py certificates', [py, 'code/reproduce.py', '--task', 'certificates'], comp, logs,
                     'verbatim task: D3, C6, C7 input map, complete C7 certificate (588,878 rows; ~6 min, 0.5 GB)')
        run_task(T, 'reproduce.py c8-positive-check', [py, 'code/reproduce.py', '--task', 'c8-positive-check'], comp, logs,
                 'verbatim: saved P8 maps and a fresh 90-digit evaluation of the P8 positive-weight divergence difference (< 1e-65)')
        run_task(T, 'reproduce.py c8-numerical', [py, 'code/reproduce.py', '--task', 'c8-numerical'], comp, logs,
                 'verbatim: two fresh evaluations of the 66,404-term P6 expression (70 and 100 digits, GMP backend, g++ and '
                 'gmp.h needed); each must agree with the record to 10^-(digits-15)')
    return comp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['test', 'replay', 'full'], default='replay')
    ap.add_argument('--work', default=str(PKG/'.work'))
    a = ap.parse_args()
    work = Path(a.work).resolve()
    t0 = time.time()
    T = L.Table('dual_d1 ' + a.mode)
    Q, whole = L.quoted(PKG.parent.parent/'results'/'quoted_numbers.json')
    section_snapshot(T)
    P, co = section_equations(T, Q, whole)
    section_quoted(T, Q, whole, P, co)
    comp = section_tasks(T, a.mode, work)
    from contextlib import redirect_stdout
    import io
    sys.path.insert(0, str(comp/'code'))
    import prepare_workflows as pw
    with redirect_stdout(io.StringIO()):
        pw.prepare('c8-candidate')
    section_c8(T, Q, P, comp/'work')
    T.add('time', 'INFO', '%.0f s' % (time.time() - t0), '-', 'wall time of this run')
    return T.report(work/('%s_dual_d1.txt' % a.mode))


if __name__ == '__main__':
    sys.exit(main())
