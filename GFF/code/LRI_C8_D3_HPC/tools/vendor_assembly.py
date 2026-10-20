#!/usr/bin/env python3
"""Vendor C63d's order-8 assembly HANDOFF into this package (PLAN.md Stage V and component E.1; A-ASM-1).

Run once per HANDOFF, on the Mac, from any directory (pytest must be importable by the interpreter):
  python3 -B tools/vendor_assembly.py --agent-lri /Users/zheng/Documents/Agent_LRI \\
      --expect-sha256 f5ff6a353371abdc22a296d106e83af03885dfa672a25662fa59f468b9948437 [--evidence FILE]
Steps, each of which stops the vendoring on a failure (nothing is written into the package before step 4):
  1. HANDOFF. LRI_C8_shared/assembly/HANDOFF_assembly.json has the reviewed sha256 (--expect-sha256); every file it
     lists has the sha256, md5 and byte count it records; C62d's H2 review record
     (LRI_C8_shared/inventory/reviews/order8_assembly_<sha12>.json) accepts this HANDOFF and records the step-0 verdict
     gate. The bytes used below are exactly the bytes whose hashes were checked.
  2. Read set (C63d's own measurement). The 13 verified files are copied into the package layout of a temporary
     directory outside Agent_LRI (<tmp>/pkg/vendor/c8_assembly/). There, under an open-audit hook installed through
     `sitecustomize` in every Python process, with LRI_ROOT=<agent-lri>, the run rules of the H2 record
     (PYTHONPYCACHEPREFIX unset, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, -B) and TMPDIR inside the temporary directory:
     the vendored tests (pytest; 30 passed required), exact_check.py (never --write; exit 0) and
     `prepare_low8.py --d 3` (compare mode; exit 0). Every regular file opened under LRI_ROOT is the read set; any
     write under LRI_ROOT, or any open outside LRI_ROOT, the temporary directory and the Python installation, stops
     the vendoring. The read set must equal C62d's measured one (LRI_C8_shared/inventory/reviews/handoff-tests/
     external_read_set.json: the same paths at the same sha256); a different set stops the vendoring until explained.
  3. Fixtures. Every read-set file is copied as a regular file into vendor/c8_assembly_fixtures/<path> from a pinned
     source: this package's reference/ copy at its reference/SHA256SUMS_c8 entry, or a git object (this repository at
     c8-base = LRI_C7_D3_HPC@a6ce987; LRI_C7_D2_HPC@a55958f; C62d's vendoring commit LRI_C8_D2_HPC@1769abc, whose
     fixture tree holds the files C62d's review measured). Each copy must equal the sha256 measured in step 2.
  4. Writes vendor/c8_assembly/ (the 13 files and the HANDOFF copy), vendor/c8_assembly_fixtures/ and
     tools/VENDORED.json (pins, fixture provenance, the review verdict and its step-0 decision with its scope, the
     interface signatures, the consumer-side wording of the H2 record, PLAN F12).
It refuses to run if vendor/c8_assembly, vendor/c8_assembly_fixtures or tools/VENDORED.json exists: a later HANDOFF
revision is a new review, a new pin and an explicit step. `--measure-only --output FILE` runs steps 1-2 only and
writes the measurement record there (it writes nothing into the package).

The vendored code is never imported here: the runs are child processes on a temporary copy, and the signatures of
the names the package uses are read from the source with `ast` (tests/check_vendored.py compares them with
`inspect.signature` of the imported module). PLAN E.1 "One read rule": this tool is the vendoring writer on the
allowlist of tests/check_vendored.py (it copies and hashes vendored files and runs the HANDOFF's own tests)."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR_REL = 'vendor/c8_assembly'
FIXTURES_REL = 'vendor/c8_assembly_fixtures'
VENDOR = ROOT / VENDOR_REL
FIXTURES = ROOT / FIXTURES_REL
OUT = ROOT / 'tools/VENDORED.json'
KEYS_REL = 'tests/fixtures/exact_check_keys.json'
TESTS_REL = f'{VENDOR_REL}/tests/test_order8_assembly.py'
C62D_READ_SET = 'LRI_C8_shared/inventory/reviews/handoff-tests/external_read_set.json'
C8_BASE = 'a6ce987'  # tag c8-base of this repository = LRI_C7_D3_HPC@a6ce987 (PLAN HD1)
C7D2_COMMIT = 'a55958f'  # LRI_C7_D2_HPC, the source_repo_head C62d's read set records
C62D_VENDORING = '1769abc'  # LRI_C8_D2_HPC "Vendor C63d assembly HANDOFF f5ff6a353371"
MAX_FIXTURE_BYTES = 20 * 1024 * 1024
# The names this package uses (PLAN E.2, E.5, A-ASM-2/4) and the module constants its reporting relies on.
USED = ('coefficients', 'jacobians', 'campaign_moments', 'sector_assembly', 'power_null_rows', 'top_slot_gate',
        'loop7_gate', 'affinity_gate', 'ms8_rows', 'ms8_value', 'slots')
CONSTANTS = ('ORDERS', 'COMPLEX_STEP', 'FLAG_PULL', 'ORDER3_ROUNDING')
# PLAN F12 / E.1 "tools/VENDORED.json wording" (from the H2 record's actions_for_C62d and step-5 notes).
INTERFACE_NOTES = {
    'loop7_gate': 'an order-8 gate: it raises ValueError at any other order (order8_assembly.py:272; at order 7 loop 7 '
                  'is the top loop). assemble.combine(order=7) skips it and records "loop7_gate": "not applicable at '
                  'order 7" (PLAN E.2).',
    'jacobians': 'takes float or complex means only: a complex-step derivative with no exact mode. B2 must be real '
                 'float or the strings of two_loop.json (an exact-mode or complex B2 raises ValueError); rational '
                 'means are read as complex floats (order8_assembly.py:136-157).',
    'power_null_rows': 'compared on its numeric fields (delta, se, pull, flag), not on its output layout, which differs '
                       "from C7(2)'s power_null_checks (H2 record step 5). It has no length or finiteness guards "
                       '(:391-412: SE = 0 or NaN gives an unflagged row, a short vector an IndexError) and no PP8 '
                       'marker: assemble.py guards its inputs and adds the marker (PLAN E.2).',
    'top_slot_gate': 'skips loops absent from J (`if L not in J: continue`, :256): assemble.py asserts one row for '
                     'every L = 3..order (PLAN E.2).',
    'affinity_gate': 'perturbs only the loops 5..order present in `means` (:301; DECISIONS B3): assemble.py asserts '
                     'loops == [5, ..., order] (PLAN E.2).',
}
RUN_RULES = [
    'PYTHONPYCACHEPREFIX unset, in the child environment too (H2 record checklist.step_1_runs.env_notes)',
    'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, pytest -p no:cacheprovider, python -B (env_notes, actions_for_C62d)',
    'exact_check.py is never given --write (actions_for_C62d)',
    'after a run vendor/c8_assembly/ holds exactly the 13 listed files and the HANDOFF copy, byte-identical, and no '
    'bytecode (actions_for_C62d)',
    'test_order7_production_reassembly (tests/test_order8_assembly.py:134, <= 8 ulp) depends on numpy and CPU: a lone '
    'failure there is environmental only if A-ASM-3 passes on the same stack in the same job, and it is recorded '
    '(ulp count, numpy, Python, CPU); otherwise it is red (PLAN A-ASM-1)',
]

AUDIT_SITECUSTOMIZE = r'''
# open-audit hook of LRI_C8_D3_HPC (tools/vendor_assembly.py, tests/vendored_isolated.py): every Python process of a
# run appends what it opens or lists to $C8_AUDIT_LOG.<pid>, one tab-separated line per event:
#   event, mode, flags, absolute path, file:function of the Python caller
# A relative name is resolved against the working directory; the caller tells a dir_fd-relative open of
# shutil.rmtree's fd walk (which the checks skip) from a cwd-relative one.
import os, sys
_log = os.environ.get("C8_AUDIT_LOG")
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
            if isinstance(a, int):  # a descriptor of a file or directory opened before (logged then)
                return
            if ev in ("subprocess.Popen", "os.exec", "os.posix_spawn"):
                _fh.write(f"{ev}\t\t\t{args[1]!r}\t\n")
                return
            if isinstance(a, bytes):
                a = os.fsdecode(a)
            a = "." if a is None else os.fspath(a)
            if isinstance(a, bytes):
                a = os.fsdecode(a)
            mode = args[1] if ev == "open" and len(args) > 1 else ""
            flags = args[2] if ev == "open" and len(args) > 2 else ""
            try:
                f = sys._getframe(1)
                caller = f"{f.f_code.co_filename}:{f.f_code.co_name}"
            except Exception:
                caller = ""
            rel = "" if os.path.isabs(a) else "rel"
            _fh.write(f"{ev}{(':' + rel) if rel else ''}\t{mode}\t{flags}\t{os.path.abspath(a)}\t{caller}\n")
        except Exception as e:
            _fh.write(f"ERR\t{ev}\t\t{e!r}\t\n")
        finally:
            _busy[0] = False
    sys.addaudithook(_hook)
'''
WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def python_dirs() -> list[str]:
    """The Python installation of this interpreter (prefixes, stdlib, site directories), resolved."""
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


def inside(path: str, roots) -> bool:
    rp = os.path.realpath(path)
    return any(rp == r or rp.startswith(r.rstrip('/') + '/') for r in roots)


def parse_audit_line(line: str) -> dict | None:
    """One line of the hook's log, or None for a line that is not a path event."""
    parts = line.split('\t')
    if parts[0] == 'ERR':
        return dict(event='ERR', text=line)
    if len(parts) != 5 or parts[0] in ('subprocess.Popen', 'os.exec', 'os.posix_spawn'):
        return None
    ev, mode, flags, path, caller = parts
    relative = ev.endswith(':rel')
    ev = ev.split(':')[0]
    try:
        fl = int(flags) if flags not in ('', 'None') else 0
    except ValueError:
        fl = 0
    write = ev == 'open' and ((mode not in ('', 'None') and any(c in mode for c in 'wax+')) or bool(fl & WRITE_FLAGS))
    fd_walk = relative and '/shutil.py:' in caller and '_rmtree' in caller
    return dict(event=ev, mode=mode, flags=fl, path=path, caller=caller, relative=relative, write=write, fd_walk=fd_walk)


