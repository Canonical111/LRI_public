#!/usr/bin/env python3
"""A-ASM-1(a), R01: the vendored assembly and its tests run from an isolated export of the package.

Default (the Mac, G-H2 and G2b): `git archive HEAD` into a fresh temporary directory outside Agent_LRI.
`--in-place` (the cluster, J-VAL-1): the package directory itself, which must be a `git archive` export (no .git),
for example $C8_PACKAGE.

In that export it runs, each in a fresh Python process with an open-audit hook installed through `sitecustomize`
(every Python process, the tests' own subprocesses included):
  * the vendored tests, `python -m pytest vendor/c8_assembly/tests/test_order8_assembly.py`, with
    LRI_ROOT=<export>/vendor/c8_assembly_fixtures and without LRI_ROOT. The pass, skip and fail counts must equal the
    counts HANDOFF_assembly.json records for each mode ("30 passed"; "21 passed, 9 skipped"), so no test is
    skipped for a missing external file when the fixtures are given, and no test fails at import or for a missing
    vendored file;
  * the vendored `exact_check.py` (never with --write) in both modes; it must complete (exit 0).
Then it checks:
  * the audit log records no file opened outside the export, the run's temporary directory and the Python
    installation (sys.prefix, sys.base_prefix and their site directories);
  * the export is unchanged by the runs (every file's size and sha256 before and after; no __pycache__, no
    .pytest_cache), and vendor/c8_assembly/ holds exactly the HANDOFF's deliverables plus the HANDOFF copy.
Environment of the runs: PYTHONDONTWRITEBYTECODE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, `-p no:cacheprovider`, a
pytest configuration file in the temporary directory (no ini search above the export) with --rootdir and --confcutdir
at the export (pytest 9 otherwise builds directory nodes from the common ancestor, e.g. `/` on Expanse, where listing
/expanse/lustre/scratch fails), PYTHONPYCACHEPREFIX unset,
TMPDIR inside the run's temporary directory (H2 review, handoff-tests lens).
`--extra-lri-root DIR` repeats the fixture-mode test run with LRI_ROOT=DIR and checks its counts only (checklist
step 1 on the Mac: DIR=/Users/zheng/Documents/Agent_LRI; reads under DIR are allowed for that run).

The record (--output) says "passed": true only when every step ran to its end ("completed": true) and every check
passed; an exception or interruption is recorded as a failed check with its "error", and the process exits nonzero
(checkpoint review T-02).

Usage: python3 -B tests/vendored_isolated.py [--in-place] [--extra-lri-root DIR] [--output FILE] [--keep]
Exit status 0 when every check passes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = Path('vendor/c8_assembly')
FIXTURES = Path('vendor/c8_assembly_fixtures')
TESTS = VENDOR / 'tests/test_order8_assembly.py'

SITECUSTOMIZE = r'''
# open-audit hook of tests/vendored_isolated.py: every Python process of the run logs the paths it opens
import os, sys
_log = os.environ.get('C8_AUDIT_LOG')
if _log:
    _fh = open(f"{_log}.{os.getpid()}", "a", buffering=1)
    _busy = [False]
    _EV = {"open", "os.listdir", "os.scandir", "subprocess.Popen", "os.exec", "os.posix_spawn"}
    def _hook(ev, args):
        if ev not in _EV or _busy[0]:
            return
        _busy[0] = True
        try:
            a = args[0] if args else None
            if isinstance(a, int):  # a descriptor of an already opened file or directory (e.g. rmtree's fd walk)
                return
            if isinstance(a, bytes):
                a = os.fsdecode(a)
            if ev in ("subprocess.Popen", "os.exec", "os.posix_spawn"):
                _fh.write(f"{ev}\t\t{args[1]!r}\n")
                return
            if a is None:
                a = "."
            mode = args[1] if ev == "open" and len(args) > 1 else ""
            _fh.write(f"{ev}\t{mode}\t{os.path.abspath(os.fspath(a))}\n")
        except Exception as e:
            _fh.write(f"ERR\t{ev}\t{e!r}\n")
        finally:
            _busy[0] = False
    sys.addaudithook(_hook)
'''


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def snapshot(root: Path) -> dict[str, tuple[int, str]]:
    """Every path of the export with its size and mtime; files under vendor/ also with their sha256 (an in-place
    export on a cluster holds the multi-GB L8 packs, which are not re-hashed here)."""
    out = {}
    for d, dirs, files in os.walk(root):
        for name in dirs + files:
            p = Path(d) / name
            rel = p.relative_to(root).as_posix()
            if p.is_symlink():
                out[rel] = (-1, 'symlink')
            elif p.is_file():
                st = p.stat()
                out[rel] = (st.st_size, sha256_file(p) if rel.startswith('vendor/') else f'mtime {st.st_mtime_ns}')
            elif p.is_dir():
                out[rel] = (0, 'dir')
    return out


def handoff_counts(text: str) -> dict:
    """Pass/skip/fail counts per mode from the HANDOFF's checks_at_handoff.tests sentence."""
    m_root = re.match(r'\s*(\d+) passed\b', text)
    m_plain = re.search(r'without LRI_ROOT:\s*(\d+) passed,\s*(\d+) skipped', text)
    if not m_root or not m_plain:
        raise SystemExit(f'cannot read the test counts from the HANDOFF: {text!r}')
    return {'fixtures': dict(passed=int(m_root.group(1)), skipped=0, failed=0, errors=0),
            'no_lri_root': dict(passed=int(m_plain.group(1)), skipped=int(m_plain.group(2)), failed=0, errors=0)}


