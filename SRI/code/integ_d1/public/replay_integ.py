#!/usr/bin/env python3
"""Replay of C^SR_8 from the integrable point, magnetization scheme (package integ_d1; new tool, 2026-10-18). Run from
code/integ_d1/. About a minute on one core.

The verbatim tools of the project (code/, results/ at commit 8bd5a22) run in a work copy (<work>/run) with the git
stand-in public/gitstub.py first on PATH (the public tree has no git history; see that file for the queries it
answers and what they prove). No record is written: every tool runs in its read-only mode.
 1. records   every record of results/frozen_records.json against its sha256; the six records of the note's App. I.8;
              the superseded first versions are marked superseded and stay frozen.
 2. rebuild   builds.py (the three engine build ids from the sources at their commits); m1_gate.py (C3);
              m2_gate.py --stage2 and m3_gate.py --stage2 (the two- and three-bubble records regenerated from their
              engine outputs, byte-identical, then C3..C7 against the closed forms); m4a_gate.py --dry (f_2_0_2:
              would-be record hash = frozen); m4b_gate.py --verify (f_3_0_1 from the three complete runs, the
              double-double overrides and both validation samples: record byte-identical, provenance sidecar
              reproduced); m4b_cx_check.py --amended --verify (confirmatory check, amendment A) and, without --amended,
              the original criterion (fails, as the frozen first record says); m3_sector_check.py --verify-record
              (three frozen checks of the three-bubble engine); c8_assemble.py --verify (record byte-identical) and
              --compare (the comparison stage, against results/C8_comparison.txt).
 3. app_i     every number the SRI note prints in App. I (gates, f_2_0_2, f_3_0_1 and its error budget, the 29 inputs
              of its input table, the C3..C7 table, C8, the comparisons, the amendments, the record hashes) from the
              verified records and the tool outputs; with the note present (../../note/sri_short_range.tex), each
              printed TeX string must occur in it.
 4. quoted    \\SRCeightMag, \\SRintegClosedDev, \\SRCeightMagDiff (paper macros, printed) from
              ../../results/quoted_numbers.json.
Tolerances: the rebuilt records must be byte-identical (sha256). Numbers printed in App. I: the recomputed value,
rounded half-up to the printed precision, must equal the printed text ('round'); a 25-digit table entry must equal the
record's decimal string ('exact'); statements of the form "to 10^-n" need round(log10|x|) = -n ('order');
"x..." needs the record to begin with the printed digits ('trunc').
Usage: python3 public/replay_integ.py [--work DIR] [--keep]
"""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
SRI = PKG.parent.parent
sys.path.insert(0, str(SRI/'verify'))
import sri_lib as SL  # noqa: E402

getcontext().prec = 60
APP_I8 = {  # the record table of the note's App. I.8 (sha256 as printed there)
    'C8_record_v2.json': '0d463b29d9ec474cacf2ab96afff62ae56b0ec262d766684ebbf0b7b8b20ec0c',
    'M2_flow_coefficients.json': '33cc2e1e9a6e9a57510b0b3c6a7ef419258317be892774c3054d04852161e833',
    'M3_flow_coefficients.json': '4328cab931ea96e953e9e6ba3789dfbfc0859c94f26fc8d38c1b1161eb271bce',
    'M4A_flow_coefficients.json': '584562ca72485e0f57c2f1e8ac6a05dcc5cc07b2acc73659a39587bd61641048',
    'M4B_flow_coefficients_v2.json': '90542a62db08d875995f2944e84ec7d6ff8987acc1b50892cd459d7e632d9899',
    'M4B_cx_check_v2.json': '66287b2af2f4c5352a1c15dc07edf6b381c2215f54b5b979fe726f4febf0f1fb',
}
SUPERSEDED = {'C8_record.json': 'C8_record_v2.json', 'M4B_flow_coefficients.json': 'M4B_flow_coefficients_v2.json',
              'M4B_cx_check.json': 'M4B_cx_check_v2.json'}
TABLE8 = [  # (index, printed value) of the note's input table tab:integ:inputs, in its order
    ('1_0_0', '1'), ('1_1_0', '6.579736267392905745889661'), ('1_2_0', '42.00883821061607434137304'),
    ('1_3_0', '174.5896405924634503829158'), ('2_0_0', '45.29870634431252721431787'),
    ('2_1_0', '777.0075210550932975552262'), ('2_2_0', '8099.313348527777075847784'),
    ('3_0_0', '3848.445467772377268238629'), ('3_1_0', '115632.5319783609240553502'),
    ('4_0_0', '545193.0244029872263588049'), ('0_0_1', '-0.5772156649015328606065121'),
    ('0_1_1', '-3.867083798597985733551342'), ('0_2_1', '-8.098095746334830014543783'),
    ('0_3_1', '-13.46681348232748267372698'), ('0_0_2', '5.292133223877124175286'),
    ('0_1_2', '43.26016741947440932389841'), ('0_2_2', '194.2323046570014639460987'),
    ('0_0_3', '-61.14566451935350750983253'), ('0_1_3', '-767.6867345496617072942533'),
    ('1_0_1', '-36.49853744243762329795634'), ('1_1_1', '-404.1590010240865956167455'),
    ('1_2_1', '-2982.066378636498938272215'), ('1_0_2', '810.9918099349166764628352'),
    ('1_1_2', '14885.33541859945105628608'), ('1_0_3', '-23498.57164495448058791384'),
    ('2_0_1', '-3157.008605154717628460989'), ('2_1_1', '-75994.36349692199322461628'),
    ('2_0_2', '172415.8301856328384692596'), ('3_0_1', '-514275.7548978331544915535'),
]
C37_TABLE = {3: ('5.72736813369645287294483', '5.72736813369645287294483', '3e-39'),
             4: ('-12.19619149266966002908757', '-12.19619149266966002908757', '2e-29'),
             5: ('29.23781158099003956882694', '29.23781158099003956882694', '3e-28'),
             6: ('-58.66569747422530894971715', '-58.66569747422530894971715', '7e-26'),
             7: ('51.06898861292810883118393', '51.06898861292810883118394', '4e-26')}


