#!/usr/bin/env python3
"""A-ASM-1(a): the vendored assembly, its tests, exact_check.py and prepare_low8.py run from an isolated export.

Default (the Mac, G-H2; again at G2a): `git archive HEAD` into a fresh temporary directory outside Agent_LRI.
`--in-place` (Expanse, J-E2 and J-VAL-1): the package directory itself, which must be a `git archive` export (no .git).

Each run is a fresh Python process (this interpreter) in the export, under the H2 record's run rules (PLAN A-ASM-1,
F12): PYTHONPYCACHEPREFIX unset, also for the tests' own child processes; PYTHONDONTWRITEBYTECODE=1 and `python -B`;
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, `-p no:cacheprovider`, a pytest configuration file in the temporary directory with
--rootdir and --confcutdir at the export; TMPDIR inside the run's temporary directory; and an open-audit hook installed
through `sitecustomize` in every Python process (tools/vendor_assembly.py AUDIT_SITECUSTOMIZE). The runs:
  * the vendored tests with LRI_ROOT=<export>/vendor/c8_assembly_fixtures and without LRI_ROOT: their pass, skip, fail
    and error counts must equal the HANDOFF's ("30 passed"; "21 passed, 9 skipped"). The `:134` disposition: if
    test_order7_production_reassembly fails at tests/test_order8_assembly.py:134 (<= 8 ulp) and nothing else fails, the
    failure is environmental only with --asm3-record FILE, a passing A-ASM-3 record of the same stack (python, numpy,
    CPU model, host, and SLURM_JOB_ID on a cluster) from the same job; it is recorded with its ulp count, numpy,
    Python and CPU, otherwise it is red;
  * exact_check.py (never with --write) with LRI_ROOT=fixtures: it completes, every exact key of
    tests/fixtures/exact_check_keys.json is string-equal to the vendored exact_check_results.json, every float
    diagnostic is within its asserted bound (float_vs_exact < 1e-13; d2_order5_lower_part within 1e-15 of
    -1.0775357715447757; PLAN F12), provenance keys are recorded apart, and no key is unclassified; without LRI_ROOT it
    completes and the same gate holds except for the keys that read LRI_ROOT (lri_root_dependent), which are absent;
  * `prepare_low8.py --d 3` (compare mode; writes nothing) with LRI_ROOT=fixtures: exit 0, all three files identical;
  * an order-7 diagnostic with LRI_ROOT=fixtures: the ulp distance of the reassembled C7_full (vendored coefficients()
    on the published means, as test :134 does) from each published C7_full, recorded for the `:134` disposition.
Then it checks:
  * the audit logs: every run's hook ran (some vendored file opened), and no file was opened or listed outside the
    export, the run's temporary directory and the Python installation, nor opened for writing inside the export;
  * the export is unchanged by the runs (every path; size and sha256 under vendor/, size and mtime elsewhere: no
    __pycache__, no .pytest_cache, no new file), and vendor/c8_assembly/ holds exactly the 13 HANDOFF files and the
    HANDOFF copy at the HANDOFF sha256s, before and after.
It records numpy, Python, the CPU and the host (`environment`).
`--extra-lri-root DIR` repeats the fixture-mode test run with LRI_ROOT=DIR (counts only; reads under DIR allowed).

Usage: python3 -B tests/vendored_isolated.py [--in-place] [--asm3-record FILE] [--extra-lri-root DIR] [--output FILE]
       [--keep]
The record says "passed": true only when every step ran to its end and every check passed; exit status 0 then."""
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
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
sys.dont_write_bytecode = True
import exact_keys as ek  # noqa: E402
from vendor_assembly import AUDIT_SITECUSTOMIZE, audit_events, environment, inside, junit_counts, python_dirs  # noqa: E402