def junit_counts(path: Path) -> dict:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == 'testsuite' else list(root.iter('testsuite'))
    tot = dict(tests=0, failed=0, errors=0, skipped=0)
    for s in suites:
        tot['tests'] += int(s.get('tests', 0))
        tot['failed'] += int(s.get('failures', 0))
        tot['errors'] += int(s.get('errors', 0))
        tot['skipped'] += int(s.get('skipped', 0))
    return dict(passed=tot['tests'] - tot['failed'] - tot['errors'] - tot['skipped'], skipped=tot['skipped'],
                failed=tot['failed'], errors=tot['errors'])


def python_dirs() -> list[str]:
    import site
    import sysconfig
    dirs = {sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix}
    for key in ('stdlib', 'platstdlib', 'purelib', 'platlib', 'include', 'scripts', 'data'):
        try:
            dirs.add(sysconfig.get_path(key))
        except KeyError:
            pass
    try:
        dirs.update(site.getsitepackages())
    except AttributeError:
        pass
    dirs.add(site.getusersitepackages())
    return sorted({os.path.realpath(d) for d in dirs if d})


def inside(path: str, roots: list[str]) -> bool:
    rp = os.path.realpath(path)
    return any(rp == r or rp.startswith(r.rstrip('/') + '/') for r in roots)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--in-place', action='store_true', help='run in this package directory (a git archive export)')
    ap.add_argument('--extra-lri-root', type=Path, help='also run the tests with LRI_ROOT=DIR (counts only)')
    ap.add_argument('--output', type=Path)
    ap.add_argument('--keep', action='store_true', help='keep the temporary directory')
    a = ap.parse_args()
    results, failed = [], []

    def check(name: str, ok: bool, detail='') -> None:
        detail = detail if isinstance(detail, str) else json.dumps(detail, default=str)
        results.append(dict(check=name, passed=bool(ok), detail=detail[-1500:]))
        if not ok:
            failed.append(name)
        print(('PASS ' if ok else 'FAIL ') + name + (f': {detail[-600:]}' if detail and not ok else ''), flush=True)

    tmp = Path(tempfile.mkdtemp(prefix='c8d2_vendored_isolated_')).resolve()
    rec: dict = dict(schema='c8-d2-gate-1', gate='A-ASM-1(a) vendored_isolated', mode='in-place' if a.in_place else
                     'git archive export', python=sys.version.split()[0], executable=sys.executable,
                     host=os.uname().nodename, temporary=str(tmp), runs={})
    # T-02: the record passes only when every step ran to its end. An exception or interruption anywhere (a refused
    # --in-place, an unreadable HANDOFF or JUnit file, ^C) is recorded as a failed check and the record says so.
    completed = False
    error = None
    try:
        if a.in_place:
            export = ROOT
            if (export / '.git').exists():
                raise SystemExit('--in-place needs a git archive export (this directory has .git)')
            rec['export'] = str(export)
        else:
            export = tmp / 'export'
            export.mkdir()
            head = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True,
                                  check=True).stdout.strip()
            arch = subprocess.run(['git', '-C', str(ROOT), 'archive', '--format=tar', head], capture_output=True,
                                  check=True).stdout
            subprocess.run(['tar', '-x', '-C', str(export)], input=arch, check=True)
            rec.update(export=str(export), commit=head)
        agent = ROOT.parent if not a.in_place else None
        if agent is not None and inside(str(export), [str(agent.resolve())]):
            raise SystemExit(f'the export {export} lies inside {agent}')
        handoff = json.loads((export / VENDOR / 'HANDOFF_assembly.json').read_bytes())
        want = handoff_counts(handoff['checks_at_handoff']['tests'])
        listed = sorted(f['path'] for f in handoff['files'])
        rec['handoff_counts'] = want
        before = snapshot(export)
        vend = sorted(k[len(str(VENDOR)) + 1:] for k, v in before.items()
                      if k.startswith(str(VENDOR) + '/') and v[1] != 'dir')
        check('vendor/c8_assembly holds exactly the HANDOFF deliverables plus the HANDOFF copy',
              vend == sorted(listed + ['HANDOFF_assembly.json']), dict(extra=sorted(set(vend) - set(listed) -
                                                                                     {'HANDOFF_assembly.json'}),
                                                                       missing=sorted(set(listed) - set(vend))))
        site = tmp / 'site'
        site.mkdir()
        (site / 'sitecustomize.py').write_text(SITECUSTOMIZE)
        ini = tmp / 'pytest.ini'
        ini.write_text('[pytest]\n')
        pyroots = python_dirs()
        rec['python_dirs'] = pyroots
        allowed_base = [str(export.resolve()), str(tmp)] + pyroots + ['/dev/null']

        def env_for(tag: str, lri_root: Path | None) -> dict:
            env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPYCACHEPREFIX', 'LRI_ROOT', 'PYTHONPATH',
                                                                    'PYTHONSTARTUP', 'PYTHONHOME')}
            (tmp / f'tmp_{tag}').mkdir()
            env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONPATH=str(site),
                       C8_AUDIT_LOG=str(tmp / f'audit_{tag}'), TMPDIR=str(tmp / f'tmp_{tag}'),
                       OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
            if lri_root is not None:
                env['LRI_ROOT'] = str(lri_root)
            return env

        def audit(tag: str, extra_allowed: list[str]) -> list[str]:
            """Paths opened or listed outside the allowed areas, and any open for writing inside the export. A run
            whose audit logs are missing, or record no open of a vendored file, is itself a violation (the hook did
            not load, so the check would be vacuous)."""
            outside = []
            logs = sorted(tmp.glob(f'audit_{tag}.*'))
            vend = str((export / VENDOR).resolve())
            if not any(f'open\tr' in ln and vend in ln for log in logs for ln in log.read_text().splitlines()):
                outside.append(f'no audit record of an open under {vend}: the open-audit hook did not run')
            for log in logs:
                for line in log.read_text().splitlines():
                    parts = line.split('\t')
                    if parts[0] == 'ERR':
                        outside.append(f'audit hook error: {line}')
                    if parts[0] in ('subprocess.Popen', 'os.exec', 'os.posix_spawn', 'ERR') or len(parts) != 3:
                        continue
                    if not inside(parts[2], allowed_base + extra_allowed):
                        outside.append(f'{parts[0]} {parts[1]} {parts[2]}')
                    elif (parts[0] == 'open' and any(c in parts[1] for c in 'wax+')
                          and inside(parts[2], [str(export.resolve())])):
                        outside.append(f'write inside the export: {parts[1]} {parts[2]}')
            return sorted(set(outside))

        def run_tests(tag: str, lri_root: Path | None, extra_allowed: list[str]) -> dict:
            junit = tmp / f'junit_{tag}.xml'
            t0 = time.time()
            r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-c', str(ini),
                                '--rootdir', str(export), '--confcutdir', str(export), f'--junitxml={junit}', str(TESTS)],
                               cwd=export,
                               env=env_for(tag, lri_root), capture_output=True, text=True)
            got = junit_counts(junit) if junit.exists() else dict(passed=0, skipped=0, failed=-1, errors=-1)
            out = dict(lri_root=str(lri_root) if lri_root else None, returncode=r.returncode, counts=got,
                       seconds=round(time.time() - t0, 1), tail=(r.stdout + r.stderr)[-1500:],
                       outside_reads=audit(tag, extra_allowed))
            rec['runs'][tag] = out
            return out

        def run_exact(tag: str, lri_root: Path | None) -> dict:
            t0 = time.time()
            r = subprocess.run([sys.executable, '-B', str(VENDOR / 'exact_check.py')], cwd=export,
                               env=env_for(tag, lri_root), capture_output=True, text=True)
            try:
                res = json.loads(r.stdout)
            except ValueError:
                res = None
            out = dict(lri_root=str(lri_root) if lri_root else None, returncode=r.returncode,
                       seconds=round(time.time() - t0, 1), keys=sorted(res) if isinstance(res, dict) else None,
                       stderr_tail=r.stderr[-800:], outside_reads=audit(tag, []))
            if isinstance(res, dict):
                (tmp / f'exact_check_{tag}.json').write_text(json.dumps(res, indent=1) + '\n')
            rec['runs'][tag] = out
            return out

        fx = (export / FIXTURES).resolve()
        for tag, lri in (('tests_fixtures', fx), ('tests_no_lri_root', None)):
            r = run_tests(tag, lri, [])
            mode = 'fixtures' if lri else 'no_lri_root'
            check(f'vendored tests, {"LRI_ROOT=fixtures" if lri else "no LRI_ROOT"}: counts equal the HANDOFF '
                  f'({want[mode]})', r['counts'] == want[mode] and r['returncode'] == 0, r)
            check(f'vendored tests, {"LRI_ROOT=fixtures" if lri else "no LRI_ROOT"}: no file opened outside the '
                  f'export, the temporary directory and the Python installation', not r['outside_reads'],
                  r['outside_reads'][:30])
        for tag, lri in (('exact_fixtures', fx), ('exact_no_lri_root', None)):
            r = run_exact(tag, lri)
            check(f'exact_check.py completes, {"LRI_ROOT=fixtures" if lri else "no LRI_ROOT"}',
                  r['returncode'] == 0 and r['keys'] is not None, r)
            check(f'exact_check.py, {"LRI_ROOT=fixtures" if lri else "no LRI_ROOT"}: no file opened outside the '
                  f'export, the temporary directory and the Python installation', not r['outside_reads'],
                  r['outside_reads'][:30])
        after = snapshot(export)
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        check('the export is unchanged by the runs (no __pycache__, .pytest_cache or other new or changed file)',
              not changed, changed[:30])
        if a.extra_lri_root:
            x = a.extra_lri_root.resolve()
            r = run_tests('tests_extra_lri_root', x, [str(x)])
            check(f'vendored tests with LRI_ROOT={x}: counts equal the HANDOFF ({want["fixtures"]})',
                  r['counts'] == want['fixtures'] and r['returncode'] == 0, r)
        completed = True
    except BaseException as e:  # recorded, then re-raised: the process still exits nonzero with its message
        error = f'{type(e).__name__}: {e}'
        check('the verification ran to completion', False, f'aborted by {error}')
        raise
    finally:
        rec.update(passed=completed and bool(results) and not failed, completed=completed, error=error,
                   failed=failed, checks=results)
        if a.output:
            a.output.parent.mkdir(parents=True, exist_ok=True)
            a.output.write_text(json.dumps(rec, indent=1) + '\n')
        if not a.keep:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f'vendored_isolated: {len(results) - len(failed)}/{len(results)} checks passed')
    return 0 if rec['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
