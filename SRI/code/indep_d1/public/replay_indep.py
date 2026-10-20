#!/usr/bin/env python3
"""Replay of the independent re-derivation of C^SR_5..C^SR_8 (package indep_d1; new tool, 2026-10-15). Run from
code/indep_d1/.

Every step runs the verbatim assembly scripts of the snapshot in a work copy (<work>/<step>/run); the raw per-sector
engine outputs are replaced by their sufficient statistics, public/pooled_sector_record.json (public/pooled_shim.py),
unless --raw DIR points at the raw chunk outputs (make replay-raw).
 1. reports   assembly/make_report.py, make_report_C8.py, make_report_C8_tierA.py on the shipped RESULTS json files:
              RESULTS.md, RESULTS_C8.md, RESULTS_C8_tierA.md must be byte-identical.
 2. p2        assembly/run_assembly.py main() (phase 2): the framework (strict, per replicate) on the engine's
              framework_input_final.json (116 raw scalars, R = 6), the three error estimators, the archive-free checks;
              the regenerated RESULTS_independent.json is compared with the shipped one.
 3. c8        assembly/run_assembly_C8.py step1(), w_three_ways(), separate_files_check() (phase 4): production +
              tiers A, B, C (201 raw scalars); compared with RESULTS_C8_independent.json step1.
 4. cmp2/cmp8 assembly/compare_archive.py, compare_archive_C8.py main(): the comparisons with the sealed archive values
              and the claimed closed forms, regenerated and compared with the shipped RESULTS_*archive_comparison.json.
 5. quoted    \\SRCeightIndep (note only since paper e89a94a0), \\SRCeightPull, \\SRCeightPullMax, \\SRindepPullMax (note
              only since paper c9adefbf): INFO rows (../../results/quoted_numbers.json, package indep_d1) from
              the recomputed values of steps 2-3, with the claims taken from the paper's eq:sr-closed and eq:sr-C8
              (quoted_numbers.json "equations", evaluated with mpmath at 50 digits); and the cited checks: C5, C6, D4,
              C7 with their pulls, the 25-input rms pull, J9, A9[eps^0 l^1] and the localisation of the C8 difference.
Tolerances: the framework is deterministic (mpmath, 50 digits), so central values must agree to 1e-24 relative and the
linear and replicate errors to 1e-12; the sector-pooled errors come from the record (exact for the six large jobs,
verbatim for the others) and must agree to 1e-6 of the quoted error of the same quantity; per-job diagnostics that
enter no quoted error (replicate projections, per-job maxima, shares), which the verbatim code sums in double precision
over up to 20,160 sectors, to 1e-2 of it.
Usage: python3 public/replay_indep.py [--work DIR] [--raw DIR] [--steps reports,p2,c8,cmp2,cmp8]
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
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG.parent.parent/'verify'))
import sri_lib as SL  # noqa: E402
import mpmath as mp  # noqa: E402

RECORD = HERE/'pooled_sector_record.json'
RAW_RUNS = ['prod_6digit', 'prod_6digit_topup1', 'poles1', 'c8tierA', 'c8tierA_topup1', 'c8tierB_s0.01_r1',
            'c8tierB_s0.01_can', 'c8tierB_s0.01_topup1', 'c8tierC_s3_r2', 'c8tierC_s3_can', 'c8tierC_s3_topup1']
PATH_KEYS = {'input_final', 'input_tier1', 'archive_files', 'date', 'results_independent_mtime', 'path', 'source',
             'run', 'main', 'merged', 'file'}


# ----------------------------------------------------------------------------------------------------------------------
def work_copy(dst, raw=None):
    """copy of the package (without public/, .work/) at dst/run; with raw, the raw *.cfg.json files are linked in"""
    run = dst/'run'
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(PKG, run, ignore=shutil.ignore_patterns('public', '.work', '__pycache__', 'public.mk'))
    for d in ('out/C8_ABC', 'out/C8'):            # log directories of the verbatim scripts (logs are not shipped)
        (run/'assembly'/d).mkdir(parents=True, exist_ok=True)
    if raw:
        for r in RAW_RUNS:
            src = Path(raw)/'engine'/'runs'/r
            for f in sorted(src.glob('*.cfg.json')):
                tgt = run/'engine'/'runs'/r/f.name
                if not tgt.exists():
                    os.symlink(f.resolve(), tgt)
    return run


def step(mode, run, record, out=None, log=None):
    cmd = [sys.executable, '-B', str(HERE/'run_step.py'), mode] + (['--record', str(record)] if record else []) + \
          (['--out', str(out)] if out else [])
    t0 = time.time()
    r = subprocess.run(cmd, cwd=run/'assembly', capture_output=True, text=True)
    if log:
        Path(log).write_text(r.stdout + r.stderr)
    return r.returncode, time.time() - t0, (r.stdout + r.stderr)[-3000:]


PLACEHOLDER = re.compile(r'<(PROJECT|HOME|DATA|SCRATCH|USER|NODE|TMP|PROJECTS|ACCOUNT|PAPER)>|personal desktops?')


def same_report(shipped, regen):
    """byte-identical; or identical up to (a) the status note added by hand to RESULTS_C8_tierA.md on 2026-10-06 and
    (b) the placeholders of the public repository's scrub (files listed in public/SCRUBBED.txt)"""
    a, b = Path(shipped).read_bytes(), Path(regen).read_bytes()
    if a == b:
        return True, 'byte-identical'
    la, lb = a.decode().splitlines(), b.decode().splitlines()
    import difflib
    extra = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, la, lb, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        if tag == 'delete' and all(not x.strip() or x.startswith('> **Status note (2026-10-06') for x in la[i1:i2]):
            extra.append('status note')
            continue
        if tag == 'replace' and i2 - i1 == j2 - j1 and all(
                PLACEHOLDER.search(x) and re.fullmatch('.*?'.join(re.escape(piece) for piece in PLACEHOLDER.split(x)[::2]), y)
                for x, y in zip(la[i1:i2], lb[j1:j2])):
            extra.append('scrubbed lines %d-%d' % (i1 + 1, i2))
            continue
        return False, 'DIFFERS at line %d' % (i1 + 1)
    return True, 'identical except ' + ', '.join(extra)


