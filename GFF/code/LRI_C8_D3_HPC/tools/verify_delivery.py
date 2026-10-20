#!/usr/bin/env python3
"""Verify (or, with --write, regenerate) the delivered file inventory and SHA-256 checksums (standard library only).

Run before rebuilding. Default mode permits additional locally generated files;
--strict requires an exact file inventory, apart from build outputs and caches
(bin/, build/, the two L8 packs of make inputs-l8, __pycache__/, .pytest_cache/, *.pyc, .venv/, .git/, .DS_Store). A symlink is never a payload file: a listed one, internal or
escaping, fails both modes, and an unlisted one fails --strict (R16). Neither mode runs
integrations or changes files. The external ZIP checksum authenticates the
manifest against the separately distributed digest; internal checks alone are
not a signature.

--write (maintainers, in a git checkout, right after `git add -A`) rewrites
DELIVERY_MANIFEST.json and SHA256SUMS over every git-tracked payload file as it
is on disk, keeping the manifest's descriptive fields; it refuses a tracked symlink.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath
RESERVED = ('DELIVERY_MANIFEST.json', 'SHA256SUMS')
SKIP_TOP = {'bin', '.git', '.venv', 'build'}
BUILT = {'inputs/packs/free_L8.pack', 'inputs/packs/power_L8.pack'}  # make inputs-l8 (about 7.5 GB, pinned in inputs/manifest.json)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def excluded(rel: str) -> bool:
    parts = rel.split('/')
    return (parts[0] in SKIP_TOP or rel in BUILT or '__pycache__' in parts or '.pytest_cache' in parts or rel.endswith('.pyc')
            or parts[-1] == '.DS_Store')


def safe_file(root: Path, name: str) -> Path:
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or '\\' in name or p.as_posix() != name:
        raise ValueError('Unsafe or noncanonical path: ' + repr(name))
    target = root.joinpath(*p.parts)
    if target.is_symlink() or not target.resolve().is_relative_to(root):
        raise ValueError('Symlink or escaping path: ' + repr(name))
    if not target.is_file():
        raise ValueError('Missing regular file: ' + name)
    return target


def verify(root: Path, strict: bool = False) -> dict:
    root = root.resolve()
    errors = []
    manifest_path = safe_file(root, 'DELIVERY_MANIFEST.json')
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('schema') != 'lri-c8-d3-hpc-delivery-1':
        raise ValueError('Unexpected delivery manifest schema')
    expected = {}
    expected_bytes = 0
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
            if digest(path) != sha:
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
    return dict(status='passed' if not errors else 'failed', root=str(root), strict=strict,
                payload_files_checked=len(expected), payload_bytes_checked=expected_bytes,
                manifest_and_checksum_files_checked=2, extra_files_count=len(extra),
                extra_files_preview=extra[:25], errors=errors,
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
    doc = {k: v for k, v in old.items() if k != 'files'}
    doc.update(schema='lri-c8-d3-hpc-delivery-1', created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               payload_file_count=len(rows), payload_bytes=sum(r['bytes'] for r in rows), expected_zip_file_count=len(rows) + 2, files=rows)
    (root / 'DELIVERY_MANIFEST.json').write_text(json.dumps(doc, indent=2) + '\n')
    sums = {r['path']: r['sha256'] for r in rows}
    sums['DELIVERY_MANIFEST.json'] = digest(root / 'DELIVERY_MANIFEST.json')
    (root / 'SHA256SUMS').write_text(''.join(f'{h}  {n}\n' for n, h in sorted(sums.items(), key=lambda t: t[0].encode())))
    return dict(status='written', payload_file_count=len(rows), payload_bytes=doc['payload_bytes'])


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
