#!/usr/bin/env python3
"""Vendor C63d's order-8 assembly from its HANDOFF (PLAN.md "On HANDOFF", H2 checklist steps 8 and 10(i); R01, R16).

Run once per HANDOFF on the Mac, after the H2 review accepted that HANDOFF, from the package root:
  python3 -B tools/vendor_assembly.py --agent-lri /Users/zheng/Documents/Agent_LRI --expect-sha256 <HANDOFF sha256> \
      --expect-read-set-sha256 <sha256 of the reviewed external_read_set.json>
Both inputs are authenticated against the reviewed digests before anything is read from them (Stage-6 finding
S6-B-04): the HANDOFF by --expect-sha256, the external read set by --expect-read-set-sha256 (the vendoring of
2026-10-03 used 7b14f50a..., recorded in tools/VENDORED.json fixtures.read_set). Every destination (a HANDOFF file
path under vendor/c8_assembly/, a read-set path under vendor/c8_assembly_fixtures/) must be a canonical relative path
(no absolute path, no '.', '..' or empty component, no backslash or control character), unique even ignoring case
(macOS), never the HANDOFF copy's own name, and contained in its vendor root with no symlink on the way; all of this
is checked before the first write, and every file is created exclusively (never over an existing file). The metadata
output tools/VENDORED.json gets the same checks (Stage-6 round-2 finding S6R2-B-02: a dangling symlink there used to
pass the existence preflight and redirect the metadata write onto a vendored module or outside the package): it must
not exist, not even as a dangling symlink, before anything is read and again just before it is written, and it is created
exclusively. If a write fails, every file and directory this run created is removed again, so a retry starts clean.
It writes, and refuses if any of them already exists (a later HANDOFF revision needs a new review and a new pin):
  vendor/c8_assembly/          every deliverable HANDOFF_assembly.json lists, byte-identical, each at the sha256,
                               md5 and byte count the HANDOFF records, plus a byte copy of the HANDOFF itself;
  vendor/c8_assembly_fixtures/ the LRI_ROOT tree: byte copies (regular files, never symlinks) of the external files
                               the vendored tests and exact_check.py read through LRI_ROOT, as measured by the H2
                               review's open-audit run (external_read_set.json). Each copy comes from a pinned source:
                               a reference/ copy whose sha256 equals its reference checksum-list entry, a pinned git
                               commit (`git show <commit>:<path>`), or a file whose sha256 was recorded first (the
                               read set); every copy must equal the read set's recorded sha256;
  tools/VENDORED.json          the HANDOFF's sha256 and date, every vendored file's pin, the fixture provenance, the
                               C62d review record (verdict and the step-0 verdict-gate decision), and the call
                               signatures of the names the package uses (for tests/check_vendored.py).
It executes the vendored order8_assembly only to check and record those signatures, from the staged (HANDOFF-checked)
bytes before the first write, so a module that fails to execute or lacks a used name leaves nothing written (bytecode
writing disabled). No input-building path, `plan` or `run` imports anything from vendor/ (PLAN "One rule governs reads
of vendor/")."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'vendor/c8_assembly'
FIXTURES = ROOT / 'vendor/c8_assembly_fixtures'
OUT = ROOT / 'tools/VENDORED.json'
USED = ('coefficients', 'jacobians', 'campaign_moments', 'sector_assembly', 'power_null_rows', 'top_slot_gate',
        'loop7_gate', 'affinity_gate', 'ms8_rows', 'ms8_value', 'slots')
INTERFACE_NOTES = {
    'jacobians': 'complex step; float or two_loop.json-string B2 only (refuses an exact-mode B2); no exact mode',
    'loop7_gate': 'order 8 only (raises at order 7, where loop 7 is the top loop)',
    'top_slot_gate': 'skips loops absent from J: assemble.py asserts coverage of L = 3..8 before calling it',
    'affinity_gate': 'perturbs loops 5..order present in `means` (DECISIONS.md B3); assemble.py asserts 5..8',
    'power_null_rows': 'no length or finiteness guards and no d argument: assemble.py guards the inputs and adds '
                       'the POWER_PROTOCOL PP8 marker (order 6 for both d; order 5 at d=2)',
}
MAX_FIXTURE_BYTES = 20 * 1024 * 1024  # PLAN: a read set above 20 MB stops for a host decision


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


HEX64 = re.compile(r'[0-9a-f]{64}')


def safe_rel(rel, what: str) -> str:
    """rel when it is a canonical relative POSIX path (no absolute path, no '.', '..' or empty component, no
    backslash, no control character); SystemExit otherwise."""
    p = PurePosixPath(rel) if isinstance(rel, str) else None
    if (p is None or not rel or p.is_absolute() or p.as_posix() != rel or any(c in ('.', '..') for c in p.parts)
            or '\\' in rel or any(ord(ch) < 32 or ord(ch) == 127 for ch in rel)):
        raise SystemExit(f'{what}: {rel!r} is not a canonical relative path (traversal or absolute path refused)')
    return rel


def destination(root: Path, rel: str, what: str) -> Path:
    """root/rel after proving containment: rel canonical, root a descendant of the package root, no existing component
    from the package root down to the destination a symlink or a non-directory, the destination absent, and the
    resolved destination under the resolved root."""
    safe_rel(rel, what)
    dest = root.joinpath(*PurePosixPath(rel).parts)
    base = ROOT.resolve()
    chain = [dest.parent, *dest.parent.parents]
    for d in reversed([c for c in chain if c == ROOT or ROOT in c.parents]):
        if d.is_symlink() or (d.exists() and not d.is_dir()):
            raise SystemExit(f'{what}: {d} is a symlink or not a directory: refusing to write {rel!r} through it')
    if dest.is_symlink() or dest.exists():
        raise SystemExit(f'{what}: {dest} exists: refusing to overwrite it')
    if not dest.resolve().is_relative_to(root.resolve()) or not root.resolve().is_relative_to(base):
        raise SystemExit(f'{what}: {rel!r} resolves outside {root.relative_to(ROOT)}')
    return dest


def checksum_entry(listing: Path, rel: str) -> str | None:
    """The sha256 that a reference checksum list (paths relative to reference/) records for rel."""
    for line in listing.read_text().splitlines():
        h, _, name = line.partition('  ')
        if name == rel:
            return h
    return None


def signature_record(fn) -> list:
    """A structured, Python-version-independent signature: parameter names, kinds and default reprs (annotations,
    which the module keeps as strings, are left out)."""
    return [dict(name=p.name, kind=p.kind.name, default=None if p.default is inspect.Parameter.empty else repr(p.default))
            for p in inspect.signature(fn).parameters.values()]


def load_vendored_module(data: bytes):
    """The vendored order8_assembly executed from its staged bytes (the HANDOFF-checked copy), so that the interface is
    checked before anything is written (fix-round-1 residual); __file__ names its vendored path. A module that fails
    to execute is refused (SystemExit)."""
    sys.dont_write_bytecode = True
    path = VENDOR / 'order8_assembly.py'
    name = 'c8_vendored_order8_assembly'
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(path))
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(path)
    sys.modules[name] = mod  # as an import would (dataclasses and typing look the module up)
    try:
        exec(compile(data, str(path), 'exec'), mod.__dict__)
    except Exception as e:  # noqa: BLE001 -- any failure of the vendored code stops the vendoring before a write
        sys.modules.pop(name, None)
        raise SystemExit(f'the vendored order8_assembly.py does not execute ({type(e).__name__}: {e}): nothing written')
    return mod


def write_all(staged: dict) -> None:
    """Create every staged file exclusively, in order, each destination re-checked just before its write (contained in
    its root, no symlink on the way, absent); if anything fails, the files and directories created here are removed
    again (newest first) and the error propagates, so a failed vendoring leaves the package as it was."""
    roots = (VENDOR, FIXTURES, OUT.parent)
    created_files: list[Path] = []
    created_dirs: list[Path] = []
    try:
        for p, data in staged.items():
            root = next(r for r in roots if r in p.parents)
            destination(root, p.relative_to(root).as_posix(), 'write')  # unchanged since the checks
            missing = [d for d in reversed([p.parent, *p.parent.parents]) if ROOT in d.parents and not d.exists()]
            for d in missing:
                d.mkdir()
                created_dirs.append(d)
            with p.open('xb') as f:
                created_files.append(p)
                f.write(data)
    except BaseException:
        for f in reversed(created_files):
            f.unlink(missing_ok=True)
        for d in reversed(created_dirs):
            try:
                d.rmdir()
            except OSError:
                pass
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--agent-lri', type=Path, required=True, help='the directory holding LRI_C8_shared and the sources')
    ap.add_argument('--expect-sha256', required=True, help='sha256 of the reviewed HANDOFF_assembly.json')
    ap.add_argument('--expect-read-set-sha256', required=True,
                    help='sha256 of the reviewed LRI_C8_shared/inventory/reviews/handoff-tests/external_read_set.json')
    a = ap.parse_args()
    for name in ('expect_sha256', 'expect_read_set_sha256'):
        if not HEX64.fullmatch(getattr(a, name)):
            raise SystemExit(f'--{name.replace("_", "-")} must be 64 lowercase hex digits')
    agent = a.agent_lri.resolve()
    shared = agent / 'LRI_C8_shared'
    for p in (VENDOR, FIXTURES, OUT):
        if p.exists() or p.is_symlink():  # a dangling symlink too (S6R2-B-02)
            raise SystemExit(f'{p} exists (or is a symlink): a HANDOFF revision needs a new review, a new pin and an '
                             'explicit step')
    destination(OUT.parent, OUT.name, 'metadata output')  # contained, no symlink on the way (S6R2-B-02)
    hbytes = (shared / 'assembly/HANDOFF_assembly.json').read_bytes()
    hsha = sha256(hbytes)
    if hsha != a.expect_sha256:
        raise SystemExit(f'HANDOFF_assembly.json has sha256 {hsha}, not the reviewed {a.expect_sha256}: stop, ask C63d')
    handoff = json.loads(hbytes)
    review_path = shared / f'inventory/reviews/order8_assembly_{hsha[:12]}.json'
    rbytes = review_path.read_bytes()
    review = json.loads(rbytes)
    gate = review.get('checklist', {}).get('step_0_handoff', {}).get('verdict_gate')
    if (review.get('handoff', {}).get('sha256') != hsha or review.get('overall_verdict') not in ('ACCEPT', 'ACCEPT_WITH_MINOR')
            or not gate):
        raise SystemExit(f'{review_path}: no accepting review of this HANDOFF with a recorded step-0 verdict gate')
    # 1. the complete deliverable set, from the bytes whose hashes were checked
    files, staged, seen = [], {}, {VENDOR: {'handoff_assembly.json': 'the HANDOFF copy'}, FIXTURES: {}}

    def claim(root: Path, rel: str, what: str) -> Path:
        """A contained, unique destination (unique also ignoring case: macOS folds case), neither a file where another
        destination needs a directory nor the reverse."""
        dest = destination(root, rel, what)
        key = rel.casefold()
        clash = [r for k, r in seen[root].items() if k == key or k.startswith(key + '/') or key.startswith(k + '/')]
        if clash:
            raise SystemExit(f'{what}: destination {rel!r} collides with {clash[0]!r} under {root.relative_to(ROOT)}')
        seen[root][key] = rel
        return dest

    for f in handoff['files']:
        rel = f['path']
        dest = claim(VENDOR, rel, 'HANDOFF file')
        data = (shared / 'assembly' / rel).read_bytes()
        if (sha256(data), md5(data), len(data)) != (f['sha256'], f['md5'], f['bytes']):
            raise SystemExit(f'assembly/{rel} differs from the HANDOFF record: the folder changed after the HANDOFF')
        staged[dest] = data
        files.append(dict(path=rel, vendored_path=f'vendor/c8_assembly/{rel}', source=f'LRI_C8_shared/assembly/{rel}',
                          sha256=f['sha256'], md5=f['md5'], bytes=f['bytes']))
    staged[VENDOR / 'HANDOFF_assembly.json'] = hbytes
    # 2. the LRI_ROOT fixtures, from the measured read set
    rs_path = shared / 'inventory/reviews/handoff-tests/external_read_set.json'
    rs_bytes = rs_path.read_bytes()
    if sha256(rs_bytes) != a.expect_read_set_sha256:
        raise SystemExit(f'{rs_path.name} has sha256 {sha256(rs_bytes)}, not the reviewed '
                         f'{a.expect_read_set_sha256}: stop, the read set changed after the H2 review')
    read_set = json.loads(rs_bytes)['read_set']
    fixtures, total = [], 0
    for e in read_set:
        rel, want = e['path'], e['sha256']
        dest = claim(FIXTURES, rel, 'read-set fixture')
        ref = e.get('c8d2_reference_copy')
        if ref:
            if not safe_rel(ref, 'c8d2_reference_copy').startswith('reference/'):
                raise SystemExit(f'c8d2_reference_copy {ref!r} is not under reference/')
            sub = ref[len('reference/'):]
            listing = ROOT / ('reference/SHA256SUMS_c8' if sub.split('/')[0] in ('c8d1_inputs8', 'c7d2_hpc_a55958f',
                                                                                 'c7d2_production_2026')
                              else 'reference/SHA256SUMS')
            data = (ROOT / ref).read_bytes()
            pinned = checksum_entry(listing, sub)
            if pinned is None or sha256(data) != pinned:
                raise SystemExit(f'{ref}: not at its {listing.name} entry')
            pin = dict(kind='reference_checksum', source=ref, list=listing.relative_to(ROOT).as_posix(), entry=sub,
                       sha256=pinned)
        elif e.get('source_repo_head'):
            repo, _, sub = rel.partition('/')
            commit = subprocess.run(['git', '-C', str(agent / repo), 'rev-parse', e['source_repo_head'] + '^{commit}'],
                                    capture_output=True, text=True, check=True).stdout.strip()
            data = subprocess.run(['git', '-C', str(agent / repo), 'show', f'{commit}:{sub}'], capture_output=True,
                                  check=True).stdout
            pin = dict(kind='git', repository=repo, commit=commit, path=sub)
        else:
            data = (agent / rel).read_bytes()
            pin = dict(kind='file_sha256_recorded_first', source=rel, sha256=want,
                       recorded_in='LRI_C8_shared/inventory/reviews/handoff-tests/external_read_set.json',
                       note=e.get('note'))
        if sha256(data) != want:
            raise SystemExit(f'{rel}: the source bytes differ from the sha256 the read set recorded')
        staged[dest] = data
        total += len(data)
        fixtures.append(dict(path=rel, sha256=want, md5=md5(data), bytes=len(data), source_pin=pin))
    if total > MAX_FIXTURE_BYTES:
        raise SystemExit(f'the fixture read set is {total} bytes (> 20 MB): stop for a host decision')
    # 3. the interface of the names the package uses, from the staged bytes: a failure leaves nothing written
    if VENDOR / 'order8_assembly.py' not in staged:
        raise SystemExit('the HANDOFF does not list order8_assembly.py: nothing to vendor')
    mod = load_vendored_module(staged[VENDOR / 'order8_assembly.py'])
    missing = [n for n in USED if not callable(getattr(mod, n, None))]
    if missing:
        raise SystemExit(f'the vendored order8_assembly lacks {missing}: Stage 2b must adapt (PLAN F01 correction); nothing written')
    signatures = {n: signature_record(getattr(mod, n)) for n in USED}
    rec = dict(
        schema='c8-d2-vendored-1',
        rule='Vendored files are hashed for integrity, imported only by the statistics tools (assemble, combine, '
             'design, verify_result) and the tests, and never used as inputs (PLAN "One rule governs reads of '
             'vendor/"; the one exception is make_lowloop.py --cross-check, which only compares).',
        handoff=dict(path='vendor/c8_assembly/HANDOFF_assembly.json', source='LRI_C8_shared/assembly/HANDOFF_assembly.json',
                     sha256=hsha, md5=md5(hbytes), bytes=len(hbytes), date=handoff.get('date'),
                     owner=handoff.get('owner'), handoff=handoff.get('handoff'),
                     tests_at_handoff=handoff.get('checks_at_handoff', {}).get('tests')),
        files=files,
        review=dict(record=review_path.relative_to(agent).as_posix(), record_sha256_at_vendoring=sha256(rbytes),
                    reviewer=review.get('reviewer'), date=review.get('date'), overall_verdict=review.get('overall_verdict'),
                    verdict_gate=gate,
                    verdict_gate_scope='this HANDOFF version only (step_0_handoff.host_decision of the review record)'),
        power_protocol=dict(path='vendor/c8_assembly/POWER_PROTOCOL.md',
                            sha256=next(f['sha256'] for f in files if f['path'] == 'POWER_PROTOCOL.md')),
        interface=dict(module='vendor/c8_assembly/order8_assembly.py',
                       signatures=signatures, notes=INTERFACE_NOTES,
                       stand_in='none: the HANDOFF arrived before Stage 3, so no stand-in Jacobian module was written'),
        fixtures=dict(root='vendor/c8_assembly_fixtures', lri_root='LRI_ROOT=<package>/vendor/c8_assembly_fixtures',
                      read_set=dict(path='LRI_C8_shared/inventory/reviews/handoff-tests/external_read_set.json',
                                    sha256=sha256(rs_bytes)),
                      count=len(fixtures), bytes=total, files=fixtures),
        exact_check_keys='tests/fixtures/exact_check_keys.json')
    staged[OUT] = (json.dumps(rec, indent=1) + '\n').encode()  # written last, by the same checked exclusive path
    # 4. the writes, each file created exclusively; any failure removes what this run created
    write_all(staged)
    print(json.dumps(dict(handoff_sha256=hsha, vendored=len(files) + 1, fixtures=len(fixtures), fixture_bytes=total,
                          output=str(OUT.relative_to(ROOT))), indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