def audit_events(logs) -> list[dict]:
    out = []
    for log in logs:
        for line in Path(log).read_text().splitlines():
            e = parse_audit_line(line)
            if e is not None:
                out.append(e)
    return out


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


def run_env(tmp: Path, site: Path, tag: str, lri_root: Path | None) -> dict:
    """The child environment of every run (the H2 run rules)."""
    env = {k: v for k, v in os.environ.items()
           if k not in ('PYTHONPYCACHEPREFIX', 'LRI_ROOT', 'PYTHONPATH', 'PYTHONSTARTUP', 'PYTHONHOME', 'PYTHONSAFEPATH',
                        'PYTHONUSERBASE', 'PYTEST_ADDOPTS', 'PYTEST_PLUGINS')}
    (tmp / f'tmp_{tag}').mkdir(exist_ok=True)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONPATH=str(site),
               C8_AUDIT_LOG=str(tmp / f'audit_{tag}'), TMPDIR=str(tmp / f'tmp_{tag}'), OPENBLAS_NUM_THREADS='1',
               OMP_NUM_THREADS='1')
    if lri_root is not None:
        env['LRI_ROOT'] = str(lri_root)
    return env


def pytest_cmd(ini: Path, pkg: Path, junit: Path) -> list[str]:
    return [sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-c', str(ini), '--rootdir', str(pkg),
            '--confcutdir', str(pkg), f'--junitxml={junit}', TESTS_REL]


