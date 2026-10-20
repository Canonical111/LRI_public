#!/usr/bin/env python3
"""Public replay of LRI_C5_d3: C5(3), the d = 3 masters K3, L3, Z3 and the d = 3 coefficients C2..C5.

Added for the public release (2026-10-13); not part of the research package. Run from the package folder
GFF/code/LRI_C5_d3 (or through `make -f public.mk replay`):

    python3 public/replay_c5_d3.py [--work .work] [--quoted ../../results/closed_forms_3/LRI_C5_d3_quoted.json]

What it does (about 10 s on one core, mpmath only):
  E  reruns the package's own scripts, unchanged, in a copy under <work>/replay/ and compares their output with the
     shipped records: pslq_d3.py (masters_d3.json from spectral runs A and B), compute_c5.py (c5_value.json),
     hp_combine.py (run_C_combined.json from the two Cauchy circles of run C), wf_L3/final_form.py and
     wf_L3/tdform.py (the 160-digit L3 constants from the stored Cauchy circle pA_dps170.json), wf_Z3/derive.py
     (the 250-digit Z3 data from the stored circles circA2/circB2);
  Q  recomputes every quoted number of LRI_C5_d3_quoted.json from the shipped records (high-precision assembly of
     gs:C5 at q = 3/4, the general C2..C4 formulas, gdk:Kr3 for r3(3)) and compares with the quoted strings;
  A  checks the accuracy statements (430 digits of K3, agreement of independent routes);
  F  checks the printed d = 3 formulas (Q3, Z3, S'(3/2), L3, P4(3), b4 and the reduced form of C5(3)) with the
     stored values, and the d = 3 specialization of gs:C5 symbolically (SymPy).
Writes <work>/replay/REPLAY_c5_d3.md and <work>/replay/reproduced_c5_d3.json; exits 1 on any FAIL.
A check marked SKIP needs a file of another package (LRI_C5_general_d) that is not present; SKIP is not a failure.
"""
import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import mpmath as mp

PKG = Path(__file__).resolve().parents[1]


# ----------------------------------------------------------------------------------------------- helpers
class Report:
    def __init__(self):
        self.rows = []

    def add(self, group, name, status, value, expected, tol, source):
        self.rows.append(dict(group=group, name=name, status=status, value=str(value), expected=str(expected),
                              tol=str(tol), source=source))
        print('%-4s %-6s %-46s %s' % (group, status, name, value if len(str(value)) < 60 else str(value)[:57] + '...'),
              flush=True)

    def check(self, group, name, ok, value, expected, tol, source):
        self.add(group, name, 'PASS' if ok else 'FAIL', value, expected, tol, source)

    def failed(self):
        return [r for r in self.rows if r['status'] == 'FAIL']

    def write(self, path, header):
        n = {s: sum(r['status'] == s for r in self.rows) for s in ('PASS', 'FAIL', 'SKIP')}
        lines = ['# LRI_C5_d3 public replay', '', header, '',
                 'Result: **%s** (%d PASS, %d FAIL, %d SKIP)' % ('FAIL' if n['FAIL'] else 'PASS', n['PASS'], n['FAIL'],
                                                                n['SKIP']), '',
                 '| group | check | status | value | expected | tolerance | source |', '|---|---|---|---|---|---|---|']
        for r in self.rows:
            cells = [r[k].replace('|', '/') for k in ('group', 'name', 'status', 'value', 'expected', 'tol', 'source')]
            lines.append('| ' + ' | '.join(cells) + ' |')
        Path(path).write_text('\n'.join(lines) + '\n')


def num(s):
    """Real part of a stored number: plain decimal strings or '(re + im j)' strings, at the current precision."""
    s = str(s).strip()
    if s.startswith('('):
        return mp.re(mp.mpmathify(s.replace(' ', '')))
    return mp.mpf(s)


def load(p):
    return json.load(open(p))


def short(x, n=25):
    return mp.nstr(x, n)


def last_unit(quoted):
    """One unit in the last quoted digit."""
    s = quoted.lstrip('+-')
    if '.' in s:
        return mp.mpf(10) ** (-(len(s.split('.')[1])))
    return mp.mpf(1)


def sig_digits(quoted):
    s = quoted.lstrip('+-').replace('.', '').lstrip('0')
    return len(s)


def rounds_to(x, quoted):
    """Correct rounding to the quoted number of significant digits, as a string comparison."""
    n = sig_digits(quoted)
    return mp.nstr(x, n, min_fixed=-mp.inf, max_fixed=mp.inf, strip_zeros=False) == quoted.lstrip('+') or \
        mp.nstr(x, n, strip_zeros=False) == quoted.lstrip('+')


def two_sig(x):
    return mp.nstr(x, 2, min_fixed=0, max_fixed=0)


