#!/usr/bin/env python3
"""Verify (or, with --write, regenerate) the delivered file inventory and SHA-256 checksums, and verify every delivered
C8 result record with tools/verify_result.py.

Run before rebuilding. Default mode permits additional locally generated files;
--strict requires an exact file inventory, apart from build outputs and caches
(bin/, build/, the two L8 packs of make inputs-l8, __pycache__/, *.pyc, .venv/, .git/, .DS_Store). A symlink is never a payload file: a listed one, internal or
escaping, or a listed path through a symlinked directory, fails both modes, and an unlisted one fails --strict (R16). Neither mode runs
integrations or changes files. The external ZIP checksum authenticates the
manifest against the separately distributed digest; internal checks alone are
not a signature.

Delivered C8 result records (W13, Stage-6 fix round 4; PLAN component E: "combine.py and verify_delivery call it").
The manifest's result_records is the explicit set of payload files that are C8 result records: JSON documents whose
top-level schema is RESULT_SCHEMA (assemble.py and combine.py results, order 7 or 8). Both modes recompute each one
with the package's own tools/verify_result.py (one subprocess: `python3 -B <root>/tools/verify_result.py`'s verify(),
with numpy and the vendored assembly; this part is not standard-library only) and fail on any problem it reports, so
a result whose gates block was deleted or whose coefficient is inconsistent fails even when its delivery checksums were
regenerated. Both modes also fail when a delivered JSON file names RESULT_SCHEMA as its top-level schema (or names it
and does not parse) but is not in result_records, and when a listed record is not a listed payload file. Historical
C7 records (schema c7-...) are not C8 result records; an intentional negative fixture is excluded only by name in
NEGATIVE_FIXTURES, with its reason (none is delivered). --write discovers the records, keeps every record the previous
manifest listed that is still delivered (the set only grows while the files exist: a record cannot leave it by losing
its schema), verifies them all and writes nothing when any fails.

--write (maintainers, in a git checkout, right after `git add -A`) rewrites
DELIVERY_MANIFEST.json and SHA256SUMS over every git-tracked payload file as it
is on disk, keeping the manifest's descriptive fields; it refuses a tracked symlink.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath
RESERVED = ('DELIVERY_MANIFEST.json', 'SHA256SUMS')
SKIP_TOP = {'bin', '.git', '.venv', 'build'}
BUILT = {'inputs/packs/free_L8.pack', 'inputs/packs/power_L8.pack'}  # make inputs-l8 (about 7.5 GB, pinned in inputs/manifest.json)
RESULT_SCHEMA = 'c8-d2-hpc-result-1'  # tools/assemble.py RESULT_SCHEMA (C8(2) result records, order 7 or 8)
RESULT_MARKER = RESULT_SCHEMA.encode()
NEGATIVE_FIXTURES: dict[str, str] = {}  # delivered path -> why it is an intentionally invalid C8 result record (W13)
# The batch verifier run in the delivered package's own interpreter context: <root>/tools first on sys.path, every
# record read once and verified with verify_result.verify(); one JSON line {path: problems} per record.
_VERIFY = r'''import json,sys
root=sys.argv[1];sys.path.insert(0,root+'/tools')
import verify_result as vr
for name in sys.argv[2:]:
    try:problems=vr.verify(json.loads(open(root+'/'+name,'rb').read()))
    except Exception as e:problems=[f'unreadable: {type(e).__name__}: {e}']
    print(json.dumps({'path':name,'problems':[str(p)for p in problems]}),flush=True)
'''


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def excluded(rel: str) -> bool:
    parts = rel.split('/')
    return parts[0] in SKIP_TOP or rel in BUILT or '__pycache__' in parts or rel.endswith('.pyc') or parts[-1] == '.DS_Store'


def safe_file(root: Path, name: str) -> Path:
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or '\\' in name or p.as_posix() != name:
        raise ValueError('Unsafe or noncanonical path: ' + repr(name))
    target = root.joinpath(*p.parts)
    # every component, not only the last: a listed 'sub/x' must not pass through a symlinked directory 'sub' (R16)
    if any(root.joinpath(*p.parts[:i]).is_symlink() for i in range(1, len(p.parts) + 1)) \
            or not target.resolve().is_relative_to(root):
        raise ValueError('Symlink or escaping path: ' + repr(name))
    if not target.is_file():
        raise ValueError('Missing regular file: ' + name)
    return target


def result_kind(data: bytes) -> str | None:
    """W13: 'record' when the bytes are a JSON object whose top-level schema is RESULT_SCHEMA, 'unparsed' when they name
    the schema but are not JSON (a truncated record), else None (another document, which may mention the schema)."""
    if RESULT_MARKER not in data:
        return None
    try:
        doc = json.loads(data)
    except ValueError:
        return 'unparsed'
    return 'record' if isinstance(doc, dict) and doc.get('schema') == RESULT_SCHEMA else None


def run_verify_result(root: Path, names: list[str]) -> dict[str, list[str]]:
    """W13: {path: problems} of tools/verify_result.py's verify() on each delivered record, run with the delivered
    package's own verifier in one subprocess (this interpreter; numpy and the vendored assembly are needed). A record
    the subprocess did not report, or a failed subprocess, is a problem: nothing is assumed verified."""
    if not names:
        return {}
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'OPENBLAS_NUM_THREADS': os.environ.get('OPENBLAS_NUM_THREADS', '1')}
    cp = subprocess.run([sys.executable, '-B', '-c', _VERIFY, str(root), *names], capture_output=True, text=True, env=env, cwd=str(root))
    out = {}
    for line in cp.stdout.splitlines():
        try:
            rec = json.loads(line)
            out[rec['path']] = list(rec['problems'])
        except (ValueError, KeyError, TypeError):
            continue
    for n in names:
        if n not in out:
            out[n] = [f'tools/verify_result.py did not report it (exit {cp.returncode}: {cp.stderr.strip()[-300:]})']
    return out


def result_errors(root: Path, listed: list, payload: dict, kinds: dict) -> list[str]:
    """W13: the result-record checks of both modes. listed: the manifest's result_records; payload: {path: sha256} of
    the manifest's files; kinds: {path: result_kind} of every listed JSON payload file read."""
    errors = []
    if not isinstance(listed, list) or not all(isinstance(x, str) for x in listed) or len(set(listed)) != len(listed):
        return ['Manifest result_records is not a list of distinct paths']
    for name in listed:
        if name not in payload:
            errors.append('Result record not a listed payload file: ' + name)
        elif name in NEGATIVE_FIXTURES:
            errors.append('Result record listed and excluded as a negative fixture: ' + name)
    for name, kind in sorted(kinds.items()):
        if kind and name not in listed and name not in NEGATIVE_FIXTURES:
            errors.append(('C8 result record not in result_records (run --write): ' if kind == 'record' else
                           'Unparsable file naming the C8 result schema, not in result_records: ') + name)
    present = [n for n in listed if n in payload and n not in NEGATIVE_FIXTURES]
    for name, problems in sorted(run_verify_result(root, present).items()):
        if problems:
            errors.append(f'Result record fails tools/verify_result.py ({len(problems)} problems; first: {"; ".join(problems[:3])}): {name}')
    return errors