def load_handoff(agent: Path, expect: str) -> tuple[bytes, dict, dict, dict, bytes, Path]:
    """Step 1: the HANDOFF, its files (verified bytes) and an accepting review record."""
    shared = agent / 'LRI_C8_shared'
    hbytes = (shared / 'assembly/HANDOFF_assembly.json').read_bytes()
    hsha = sha256(hbytes)
    if hsha != expect:
        raise SystemExit(f'HANDOFF_assembly.json has sha256 {hsha}, not the reviewed {expect}: stop')
    handoff = json.loads(hbytes)
    files = {}
    for f in handoff['files']:
        data = (shared / 'assembly' / f['path']).read_bytes()
        if (sha256(data), md5(data), len(data)) != (f['sha256'], f['md5'], f['bytes']):
            raise SystemExit(f'assembly/{f["path"]} differs from the HANDOFF record: the folder changed after the HANDOFF')
        files[f['path']] = data
    if len(files) != 13:
        raise SystemExit(f'the HANDOFF lists {len(files)} files, not 13 (PLAN F11): stop')
    rpath = shared / f'inventory/reviews/order8_assembly_{hsha[:12]}.json'
    rbytes = rpath.read_bytes()
    review = json.loads(rbytes)
    step0 = review.get('checklist', {}).get('step_0_handoff', {})
    if (review.get('handoff', {}).get('sha256') != hsha or review.get('overall_verdict') not in ('ACCEPT', 'ACCEPT_WITH_MINOR')
            or not step0.get('verdict_gate') or review.get('required_changes_for_C63d')):
        raise SystemExit(f'{rpath}: no accepting review of this HANDOFF with a step-0 verdict gate and no required change')
    return hbytes, handoff, files, review, rbytes, rpath


