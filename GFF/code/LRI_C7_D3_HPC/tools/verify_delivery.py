#!/usr/bin/env python3
"""Verify the delivered file inventory and SHA-256 checksums (standard library only).

Run before rebuilding. Default mode permits additional locally generated files;
--strict requires an exact file inventory. Neither mode runs integrations or
changes files. The external ZIP checksum authenticates the manifest against the
separately distributed digest; internal checks alone are not a signature.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


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
    if manifest.get('schema') != 'lri-c7-d3-hpc-delivery-1':
        raise ValueError('Unexpected delivery manifest schema')
    expected = {}
    expected_bytes = 0
    for row in manifest['files']:
        name, sha = row['path'], row['sha256']
        if name in expected or name in ('DELIVERY_MANIFEST.json', 'SHA256SUMS'):
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
    known = set(expected) | {'DELIVERY_MANIFEST.json', 'SHA256SUMS'}
    extra = sorted(p.relative_to(root).as_posix() for p in root.rglob('*')
                   if (p.is_file() or p.is_symlink()) and p.relative_to(root).as_posix() not in known)
    if strict and extra:
        errors.append(f'{len(extra)} unexpected files in strict mode')
    return dict(status='passed' if not errors else 'failed', root=str(root), strict=strict,
                payload_files_checked=len(expected), payload_bytes_checked=expected_bytes,
                manifest_and_checksum_files_checked=2, extra_files_count=len(extra),
                extra_files_preview=extra[:25], errors=errors,
                integrations_rerun=False, files_modified=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument('--strict', action='store_true')
    args = ap.parse_args()
    try:
        report = verify(args.root, args.strict)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        report = dict(status='failed', errors=[str(exc)])
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'passed' else 1

if __name__ == '__main__':
    sys.exit(main())