def is_num_str(s):
    return isinstance(s, str) and re.fullmatch(r'[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?', s.strip()) is not None


def walk(a, b, path, rows, skip):
    """collect leaf comparisons: (path, kind, a, b) with kind 'str', 'numstr', 'num', 'other'"""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k in skip:
                continue
            if k not in a or k not in b:
                rows.append((path + '/' + str(k), 'missing', a.get(k, '<absent>'), b.get(k, '<absent>')))
                continue
            walk(a[k], b[k], path + '/' + str(k), rows, skip)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            rows.append((path, 'length', len(a), len(b)))
            return
        for i, (u, v) in enumerate(zip(a, b)):
            walk(u, v, '%s[%d]' % (path, i), rows, skip)
    elif isinstance(a, bool) or isinstance(b, bool) or a is None or b is None:
        rows.append((path, 'other', a, b))
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        rows.append((path, 'num', a, b))
    elif is_num_str(a) and is_num_str(b):
        rows.append((path, 'numstr', a, b))
    else:
        rows.append((path, 'other', a, b))


POOL_KEYS = ('sigma_pool', 'sigma', 'sigma_pool_stat', 'sigma_rep_stat_projection', 'sigma_jobmax', 'pool', 'rep',
             'max', 'share_of_variance', 'sigma_pool_tot', 'sigma_jobmax_stat', 'sigma_rep_stat', 'pull', 'pull_pool',
             'pull_jobmax', 'sigma_in_C8', 'sigma_diff', 'sigma_contribution', 'rel_sigma', 'share_of_jobmax_variance',
             'sigma_ours_part', 'quoted_estimator')


REP_DIAG = ('rep', 'sigma_rep_stat_projection', 'sigma_rep_stat', 'sigma_jobmax', 'sigma_jobmax_stat', 'max',
            'share_of_variance', 'share_of_jobmax_variance', 'rep2', 'max2', 'pool2')


