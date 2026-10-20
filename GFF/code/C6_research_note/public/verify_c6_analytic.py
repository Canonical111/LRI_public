#!/usr/bin/env python3
"""Public test/replay checks for GFF/code/C6_research_note (analytic representation of C6(1)).

Subcommands (run from the package folder, normally through public.mk):
  test           integrity of the shipped package (checksum lists, provenance hashes, run records,
                 note build record, protected equations) and three exact stage tasks in a scratch copy.
  replay         rerun code/make_outputs.py in a scratch copy from the shipped run records, compare the
                 regenerated records with the shipped ones, recompute every number the condensed note quotes
                 for this package (value, sector table, interval certificate, graph-sum comparison, source
                 repair, PSLQ search) and write a PASS/FAIL table.
  prepare-rerun  make a scratch copy for a fresh run of the 22 final-method tasks (rerun-final target).
  compare-rerun  compare the fresh task outputs and the reassembly made from them with the shipped records.

Nothing in the package tree is modified: every run happens in a copy under the work directory.
Exit status is 1 if any row is FAIL.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from decimal import Decimal, getcontext, ROUND_HALF_EVEN, ROUND_DOWN
from fractions import Fraction
from pathlib import Path

getcontext().prec = 250
sys.dont_write_bytecode = True   # never write __pycache__ into the shipped tree
if hasattr(sys, 'set_int_max_str_digits'):
    sys.set_int_max_str_digits(0)

PKG = Path(__file__).resolve().parents[1]
PUBLIC = PKG / 'public'
OVERLAY = {'public.mk', 'REVIEWS.md'}  # top-level files added by the public overlay
TIMING_KEYS = {'seconds', 'elapsed_seconds'}
GRAPH_SUM_SHA256 = '3ff496c2fd6a00507011ba228ae08bc990999ee7a09efc52c7788bedca2ee717'


# ----------------------------------------------------------------------------------------------- table
class Table:
    def __init__(self, title):
        self.title, self.rows = title, []

    def add(self, cid, status, what, detail='', tol=''):
        self.rows.append(dict(id=cid, status=status, check=what, detail=str(detail), tolerance=tol))
        print(f'{status:4s}  {cid:28s} {what}' + (f'  [{detail}]' if detail else ''), flush=True)

    def ok(self, cid, cond, what, detail='', tol=''):
        self.add(cid, 'PASS' if cond else 'FAIL', what, detail, tol)
        return cond

    def write(self, work, name):
        work.mkdir(parents=True, exist_ok=True)
        n = {s: sum(r['status'] == s for r in self.rows) for s in ('PASS', 'FAIL', 'SKIP', 'INFO')}
        lines = [f'# {self.title}', f'# package: {PKG}', f'# {time.strftime("%Y-%m-%d %H:%M:%S")}  python {sys.version.split()[0]}',
                 f'# PASS {n["PASS"]}  FAIL {n["FAIL"]}  SKIP {n["SKIP"]}  INFO {n["INFO"]}', '',
                 f'{"status":6s} {"id":28s} {"check":70s} detail | tolerance']
        for r in self.rows:
            lines.append(f'{r["status"]:6s} {r["id"]:28s} {r["check"]:70s} {r["detail"]} | {r["tolerance"]}')
        (work / f'{name}.txt').write_text('\n'.join(lines) + '\n')
        (work / f'{name}.json').write_text(json.dumps(dict(title=self.title, counts=n, rows=self.rows), indent=1) + '\n')
        print(f'\n{self.title}: PASS {n["PASS"]}  FAIL {n["FAIL"]}  SKIP {n["SKIP"]}  INFO {n["INFO"]}'
              f'   (table: {work / (name + ".txt")})')
        return 1 if n['FAIL'] else 0


# --------------------------------------------------------------------------------------------- helpers
def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_json(p: Path):
    return json.loads(p.read_text())


def dropped_prefixes():
    pre, expect = [], {}
    for line in (PUBLIC / 'dropped_paths.txt').read_text().splitlines():
        m = re.match(r'#\s*(expected_\w+):\s*(\d+)', line)
        if m:
            expect[m.group(1)] = int(m.group(2))
        elif line.strip() and not line.startswith('#'):
            pre.append(line.strip())
    return pre, expect


def is_dropped(rel, pre):
    return any(rel.startswith(p) for p in pre)


def selected_tasks():
    """The 22 tasks of code/reproduce_final.py, read from the shipped scripts (not hard-coded)."""
    def lists(path):
        tree = ast.parse(path.read_text())
        out = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                try:
                    out[node.targets[0].id] = ast.literal_eval(node.value)
                except ValueError:
                    pass
        return out
    r = lists(PKG / 'code/reproduce.py')
    f = lists(PKG / 'code/reproduce_final.py')
    core = [t[0] for t in r['CORE']]
    numerical = [t[0] for t in r['NUMERICAL']]
    exact = list(f['EXACT'])
    stage = {t[0]: t[1] for t in r['CORE'] + r['EXACT'] + r['NUMERICAL']}
    return core, exact, numerical, stage


def copy_package(dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(PKG, dst, ignore=shutil.ignore_patterns('.work', 'public', 'public.mk', 'REVIEWS.md', '__pycache__', '*.pyc', '.DS_Store'))
    return dst


def run(cmd, cwd, log: Path, timeout=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', MPLBACKEND='Agg')
    t0 = time.monotonic()
    p = subprocess.run(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(p.stdout)
    return p.returncode, time.monotonic() - t0, p.stdout


NUM = re.compile(r'^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?\s*$')


def as_dec(s):
    return Decimal(s.strip()) if isinstance(s, str) and NUM.match(s) else None


def json_diff(a, b, rel_tol, path=''):
    """Return (n_leaves, n_bitwise_equal, worst_rel_diff, list_of_mismatches) ignoring timing keys."""
    if isinstance(a, dict) and isinstance(b, dict):
        ka, kb = set(a) - TIMING_KEYS, set(b) - TIMING_KEYS
        if ka != kb:
            return 1, 0, None, [f'{path}: keys differ {sorted(ka ^ kb)[:5]}']
        tot = [0, 0, Decimal(0), []]
        for k in sorted(ka):
            n, e, w, m = json_diff(a[k], b[k], rel_tol, f'{path}/{k}')
            tot[0] += n; tot[1] += e; tot[3] += m
            if w is not None and w > tot[2]:
                tot[2] = w
        return tot[0], tot[1], tot[2], tot[3]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return 1, 0, None, [f'{path}: list lengths {len(a)} != {len(b)}']
        tot = [0, 0, Decimal(0), []]
        for i, (x, y) in enumerate(zip(a, b)):
            n, e, w, m = json_diff(x, y, rel_tol, f'{path}[{i}]')
            tot[0] += n; tot[1] += e; tot[3] += m
            if w is not None and w > tot[2]:
                tot[2] = w
        return tot[0], tot[1], tot[2], tot[3]
    if a == b:
        return 1, 1, Decimal(0), []
    da, db = as_dec(a) if isinstance(a, str) else None, as_dec(b) if isinstance(b, str) else None
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        da, db = Decimal(repr(a)), Decimal(repr(b))
    if da is not None and db is not None:
        scale = max(abs(da), abs(db))
        r = abs(da - db) / scale if scale else Decimal(0)
        return 1, 0, r, ([] if r <= rel_tol else [f'{path}: rel diff {r:.3e}'])
    return 1, 0, None, [f'{path}: {str(a)[:60]!r} != {str(b)[:60]!r}']


def rnd(x: Decimal, places: int) -> str:
    return str(x.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN))


def trunc(x: Fraction, places: int) -> str:
    sign = '-' if x < 0 else ''
    x = abs(x)
    n = (x.numerator * 10 ** places) // x.denominator
    a, b = divmod(n, 10 ** places)
    return f'{sign}{a}.{b:0{places}d}'


def interval(rec):
    den = 1 << rec['denominator_power_of_two']
    return Fraction(int(rec['lower_numerator']), den), Fraction(int(rec['upper_numerator']), den)


def frac_of(s: str) -> Fraction:
    return Fraction(Decimal(s))


# ------------------------------------------------------------------------------------------- integrity
def integrity(t: Table):
    pre, expect = dropped_prefixes()
    # 1. top-level MANIFEST.sha256
    lines = [l.split('  ', 1) for l in (PKG / 'MANIFEST.sha256').read_text().splitlines() if l.strip()]
    listed = {rel for _, rel in lines}
    bad, absent_dropped, absent_other, ok = [], 0, [], 0
    for h, rel in lines:
        p = PKG / rel
        if p.is_file():
            if sha(p) == h:
                ok += 1
            else:
                bad.append(rel)
        elif is_dropped(rel, pre):
            absent_dropped += 1
        else:
            absent_other.append(rel)
    t.ok('manifest.hashes', not bad, 'MANIFEST.sha256: every shipped listed file is byte-identical',
         f'{ok} of {len(lines)} lines verified; mismatches {bad[:5]}', 'bitwise (sha256)')
    t.ok('manifest.absent', not absent_other and absent_dropped == expect.get('expected_absent_manifest_lines'),
         'MANIFEST.sha256: absent files are exactly the documented dropped paths',
         f'{absent_dropped} absent under public/dropped_paths.txt (expected {expect.get("expected_absent_manifest_lines")}); '
         f'other absent {absent_other[:5]}', 'exact count')
    # unlisted files
    unlisted = []
    for p in sorted(PKG.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(PKG).as_posix()
        if rel.split('/')[0] in ('.work', 'public') or rel in OVERLAY or '__pycache__' in rel or p.name in ('.DS_Store', '.gitignore'):
            continue
        if rel not in listed and p.name != 'MANIFEST.sha256':
            unlisted.append(rel)
    t.ok('manifest.unlisted', not unlisted, 'no shipped file outside MANIFEST.sha256 except checksum lists and the public overlay',
         f'unlisted {unlisted[:5]}', 'exact')
    # 2. provenance/source_manifest.json (origin hashes of the stage files and snapshots)
    src = read_json(PKG / 'provenance/source_manifest.json')
    patches = {p['path']: p for p in read_json(PKG / 'provenance/portability_patches.json')}
    bad, patched, absent_dropped, absent_other, ok = [], [], 0, [], 0
    for rec in src:
        rel = rec['packaged_path']; p = PKG / rel
        if not p.is_file():
            (absent_other.append(rel) if not is_dropped(rel, pre) else None)
            absent_dropped += is_dropped(rel, pre)
            continue
        if sha(p) == rec['sha256']:
            ok += 1
        elif rel in patches and hashlib.sha256(p.read_text().replace(patches[rel]['new'], patches[rel]['old']).encode()).hexdigest() == rec['sha256']:
            patched.append(rel)
        else:
            bad.append(rel)
    t.ok('source_manifest.hashes', not bad, 'provenance/source_manifest.json: shipped files equal their original sources',
         f'{ok} identical, {len(patched)} differ only by the documented portability patch {patched}; mismatches {bad[:5]}',
         'bitwise (sha256)')
    t.ok('source_manifest.absent', not absent_other and absent_dropped == expect.get('expected_absent_source_manifest_records'),
         'provenance/source_manifest.json: absent records are exactly the dropped stages',
         f'{absent_dropped} absent (expected {expect.get("expected_absent_source_manifest_records")}); other {absent_other[:5]}', 'exact count')
    # 3. stage-local checksum lists of the shipped stages
    bad, logs_missing, n = [], [], 0
    for m in sorted((PKG / 'code/stages').rglob('MANIFEST.sha256')):
        for line in m.read_text().splitlines():
            if not line.strip():
                continue
            h, rel = line.split('  ', 1)
            p = m.parent / rel; full = p.relative_to(PKG).as_posix()
            if not p.is_file():
                (logs_missing.append(full) if rel.endswith('.log') else bad.append(full + ' (missing)'))
                continue
            n += 1
            if sha(p) != h:
                pt = patches.get(full)
                if not (pt and hashlib.sha256(p.read_text().replace(pt['new'], pt['old']).encode()).hexdigest() == h):
                    bad.append(full)
    t.ok('stage_manifests', not bad, 'stage-local MANIFEST.sha256 lists of the shipped stages',
         f'{n} files verified; {len(logs_missing)} listed .log files were already absent in the delivered package; '
         f'mismatches {bad[:5]}', 'bitwise; build.py via documented patch')
    # 4. run records of the 22 final-method tasks
    core, exact, numerical, stage = selected_tasks()
    sel = core + exact + numerical
    rr = PKG / 'outputs/rerun'
    recs = {p.parent.name: read_json(p) for p in rr.glob('*/execution.json')}
    missing = [x for x in sel if x not in recs]
    failed = [x for x in sel if x in recs and recs[x].get('status') != 'passed']
    extra = sorted(set(recs) - set(sel))
    gen_missing = [g for x in sel if x in recs for g in recs[x].get('generated_files', []) if not (PKG / g).is_file()]
    t.ok('run_records', len(sel) == 22 and not missing and not failed and not extra and not gen_missing,
         'outputs/rerun: the 22 final-method task records (code/reproduce_final.py) passed, outputs present',
         f'{len(sel)} selected; missing {missing}; not passed {failed}; extra {extra}; missing outputs {gen_missing[:3]}', 'exact')
    sums = {p: read_json(rr / f'summary_{p}.json') for p in ('core', 'exact', 'numerical')}
    want = {'core': core, 'exact': exact, 'numerical': numerical}
    good = all(sums[p]['all_passed'] and [x['id'] for x in sums[p]['tasks']] == want[p] for p in sums)
    fm = read_json(PKG / 'outputs/final_method_run.json')
    t.ok('run_summaries', good and fm['all_profiles_passed'] and fm['expected_tasks'] == 22,
         'summary_{core,exact,numerical}.json and final_method_run.json agree with the selection',
         f'resume_requested={fm["resume_requested"]} (21 of 22 records are fresh executions; see README)', 'exact')
    # 5. note build record and protected equations
    br = read_json(PKG / 'outputs/build_report.json')
    if not (PKG / 'note/C6_progress_note.tex').is_file():
        # The package's note is merged into the condensed note (GFF/note, appendix on the derivation of the C6(1)
        # representation) and is not shipped (public/dropped_paths.txt). Its build record and the hashes of its
        # protected equations (provenance/editorial_revision.json) ship unchanged but describe the delivered note.
        t.add('note.merged', 'INFO', 'note/C6_progress_note.{tex,pdf} not shipped: merged into the condensed note',
              f'delivered note sha256 {br["source_sha256"][:16]}..., pdf {br["pdf_sha256"][:16]}...', '')
    else:
        t.ok('note.build_record', sha(PKG / 'note/C6_progress_note.tex') == br['source_sha256'] and
             sha(PKG / 'note/C6_progress_note.pdf') == br['pdf_sha256'] and not br['warnings'],
             'note/C6_progress_note.{tex,pdf} match outputs/build_report.json (no LaTeX warnings)', br['engine'], 'bitwise (sha256)')
        spec = importlib.util.spec_from_file_location('audit_final_note', PKG / 'code/audit_final_note.py')
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        tex = (PKG / 'note/C6_progress_note.tex').read_text()
        prot = read_json(PKG / 'provenance/editorial_revision.json')['protected_equations']
        badeq = [k for k, h in prot.items() if hashlib.sha256(mod.equation(tex, k).encode()).hexdigest() != h]
        t.ok('note.protected_equations', not badeq, 'protected equations of the note (eq:preferred, eq:E, ...) unchanged',
             f'{len(prot) - len(badeq)} of {len(prot)}; changed {badeq}', 'bitwise (sha256 of whitespace-stripped display)')


def exact_smoke(t: Table, work: Path, tasks=('wheel_exact', 'cubic_exact', 'single_wheel_exact')):
    cp = copy_package(work / 'test' / 'pkg')
    for task in tasks:
        rc, dt, out = run([sys.executable, 'code/reproduce.py', '--profile', 'exact', '--only', task, '--timeout', '600'],
                          cp, work / 'test' / f'{task}.log')
        rec = cp / 'outputs/rerun' / task
        st = read_json(rec / 'execution.json').get('status') if (rec / 'execution.json').is_file() else 'no record'
        same = (rec / 'stdout.txt').is_file() and (rec / 'stdout.txt').read_text() == (PKG / 'outputs/rerun' / task / 'stdout.txt').read_text()
        t.ok(f'smoke.{task}', rc == 0 and st == 'passed', f'exact task {task} reruns in a scratch copy and passes',
             f'{dt:.1f} s; stdout identical to shipped record: {same}', 'exit status')


# ---------------------------------------------------------------------------------------------- replay
def compare_reassembly(t, new, old, tag):
    rel_tol = Decimal('1e-85')
    same_struct = new['exact_checks'] == old['exact_checks'] and all(new['exact_checks'].values()) \
        and new['known_polynomial_real'] == old['known_polynomial_real'] and new['source_files'] == old['source_files']
    t.ok(f'{tag}.exact', same_struct, 'reassembly: exact polynomial checks and the 18-monomial real polynomial reproduce',
         'recommended_known_polynomial_has_18_monomials, G pi^3 and pi^5 coefficients', 'exact (sympy)')
    worst, n, bad = Decimal(0), 0, []
    for grp in ('blocks_r6', 'fixed_values'):
        for k, v in old[grp].items():
            a, b = Decimal(new[grp][k]), Decimal(v)
            tol = Decimal('1e-37') if k in ('G7', 'H7_unit') else rel_tol
            r = abs(a - b) / abs(b); n += 1; worst = max(worst, r)
            if r > tol:
                bad.append(f'{grp}.{k} {r:.2e}')
    for k in ('C6_reassembled_from_series', 'C6_reassembled_real_form', 'reference_interval_midpoint', 'C6_reassembled_with_Barnes_seventh'):
        a, b = Decimal(new[k]), Decimal(old[k])
        tol = Decimal('1e-37') if 'Barnes' in k else rel_tol
        r = abs(a - b) / abs(b); n += 1; worst = max(worst, r)
        if r > tol:
            bad.append(f'{k} {r:.2e}')
    t.ok(f'{tag}.values', not bad, f'reassembly: {n} values (8 blocks, 9 fixed values, 4 C6 strings) agree with outputs/reassembly.json',
         f'worst rel diff {float(worst):.2e}; {bad[:4]}', '1e-85 rel (110-digit assembly); 1e-37 for the 40-digit Barnes values')
    bad = []
    for k, v in old['absolute_discrepancies'].items():
        a, b = Decimal(new['absolute_discrepancies'][k]), Decimal(v)
        if 'Barnes' in k:
            good = abs(a - b) <= Decimal('1e-6') * b
        else:
            good = a < Decimal('1e-85') and b < Decimal('1e-85')
        if not good:
            bad.append(f'{k}: {a:.3e} vs {b:.3e}')
    t.ok(f'{tag}.discrepancies', not bad, 'reassembly: internal discrepancies (series, real form, Barnes seventh) reproduce',
         f'{bad}' if bad else 'all below 1e-85 (110-digit rounding level); Barnes ones to 1e-6 rel', '< 1e-85 abs; Barnes 1e-6 rel')


def compare_tables(t, newdir, olddir, tag):
    import csv
    bad, n = [], 0
    for p in sorted(olddir.glob('*.csv')):
        q = newdir / p.name
        if not q.is_file():
            bad.append(f'{p.name} missing'); continue
        ra, rb = list(csv.reader(p.open())), list(csv.reader(q.open()))
        if len(ra) != len(rb) or ra[0] != rb[0]:
            bad.append(f'{p.name} shape'); continue
        for x, y in zip(ra[1:], rb[1:]):
            for u, v in zip(x, y):
                n += 1
                du, dv = as_dec(u), as_dec(v)
                if du is not None and dv is not None:
                    sc = max(abs(du), abs(dv))
                    if sc and abs(du - dv) / sc > Decimal('1e-30'):
                        bad.append(f'{p.name}: {u[:20]} vs {v[:20]}')
                elif u != v:
                    bad.append(f'{p.name}: {u[:20]} vs {v[:20]}')
    t.ok(f'{tag}.tables', not bad, 'outputs/tables/*.csv regenerate', f'{n} cells; {bad[:3]}', '1e-30 rel (printed 12 to 55 digits)')


def replay(t: Table, work: Path, quoted_path: Path, graph_sum_paths):
    import mpmath as mp
    import sympy as sp
    mp.mp.dps = 120
    Q = read_json(quoted_path)
    cp = copy_package(work / 'replay' / 'pkg')
    # R1. regenerate reassembly from the shipped run records
    rc, dt, out = run([sys.executable, 'code/make_outputs.py'], cp, work / 'replay' / 'make_outputs.log')
    if not t.ok('reassembly.run', rc == 0, 'code/make_outputs.py reruns from the shipped run records', f'{dt:.1f} s', 'exit status'):
        return
    new, old = read_json(cp / 'outputs/reassembly.json'), read_json(PKG / 'outputs/reassembly.json')
    compare_reassembly(t, new, old, 'reassembly')
    compare_tables(t, cp / 'outputs/tables', PKG / 'outputs/tables', 'reassembly')
    canon = [p.name for p in sorted((PKG / 'inputs/canonical').glob('*.json')) if (cp / 'inputs/canonical' / p.name).read_bytes() != p.read_bytes()]
    t.ok('reassembly.canonical', not canon, 'inputs/canonical/*.json regenerate byte-identically', f'differ: {canon}', 'bitwise')

    rep = Decimal(new['C6_reassembled_real_form'])
    # R2. quoted value of C6(1)
    for key, s in Q['C6_rep'].items():
        places = len(s.split('.')[1])
        good = rnd(rep, places) == s if key.startswith('rounded') else str(rep).startswith(s)
        t.ok(f'value.{key}', good, f'C6(1) quoted as {s}', f'{"rounded" if key.startswith("rounded") else "leading digits"} of '
             f'{str(rep)[:places + 8]}...', 'exact digits')
    # R3. sector table of note Sec 22.9 (C6 units, 9 decimals)
    b = {k: Decimal(v) for k, v in new['blocks_r6'].items()}
    pi, G = mp.pi, mp.catalan
    shift = Decimal(mp.nstr(mp.mpf(476) / 3 * pi ** 3 * (32 * G + 9 * pi ** 2), 110))
    E = b['known_real'] + shift
    S = dict(E=E, S_pol=b['known_real'] + b['log_sine_and_Clausen'] - E, S_low=b['lower'], S_6=b['sixth'], S_8=b['eighth'],
             wheel=b['wheel'], seventh=b['seventh'], primitive=b['primitive'])
    bad = [f'{k}: {rnd(S[k] / 2187, 9)} vs {v}' for k, v in Q['sector_table_C6_units'].items() if not k.startswith('_') and rnd(S[k] / 2187, 9) != v]
    t.ok('sector_table', not bad, 'Sec 22.9 sector contributions E/2187 ... 96P_a/2187 (8 entries)', f'{bad}' if bad else 'all 8 match',
         'exact digits (9 decimals)')
    tot = sum(S.values()) / 2187
    t.ok('sector_table.sum', abs(tot - rep) < Decimal('1e-84'), 'the eight sectors add up to C6(1)', f'{float(abs(tot - rep)):.1e}',
         '1e-84 abs (blocks are printed to 90 significant digits)')
    # R4. interval certificate
    cert = read_json(PKG / 'outputs/rerun/complete_refined/generated/results/complete_refined.json')
    rec = cert['C6_representation']
    lo, hi = interval(rec)
    width = hi - lo
    t.ok('interval.encoding', int(rec['upper_numerator']) - int(rec['lower_numerator']) == int(rec['width_numerator'])
         and frac_of(rec['decimal_lower']) <= lo < frac_of(rec['decimal_lower']) + Fraction(1, 10 ** rec['decimal_places'])
         and frac_of(rec['decimal_upper']) - Fraction(1, 10 ** rec['decimal_places']) < hi <= frac_of(rec['decimal_upper']),
         'complete_refined.json: dyadic bounds, width and outward decimal bounds are consistent',
         f'{rec["denominator_power_of_two"]} bits, {rec["decimal_places"]} decimals', 'exact rational')
    lim = Fraction(Decimal(Q['interval_width_below']))
    t.ok('interval.width', 0 < width < lim, f'certificate width below {Q["interval_width_below"]} (Sec 1.2, 22.9)',
         f'width {float(width):.5e}', 'exact rational')
    for key, s in Q['C6_rep'].items():
        if key.startswith('rounded'):
            continue
        places = len(s.split('.')[1])
        t.ok(f'interval.digits.{key}', trunc(lo, places) == trunc(hi, places) == s,
             f'both certified bounds begin with the quoted {places}-decimal value', s[:24] + '...', 'exact rational')
    fr = Fraction(new['C6_reassembled_real_form'])
    t.ok('interval.contains_reassembly', lo - Fraction(1, 10 ** 90) <= fr <= hi + Fraction(1, 10 ** 90),
         'the reassembled real form lies in the certified interval', f'distance to midpoint {float(abs(fr - (lo + hi) / 2)):.2e}',
         '1e-90 (110-digit floating reassembly)')
    t.ok('interval.midpoint', abs(Fraction(new['reference_interval_midpoint']) - (lo + hi) / 2) < Fraction(1, 10 ** 105),
         'reassembly reference_interval_midpoint equals the exact midpoint', '', '1e-105 abs')
    stage = read_json(PKG / 'code/stages/C6_complete_interval/results/complete_refined.json')
    t.ok('interval.stage_record', stage['C6_representation'] == rec,
         'rerun certificate equals the stage-recorded certificate (code/stages/C6_complete_interval/results/)', '', 'bitwise (JSON field)')
    ivs = [interval(read_json(PKG / f'outputs/rerun/complete_{p}/generated/results/complete_{p}.json')['C6_representation'])
           for p in ('smoke', 'release', 'refined')]
    t.ok('interval.nested', ivs[0][0] <= ivs[1][0] <= ivs[2][0] and ivs[2][1] <= ivs[1][1] <= ivs[0][1],
         'smoke, release and refined certificates are nested', ' > '.join(f'{float(b - a):.2e}' for a, b in ivs), 'exact rational')
    # R5. comparison with the independent all-graph sum
    gq = Q['graph_sum']
    pinned_c6, pinned_u = Decimal(gq['pinned_C6_unrounded']), Decimal(gq['pinned_allowance_U'])
    found = next((p for p in graph_sum_paths if p and p.is_file()), None)
    if found:
        h = sha(found)
        g = read_json(found)['headline']
        gs, U = Decimal(g['C6_unrounded']), Decimal(str(g['allowance_U']))
        t.ok('graph_sum.record', gs == pinned_c6 and U == pinned_u, 'graph-sum record found; headline values as pinned',
             f'{found} sha256 {"identical" if h == GRAPH_SUM_SHA256 else "differs from " + GRAPH_SUM_SHA256[:12]}', 'exact')
    else:
        gs, U = pinned_c6, pinned_u
        t.add('graph_sum.record', 'SKIP', 'graph-sum record not found; pinned values used',
              f'looked for {[str(p) for p in graph_sum_paths if p]}; set GRAPH_SUM=<path to C6_final.json>', '')
    t.ok('graph_sum.printed', rnd(gs, 11) == gq['unrounded'] and rnd(gs, 7) == gq['printed'].split('(')[0]
         and rnd(U * 10 ** 7, 0) == gq['printed'].split('(')[1].rstrip(')'),
         f'graph sum quoted as {gq["unrounded"]} and {gq["printed"]}', f'{gs}, U={U}', 'exact digits')
    d = rep - gs
    q = Q['difference']
    t.ok('difference.below', d < 0 and f'{float(abs(d)):.2e}' == q['below_by'], f'representation lies {q["below_by"]} below the graph sum',
         f'{float(d):.4e}', '3 significant digits')
    t.ok('difference.agreement', f'{float(abs(d)):.1e}' == q['agreement'], f'agreement to {q["agreement"]} (abstract, Sec 1, 22.1, 22.10)',
         f'{float(abs(d)):.3e}', '2 significant digits')
    t.ok('difference.allowance', rnd(abs(d) / U, 3) == q['allowance_fraction'], f'{q["allowance_fraction"]} of the allowance U',
         f'{float(abs(d) / U):.4f}', '3 decimals')
    t.ok('difference.relative_level', f'{float(U / rep):.0e}' == q['relative_level'], f'test level {q["relative_level"]} relative = U/C6(1)',
         f'U/C6 = {float(U / rep):.2e}; |difference|/C6 = {float(abs(d) / rep):.2e}', '1 significant digit')
    # R6. source repair (restored Laurent coefficients)
    corr = cert['unchanged_source_correction']
    t.ok('repair.coefficients', corr['R147_-3'] == Q['repair']['R147_-3'] and corr['R148_-3'] == Q['repair']['R148_-3'],
         'restored coefficients R_{147,-3} = R_{148,-3} = 2/5', '', 'exact')
    A_, pi_, z3_, z5_ = sp.symbols('A pi z3 z5')
    poly = sp.sympify(corr['added_polynomial_r6'], locals=dict(A=A_, pi=pi_, z3=z3_, z5=z5_))
    val = sp.N(poly.subs({A_: sp.pi + 4 * sp.log(2), pi_: sp.pi, z3_: sp.zeta(3), z5_: sp.zeta(5)}), 60)
    rep_c6 = Decimal(str(val)) / 2187
    t.ok('repair.size', rnd(rep_c6, 6) == Q['repair']['delta_C6_6'] and rnd(rep_c6, 3) == Q['repair']['delta_C6_3'],
         f'repair contributes +{Q["repair"]["delta_C6_6"]} (Sec 22.9) and +{Q["repair"]["delta_C6_3"]} (Sec 1.2) to C6',
         f'{rnd(rep_c6, 12)}', 'exact digits')
    t.ok('repair.without', rnd(rep - rep_c6, 3) == Q['repair']['C6_without'], f'without the repair C6 would be {Q["repair"]["C6_without"]}',
         f'{rnd(rep - rep_c6, 6)}', 'exact digits (3 decimals)')
    # R7. PSLQ search of the package (code/stages/C6_closed_form_attempt_report)
    st = cp / 'code/stages/C6_closed_form_attempt_report'
    rc, dt, out = run([sys.executable, 'recognition.py'], st, work / 'replay' / 'recognition.log')
    newr, oldr = read_json(st / 'recognition.json'), read_json(PKG / 'code/stages/C6_closed_form_attempt_report/recognition.json')
    good = rc == 0 and len(newr['runs']) == Q['pslq']['bases'] and all(r['result'] is None for r in newr['runs']) \
        and [r['basis'] for r in newr['runs']] == [r['basis'] for r in oldr['runs']] and newr['working_digits'] == oldr['working_digits']
    t.ok('pslq.rerun', good, 'PSLQ in the three bases of the package finds no relation (rerun, 150 digits, tol 1e-125)',
         f'{dt:.1f} s; results {[r["result"] for r in newr["runs"]]}', 'exact (no relation with coefficients below 1e6)')


# ------------------------------------------------------------------------------------------ rerun mode
def compare_rerun(t: Table, work: Path):
    cp = work / 'rerun' / 'pkg'
    core, exact, numerical, stage = selected_tasks()
    fm = read_json(cp / 'outputs/final_method_run.json')
    t.ok('rerun.profiles', fm['all_profiles_passed'] and not fm['resume_requested'],
         'code/reproduce_final.py: all three profiles passed, fresh run (no --resume)', '', 'exit status')
    tot_t = 0.0
    for task in core + exact + numerical:
        r = read_json(cp / 'outputs/rerun' / task / 'execution.json')
        o = read_json(PKG / 'outputs/rerun' / task / 'execution.json')
        tot_t += r.get('elapsed_seconds') or 0
        if r['status'] != 'passed':
            t.add(f'rerun.{task}', 'FAIL', f'task {task}', f'status {r["status"]}', 'exit status'); continue
        msgs, eq, nl, worst = [], 0, 0, Decimal(0)
        for g in o['generated_files']:
            a, b = cp / g, PKG / g
            if not a.is_file():
                msgs.append(f'{g} not regenerated'); continue
            n, e, w, m = json_diff(read_json(a), read_json(b), Decimal('1e-30'))
            nl += n; eq += e; msgs += m
            if w is not None and w > worst:
                worst = w
        same_out = (cp / 'outputs/rerun' / task / 'stdout.txt').read_text() == (PKG / 'outputs/rerun' / task / 'stdout.txt').read_text()
        t.ok(f'rerun.{task}', not msgs, f'task {task} ({stage[task]}) reproduces its shipped outputs',
             f'{r["elapsed_seconds"]:.1f} s; {len(o["generated_files"])} output files, {eq}/{nl} leaves bitwise, worst rel {worst:.1e}; '
             f'stdout identical: {same_out}; {msgs[:2]}', 'bitwise for exact rationals; 1e-30 rel for floating values; timing keys ignored')
    t.add('rerun.time', 'INFO', 'total task time', f'{tot_t:.0f} s', '')
    new, old = read_json(cp / 'outputs/reassembly.json'), read_json(PKG / 'outputs/reassembly.json')
    compare_reassembly(t, new, old, 'rerun.reassembly')
    compare_tables(t, cp / 'outputs/tables', PKG / 'outputs/tables', 'rerun.reassembly')


# ---------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['test', 'replay', 'prepare-rerun', 'compare-rerun'])
    ap.add_argument('--work', default=str(PKG / '.work'))
    ap.add_argument('--quoted', default=str(PKG / '../../results/C6_1/analytic/quoted_numbers.json'))
    ap.add_argument('--graph-sum', default='', help='path of the graph-sum record C6_final.json (LRI_C6_1D_HPC)')
    ap.add_argument('--no-smoke', action='store_true', help='test: skip the three exact tasks')
    a = ap.parse_args()
    work = Path(a.work).resolve()
    if a.mode == 'prepare-rerun':
        cp = copy_package(work / 'rerun' / 'pkg')
        print(f'fresh copy for rerun-final: {cp}')
        return 0
    if a.mode == 'test':
        t = Table('C6_research_note public test')
        integrity(t)
        if not a.no_smoke:
            exact_smoke(t, work)
        return t.write(work, 'test_report')
    if a.mode == 'replay':
        t = Table('C6_research_note public replay')
        gpaths = [Path(a.graph_sum).resolve()] if a.graph_sum else []
        gpaths += [(PKG / '../../results/C6_1/C6_final.json').resolve(),
                   (PKG / '../LRI_C6_1D_HPC/results/2026-09_symmetry/C6_final.json').resolve()]
        replay(t, work, Path(a.quoted).resolve(), gpaths)
        return t.write(work, 'replay_report')
    t = Table('C6_research_note fresh rerun of the 22 final-method tasks')
    compare_rerun(t, work)
    return t.write(work, 'rerun_report')


if __name__ == '__main__':
    raise SystemExit(main())