VENDOR = 'vendor/c8_assembly'
FIXTURES = 'vendor/c8_assembly_fixtures'
TESTS = f'{VENDOR}/tests/test_order8_assembly.py'
TEST_134 = 'test_order7_production_reassembly'
ULPS = r'''
import json, sys
import numpy as np
from pathlib import Path
import importlib.util
p = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location('c8d3_vendored_test_order8_assembly', p)
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
out = {}
for d, hd in ((3, 1.5), (2, 1)):
    run, res = t._production(d)
    B2 = t.b2_c7(d)
    pub = {s: {int(L): np.asarray(v, float) for L, v in res['means'][s].items()} for s in res['means']}
    m = {L: pub['free'][L] + pub['power'][L] for L in range(3, 8)}
    mine = t.oa.coefficients(m, B2, 7, hd)
    c7 = float(res['C7_full'])
    out[f'd{d}'] = dict(published_C7_full=c7, reassembled_C7_full=float(mine[7]),
                        ulps=(float(mine[7]) - c7) / float(np.spacing(abs(c7))), bound_ulps=8,
                        bitwise_equal_to_delivered=mine.tobytes() == t.delivered_coeffs(d, m, B2).tobytes())
print(json.dumps(out))
'''


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def snapshot(root: Path) -> dict[str, tuple]:
    """Every path of the export: size and sha256 under vendor/ (and for the vendored tests' inputs), size and mtime
    elsewhere (an in-place export on a cluster holds the multi-GB L8 packs, which are not re-hashed here)."""
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
            else:
                out[rel] = (-2, 'special')
    return out


def handoff_counts(text: str) -> dict:
    """Pass/skip/fail counts per mode from the HANDOFF's checks_at_handoff.tests sentence."""
    m_root = re.match(r'\s*(\d+) passed\b', text)
    m_plain = re.search(r'without LRI_ROOT:\s*(\d+) passed,\s*(\d+) skipped', text)
    if not m_root or not m_plain:
        raise SystemExit(f'cannot read the test counts from the HANDOFF: {text!r}')
    return {'fixtures': dict(passed=int(m_root.group(1)), skipped=0, failed=0, errors=0),
            'no_lri_root': dict(passed=int(m_plain.group(1)), skipped=int(m_plain.group(2)), failed=0, errors=0)}