def compare_tree(shipped, rerun, skip=PATH_KEYS):
    """rules (module docstring): values exact (1e-24 rel), linear/replicate errors 1e-12 rel, everything that
    depends on the sector-pooled errors within 1e-6 of the quoted error of the same entry (or 1e-6 relative); the
    per-job diagnostics (replicate projections, per-job maxima, shares, per-tier sums, which the verbatim code sums in
    double precision over up to 20,160 sectors and which enter no quoted error) within 1e-2; relative differences and
    rounding residuals within 1e-9 absolute"""
    rows = []
    walk(shipped, rerun, '', rows, skip)
    bad, worst_val, worst_pool, n = [], 0.0, 0.0, 0
    for path, kind, a, b in rows:
        n += 1
        last = re.sub(r'\[\d+\]$', '', path.rsplit('/', 1)[-1])
        if kind in ('missing', 'length'):
            bad.append((path, a, b))
            continue
        if kind == 'other':
            if a != b:
                bad.append((path, a, b))
            continue
        x, y = (mp.mpf(a), mp.mpf(b)) if kind == 'numstr' else (mp.mpf(repr(a)), mp.mpf(repr(b)))
        d = abs(x - y)
        if d == 0:
            continue
        pooled = any(last == k or last.startswith(k) for k in POOL_KEYS) or '/top_jobs' in path or \
            '/largest_jobs' in path or '/by_tier' in path or 'pull' in last or 'sigma' in last or 'share' in last
        if last.endswith('_rel') or last.startswith('rel_') or 'residual' in last:
            r = float(d)                            # relative differences and rounding residuals: absolute 1e-9
            worst_pool = max(worst_pool, r * 1e-3)
            if r > 1e-9:
                bad.append((path, a, b))
        elif pooled:
            scale = max(sigma_scale(shipped, path) or 0, abs(x))
            r = float(d / max(scale, mp.mpf(10) ** -300))
            diag = last in REP_DIAG or '/top_jobs' in path or '/largest_jobs' in path or '/by_tier' in path
            worst_pool = max(worst_pool, r if not diag else r * 1e-4)
            if r > (1e-2 if diag else 1e-6):
                bad.append((path, a, b))
        else:
            r = float(d / max(abs(x), mp.mpf(10) ** -300))
            worst_val = max(worst_val, r)
            if r > (1e-24 if kind == 'numstr' else 1e-12):
                bad.append((path, a, b))
    return bad, n, worst_val, worst_pool


def dump_bad(path, bad):
    Path(path).write_text(json.dumps([[p, str(a), str(b)] for p, a, b in bad], indent=0))


def sigma_scale(tree, path):
    """the quoted sigma of the entry that contains path (for pull-like leaves: 1, i.e. absolute 1e-6 in the pull)"""
    last = path.rsplit('/', 1)[-1]
    if 'pull' in last:
        return mp.mpf(1)
    parts = [p for p in path.split('/') if p]
    node = tree
    best = None
    for p in parts:
        m = re.fullmatch(r'(.*)\[(\d+)\]', p)
        try:
            if m:
                node = node[m.group(1)] if m.group(1) else node
                node = node[int(m.group(2))]
            else:
                node = node[p]
        except (KeyError, IndexError, TypeError):
            break
        if isinstance(node, dict) and isinstance(node.get('sigma'), (int, float)) and node.get('sigma'):
            best = mp.mpf(repr(node['sigma']))
    return best


# ----------------------------------------------------------------------------------------------------------------------
_TERM = re.compile(r'([+-]?)\s*(?:\\frac\{(\d+)\}\{(\d+)\}|(\d+))?\s*((?:\\zeta\(\d+\)(?:\^\{?\d+\}?)?)*)')


def tex_zeta_value(tex, dps=50):
    """value of a rational combination of zeta products written in TeX (eq:sr-closed, eq:sr-C8 style)"""
    with mp.workdps(dps + 10):
        t = tex.replace('{}', '').replace('&', '').replace('\\quad', '').replace('\\\\', '').replace(' ', '').replace('\n', '')
        tot = mp.mpf(0)
        pos = 0
        while pos < len(t):
            m = _TERM.match(t, pos)
            if not m or m.end() == pos:
                raise ValueError('cannot parse %r' % t[pos:pos + 30])
            sg, fn, fd, integer, zs = m.groups()
            c = mp.mpf(fn) / mp.mpf(fd) if fn else (mp.mpf(integer) if integer else mp.mpf(1))
            for zn, zp in re.findall(r'\\zeta\((\d+)\)(?:\^\{?(\d+)\}?)?', zs):
                c *= mp.zeta(int(zn)) ** (int(zp) if zp else 1)
            tot += -c if sg == '-' else c
            pos = m.end()
        return +tot


