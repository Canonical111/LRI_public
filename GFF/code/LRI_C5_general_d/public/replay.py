#!/usr/bin/env python3
"""Replay of LRI_C5_general_d: the generic-dimensional reduction of L_d and Z_d (note Section 20) and its C5(d) checks.

Run from the package folder (GFF/code/LRI_C5_general_d) as `make -f public.mk replay` (about 30-45 s on one core).

The package has no Monte Carlo and no production campaign: every number is a deterministic multiple-precision evaluation
(mpmath, pure Python big integers; no BLAS, no floating point in the quoted digits). The replay therefore has two parts.

1. Records (R0). Every number that note Section 20 (and the gdk table column computed here, and the paper) quotes for this
   package is recomputed from the shipped records and compared with the printed text, by the rules of
   ../../results/closed_forms_general/reduction_d/expected.json:
     value  the record rounded to the printed digits equals the quoted number (a trailing ellipsis also accepts truncation);
     bound  the record truncated to the printed significant digits is <= the quoted bound;
     range  the record minimum and maximum, rounded or truncated to the printed digits, equal the quoted ends;
     lower  the record is >= the quoted number;  exact  equal integers.
   Before that it checks the md5 prefixes that the package's own records pin on its code (L_general.py, Z_general.py,
   hypsums.py, lg_engine.py, rblocks.py, reference_values.json) and the SHA-256 of every record it reads. If the condensed
   note is present (../../note/long_range_ising_condensed.tex) it also checks that every quoted TeX string occurs in it.
2. Fast recompute (skipped with --records-only). In a copy of the package (public/out/work/; several scripts overwrite
   their own records) it reruns the package's own scripts whose cost is seconds and compares their output with the
   shipped records:
     review/joint/numerics-end-to-end/e2e.py samples_dps60.json   -> e2e_report.json, byte for byte (C5(1), C5(2), C5(3))
     public/e2e_k3_public.py k3_jets.json (path-fixed copy)       -> e2e_k3.log, line for line
     specialize/check_d3.py 50                                     -> results/check_d3_dps50.log, line for line
     specialize/check_special.py                                   -> public/out/check_special.log (no log was shipped)
     foundation/check_topG.py                                      -> check_topG.log, line for line without timings
     review/lemmaG-numeric/{summarize,compare_external}.py         -> results/summary*.json, external_comparison.json
   plus public/check_DL_Phat.py (the d = 3 identity of Section 20.4, whose run left no record) from the shipped samples.
   The 60-digit samples themselves, the five-Horn and two-node codes at 50-90 digits, the C5 assembly at 8 dimensions and
   the pole-node check are recomputed by `make -f public.mk replay-full` (about 1 core-hour; CLUSTER_CHECKS.md).

Tolerances. Same records and the same code: mpmath arithmetic is deterministic, so reruns are compared byte for byte or
line for line. Checked on 2026-10-13: Python 3.10.11 with mpmath 1.2.1 (macOS; both the gmpy2 and the pure-Python
backend, MPMATH_NOGMPY=1) reproduces the records written on the symmetry cluster (python/3.11 module, mpmath version not
recorded) byte for byte. Timings printed by check_topG.py are
removed before the comparison. Quoted numbers are compared at their printed digits only.

Output: a PASS/FAIL table on stdout, public/out/replay.json; exit 1 on any FAIL. SKIP only for rows of a part that was
not run (--records-only) or for the note-text check when the note is absent.
"""
import argparse
import ast
import datetime as dt
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Decimal, getcontext
from pathlib import Path

import mpmath as mp

getcontext().prec = 120
PKG = Path(__file__).resolve().parents[1]
E2E = 'review/joint/numerics-end-to-end'
ROWS = []


# ----------------------------------------------------------------------------------------------------------- helpers
def row(group, rid, what, got, expected, ok, note=''):
    st = ok if isinstance(ok, str) else ('PASS' if ok else 'FAIL')
    ROWS.append(dict(group=group, id=rid, what=what, got=str(got), expected=str(expected), status=st, note=note))


def jload(p):
    return json.loads(Path(p).read_text())


def clean(q):
    return q.replace('−', '-').replace('…', '').replace('\\ldots', '').replace('...', '').strip()


def has_ellipsis(q):
    return '…' in q or '\\ldots' in q or q.endswith('...')


