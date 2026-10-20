#!/usr/bin/env python3
"""Replay of c_1 in d = 3 (new tool, 2026-10-15). Run from code/c1_d3/:  python3 public/replay_c1_d3.py [--work DIR]

Recomputes the paper's d = 3 numbers from the shipped inputs (data/inputs/) with the package's verbatim scripts, run
in a copy under <work>/replay/run (nothing in the shipped tree is written):
1. code/workflow/reproduce.py full --from-scratch: the 20-stage workflow (block recurrences, the retained 60-primary
   functional a0, b0, C1 = a0/b0, input errors and denominator box, crossing bases at descendant levels 32/40/48,
   the nominal (gaps 8 even, 7 odd), doubled-padding and weaker-gap (6, 6) envelopes, and the validation stages).
   About 8 min on one core (Xeon 6148 or EPYC 7532).
2. code/workflow/verify.py results on the rerun: the package's own 23 regression checks against outputs/reference/.
3. Every JSON and NPZ output of the rerun against the shipped full-run outputs (outputs/reproduced/), and
   code/workflow/make_assets.py on the rerun: outputs/tables/current_summary.json (the file other folders read, pointer
   /retained/C1) and the CSV tables regenerated and compared with the shipped ones. Tolerances: see TOL below.
4. Quoted numbers (../../results/quoted_numbers.json, package "c1_d3"):
   \\SRthreeCone       C1 of the rerun (rounded half-up to the printed digits);
   \\SRthreeConeRange  [floor_3(l), ceil_3(u)]: the hull [l, u] of the nominal and doubled-padding envelopes, rounded
                      outward to 0.001 (the package's scenario-specific working range [0.269, 0.276]; the paper prints
                      it with four decimals);
   \\SRthreeConeBRRZ   literature (Behan, Rastelli, Rychkov, Zan 2017): cited, not recomputed (INFO);
   tab:sr, d = 3 row;
   \\SRthreeConeImplDev ("two independent implementations agree on c_1 to 10^{-12}"; a bound; note only, so an INFO
   row; each implementation's own row stays PASS/FAIL): the two independent re-implementations of the
   2026-10-07 review (review_indep/, verbatim; they do not import the package), rerun on the shipped
   data/inputs/retained_spectrum.json at the review's finest settings (about 45 s and 25 s): A = own Casimir-recursion
   blocks and quadrature (indep/indep_a0b0_v2.py 128 0.2 44), B = Zamolodchikov-type recursion blocks of Kos, Poland and
   Simmons-Duffin and the other arrangement of the integrals of Behan et al. (physics_review/indep_a0b0.py --NS 34 --nr 160 --na 160 --r0 0.3
   --q 4). Tolerance (the paper's claim, applied to the quoted quantity): |c_1(A) - c_1|, |c_1(B) - c_1| and
   |c_1(A) - c_1(B)| <= 1e-12, with c_1 the package's rerun value; a0 and b0 are reported (INFO). The package's own two
   integrated forms (blocks.integrate vs kernels.py) are an INFO row: a same-domain consistency check.
5. The short-range inputs S = Delta_sigma and E_SR = Delta_epsilon (arXiv:2411.15300v2, Table 1) as used.
Usage: python3 public/replay_c1_d3.py [--work DIR]
"""
import argparse, csv, json, math, re, sys
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c1d3_common as C  # noqa: E402
L = C.L

# Comparison of the rerun with the shipped full-run outputs (outputs/reproduced/, produced on Linux with Python 3.13.5,
# NumPy 2.3.5, SciPy 1.17.0). The package's own regression tolerances are 5e-10 (central coefficients) and 2e-8
# (envelope endpoints, LP-based); the generic comparison of every number uses the looser of the two.
TOL = dict(atol=2e-8, rtol=1e-8)
CHANG = {'S': (0.518148806, 2.4e-08), 'E': (1.41262528, 2.9e-07)}   # arXiv:2411.15300v2, Table 1 (rigorous entries)
TOL_INDEP = 1e-12          # "two independent implementations agree to 10^{-12}" (\\SRthreeConeImplDev): absolute, on c_1
INDEP = [('A', 'review_indep/indep', ['indep_a0b0_v2.py', '{spec}', '128', '0.2', '44'],
          'own Casimir-recursion blocks (sympy) and quadrature; the note\'s arrangement of the integrals'),
         ('B', 'review_indep/physics_review', ['indep_a0b0.py', '{spec}', '--NS', '34', '--nr', '160', '--na', '160',
                                               '--r0', '0.3', '--q', '4'],
          'Zamolodchikov-type recursion blocks of Kos, Poland, Simmons-Duffin; Behan et al. Method 2 arrangement')]