def measure(agent: Path, files: dict, keep: bool = False) -> dict:
    """Step 2: run the HANDOFF's tests, exact_check.py and prepare_low8.py --d 3 on a temporary copy with
    LRI_ROOT=agent under the open-audit hook; return the measurement record with the read set."""
    agent_real = os.path.realpath(agent)
    tmp = Path(tempfile.mkdtemp(prefix='c8d3_vendor_measure_')).resolve()
    if inside(str(tmp), [agent_real]):
        raise SystemExit(f'the temporary directory {tmp} lies inside {agent_real}: set TMPDIR elsewhere')
    try:
        pkg = tmp / 'pkg'
        for rel, data in files.items():
            p = pkg / VENDOR_REL / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        site = tmp / 'site'
        site.mkdir()
        (site / 'sitecustomize.py').write_text(AUDIT_SITECUSTOMIZE)
        ini = tmp / 'pytest.ini'
        ini.write_text('[pytest]\n')
        runs = {}
        t0 = time.time()
        junit = tmp / 'junit.xml'
        r = subprocess.run(pytest_cmd(ini, pkg, junit), cwd=pkg, env=run_env(tmp, site, 'tests', agent),
                           capture_output=True, text=True)
        counts = junit_counts(junit) if junit.exists() else None
        runs['tests'] = dict(returncode=r.returncode, counts=counts, seconds=round(time.time() - t0, 1),
                             tail=(r.stdout + r.stderr)[-1200:])
        if r.returncode != 0 or counts != dict(passed=30, skipped=0, failed=0, errors=0):
            raise SystemExit(f'vendored tests with LRI_ROOT={agent}: {counts}, exit {r.returncode} (30 passed required)'
                             f'\n{runs["tests"]["tail"]}')
        for tag, cmd in (('exact_check', [sys.executable, '-B', f'{VENDOR_REL}/exact_check.py']),
                         ('prepare_low8_d3', [sys.executable, '-B', f'{VENDOR_REL}/prepare_low8.py', '--d', '3'])):
            t0 = time.time()
            r = subprocess.run(cmd, cwd=pkg, env=run_env(tmp, site, tag, agent), capture_output=True, text=True)
            runs[tag] = dict(command=' '.join(cmd[1:]), returncode=r.returncode, seconds=round(time.time() - t0, 1),
                             stderr_tail=r.stderr[-600:], stdout_tail=r.stdout[-600:] if tag != 'exact_check' else '')
            if r.returncode != 0:
                raise SystemExit(f'{tag} with LRI_ROOT={agent} exited {r.returncode}:\n{r.stderr[-1500:]}')
        events = audit_events(sorted(tmp.glob('audit_*.*')))
        if not any(e['event'] == 'open' and inside(e['path'], [str(pkg / VENDOR_REL)]) for e in events):
            raise SystemExit('the open-audit hook recorded no open of a vendored file: the measurement would be vacuous')
        pyroots = python_dirs()
        allowed = [str(tmp), agent_real, '/dev/null'] + pyroots
        reads, walks, outside, writes, errors = {}, set(), set(), set(), []
        for e in events:
            if e['event'] == 'ERR':
                errors.append(e['text'])
                continue
            if e['fd_walk']:
                continue
            p = e['path']
            if not inside(p, allowed):
                outside.add(f'{e["event"]} {p}')
                continue
            if inside(p, [agent_real]):
                rel = os.path.relpath(os.path.realpath(p), agent_real)
                if e['write']:
                    writes.add(rel)
                elif e['event'] == 'open' and os.path.isfile(p):
                    reads.setdefault(rel, set()).add(e['caller'].rsplit('/', 1)[-1])
                elif e['event'] in ('os.listdir', 'os.scandir'):
                    walks.add(rel)
        if errors or outside or writes:
            raise SystemExit(f'measurement audit: hook errors {errors[:5]}, opens outside the allowed areas '
                             f'{sorted(outside)[:20]}, writes under LRI_ROOT {sorted(writes)[:20]}: stop')
        read_set = []
        for rel in sorted(reads):
            data = (Path(agent_real) / rel).read_bytes()
            read_set.append(dict(path=rel, bytes=len(data), sha256=sha256(data), md5=md5(data),
                                 opened_by=sorted(reads[rel])))
        tops = sorted({'/'.join(w.split('/')[:1]) for w in walks})
        return dict(schema='c8-d3-vendored-readset-1', date=time.strftime('%Y-%m-%d'),
                    measured_by='tools/vendor_assembly.py: sys.addaudithook open/listdir/scandir log in every Python '
                                'process (sitecustomize), on a temporary copy of the 13 verified HANDOFF files in the '
                                'package layout, LRI_ROOT=<agent-lri>',
                    lri_root=agent_real, runs=runs, audited_events=len(events),
                    files=len(read_set), total_bytes=sum(e['bytes'] for e in read_set),
                    directory_listings=dict(count=len(walks), top_level=tops,
                                            note='directory listings only (rglob of the delivered C7 packages by '
                                                 'test_no_bytecode_written_into_delivered_packages; iterdir of the '
                                                 'production groups); no file read'),
                    environment=environment(), read_set=read_set)
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)