def run(script, args, cwd):
    p = subprocess.run([sys.executable, script] + list(args), cwd=str(cwd), capture_output=True, text=True)
    return p


def copy(src_rel, dst_dir):
    dst = Path(dst_dir) / Path(src_rel).name
    shutil.copy2(PKG / src_rel, dst)
    return dst


# ----------------------------------------------------------------------------------------------- E: script reruns
def reruns(rep, W):
    bundle = W / 'bundle'
    gd3 = bundle / 'lri_d3_reduction_update' / 'verification' / 'general_d3'
    gd3.mkdir(parents=True)
    shutil.copy2(PKG / 'inputs/general_d3/period_values.json', gd3 / 'period_values.json')

    # E1 pslq_d3.py: masters_d3.json and pslq_d3.log from the spectral runs A and B
    d = W / 'pslq'; d.mkdir()
    for f in ('pslq_d3.py', 'run_A_dps50.json', 'run_B_dps56.json'):
        copy(f, d)
    t = time.time(); p = run('pslq_d3.py', ['run_A_dps50.json', 'run_B_dps56.json', str(bundle)], d)
    if p.returncode:
        rep.check('E', 'pslq_d3.py runs', False, 'rc=%d' % p.returncode, 'rc=0', '-', p.stderr[-300:]); return
    (d / 'pslq_d3_rerun.log').write_text(p.stdout)
    same = filecmp.cmp(d / 'masters_d3.json', PKG / 'masters_d3.json', shallow=False)
    a, b = load(d / 'masters_d3.json'), load(PKG / 'masters_d3.json')
    dev = max(abs(mp.mpf(a[k]) - mp.mpf(b[k])) for k in ('K3', 'L3', 'Z3', 'N3'))
    rep.check('E', 'pslq_d3.py -> masters_d3.json', same or dev <= mp.mpf('1e-50'),
              'byte-identical' if same else 'max diff %s' % short(dev, 3), 'shipped masters_d3.json',
              'bytes, else 1e-50 abs', 'pslq_d3.py run_A_dps50.json run_B_dps56.json (%.1f s)' % (time.time() - t))
    logsame = p.stdout == (PKG / 'pslq_d3.log').read_text()
    rep.add('E', 'pslq_d3.py stdout = pslq_d3.log', 'PASS' if logsame else 'INFO',
            'identical' if logsame else 'differs (PSLQ output may depend on the mpmath version)', 'pslq_d3.log', 'text',
            'informational; the masters are compared above')

    # E2 compute_c5.py: c5_value.json from masters_d3.json and the 90-digit period values
    d = W / 'compute'; d.mkdir()
    for f in ('compute_c5.py', 'masters_d3.json'):
        copy(f, d)
    p = run('compute_c5.py', [str(bundle)], d)
    ok = p.returncode == 0
    if ok:
        same = filecmp.cmp(d / 'c5_value.json', PKG / 'c5_value.json', shallow=False)
        dev = abs(mp.mpf(load(d / 'c5_value.json')['C5']) - mp.mpf(load(PKG / 'c5_value.json')['C5']))
        ok = same or dev <= mp.mpf('1e-55')
        val = 'byte-identical' if same else 'diff %s' % short(dev, 3)
    else:
        val = 'rc=%d %s' % (p.returncode, p.stderr[-200:])
    rep.check('E', 'compute_c5.py -> c5_value.json', ok, val, 'shipped c5_value.json', 'bytes, else 1e-55 abs',
              'compute_c5.py (N3 form of C5(3), 60 digits)')

    # E3 hp_combine.py: run_C_combined.json from the two Cauchy circles of spectral run C
    d = W / 'runC'; d.mkdir()
    for f in ('hp_combine.py', 'run_C_b.json', 'run_C_t.json'):
        copy(f, d)
    p = run('hp_combine.py', ['run_C_b.json', 'run_C_t.json', 'run_C_combined.json'], d)
    ok = p.returncode == 0
    if ok:
        same = filecmp.cmp(d / 'run_C_combined.json', PKG / 'run_C_combined.json', shallow=False)
        a, b = load(d / 'run_C_combined.json'), load(PKG / 'run_C_combined.json')
        with mp.workdps(120):
            dev = max(abs(num(a[k]) - num(b[k])) for k in ('K3', 'L3', 'Z3'))
        ok = same or dev <= mp.mpf('1e-100')
        val = 'byte-identical' if same else 'diff %s' % short(dev, 3)
    else:
        val = 'rc=%d %s' % (p.returncode, p.stderr[-200:])
    rep.check('E', 'hp_combine.py -> run_C_combined.json', ok, val, 'shipped run_C_combined.json',
              'bytes, else 1e-100 abs', 'hp_combine.py run_C_b.json run_C_t.json (110-digit spectral run C)')

    # E4, E5 wf_L3: final_form.py and tdform.py on the stored 170-digit Cauchy circle
    d = W / 'wf_L3'; d.mkdir()
    for f in ('final_form.py', 'tdform.py', 'load.py', 'pieces.py', 'gen3.py', 'pA_dps170.json'):
        copy('wf_L3/' + f, d)
    ref = load(PKG / 'wf_L3/L3_final_values.json')
    p = run('final_form.py', ['pA_dps170.json', 'L3_final_values.json'], d)
    if p.returncode:
        rep.check('E', 'wf_L3/final_form.py runs', False, 'rc=%d' % p.returncode, 'rc=0', '-', p.stderr[-300:])
    else:
        new = load(d / 'L3_final_values.json')
        bad = [k for k in new['values'] if new['values'][k] != ref['values'].get(k)]
        bad += [k for k in new['checks'] if new['checks'][k] != ref['checks'].get(k)]
        rep.check('E', 'wf_L3/final_form.py -> L3 constants', not bad,
                  '%d values, %d checks identical' % (len(new['values']), len(new['checks'])) if not bad else 'differ: %s' % bad,
                  'wf_L3/L3_final_values.json (same strings)', 'identical 165-digit strings',
                  'final_form.py pA_dps170.json (L3, P4, X0, Xh, a4, b4, c_k, dH, da, Phat_prime, ...)')
        p = run('tdform.py', ['pA_dps170.json'], d)          # adds the td-sample derivatives to L3_final_values.json
        if p.returncode:
            rep.check('E', 'wf_L3/tdform.py runs', False, 'rc=%d' % p.returncode, 'rc=0', '-', p.stderr[-300:])
        else:
            new = load(d / 'L3_final_values.json')
            keys = ['NX0dot', 'NXhdot', 'ds', 'dPdb_tdform']
            bad = [k for k in keys if new['values'][k] != ref['values'][k]]
            if new['checks']['td_form_residual'] != ref['checks']['td_form_residual']:
                bad.append('td_form_residual')
            rep.check('E', 'wf_L3/tdform.py -> dPdb_tdform etc.', not bad, 'identical' if not bad else 'differ: %s' % bad,
                      'wf_L3/L3_final_values.json', 'identical 165-digit strings', 'tdform.py pA_dps170.json')

    # E7 wf_d2check/combine_d2.py: the d = 2 spectral check of C62d's closed forms (note 17.2, l.3892)
    d = W / 'wf_d2check'; d.mkdir()
    for f in ('combine_d2.py', 'run4_b.json', 'run4_t.json', 'targets_dps120.json'):
        copy('wf_d2check/' + f, d)
    p = run('combine_d2.py', ['run4_b.json', 'run4_t.json', 'targets_dps120.json', 'run4_combined.json'], d)
    if p.returncode:
        rep.check('E', 'wf_d2check/combine_d2.py runs', False, 'rc=%d' % p.returncode, 'rc=0', '-', p.stderr[-300:])
    else:
        same = filecmp.cmp(d / 'run4_combined.json', PKG / 'wf_d2check/run4_combined.json', shallow=False)
        res = load(d / 'run4_combined.json')['residuals']
        rep.check('E', 'wf_d2check/combine_d2.py run 4', same, 'byte-identical' if same else 'differs',
                  'wf_d2check/run4_combined.json', 'bytes', 'combine_d2.py run4_b.json run4_t.json targets_dps120.json')
        for key, quoted in (('L2_minus_claim', '1.7e-79'), ('K2_minus_claim', '3.1e-62')):
            x = mp.mpf(res[key])
            rep.check('Q', 'd=2 residual %s' % key, two_sig(abs(x)) == quoted, res[key], quoted, 'two significant digits',
                      'note 17.2 (l.3892): L2 = -2 log2 P4(2), K2 = 32G^2 - 28 zeta3 log2 (number of C62d\'s row)')

    # E4b the second Cauchy circle of wf_L3 (run B), which fixes the accuracy of the L3 constants
    d = W / 'wf_L3B'; d.mkdir()
    for f in ('final_form.py', 'load.py', 'pieces.py', 'gen3.py', 'pB_dps170.json'):
        copy('wf_L3/' + f, d)
    p = run('final_form.py', ['pB_dps170.json', 'L3_final_values_runB.json'], d)
    ok = p.returncode == 0 and filecmp.cmp(d / 'L3_final_values_runB.json', PKG / 'wf_L3/L3_final_values_runB.json', shallow=False)
    rep.check('E', 'wf_L3/final_form.py pB -> run B values', ok, 'byte-identical' if ok else 'differs or rc=%d' % p.returncode,
              'wf_L3/L3_final_values_runB.json', 'bytes', 'final_form.py pB_dps170.json (N=320, K=128, M=240, rho=0.05)')

    # E6 wf_Z3/derive.py on the two stored 260/270-digit circles
    d = W / 'wf_Z3'; d.mkdir()
    for f in ('derive.py', 'circA2.json', 'circB2.json'):
        copy('wf_Z3/' + f, d)
    for c in ('A2', 'B2'):
        p = run('derive.py', ['circ%s.json' % c, 'derived_circ%s.json' % c], d)
        ok = p.returncode == 0 and filecmp.cmp(d / ('derived_circ%s.json' % c), PKG / 'wf_Z3' / ('derived_circ%s.json' % c),
                                               shallow=False)
        if p.returncode == 0 and not ok:
            a, b = load(d / ('derived_circ%s.json' % c)), load(PKG / 'wf_Z3' / ('derived_circ%s.json' % c))
            with mp.workdps(300):
                dev = max(abs(mp.mpf(a[k]) - mp.mpf(b[k])) for k in ('H30', 'S1', 'S2', 'Q3', 'Z3'))
            ok = dev <= mp.mpf('1e-250')
            val = 'diff %s' % short(dev, 3)
        else:
            val = 'byte-identical' if ok else 'rc=%d %s' % (p.returncode, p.stderr[-200:])
        rep.check('E', 'wf_Z3/derive.py circ%s' % c, ok, val, 'wf_Z3/derived_circ%s.json' % c, 'bytes, else 1e-250 abs',
                  'derive.py circ%s.json (H3(0), S\', S\'\', Q3, Z3)' % c)


