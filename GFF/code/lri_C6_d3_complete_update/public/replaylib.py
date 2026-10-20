"""Shared helpers of the public replays of the d=3 research-bundle packages.

Added for the public release (2026-10-13); not part of the research bundle. The same file is shipped in the public/
folder of lri_d3_reduction_update, lri_d3_matrix_update and lri_C6_d3_complete_update.

The original scripts of these packages write their records next to the inputs (verification/, records/). A replay
therefore never runs them in the package itself: it copies the package into a work directory (default .work/,
git-ignored), runs the original commands there, and compares what they write with the shipped records and with the
numbers quoted in the condensed note. Nothing outside the work directory is written.

Merged notes (author rule 2026-10-16: one TeX note per direction): the TeX/PDF note revisions that a bundle package
carries are merged into the condensed note (GFF/note) and are not shipped. The checksum lists ship unchanged; the package's
public/dropped_paths.txt names the listed files that the release leaves out, and only those may be absent.
"""
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

import mpmath as mp

PKG = Path(__file__).resolve().parents[1]          # package root; public/ sits directly below it


# ----------------------------------------------------------------------------------------------- numbers
def parse_num(s):
    """Parse an mpmath string as written by the packages: '1.5', '-2.3e-59', '(a + bj)', '(a - bj)'."""
    if isinstance(s, (int, float)):
        return mp.mpc(s)
    s = str(s).strip()
    if s.startswith('(') and s.endswith(')'):
        s = s[1:-1].strip()
        cut = max(s.rfind(' + '), s.rfind(' - '))
        if cut > 0:
            re_part, im_part = s[:cut], s[cut + 1:].replace(' ', '')
            return mp.mpc(mp.mpf(re_part), mp.mpf(im_part.rstrip('j')))
        return mp.mpc(mp.mpf(s.rstrip('j')) * (1j if s.endswith('j') else 1))
    if s.endswith('j'):
        return mp.mpc(0, mp.mpf(s[:-1]))
    return mp.mpc(mp.mpf(s))


def real(s):
    return parse_num(s).real


def short(x, n=6):
    try:
        x = parse_num(x) if isinstance(x, str) else x
        if isinstance(x, mp.mpc) and x.imag == 0:
            x = x.real
        return mp.nstr(x, n)
    except Exception:
        return str(x)[:60]


def shown_decimals(shown):
    """Number of decimals of a fixed-point string such as '62.0583279434066724664633885840967'."""
    return len(shown.split('.')[1]) if '.' in shown else 0


def agrees_to_shown(value, shown, units=1):
    """|value - shown| <= units * 10^-decimals: the note's truncated or rounded digits ('...') are reproduced."""
    tol = mp.mpf(units) * mp.mpf(10) ** (-shown_decimals(shown))
    return abs(mp.mpf(value) - mp.mpf(shown)) <= tol, tol


def rounds_to(value, shown):
    """value rounded to the significant digits of shown (e.g. '-1.02e-89', '2.27e-59') equals shown."""
    mant, _, expo = shown.lower().partition('e')
    digits = len(mant.replace('-', '').replace('.', '').lstrip('0'))
    got = mp.nstr(mp.mpf(value), digits, min_fixed=1, max_fixed=0)
    return (mp.mpf(got) == mp.mpf(shown)), got


def about(value, k):
    """'about 10^k' in the note: 10^(k-1) < |value| < 10^(k+1)."""
    v = abs(mp.mpf(value))
    return mp.mpf(10) ** (k - 1) < v < mp.mpf(10) ** (k + 1)


def numeric_leaves(x, prefix=''):
    """Yield (path, string) for every string leaf that parses as a number."""
    if isinstance(x, dict):
        for k, v in x.items():
            yield from numeric_leaves(v, f'{prefix}/{k}')
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from numeric_leaves(v, f'{prefix}[{i}]')
    elif isinstance(x, str):
        try:
            parse_num(x)
        except Exception:
            return
        yield prefix, x


def max_leaf_difference(a, b, skip=()):
    """Largest |a-b| over matching numeric string leaves; also reports structural mismatches."""
    la = {p: v for p, v in numeric_leaves(a) if not any(s in p for s in skip)}
    lb = {p: v for p, v in numeric_leaves(b) if not any(s in p for s in skip)}
    if set(la) != set(lb):
        return None, sorted(set(la) ^ set(lb))[:5]
    worst = mp.mpf(0)
    for p in la:
        d = abs(parse_num(la[p]) - parse_num(lb[p]))
        worst = max(worst, d)
    return worst, len(la)


def strip_keys(x, keys):
    if isinstance(x, dict):
        return {k: strip_keys(v, keys) for k, v in x.items() if k not in keys}
    if isinstance(x, list):
        return [strip_keys(v, keys) for v in x]
    return x