def environment() -> dict:
    """Python, numpy, CPU and host of this interpreter (the children use the same one)."""
    def version(mod):
        try:
            return __import__(mod).__version__
        except Exception:  # pragma: no cover - recorded
            return None
    cpu = None
    try:
        if sys.platform == 'darwin':
            cpu = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True, text=True).stdout.strip()
        else:
            for line in Path('/proc/cpuinfo').read_text().splitlines():
                if line.startswith('model name'):
                    cpu = line.split(':', 1)[1].strip()
                    break
    except OSError:
        pass
    return dict(python=sys.version.split()[0], implementation=platform.python_implementation(), executable=sys.executable,
                numpy=version('numpy'), mpmath=version('mpmath'), sympy=version('sympy'), pytest=version('pytest'),
                platform=platform.platform(), machine=platform.machine(), cpu_model=cpu or platform.processor(),
                host=platform.node(), slurm_job_id=os.environ.get('SLURM_JOB_ID'))


def compare_with_c62d(agent: Path, m: dict) -> dict:
    """PLAN E.1: the measured read set must equal C62d's (paths and sha256); a difference stops the vendoring."""
    rs_path = agent / C62D_READ_SET
    rs_bytes = rs_path.read_bytes()
    theirs = {e['path']: e['sha256'] for e in json.loads(rs_bytes)['read_set']}
    ours = {e['path']: e['sha256'] for e in m['read_set']}
    only_ours, only_theirs = sorted(set(ours) - set(theirs)), sorted(set(theirs) - set(ours))
    differ = sorted(p for p in set(ours) & set(theirs) if ours[p] != theirs[p])
    if only_ours or only_theirs or differ:
        raise SystemExit('the measured read set differs from C62d\'s (stop until explained): '
                         + json.dumps(dict(only_c63d=only_ours, only_c62d=only_theirs, sha256_differs=differ), indent=1))
    total = json.loads(rs_bytes).get('total_bytes')
    return dict(path=C62D_READ_SET, sha256=sha256(rs_bytes), files=len(theirs), total_bytes=total,
                comparison='identical: the same paths at the same sha256')