# ----------------------------------------------------------------------------------------------- numbers
def polyconsts(q):
    A = mp.psi(0, 2 * q) + mp.psi(0, 1) - 2 * mp.psi(0, q)
    R = mp.psi(1, 2 * q) - mp.psi(1, 1)
    U = mp.psi(2, q)
    V = mp.psi(2, 1) + mp.psi(2, 2 * q)
    X = mp.psi(3, 2 * q) - mp.psi(3, 1)
    return A, R, U, V, X


def c5_general(q, Q, P4, P5, K, L, Z):
    A, R, U, V, X = polyconsts(q)
    return (-1536 * (P5 + K) + 384 * A * P4 - 576 * L - 1728 * Q ** 2 + 720 * A ** 2 * Q + 1008 * Q * R + 7152 * Z
            - 15 * A ** 4 - 90 * A ** 2 * R + 414 * A * U - 108 * A * V - 117 * R ** 2 - 75 * X) / 46656


def s3_bell(q):
    def xh(h):
        x = mp.psi(h - 1, 1) - (-1) ** h * mp.psi(h - 1, 2 * q)
        if h % 2:
            x -= mp.mpf(2) ** (3 - h) * mp.psi(h - 1, q)
        return x
    x1, x2, x3, x4 = (xh(h) for h in (1, 2, 3, 4))
    return (x1 ** 4 + 6 * x1 ** 2 * x2 + 4 * x1 * x3 + 3 * x2 ** 2 + x4) / 24