def verify(root: Path, strict: bool = False) -> dict:
    root = root.resolve()
    errors = []
    manifest_path = safe_file(root, 'DELIVERY_MANIFEST.json')
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('schema') != 'lri-c8-d2-hpc-delivery-1':
        raise ValueError('Unexpected delivery manifest schema')
    expected = {}
    expected_bytes = 0
    kinds = {}
    for row in manifest['files']:
        name, sha = row['path'], row['sha256']
        if name in expected or name in RESERVED:
            raise ValueError('Duplicate or reserved manifest entry: '+name)
        if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError('Invalid digest: '+name)
        if not isinstance(row['bytes'], int) or row['bytes'] < 0:
            raise ValueError('Invalid size: '+name)
        expected[name] = sha
        expected_bytes += row['bytes']
        try:
            path = safe_file(root, name)
            if path.stat().st_size != row['bytes']:
                errors.append('Size mismatch: '+name)
            if name.endswith('.json'):  # W13: read once, hashed and classified from the same bytes
                data = path.read_bytes()
                got = hashlib.sha256(data).hexdigest()
                kinds[name] = result_kind(data)
            else:
                got = digest(path)
            if got != sha:
                errors.append('SHA-256 mismatch: '+name)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    if len(expected) != manifest['payload_file_count'] or expected_bytes != manifest['payload_bytes']:
        errors.append('Manifest totals disagree with its inventory')
    listed = {}
    for line in safe_file(root, 'SHA256SUMS').read_text().splitlines():
        sha, sep, name = line.partition('  ')
        if not sep or len(sha) != 64 or name in listed:
            errors.append('Malformed or duplicate SHA256SUMS row: '+line[:160])
            continue
        listed[name] = sha
    wanted = {**expected, 'DELIVERY_MANIFEST.json': digest(manifest_path)}
    if listed != wanted:
        errors.append('SHA256SUMS does not match the payload plus delivery manifest')
    known = set(expected) | set(RESERVED)
    extra = sorted(rel for rel in (p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() or p.is_symlink())
                   if rel not in known and not excluded(rel))
    if strict and extra:
        errors.append(f'{len(extra)} unexpected files in strict mode')
    listed = manifest.get('result_records', [])
    errors += result_errors(root, listed, expected, kinds)  # W13: both modes
    return dict(status='passed' if not errors else 'failed', root=str(root), strict=strict,
                payload_files_checked=len(expected), payload_bytes_checked=expected_bytes,
                manifest_and_checksum_files_checked=2, extra_files_count=len(extra),
                extra_files_preview=extra[:25], errors=errors,
                result_records_verified=len(listed) if isinstance(listed, list) else 0,
                integrations_rerun=False, files_modified=False)