def git_show(repo: Path, commit: str, path: str) -> tuple[str, bytes]:
    full = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', commit + '^{commit}'], capture_output=True,
                          text=True, check=True).stdout.strip()
    data = subprocess.run(['git', '-C', str(repo), 'show', f'{full}:{path}'], capture_output=True, check=True).stdout
    return full, data


def reference_entries() -> dict[str, tuple[str, str]]:
    """reference/SHA256SUMS_c8: package path -> (sha256, source relative to Agent_LRI)."""
    out = {}
    for line in (ROOT / 'reference/SHA256SUMS_c8').read_text().splitlines():
        m = re.match(r'^([0-9a-f]{64})  (\S+)  <=  (\S+)$', line)
        if m:
            out[m.group(2)] = (m.group(1), m.group(3))
    return out


def fixture_source(agent: Path, rel: str, refs: dict) -> tuple[bytes, dict]:
    """Step 3: the bytes of one read-set file from its pinned source, and the pin."""
    top, _, sub = rel.partition('/')
    if top == 'LRI_C7_D3_HPC':
        full, data = git_show(ROOT, C8_BASE, sub)
        return data, dict(kind='git', repository='.', commit=full, path=sub,
                          note='this repository at tag c8-base = LRI_C7_D3_HPC@a6ce987 (PLAN HD1)')
    if rel.startswith('LRI_C7_D3_HPC_production/results_run1-20260930-m4096/'):
        pkg_path = 'reference/c7d3_run1_results/' + rel[len('LRI_C7_D3_HPC_production/results_run1-20260930-m4096/'):]
        h, source = refs.get(pkg_path, (None, None))
        data = (ROOT / pkg_path).read_bytes()
        if h is None or source != rel or sha256(data) != h:
            raise SystemExit(f'{pkg_path}: not at its reference/SHA256SUMS_c8 entry for {rel}')
        return data, dict(kind='reference_checksum', source=pkg_path, list='reference/SHA256SUMS_c8', sha256=h,
                          entry_source=source)
    if top == 'LRI_C7_D2_HPC':
        full, data = git_show(agent / 'LRI_C7_D2_HPC', C7D2_COMMIT, sub)
        return data, dict(kind='git', repository='LRI_C7_D2_HPC', commit=full, path=sub)
    full, data = git_show(agent / 'LRI_C8_D2_HPC', C62D_VENDORING, f'{FIXTURES_REL}/{rel}')
    return data, dict(kind='git', repository='LRI_C8_D2_HPC', commit=full, path=f'{FIXTURES_REL}/{rel}',
                      note="C62d's vendoring commit; the bytes C62d's H2 review measured (sha256 recorded first in "
                           f'{C62D_READ_SET}); the live file is {rel}')