# ----------------------------------------------------------------------------------------------- report
class Report:
    def __init__(self, title, work):
        self.title = title
        self.work = Path(work)
        self.rows = []

    def add(self, check, status, observed='', reference='', tolerance='', source=''):
        self.rows.append([check, status, str(observed), str(reference), str(tolerance), str(source)])
        print(f'{status:4s}  {check}  [{observed}]', flush=True)

    def check(self, check, ok, observed='', reference='', tolerance='', source=''):
        self.add(check, 'PASS' if ok else 'FAIL', observed, reference, tolerance, source)
        return ok

    def guard(self, check, fn, source=''):
        """Run a check function; an exception (missing key, unparsable value) is a FAIL, not a crash."""
        try:
            fn()
        except Exception as ex:  # noqa: BLE001
            self.add(check, 'FAIL', f'{type(ex).__name__}: {ex}'[:160], '', '', source)

    def write(self):
        n_pass = sum(r[1] == 'PASS' for r in self.rows)
        n_fail = sum(r[1] == 'FAIL' for r in self.rows)
        n_skip = sum(r[1] == 'SKIP' for r in self.rows)
        n_info = sum(r[1] == 'INFO' for r in self.rows)
        esc = lambda s: s.replace('|', '\\|').replace('\n', ' ')
        lines = [f'# {self.title}', '',
                 f'{n_pass} PASS, {n_fail} FAIL, {n_skip} SKIP' + (f', {n_info} INFO' if n_info else ''), '',
                 '| # | check | status | observed | reference | tolerance / why | source |',
                 '|---|---|---|---|---|---|---|']
        for i, r in enumerate(self.rows, 1):
            lines.append('| ' + ' | '.join([str(i)] + [esc(x) for x in r]) + ' |')
        text = '\n'.join(lines) + '\n'
        self.work.mkdir(parents=True, exist_ok=True)
        (self.work / 'REPLAY.md').write_text(text)
        print()
        print(text)
        print(f'written: {self.work.name}/REPLAY.md')
        return 1 if n_fail else 0


# ----------------------------------------------------------------------------------------------- files
def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def shipped_files():
    out = []
    for p in sorted(PKG.rglob('*')):
        rel = p.relative_to(PKG).as_posix()
        if p.is_file() and not rel.startswith(('public/', '.work/', '.work')) and rel != 'public.mk' \
                and '__pycache__' not in rel and p.name != '.DS_Store' and not rel.endswith('.pyc'):
            out.append(rel)
    return out


def scrubbed_paths():
    """Files the public export's privacy scrub changed (public/SCRUBBED.txt: one package-relative path per line, '#'
    comments). They are bound only by checksum lists, so a listed file is counted as scrubbed instead of compared."""
    f = PKG / 'public/SCRUBBED.txt'
    if not f.is_file():
        return set()
    return {l.split('#', 1)[0].strip() for l in f.read_text().splitlines() if l.split('#', 1)[0].strip()}


def dropped_paths():
    """Listed files that the public release leaves out on purpose (public/dropped_paths.txt: one package-relative path per
    line, '#' comments): the package's TeX/PDF note revisions, merged into the condensed note GFF/note (author rule
    2026-10-16: one TeX note per direction), and superseded drafts. A path named there must be absent, and the checksum
    lists keep their lines for it."""
    f = PKG / 'public/dropped_paths.txt'
    if not f.is_file():
        return set()
    return {l.split('#', 1)[0].strip() for l in f.read_text().splitlines() if l.split('#', 1)[0].strip()}


