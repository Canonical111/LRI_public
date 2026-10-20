#!/usr/bin/env python3
"""Verify this reviewed patch's inputs, then version the distribution manifest.

This is for applying the source patch to the untouched 0.2.0 distribution plus
site-layer additions. It does not regenerate hashes indiscriminately from a tree.
Site-only files remain governed by the site's separate RELEASE.sha256.
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OLD_MANIFEST = 'provenance/MANIFEST_0_2_0.sha256'
PAYLOAD_MANIFEST = 'provenance/PATCH_PAYLOAD.sha256'
OLD_MANIFEST_SHA256 = '4594f46dba287d5861fd17e289f9e35b29a800414d94890a176e394fdb0ea8b2'


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()


def parse_manifest(data: bytes) -> dict[str, str]:
    result = {}
    for line in data.decode('utf8').splitlines():
        if not line:
            continue
        expected, name = line.split('  ', 1)
        p = PurePosixPath(name)
        if (len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected)
                or not name or p.is_absolute() or '..' in p.parts
                or str(p) != name or '\\' in name or name in result):
            raise ValueError(f'Invalid or duplicate manifest entry: {line!r}')
        result[name] = expected
    if not result:
        raise ValueError('Empty manifest')
    return result


def regular_file(root: Path, name: str) -> Path:
    path = root / name
    if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root.parent):
        # Explicitly forbid symlinks anywhere in a verified input's path, including
        # an installation root passed as a symlink. Resolve the root first instead.
        raise ValueError(f'Symlink in verified path: {name}')
    if not path.is_file() or not path.resolve().is_relative_to(root):
        raise ValueError(f'Not a regular file in the installation: {name}')
    return path


def rebuild(root: Path, *, expected_original_sha: str = OLD_MANIFEST_SHA256) -> int:
    root = root.resolve(strict=True)
    old_path = regular_file(root, OLD_MANIFEST)
    if digest(old_path) != expected_original_sha:
        raise ValueError('Pinned original manifest does not match')
    old = parse_manifest(old_path.read_bytes())
    payload_path = regular_file(root, PAYLOAD_MANIFEST)
    payload = parse_manifest(payload_path.read_bytes())
    if 'MANIFEST.sha256' in payload or PAYLOAD_MANIFEST in payload:
        raise ValueError('Patch payload must not list itself or the output manifest')
    expected = dict(old)
    expected.update(payload)
    expected[OLD_MANIFEST] = expected_original_sha
    expected[PAYLOAD_MANIFEST] = digest(payload_path)
    # No writes until ALL old-unmodified and declared patched/new files pass.
    for name, want in expected.items():
        found = digest(regular_file(root, name))
        if found != want:
            raise ValueError(f'Hash mismatch in patch input: {name}: {found} != {want}')
    target = root / 'MANIFEST.sha256'
    if target.is_symlink():
        raise ValueError('Refusing symlink output manifest')
    contents = ''.join(f'{expected[k]}  {k}\n' for k in sorted(expected)).encode()
    # A second invocation is idempotent; it does not bless later edits or new
    # generated artifacts. Those need the site's reviewed release workflow.
    fd, temporary = tempfile.mkstemp(prefix='.manifest-0.2.1-', dir=root)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return len(expected)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    count = rebuild(args.root)
    print(f'Verified and wrote {count} distribution entries for 0.2.1rc1. '
          'Site-only files were not modified; rebuild RELEASE.sha256 separately.')