def junit_failures(path: Path) -> list[dict]:
    """Failed or erroring test cases: name and failure text."""
    out = []
    for tc in ET.parse(path).getroot().iter('testcase'):
        for kind in ('failure', 'error'):
            for el in tc.findall(kind):
                out.append(dict(name=tc.get('name'), kind=kind,
                                text=((el.get('message') or '') + '\n' + (el.text or ''))[-3000:]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--in-place', action='store_true', help='run in this package directory (a git archive export)')
    ap.add_argument('--asm3-record', type=Path, help='a passing A-ASM-3 record of this stack (the :134 disposition)')
    ap.add_argument('--extra-lri-root', type=Path, help='also run the tests with LRI_ROOT=DIR (counts only)')
    ap.add_argument('--output', type=Path)
    ap.add_argument('--keep', action='store_true', help='keep the temporary directory')
    a = ap.parse_args()
    results, failed = [], []

    def check(name: str, ok: bool, detail='') -> None:
        detail = detail if isinstance(detail, str) else json.dumps(detail, default=str)
        results.append(dict(check=name, passed=bool(ok), detail=detail[-2000:]))
        if not ok:
            failed.append(name)
        print(('PASS ' if ok else 'FAIL ') + name + (f': {detail[-800:]}' if detail and not ok else ''), flush=True)

    tmp = Path(tempfile.mkdtemp(prefix='c8d3_vendored_isolated_')).resolve()
    env_rec = environment()
    rec: dict = dict(schema='c8-d3-gate-1', gate='A-ASM-1(a) vendored_isolated',
                     mode='in-place' if a.in_place else 'git archive export', environment=env_rec,
                     temporary=str(tmp), runs={})
    completed, error = False, None
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
            dirty = subprocess.run(['git', '-C', str(ROOT), 'status', '--porcelain', '--untracked-files=no'],
                                   capture_output=True, text=True, check=True).stdout.strip()
            arch = subprocess.run(['git', '-C', str(ROOT), 'archive', '--format=tar', head], capture_output=True,
                                  check=True).stdout
            subprocess.run(['tar', '-x', '-C', str(export)], input=arch, check=True)
            rec.update(export=str(export), commit=head)
            check('the checkout has no uncommitted change to a tracked file (the checking code is the exported '
                  'commit\'s)', not dirty, dirty[:600])
            agent = ROOT.parent.resolve()
            if inside(str(export), [str(agent)]):
                raise SystemExit(f'the export {export} lies inside {agent}: set TMPDIR elsewhere')
        hbytes = (export / VENDOR / 'HANDOFF_assembly.json').read_bytes()
        handoff = json.loads(hbytes)
        rec['handoff_sha256'] = hashlib.sha256(hbytes).hexdigest()
        want = handoff_counts(handoff['checks_at_handoff']['tests'])
        listed = {f['path']: f['sha256'] for f in handoff['files']}
        rec['handoff_counts'] = want

        def vendored_state(snap: dict) -> tuple[bool, dict]:
            files = {k[len(VENDOR) + 1:]: v for k, v in snap.items() if k.startswith(VENDOR + '/') and v[1] != 'dir'}
            dirs = sorted(k for k, v in snap.items() if k.startswith(VENDOR + '/') and v[1] == 'dir')
            want_files = dict(listed, **{'HANDOFF_assembly.json': rec['handoff_sha256']})
            bad = sorted(n for n in set(files) | set(want_files) if files.get(n, (0, None))[1] != want_files.get(n))
            okdirs = all(d.split('/')[-1] in ('tests', 'inputs_d3', 'inputs_d2_check') for d in dirs)
            return not bad and okdirs, dict(differ=bad, dirs=dirs)

        before = snapshot(export)
        ok, detail = vendored_state(before)
        check('before the runs: vendor/c8_assembly holds exactly the 13 HANDOFF files and the HANDOFF copy at the '
              'HANDOFF sha256s', ok and rec['handoff_sha256'] == json.loads(
                  (export / 'tools/VENDORED.json').read_bytes())['handoff']['sha256'], detail)
        site = tmp / 'site'
        site.mkdir()
        (site / 'sitecustomize.py').write_text(AUDIT_SITECUSTOMIZE)
        ini = tmp / 'pytest.ini'
        ini.write_text('[pytest]\n')
        pyroots = python_dirs()
        rec['python_dirs'] = pyroots
        allowed_base = [str(export.resolve()), str(tmp)] + pyroots + ['/dev/null']
        fx = (export / FIXTURES).resolve()
        classes = json.loads((export / 'tests/fixtures/exact_check_keys.json').read_bytes())
        reference = json.loads((export / VENDOR / 'exact_check_results.json').read_bytes())

        def env_for(tag: str, lri_root: Path | None) -> dict:
            env = {k: v for k, v in os.environ.items()
                   if k not in ('PYTHONPYCACHEPREFIX', 'LRI_ROOT', 'PYTHONPATH', 'PYTHONSTARTUP', 'PYTHONHOME',
                                'PYTHONSAFEPATH', 'PYTHONUSERBASE', 'PYTEST_ADDOPTS', 'PYTEST_PLUGINS')}
            (tmp / f'tmp_{tag}').mkdir()
            env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONPATH=str(site),
                       C8_AUDIT_LOG=str(tmp / f'audit_{tag}'), TMPDIR=str(tmp / f'tmp_{tag}'),
                       OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
            if lri_root is not None:
                env['LRI_ROOT'] = str(lri_root)
            return env

        def audit(tag: str, extra_allowed: list[str]) -> list[str]:
            """Paths opened or listed outside the allowed areas, opens for writing inside the export, hook errors,
            and a run whose hook recorded no open of a vendored file (the check would be vacuous)."""
            out = []
            logs = sorted(tmp.glob(f'audit_{tag}.*'))
            events = audit_events(logs)
            vend = str((export / VENDOR).resolve())
            if not any(e['event'] == 'open' and not e['write'] and inside(e['path'], [vend]) for e in events):
                out.append(f'no audit record of an open under {vend}: the open-audit hook did not run')
            for e in events:
                if e['event'] == 'ERR':
                    out.append(f'audit hook error: {e["text"]}')
                    continue
                if e['fd_walk']:
                    continue
                if not inside(e['path'], allowed_base + extra_allowed):
                    out.append(f'{e["event"]} {e["mode"]} {e["path"]}')
                elif e['write'] and inside(e['path'], [str(export.resolve())]):
                    out.append(f'write inside the export: {e["mode"]} {e["path"]}')
            rec['runs'].setdefault(tag, {})['audited_events'] = len(events)
            return sorted(set(out))

        def run(tag: str, cmd: list[str], lri_root: Path | None, extra_allowed=()) -> tuple[subprocess.CompletedProcess,
                                                                                            dict]:
            t0 = time.time()
            r = subprocess.run(cmd, cwd=export, env=env_for(tag, lri_root), capture_output=True, text=True)
            out = rec['runs'].setdefault(tag, {})
            out.update(command=' '.join(c if c != sys.executable else 'python' for c in cmd),
                       lri_root=str(lri_root) if lri_root else None, returncode=r.returncode,
                       seconds=round(time.time() - t0, 1), outside_or_write=audit(tag, list(extra_allowed)))
            return r, out

        def run_tests(tag: str, lri_root: Path | None, extra_allowed=()) -> dict:
            junit = tmp / f'junit_{tag}.xml'
            r, out = run(tag, [sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-c', str(ini),
                               '--rootdir', str(export), '--confcutdir', str(export), f'--junitxml={junit}', TESTS],
                         lri_root, extra_allowed)
            out['counts'] = junit_counts(junit) if junit.exists() else dict(passed=0, skipped=0, failed=-1, errors=-1)
            out['failures'] = junit_failures(junit) if junit.exists() else []
            out['tail'] = (r.stdout + r.stderr)[-1500:]
            return out

        # 0. negative control of the audit: a child that reads a vendored file and /etc/hosts must be flagged for
        # /etc/hosts alone
        r, out = run('audit_control', [sys.executable, '-B', '-c', "import sys; open(sys.argv[1]).read(); "
                                       "open('/etc/hosts').read()", f'{VENDOR}/POWER_PROTOCOL.md'], None)
        flagged = out['outside_or_write']
        check('audit negative control: a read of /etc/hosts is flagged and nothing else',
              r.returncode == 0 and len(flagged) == 1 and flagged[0].endswith('/etc/hosts'), flagged)
        # 1. the vendored tests, with and without LRI_ROOT
        for tag, lri in (('tests_fixtures', fx), ('tests_no_lri_root', None)):
            r = run_tests(tag, lri)
            mode = 'fixtures' if lri else 'no_lri_root'
            label = 'LRI_ROOT=fixtures' if lri else 'no LRI_ROOT'
            ok = r['counts'] == want[mode] and r['returncode'] == 0
            if not ok and lri is not None:
                fails = r['failures']
                lone_134 = (len(fails) == 1 and fails[0]['name'] == TEST_134 and fails[0]['kind'] == 'failure'
                            and 'test_order8_assembly.py:134' in fails[0]['text']
                            and r['counts'] == dict(want[mode], passed=want[mode]['passed'] - 1, failed=1))
                if lone_134:
                    disp = dict(test=f'{TESTS}:134 ({TEST_134})', environment=env_rec, asm3_record=None)
                    if a.asm3_record:
                        asm3 = json.loads(a.asm3_record.read_bytes())
                        same = all(asm3.get('environment', {}).get(k) == env_rec.get(k)
                                   for k in ('python', 'numpy', 'cpu_model', 'host', 'slurm_job_id'))
                        disp['asm3_record'] = dict(path=str(a.asm3_record), passed=asm3.get('passed'), same_stack=same)
                        ok = asm3.get('passed') is True and same
                    disp['verdict'] = ('environmental (A-ASM-3 passed on the same stack)' if ok else
                                       'environmental candidate: red until A-ASM-3 passes on the same stack in the '
                                       'same job (--asm3-record)')
                    rec['disposition_134'] = disp
            check(f'vendored tests, {label}: counts equal the HANDOFF ({want[mode]})'
                  + (' with the recorded :134 disposition' if 'disposition_134' in rec and lri else ''), ok,
                  dict(counts=r['counts'], returncode=r['returncode'], failures=[f['name'] for f in r['failures']],
                       disposition_134=rec.get('disposition_134') if lri else None, tail=r['tail'][-600:]))
            check(f'vendored tests, {label}: the audit hook ran, nothing opened outside the export, the temporary '
                  f'directory and the Python installation, no write inside the export', not r['outside_or_write'],
                  r['outside_or_write'][:30])
        # 2. exact_check.py, with and without LRI_ROOT, through the classified keys
        for tag, lri in (('exact_fixtures', fx), ('exact_no_lri_root', None)):
            r, out = run(tag, [sys.executable, '-B', f'{VENDOR}/exact_check.py'], lri)
            try:
                res = json.loads(r.stdout)
            except ValueError:
                res = None
            g = ek.gate(classes, reference, res, lri_root=lri is not None) if isinstance(res, dict) else None
            out.update(stderr_tail=r.stderr[-600:], gate=g)
            if isinstance(res, dict):
                (tmp / f'exact_check_{tag}.json').write_text(json.dumps(res, indent=1) + '\n')
            label = 'LRI_ROOT=fixtures' if lri else 'no LRI_ROOT'
            extra = (not lri and g is not None and sorted(g['absent_lri_root_dependent'])
                     != sorted(classes['lri_root_dependent']['exact']))
            check(f'exact_check.py, {label}: completes; exact keys string-equal to exact_check_results.json, float '
                  f'diagnostics within their bounds, no unclassified key'
                  + ('' if lri else '; exactly the LRI_ROOT-dependent keys absent'),
                  r.returncode == 0 and g is not None and g['passed'] and not extra,
                  dict(returncode=r.returncode, errors=(g or {}).get('errors'), absent=(g or {}).get(
                      'absent_lri_root_dependent'), stderr=r.stderr[-300:]))
            check(f'exact_check.py, {label}: the audit hook ran, nothing opened outside the allowed areas, no write '
                  f'inside the export', not out['outside_or_write'], out['outside_or_write'][:30])
        # 3. prepare_low8.py --d 3, compare mode
        r, out = run('prepare_low8_d3', [sys.executable, '-B', f'{VENDOR}/prepare_low8.py', '--d', '3'], fx)
        lines = [ln for ln in r.stdout.splitlines() if ln.startswith('d=3 ')]
        out.update(stdout=r.stdout[-600:], stderr_tail=r.stderr[-300:])
        check('prepare_low8.py --d 3 (compare mode, LRI_ROOT=fixtures): exit 0, the three d=3 files identical',
              r.returncode == 0 and len(lines) == 3 and all(': identical md5 ' in ln for ln in lines), out)
        check('prepare_low8.py --d 3: the audit hook ran, nothing opened outside the allowed areas, no write inside '
              'the export', not out['outside_or_write'], out['outside_or_write'][:30])
        # 4. the order-7 ulp diagnostic of test :134
        ulps_py = tmp / 'order7_ulps.py'
        ulps_py.write_text(ULPS)
        r, out = run('order7_ulps', [sys.executable, '-B', str(ulps_py), TESTS], fx)
        try:
            out['ulps'] = json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            out['ulps'] = None
        out['stderr_tail'] = r.stderr[-600:]
        rec['order7_reassembly_ulps'] = out['ulps']
        if 'disposition_134' in rec:
            rec['disposition_134']['ulps'] = out['ulps']
        check('order-7 diagnostic (test :134 quantities) ran and is recorded, with its audit clean',
              r.returncode == 0 and out['ulps'] is not None and not out['outside_or_write'],
              dict(returncode=r.returncode, ulps=out['ulps'], audit=out['outside_or_write'][:10],
                   stderr=r.stderr[-300:]))
        # the export after the runs
        after = snapshot(export)
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        check('the export is unchanged by the runs (no __pycache__, .pytest_cache or other new or changed path)',
              not changed, changed[:30])
        ok, detail = vendored_state(after)
        pyc = sorted(k for k in after if k.endswith('.pyc') or '__pycache__' in k)   # anywhere in the export (named)
        check('after the runs: vendor/c8_assembly holds exactly the 13 HANDOFF files and the HANDOFF copy, '
              'byte-identical, and no bytecode', ok and not pyc, dict(detail, bytecode=pyc[:30]))
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
            a.output.write_text(json.dumps(rec, indent=1, default=str) + '\n')
        if not a.keep:
            shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps(dict(environment={k: env_rec[k] for k in ('python', 'numpy', 'cpu_model', 'host')},
                          order7_reassembly_ulps=rec.get('order7_reassembly_ulps')), indent=1))
    print(f'vendored_isolated: {len(results) - len(failed)}/{len(results)} checks passed')
    return 0 if rec['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