def claims_from_paper(Q):
    eqs = {e['label']: e['tex'] for e in Q['equations']}
    out = {}
    body = eqs['eq:sr-closed'].replace('\\begin{aligned}', '').replace('\\end{aligned}', '')
    # split on the C^{SR}_n= markers
    parts = re.split(r'C\^\{\\rm SR\}_(\d)(?:\(\d\))?\s*&?\s*=', body)
    for i in range(1, len(parts), 2):
        n = int(parts[i])
        expr = parts[i + 1].strip().rstrip('.').rstrip(',').replace(',\\qquad', '')
        expr = re.sub(r',\s*\\\\\s*$', '', expr.strip()).rstrip(',').rstrip('.')
        out[n] = tex_zeta_value(expr)
    c8 = eqs['eq:sr-C8'].replace('\\begin{aligned}', '').replace('\\end{aligned}', '')
    c8 = re.split(r'C\^\{\\rm SR\}_8(?:\(\d\))?\s*=\s*', c8)[1].strip().rstrip('.')
    out[8] = tex_zeta_value(c8)
    return out


# ----------------------------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=str(PKG/'.work'))
    ap.add_argument('--raw', default=None, help='directory holding engine/runs/<run>/*.cfg.json (fetch-data)')
    ap.add_argument('--steps', default='reports,p2,c8,cmp2,cmp8')
    a = ap.parse_args()
    steps = a.steps.split(',')
    work = Path(a.work).resolve()/('replay_raw' if a.raw else 'replay')
    work.mkdir(parents=True, exist_ok=True)
    record = None if a.raw else RECORD
    T = SL.Table('indep_d1 replay' + (' (raw chunk outputs)' if a.raw else ' (pooled sector record)'))
    Qm, Q = SL.quoted(PKG.parent.parent/'results'/'quoted_numbers.json')
    mp.mp.dps = 50

    # ---------------------------------------------------------------- 0. raw mode: rebuild the pooled record
    if a.raw:
        bad, n = [], 0
        for line in (HERE/'RAW_SHA256SUMS.txt').read_text().splitlines():
            if not line.strip() or line.startswith('#'):
                continue
            h, rel = line.split()[:2]
            n += 1
            p = Path(a.raw)/rel
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != h:
                bad.append(rel)
        T.check('raw chunk outputs', not bad, '%d files%s' % (n, '; missing or different: %s' % bad[:3] if bad else ''),
                'all sha256 equal', 'public/RAW_SHA256SUMS.txt (the files fetch-data provides)')
        run = work_copy(work/'record', a.raw)
        out = work/'record'/'pooled_sector_record.json'
        t0 = time.time()
        r = subprocess.run([sys.executable, '-B', str(HERE/'make_pooled_record.py'), '--tree', str(run), '--out', str(out),
                            '--check', str(RECORD)], capture_output=True, text=True)
        (work/'record'/'make_pooled_record.log').write_text(r.stdout + r.stderr)
        lines = [l.strip() for l in r.stdout.splitlines() if 'largest' in l]
        T.check('pooled sector record rebuilt', r.returncode == 0, '; '.join(lines)[:200] + ' (%.0f s)' % (time.time() - t0),
                'RECORD CHECK PASSED', 'public/make_pooled_record.py on the raw chunk outputs (verbatim job_sector_values) '
                'vs the shipped record (1e-20), and the shim vs the verbatim pooled_projection (unit gradients 1e-12)')

    # ---------------------------------------------------------------- 1. reports from the shipped json
    if 'reports' in steps:
        run = work_copy(work/'reports')
        for script, md in (('make_report.py', 'RESULTS.md'), ('make_report_C8.py', 'RESULTS_C8.md'),
                           ('make_report_C8_tierA.py', 'RESULTS_C8_tierA.md')):
            r = subprocess.run([sys.executable, '-B', script], cwd=run/'assembly', capture_output=True, text=True)
            ok, how = same_report(PKG/md, run/md) if r.returncode == 0 else (False, 'exit %d' % r.returncode)
            T.check(md + ' regenerated', ok, how, 'byte-identical' + (' except the status note' if md == 'RESULTS_C8_tierA.md'
                                                                      else ''),
                    'verbatim assembly/%s on the shipped RESULTS json files%s' % (script, '; the shipped report carries '
                    'a hand-added status note of 2026-10-06 (two lines after the title) that the script does not write'
                    if md == 'RESULTS_C8_tierA.md' else ''))

    # ---------------------------------------------------------------- 2. phase 2: run_assembly.py main()
    p2 = None
    if 'p2' in steps:
        run = work_copy(work/'p2', a.raw)
        (run/'RESULTS_independent.json').unlink()
        rc, dt, tail = step('p2', run, record, log=work/'p2'/'run_step.log')
        ok = rc == 0 and (run/'RESULTS_independent.json').exists()
        T.check('run_assembly.py main()', ok, 'exit %d, %.0f s' % (rc, dt), 'exit 0',
                'verbatim phase-2 assembly (steps 1-2) in a work copy' + ('' if ok else '; ' + tail[-300:]))
        if ok:
            p2 = json.loads((run/'RESULTS_independent.json').read_text())
            ship = json.loads((PKG/'RESULTS_independent.json').read_text())
            bad, n, wv, wp = compare_tree(ship, p2)
            dump_bad(work/'p2'/'diff_RESULTS_independent.json', bad)
            T.check('RESULTS_independent.json', not bad, '%d leaves; %d outside tolerance%s; worst value %.1e, worst pooled '
                    '%.1e' % (n, len(bad), (' e.g. %s' % (bad[:2],)) if bad else '', wv, wp),
                    'values 1e-24, linear/replicate 1e-12, pooled 1e-6 of sigma',
                    'regenerated vs shipped (all of steps 1-2; paths and dates skipped)')

    # ---------------------------------------------------------------- 3. C8: run_assembly_C8.step1()
    c8 = None
    if 'c8' in steps:
        run = work_copy(work/'c8', a.raw)
        out = work/'c8'/'c8_step1.json'
        rc, dt, tail = step('c8', run, record, out=out, log=work/'c8'/'run_step.log')
        ok = rc == 0 and out.exists()
        T.check('run_assembly_C8.py step1()', ok, 'exit %d, %.0f s' % (rc, dt), 'exit 0',
                'verbatim C8 assembly (strict, per replicate; engine SHA-256 records verified; the old results '
                'unchanged; the note\'s raw structure) + W_three_ways + separate tier files' + ('' if ok else '; ' + tail[-300:]))
        if ok:
            c8 = json.loads(out.read_text())
            ship = json.loads((PKG/'RESULTS_C8_independent.json').read_text())['step1']
            sub = {k: ship[k] for k in c8}
            bad, n, wv, wp = compare_tree(sub, c8, skip=PATH_KEYS | {'assembly_seconds'})
            dump_bad(work/'c8'/'diff_RESULTS_C8_independent_step1.json', bad)
            T.check('RESULTS_C8_independent.json step1', not bad, '%d leaves; %d outside tolerance%s; worst value %.1e, '
                    'worst pooled %.1e' % (n, len(bad), (' e.g. %s' % (bad[:2],)) if bad else '', wv, wp),
                    'values 1e-24, linear/replicate 1e-12, pooled 1e-6 of sigma',
                    'recomputed vs shipped: meta, outputs, sub_pieces, terms, error budgets, raw structure, W, tier files')

    # ---------------------------------------------------------------- 4. comparisons with the archive values
    cmp2 = cmp8 = None
    for mode, fn in (('cmp2', 'RESULTS_archive_comparison.json'), ('cmp8', 'RESULTS_C8_archive_comparison.json')):
        if mode not in steps:
            continue
        run = work_copy(work/mode, a.raw)
        rc, dt, tail = step(mode, run, record, log=work/mode/'run_step.log')
        ok = rc == 0
        new = json.loads((run/fn).read_text()) if ok else None
        ship = json.loads((PKG/fn).read_text())
        if ok and new.get('date') == ship.get('date'):
            ok = False
            tail = 'output not rewritten'
        T.check('compare_archive%s.py main()' % ('_C8' if mode == 'cmp8' else ''), ok, 'exit %d, %.0f s' % (rc, dt),
                'exit 0', 'verbatim comparison with the sealed archive values (spec/comparison%s, SHA256SUMS checked by '
                'the C8 script)' % ('_C8' if mode == 'cmp8' else '') + ('' if ok else '; ' + tail[-300:]))
        if ok:
            bad, n, wv, wp = compare_tree(ship, new)
            dump_bad(work/mode/('diff_' + fn), bad)
            T.check(fn, not bad, '%d leaves; %d outside tolerance%s; worst value %.1e, worst pooled %.1e' % (
                n, len(bad), (' e.g. %s' % (bad[:2],)) if bad else '', wv, wp),
                'values 1e-24, linear/replicate 1e-12, pooled 1e-6 of sigma', 'regenerated vs shipped (dates, paths skipped)')
            if mode == 'cmp2':
                cmp2 = new
            else:
                cmp8 = new

    # ---------------------------------------------------------------- 5. quoted numbers and cited checks
    if p2 and c8:
        quoted_rows(T, Qm, Q, p2, c8, cmp2, cmp8)
    else:
        T.add('quoted numbers', 'SKIP', 'steps p2 and c8 needed', '', 'run all steps')
    return T.report(work/'replay_indep.txt')