def numbers(rep, quoted, mb_path):
    mp.mp.dps = 460
    q = mp.mpf(3) / 4
    pi, G, l2, z3 = mp.pi, mp.catalan, mp.log(2), mp.zeta(3)
    r2 = mp.sqrt(2)
    g14 = mp.gamma(mp.mpf(1) / 4)
    pv = load(PKG / 'inputs/general_d3/period_values.json')['runs']
    run90 = [r for r in pv if r['dps'] == 90][0]['values']
    Q, P4, P5 = (num(run90[k]) for k in ('Q3', 'P4_3', 'P5_3'))
    K3 = mp.mpf(load(PKG / 'wf_K3/K3_value.json')['K3'])
    Lv = {k: mp.mpf(v) for k, v in load(PKG / 'wf_L3/L3_final_values.json')['values'].items()}
    LvB = {k: mp.mpf(v) for k, v in load(PKG / 'wf_L3/L3_final_values_runB.json')['values'].items()}
    Zv = {k: mp.mpf(v) for k, v in load(PKG / 'wf_Z3/Z3_values.json')['values'].items()}
    L3, Z3 = Lv['L3'], Zv['Z3']
    masters = load(PKG / 'masters_d3.json')
    runC = load(PKG / 'run_C_combined.json')
    A, R, U, V, X = polyconsts(q)
    out = {}

    # high-precision assembly of gs:C5 and of C2..C4 at q = 3/4
    C5 = c5_general(q, Q, P4, P5, K3, L3, Z3)
    N3 = K3 + mp.mpf(3) / 8 * L3 - mp.mpf(149) / 32 * Z3
    SA = -15 * A ** 4 + (360 - 30 * pi ** 2) * A ** 2 + (828 * pi ** 3 - 1728) * A - 21456 * z3 * A - 83 * pi ** 4 \
        + 312 * pi ** 2 + 5328
    C5_spec = (-1536 * (P5 + N3) + 384 * A * P4 - 1728 * Q ** 2 + (720 * A ** 2 + 336 * pi ** 2 - 4032) * Q + SA) / 46656
    C4 = (16 * P4 - A ** 3 - 8 * A * Q - 3 * A * R + mp.mpf(53) / 2 * U - 3 * V) / 648
    C3 = (A ** 2 + R - 8 * Q) / 108
    C2 = A / 9
    C5_json = mp.mpf(load(PKG / 'c5_value.json')['C5'])
    out.update(C5_3=mp.nstr(C5, 80), C4_3=mp.nstr(C4, 80), C3_3=mp.nstr(C3, 80), C2_3=mp.nstr(C2, 80), N3=mp.nstr(N3, 80))
    vals = dict(C5_3_50=C5, C5_3_note20=C5, C5_3_paper34=C5, C5_3_short=C5, C5_3_table=C5, C4_3_paper=C4,
                C4_3_table=C4, C3_3_table=C3, C2_3_table=C2)
    for e in quoted['coefficients']:
        x = vals[e['id']]
        if e['kind'] == 'unit_last':
            tol = last_unit(e['quoted'])
            rep.check('Q', e['id'], abs(x - mp.mpf(e['quoted'])) <= tol, short(x, sig_digits(e['quoted']) + 3),
                      e['quoted'], 'one unit in the last digit (%s)' % short(tol, 1), e['where'])
        else:
            rep.check('Q', e['id'], rounds_to(x, e['quoted']), short(x, sig_digits(e['quoted']) + 3), e['quoted'],
                      'correct rounding to %d digits' % sig_digits(e['quoted']), e['where'])
    rep.check('Q', 'C5_3_50 from c5_value.json', abs(C5_json - mp.mpf(quoted['coefficients'][0]['quoted'])) <= mp.mpf('1e-49'),
              short(C5_json, 53), quoted['coefficients'][0]['quoted'], 'one unit in the last digit (1e-49)',
              'c5_value.json (compute_c5.py, 43-digit masters of runs A/B)')
    rep.check('F', 'd=3 form of gs:C5 = general form', abs(C5_spec - C5) <= mp.mpf('1e-150'), short(abs(C5_spec - C5), 3),
              '0', '1e-150 abs', 'note 1.1 (S(A), 720A^2+336pi^2-4032) vs gs:C5 with polygammas')

    # masters
    r3 = s3_bell(q) + 4 * (K3 - U / 8 * (mp.psi(0, 1) + mp.psi(0, 2 * q) + 4 * mp.psi(0, q)))
    out['r3_3'] = mp.nstr(r3, 60)
    mvals = dict(Q3=Q, P4_3=P4, P5_3=P5, K3=K3, K3_table=K3, r3_3=r3, L3=L3, Z3=Z3, dH=Lv['dH'], da=Lv['da'],
                 DL_frozen=Lv['dPdb_tdform'], Phat_prime=Lv['Phat_prime'])
    for e in quoted['masters']:
        x = mvals[e['id']]
        tag = e['where'] + ('; owned by %s' % e['owner'] if 'owner' in e else '')
        if e['kind'] == 'unit_last':
            tol = last_unit(e['quoted'])
            rep.check('Q', e['id'], abs(x - mp.mpf(e['quoted'])) <= tol, short(x, sig_digits(e['quoted']) + 3),
                      e['quoted'], 'one unit in the last digit (%s)' % short(tol, 1), tag)
        elif e['kind'] == 'round_eq_fixed2':
            s = mp.nstr(x, sig_digits(e['quoted']), strip_zeros=False)
            rep.check('Q', e['id'], s == e['quoted'], short(x, 12), e['quoted'], 'rounded to 2 decimals', tag)
        else:
            rep.check('Q', e['id'], rounds_to(x, e['quoted']), short(x, sig_digits(e['quoted']) + 3), e['quoted'],
                      'correct rounding to %d digits' % sig_digits(e['quoted']), tag)

    # accuracy statements
    acc = {e['id']: e for e in quoted['accuracy']}
    h3 = mp.mpf(load(PKG / 'wf_K3/run_hp3.json')['K3']); h4 = mp.mpf(load(PKG / 'wf_K3/run_hp4.json')['K3'])
    d = abs(h3 - h4)
    rep.check('A', 'K3_430', d <= mp.mpf(acc['K3_430']['tol']), short(d, 3), acc['K3_430']['quoted'], '<= 1e-430',
              acc['K3_430']['how'])
    with mp.workdps(120):
        d = abs(K3 - num(runC['K3']))
    rep.check('A', 'K3_vs_runC', d <= mp.mpf(acc['K3_vs_runC']['tol']), short(d, 3), acc['K3_vs_runC']['quoted'], '<= 2e-96',
              acc['K3_vs_runC']['how'])
    if mb_path and Path(mb_path).exists():
        Kmb = mp.mpf(load(mb_path)['values']['3']['K'])
        rel = (Kmb - K3) / K3
        rep.check('A', 'K3_vs_MB', two_sig(rel) == acc['K3_vs_MB']['quoted'], two_sig(rel), acc['K3_vs_MB']['quoted'],
                  'two significant digits', acc['K3_vs_MB']['how'])
    else:
        rep.add('A', 'K3_vs_MB', 'SKIP', 'LRI_C5_general_d not present', acc['K3_vs_MB']['quoted'], '-', acc['K3_vs_MB']['how'])
    rel = abs(L3 - mp.mpf(masters['L3'])) / abs(L3)
    rep.check('A', 'L3_vs_spectral43', rel <= mp.mpf('1e-43'), short(rel, 3), 'all 43 digits', '<= 1e-43 relative',
              acc['L3_vs_spectral43']['how'])
    with mp.workdps(120):
        d = abs(Z3 - num(runC['Z3']))
    rep.check('A', 'Z3_vs_runC', '%.0e' % float(d) == acc['Z3_vs_runC']['quoted'], short(d, 3),
              acc['Z3_vs_runC']['quoted'], 'one significant digit', acc['Z3_vs_runC']['how'])
    d = max(abs(Lv[k] - LvB[k]) for k in ('L3', 'P4', 'dH', 'da', 'X0', 'a4', 'b4'))
    rep.check('A', 'L3_158', d <= mp.mpf('1e-157'), short(d, 3), 'about 158 digits', '<= 1e-157 abs', acc['L3_158']['how'])
    dA, dB = load(PKG / 'wf_Z3/derived_circA2.json'), load(PKG / 'wf_Z3/derived_circB2.json')
    d = max(abs(mp.mpf(dA[k]) - mp.mpf(dB[k])) for k in ('H30', 'S2', 'Z3'))
    rep.check('A', 'Z3_250', d <= mp.mpf('1e-250'), short(d, 3), 'about 250 digits', '<= 1e-250 abs', acc['Z3_250']['how'])
    d = max(abs(Zv[k] - mp.mpf(dB[kk])) for k, kk in (('H3_0', 'H30'), ('S1', 'S1'), ('S2', 'S2'), ('Z3', 'Z3'), ('Q3', 'Q3')))
    rep.check('A', 'Z3_values.json = derived circles', d <= mp.mpf('1e-247'), short(d, 3), 'the 250-digit rounding',
              '<= 1e-247 abs', 'wf_Z3/Z3_values.json (assembled by hand from the derived files) vs derived_circB2.json')
    rA, rB = load(PKG / 'run_A_dps50.json'), load(PKG / 'run_B_dps56.json')
    with mp.workdps(70):
        d = max(abs(num(rA[k]) - num(rB[k])) / abs(num(rB[k])) for k in ('K3', 'L3', 'Z3'))
    rep.check('A', 'runs_AB_43', d <= mp.mpf('1e-43'), short(d, 3), '43 established digits', '<= 1e-43 relative',
              acc['runs_AB_43']['how'])
    d = max(abs(Q - Zv['Q3']), abs(P4 - Lv['P4']))
    rep.check('A', 'inputs_1e80', d <= mp.mpf('1e-78'), short(d, 3), 'about 1e-80', '<= 1e-78 abs', acc['inputs_1e80']['how'])
    out['K3_hp3_hp4'] = short(abs(h3 - h4), 3)

    # printed formulas with the stored values
    gam10 = g14 ** 10
    H30, S1, S2 = Zv['H3_0'], Zv['S1'], Zv['S2']
    with mp.workdps(300):
        f1 = abs(Zv['Q3'] - (4 * pi ** 2 * H30 - gam10 / (48 * pi ** mp.mpf(3.5))))
        f2 = abs(Z3 - (4 * pi ** 2 / 3 * S2 - (4 * G + pi ** 2 / 2) * gam10 / (16 * pi ** mp.mpf(3.5))))
        f3 = abs(S1 - (gam10 / (64 * pi ** mp.mpf(4.5)) - pi * H30))
    rep.check('F', 'td:Qanswer Q3 = 4pi^2 H3(0) - G(1/4)^10/(48pi^3.5)', f1 <= mp.mpf('1e-240'), short(f1, 3), '0',
              '1e-240 abs', 'wf_Z3/Z3_values.json (note 19; paper App. A after eq. cf:d123-blocks)')
    rep.check('F', 'Z3 = (4pi^2/3) t3\'\'(3/2) - (4G+pi^2/2) G(1/4)^10/(16pi^3.5)', f2 <= mp.mpf('1e-240'), short(f2, 3), '0',
              '1e-240 abs', 'wf_Z3/Z3_values.json (note 20.4)')
    rep.check('F', "S'(3/2) = G(1/4)^10/(64pi^4.5) - pi H3(0) (dW3/db=0)", f3 <= mp.mpf('1e-240'), short(f3, 3), '0',
              '1e-240 abs', 'wf_Z3/Z3_values.json (WORKFLOW_RESULT.md)')
    a4, b4, X0, Xh = Lv['a4'], Lv['b4'], Lv['X0'], Lv['Xh']
    with mp.workdps(180):
        f4 = abs(L3 - (4 * pi * Lv['P4'] - 2 * pi ** 2 * X0 + 6 * r2 * pi * (pi - 2 * l2) * a4 * b4 - 2 * pi * Lv['dH']
                       + 12 * r2 * pi * b4 * Lv['da']))
        f5 = abs(Lv['P4'] - (2 * pi * X0 - 10 * pi * Xh + (14 * r2 - 20) * pi * a4 * b4))
        f6 = abs(b4 - g14 ** 6 / (16 * pi ** mp.mpf(2.5)))
        f7 = max(abs(Lv['c1'] - 2 * a4 * b4), abs(X0 - (Lv['c0'] - Lv['c1'] / r2)), abs(Xh - (Lv['c0'] - Lv['c1'] + Lv['c2'])))
        Nb4 = pi ** 2 / 16
        f8 = abs(Lv['dPdb_tdform'] - (Lv['Phat_prime'] - 8 * r2 * Nb4 * Lv['c1'] + 32 * Nb4 * Lv['c2']))
    rep.check('F', 'L3 = 4piP4 - 2pi^2 X0 + ... + 12sqrt2 pi b4 da', f4 <= mp.mpf('1e-150'), short(f4, 3), '0', '1e-150 abs',
              'wf_L3/L3_final_values.json (note 20.4)')
    rep.check('F', 'P4(3) = 2pi X0 - 10pi Xh + (14sqrt2-20)pi a4 b4', f5 <= mp.mpf('1e-150'), short(f5, 3), '0', '1e-150 abs',
              'wf_L3/L3_final_values.json (note 19)')
    rep.check('F', 'b4 = G(1/4)^6/(16 pi^2.5) (Rogers-Dougall)', f6 <= mp.mpf('1e-150'), short(f6, 3), '0', '1e-150 abs',
              'wf_L3/L3_final_values.json (note 19)')
    rep.check('F', 'c41 = 2 a4 b4, X0 and Xh from the modes', f7 <= mp.mpf('1e-150'), short(f7, 3), '0', '1e-150 abs',
              'wf_L3/L3_final_values.json (definitions)')
    rep.check('F', "-1332.48 = Phat' - 8sqrt2 N^4 c41 + 32 N^4 c42", f8 <= mp.mpf('1e-150'), short(f8, 3), '0', '1e-150 abs',
              'wf_L3/L3_final_values.json (note 20.4 identity at b = 3/2, N_b^4 = pi^2/16)')

    # reduced form of C5(3) (WORKFLOW_RESULT.md section 2) against the N3 form, with the same inputs
    with mp.workdps(180):
        Qz, P4l = Zv['Q3'], Lv['P4']
        sfr = S2 - (36 * G + 9 * pi ** 2 / 2) * H30
        red = (-1536 * (P5 + K3) + (384 * A - 2304 * pi) * P4l + 1152 * pi ** 2 * X0
               - 3456 * r2 * pi * (pi - 2 * l2) * a4 * b4 + 1152 * pi * Lv['dH'] - 6912 * r2 * pi * b4 * Lv['da']
               + 9536 * pi ** 2 * sfr - 1728 * Qz ** 2 + (720 * A ** 2 + 11064 * pi ** 2 + 85824 * G - 4032) * Qz + SA) / 46656
        nform = c5_general(q, Qz, P4l, P5, K3, L3, Z3)
        f9 = abs(red - nform)
    rep.check('A', 'C5_N3_vs_reduced', f9 <= mp.mpf('1e-110'), short(f9, 3), acc['C5_N3_vs_reduced']['quoted'], '<= 1e-110 abs',
              acc['C5_N3_vs_reduced']['how'])
    out['sfrak'] = mp.nstr(sfr, 40)
    return out