# ---------------------------------------------------------------------------------------------------------------- tools
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def setup(work):
    """work copy of code/ and results/, and the git wrapper on a private PATH"""
    shutil.rmtree(work, ignore_errors=True)
    run = work/'run'
    run.mkdir(parents=True)
    for d in ('code', 'results'):
        shutil.copytree(PKG/d, run/d, ignore=shutil.ignore_patterns('__pycache__'))
    (work/'bin').mkdir()
    (work/'logs').mkdir()
    g = work/'bin'/'git'
    g.write_text('#!/bin/sh\nexec "%s" "%s" "$@"\n' % (sys.executable, HERE/'gitstub.py'))
    g.chmod(0o755)
    # PATH: the git wrapper first, then the directory of this interpreter (m1_gate.py starts 'python3' with
    # executable=sys.executable; a virtual-environment interpreter started under the bare name finds its prefix on PATH)
    env = dict(os.environ, PATH=os.pathsep.join([str(work/'bin'), os.path.dirname(sys.executable), os.environ.get('PATH', '')]),
               INTEG_GITSTUB_LOG=str(work/'gitstub.log'), PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1')
    return run, env


def tool(name, args, run, env, work, times):
    t0 = time.time()
    r = subprocess.run([sys.executable] + args, cwd=run/'code', env=env, capture_output=True, text=True)
    times[name] = time.time() - t0
    out = r.stdout + r.stderr
    (work/'logs'/(name + '.txt')).write_text(out)
    return r.returncode, out


def D(x):
    return Decimal(str(x))


def round_to(value, printed):
    """value (Decimal) rounded half-up to the precision of `printed` ('-514275.75', '1.7e-7', '+34.8')"""
    p = printed.lstrip('+')
    mant, _, exp = p.partition('e')
    exp = int(exp) if exp else 0
    nd = len(mant.split('.')[1]) if '.' in mant else 0
    q = Decimal(1).scaleb(exp - nd)
    return value.quantize(q, rounding=ROUND_HALF_UP)


def judge(rule, value, printed):
    """(ok, shown) for the App. I comparison rules"""
    if rule == 'round':
        r = round_to(value, printed)
        return r == D(printed.lstrip('+')), str(r)
    if rule == 'exact':
        return value == D(printed), str(value)
    if rule == 'order':
        # "to 10^-n": the value lies in [10^(-n-1/2), 10^(-n+1)), i.e. -n is its rounded or its leading decimal exponent
        x, n = math.log10(abs(float(value))), int(printed.partition('e')[2])
        return n - 0.5 <= x < n + 1, '%.2e' % float(value)
    if rule == 'trunc':
        s = str(value)
        return s.startswith(printed), s[:len(printed) + 3]
    if rule == 'int':
        return int(value) == int(printed), str(int(value))
    raise ValueError(rule)


def grab(pattern, text, cast=Decimal, group=1):
    m = re.search(pattern, text, re.M)
    return cast(m.group(group)) if m else None


# ---------------------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=str(PKG/'.work'/'replay'))
    ap.add_argument('--keep', action='store_true', help='keep the work copy')
    a = ap.parse_args()
    work = Path(a.work).resolve()
    T = SL.Table('integ_d1 replay: C^SR_8 from the integrable point (magnetization scheme)')
    t_start = time.time()
    times = {}
    RES = PKG/'results'
    reg = json.loads((RES/'frozen_records.json').read_text())

    # 1. records ------------------------------------------------------------------------------------------------------
    bad = [n for n, e in reg.items() if not (RES/n).exists() or sha(RES/n) != e['sha256']]
    T.check('records: frozen-record registry', not bad, '%d records%s' % (len(reg), '; differ: %s' % bad if bad else ''),
            'every sha256 = registry', 'results/frozen_records.json; sha256 of the shipped file')
    bad = [n for n, h in APP_I8.items() if reg.get(n, {}).get('sha256') != h or sha(RES/n) != h or 'superseded_by' in reg.get(n, {})]
    T.check('records: the six of App. I.8', not bad, '6 records, current%s' % ('; differ: %s' % bad if bad else ''),
            'sha256 as printed', 'C8 v2, M2, M3, M4A, M4B v2, cx v2: file = registry = note, not superseded')
    bad = [n for n, by in SUPERSEDED.items() if reg.get(n, {}).get('superseded_by') != by]
    T.check('records: superseded first versions', not bad, 'C8 v1, M4B v1, cx v1 superseded by v2, still frozen%s' % (
        '; wrong: %s' % bad if bad else ''), 'superseded_by v2', 'kept frozen and shipped because App. I.7 cites them')

    # 2. rebuild ------------------------------------------------------------------------------------------------------
    run, env = setup(work)
    R, P = run/'results', run/'results'/'m4_runs'/'prod'
    rc, out = tool('builds', ['builds.py'], run, env, work, times)
    T.check('rebuild: engine build ids', rc == 0 and out.count('ok ') == 3, '%d of 3 reproduced' % out.count('ok '),
            '3 of 3', 'builds.py: sha256 of the engine sources at the build commit + compile command = recorded id')
    rc, out1 = tool('m1_gate', ['m1_gate.py'], run, env, work, times)
    T.check('rebuild: M1 (C3 from exact inputs)', rc == 0 and 'PASS' in out1, 'exit %d' % rc, 'PASS', 'm1_gate.py')
    m2rec = json.loads((R/'M2_flow_coefficients.json').read_text())
    rc, out2 = tool('m2_gate', ['m2_gate.py', m2rec['source'], '--stage2', '--expect-sha', APP_I8['M2_flow_coefficients.json']],
                    run, env, work, times)
    T.check('rebuild: M2 record (two bubbles)', rc == 0 and 'M2 GATE PASS' in out2, 'exit %d' % rc, 'M2 GATE PASS',
            'm2_gate.py --stage2: regenerated record = frozen file and hash, sidecar, C3..C5 vs closed forms <= 1e-20')
    rc, out3 = tool('m3_gate', ['m3_gate.py', str(R/'m3_runs'/'s3'), '--stage2', '--expect-sha',
                                APP_I8['M3_flow_coefficients.json']], run, env, work, times)
    T.check('rebuild: M3 record (three bubbles)', rc == 0 and 'M3 GATE PASS' in out3, 'exit %d' % rc, 'M3 GATE PASS',
            'm3_gate.py --stage2: regenerated record = frozen, sidecar, C3..C7 vs closed forms <= 1e-20')
    rc, out4a = tool('m4a_gate', ['m4a_gate.py', str(R/'m4_runs'/'n3d2_B'), str(R/'m4_runs'/'n3d2_A'), '--dry'], run, env, work, times)
    wb = grab(r'would-be record (\S+)', out4a, str)
    T.check('rebuild: M4A record (f_2_0_2)', rc == 0 and 'M4A GATE (dry) PASS' in out4a and wb == APP_I8['M4A_flow_coefficients.json'],
            'exit %d, would-be %s' % (rc, (wb or '-')[:12]), 'PASS, 584562ca...', 'm4a_gate.py --dry: sha256 of the rebuilt record = frozen')
    gargs = ['m4b_gate.py', str(P/'F'), str(P/'C'), '--fine-dd', str(P/'Fdd'), '--coarse-dd', str(P/'Cdd'), '--radius', str(P/'R'),
             '--radius-dd', str(P/'Rdd'), '--dd-sample', str(P/'Vdd'), '--dd-sample2', str(P/'Vdd2'), '--verify']
    rc, outg = tool('m4b_gate', gargs, run, env, work, times)
    rep = [json.loads(l[len('VERIFY_REPORT_JSON '):]) for l in outg.splitlines() if l.startswith('VERIFY_REPORT_JSON ')]
    gv = rep[0] if len(rep) == 1 else {}
    ok = rc == 0 and 'M4B GATE (verify) PASS' in outg and gv.get('identical') is True and gv.get('sidecar_keys_ok') is True \
        and not gv.get('sidecar_fields_differing') and gv.get('rebuilt_sha256') == APP_I8['M4B_flow_coefficients_v2.json']
    nfail = sum(1 for c in gv.get('checks', []) if not c[3])
    T.check('rebuild: M4B v2 record (f_3_0_1)', ok, 'exit %d, %d gate checks (%d failed), identical %s' % (
        rc, len(gv.get('checks', [])), nfail, gv.get('identical')), 'PASS, byte-identical',
        'm4b_gate.py --verify: 3 runs + dd overrides + both dd samples; record and provenance sidecar reproduced')
    rc, outcx = tool('cx_v2', ['m4b_cx_check.py', str(P/'cxA'), str(P/'cxB'), '--amended', '--verify'], run, env, work, times)
    T.check('rebuild: confirmatory check v2', rc == 0 and 'M4B CX CHECK PASS' in outcx and 'VERIFY M4B_cx_check_v2.json IDENTICAL' in outcx,
            'exit %d' % rc, 'PASS, IDENTICAL', 'm4b_cx_check.py --amended --verify (amendment A criterion)')
    rc, outcx1 = tool('cx_v1_criterion', ['m4b_cx_check.py', str(P/'cxA'), str(P/'cxB'), '--dry'], run, env, work, times)
    v1 = json.loads((R/'M4B_cx_check.json').read_text())
    failb = re.search(r'cxB: J4\^\(0\)\(K\) vs Bethe ansatz \(relative\)\s+(\S+)\s+<=\s+1\.0e-12\s+FAIL', outcx1)
    passa = re.search(r'cxA: J4\^\(0\)\(K\) vs Bethe ansatz \(relative\)\s+(\S+)\s+<=\s+1\.0e-12\s+PASS', outcx1)
    ok = rc != 0 and failb and passa and v1['pass'] is False and failb.group(1) == v1['results'][1]['rel_diff'] \
        and passa.group(1) == v1['results'][0]['rel_diff']
    T.check('rebuild: original cx criterion fails', bool(ok), 'K_A %s PASS, K_B %s FAIL' % (passa and passa.group(1), failb and failb.group(1)),
            'as frozen in cx v1 (pass false)', 'm4b_cx_check.py --dry, threshold 1e-12 fixed before the runs')
    nsc = 0
    for n in ('K0.92_L3', 'K0.92_L4', 'K1.05_L3'):
        rec = json.loads((R/('M3_sector_check_%s.json' % n)).read_text())
        rc, o = tool('sector_check_' + n, ['m3_sector_check.py', str(run/rec['engine_output']['file'])] +
                     [str(run/c['file']) for c in rec['checks']] + ['--tol', rec['threshold'], '--verify-record',
                                                                     'M3_sector_check_%s.json' % n], run, env, work, times)
        nsc += rc == 0 and 'SECTOR CHECK PASS' in o and ('VERIFY M3_sector_check_%s.json IDENTICAL' % n) in o
    T.check('rebuild: three-bubble sector checks', nsc == 3, '%d of 3 identical' % nsc, '3 of 3',
            'm3_sector_check.py --verify-record (independent checker vs engine, frozen records)')
    g3files = sorted((R/'m3_runs'/'g2g3').glob('*_L2.out'))
    rc, outg3 = tool('cluster_check_n3', ['cluster_check.py', '3'] + [str(f) for f in g3files], run, env, work, times)
    g3rel = {'real': [], 'cx': []}
    for m in re.finditer(r'^(\S+)\s+K=\s*\((\S+) ([+-]) (\S+)j\).* rel\.diff=(\S+)', outg3, re.M):
        g3rel['real' if D(m.group(4)) == 0 else 'cx'].append(D(m.group(5)))
    T.check('rebuild: three-bubble engine vs exact cluster', rc == 0 and len(g3rel['real']) == 4 and len(g3rel['cx']) == 3,
            '%d real-K, %d complex-K outputs' % (len(g3rel['real']), len(g3rel['cx'])), '4 + 3',
            'cluster_check.py 3 on the level-2 outputs of results/m3_runs/g2g3 (J3^(0) vs the exact cluster)')
    rc, out8 = tool('c8_verify', ['c8_assemble.py', '--verify'], run, env, work, times)
    T.check('rebuild: C8 v2 record', rc == 0 and 'C8 ASSEMBLY (verify) PASS' in out8 and 'VERIFY C8_record_v2.json IDENTICAL' in out8,
            'exit %d' % rc, 'PASS, IDENTICAL', 'c8_assemble.py --verify: C3..C8 and the uncertainty, record byte-identical')
    rc, outc = tool('c8_compare', ['c8_assemble.py', '--compare', '--expect-sha', APP_I8['C8_record_v2.json']], run, env, work, times)
    shipped = (RES/'C8_comparison.txt').read_text()
    blk = lambda s: s[s.find('Stage 2: comparison'):s.find('C8 COMPARISON checks')] if 'Stage 2: comparison' in s else None
    T.check('rebuild: comparison stage', rc == 0 and 'C8 COMPARISON PASS' in outc and blk(outc) is not None and blk(outc) == blk(shipped),
            'exit %d; stage-2 block %s' % (rc, 'identical to results/C8_comparison.txt' if blk(outc) == blk(shipped) else 'differs'),
            'PASS, same text', 'c8_assemble.py --compare --expect-sha 0d463b29...: gated on the current records and a passing cx check')
    q = {}
    if (work/'gitstub.log').exists():
        for line in (work/'gitstub.log').read_text().splitlines():
            k = line.split('\t')[0]
            q[k] = q.get(k, 0) + 1
    T.add('rebuild: git stand-in queries', 'INFO', ', '.join('%s %d' % kv for kv in sorted(q.items())) or 'none', '-',
          'answered from public/git_blobs.json (content identity with the committed blobs; commit order not provable here)')

    # 3. App. I numbers -----------------------------------------------------------------------------------------------
    c8 = json.loads((RES/'C8_record_v2.json').read_text())
    c8v1 = json.loads((RES/'C8_record.json').read_text())
    m3 = json.loads((RES/'M3_flow_coefficients.json').read_text())
    m4a = json.loads((RES/'M4A_flow_coefficients.json').read_text())
    m4b = json.loads((RES/'M4B_flow_coefficients_v2.json').read_text())
    cx2 = json.loads((RES/'M4B_cx_check_v2.json').read_text())
    design = json.loads((RES/'m4_inputs'/'cx_v2_design.json').read_text())
    dry = (RES/'M4B_gate_v2_dry.txt').read_text()
    e = m4b['errors']
    dv = m4b['dd_validation_sample']
    st = dv['strata']
    rows = dv['rows']
    C8, sC8 = D(c8['C8']), D(c8['C8_error'])
    rels = {int(m.group(1)): D(m.group(2)) for m in re.finditer(r'^\s+C(\d): .* rel (\S+)$', out8, re.M)}
    vals = {int(m.group(1)): D(m.group(2)) for m in re.finditer(r'^\s+C(\d):\s+(\S+)\s+exact', out8, re.M)}
    m2diff = {int(m.group(1)): D(m.group(2)) for m in re.finditer(r'^C(\d): pipeline \S+\s+compendium \S+\s+diff (\S+)', out2, re.M)}
    m3rel = {int(m.group(1)): D(m.group(2)) for m in re.finditer(r'^\s+C(\d) vs compendium \(relative\)\s+(\S+)', out3, re.M)}
    m1diff = grab(r'^difference\s+=\s+(\S+)', out1)
    nrel_m2 = len(re.findall(r'^\s+relation \[d\^\d w\^-?\d+\] \(relative\)', out2, re.M))
    nrel_m4a = len(re.findall(r'^\s+fine: relation \[d\^2 w\^-?\d+\]', out4a, re.M))
    nrel_m4b = len([c for c in gv.get('checks', []) if re.match(r'fine: relation \[d\^1 w\^-?\d+\] \(relative\)', c[0])])
    sc = {n: json.loads((RES/('M3_sector_check_%s.json' % n)).read_text()) for n in ('K0.92_L3', 'K0.92_L4', 'K1.05_L3')}
    # fine-level bounds eps*B per stratum and of the first 40 sampled sectors, as fixed in the two designs (the gate's
    # --verify above recomputes the strata from the fine level and checks them)
    d3 = json.loads((RES/'m4_inputs'/'fix3_design.json').read_text())
    d3b = json.loads((RES/'m4_inputs'/'fix3b_design.json').read_text())
    sbound = {k: D(v) for k, v in d3b['stratum_bound'].items()}
    share = (sbound['rank9_24'] + sbound['decile10']) / sum(sbound.values())
    orig_nonsampled = sum(sbound.values()) - sum(D(v) for v in d3['fine_bound_eps_B'].values())
    dry_total = grab(r'f_3_0_1 error \|fine - coarse\| \+ \|fine - radius\| \+ validated roundoff \(absolute\)\s+(\S+)', dry)
    dry_nonsampled = grab(r'roundoff estimate 4\.11 x (\S+) \+', dry)
    indep = None
    ind_file = PKG.parent/'indep_d1'/'RESULTS_C8_independent.json'
    if ind_file.exists():
        o = json.loads(ind_file.read_text())['step1']['outputs']['C8']
        indep = (D(o['value']), D(o['sigma']))
    ref_rec = D('247.3812048049935')
    d_rec = C8 - ref_rec
    rows_i = []   # (name, printed, value, rule, tex)

    def row(name, printed, value, rule, tex=None):
        rows_i.append((name, printed, value, rule, tex))
    # I.7 gates
    row('C3 (M1, absolute)', '2e-38', abs(m1diff) if m1diff is not None else None, 'round', r'\sci{2}{-38}')
    row('two bubbles: delta^0 vs BA', '4e-32', D(m2rec['delta0_vs_BA_max_rel']), 'round', r'\sci{4}{-32}')
    row('two bubbles: number of relations', '36', nrel_m2, 'int', 'all 36 analyticity relations')
    row('two bubbles: relations', '1e-28', D(m2rec['relations_max_rel']), 'order', '$10^{-28}$')
    row('f_101 (printed in advance)', '-36.49853744243762', D(m2rec['flow_coefficients']['f_1_0_1']), 'trunc', r'f_{101}=-36.49853744243762\ldots')
    row('C4 (M2, absolute)', '3e-28', abs(m2diff.get(4, D(0))), 'round', r'\sci{3}{-28}')
    row('C5 (M2, absolute)', '1e-26', abs(m2diff.get(5, D(0))), 'order', '$10^{-26}$ (absolute)')
    row('three bubbles: engine vs exact cluster, real v', '1e-23', max(g3rel['real']) if g3rel['real'] else None, 'order', '$10^{-23}$ at real $v$')
    row('three bubbles: engine vs exact cluster, complex v', '1e-28', max(g3rel['cx']) if g3rel['cx'] else None, 'order', '$10^{-28}$ at complex $v$')
    row('three bubbles: relations', '1e-27', D(m3['relations_max_rel']), 'order', '$10^{-27}$')
    row('C6 (M3, absolute)', '4e-24', m3rel.get(6, D(0)) * abs(vals.get(6, D(1))), 'round', r'\sci{4}{-24}')
    row('C7 (M3, absolute)', '2e-24', m3rel.get(7, D(0)) * abs(vals.get(7, D(1))), 'round', r'\sci{2}{-24}')
    row('f_202: delta^0 vs BA', '4e-23', D(m4a['checks']['delta0_vs_BA_max_rel']), 'round', r'\sci{4}{-23}')
    row('f_202: delta^1 vs frozen M3', '9e-24', D(m4a['checks']['delta1_vs_M3_max_rel']), 'round', r'\sci{9}{-24}')
    row('f_202: number of delta^2 relations', '12', nrel_m4a, 'int', 'all twelve $\\db^2$ analyticity relations')
    row('f_202: delta^2 relations', '4e-24', D(m4a['checks']['delta2_relations_max_rel_fine']), 'round', r'\sci{4}{-24}')
    row('f_202', '172415.83018563', D(m4a['flow_coefficients']['f_2_0_2']), 'round', r'f_{202}=172415.83018563')
    row('f_202 two-grid error', '1.7e-7', D(m4a['errors']['f_2_0_2_two_grid']), 'round', r'\pm\sci{1.7}{-7}')
    ddn = m4b['dd_sectors']
    row('f_301: dd overrides at 0.2 (fine = coarse)', '8', ddn['fine'] if ddn['fine'] == ddn['coarse'] else -1, 'int', '(8 at ratio $0.2$')
    row('f_301: dd overrides at 0.3 (radius)', '14', m4b['dd_sectors']['radius'], 'int', '14 at $0.3$)')
    row('f_301: delta^0 vs exact cluster', '4e-11', D(m4b['checks']['delta0_vs_BA_max_rel']['fine']), 'round', r'\sci{4}{-11}')
    row('f_301: number of delta^1 relations', '12', nrel_m4b, 'int', 'all twelve $\\db^1$ analyticity relations')
    row('f_301: delta^1 relations', '7e-12', D(m4b['checks']['delta1_relations_max_rel']['fine']), 'round', r'\sci{7}{-12}')
    row('confirmatory check K_A', '1.7e-14', D(cx2['results'][0]['rel_diff']), 'round', r'\sci{1.7}{-14}')
    row('confirmatory check K_B', '1.6e-12', D(cx2['results'][1]['rel_diff']), 'round', r'\sci{1.6}{-12}')
    row('roundoff: further dd sectors', '56', len(rows), 'int', '56 further sectors')
    row('roundoff: next-largest bounds', '16', sum(1 for r in rows if r[1] == 'rank9_24'), 'int', '16 with the next-largest bounds')
    row('roundoff: drawn by decile', '24', sum(1 for r in rows if r[1].startswith('decile') and r[4] == 'old'), 'int', '24 drawn by bound decile')
    row('roundoff: held-out sample', '16', sum(1 for r in rows if r[4] == 'new' and r[1] in ('decile9', 'decile10')), 'int', '16 from the two top deciles')
    row('roundoff: max ratio, top 16 + top decile', '2.5e-3', max(D(st['rank9_24']['ratio_max']), D(st['decile10']['ratio_max'])), 'round', r'\sci{2.5}{-3}')
    row('roundoff: bound share of top 16 + top decile (%)', '98', share * 100, 'round', 'about 98\\%')
    row('roundoff: max ratio, decile 9', '1.3e-2', D(st['decile9']['ratio_max']), 'round', r'\sci{1.3}{-2}')
    row('roundoff: max ratio, any sector', '0.41', max(D(v['ratio_max']) for v in st.values()), 'round', 'reaches $0.41$')
    row('f_301', '-514275.75', D(m4b['flow_coefficients']['f_3_0_1']), 'round', r'f_{301}=-514275.75\pm0.17')
    row('f_301 uncertainty (2 digits)', '0.17', D(e['f_3_0_1_total']), 'round', r'-514275.75\pm0.17')
    row('f_301 uncertainty', '0.174', D(e['f_3_0_1_two_grid']) + D(e['f_3_0_1_radius_diff']) + D(e['roundoff_estimate_fine']), 'round', 'uncertainty, $0.174$')
    row('fine - coarse', '0.016', D(e['f_3_0_1_two_grid']), 'round', 'difference $0.016$')
    row('fine - radius', '0.022', D(e['f_3_0_1_radius_diff']), 'round', 'difference $0.022$')
    row('validated roundoff estimate', '0.137', D(e['roundoff_estimate_fine']), 'round', 'estimate $0.137$')
    for n in (3, 4, 5, 6, 7):
        mag, cf, rl = C37_TABLE[n]
        row('C%d (assembly)' % n, mag, D(c8['C3_C7']['C%d' % n]), 'exact', mag)
        row('C%d closed form' % n, cf, D(closed_form(n)), 'round', cf)
        row('C%d relative difference' % n, rl, rels.get(n, D(0)), 'round', r'\sci{%s}{%s}' % tuple(rl.split('e')))
    row('C8', '247.381179745789', C8, 'round', r'\CSR_8=247.381179745789\pm0.131')
    row('C8 uncertainty', '0.131', sC8, 'round', r'247.381179745789\pm0.131')
    row('C8 (quoted)', '247.38118', C8, 'round', r'247.38118\pm0.13')
    row('3/4 x 0.174', '0.13', D(c8['components']['0.75*sigma_f_3_0_1']), 'round', r'\frac34\times0.174=0.13')
    row('from f_202', '3.3e-7', D(c8['components']['2*sigma_f_2_0_2']), 'round', r'\sci{3.3}{-7}')
    row('from all other inputs', '3.6e-15', D(c8['components']['other_inputs']), 'round', r'\sci{3.6}{-15}')
    row('number of inputs', '29', len(c8['inputs']), 'int', 'lists the 29 inputs')
    for idx, pv in TABLE8:
        row('input f_%s' % idx.replace('_', ''), pv, D(c8['inputs']['f_' + idx]), 'exact', pv)
    # reassembly from the printed 25-digit values (mscheme_numeric of the work copy)
    sys.path.insert(0, str(run/'code'))
    import mpmath as mp
    from mscheme_numeric import C_numeric
    mp.mp.dps = 40
    fuse = {tuple(int(x) for x in idx.split('_')): mp.mpf(pv) for idx, pv in TABLE8}
    Cp = C_numeric(fuse, 4)
    relp = [abs((Cp[n - 1] - mp.mpf(closed_form(n))) / mp.mpf(closed_form(n))) for n in (3, 4, 5, 6, 7)]
    row('reassembled C8 from the printed inputs', '247.381179745789', D(mp.nstr(Cp[7], 30)), 'round', None)
    row('reassembled C3..C7: smallest relative difference', '1e-25', D(mp.nstr(min(relp), 5)), 'order', '$10^{-25}$ to')
    row('reassembled C3..C7: largest relative difference', '2e-22', D(mp.nstr(max(relp), 5)), 'round', r'\sci{2}{-22}')
    # I.8 comparison
    row('Delta vs the record', '-2.506e-5', d_rec, 'round', r'\sci{-2.506}{-5}')
    row('Delta / 0.131 vs the record', '-0.0002', d_rec / sC8, 'round', '$-0.0002$')
    if indep:
        iv, isg = indep
        row('independent value (indep_d1 record)', '242.825', iv, 'round', r'$242.825\pm2.371$')
        row('independent uncertainty', '2.371', isg, 'round', r'242.825\pm2.371')
    else:
        iv, isg = D('242.825'), D('2.371')
        T.add('App. I: independent value', 'SKIP', '../indep_d1 absent', '242.825 +- 2.371', 'printed values used below')
    row('Delta vs independent', '+4.556', C8 - iv, 'round', '$+4.556$')
    row('Delta / 0.131 vs independent', '+34.8', (C8 - iv) / sC8, 'round', '$+34.8$')
    row('Delta / own error vs independent', '+1.92', (C8 - iv) / isg, 'round', '$+1.92$')
    row('Delta vs 242.83 (comparison stage)', '+4.551', grab(r'independent estimate .*\n\s+difference Delta = (\S+);', outc), 'round', r'\Delta=+4.551')
    # disclosures
    row('first version C8', '247.38118', D(c8v1['C8']), 'round', r'$247.38118\pm0.077$')
    row('first version uncertainty', '0.077', D(c8v1['C8_error']), 'round', r'247.38118\pm0.077')
    row('A: K_B relative difference', '1.6e-12', D(v1['results'][1]['rel_diff']), 'round', r'($\sci{1.6}{-12}$')
    row('A: original criterion', '1e-12', D(v1['threshold']), 'round', 'criterion $10^{-12}$')
    row('A: K_B own roundoff bound', '1.7e-9', D(cx2['results'][1]['roundoff_bound_rel']), 'round', r'\sci{1.7}{-9}')
    row('A: dd rerun (core-hours, design projection)', '1.7e4', D(design['cost_projection']['dd_rerun_core_h_model']), 'round', r'\sci{1.7}{4}')
    row('A: amended criterion', '1e-11', D(cx2['threshold']), 'round', 'at most $10^{-11}$')
    row('B: global factor-ten rule, roundoff (dry run)', '21.3', D('4.11') * dry_nonsampled if dry_nonsampled else None, 'round', None)
    row('B: non-sampled bound before the held-out sample', '5.184', orig_nonsampled, 'round', None)
    row('B: uncertainty of C8 under the global rule', '16', D('0.75') * dry_total + D(c8['components']['2*sigma_f_2_0_2'])
        if dry_total else None, 'round', 'about 16')
    nh = sum(1 for r in rows if r[4] == 'new')
    newmax = {s: max([D(r[2]) for r in rows if r[1] == s and r[4] == 'new'] or [D(0)]) for s in ('decile9', 'decile10')}
    oldmax = {s: max([D(r[2]) for r in rows if r[1] == s and r[4] == 'old'] or [D(0)]) for s in ('decile9', 'decile10')}
    ok = nh == 16 and all(newmax[s] <= 10 * oldmax[s] for s in newmax) and all(D(st[s]['ratio_max']) <= D('0.1') for s in ('rank9_24', 'decile9', 'decile10'))
    T.check('App. I: held-out sample within the margin', ok, 'new max %s vs 10 x old max %s' % (
        {s: str(v) for s, v in newmax.items()}, {s: str(10 * v) for s, v in oldmax.items()}), 'new <= 10 x old; stop strata <= 0.1',
        'fix3b_design.json rule; rows of the M4B v2 dd_validation_sample')
    note = SRI/'note'/'sri_short_range.tex'
    tex = note.read_text() if note.exists() else None
    if tex is not None:
        i0, i1 = tex.find(r'\label{app:integ}'), tex.find(r'\begin{thebibliography}')
        tex = tex[i0:i1] if i0 >= 0 else tex
    missing = []
    for name, printed, value, rule, t in rows_i:
        if value is None:
            T.check('App. I: ' + name, False, 'not computed', printed, rule)
            continue
        ok, shown = judge(rule, value if isinstance(value, Decimal) else D(value), printed)
        T.check('App. I: ' + name, ok, shown, printed, rule)
        if tex is not None and t is not None and t not in tex:
            missing.append(t)
    for n, h in APP_I8.items():
        if tex is not None and h not in tex:
            missing.append(h[:12])
    if tex is None:
        T.add('App. I: printed strings in the note', 'SKIP', '../../note/sri_short_range.tex absent', '-', '-')
    else:
        T.check('App. I: printed strings in the note', not missing, '%d strings checked%s' % (
            sum(1 for r in rows_i if r[4]) + len(APP_I8), '; not found: %s' % missing[:6] if missing else ''),
            'all found', 'each printed TeX string of the rows above occurs in App. I of the note')
    T.add('App. I: compute (core-hours)', 'INFO', 'engine node-seconds in the records: M4B %.0f, M4A %.0f, M3 %.0f' % (
        sum(m4b['engine_node_seconds'].values()), sum(m4a['engine_cpu_seconds'].values()), m3['engine_cpu_seconds']),
        'about 2.7e4 core-hours', 'from the cluster accounting of all jobs (failed and auxiliary ones included); not recomputable from the records')

    # 4. quoted macro -------------------------------------------------------------------------------------------------
    try:
        macros, _ = SL.quoted()
        ent = macros.get('\\SRCeightMag')
    except (OSError, ValueError):
        ent = None
    if ent is None:
        T.add('\\SRCeightMag', 'FAIL', 'macro missing from ../../results/quoted_numbers.json', '247.38\\pm0.13', '-')
    else:
        T.quoted(ent, [float(C8), float(sC8)], 'C8 and its empirical uncertainty (C8_record_v2.json, rebuilt above), half-up')
        T.check('\\SRCeightMag package', ent.get('package') == 'integ_d1', ent.get('package'), 'integ_d1', 'quoted_numbers.json')
    # the two checks printed in the paper's Sec. 3.2 (from paper ffc64564): the relative differences come from the
    # unrounded assembly (c8_assemble.py --verify above, 40 digits), not from the record's 25-digit strings
    max_rel = max(rels.get(n, D('inf')) for n in (3, 4, 5, 6, 7))
    for name, vals_, rule, absolute in (
            ('\\SRintegClosedDev', [float(max_rel)], 'max relative |C_n(scheme) - closed form|, n = 3..7, unrounded assembly', False),
            ('\\SRCeightMagDiff', [float(abs(d_rec))], '|eq:C8integ - eq:C8num| (C8_record_v2.json - 247.3812048049935)', True)):
        e_ = macros.get(name) if ent is not None else None
        if e_ is None:
            T.add(name, 'SKIP', 'not in ../../results/quoted_numbers.json', '-', rule)
        else:
            T.quoted(e_, vals_, rule, absolute=absolute)
    T.add('timing', 'INFO', ', '.join('%s %.1fs' % kv for kv in times.items()), '-', 'total %.0f s' % (time.time() - t_start))
    st_ = T.report(work.parent/'replay_integ_table.txt')
    if not a.keep and st_ == 0:
        shutil.rmtree(work/'run', ignore_errors=True)
    sys.exit(st_)


def closed_form(n):
    """C3..C7 closed forms of the note's Eq. (closed), evaluated with mpmath at 40 digits, as a 30-digit string"""
    import mpmath as mp
    mp.mp.dps = 40
    z = mp.zeta
    ex = {3: mp.mpf(39) / 16 + 2 * z(2),
          4: 4 - 4 * z(2) - 8 * z(3),
          5: mp.mpf(11249) / 1024 - mp.mpf(361) / 16 * z(2) + 24 * z(3) + mp.mpf(49) / 2 * z(4),
          6: 26 - 38 * z(2) + 104 * z(3) - 80 * z(4) - 272 * z(5) + 112 * z(2) * z(3),
          7: mp.mpf(1798583) / 32768 - mp.mpf(90637) / 1024 * z(2) + mp.mpf(453) / 4 * z(3) - mp.mpf(16835) / 64 * z(4)
             + 1224 * z(5) - 540 * z(2) * z(3) + mp.mpf(4335) / 8 * z(6) - 320 * z(3) ** 2}
    return mp.nstr(ex[n], 30)


if __name__ == '__main__':
    main()