def quoted_rows(T, Qm, Q, p2, c8, cmp2, cmp8):
    """the macros of package indep_d1 and the cited checks, from the recomputed values"""
    claims = claims_from_paper(Q)
    o2 = p2['step1']['outputs']
    # the paper's equations vs the framework's claimed closed forms (L.closed_forms, used by compare_archive.py)
    if cmp2:
        cf = {c['name']: mp.mpf(c['closed_form_value']) for c in cmp2['claims_vs_closed_forms'] if c['name'] in ('C5', 'C6', 'C7')}
        d = max(abs(claims[n] - cf['C%d' % n]) for n in (5, 6, 7))
        T.check('eq:sr-closed = claims used', d < mp.mpf(10) ** -25, '%.1e' % float(d), '< 1e-25',
                'C5, C6, C7 of the paper\'s eq:sr-closed (quoted_numbers.json, mpmath) vs the closed forms of the '
                'framework (lri_framework.closed_forms) that compare_archive.py tests')
    if cmp8:
        d = abs(claims[8] - mp.mpf(cmp8['C8']['claim_C8_archive']))
        T.check('eq:sr-C8 = archive record', d < mp.mpf(10) ** -25, '%.1e' % float(d), '< 1e-25',
                'the paper\'s eq:sr-C8 (mpmath) vs the archive\'s 100-digit C8 record (spec/comparison_C8, sealed)')
    # C5..C7 (and D4): recomputed values and pulls against the paper's closed forms
    pulls = {}
    exp = {'C5': ('29.237811563', '1.35e-07', '-0.13'), 'C6': ('-58.66569861', '1.45e-06', '-0.78'),
           'C7': ('51.0689860', '3.14e-05', '-0.08')}
    for n in (5, 6, 7):
        e = o2['C%d' % n]
        v, s = mp.mpf(e['value']), mp.mpf(repr(e['sigma']))
        p = float((v - claims[n]) / s)
        pulls[n] = p
        ev, es, ep = exp['C%d' % n]
        got = (e['value'][:len(ev)], '%.2e' % float(s), '%+.2f' % p)
        ok = got[0] == ev and got[1] == es and got[2] == ('%+.2f' % float(ep))
        T.check('C%d independent' % n, ok, '%s +- %s, pull %s' % got, '%s +- %s, pull %s' % (ev, es, ep),
                'recomputed (run_assembly.py) value +- quoted sigma (max of the three estimators), pull against the '
                'paper\'s eq:sr-closed; as printed in RESULTS.md (value cut, not rounded, to the printed digits, as '
                'make_report.py does)')
    if cmp2:
        d4 = next(c for c in cmp2['claims_vs_closed_forms'] if c['name'] == 'D4')
        e = o2['D4']
        p = float((mp.mpf(e['value']) - mp.mpf(d4['closed_form_value'])) / mp.mpf(repr(e['sigma'])))
        got = '%s +- %.2e, pull %+.2f' % (e['value'][:len('-2.53463048')], e['sigma'], p)
        T.check('D4 independent', got == '-2.53463048 +- 7.85e-06, pull -0.09', got, '-2.53463048 +- 7.85e-06, pull -0.09',
                'recomputed D4 against the claimed closed form (framework); as printed in RESULTS.md')
    pmax = max(abs(p) for p in pulls.values())
    # the 25 inputs against the archive's 100-digit values
    if cmp2:
        rows = [r for r in cmp2['inputs_and_invariants_vs_archive']['rows'] if r['name'] in
                ['a', 'p', 'A', 'E', 'c', 'f', 'b', 'G', 'q', 'k', 'V', 'R', 'J', 'L', 'M', 'N', 'alpha', 'beta', 'gamma',
                 'Phi', 'Psi', 'Omega', 'Q', 'P', 'K']]
        ip = []
        for r in rows:
            e = o2[r['name']]
            ip.append((float((mp.mpf(e['value']) - mp.mpf(r['archive'])) / mp.mpf(repr(e['sigma']))), r['name']))
        rms = math.sqrt(sum(x * x for x, _ in ip) / len(ip))
        mx = max(ip, key=lambda t: abs(t[0]))
        T.check('25 inputs: rms pull', len(ip) == 25 and '%.2f' % rms == '0.34' and abs(mx[0]) < 1,
                'n %d, rms %.2f, max |pull| %.2f (%s)' % (len(ip), rms, abs(mx[0]), mx[1]), 'n 25, rms 0.34, none above 1',
                'recomputed inputs vs the archive 100-digit values (spec/comparison, sealed); RESULTS.md')
        # \SRindepPullMax (numbers.tex, 2026-10-15; note only): the max |pull| over the 25 inputs of C5..C7; the
        # coefficients' own max is an INFO row
        T.quoted(Qm['\\SRindepPullMax'], [abs(mx[0])], 'max |pull| of the 25 recomputed inputs of C5..C7 against the '
                 "archive's 100-digit values (%s); quoted sigma = max of the three estimators" % mx[1])
        T.add('max |pull| of C5, C6, C7', 'INFO', '%.2f (C6: %.2f)' % (pmax, pulls[6]), 'below the inputs\' maximum',
              'the coefficients themselves against eq:sr-closed (the macro is defined over the inputs)')
    else:
        T.add('\\SRindepPullMax', 'FAIL', '(archive comparison record missing)', Qm['\\SRindepPullMax']['text'],
              'needs RESULTS_archive_comparison.json')
    # C8
    o8, s8 = c8['outputs'], c8['sub_pieces']
    C8v, C8s = mp.mpf(o8['C8']['value']), o8['C8']['sigma']
    T.check('C8 quoted estimator', o8['C8']['quoted_estimator'] == 'sigma_pool', '%s: cov %.3g, rep %.3g, pool %.3g' % (
        o8['C8']['quoted_estimator'], o8['C8']['sigma_cov'], o8['C8']['sigma_rep'], o8['C8']['sigma_pool']),
        'sigma_pool (the largest)', 'quoted error = max of the three estimators (protocol)')
    T.quoted(Qm['\\SRCeightIndep'], [float(C8v), C8s], 'recomputed C8 = 8 T4 (run_assembly_C8.step1) +- the quoted sigma')
    pull8 = float((C8v - claims[8]) / C8s)
    T.quoted(Qm['\\SRCeightPull'], [pull8], '|C8 - eq:sr-C8| / sigma (sector-pooled); %.3f' % pull8, absolute=True)
    T.check('C8 pull sign', pull8 < 0, '%+.2f' % pull8, 'below the claim', 'the paper says "below the claimed value"')
    # \SRCeightPullMax (numbers.tex, 2026-10-16): the largest |pull| over the three error estimators; the paper reads
    # "1.9 to 4.0 standard errors below the claimed value depending on the error estimator"
    pulls8 = {k: float((C8v - claims[8]) / mp.mpf(repr(o8['C8'][k]))) for k in ('sigma_cov', 'sigma_rep', 'sigma_pool')}
    if '\\SRCeightPullMax' in Qm:
        T.quoted(Qm['\\SRCeightPullMax'], [max(abs(x) for x in pulls8.values())],
                 'largest |pull| over the three estimators (replicate spread %.2f, linear %.2f, sector-pooled %.2f)' % (
                     abs(pulls8['sigma_rep']), abs(pulls8['sigma_cov']), abs(pulls8['sigma_pool'])), absolute=True)
    # where the C8 difference sits (cmp8 for the archive values of the pieces)
    if cmp8:
        arch = {}
        for k, r in cmp8['inputs']['rows'].items():
            arch[k] = mp.mpf(r['archive'])
        for k, r in cmp8['sub_pieces'].items():
            if r.get('archive') is not None:
                arch[k] = mp.mpf(r['archive'])

        def pull(nm, src):
            e = src[nm]
            return float((mp.mpf(e['value']) - arch[nm]) / mp.mpf(repr(e['sigma']))), float(mp.mpf(e['value']) - arch[nm]), e['sigma']
        pj, dj, sj = pull('J9', o8)
        got = '%s +- %.1f vs %s, pull %+.2f' % (mp.nstr(mp.mpf(o8['J9']['value']), 4), sj, mp.nstr(arch['J9'], 5), pj)
        T.check('J9 = b9', got == '-291.9 +- 9.5 vs -273.72, pull -1.92', got, '-291.9 +- 9.5 vs -273.72, pull -1.92',
                'recomputed J9 vs the archive record; RESULTS_C8.md')
        pa, da, sa = pull('A9_1', s8)
        got = 'ours - archive %+.1f +- %.1f (%+.2f sigma, %.1e relative)' % (da, sa, pa, abs(da / float(arch['A9_1'])))
        T.check('A9[eps^0 l^1] tension', got == 'ours - archive -20.4 +- 9.3 (-2.19 sigma, 3.3e-05 relative)', got,
                'ours - archive -20.4 +- 9.3 (-2.19 sigma, 3.3e-05 relative)', 'recomputed sub-piece A9_1 vs the archive record')
        others = {nm: pull(nm, s8)[0] for nm in ('Z8_1', 'EA7_0', 'EZ6_0', 'D9_lower')}
        bc = {nm: pull(nm, o8)[0] for nm in ('U', 'Kv')}
        w = c8['outputs']
        cw = mp.mpf(next(v for k, v in c8['sub_pieces'].items() if k == 'C8_without_J9')['value'])
        a_cw = mp.mpf(cmp8['C8']['C8_without_J9']['archive_C8_minus_J9_over_4'])
        p_cw = float((cw - a_cw) / mp.mpf(repr(c8['sub_pieces']['C8_without_J9']['sigma'])))
        ok = abs(pa) > 2 and all(abs(x) < 1 for x in others.values()) and all(abs(x) < 1 for x in bc.values()) and abs(p_cw) < 1
        T.check('C8 difference in one integral', ok, 'A9_1 %+.2f; other J9 pieces %s; U %+.2f, Kv %+.2f; C8 - J9/4 %+.2f' % (
            pa, ', '.join('%s %+.2f' % kv for kv in others.items()), bc['U'], bc['Kv'], p_cw),
            '|A9_1| > 2, all others < 1', 'rule for "traces to a single input integral": C8 - J9/4 (everything but J9) '
            'agrees, and within J9 = A9_1 - Z8_1 + 2(EA7)_0 - 2(EZ6)_0 + D9_lower only A9[eps^0 l^1] deviates')
        del w
    T.add('chunk-pooled C8 pull', 'INFO', '-2.09 (statistics verifier, not recomputed)', '1.9 (note only)',
          'the post-assembly statistics verifier\'s chunk-pooled sigma(A9_1) = 8.50 gives -2.09; RESULTS_C8.md; the paper '
          'quotes the protocol estimator (sector-pooled, -1.92)')


if __name__ == '__main__':
    sys.exit(main())