def ndig(q):
    m = clean(q).lstrip('+-').lower().split('e')[0].replace('.', '').lstrip('0')
    return max(len(m), 1)


def dec(x):
    if isinstance(x, Decimal):
        return x
    if isinstance(x, (mp.mpf, mp.mpc)):
        return Decimal(mp.nstr(mp.re(x), 60, strip_zeros=False))
    return Decimal(str(x).strip())


def to_sig(x, n, mode):
    x = dec(x)
    if x == 0:
        return x
    return x.quantize(Decimal(1).scaleb(x.adjusted() - n + 1), rounding=mode)


def check_value(x, q):
    modes = (ROUND_HALF_EVEN, ROUND_DOWN) if has_ellipsis(q) else (ROUND_HALF_EVEN,)
    return any(to_sig(x, ndig(q), m) == Decimal(clean(q)) for m in modes)


def check_bound(x, q):
    return to_sig(abs(dec(x)), ndig(q), ROUND_DOWN) <= Decimal(clean(q))


def check_end(x, q):
    return any(to_sig(x, ndig(q), m) == Decimal(clean(q)) for m in (ROUND_HALF_EVEN, ROUND_DOWN))


def short(x, n=4):
    return mp.nstr(mp.mpf(str(x)), n) if not isinstance(x, str) or re.match(r'^[-+0-9.eE]+$', x) else x


class Expected:
    def __init__(self, path):
        self.e = jload(path)
        self.rows = self.e['rows']
        self.used = set()

    def q(self, rid):
        self.used.add(rid)
        return self.rows[rid]

    def judge(self, group, rid, got, note=''):
        r = self.q(rid)
        q, rule = r['quoted'], r['rule']
        if rule == 'value':
            ok, shown = check_value(got, q), got
        elif rule == 'bound':
            ok, shown = check_bound(got, q), short(got)
        elif rule == 'lower':
            ok, shown = dec(got) >= Decimal(clean(q)), got
        elif rule == 'exact':
            ok, shown = int(got) == int(q), got
        elif rule == 'range':
            lo, hi = got
            ok = check_end(lo, q[0]) and check_end(hi, q[1])
            shown = '%s .. %s' % (short(lo), short(hi))
        elif rule == 'values':
            ok = len(got) == len(q) and all(check_value(g, x) for g, x in zip(got, q))
            shown = ', '.join(short(g, 6) if len(str(g)) > 20 else str(g) for g in got)
        else:
            raise ValueError(rule)
        exp = (' .. '.join(q) if rule == 'range' else ', '.join(q) if isinstance(q, list) else q)
        if r.get('note_change'):
            note = (note + '; ' if note else '') + 'quoted text as corrected by note change %s (note at %s prints %s)' % (
                r['note_change'], self.e['note']['commit'], ' .. '.join(r['quoted_fa71533']))
        row(group, rid, r['what'], shown, exp + ('   [%s]' % r['where']), ok, note)


# ----------------------------------------------------------------------------------------------- R0: identities
def check_bindings(E):
    for p, full in E.e['code_md5'].items():
        f = PKG / p
        if not f.exists():
            row('binding', 'md5:' + p, 'code md5 pinned by the package records', 'missing', full[:8], False)
            continue
        m = hashlib.md5(f.read_bytes()).hexdigest()
        row('binding', 'md5:' + p, 'md5 recorded in the package (record.json / probe_report.json / STATUS)',
            m[:8], E.e['code_md5_recorded'][p], m == full)
    for p, h in E.e['record_sha256'].items():
        f = PKG / p
        got = hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else 'missing'
        row('binding', 'sha256:' + p, 'shipped record read by this replay', got[:16], h[:16], got == h)


def check_note_text(E, note):
    if not note.exists():
        row('note', 'note-text', 'quoted TeX strings occur in the note', 'note not found', str(note), 'SKIP')
        return
    t = note.read_text()
    miss = [k for k, r in E.rows.items()
            if r.get('tex') and r['tex'] not in t and not (r.get('tex_after') and r['tex_after'] in t)]
    row('note', 'note-text', 'quoted TeX strings of expected.json occur in the note (%d rows; a row with a pending '
        'note change also accepts its corrected text)' % sum(1 for r in E.rows.values() if r.get('tex')),
        'missing: ' + ', '.join(miss) if miss else 'all found', 'all found', not miss)


