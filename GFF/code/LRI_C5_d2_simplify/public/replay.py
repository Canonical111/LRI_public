#!/usr/bin/env python3
"""Replay of the d = 2 closed forms of L2, K2 and C5(2) (note Sections 1, 17.2; HEAD fa71533) for LRI_C5_d2_simplify.

Run from the package folder (GFF/code/LRI_C5_d2_simplify) as `make -f public.mk replay`. Nothing is summed again.

Steps:
1. Record pins. The sha256 of the shipped records (confirm_dps70.json, confirm_dps18.json, L2_factorized.json,
   K2_factorized.json) must equal the pins in ../../results/closed_forms_2/closed_forms_2.json.
2. Production assembly. The package's own parallel_eval.py runs at 70 digits in a work copy (public/out/work/), with its
   per-sum cache prefilled from the 50 single sums stored in confirm_dps70.json. It therefore computes no sum and only
   re-runs its own assembly of L2 (48-term factorization), K2 (81-term factorization plus the theta -> 0 strip limit) and
   the ten identity checks. The result is compared with the record.
3. Recorded checks. The residuals of job 567346 that the note quotes (4.5e-69 for L2, 2.0e-70 for K2) are read from the
   record and compared at the printed digits.
4. Closed forms. L2, K2 and C5(2) are evaluated at 80 digits with mpmath (public/closed_forms_d2.py), in all their stated
   forms, and compared with the record, with the owned 70-digit values in the results JSON, and with every decimal the
   note and the paper quote for them (correct rounding at the printed digits). Cross-checks of numbers owned by other
   units (P4(2), Q2, P5(2), C2..C4(2); C5(2) and K2 in Sections 20-21) are marked [cross-check].
5. Independent spectral check. The residuals 1.7e-79 and 3.1e-62 are read from C63d's record
   ../LRI_C5_d3/wf_d2check/d2check_results.json (sha256 pinned). Its L2, K2 and P4(2) are compared with the closed forms.

Tolerances:
- The stored singles have 70 significant digits (they were computed at 80). The re-run assembly therefore reproduces L2
  and K2 to about 1e-67 relative, and its identity residuals rise from 1e-69..1e-82 (record) to at most 2e-67 at 70-digit
  input. Bound: 1e-65 relative or absolute.
- Re-written singles, a and B+- must be string-identical to the record; b may differ in its last (70th) digit, bound 1e-68.
- Closed-form evaluations at 80 digits must agree among their forms to 1e-75 and with the owned 70-digit strings to 1e-68.
  mpmath's |z| = 1 hypergeometric acceleration may move the last digits between versions.
- Quoted decimals must be correctly rounded at the printed digits. Quoted residuals are compared as strings at the
  printed significant digits.
Checked with Python 3.10.11 and mpmath 1.2.1 (macOS), and with mpmath 1.3.0 and 1.4.1 for steps 4-5.
"""
import argparse, ast, json, os, sys, time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / 'public'))
import mpmath as mp  # noqa: E402
from cf2common import ROWS, row, quoted, quoted_sci, sha, load, run_pinned, report, versions  # noqa: E402
from closed_forms_d2 import evaluate  # noqa: E402

RECORD = 'confirm_dps70.json'


