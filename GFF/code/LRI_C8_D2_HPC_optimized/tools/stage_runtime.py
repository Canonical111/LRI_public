#!/usr/bin/env python3
"""Stage a verified job runtime; optionally reuse a locked node-local pack cache.

Without --pack-cache this preserves the original full-pack copy behaviour.
With it, a content-addressed pack is copied and SHA-256 checked once per node
and user. Cache hits verify a stat-bound receipt; every graph member is still
SHA-256 checked by production.stage_graphs before native work. Cache entries
are immutable to jobs and are never removed by job-stage cleanup. The cache
must be on genuinely node-local storage, in a directory owned by this user
and not writable by other users. --reverify-cache forces a full hash on hits.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile

from common import ROOT, checked, digest, load
from production import verify_base, exe_for, group_of

CACHE_SCHEMA = 'c8-d2-local-pack-cache-1'


def file_identity(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError('Pack cache entry must be a regular file owned by this user')
    return {key: getattr(info, key) for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')}


def atomic_json(path, data):
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump(data, output, sort_keys=True, allow_nan=False)
            output.write('\n'); output.flush(); os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def cached_pack(source, checksum, cache_root, reverify=False):
    """Return a verified immutable pack and whether a new copy was needed.

    flock serializes publishers of the same content on one node. Publication
    uses a private temporary file plus atomic replace; interrupted copies are
    never mistaken for a usable pack. The lock is automatically released if a
    process or node fails. A changed cache entry is rehashed before reuse.
    """
    if not re.fullmatch(r'[0-9a-f]{64}', checksum):
        raise ValueError('Invalid pack SHA-256')
    cache_root = Path(cache_root).absolute()
    cache_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = cache_root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
        raise ValueError('Pack cache must be a real directory owned by this user, without group/other write permission')
    pack = cache_root / (checksum + '.pack')
    receipt = cache_root / (checksum + '.json')
    lock_path = cache_root / (checksum + '.lock')
    flags = os.O_CREAT | os.O_RDWR | getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_NOFOLLOW', 0)
    lock_fd = os.open(lock_path, flags, 0o600)
    try:
        lock_info = os.fstat(lock_fd)
        if not stat.S_ISREG(lock_info.st_mode) or lock_info.st_uid != os.getuid() or stat.S_IMODE(lock_info.st_mode) & 0o022:
            raise ValueError('Unsafe pack-cache lock file')
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        copied = False
        if pack.exists() or pack.is_symlink():
            identity = file_identity(pack)
            try:
                metadata = load(receipt)
            except (OSError, ValueError):
                metadata = None
            valid_receipt = (isinstance(metadata, dict) and metadata.get('schema') == CACHE_SCHEMA and
                             metadata.get('sha256') == checksum and metadata.get('identity') == identity)
            if valid_receipt and not reverify:
                return pack, copied
            if digest(pack) == checksum:
                os.chmod(pack, 0o444)
                atomic_json(receipt, {'schema': CACHE_SCHEMA, 'sha256': checksum, 'identity': file_identity(pack)})
                return pack, copied
        fd, temporary = tempfile.mkstemp(prefix=checksum + '.copy_', dir=cache_root)
        os.close(fd)
        try:
            shutil.copyfile(source, temporary)
            checked(Path(temporary), checksum)
            with open(temporary, 'rb') as stream:
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o444)
            os.replace(temporary, pack)
            copied = True
            atomic_json(receipt, {'schema': CACHE_SCHEMA, 'sha256': checksum, 'identity': file_identity(pack)})
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return pack, copied
    finally:
        os.close(lock_fd)


def stage(run, destination, index, pack_cache=None, reverify_cache=False):
    run = Path(run).resolve()
    m, im, mh, _ = verify_base(run)
    if not 0 <= index < len(m['jobs']):
        raise ValueError('Job index outside plan')
    job = m['jobs'][index]
    _, cfg = group_of(run, m, job['group'])
    out = Path(destination).resolve()
    if pack_cache is not None:
        cache_path = Path(pack_cache).resolve()
        if cache_path == out or out in cache_path.parents:
            raise ValueError('Reusable pack cache must be outside the job-private staging directory')
    if out.exists() and any(out.iterdir()):
        raise FileExistsError('Use a new or empty staging directory')
    for directory in ('bin', 'tools', 'inputs/packs'):
        (out / directory).mkdir(parents=True, exist_ok=True)
    for path in (ROOT / 'tools').iterdir():
        if path.is_file():
            shutil.copy2(path, out / 'tools' / path.name)
    exe = exe_for(m['backend'])
    shutil.copy2(exe, out / 'bin' / exe.name)
    checked(out / 'bin' / exe.name, m['executable_sha256'])
    for name in ('manifest.json', 'inventory.json', 'two_loop.json', 'gamma_d2_8.txt'):
        shutil.copy2(ROOT / 'inputs' / name, out / 'inputs' / name)
        if name != 'manifest.json':
            checked(out / 'inputs' / name, im['sha256'][name])
    checked(out / 'inputs/manifest.json', m['inputs_manifest_sha256'])
    relative = f'packs/{cfg["sector"]}_L{cfg["L"]}.pack'
    if pack_cache is None:
        shutil.copy2(ROOT / 'inputs' / relative, out / 'inputs' / relative)
        checked(out / 'inputs' / relative, im['sha256'][relative])
        cache_info = None
    else:
        pack, copied = cached_pack(ROOT / 'inputs' / relative, im['sha256'][relative], pack_cache, reverify_cache)
        # The link avoids a second full pack per array element. Removing this
        # private stage unlinks it and never removes the shared cache entry.
        (out / 'inputs' / relative).symlink_to(pack)
        cache_info = {'path': str(pack), 'copied': copied, 'sha256': im['sha256'][relative],
                      'cache_hit_verification': 'full hash' if reverify_cache else 'stat-bound full-hash receipt; per-member hashes on use'}
    atomic_json(out / 'staging.json', {'manifest_sha256': mh, 'group': job['group'], 'pack_cache': cache_info})
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--index', type=int, required=True)
    parser.add_argument('--pack-cache', type=Path, help='Reusable user-owned node-local directory; do not put this on the shared project filesystem')
    parser.add_argument('--reverify-cache', action='store_true', help='Force a full SHA-256 of cached packs before reuse')
    args = parser.parse_args()
    print(stage(args.run, args.destination, args.index, args.pack_cache, args.reverify_cache))


if __name__ == '__main__':
    main()