def ast_interface(src: str) -> tuple[dict, dict]:
    """Signatures of USED (parameter name, kind and default as source text, which is repr() of the default for the
    literal defaults used) and the values of CONSTANTS, read from the source without importing it."""
    tree = ast.parse(src)
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    sigs = {}
    for name in USED:
        if name not in funcs:
            raise SystemExit(f'the vendored order8_assembly.py defines no {name}: PLAN E.2 must adapt')
        a = funcs[name].args
        pos = a.posonlyargs + a.args
        defaults = [None] * (len(pos) - len(a.defaults)) + list(a.defaults)
        rec = []
        for i, p in enumerate(pos):
            rec.append(dict(name=p.arg, kind='POSITIONAL_ONLY' if i < len(a.posonlyargs) else 'POSITIONAL_OR_KEYWORD',
                            default=None if defaults[i] is None else ast.unparse(defaults[i])))
        if a.vararg:
            rec.append(dict(name=a.vararg.arg, kind='VAR_POSITIONAL', default=None))
        for p, d in zip(a.kwonlyargs, a.kw_defaults):
            rec.append(dict(name=p.arg, kind='KEYWORD_ONLY', default=None if d is None else ast.unparse(d)))
        if a.kwarg:
            rec.append(dict(name=a.kwarg.arg, kind='VAR_KEYWORD', default=None))
        sigs[name] = rec
    consts = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                and n.targets[0].id in CONSTANTS:
            consts[n.targets[0].id] = ast.unparse(n.value)
    if set(consts) != set(CONSTANTS):
        raise SystemExit(f'the vendored order8_assembly.py lacks the constants {sorted(set(CONSTANTS) - set(consts))}')
    return sigs, consts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--agent-lri', type=Path, required=True, help='the directory holding LRI_C8_shared and the sources')
    ap.add_argument('--expect-sha256', required=True, help='sha256 of the reviewed HANDOFF_assembly.json')
    ap.add_argument('--measure-only', action='store_true', help='steps 1-2 only; writes --output, nothing else')
    ap.add_argument('--output', type=Path, help='the measurement record (with --measure-only)')
    ap.add_argument('--evidence', type=Path, help='also write the measurement record here (outside vendor/)')
    ap.add_argument('--keep', action='store_true', help='keep the temporary measurement directory')
    a = ap.parse_args()
    agent = a.agent_lri.resolve()
    if not a.measure_only:
        for p in (VENDOR, FIXTURES, OUT):
            if p.exists():
                raise SystemExit(f'{p} exists: a HANDOFF revision needs a new review, a new pin and an explicit step')
    elif not a.output:
        raise SystemExit('--measure-only needs --output')
    hbytes, handoff, files, review, rbytes, rpath = load_handoff(agent, a.expect_sha256)
    hsha = sha256(hbytes)
    m = measure(agent, files, keep=a.keep)
    m['c62d_read_set'] = compare_with_c62d(agent, m)
    m['handoff_sha256'] = hsha
    for path in ([a.output] if a.measure_only else []) + ([a.evidence] if a.evidence else []):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(m, indent=1) + '\n')
    if a.measure_only:
        print(json.dumps(dict(read_set_files=m['files'], bytes=m['total_bytes'], c62d=m['c62d_read_set']['comparison']),
                         indent=1))
        return 0
    if m['total_bytes'] > MAX_FIXTURE_BYTES:
        raise SystemExit(f'the read set is {m["total_bytes"]} bytes (> 20 MB): stop for a host decision')
    # step 3: fixtures from pinned sources
    refs = reference_entries()
    staged, fixtures = {}, []
    for e in m['read_set']:
        data, pin = fixture_source(agent, e['path'], refs)
        if sha256(data) != e['sha256'] or len(data) != e['bytes']:
            raise SystemExit(f'{e["path"]}: the pinned source {pin} differs from the measured file')
        staged[FIXTURES / e['path']] = data
        fixtures.append(dict(path=e['path'], sha256=e['sha256'], md5=e['md5'], bytes=e['bytes'], source_pin=pin,
                             measured_live_sha256=e['sha256'], opened_by=e['opened_by']))
    # step 4: the vendored set, the HANDOFF copy, VENDORED.json
    vfiles = []
    for f in handoff['files']:
        staged[VENDOR / f['path']] = files[f['path']]
        vfiles.append(dict(path=f['path'], vendored_path=f'{VENDOR_REL}/{f["path"]}',
                           source=f'LRI_C8_shared/assembly/{f["path"]}', sha256=f['sha256'], md5=f['md5'],
                           bytes=f['bytes']))
    staged[VENDOR / 'HANDOFF_assembly.json'] = hbytes
    sigs, consts = ast_interface(files['order8_assembly.py'].decode())
    step0 = review['checklist']['step_0_handoff']
    rec = dict(
        schema='c8-d3-vendored-1',
        rule=('PLAN E.1 "One read rule": vendored files are hashed by prepare_inputs.verify() (hence plan), verify_base '
              '(merge, assemble) and verify_delivery; imported only by assemble.py, combine.py, verify_result.py, '
              'report.py, pilot_report.py, design.py/design_fallback.py and the tests; `make inputs` copies inputs_d3/ '
              'after the hash check and executes prepare_low8.py --d 3 in compare mode (writing nothing into inputs/, '
              'HD4); run never opens vendor/ (A-ORC-13). tools/vendor_assembly.py is the vendoring writer. The '
              'allowlist of tests/check_vendored.py is this list.'),
        handoff=dict(path=f'{VENDOR_REL}/HANDOFF_assembly.json', source='LRI_C8_shared/assembly/HANDOFF_assembly.json',
                     sha256=hsha, md5=md5(hbytes), bytes=len(hbytes), date=handoff.get('date'),
                     owner=handoff.get('owner'), checker=handoff.get('checker'), handoff=handoff.get('handoff'),
                     rule=handoff.get('rule'), tests_at_handoff=handoff.get('checks_at_handoff', {}).get('tests'),
                     platform_at_handoff=handoff.get('checks_at_handoff', {}).get('platform')),
        files=vfiles,
        review=dict(record=rpath.relative_to(agent).as_posix(), record_sha256_at_vendoring=sha256(rbytes),
                    reviewer=review.get('reviewer'), date=review.get('date'),
                    overall_verdict=review.get('overall_verdict'),
                    required_changes_for_C63d=review.get('required_changes_for_C63d'),
                    verdict_gate=step0['verdict_gate'], verdict_gate_decision=step0.get('host_decision'),
                    verdict_gate_scope='this HANDOFF version only (checklist.step_0_handoff.host_decision of the '
                                       'review record: "It does not extend to any later HANDOFF revision.")'),
        power_protocol=dict(path=f'{VENDOR_REL}/POWER_PROTOCOL.md',
                            sha256=next(f['sha256'] for f in vfiles if f['path'] == 'POWER_PROTOCOL.md'),
                            implemented_by='the vendored power_null_rows and tools/assemble.py reporting (PLAN HD10, '
                                           'E.2; PP1-PP10 with one A-ASM-5 test each)'),
        interface=dict(module=f'{VENDOR_REL}/order8_assembly.py', signatures=sigs, constants=consts,
                       signature_method='ast of the vendored source (no import); tests/check_vendored.py compares it '
                                        'with inspect.signature of the imported module (names, kinds, default reprs)',
                       notes=INTERFACE_NOTES),
        run_rules=RUN_RULES,
        fixtures=dict(root=FIXTURES_REL, lri_root=f'LRI_ROOT=<package>/{FIXTURES_REL}',
                      measurement={k: m[k] for k in ('schema', 'date', 'measured_by', 'audited_events', 'files',
                                                     'total_bytes', 'directory_listings', 'environment')}
                      | dict(runs={k: {x: y for x, y in v.items() if x in ('returncode', 'counts', 'seconds', 'command')}
                                   for k, v in m['runs'].items()}),
                      c62d_read_set=m['c62d_read_set'], count=len(fixtures), bytes=sum(f['bytes'] for f in fixtures),
                      files=fixtures),
        exact_check_keys=KEYS_REL)
    total = 0
    for p, data in staged.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'xb') as fh:
            fh.write(data)
        total += len(data)
    OUT.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(handoff_sha256=hsha, vendored=len(vfiles) + 1, fixtures=len(fixtures),
                          fixture_bytes=rec['fixtures']['bytes'], read_set=m['c62d_read_set']['comparison'],
                          output=str(OUT.relative_to(ROOT))), indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