def git_files(root: Path) -> list[str]:
    def git(*args):
        return subprocess.run(['git', '-C', str(root), *args], capture_output=True, check=True).stdout.decode().split('\0')
    if not (root / '.git').exists():
        raise ValueError('--write needs a git checkout of the package')
    untracked = [f for f in git('ls-files', '-z', '--others', '--exclude-standard') if f and not excluded(f)]
    if untracked:
        raise ValueError(f'{len(untracked)} untracked files (e.g. {untracked[:3]}); run `git add -A` (or remove them) before --write')
    names = [f for f in git('ls-files', '-z', '--cached') if f and f not in RESERVED and not excluded(f)]
    links = [f for f in names if (root / f).is_symlink()]
    if links:
        raise ValueError(f'{len(links)} tracked symlinks (e.g. {links[:3]}): the package holds regular files only (R16)')
    missing = [f for f in names if not (root / f).is_file()]
    if missing:
        raise ValueError(f'tracked files missing on disk: {missing[:5]}')
    return sorted(names, key=lambda s: s.encode())


def write(root: Path) -> dict:
    root = root.resolve()
    names = git_files(root)
    old = json.loads((root / 'DELIVERY_MANIFEST.json').read_text()) if (root / 'DELIVERY_MANIFEST.json').exists() else {}
    rows = [dict(path=n, bytes=(root / n).stat().st_size, sha256=digest(root / n)) for n in names]
    # W13: the explicit result-record set: every delivered record found now, plus every record the previous manifest
    # listed that is still delivered (sticky); each is verified before anything is written
    kinds = {n: result_kind((root / n).read_bytes()) for n in names if n.endswith('.json')}
    bad = sorted(n for n, k in kinds.items() if k == 'unparsed' and n not in NEGATIVE_FIXTURES)
    if bad:
        raise ValueError(f'{len(bad)} delivered files name the C8 result schema but do not parse as JSON (e.g. {bad[:3]}); nothing written')
    prev = old.get('result_records', [])
    if not isinstance(prev, list):
        raise ValueError('the previous manifest\'s result_records is not a list; nothing written')
    present = set(names)
    listed = sorted({n for n, k in kinds.items() if k == 'record' and n not in NEGATIVE_FIXTURES} |
                    {n for n in prev if isinstance(n, str) and n in present and n not in NEGATIVE_FIXTURES}, key=lambda s: s.encode())
    failed = {n: p for n, p in run_verify_result(root, listed).items() if p}
    if failed:
        raise ValueError(f'{len(failed)} delivered C8 result records fail tools/verify_result.py; nothing written: '
                         + '; '.join(f'{n}: {p[0]}' for n, p in sorted(failed.items())[:3]))
    doc = {k: v for k, v in old.items() if k != 'files'}
    doc.update(schema='lri-c8-d2-hpc-delivery-1', created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               payload_file_count=len(rows), payload_bytes=sum(r['bytes'] for r in rows), expected_zip_file_count=len(rows) + 2,
               result_records=listed,
               result_records_rule=('W13: every delivered JSON whose top-level schema is ' + RESULT_SCHEMA + ' (plus every record an earlier '
                                    'manifest listed that is still delivered), each verified by tools/verify_result.py in both modes'),
               files=rows)
    (root / 'DELIVERY_MANIFEST.json').write_text(json.dumps(doc, indent=2) + '\n')
    sums = {r['path']: r['sha256'] for r in rows}
    sums['DELIVERY_MANIFEST.json'] = digest(root / 'DELIVERY_MANIFEST.json')
    (root / 'SHA256SUMS').write_text(''.join(f'{h}  {n}\n' for n, h in sorted(sums.items(), key=lambda t: t[0].encode())))
    return dict(status='written', payload_file_count=len(rows), payload_bytes=doc['payload_bytes'], result_records=len(listed))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument('--strict', action='store_true')
    ap.add_argument('--write', action='store_true', help='regenerate DELIVERY_MANIFEST.json and SHA256SUMS over the git-tracked files (after git add -A)')
    args = ap.parse_args()
    try:
        report = write(args.root) if args.write else verify(args.root, args.strict)
    except (OSError, KeyError, TypeError, ValueError, subprocess.CalledProcessError) as exc:
        report = dict(status='failed', errors=[str(exc)])
    print(json.dumps(report, indent=2))
    return 0 if report['status'] in ('passed', 'written') else 1

if __name__ == '__main__':
    sys.exit(main())