# ------------------------------------------------------------------------------------------------ R0: the numbers
def end_to_end(E):
    e = jload(PKG / E2E / 'e2e_report.json')
    v = {d: e[d]['values']['C5_reduced_jetK_P5hp'] for d in ('1', '2', '3')}
    for d in ('1', '2', '3'):
        E.judge('C5 end to end', 'C5_%s_end_to_end' % d, v[d])
    mp.mp.dps = 60
    c1 = mp.mpf(v['1'])
    note33 = mp.mpf('-731.139476624539825853869126582527')  # note l.2531
    E.judge('C5 end to end', 'C5_1_vs_note', abs(c1 - note33) / abs(note33), 'record: %s' % e['1']['checks']['C5red_jetK_P5hp_vs_note'])
    E.judge('C5 end to end', 'C5_2_vs_closed', e['2']['checks']['C5red_jetK_vs_C5_twoClosed'])
    # The printed strings of e2e_report.json carry 40 digits, so the agreement with the 50-digit C5(3) of LRI_C5_d3 (note
    # l.6078) is taken from the full-precision values that e2e.py and e2e_k3.py computed and recorded (five-node K and
    # three-node K); the 40-digit string is checked against l.6078 at its own precision.
    five = e['3']['checks']['C5red_jetK_P5hp_vs_LRI_C5_d3_json']
    m = re.search(r'C5\(3\) three-node K\s+(\S+)\s+vs LRI_C5_d3\s+(\S+)', (PKG / E2E / 'e2e_k3.log').read_text())
    three = m.group(2)
    note50 = mp.mpf('-5.8503514207513272292179442304977443001109973463783')  # note l.6078 (LRI_C5_d3)
    string_dev = abs(mp.mpf(v['3']) - note50) / abs(note50)
    E.judge('C5 end to end', 'C5_3_vs_d3', max(float(five), float(three)),
            'five-node K %s (e2e_report checks), three-node K %s (e2e_k3.log); the 40-digit string vs l.6078: %s' % (
                five, three, mp.nstr(string_dev, 2)))
    # cross-checks of values owned by other packages
    E.judge('cross-check', 'xc_C5_table_sec1', [v['1'], v['2'], v['3']])
    E.judge('cross-check', 'xc_C5_status', [v['1'], v['2'], v['3']])
    E.judge('cross-check', 'xc_C5_1_note33', v['1'])
    E.judge('cross-check', 'xc_C5_2_note25', v['2'])
    E.judge('cross-check', 'xc_paper_C5_3', v['3'])
    E.judge('cross-check', 'xc_paper_L3', e['3']['values']['L'])
    return e


def assembly(E):
    a = jload(PKG / 'specialize/results/c5_assembly_dps50.json')
    mx = lambda keys, dims=None: max(float(a[d][k]) for d in a for k in keys if dims is None or d in dims)
    E.judge('C5 assembly', 'masters_vs_codes', mx(['dev_P4_compact', 'dev_L_compact', 'dev_Z_Qform', 'dev_Q_c0form']))
    E.judge('C5 assembly', 'block_reduced_form', mx(['dev_Bred_vs_B']))
    E.judge('C5 assembly', 'block_vs_closed_d12', mx(['dev_P4_ref', 'dev_L_ref', 'dev_Q_ref', 'dev_Z_ref', 'dev_B_ref'], ('1', '2')))
    E.judge('C5 assembly', 'block_d3_Q3_limited', float(a['3']['dev_B_ref']))