def jl(p):
    return json.loads(Path(p).read_text())


def outward(lo, hi, q='0.001'):
    return (float(Decimal(repr(lo)).quantize(Decimal(q), rounding=ROUND_FLOOR)),
            float(Decimal(repr(hi)).quantize(Decimal(q), rounding=ROUND_CEILING)))


def compare_tree(T, name, shipped_dir, rerun_dir, pattern):
    files = sorted(shipped_dir.glob(pattern))
    bad, worst, missing = [], (0.0, ''), []
    for f in files:
        g = rerun_dir/f.name
        if not g.exists():
            missing.append(f.name); continue
        ok, how, b = L.compare_json(f, g, **TOL)
        d = float(how.split('|diff| ')[1].split(' at ')[0]) if '|diff| ' in how else 0.0
        if d > worst[0]:
            worst = (d, f.name + ':' + how.split(' at ')[-1])
        if not ok:
            bad.append('%s: %s' % (f.name, b[:2]))
    T.check(name, files and not bad and not missing,
            '%d files; largest |diff| %.1e (%s)%s%s' % (len(files), worst[0], worst[1] or '-',
                                                       '; outside tolerance: %s' % bad[:3] if bad else '',
                                                       '; missing: %s' % missing[:3] if missing else ''),
            'atol %g + rtol %g' % (TOL['atol'], TOL['rtol']), 'rerun vs shipped %s' % shipped_dir.relative_to(C.PKG))