def check_bundle_sums(rep, listfile='public/BUNDLE_SHA256SUMS', complete=True):
    """Every shipped file (outside public/) is listed and byte-identical to the research bundle.

    complete=True: the list names the whole package and every listed file is shipped, except the paths of
    public/dropped_paths.txt, which must be absent (one INFO row counts them). complete=False: the release ships a
    subset; listed files that are not shipped are counted, not failed.
    """
    lines = [l.split(None, 1) for l in (PKG / listfile).read_text().splitlines() if l.strip()]
    listed = {path.strip(): digest for digest, path in lines}
    files = shipped_files()
    scrub = scrubbed_paths()
    dropped = dropped_paths()
    bad = [f for f in files if f in listed and f not in scrub and sha256(PKG / f) != listed[f]]
    unlisted = [f for f in files if f not in listed]
    present_dropped = [f for f in files if f in dropped]
    stray = sorted(f for f in dropped if f not in listed)
    gone = [f for f in listed if f in dropped and not (PKG / f).exists()]
    missing = [f for f in listed if f not in dropped and not (PKG / f).exists()]
    ok = not bad and not unlisted and not present_dropped and not stray and (not missing or not complete)
    rep.check('shipped files byte-identical to the research bundle', ok,
              f'{len(files) - len(bad) - len(unlisted)}/{len(files)} match; differ {bad[:3]}, unlisted '
              f'{unlisted[:3]}, ' + (f'missing {missing[:3]}' if complete else f'{len(missing)} listed files not shipped')
              + (f', dropped but present {present_dropped[:3]}' if present_dropped else '')
              + (f', dropped_paths.txt names unlisted {stray[:3]}' if stray else ''),
              f'{len(listed)} lines of {listfile}',
              'exact (sha256)' + ('; only public/dropped_paths.txt may be absent' if complete else '; ignore-missing'),
              'LRI_complete_research_bundle.zip MANIFEST.sha256, the lines of this bundle package (shipped unchanged)')
    if dropped:
        rep.add('merged notes and superseded drafts not shipped (public/dropped_paths.txt)', 'INFO',
                f'{len(gone)} listed files absent as declared', f'{len(dropped)} paths in public/dropped_paths.txt',
                'not a check: their substance is in the condensed note (GFF/note)', listfile)


def check_own_list(rep, listfile, entries, strict=False):
    """The package's own checksum list, shipped unchanged.

    strict=False: ignore-missing semantics (the release ships a subset of the listed files). strict=True: every listed
    file is shipped, except the paths of public/dropped_paths.txt, which must be absent.
    """
    ok, bad, absent, gone = 0, [], [], 0
    scrub = scrubbed_paths()
    dropped = dropped_paths()
    for path, digest in entries:
        if not (PKG / path).exists():
            if path in dropped:
                gone += 1
            else:
                absent.append(path)
        elif path in dropped:
            bad.append(path + ' (in public/dropped_paths.txt but present)')
        elif path in scrub:
            ok += 1
        elif sha256(PKG / path) == digest:
            ok += 1
        else:
            bad.append(path)
    if strict:
        rep.check(f'package checksum list {listfile} (only public/dropped_paths.txt may be absent)',
                  not bad and not absent and ok > 0, f'{ok} shipped files match, {len(bad)} differ {bad[:3]}, '
                  f'missing {absent[:3]}', f'{gone} listed files dropped as declared', 'exact (sha256)', listfile)
    else:
        rep.check(f'package checksum list {listfile} (ignore-missing)', not bad and ok > 0,
                  f'{ok} shipped files match, {len(bad)} differ', f'{len(absent) + gone} listed files not shipped (ignored)',
                  'exact (sha256)', listfile)


# ----------------------------------------------------------------------------------------------- work copy
def make_work(work, name='pkg'):
    dst = Path(work) / name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(PKG, dst, ignore=shutil.ignore_patterns('.work*', 'public', 'public.mk', '__pycache__', '*.pyc'))
    for p in [dst, *dst.rglob('*')]:
        mode = p.stat().st_mode
        p.chmod(mode | stat.S_IWUSR | (stat.S_IXUSR if p.is_dir() else 0))
    return dst


def run(rep, label, cmd, cwd, logdir, env=None, expect=None):
    """Run an original command in the work copy; log to logdir/<label>.log; PASS if exit 0 (and expect in stdout)."""
    logdir = Path(logdir)
    logdir.mkdir(parents=True, exist_ok=True)
    full_env = dict(os.environ)
    full_env.update({'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '0'})
    full_env.update(env or {})
    start = time.time()
    proc = subprocess.run(cmd, cwd=cwd, env=full_env, capture_output=True, text=True)
    sec = time.time() - start
    (logdir / f'{label}.log').write_text(proc.stdout + ('\n[stderr]\n' + proc.stderr if proc.stderr else ''))
    ok = proc.returncode == 0 and (expect is None or expect in proc.stdout)
    shown = ' '.join(f'{k}={v}' for k, v in (env or {}).items())
    rep.check(f'run {label}', ok, f'exit {proc.returncode}, {sec:.1f} s',
              (f'stdout contains "{expect}"' if expect else 'exit 0'), '', (shown + ' ' if shown else '')
              + ' '.join(cmd[1:]))
    return ok, proc.stdout


def load(path):
    return json.loads(Path(path).read_text())


def common_args(argv, default_results):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--tier', choices=['test', 'replay', 'search'], default='replay')
    ap.add_argument('--work', default='.work')
    ap.add_argument('--results', default=default_results)
    a = ap.parse_args(argv)
    a.work = (PKG / a.work).resolve() if not os.path.isabs(a.work) else Path(a.work)
    a.results = (PKG / a.results).resolve() if not os.path.isabs(a.results) else Path(a.results)
    return a


def py():
    return sys.executable or 'python3'