def block_vs_refs(E):
    """The block 384 A P4 - 576 L - 1728 Q^2 + (720 A^2 + 1008 R) Q + 7152 Z from the code records (L/results/val50.json:
    P4 = W, L = dW of center_r4; Z/results/zj90.json: 3Q = W, Z) against the same block from the spectral references."""
    mp.mp.dps = 80
    refs = jload(PKG / 'references/reference_values.json')['values']
    L50 = jload(PKG / 'L/results/val50.json')['results']
    Z90 = jload(PKG / 'Z/results/zj90.json')['results']
    worst, worst_m = 0, 0
    for d in ('0.8', '1.25', '1.5', '2.5', '2.75'):
        q = mp.mpf(d) / 4
        A = mp.psi(0, 2 * q) + mp.psi(0, 1) - 2 * mp.psi(0, q)
        R = mp.psi(1, 2 * q) - mp.psi(1, 1)
        blk = lambda P4, L, Q, Z: 384 * A * P4 - 576 * L - 1728 * Q ** 2 + (720 * A ** 2 + 1008 * R) * Q + 7152 * Z
        c = L50['center_r4_d' + d]
        mine = (mp.mpf(c['W']), mp.mpf(c['dW']), mp.re(mp.mpmathify(Z90[d]['W'])) / 3, mp.re(mp.mpmathify(Z90[d]['Z'])))
        r = refs['d=' + d]
        ref = (mp.mpf(r['P4']['value']), mp.mpf(r['L']['value']), mp.mpf(r['threeQ']['value']) / 3, mp.mpf(r['Z']['value']))
        worst = max(worst, abs(blk(*mine) - blk(*ref)) / abs(blk(*ref)))
        worst_m = max([worst_m] + [abs(x - y) / abs(y) for x, y in zip(mine, ref)])
    rec = jload(PKG / E2E / 'record.json')['noninteger_refs']
    E.judge('masters', 'block_vs_spectral_refs', worst, 'masters P4, L, Q, Z individually <= %s; record.json: %s' % (
        mp.nstr(worst_m, 2), rec['P4,L,Q,Z (printed gdr formulas)']))


def closed_forms_d12():
    """Not a printed number: the masters of the code records at d = 1, 2 against their closed forms (supports the
    'closed forms' row). Records: L/results/val70.json (70 digits), Z/results/zj90.json (90 digits)."""
    mp.mp.dps = 80
    L70 = jload(PKG / 'L/results/val70.json')['results']
    Z90 = jload(PKG / 'Z/results/zj90.json')['results']
    pi, G, l2 = mp.pi, mp.catalan, mp.log(2)
    g4 = mp.gamma(mp.mpf(1) / 4) ** 4
    Fm = mp.hyper([0.25, 0.25, 0.5, 0.5], [0.75, 0.75, 1], 1)
    Fp = mp.hyper([0.75, 0.75, 0.5, 0.5], [1.25, 1.25, 1], 1)
    Bm, Bp = g4 * Fm, 64 * pi ** 4 / g4 * Fp
    P41 = 13 * Bm - 3 * Bp
    L1 = -(3 * (pi + 4 * l2) - pi) / 6 * P41 - 2 * pi / 3 * Bm
    P42 = (Bm ** 2 - Bp ** 2) / (4 * pi ** 3)
    Q1, Q2 = g4 / pi, g4 ** 2 / (24 * pi ** 4)
    pairs = [(L70['center_r4_d1']['W'], P41), (L70['center_r4_d1']['dW'], L1), (L70['center_r4_d2']['W'], P42),
             (L70['center_r4_d2']['dW'], -2 * l2 * P42), (Z90['1']['W'], 3 * Q1), (Z90['2']['W'], 3 * Q2),
             (Z90['1']['Z'], Q1 * (2 * pi ** 2 / 3 + 8 * G)), (Z90['2']['Z'], 4 * G * Q2)]
    worst = max(abs(mp.re(mp.mpmathify(x)) - y) / abs(y) for x, y in pairs)
    row('masters', 'closed_forms_d12_records', 'P4, L, 3Q, Z at d = 1, 2 in the code records vs their closed forms '
        '(L2 = -2 log2 P4(2), Z1 = Q1(2pi^2/3 + 8G), Z2 = 4G Q2)', mp.nstr(worst, 3), '<= 1e-65 (supporting row)', worst < mp.mpf('1e-65'))


