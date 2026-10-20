#!/usr/bin/env python3
"""A-ASM-1: the vendored order-8 assembly against its HANDOFF, its pins and the vendor/ rule (PLAN component F; R15).

--standalone, A-ASM-1(a) (G-H2 in every case; the cluster parts in J-VAL-1):
  * vendor/c8_assembly/HANDOFF_assembly.json is the HANDOFF byte copy; its sha256 equals tools/VENDORED.json's, the
    review recorded in VENDORED.json accepted this HANDOFF and records the step-0 verdict-gate decision
    (accepted_documentation_only_minor_fixes: the HANDOFF has no structured per-verifier verdicts, H2 review);
  * the complete deliverable set (R01): vendor/c8_assembly/ holds exactly the files the HANDOFF lists plus the
    HANDOFF copy, none missing and none extra, each at the sha256, md5 and byte count the HANDOFF records, and
    VENDORED.json agrees file by file;
  * the fixtures (R16): every file of vendor/c8_assembly_fixtures/ is a regular file at its VENDORED.json pin, the
    set equals VENDORED.json's list, and a source in reference/ is at its checksum-list entry; no symlink is tracked
    anywhere in the package (`git ls-files -s` mode 120000, or a walk of an export);
  * the review record LRI_C8_shared/inventory/reviews/order8_assembly_<sha12>.json, when reachable (the Mac; give
    --no-review-record on a cluster export), names this HANDOFF, accepts it, records the same verdict gate and holds
    a result for every checklist step 0-10;
  * the interface: the vendored order8_assembly.py exports every name the package uses, with the signatures
    recorded in VENDORED.json (no stand-in module exists: the HANDOFF arrived before Stage 3);
  * the vendor/ rule: an open/import spy shows that tools/prepare_inputs.py (a build into a scratch directory, the
    L3..L7 part of regenerate(), and verify()) opens vendored files only through the hash helper (common.digest) and
    imports nothing from vendor/; in a scratch copy of the package (tests/pkgcopy.py, the fake native worker), a
    test-only `production.py plan` on tests/fixtures/inputs_mini opens vendored files only through the hash helper (the
    inputs manifest's vendored pins, A-IN-4) and imports nothing from vendor/, and `production.py run --index 0` of that
    plan opens nothing under vendor/ at all (PLAN "One rule governs reads of vendor/", A-ORC-13).
Default (no --standalone), A-ASM-1(a) and A-ASM-1(b) (G-H2 after Stage 2a, otherwise G2a):
  * inputs/manifest.json records vendored_assembly_handoff_sha256 and every vendored file's sha256, equal to
    VENDORED.json and the HANDOFF; a manifest without the pins fails this mode, never skips it;
  * prepare_inputs.verify() hashes each vendored file against the manifest, and a one-byte change to a vendored file
    (in a scratch export) makes it fail.
Both modes, Stage-6 finding S6-B-04: tools/vendor_assembly.py in sandboxes (a copy of the tool as package root, a
miniature LRI_C8_shared with an accepting review, a stub order8_assembly.py and a read set of one reference-copy and
one recorded-first fixture):
  * the clean sandbox vendors with both reviewed digests (--expect-sha256, --expect-read-set-sha256);
  * refused before any write, with the package's files byte for byte unchanged, no vendor/ tree, no VENDORED.json and
    nothing written outside: a read-set path '../../tools/common.py' carrying a valid reference copy of a
    common.py (the reviewer's example), a HANDOFF file path '../../tools/common.py', an absolute path, a '.'
    component, a repeated fixture path, two fixture paths equal ignoring case, a fixture path that is the directory
    of another, a HANDOFF file named like the HANDOFF copy, a c8d2_reference_copy outside reference/, a read set not at the reviewed digest, a vendor/ that is a
    symlink to a directory outside the package, and (fix-round-1 residual: the interface is checked from the staged
    bytes before the first write) an order8_assembly.py that lacks a used name or fails to execute;
  * Stage-6 round-2 finding S6R2-B-02, refused the same way: a tools/VENDORED.json that is a dangling symlink to the
    staged deliverable ../vendor/c8_assembly/order8_assembly.py (the reviewer's example: the metadata used to
    overwrite the vendored module) or to a path outside the package (an external write), and a vendor/c8_assembly
    that is a dangling symlink;
  * a write that fails part-way (the VENDORED.json write, or a fixture write, made to raise OSError) leaves the
    package as it was: no vendor/ tree, no VENDORED.json, the error reported.
Usage: python3 -B tests/check_vendored.py [--standalone] [--no-review-record] [--output FILE]"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'vendor/c8_assembly'
FIXTURES = ROOT / 'vendor/c8_assembly_fixtures'
VENDORED = ROOT / 'tools/VENDORED.json'
GATE_DECISIONS = {'accepted_documentation_only_minor_fixes', 'all_verifier_verdicts_pass'}

SPY = r'''
import json, os, sys, traceback
from pathlib import Path
root, vendor, out, mode, dest = sys.argv[1:6]
sys.path.insert(0, os.path.join(root, 'tools'))
events = []
def hook(ev, args):
    if ev != 'open' or not args or isinstance(args[0], int):
        return
    p = os.path.realpath(os.fsdecode(args[0]))
    if p == vendor or p.startswith(vendor + os.sep):
        fn = [(f.f_code.co_filename, f.f_code.co_name) for f in _frames()]
        events.append(dict(path=p, mode=str(args[1]) if len(args) > 1 else '', stack=fn))
def _frames():
    f = sys._getframe(2)
    while f is not None:
        yield f
        f = f.f_back
sys.addaudithook(hook)
import prepare_inputs as pi
err = None
try:
    if mode == 'build':
        pi.regenerate(Path(dest), None, None, None, 1, l8=False)
    else:
        pi.verify(allow_no_l8=True)
except Exception as e:
    err = f'{type(e).__name__}: {e}'
mods = sorted(n for n, m in list(sys.modules.items())
              if getattr(m, '__file__', None) and os.path.realpath(m.__file__).startswith(vendor + os.sep))
json.dump(dict(events=events, vendored_modules=mods, error=err), open(out, 'w'))
'''


SPY_PROD = r'''
import json, os, sys
root, vendor, out, mode, camp, scratch = sys.argv[1:7]
sys.path.insert(0, os.path.join(root, 'tools'))
events, relative = [], []
def _frames():
    f = sys._getframe(2)
    while f is not None:
        yield f
        f = f.f_back
def hook(ev, args):
    if ev != 'open' or not args or isinstance(args[0], int):
        return
    raw = os.fsdecode(args[0])
    stack = [(f.f_code.co_filename, f.f_code.co_name) for f in _frames()]
    if not os.path.isabs(raw):  # a dir_fd-relative name: only shutil.rmtree's fd walk of the job-private runtime
        relative.append(dict(name=raw, via=[fn for file, fn in stack if file.endswith('shutil.py')][:1]))
        return
    p = os.path.realpath(raw)
    if p == vendor or p.startswith(vendor + os.sep):
        events.append(dict(path=p, mode=str(args[1]) if len(args) > 1 else '', stack=stack))
sys.addaudithook(hook)
import production
argv = {'plan': ['plan', camp, '--seed', '771100231', '--threads', '1', '--pilot', '--points', '8', '--replicates', '2',
                 '--test-graphs', '1', '--bootstrap-chunk', '4', '--shards', '1'],
        'run': ['run', camp, '--index', '0', '--threads', '1', '--scratch', scratch]}[mode]
sys.argv = ['production.py', *argv]
err = None
try:
    rc = production.main()
    if rc:
        err = f'exit {rc}'
except SystemExit as e:
    if e.code:
        err = f'exit {e.code}'
except Exception as e:
    err = f'{type(e).__name__}: {e}'
mods = sorted(n for n, m in list(sys.modules.items())
              if getattr(m, '__file__', None) and os.path.realpath(m.__file__).startswith(vendor + os.sep))
json.dump(dict(events=events, relative=relative, vendored_modules=mods, error=err), open(out, 'w'))
'''


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def md5_file(p: Path) -> str:
    h = hashlib.md5()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def regular_files(d: Path) -> dict[str, Path]:
    out = {}
    for p in sorted(d.rglob('*')):
        if p.is_symlink() or p.is_file():
            out[p.relative_to(d).as_posix()] = p
    return out


def signature_record(fn) -> list:
    return [dict(name=p.name, kind=p.kind.name, default=None if p.default is inspect.Parameter.empty else repr(p.default))
            for p in inspect.signature(fn).parameters.values()]


STUB_ASSEMBLY = ''.join(f'def {n}(*args, **kwargs):\n    return None\n\n\n' for n in (
    'coefficients', 'jacobians', 'campaign_moments', 'sector_assembly', 'power_null_rows', 'top_slot_gate', 'loop7_gate',
    'affinity_gate', 'ms8_rows', 'ms8_value', 'slots'))


def vendor_assembly_sandbox(td: Path, check) -> None:
    """S6-B-04: tools/vendor_assembly.py refuses unsafe destinations and an unreviewed read set before any write."""
    sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
    md5 = lambda b: hashlib.md5(b).hexdigest()  # noqa: E731
    common_pkg = b'# the package tools/common.py: must never be overwritten\n'
    common_c7 = b'# a pinned C7 tools/common.py (a reference copy)\n'
    data_txt = b'a recorded-first fixture\n'
    deliver = {'order8_assembly.py': STUB_ASSEMBLY.encode(), 'POWER_PROTOCOL.md': b'# power protocol\n'}

    def sandbox(name: str, files=None, read_set=None, vendor_link: bool = False, tamper_read_set: bool = False,
                assembly: bytes | None = None, vendored_link: str | None = None, assembly_link: bool = False):
        deliver_ = dict(deliver, **({'order8_assembly.py': assembly} if assembly is not None else {}))
        base = td / name
        pkg, agent, outside = base / 'pkg', base / 'agent', base / 'outside'
        (pkg / 'tools').mkdir(parents=True)
        outside.mkdir()
        shutil.copyfile(ROOT / 'tools/vendor_assembly.py', pkg / 'tools/vendor_assembly.py')
        (pkg / 'tools/common.py').write_bytes(common_pkg)
        (pkg / 'reference/c7').mkdir(parents=True)
        (pkg / 'reference/c7/common.py').write_bytes(common_c7)
        (pkg / 'reference/SHA256SUMS').write_text(f'{sha(common_c7)}  c7/common.py\n')
        (pkg / 'reference/SHA256SUMS_c8').write_text('')
        if vendor_link:
            (pkg / 'vendor').symlink_to(outside, target_is_directory=True)
        if vendored_link == 'deliverable':  # S6R2-B-02, the reviewer's example: dangling until the vendoring
            (pkg / 'tools/VENDORED.json').symlink_to('../vendor/c8_assembly/order8_assembly.py')
        elif vendored_link == 'external':
            (pkg / 'tools/VENDORED.json').symlink_to(outside / 'metadata.json')
        if assembly_link:  # a dangling vendor/c8_assembly
            (pkg / 'vendor').mkdir()
            (pkg / 'vendor/c8_assembly').symlink_to(outside / 'c8_assembly', target_is_directory=True)
        shared = agent / 'LRI_C8_shared'
        (shared / 'assembly').mkdir(parents=True)
        for rel, data in deliver_.items():
            (shared / 'assembly' / rel).write_bytes(data)
        hfiles = files if files is not None else [dict(path=k, sha256=sha(v), md5=md5(v), bytes=len(v))
                                                  for k, v in deliver_.items()]
        hbytes = json.dumps(dict(handoff='H2', owner='C63d', date='2026-10-03', files=hfiles,
                                 checks_at_handoff=dict(tests=1))).encode()
        (shared / 'assembly/HANDOFF_assembly.json').write_bytes(hbytes)
        hsha = sha(hbytes)
        reviews = shared / 'inventory/reviews'
        (reviews / 'handoff-tests').mkdir(parents=True)
        (reviews / f'order8_assembly_{hsha[:12]}.json').write_text(json.dumps(dict(
            handoff=dict(sha256=hsha), overall_verdict='ACCEPT', reviewer='test', date='2026-10-03',
            checklist=dict(step_0_handoff=dict(verdict_gate='accepted_documentation_only_minor_fixes')))))
        (agent / 'X').mkdir()
        (agent / 'X/data.txt').write_bytes(data_txt)
        # sources a traversing path would read: without the S6-B-04 checks these hashes match and the copy is written
        (agent / 'tools').mkdir()
        (agent / 'tools/common.py').write_bytes(deliver['POWER_PROTOCOL.md'])
        (td / 'abs.txt').write_bytes(data_txt)
        rs = read_set if read_set is not None else [
            dict(path='LRI_C7_D2_HPC/tools/common.py', sha256=sha(common_c7), c8d2_reference_copy='reference/c7/common.py'),
            dict(path='X/data.txt', sha256=sha(data_txt), note='recorded first')]
        rs_bytes = json.dumps(dict(read_set=rs)).encode()
        rs_sha = sha(rs_bytes)
        if tamper_read_set:
            rs_bytes = json.dumps(dict(read_set=rs, note='edited after the review')).encode()
        (reviews / 'handoff-tests/external_read_set.json').write_bytes(rs_bytes)
        return pkg, agent, outside, hsha, rs_sha

    def snapshot(d: Path) -> dict:
        return {p.relative_to(d).as_posix(): (p.read_bytes() if p.is_file() and not p.is_symlink() else 'link')
                for p in sorted(d.rglob('*')) if p.is_file() or p.is_symlink()}

    def vend(pkg: Path, agent: Path, hsha: str, rs_sha: str, fail_write: str | None = None) -> subprocess.CompletedProcess:
        """Run the sandbox's tool; fail_write: make every write-mode open of a file of that name raise OSError (an
        injected I/O failure in the write phase, through a runpy wrapper)."""
        args = ['--agent-lri', str(agent), '--expect-sha256', hsha, '--expect-read-set-sha256', rs_sha]
        tool = str(pkg / 'tools/vendor_assembly.py')
        cmd = [sys.executable, '-B', tool, *args] if fail_write is None else [sys.executable, '-B', '-c', (
            'import pathlib, runpy, sys\n'
            'orig, target = pathlib.Path.open, sys.argv[2]\n'
            'def guarded(self, mode="r", *a, **k):\n'
            '    if self.name == target and any(c in mode for c in "wxa"):\n'
            '        raise OSError(f"injected write failure: {self}")\n'
            '    return orig(self, mode, *a, **k)\n'
            'pathlib.Path.open = guarded\n'
            'tool = sys.argv[1]\n'
            'sys.argv = [tool] + sys.argv[3:]\n'
            'runpy.run_path(tool, run_name="__main__")\n'), tool, fail_write, *args]
        return subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})

    pkg, agent, outside, hsha, rs_sha = sandbox('clean')
    r = vend(pkg, agent, hsha, rs_sha)
    ok = r.returncode == 0 and (pkg / 'tools/VENDORED.json').is_file()
    if ok:
        vj = json.loads((pkg / 'tools/VENDORED.json').read_text())
        ok = (vj['fixtures']['read_set']['sha256'] == rs_sha and (pkg / 'tools/common.py').read_bytes() == common_pkg
              and (pkg / 'vendor/c8_assembly_fixtures/LRI_C7_D2_HPC/tools/common.py').read_bytes() == common_c7
              and (pkg / 'vendor/c8_assembly/HANDOFF_assembly.json').is_file())
    check('S6-B-04: vendor_assembly.py vendors a clean sandbox with both reviewed digests', ok,
          r.stdout[-300:] + r.stderr[-600:])
    good = [dict(path=k, sha256=sha(v), md5=md5(v), bytes=len(v)) for k, v in deliver.items()]
    ref_entry = dict(path='LRI_C7_D2_HPC/tools/common.py', sha256=sha(common_c7), c8d2_reference_copy='reference/c7/common.py')
    data_entry = dict(path='X/data.txt', sha256=sha(data_txt))
    cases = [
        ('a read-set path ../../tools/common.py with a valid reference copy (the reviewer\'s example)',
         dict(read_set=[dict(ref_entry, path='../../tools/common.py')]), 'not a canonical relative path'),
        ('a HANDOFF file path ../../tools/common.py',
         dict(files=good + [dict(good[1], path='../../tools/common.py')]), 'not a canonical relative path'),
        ('an absolute read-set path', dict(read_set=[dict(data_entry, path=str(td / 'abs.txt'))]),
         'not a canonical relative path'),
        ("a '.' component", dict(read_set=[dict(data_entry, path='X/./data.txt')]), 'not a canonical relative path'),
        ('a repeated fixture path', dict(read_set=[data_entry, data_entry]), 'collides with'),
        ('two fixture paths equal ignoring case', dict(read_set=[data_entry, dict(data_entry, path='x/DATA.txt')]),
         'collides with'),
        ('a fixture path that is the directory of another', dict(read_set=[data_entry, dict(data_entry, path='X')]),
         'collides with'),
        ('a HANDOFF file named like the HANDOFF copy',
         dict(files=good + [dict(good[1], path='HANDOFF_assembly.json')]), 'collides with'),
        ('a c8d2_reference_copy outside reference/',
         dict(read_set=[dict(ref_entry, c8d2_reference_copy='tools/common.py')]), 'not under reference/'),
        ('a read set not at the reviewed digest', dict(tamper_read_set=True), 'not the reviewed'),
        ('vendor/ a symlink to a directory outside the package', dict(vendor_link=True), 'symlink'),
        # fix-round-1 residual: the interface is checked from the staged bytes before the first write
        ('an order8_assembly.py that lacks a used name (slots)',
         dict(assembly=STUB_ASSEMBLY.replace('def slots(', 'def slots_renamed(').encode()), "lacks ['slots']"),
        ('an order8_assembly.py whose execution fails',
         dict(assembly=STUB_ASSEMBLY.encode() + b'raise RuntimeError("broken at import")\n'), 'does not execute'),
        # S6R2-B-02: the metadata output gets the destination checks of every other output
        ('a tools/VENDORED.json that is a dangling symlink to the staged ../vendor/c8_assembly/order8_assembly.py '
         "(the reviewer's example)", dict(vendored_link='deliverable'), 'VENDORED.json'),
        ('a tools/VENDORED.json that is a dangling symlink to a path outside the package',
         dict(vendored_link='external'), 'VENDORED.json'),
        ('a vendor/c8_assembly that is a dangling symlink', dict(assembly_link=True), 'c8_assembly'),
    ]
    for i, (name, kw, needle) in enumerate(cases):
        pkg, agent, outside, hsha, rs_sha = sandbox(f'case{i}', **kw)
        before = snapshot(pkg)
        r = vend(pkg, agent, hsha, rs_sha)
        after = snapshot(pkg)
        tag = 'S6R2-B-02' if kw.keys() & {'vendored_link', 'assembly_link'} else 'S6-B-04'
        check(f'{tag}: vendor_assembly.py refuses {name} before any write',
              r.returncode != 0 and needle in r.stdout + r.stderr and after == before
              and not (pkg / 'vendor/c8_assembly').exists() and not (pkg / 'vendor/c8_assembly_fixtures').exists()
              and not (pkg / 'tools/VENDORED.json').exists() and not any(outside.iterdir())
              and (pkg / 'tools/common.py').read_bytes() == common_pkg,
              dict(rc=r.returncode, out=(r.stdout + r.stderr)[-500:],
                   changed=sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))[:10],
                   outside=[p.name for p in outside.iterdir()]))
    # S6R2-B-02 (same defect class): a write that fails part-way removes everything this run created
    for i, (name, target) in enumerate((('the VENDORED.json write (the last one)', 'VENDORED.json'),
                                        ('a fixture write (data.txt)', 'data.txt'))):
        pkg, agent, outside, hsha, rs_sha = sandbox(f'fail{i}')
        before = snapshot(pkg)
        r = vend(pkg, agent, hsha, rs_sha, fail_write=target)
        after = snapshot(pkg)
        check(f'S6R2-B-02: a failure of {name} leaves the package as it was (no vendor/ tree, no VENDORED.json)',
              r.returncode != 0 and 'injected write failure' in r.stderr and after == before
              and not (pkg / 'vendor').exists() and not (pkg / 'tools/VENDORED.json').exists()
              and not any(outside.iterdir()),
              dict(rc=r.returncode, out=(r.stdout + r.stderr)[-500:],
                   changed=sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))[:10]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--standalone', action='store_true', help='A-ASM-1(a) only (an early HANDOFF before G2a)')
    ap.add_argument('--no-review-record', action='store_true', help='the review record is not reachable (cluster)')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    results, failed, notes = [], [], []

    def check(name: str, ok: bool, detail='') -> None:
        detail = detail if isinstance(detail, str) else json.dumps(detail, default=str)
        results.append(dict(check=name, passed=bool(ok), detail=detail[-1200:]))
        if not ok:
            failed.append(name)
        print(('PASS ' if ok else 'FAIL ') + name + (f': {detail[-500:]}' if detail and not ok else ''), flush=True)

    v = json.loads(VENDORED.read_bytes())
    hcopy = VENDOR / 'HANDOFF_assembly.json'
    hbytes = hcopy.read_bytes()
    handoff = json.loads(hbytes)
    hsha = hashlib.sha256(hbytes).hexdigest()
    # (a) the HANDOFF and its acceptance
    check('the HANDOFF copy is at the sha256 VENDORED.json records', hsha == v['handoff']['sha256'],
          dict(copy=hsha, vendored=v['handoff']['sha256']))
    check('VENDORED.json records an accepting review of this HANDOFF with a step-0 verdict-gate decision',
          v['review']['overall_verdict'] in ('ACCEPT', 'ACCEPT_WITH_MINOR') and v['review']['verdict_gate'] in GATE_DECISIONS
          and v['review']['record'].endswith(f'order8_assembly_{hsha[:12]}.json'), v['review'])
    # the complete deliverable set
    listed = {f['path']: f for f in handoff['files']}
    have = regular_files(VENDOR)
    extra = sorted(set(have) - set(listed) - {'HANDOFF_assembly.json'})
    missing = sorted(set(listed) - set(have))
    check('vendor/c8_assembly holds exactly the HANDOFF deliverables plus the HANDOFF copy', not extra and not missing,
          dict(extra=extra, missing=missing))
    bad = [n for n, f in listed.items() if n in have and (have[n].is_symlink() or sha256_file(have[n]) != f['sha256']
                                                            or md5_file(have[n]) != f['md5']
                                                            or have[n].stat().st_size != f['bytes'])]
    check('every vendored file is a regular file at the sha256, md5 and size the HANDOFF records', not bad, bad)
    vf = {f['path']: f for f in v['files']}
    check('VENDORED.json lists the HANDOFF deliverables with the HANDOFF pins',
          set(vf) == set(listed) and all((vf[n]['sha256'], vf[n]['md5'], vf[n]['bytes']) ==
                                         (listed[n]['sha256'], listed[n]['md5'], listed[n]['bytes']) for n in listed),
          sorted(set(vf) ^ set(listed)))
    # fixtures
    fx = {f['path']: f for f in v['fixtures']['files']}
    have = regular_files(FIXTURES)
    check('vendor/c8_assembly_fixtures holds exactly the VENDORED.json fixtures',
          set(have) == set(fx), dict(extra=sorted(set(have) - set(fx)), missing=sorted(set(fx) - set(have))))
    badfx = []
    for n, f in fx.items():
        p = have.get(n)
        if p is None or p.is_symlink() or not p.is_file() or sha256_file(p) != f['sha256'] or p.stat().st_size != f['bytes']:
            badfx.append(n)
            continue
        pin = f['source_pin']
        if pin['kind'] == 'reference_checksum':
            listing = ROOT / pin['list']
            entry = next((ln.split('  ', 1)[0] for ln in listing.read_text().splitlines()
                          if ln.split('  ', 1)[-1] == pin['entry']), None)
            if entry != f['sha256'] or sha256_file(ROOT / pin['source']) != entry:
                badfx.append(f'{n} (reference pin)')
        elif pin['kind'] == 'file_sha256_recorded_first' and pin['sha256'] != f['sha256']:
            badfx.append(f'{n} (recorded pin)')
        elif pin['kind'] == 'git':
            repo = ROOT.parent / pin['repository']
            if (repo / '.git').exists():
                r = subprocess.run(['git', '-C', str(repo), 'show', f'{pin["commit"]}:{pin["path"]}'], capture_output=True)
                if r.returncode != 0 or hashlib.sha256(r.stdout).hexdigest() != f['sha256']:
                    badfx.append(f'{n} (git pin)')
            else:
                notes.append(f'git pin of {n} not re-read: {pin["repository"]} is not reachable here')
    check('every fixture is a regular file at its pin (reference copies at their checksum-list entries)', not badfx,
          badfx)
    if (ROOT / '.git').exists():
        ls = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-s'], capture_output=True, text=True, check=True).stdout
        links = [ln.split('\t', 1)[1] for ln in ls.splitlines() if ln.startswith('120000 ')]
    else:
        links = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_symlink()]
    check('no symlink is tracked anywhere in the package', not links, links[:20])
    # the review record
    rpath = ROOT.parent / v['review']['record']
    if a.no_review_record:
        notes.append(f'review record not checked here (--no-review-record): {v["review"]["record"]}')
    else:
        try:
            rr = json.loads(rpath.read_bytes())
        except OSError as e:
            rr = {'error': str(e)}
        steps = rr.get('checklist', {})
        want = [s for s in steps if s.startswith('step_')]
        nums = sorted(int(s.split('_')[1]) for s in want)
        check('the review record exists, accepts this HANDOFF with the same verdict gate and has steps 0-10',
              rr.get('handoff', {}).get('sha256') == hsha and rr.get('overall_verdict') == v['review']['overall_verdict']
              and steps.get('step_0_handoff', {}).get('verdict_gate') == v['review']['verdict_gate']
              and nums == list(range(11)) and all('status' in steps[s] for s in want),
              dict(record=str(rpath), steps=nums, statuses={s: steps[s].get('status') for s in want}))
    # the interface
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('c8_vendored_order8_assembly_check', VENDOR / 'order8_assembly.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sigs = v['interface']['signatures']
    badsig = [n for n, s in sigs.items() if not callable(getattr(mod, n, None)) or signature_record(getattr(mod, n)) != s]
    check('the vendored order8_assembly exports every used name with the signature VENDORED.json records',
          not badsig and set(sigs) >= {'coefficients', 'jacobians', 'campaign_moments', 'sector_assembly',
                                        'power_null_rows', 'top_slot_gate', 'loop7_gate', 'affinity_gate',
                                        'ms8_rows', 'ms8_value'}, badsig)
    notes.append(v['interface'].get('stand_in', ''))
    # the vendor/ rule: prepare_inputs (build and verify) through an open/import spy
    with tempfile.TemporaryDirectory(prefix='c8d2_vendor_rule_') as td:
        spy = Path(td) / 'spy.py'
        spy.write_text(SPY)
        vend = os.path.realpath(ROOT / 'vendor')
        for mode in ('build', 'verify'):
            out = Path(td) / f'{mode}.json'
            dest = Path(td) / 'inputs_regenerated'
            r = subprocess.run([sys.executable, '-B', str(spy), str(ROOT), vend, str(out), mode, str(dest)],
                               capture_output=True, text=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
            rec = json.loads(out.read_text()) if out.exists() else dict(events=[], vendored_modules=['?'],
                                                                        error=r.stderr[-500:])
            if mode == 'build' and dest.exists():
                shutil.rmtree(dest)
            via_helper = all(any(fn == 'digest' and file.endswith('common.py') for file, fn in e['stack'])
                             and e['mode'] in ('rb', 'r') for e in rec['events'])
            check(f'vendor/ rule: prepare_inputs {mode} opens vendored files only through the hash helper and imports '
                  f'nothing from vendor/', rec.get('error') is None and via_helper and not rec['vendored_modules'],
                  dict(error=rec.get('error'), opened=[e['path'] for e in rec['events']][:10],
                       vendored_modules=rec['vendored_modules']))
            if mode == 'build':
                notes.append(f'prepare_inputs build opened {len(rec["events"])} vendored files (it reads the pins from '
                             f'tools/VENDORED.json)')
            else:
                notes.append(f'prepare_inputs verify opened {len(rec["events"])} vendored files, each through common.digest')
    # the vendor/ rule for `plan` and `run --index`, in a scratch package copy with the fake native worker
    sys.path.insert(0, str(ROOT / 'tests'))
    from pkgcopy import make_package  # noqa: E402
    with tempfile.TemporaryDirectory(prefix='c8d2_vendor_rule_pr_') as td:
        td = Path(td)
        pkg = make_package(td)
        spy = td / 'spy_prod.py'
        spy.write_text(SPY_PROD)
        vend = os.path.realpath(pkg / 'vendor')
        camp, scratch = td / 'campaign', td / 'scratch'
        scratch.mkdir()
        env = {k: v for k, v in os.environ.items() if not k.startswith(('C8_', 'SLURM_', 'SBATCH_'))}
        env.update(PYTHONDONTWRITEBYTECODE='1', C8_INPUTS=str(pkg / 'tests/fixtures/inputs_mini'))
        if os.environ.get('C8_SEEDS'):
            env['C8_SEEDS'] = os.environ['C8_SEEDS']
        for mode in ('plan', 'run'):
            out = td / f'{mode}.json'
            r = subprocess.run([sys.executable, '-B', str(spy), str(pkg), vend, str(out), mode, str(camp), str(scratch)],
                               capture_output=True, text=True, env=env)
            rec = json.loads(out.read_text()) if out.exists() else dict(events=[], relative=[], vendored_modules=['?'],
                                                                        error=r.stderr[-500:])
            if mode == 'plan':
                ok = (rec.get('error') is None and not rec['vendored_modules']
                      and all(any(fn == 'digest' and file.endswith('common.py') for file, fn in e['stack'])
                              and e['mode'] in ('rb', 'r') for e in rec['events']))
                what = 'opens vendored files only through the hash helper and imports nothing from vendor/'
            else:
                ok = rec.get('error') is None and not rec['vendored_modules'] and not rec['events']
                what = 'opens nothing under vendor/ and imports nothing from vendor/'
            ok = ok and all(x['via'] and x['via'][0].startswith('_rmtree') for x in rec['relative'])
            check(f'vendor/ rule: production.py {mode}{" --index 0" if mode == "run" else ""} (test-only, scratch copy) '
                  f'{what}', ok, dict(error=rec.get('error'), opened=[e['path'] for e in rec['events']][:10],
                                      vendored_modules=rec['vendored_modules'],
                                      relative=[x for x in rec['relative'] if not (x['via'] and x['via'][0].startswith('_rmtree'))][:5],
                                      stderr=r.stderr[-300:] if r.returncode else ''))
            notes.append(f'production.py {mode} opened {len(rec["events"])} vendored files'
                         + (' (the inputs manifest pins, through common.digest)' if mode == 'plan' else ''))
    # (b) the input manifest
    if not a.standalone:
        m = json.loads((ROOT / 'inputs/manifest.json').read_bytes())
        pins = m.get('vendored_assembly') or {}
        ok = (m.get('vendored_assembly_handoff_sha256') == hsha and pins.get('handoff_sha256') == hsha
              and pins.get('files') == {f['vendored_path']: f['sha256'] for f in v['files']}
              and pins.get('files') == {f'vendor/c8_assembly/{n}': f['sha256'] for n, f in listed.items()})
        check('A-ASM-1(b): inputs/manifest.json records the HANDOFF sha256 and every vendored pin, equal to '
              'VENDORED.json and the HANDOFF', ok, dict(handoff=m.get('vendored_assembly_handoff_sha256'),
                                                        files=len(pins.get('files') or {})))
        if ok:
            sys.path.insert(0, str(ROOT / 'tools'))
            import prepare_inputs as pi  # noqa: E402
            try:
                pi.verify(allow_no_l8=True)  # the L8 packs are check_inputs.py's; the vendored pins are checked here
                verified = True
            except Exception as e:  # pragma: no cover - reported
                verified = f'{type(e).__name__}: {e}'
            check('A-ASM-1(b): prepare_inputs.verify() passes with the vendored pins', verified is True, str(verified))
            with tempfile.TemporaryDirectory(prefix='c8d2_vendor_flip_') as td:
                exp = Path(td) / 'pkg'
                exp.mkdir()
                arch = subprocess.run(['git', '-C', str(ROOT), 'archive', '--format=tar', 'HEAD'], capture_output=True,
                                      check=True).stdout if (ROOT / '.git').exists() else None
                if arch is None:  # an export without .git (cluster): copy it, leaving out the multi-GB L8 packs
                    shutil.copytree(ROOT, exp, dirs_exist_ok=True, symlinks=False,
                                    ignore=shutil.ignore_patterns('free_L8.pack', 'power_L8.pack'))
                else:
                    subprocess.run(['tar', '-x', '-C', str(exp)], input=arch, check=True)
                code = ('import sys; sys.path.insert(0, sys.argv[1]); import prepare_inputs as pi\n'
                        'try:\n    pi.verify()\nexcept Exception as e:\n    print("REFUSED", e); sys.exit(3)\n'
                        'print("ACCEPTED")\n')
                env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'C8_ALLOW_NO_L8': '1'}
                env.pop('C8_INPUTS', None)
                r0 = subprocess.run([sys.executable, '-B', '-c', code, str(exp / 'tools')], capture_output=True,
                                    text=True, env=env)
                target = exp / 'vendor/c8_assembly/order8_assembly.py'
                b = bytearray(target.read_bytes())
                b[100] ^= 1
                target.write_bytes(bytes(b))
                r = subprocess.run([sys.executable, '-B', '-c', code, str(exp / 'tools')], capture_output=True,
                                   text=True, env=env)
                check('A-ASM-1(b): a one-byte change to a vendored file makes prepare_inputs.verify() fail (the '
                      'untouched scratch export verifies)', r0.returncode == 0 and r.returncode == 3
                      and 'order8_assembly.py' in r.stdout, (r0.stdout + r0.stderr + r.stdout + r.stderr)[-700:])
    # S6-B-04: tools/vendor_assembly.py's destinations and read-set authentication, in sandboxes (both modes)
    with tempfile.TemporaryDirectory(prefix='c8d2_vendor_assembly_') as td:
        vendor_assembly_sandbox(Path(td), check)
    rec = dict(schema='c8-d2-gate-1', gate='A-ASM-1(a)' if a.standalone else 'A-ASM-1(a)+(b)',
               handoff_sha256=hsha, passed=not failed, failed=failed, checks=results, notes=[n for n in notes if n],
               python=sys.version.split()[0], host=os.uname().nodename)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    for n in rec['notes']:
        print('NOTE', n)
    print(f'check_vendored{" --standalone" if a.standalone else ""}: {len(results) - len(failed)}/{len(results)} '
          f'checks passed')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