def symbolic(rep):
    try:
        import sympy as sp
    except ImportError:
        rep.add('F', 'symbolic d=3 specialization', 'SKIP', 'sympy missing', '-', '-', 'pip install sympy'); return
    q = sp.Rational(3, 4)
    A = sp.expand_func(sp.polygamma(0, 2 * q) + sp.polygamma(0, 1) - 2 * sp.polygamma(0, q))
    R = sp.expand_func(sp.polygamma(1, 2 * q) - sp.polygamma(1, 1))
    U = sp.expand_func(sp.polygamma(2, q))
    V = sp.expand_func(sp.polygamma(2, 1) + sp.polygamma(2, 2 * q))
    X = sp.expand_func(sp.polygamma(3, 2 * q) - sp.polygamma(3, 1))
    a = sp.Symbol('A')
    pi, z3 = sp.pi, sp.zeta(3)
    target = dict(A=2 + 4 * sp.log(2) - pi, R=pi ** 2 / 3 - 4, U=2 * pi ** 3 - 56 * z3, V=16 - 16 * z3, X=sp.Rational(14, 15) * pi ** 4 - 96)
    got = dict(A=A, R=R, U=U, V=V, X=X)
    bad = [k for k in got if sp.simplify(sp.nsimplify(got[k]) - target[k]) != 0 and abs(sp.N(got[k] - target[k], 60)) > 1e-50]
    rep.check('F', 'polygamma constants at q=3/4', not bad, 'A,R,U,V,X closed forms' if not bad else 'differ: %s' % bad,
              'A=2+4log2-pi, R=pi^2/3-4, U=2pi^3-56z3, V=16-16z3, X=14pi^4/15-96', 'exact (SymPy) or 1e-50',
              'note 1.1 (three dimensions), assemble_c5_d3.py')
    Rv, Uv, Vv, Xv = (target[k] for k in ('R', 'U', 'V', 'X'))
    S_gen = -15 * a ** 4 - 90 * a ** 2 * Rv + 414 * a * Uv - 108 * a * Vv - 117 * Rv ** 2 - 75 * Xv
    S_d3 = -15 * a ** 4 + (360 - 30 * pi ** 2) * a ** 2 + (828 * pi ** 3 - 1728 - 21456 * z3) * a - 83 * pi ** 4 + 312 * pi ** 2 + 5328
    qcoef = sp.expand(720 * a ** 2 + 1008 * Rv - (720 * a ** 2 + 336 * pi ** 2 - 4032))
    c4 = sp.expand(-3 * a * Rv + sp.Rational(53, 2) * Uv - 3 * Vv - ((12 - pi ** 2) * a + 53 * pi ** 3 - 1436 * z3 - 48))
    Q, P4, P5, K, L, Z, N = sp.symbols('Q P4 P5 K L Z N')
    gen = -1536 * (P5 + K) + 384 * a * P4 - 576 * L - 1728 * Q ** 2 + 720 * a ** 2 * Q + 1008 * Q * Rv + 7152 * Z + S_gen
    spec = -1536 * (P5 + N) + 384 * a * P4 - 1728 * Q ** 2 + (720 * a ** 2 + 336 * pi ** 2 - 4032) * Q + S_d3
    diff = sp.expand(gen.subs(K, N - sp.Rational(3, 8) * L + sp.Rational(149, 32) * Z) - spec)
    ok = sp.expand(S_gen - S_d3) == 0 and qcoef == 0 and c4 == 0 and diff == 0
    rep.check('F', 'symbolic d=3 specialization of gs:C5, C4', ok, 'difference 0' if ok else 'nonzero', '0', 'exact (SymPy)',
              'note 1.1; README.md of the package')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--work', default=str(PKG / '.work'))
    ap.add_argument('--quoted', default=str(PKG.parent.parent / 'results' / 'closed_forms_3' / 'LRI_C5_d3_quoted.json'))
    ap.add_argument('--mb', default=str(PKG.parent / 'LRI_C5_general_d' / 'K_general' / 'position_space' / 'K_d_values_mb_D100.json'),
                    help='optional 100-digit position-space K_d of LRI_C5_general_d')
    ap.add_argument('--symbolic-only', action='store_true', help='only the SymPy check (used by make test)')
    a = ap.parse_args()
    W = Path(a.work).resolve() / 'replay'
    shutil.rmtree(W, ignore_errors=True)
    W.mkdir(parents=True)
    t0 = time.time()
    rep = Report()
    if a.symbolic_only:
        symbolic(rep)
        rep.write(W / 'TEST_symbolic.md', 'SymPy check only (make test).')
        sys.exit(1 if rep.failed() else 0)
    print('LRI_C5_d3 replay: package %s, work %s' % (PKG, W))
    reruns(rep, W)
    quoted = load(a.quoted)
    out = numbers(rep, quoted, a.mb)
    symbolic(rep)
    out.update(python=sys.version.split()[0], mpmath=mp.__version__, seconds=round(time.time() - t0, 1))
    json.dump(out, open(W / 'reproduced_c5_d3.json', 'w'), indent=1)
    rep.write(W / 'REPLAY_c5_d3.md', 'Python %s, mpmath %s, %.1f s. Quoted numbers: %s.' % (
        sys.version.split()[0], mp.__version__, time.time() - t0, os.path.relpath(a.quoted, PKG)))
    nf = len(rep.failed())
    print('%s: %d checks, %d FAIL; table in %s' % ('FAIL' if nf else 'PASS', len(rep.rows), nf, W / 'REPLAY_c5_d3.md'))
    sys.exit(1 if nf else 0)


if __name__ == '__main__':
    main()