def specializations(E, special_log):
    t = (PKG / 'specialize/results/check_d3_dps50.log').read_text()
    devs = [float(x) for x in re.findall(r'rel\.dev vs C63d\s+(\S+)', t)]
    E.judge('d = 3', 'd3_dictionary', max(devs), '%d quantities' % len(devs))
    E.judge('d = 3', 'd3_L3_formula', float(re.search(r'formula with our dictionary vs our L3:\s+(\S+)', t).group(1)))
    vals = dict(re.findall(r'^(\w+)\s+(-?[0-9.]+)\s+rel\.dev', t, re.M))
    E.judge('cross-check', 'xc_paper_dH', vals['dH'])
    E.judge('cross-check', 'xc_paper_da', vals['da'])
    tl = (PKG / 'specialize/results/check_taylor_dps30.log').read_text()
    rels = [float(x) for x in re.findall(r'rel=(\S+)', tl)]
    E.judge('pole node', 'pole_node_vs_multinode', (max(rels), min(rels)))
    if special_log is None:
        for rid in ('lattice_identities_d12', 'landen_relations', 'P4_L_from_modes_d12'):
            E.q(rid)
            row('d = 1, 2', rid, E.rows[rid]['what'], 'not run (--records-only)', E.rows[rid]['quoted'], 'SKIP',
                'specialize/check_special.py left no log; the fast recompute writes public/out/check_special.log')
        return
    s = dict((k.strip(), float(v)) for k, v in re.findall(r'^(.*?)\s{2,}(\S+)$', special_log, re.M))
    lat = [v for k, v in s.items() if k.startswith(('d=1 duplication', 'd=2 square'))]
    lan = [v for k, v in s.items() if k.startswith(('a = 8', 'b = 8', "A'(1/2)", "B'(1/2)"))]
    mod = [v for k, v in s.items() if 'from modes' in k or k.startswith(('d=1: W_4', 'd=1: dW_4', 'd=2: W_4', 'd=2: dW_4'))]
    E.judge('d = 1, 2', 'lattice_identities_d12', (max(lat), min(lat)), '%d identities (public/out/check_special.log)' % len(lat))
    E.judge('d = 1, 2', 'landen_relations', max(lan), '%d relations' % len(lan))
    E.judge('d = 1, 2', 'P4_L_from_modes_d12', max(mod), '%d values' % len(mod))


def dl_identity(E):
    sys.path.insert(0, str(PKG / 'public'))
    import check_DL_Phat
    r = check_DL_Phat.evaluate()
    E.judge('d = 3', 'DL_identity', r['rel'], 'lhs %s' % r['lhs'][:24])
    E.judge('d = 3', 'DL_value_d3', r['lhs'])
    E.judge('d = 3', 'Phat_prime_d3', r['Phat_prime'])
    return r