def compare_npz(T, shipped_dir, rerun_dir):
    import numpy as np
    files = sorted(shipped_dir.glob('*.npz'))
    bad, worst, ratio = [], 0.0, 0.0
    for f in files:
        a, b = np.load(f), np.load(rerun_dir/f.name) if (rerun_dir/f.name).exists() else None
        if b is None or set(a.files) != set(b.files):
            bad.append(f.name); continue
        for k in a.files:
            x, y = a[k], b[k]
            if x.shape != y.shape:
                bad.append('%s:%s shape' % (f.name, k)); continue
            if x.size:
                d = float(np.max(np.abs(x - y)))
                worst = max(worst, d)
                ratio = max(ratio, float(np.max(np.abs(x - y) / (TOL['atol'] + TOL['rtol']*np.abs(x)))))
                if not np.allclose(y, x, atol=TOL['atol'], rtol=TOL['rtol'], equal_nan=True):
                    bad.append('%s:%s' % (f.name, k))
    T.check('rerun arrays (npz)', files and not bad, '%d files; largest |diff| %.1e, largest |diff|/tolerance %.2f%s' % (
        len(files), worst, ratio, '; outside tolerance: %s' % bad[:4] if bad else ''),
        'atol %g + rtol %g' % (TOL['atol'], TOL['rtol']),
        'crossing bases (levels 32, 40, 48) and the three final LP arrays vs outputs/reproduced/refinement/')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=str(C.PKG/'.work'))
    a = ap.parse_args()
    work = Path(a.work).resolve()/'replay'
    T = L.Table('c1_d3 replay')
    Q, QF = L.quoted(C.SRI/'results'/'quoted_numbers.json')
    run = C.work_copy(work/'run')
    res = run/'outputs'/'replay_full'

    # 1-2. the full workflow and the package's regression suite
    rc, out, dt = C.run(['code/workflow/reproduce.py', 'full', '--from-scratch', '--output', res], run, work/'tmp',
                        work/'reproduce_full.log')
    rec = jl(res/'run_receipt.json') if (res/'run_receipt.json').exists() else {}
    T.check('full workflow from scratch', rc == 0 and rec.get('status') == 'passed' and len(rec.get('steps', [])) == 20
            and not rec.get('cached_dependencies'), 'exit %d, %d steps, %.0f s' % (rc, len(rec.get('steps', [])), dt),
            'exit 0, 20 steps, no cached inputs', 'verbatim reproduce.py full --from-scratch in the copy')
    if rc:
        print(out[-3000:])
        return T.report(work/'replay_c1_d3.txt')
    rc, out, _ = C.run(['code/workflow/verify.py', 'results', '--results', res], run, work/'tmp', work/'verify.log')
    reg = jl(res/'verification'/'regression_checks.json')
    npass = sum(c['passed'] for c in reg['checks'])
    T.check('package regression suite', rc == 0 and npass == len(reg['checks']) == 23,
            '%d/%d passed' % (npass, len(reg['checks'])), '23/23',
            'verbatim verify.py results: retained a0, b0, C1 (5e-10) and the three envelopes (2e-8) vs outputs/reference, '
            'block checks, 34 nonlinear tests, LP optimality, descendant convergence, radial positivity, ...')

    # 3. rerun vs the shipped full-run outputs, and the regenerated summary/tables
    shipped = C.PKG/'outputs'/'reproduced'
    compare_tree(T, 'rerun precision outputs', shipped/'precision', res/'precision', '*.json')
    compare_tree(T, 'rerun refinement outputs', shipped/'refinement', res/'refinement', '*.json')
    compare_npz(T, shipped/'refinement', res/'refinement')
    rc, out, _ = C.run(['code/workflow/make_assets.py', '--results', res], run, work/'tmp', work/'make_assets.log')
    T.check('make_assets.py on the rerun', rc == 0, 'exit %d' % rc, 'exit 0', 'verbatim; regenerates outputs/tables/ in the copy')
    if rc == 0:
        ok, how, bad = L.compare_json(C.PKG/'outputs/tables/current_summary.json', run/'outputs/tables/current_summary.json', **TOL)
        T.check('current_summary.json regenerated', ok, how + ('; %s' % bad if bad else ''), 'atol %g + rtol %g, strings equal' % (TOL['atol'], TOL['rtol']),
                'the file other folders read (pointer /retained/C1), rebuilt from the rerun')
        tabs = ['conditional_intervals.csv', 'family_contributions.csv', 'cutoff_convergence.csv', 'central_progress.csv',
                'crossing_comparison.csv', 'retained_spectrum.csv', 'low_inputs.csv', 'known_input_sensitivities.csv',
                'numerical_stability.csv', 'error_budget.csv', 'alternative_domain_sensitivity.csv']
        bad, worst = [], 0.0
        for t in tabs:
            ok, how = C.compare_table(C.PKG/'outputs/tables'/t, run/'outputs/tables'/t, TOL['atol'], TOL['rtol'])
            w = float(how.split('|diff| ')[1].split(';')[0])
            worst = max(worst, w)
            if not ok:
                bad.append('%s: %s' % (t, how))
        T.check('CSV tables regenerated', not bad, '%d tables; largest |diff| %.1e%s' % (len(tabs), worst, '; differ: %s' % bad[:3] if bad else ''),
                'atol %g + rtol %g' % (TOL['atol'], TOL['rtol']), 'outputs/tables/*.csv rebuilt from the rerun')

    # 4. quoted numbers
    diag = jl(res/'precision'/'diagnostics_results.json')
    cen, ind = diag['central'], diag['independent_folding']
    C1 = cen['C1']
    T.quoted(Q['\\SRthreeCone'], [C1], 'C1 = a0/b0 of the retained 60-primary spectrum (rerun diagnostics_results.json)')
    nom = jl(res/'refinement'/'final_8_7_pad1_summary.json')
    pad = jl(res/'refinement'/'final_8_7_pad2_summary.json')
    lo, hi = outward(min(nom['interval'][0], pad['interval'][0]), max(nom['interval'][1], pad['interval'][1]))
    T.quoted(Q['\\SRthreeConeRange'], [lo, hi],
             'hull of the nominal [%.6f, %.6f] and doubled-padding [%.6f, %.6f] envelopes, rounded outward to 0.001'
             % (*nom['interval'], *pad['interval']))
    summ = jl(C.PKG/'outputs/tables/current_summary.json')
    T.check('working range = package\'s range', [lo, hi] == summ['recommended_working_summary']['interval'],
            '[%g, %g]' % (lo, hi), str(summ['recommended_working_summary']['interval']),
            'outputs/tables/current_summary.json /recommended_working_summary/interval (chosen by the authors; the rule above reproduces it)')
    T.check('gap assumption of the range', (nom['even_gap'], nom['odd_gap'], pad['even_gap'], pad['odd_gap']) == (8, 7, 8, 7)
            and jl(C.PKG/'data/inputs/assumptions.json')['omitted_even_gap'] == 8
            and jl(C.PKG/'data/inputs/assumptions.json')['omitted_odd_gap'] == 7,
            'even %g, odd %g' % (nom['even_gap'], nom['odd_gap']), 'even 8, odd 7',
            'the range assumes no unlisted even primary below 8 and no unlisted odd primary below 7 above the '
            'retained spectrum of Simmons-Duffin 2016 (numbers.tex comment of \\SRthreeConeRange)')
    weak = jl(res/'refinement'/'final_6_6_pad1_summary.json')['interval']
    T.add('weaker gaps (6, 6)', 'INFO', '[%.6f, %.6f]' % tuple(weak), 'outside the range',
          'sensitivity scenario of the package (not quoted): the range is conditional on the gaps')
    e = Q['\\SRthreeConeBRRZ']
    T.add('\\SRthreeConeBRRZ', 'INFO', 'C1 = %.4f, |C1 - 0.27| = %.4f <= 0.04' % (C1, abs(C1 - 0.27)), e['text'],
          'literature: C. Behan, L. Rastelli, S. Rychkov, B. Zan, J. Phys. A 50 (2017) 354002 [arXiv:1703.05325]; '
          'cited, not recomputed')
    row = [r for r in QF['tab_sr'] if (r.get('d') == 3 or r['row'].startswith('$d=3$'))]
    ok = len(row) == 1 and row[0]['cells'][0] == '\\ptNum{\\SRthreeCone}' and not any(row[0]['cells'][1:])
    st = L.matches([C1], Q['\\SRthreeCone']['text'])[0]
    T.check('tab:sr, d = 3 row', ok and st, row[0]['cells'][:2] if row else 'row missing', "['\\ptNum{\\SRthreeCone}', '']",
            'c_1 cell = \\SRthreeCone (new, numerical), as recomputed above; c_2..c_8 empty')
    spec = C.PKG/'data'/'inputs'/'retained_spectrum.json'
    got, ok_all = {}, True
    for name, sub, args, what in INDEP:
        rc, out, dt = C.run([a.replace('{spec}', str(spec)) for a in args], run/sub, work/'tmp', work/('indep_%s.log' % name))
        res_ = None
        for line in reversed(out.splitlines()):
            if line.startswith('{') and '"C1"' in line:
                res_ = json.loads(line); break
        ok = rc == 0 and res_ is not None
        if ok:
            got[name] = res_
            d = abs(res_['C1'] - C1)
            ok = d <= TOL_INDEP
            T.check('independent implementation %s' % name, ok, 'c_1 %.17g (|diff| %.1e), %.0f s' % (res_['C1'], d, dt),
                    '|c_1 - %.17g| <= %g' % (C1, TOL_INDEP), '%s: %s (verbatim, review 2026-10-07)' % (sub, what))
            T.add('implementation %s: a0, b0' % name, 'INFO', 'rel. diff a0 %.1e, b0 %.1e' % (
                abs(res_['a0'] - cen['a']) / cen['a'], abs(res_['b0'] - cen['b']) / cen['b']),
                'a0 %.17g, b0 %.17g' % (cen['a'], cen['b']), 'against the package rerun; reported, not a criterion')
        else:
            T.check('independent implementation %s' % name, False, 'exit %d, no result line' % rc, 'exit 0', sub)
        ok_all = ok_all and ok
    # \SRthreeConeImplDev ("two implementations ... agree on C^SR_1(3) to 10^{-12}"; note only): a bound, not a rounded value: both re-implementations and their difference must lie
    # within it (absolute, on c_1). PASS/FAIL while printed, INFO otherwise.
    e = Q.get('\\SRthreeConeImplDev')
    rule = ('two independent implementations agree on c_1 to the printed bound: max |c_1 - package| and '
            '|c_1(A) - c_1(B)| <= bound (absolute)')
    if len(got) == 2:
        dab = abs(got['A']['C1'] - got['B']['C1'])
        dmax = max(abs(g['C1'] - C1) for g in got.values())
        shown = 'max |c_1 - package| %.1e; |c_1(A) - c_1(B)| %.1e' % (dmax, dab)
        if e is None:
            T.check('two independent implementations', ok_all and dab <= TOL_INDEP, shown, '<= %g' % TOL_INDEP,
                    'SRI note Table 2: ' + rule)
        else:
            m = re.fullmatch(r'10\^\{(-?\d+)\}', e['text'].strip())
            bound = 10.0 ** int(m.group(1)) if m else None
            ok = bound is not None and ok_all and max(dab, dmax) <= bound
            st = ('PASS' if ok else 'FAIL') if e['status'] == 'printed' else 'INFO'
            T.add(e['macro'], st, shown, e['text'] + ('' if e['status'] == 'printed' else ' (note only)'), rule)
    elif e is not None and e['status'] == 'printed':
        T.check(e['macro'], False, 'implementations missing (%d of 2 ran)' % len(got), e['text'], rule)
    rel = {k: abs(cen[k] - ind[k + '0' if k in 'ab' else k]) / abs(cen[k]) for k in ('a', 'b', 'C1')}
    T.add('same-domain consistency check', 'INFO', 'rel. diff a0 %.1e, b0 %.1e, C1 %.1e' % (rel['a'], rel['b'], rel['C1']),
          'package internal', 'blocks.integrate vs kernels.py, the package\'s two integrated forms on the same folded '
          'domain (diagnostics_results.json, key independent_folding); not an independent validation of the folding')

    # 5. inputs
    low = jl(C.PKG/'data/inputs/low_inputs.json')['values']
    spec = jl(C.PKG/'data/inputs/retained_spectrum.json')
    sig = [r for r in spec if r['sector'] == 'odd' and r['ell'] == 0 and r['Delta'] < 1]
    eps = [r for r in spec if r['sector'] == 'even' and r['ell'] == 0 and 1 < r['Delta'] < 2]
    for k, rows, nm in (('S', sig, 'Delta_sigma'), ('E', eps, 'Delta_epsilon (E_SR)')):
        v, err = CHANG[k]
        ok = low[k]['value'] == v and low[k]['quoted_error'] == err and len(rows) == 1 and rows[0]['Delta'] == v
        T.check('input ' + nm, ok, '%r(%g)' % (low[k]['value'], low[k]['quoted_error']), '%r(%g)' % (v, err),
                'data/inputs/low_inputs.json and retained_spectrum.json vs Chang et al., arXiv:2411.15300v2 Table 1')
    ok = abs(summ['retained']['C1'] - C1) <= 5e-10 and summ['retained']['C1'] == jl(shipped/'precision/diagnostics_results.json')['central']['C1']
    T.check('published value /retained/C1', ok, '%.17g' % summ['retained']['C1'], '%.17g (rerun)' % C1,
            'outputs/tables/current_summary.json: equals the shipped full run exactly and the rerun within 5e-10')
    return T.report(work/'replay_c1_d3.txt')


if __name__ == '__main__':
    sys.exit(main())
