"""Helpers of the public replay scripts.

The same file is shipped in public/ of lri_numerical_resolution, lri_psi_complete_update and
lri_fixed_hypergeometric_update, so that each package replays on its own. Written for the public
edition (2026-10-13); not part of the original packages.

The original verification scripts write their records in place, so every run happens in a fresh copy of
the package under .work/ (git-ignored). Nothing in the package tree is written.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

import mpmath as mp

PKG = Path(__file__).resolve().parent.parent            # GFF/code/<pkg>
QUOTED_DEFAULT = PKG.parent.parent / 'results' / 'closed_forms_1' / 'C5_1_quoted.json'
mp.mp.dps = 160                                          # parsing and comparison only

NUM = re.compile(r'^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$')
CPX = re.compile(r'^\(?\s*([+-]?[\d.]+(?:[eE][+-]?\d+)?)\s*([+-])\s*([\d.]+(?:[eE][+-]?\d+)?)j\s*\)?$')


class Table:
    """PASS/FAIL table printed while running and written as Markdown at the end."""

    def __init__(self, title: str):
        self.title, self.rows, self.t0 = title, [], time.time()

    def add(self, check, ok, recomputed='', reference='', tolerance=''):
        row = (str(check), bool(ok), str(recomputed), str(reference), str(tolerance))
        self.rows.append(row)
        print(f"{'PASS' if ok else 'FAIL'}  {row[0]}  |  {row[2]}  |  ref {row[3]}  |  {row[4]}", flush=True)
        return bool(ok)

    def finish(self, path: Path) -> int:
        nfail = sum(not r[1] for r in self.rows)
        esc = lambda s: s.replace('|', '\\|')
        lines = [f'# {self.title}', '',
                 f'{len(self.rows)} checks, {nfail} FAIL, {time.time() - self.t0:.1f} s wall, '
                 f'Python {sys.version.split()[0]}, mpmath {mp.__version__}', '',
                 '| Result | Check | Recomputed | Reference | Tolerance |', '|---|---|---|---|---|']
        lines += [f"| {'PASS' if ok else 'FAIL'} | {esc(c)} | {esc(a)} | {esc(b)} | {esc(t)} |"
                  for c, ok, a, b, t in self.rows]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(lines) + '\n')
        print(f'\n{len(self.rows)} checks, {nfail} FAIL. Table: {path}')
        return 1 if nfail else 0


def fresh_copy(work: Path) -> Path:
    """Copy the shipped package (without .work, public/, public.mk) to work/pkg and return that path."""
    dst = work / 'pkg'
    if dst.exists():
        shutil.rmtree(dst)
    ignore = shutil.ignore_patterns('.work', 'public', 'public.mk', '__pycache__', '*.pyc')
    shutil.copytree(PKG, dst, ignore=ignore)
    for d, dirs, files in os.walk(dst):              # sources may be read-only (bundle extraction)
        for x in dirs + files:
            p = os.path.join(d, x)
            os.chmod(p, os.stat(p).st_mode | 0o200)
    return dst


def run(table: Table, label: str, args, cwd: Path, logdir: Path, outputs=(), check_rc=True):
    """Run one script with this Python, single-threaded; log to logdir/<label>.log. The files in outputs
    (the records the script writes) are deleted first, so that a failed run cannot leave a stale copy."""
    for o in outputs:
        Path(o).unlink(missing_ok=True)
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
               PYTHONDONTWRITEBYTECODE='1')
    env.pop('LRI_BASELINE', None)
    logdir.mkdir(parents=True, exist_ok=True)
    t = time.time()
    out = subprocess.run([sys.executable] + [str(a) for a in args], cwd=cwd, env=env,
                         capture_output=True, text=True)
    dt = time.time() - t
    (logdir / (re.sub(r'[^A-Za-z0-9_.-]+', '_', label) + '.log')).write_text(out.stdout + ('\n--- stderr ---\n' + out.stderr if out.stderr else ''))
    if check_rc:
        kind = 'public-edition script' if Path(str(args[0])).parent.name == 'public' else 'original script, unchanged'
        table.add(f'run {label}', out.returncode == 0, f'exit {out.returncode}, {dt:.1f} s', 'exit 0', kind)
    return out.returncode == 0, out.stdout


def load(path: Path):
    return json.loads(Path(path).read_text(), parse_float=str)


def as_num(x):
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, int):
        return mp.mpf(x)
    if isinstance(x, float):
        return mp.mpf(repr(x))
    if isinstance(x, str):
        s = x.strip()
        if NUM.match(s):
            return mp.mpf(s)
        m = CPX.match(s)
        if m:
            re_, sign, im = m.groups()
            return mp.mpc(mp.mpf(re_), mp.mpf(im) * (1 if sign == '+' else -1))
    return None


def compare_records(new, old, rtol, skip=('elapsed_seconds',), path=''):
    """Recursive comparison. Integers, booleans and non-numeric strings must be equal; decimal strings
    (real or complex) must satisfy |new - old| <= rtol * max(1, |old|). Returns (count, max_dev, problems)."""
    problems, count, maxdev = [], 0, mp.mpf(0)
    if isinstance(old, dict):
        if not isinstance(new, dict):
            return 0, maxdev, [f'{path}: type']
        for k in old:
            if k in skip:
                continue
            if k not in new:
                problems.append(f'{path}/{k}: missing')
                continue
            c, d, p = compare_records(new[k], old[k], rtol, skip, f'{path}/{k}')
            count, maxdev, problems = count + c, max(maxdev, d), problems + p
        for k in new:
            if k not in old and k not in skip:
                problems.append(f'{path}/{k}: extra')
        return count, maxdev, problems
    if isinstance(old, list):
        if not isinstance(new, list) or len(new) != len(old):
            return 0, maxdev, [f'{path}: list length']
        for i, (a, b) in enumerate(zip(new, old)):
            c, d, p = compare_records(a, b, rtol, skip, f'{path}[{i}]')
            count, maxdev, problems = count + c, max(maxdev, d), problems + p
        return count, maxdev, problems
    if isinstance(old, (bool, int)) or old is None or isinstance(new, (bool, int)):
        return 1, maxdev, ([] if new == old and type(new) == type(old) else [f'{path}: {new!r} != {old!r}'])
    a, b = as_num(new), as_num(old)
    if a is None or b is None:
        return 1, maxdev, ([] if new == old else [f'{path}: {new!r} != {old!r}'])
    dev = abs(a - b) / max(1, abs(b))
    return 1, dev, ([] if dev <= rtol else [f'{path}: deviation {mp.nstr(dev, 3)}'])


def record_row(table, label, new_path, old_path, rtol, skip=('elapsed_seconds',)):
    old = load(old_path)
    if not Path(new_path).exists():
        table.add(f'{label}: regenerated record vs shipped {Path(old_path).name}', False, 'record not written',
                  str(Path(old_path).relative_to(PKG)), 'the script must write it')
        raise SystemExit(table.finish(Path(new_path).parent / 'VERIFY_aborted.md'))
    new = load(new_path)
    n, dev, probs = compare_records(new, old, rtol, skip)
    same = Path(new_path).read_bytes() == Path(old_path).read_bytes()
    table.add(f'{label}: regenerated record vs shipped {Path(old_path).name}', not probs,
              f'{n} fields, max scaled deviation {mp.nstr(dev, 3)}, byte-identical: {"yes" if same else "no"}'
              + (f'; first problems: {probs[:3]}' if probs else ''),
              str(Path(old_path).relative_to(PKG)),
              f'numbers |d| <= {rtol:g}*max(1,|ref|); integers, flags, strings exact; ignored: {", ".join(skip)}')
    return new


def quoted_table(path=None):
    d = json.loads(Path(path or QUOTED_DEFAULT).read_text())
    return {v['id']: v for v in d['values'] + d['package_reports']}


def ulp_of(s: str):
    s = s.replace('\\ldots', '').replace('...', '').replace(',', '').strip()
    m = re.match(r'^[+-]?\d*\.?(\d*)(?:[eE]([+-]?\d+))?$', s)
    frac, exp = m.group(1), int(m.group(2) or 0)
    return mp.mpf(s), mp.mpf(10) ** (exp - len(frac))


def check_quoted(table, q, qid, value, label=None, source=''):
    """Compare a recomputed value with the quoted entry qid (rules in C5_1_quoted.json)."""
    e = q[qid]
    kind, quoted, where = e['kind'], e['quoted'], e['where']
    name = f'{label or qid} [{where}]'
    if kind in ('decimal', 'decimal_about'):
        qv, ulp = ulp_of(quoted)
        if kind == 'decimal_about':
            ulp = mp.mpf('0.01e-9')
        v = mp.mpf(value)
        ok = abs(v - qv) <= ulp
        return table.add(name, ok, f'{mp.nstr(v, 45)} {source}'.strip(), quoted, f'|d| <= {mp.nstr(ulp, 2)} (last quoted digit)')
    if kind == 'integer':
        return table.add(name, int(value) == int(quoted), f'{value} {source}'.strip(), quoted, 'exact')
    if kind == 'exact':
        ok = value == (Fraction(quoted) if isinstance(quoted, str) else quoted)
        return table.add(name, ok, f'{value} {source}'.strip(), str(quoted), 'exact')
    if kind == 'bound':
        v, f = abs(mp.mpf(value)), e.get('factor', 10)
        ok = v <= f * mp.mpf(quoted)
        return table.add(name, ok, f'{mp.nstr(v, 8)} {source}'.strip(), quoted,
                         f'|value| <= {f} x quoted (observed residual; last digits are platform dependent)')
    if kind == 'less_than':
        v = abs(mp.mpf(value))
        return table.add(name, v < mp.mpf(quoted), f'{mp.nstr(v, 8)} {source}'.strip(), f'< {quoted}', 'strict bound')
    raise ValueError(kind)


def check_manifest(table, manifest_name, not_exported):
    """sha256_manifest.json with --ignore-missing semantics: every shipped listed file must match; the
    missing ones must be exactly the files the public export leaves out (prefixes in not_exported)."""
    recs = json.loads((PKG / manifest_name).read_text())
    bad, missing = [], []
    for r in recs:
        p = PKG / r['path']
        if not p.is_file():
            missing.append(r['path'])
        elif p.stat().st_size != r['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest() != r['sha256']:
            bad.append(r['path'])
    unexpected = [m for m in missing if not any(m == x or m.startswith(x) for x in not_exported)]
    table.add(f'{manifest_name}: shipped files byte-identical to the delivered package', not bad and not unexpected,
              f'{len(recs) - len(missing)} verified, {len(bad)} changed, {len(missing)} not exported'
              + (f'; changed {bad[:3]}' if bad else '') + (f'; unexpectedly missing {unexpected[:3]}' if unexpected else ''),
              f'{len(recs)} listed', 'sha256 exact; not-exported files skipped (ignore-missing)')


def check_sha256_list(table, listfile: Path, not_exported):
    """Same as check_manifest for a 'sha256  path' list (comment lines start with #)."""
    lines = [l.split(None, 1) for l in Path(listfile).read_text().splitlines() if l.strip() and not l.startswith('#')]
    bad, missing = [], []
    for sha, rel in lines:
        p = PKG / rel.strip()
        if not p.is_file():
            missing.append(rel.strip())
        elif hashlib.sha256(p.read_bytes()).hexdigest() != sha:
            bad.append(rel.strip())
    unexpected = [m for m in missing if not any(m == x or m.startswith(x) for x in not_exported)]
    table.add(f'{Path(listfile).name}: shipped files byte-identical to the bundle', not bad and not unexpected,
              f'{len(lines) - len(missing)} verified, {len(bad)} changed, {len(missing)} not exported'
              + (f'; changed {bad[:3]}' if bad else '') + (f'; unexpectedly missing {unexpected[:3]}' if unexpected else ''),
              f'{len(lines)} listed', 'sha256 exact; not-exported files skipped (ignore-missing)')