def topmode(E):
    sup = {('probe_mainG1.json', 'D2r3'), ('probe_mainG2.json', 'D2r4'), ('probe_extra1.json', 'A4r3'),
           ('probe_extra1.json', 'A1r2')}  # superseded entries, as in review/topmode-numeric/summarize.py
    P = lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    rows = {}
    for f in sorted(glob.glob(str(PKG / 'review/topmode-numeric/results/probe_*.json'))):
        for k, v in jload(f)['configs'].items():
            if (os.path.basename(f), k) not in sup:
                rows[k] = v
    bal = {k: v for k, v in rows.items() if P(v['g']) is None and v['mult'] == 'so'}
    tops = [float(v['top_rel']) for v in bal.values()]
    surv, hi = [], []
    for v in bal.values():
        r = int(v['r'])
        rel = {int(a): float(b) for a, b in P(v['rel']).items()}
        surv += [rel[m] for m in rel if abs(m) <= r - 2]
        if r in (5, 6):
            hi += [rel[m] for m in rel if abs(m) == r - 2]
    unb = [float(v['top_rel']) for k, v in rows.items() if k.startswith(('U1', 'U2'))]
    E.judge('top modes', 'topmode_balanced', (min(tops), max(tops)))
    E.judge('top modes', 'topmode_balanced_count', len(bal))
    E.judge('top modes', 'topmode_surviving', (min(surv), max(surv)))
    E.judge('top modes', 'topmode_unbalanced', (min(unb), max(unb)))
    E.judge('top modes', 'topmode_no_1plusz', rows['N1r4']['top_rel'])
    E.judge('top modes', 'higher_modes_c53_c64', (min(hi), max(hi)))
    cu = (PKG / 'review/foundation-rigor/results/control_unbalanced.log').read_text()
    E.judge('top modes', 'unbalanced_control_fr', re.search(r"'top': ([0-9.e-]+)", cu).group(1))
    s = jload(PKG / 'review/lemmaG-numeric/results/summary.json')
    tp = lambda k: [float(s[k]['top_minus']), float(s[k]['top_plus'])]
    mixed = sum((tp(k) for k in ['A%d' % i for i in range(1, 7)] + ['B%d' % i for i in range(1, 7)]), [])
    rk = sum((tp('R%d' % i) for i in range(1, 5)), [])
    E.judge('top modes', 'lemmaG_mixed', (min(mixed), max(mixed)))
    E.judge('top modes', 'lemmaG_R', (min(rk), max(rk)))
    E.judge('top modes', 'lemmaG_W0', s['W0']['top_minus'] if s['W0']['top_minus'] == s['W0']['top_plus'] else max(tp('W0')))
    fine = sum((tp(k) for k in s if k.endswith('_fine') and s[k]['inside_C']), [])
    cont = sum((tp(k) for k in s if k.endswith('_cont_fine')), [])
    E.judge('top modes', 'lemmaG_fine', max(fine), '%d reruns' % (len(fine) // 2))
    E.judge('top modes', 'lemmaG_continued', max(cont), '%d continued points' % (len(cont) // 2))
    c = {x['eps']: float(x['top_minus_rel']) for x in jload(PKG / 'review/lemmaG-numeric/results/summary_controls.json')['imbalance_A1']}
    E.judge('top modes', 'lemmaG_controls', (c['0.0015'], c['0.15']))
    ext = jload(PKG / 'review/lemmaG-numeric/results/external_comparison.json')
    perspin = [float(x) for k in ('X_R5', 'X_G2', 'X_C1') for x in P(ext[k]['rel_dev_by_mode']).values()]
    E.judge('top modes', 'lemmaG_external', max(perspin))
    tg = (PKG / 'foundation/check_topG.log').read_text()
    big, ctrl, case_r = [], [], None
    for line in tg.splitlines():
        m = re.match(r'\s+[A-D] d=\S+ r=(\d)', line)
        if m:
            case_r = int(m.group(1))
        cut = re.search(r'\(\s*(\d+),\s*(\d+)\)', line)
        if case_r is None or not cut or cut.group(1) != '110':
            continue
        modes = {int(a): float(b) for a, b in re.findall(r'([+-]\d):(\S+)', line)}
        (ctrl if 'control' in line else big).extend([modes[-(case_r - 1)], modes[case_r - 1]])
    E.judge('top modes', 'check_topG_modes', (min(big), max(big)), 'cutoff (110, 110)')
    E.judge('top modes', 'check_topG_controls', (min(ctrl), max(ctrl)))
    ids = [float(x) for x in re.findall(r'max rel\. deviation(?: \(and balance defect\))? (\S+)', tg)]
    E.judge('top modes', 'check_topG_identities', max(ids))


def review_codes(E):
    t = (PKG / 'review/formula-from-text/compare.out').read_text()
    data, sec = [], None
    for line in t.splitlines():
        m = re.match(r'results/d([0-9.]+)_M(\d+)_N\d+_J(\d+)\.json', line)
        if m:
            sec = m.group(1)
            continue
        m = re.match(r'(P4|L|threeQ|Z)\s+printed=\S+\s+vs ref:\s+([0-9.]+) digits', line)
        if m and sec:
            data.append((sec, m.group(1), float(m.group(2))))
        m = re.match(r'offdiag b=\S+: W3 ([0-9.]+) digits, W4 ([0-9.]+) digits', line)
        if m and sec:
            data += [(sec, 'off', float(m.group(1))), (sec, 'off', float(m.group(2)))]
        m = re.match(r'C5 block .*: ([0-9.]+) digits', line)
        if m and sec:
            data.append((sec, 'block', float(m.group(1))))
    pick = lambda q, d=None: [x for s, k, x in data if k == q and (d is None or s == d)]
    E.judge('review codes', 'review_offcentre_digits', (min(pick('off')), max(pick('off'))))
    E.judge('review codes', 'review_P4_digits', (min(pick('P4')), max(pick('P4'))))
    E.judge('review codes', 'review_L_digits', (min(pick('L')), max(pick('L'))))
    for d in ('1', '2', '3'):
        z = set(pick('Z', d))
        E.judge('review codes', 'review_Z%s_digits' % d, z.pop() if len(z) == 1 else 'ambiguous %s' % sorted(z))
    E.judge('review codes', 'review_block_digits', (min(pick('block')), max(pick('block'))))
    cc = (PKG / 'review/L-rigor/coeff_check.log').read_text()
    E.judge('review codes', 'review_coeff_functions', re.search(r'worst.*?:\s*(\S+)\s*$', cc, re.M).group(1))
    zr = (PKG / 'review/Z-rigor/d3_gamma_offcenter.log').read_text()
    E.judge('review codes', 'c0hat_gamma_offcentre', max(float(x) for x in re.findall(r'rel dev (\S+)', zr)),
            'b = %s' % ', '.join(re.findall(r'^b=(\S+)', zr, re.M)))


def pslq(E):
    g = jload(PKG / 'specialize/results/gamma_c0_dps80.json')
    E.judge('PSLQ', 'pslq_c0hat', min(int(v['pslq_log_c0hat_maxcoeff']) for v in g.values()), 'd = %s' % ', '.join(g))
    p = jload(PKG / 'specialize/results/pslq_L_dps110.json')
    differ = all(v['pslq_hi'] != v['pslq_lo'] for v in p.values())
    E.judge('PSLQ', 'pslq_DL', min(min(int(v['maxcoeff_hi']), int(v['maxcoeff_lo'])) for v in p.values()) if differ else 0,
            'the relations found at the two precisions differ at d = %s (unstable)' % ', '.join(p))


def k3_column(E, log_text):
    vals = [m.group(1) for m in re.finditer(r'K3node vs MB (\S+)', log_text)]
    E.judge('gdk table', 'k3_three_node', vals, 'd = 1.5, 2.5, 3')


# --------------------------------------------------------------------------------------------- fast recompute
def run(cmd, cwd, env=None, timeout=900):
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    return p, time.time() - t0


def lines(s):
    return [x.rstrip() for x in s.strip().splitlines()]


def recompute(out, py):
    work = out / 'work'
    if work.exists():
        shutil.rmtree(work)
    dst = work / 'LRI_C5_general_d'
    skip = (PKG / 'public' / 'out').resolve()
    shutil.copytree(PKG, dst, ignore=lambda d, names: [n for n in names if (Path(d) / n).resolve() == skip
                                                         or n == '__pycache__'], symlinks=True)
    d3 = (PKG.parent / 'LRI_C5_d3').resolve()
    if d3.exists():
        os.symlink(d3, work / 'LRI_C5_d3')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1')
    res = {}
    # 1. e2e.py: C5(1), C5(2), C5(3) end to end from the shipped 60-digit samples
    wd = dst / E2E
    p, sec = run([py, 'e2e.py', 'samples_dps60.json'], wd, env)
    same = p.returncode == 0 and (wd / 'e2e_report.json').read_bytes() == (PKG / E2E / 'e2e_report.json').read_bytes()
    row('recompute', 'e2e.py', 'e2e.py samples_dps60.json: e2e_report.json equals the shipped record byte for byte',
        'identical' if same else 'rc %d / differs' % p.returncode, 'identical', same, '%.1f s' % sec)
    # 2. three-node K and C5(3) with the three-node K (path-fixed public copy)
    p, sec = run([py, str(dst / 'public' / 'e2e_k3_public.py'), 'k3_jets.json'], wd, dict(env, C5GD_E2E_DIR=str(wd)))
    want = lines((PKG / E2E / 'e2e_k3.log').read_text())
    ok = p.returncode == 0 and lines(p.stdout) == want
    row('recompute', 'e2e_k3', 'public/e2e_k3_public.py k3_jets.json: output equals e2e_k3.log line for line',
        'identical' if ok else 'rc %d / differs' % p.returncode, 'identical', ok, '%.1f s; needs ../LRI_C5_d3' % sec)
    res['k3_log'] = p.stdout if ok else None
    # 3. d = 3 dictionary at 50 digits
    p, sec = run([py, 'check_d3.py', '50'], dst / 'specialize', env)
    ok = p.returncode == 0 and lines(p.stdout) == lines((PKG / 'specialize/results/check_d3_dps50.log').read_text())
    row('recompute', 'check_d3', 'specialize/check_d3.py 50: output equals results/check_d3_dps50.log', 'identical' if ok
        else 'rc %d / differs' % p.returncode, 'identical', ok, '%.1f s' % sec)
    # 4. d = 1, 2 identities (the shipped package has no log of this run)
    p, sec = run([py, 'check_special.py'], dst / 'specialize', env)
    (out / 'check_special.log').write_text(p.stdout)
    row('recompute', 'check_special', 'specialize/check_special.py ran; output saved to public/out/check_special.log',
        'rc %d, %d lines' % (p.returncode, len(lines(p.stdout))), 'rc 0, 19 lines',
        p.returncode == 0 and len(lines(p.stdout)) == 19, '%.1f s' % sec)
    res['special'] = p.stdout if p.returncode == 0 else None
    # 5. product form of the top-mode theorem, 30 digits
    p, sec = run([py, 'check_topG.py'], dst / 'foundation', env)
    strip = lambda s: [re.sub(r'\s*\(\d+\.\ds\)', '', x) for x in lines(s)]
    ok = p.returncode == 0 and strip(p.stdout) == strip((PKG / 'foundation/check_topG.log').read_text())
    row('recompute', 'check_topG', 'foundation/check_topG.py: output equals check_topG.log (timings removed)',
        'identical' if ok else 'rc %d / differs' % p.returncode, 'identical', ok, '%.1f s' % sec)
    # 6. lemmaG probe summaries rebuilt from its per-case results
    lg = dst / 'review/lemmaG-numeric'
    for script, files in (('summarize.py', ('results/summary.json', 'results/summary_controls.json')),
                          ('compare_external.py', ('results/external_comparison.json',))):
        p, sec = run([py, script], lg, env)
        ok = p.returncode == 0 and all((lg / f).read_bytes() == (PKG / 'review/lemmaG-numeric' / f).read_bytes() for f in files)
        row('recompute', 'lemmaG:' + script, 'review/lemmaG-numeric/%s rebuilds %s byte for byte' % (script, ', '.join(files)),
            'identical' if ok else 'rc %d / differs' % p.returncode, 'identical', ok, '%.1f s' % sec)
    return res


# ------------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--results', default='../../results/closed_forms_general/reduction_d')
    ap.add_argument('--note', default='../../note/long_range_ising_condensed.tex')
    ap.add_argument('--out', default='public/out')
    ap.add_argument('--records-only', action='store_true')
    ap.add_argument('--python', default=sys.executable)
    a = ap.parse_args()
    t0 = time.time()
    out = (PKG / a.out).resolve() if not os.path.isabs(a.out) else Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    E = Expected((PKG / a.results / 'expected.json').resolve())
    check_bindings(E)
    check_note_text(E, (PKG / a.note).resolve())
    rec = {} if a.records_only else recompute(out, a.python)
    end_to_end(E)
    assembly(E)
    block_vs_refs(E)
    closed_forms_d12()
    specializations(E, rec.get('special'))
    dl_identity(E)
    topmode(E)
    review_codes(E)
    pslq(E)
    k3_column(E, rec.get('k3_log') or (PKG / E2E / 'e2e_k3.log').read_text())
    for rid in sorted(set(E.rows) - E.used):
        row('expected', rid, 'row of expected.json without a check', '-', '-', False)
    w = max(len(r['id']) for r in ROWS)
    print('%-12s %-*s %-6s %-34s %s' % ('group', w, 'check', 'status', 'got', 'expected'))
    for r in ROWS:
        print('%-12s %-*s %-6s %-34s %s%s' % (r['group'][:12], w, r['id'], r['status'], r['got'][:34], r['expected'],
                                             ('   # ' + r['note']) if r['note'] else ''))
    n = {s: sum(1 for r in ROWS if r['status'] == s) for s in ('PASS', 'FAIL', 'SKIP')}
    summary = dict(package='LRI_C5_general_d', date=dt.datetime.now().isoformat(timespec='seconds'),
                   python=sys.version.split()[0], mpmath=mp.__version__, records_only=a.records_only,
                   seconds=round(time.time() - t0, 1), counts=n, rows=ROWS)
    (out / 'replay.json').write_text(json.dumps(summary, indent=1) + '\n')
    print('\nreplay: %d PASS, %d FAIL, %d SKIP in %.0f s (python %s, mpmath %s); table in %s' % (
        n['PASS'], n['FAIL'], n['SKIP'], time.time() - t0, summary['python'], summary['mpmath'], out / 'replay.json'))
    sys.exit(1 if n['FAIL'] else 0)


if __name__ == '__main__':
    main()