def cache_name(key):
    # the cache file name used by parallel_eval.py (fn(s) there), from repr() of the single-sum key
    return ''.join(c if c.isalnum() or c in '-+' else '_' for c in key) + '.txt'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--results', type=Path, default=PKG / '../../results/closed_forms_2/closed_forms_2.json')
    ap.add_argument('--d2check', type=Path, default=PKG / '../LRI_C5_d3/wf_d2check/d2check_results.json')
    ap.add_argument('--out', type=Path, default=PKG / 'public/out')
    a = ap.parse_args()
    res = load(a.results)
    pins = res['record_sha256']

    # 1. record pins
    for f in ('confirm_dps70.json', 'confirm_dps18.json', 'L2_factorized.json', 'K2_factorized.json'):
        h = sha(PKG / f); want = pins[f'LRI_C5_d2_simplify/{f}']
        row(f'sha256 of {f} as pinned', h[:16], want[:16], h == want)
    rec = load(PKG / RECORD)

    # 2. the package's own assembly from the stored singles
    def prefill(wd):
        c = wd / 'cache_dps70'; c.mkdir()
        for k, v in rec['singles'].items():
            (c / cache_name(k)).write_text(v)
    rc, out, wd, secs, nsub = run_pinned(PKG, 'parallel_eval.py', ['70'], work='assembly_dps70', prepare=prefill)
    row('parallel_eval.py 70 (record singles prefilled) exits 0', rc, 0, rc == 0, f'{secs:.1f} s')
    row('all 50 single sums taken from the record, none recomputed', '50 cached, 0 to compute' in out, True,
        '50 cached, 0 to compute' in out)
    new = load(wd / RECORD)
    same = sum(new['singles'].get(k) == v for k, v in rec['singles'].items())
    row('re-written single sums string-identical to the record', f'{same}/{len(rec["singles"])}', '50/50', same == 50 == len(new['singles']))
    for k in ('a', 'B-', 'B+'):
        row(f'{k} string-identical to the record', new[k] == rec[k], True, new[k] == rec[k])
    mp.mp.dps = 90
    rb = abs(mp.mpf(new['b']) / mp.mpf(rec['b']) - 1)
    row('b equals the record (last digit)', mp.nstr(rb, 2), '<= 1e-68', rb <= mp.mpf('1e-68'))
    for k in ('L2', 'K2'):
        d = abs(mp.mpf(new['checks'][k]) / mp.mpf(rec['checks'][k]) - 1)
        row(f'{k} re-assembled = record (relative)', mp.nstr(d, 2), '<= 1e-65', d <= mp.mpf('1e-65'))
    for k, v in new['checks'].items():
        if k in ('L2', 'K2'):
            continue
        x = abs(mp.mpf(v))
        row(f're-assembled residual |{k}|', mp.nstr(x, 2), '<= 1e-65', x <= mp.mpf('1e-65'), f'record {mp.nstr(mp.mpf(rec["checks"][k]), 2)}')

    # 3. the record of job 567346 (computed at 80 digits)
    row('record precision (dps)', rec['dps'], 70, rec['dps'] == 70)
    for k, v in rec['checks'].items():
        if k not in ('L2', 'K2'):
            x = abs(mp.mpf(v))
            row(f'recorded residual |{k}|', mp.nstr(x, 2), '<= 1e-68', x <= mp.mpf('1e-68'))
    quoted_sci('note l.3885: L2 residual of the 70-digit evaluation', mp.mpf(rec['checks']['L2+2log2*P4(=8pi^3ab)']), '4.5e-69')
    quoted_sci('note l.3885: K2 residual of the 70-digit evaluation', mp.mpf(rec['checks']['K2-(32G^2-28z3log2)']), '2.0e-70')

    # 4. closed forms at 80 digits
    t0 = time.time(); v = evaluate(80); tcf = time.time() - t0
    mp.mp.dps = 90
    for name, x, y in (('L2: -2 log2 P4(2) = -(A/2) P4(2)', v['L2'], v['L2_form_A']),
                       ('L2: -2 log2 P4(2) = -log2 (B-^2-B+^2)/(2pi^3)', v['L2'], v['L2_form_B']),
                       ('K2: 32G^2-28 zeta3 log2 = [(psi1(1/4)-psi1(3/4))^2/4 + AU]/2', v['K2'], v['K2_form_psi']),
                       ('C5(2): gc:C5twoClosed = gc:d2coefficients with L2, K2 inserted', v['C5_2'], v['C5_2_from_gc_d2coefficients']),
                       ('-1536 K2 = -768 (Phi2 + A U), Phi2 = 64 G^2', -1536 * v['K2'], -768 * (64 * v['Catalan'] ** 2 + v['A'] * v['U'])),
                       ('384 A P4 - 576 L2 = 672 A P4', 384 * v['A'] * v['P4_2'] - 576 * v['L2'], 672 * v['A'] * v['P4_2'])):
        d = abs(x - y) / abs(y)
        row(name, mp.nstr(d, 2), '<= 1e-75', d <= mp.mpf('1e-75'), f'80 digits, {tcf:.1f} s')
    for k in ('L2', 'K2', 'C5_2'):
        d = abs(v[k] / mp.mpf(res['values_70_digits'][k]) - 1)
        row(f'{k} at 80 digits = owned 70-digit value (results JSON)', mp.nstr(d, 2), '<= 1e-68', d <= mp.mpf('1e-68'))
    for k, f in (('L2', 'L2+2log2*P4(=8pi^3ab)'), ('K2', 'K2-(32G^2-28z3log2)')):
        d = abs(mp.mpf(rec['checks'][k]) - v[k])
        row(f'record {k} - closed form (absolute)', mp.nstr(d, 2), '<= 1e-67', d <= mp.mpf('1e-67'))
    quoted('note l.101 (Sec 1 table): C5(2)', v['C5_2'], '-38.833645896')
    quoted('note l.3778 (Sec 16.7 table): C5(2)', v['C5_2'], '-38.833645896')
    quoted('note l.3896: L2 to fifty digits', v['L2'], '-347.24915312320113105847678307522316920816760199487')
    quoted('note l.3897: K2 to fifty digits', v['K2'], '3.5181091385902522416490901703077395226226728094710')
    quoted('note l.3915: C5(2)', v['C5_2'], '-38.83364589622536055293698')
    quoted('paper numbers.tex \\CfiveTwo', v['C5_2'], '-38.833645896')
    quoted('C5(2) to 25 digits (note l.3915; printed by the paper before f496d39a)', v['C5_2'], '-38.83364589622536055293698')
    # cross-checks of numbers owned elsewhere
    X = '[cross-check] '
    quoted(X + 'note l.3895: P4(2) to fifty digits (closed_forms_general)', v['P4_2'], '250.48731558186728553185175688791140716835571092358')
    quoted(X + 'note l.3802: Q2 (closed_forms_general)', v['Q2'], '12.7713811986469576577497636845240084220372849859347')
    quoted(X + 'note l.6917: C5(2) end to end (reduction_d)', v['C5_2'], '-38.8336458962253605529369824675329232')
    quoted(X + 'note l.6996: C5(2) (reduction_d)', v['C5_2'], '-38.8336458962')
    quoted(X + 'note l.7612: K2 = K_d at d=2 (reduction_d)', v['K2'], '3.5181091385902522416490901703077')
    quoted(X + 'note l.100 / numbers.tex \\CfourTwo: C4(2) (closed_forms_general)', v['C4_2'], '5.048868431')
    quoted(X + 'note l.99: C3(2) (closed_forms_general)', v['C3_2'], '-0.874850012653')
    quoted(X + 'Q2 to 29 decimals (printed by the paper before f496d39a)', v['Q2'], '12.77138119864695765774976368452')
    quoted(X + 'P4(2) to 25 digits (printed by the paper before f496d39a)', v['P4_2'], '250.4873155818672855318518')
    quoted(X + 'P5(2) to 25 digits (printed by the paper before f496d39a)', v['P5_2'], '1548.082640233120615132439')
    quoted(X + 'C3(2) to 25 digits (printed by the paper before f496d39a)', v['C3_2'], '-0.8748500126526336895122636')
    quoted(X + 'C4(2) to 25 digits (printed by the paper before f496d39a)', v['C4_2'], '5.048868431354847007612317')
    for k, key in (('B-', 'Bm'), ('B+', 'Bp')):
        d = abs(mp.mpf(rec[k]) / v[key] - 1)
        row(X + f'{k}: Euler-Maclaurin record (70 digits) = mpmath 4F3(1) value', mp.nstr(d, 2), '<= 1e-68', d <= mp.mpf('1e-68'))

    # 5. the independent spectral evaluation (C63d, GFF/code/LRI_C5_d3/wf_d2check)
    p = a.d2check
    if p.exists():
        h = sha(p); want = pins['LRI_C5_d3/wf_d2check/d2check_results.json']
        row('sha256 of LRI_C5_d3/wf_d2check/d2check_results.json as pinned', h[:16], want[:16], h == want)
        s = load(p)
        quoted_sci('note l.3892: independent spectral L2 residual (run4)', mp.mpf(s['L2_plus_2log2P4']['run4']), '1.7e-79')
        quoted_sci('note l.3892: independent spectral K2 residual (run4)', mp.mpf(s['K2_minus_32G2_plus_28z3log2']['run4']), '3.1e-62')
        for k, tol in (('L2', '1e-78'), ('K2', '1e-61')):
            d = abs(mp.mpf(s[k]) - v[k])
            row(f'spectral {k} (d2check_results.json) - closed form', mp.nstr(d, 2), f'<= {tol}', d <= mp.mpf(tol))
        d = abs(mp.mpf(s['P4_2_closed_form']) - v['P4_2'])
        row(X + 'spectral record P4(2) - closed form', mp.nstr(d, 2), '<= 1e-55', d <= mp.mpf('1e-55'))
    else:
        row('LRI_C5_d3/wf_d2check/d2check_results.json present (sibling package GFF/code/LRI_C5_d3)', 'missing', 'present', False)

    return report(a.out, 'replay', versions())


if __name__ == '__main__':
    sys.exit(main())
