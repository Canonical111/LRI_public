#!/usr/bin/env python3
"""Attach the unchanged C8 graph packs to this separate optimized source tree.

Usage: python3 tools/attach_inputs.py ../LRI_C8_D2_HPC/inputs
The complete source and destination input manifests must agree. Every source
pack is hashed before any new link is installed. Existing files are retained
only when their content already matches; this command never replaces them.
"""
from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

from common import ROOT, checked, digest, read_verified, umask_mode


def attach(source: Path, destination: Path, mode: str = 'symlink') -> dict:
    source = source.resolve()
    destination = destination.resolve()
    if mode not in ('symlink', 'hardlink', 'copy'):
        raise ValueError('mode must be symlink, hardlink, or copy')
    manifest_sha = digest(destination / 'manifest.json')
    manifest = read_verified(destination / 'manifest.json', manifest_sha)
    checked(source / 'manifest.json', manifest_sha)
    if manifest.get('schema') != 'c8-d2-hpc-inputs-1' or manifest.get('order') != 8:
        raise ValueError('The source must contain the complete C8 input packs')
    packs = []
    for name, sha in manifest['sha256'].items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe input manifest path')
        if relative.parts[0] != 'packs':
            checked(destination / relative, sha)
            continue
        src, dst = source / relative, destination / relative
        checked(src, sha)
        exists = dst.exists() or dst.is_symlink()
        if exists:
            checked(dst, sha)
        packs.append((relative, src, dst, sha, exists))
    if len(packs) != 12:
        raise ValueError('Expected exactly twelve unchanged graph packs')
    created, retained = [], []
    for relative, src, dst, sha, exists in packs:
        if exists:
            retained.append(relative.as_posix())
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if mode == 'symlink':
            # Creation itself is atomic and refuses an existing destination.
            dst.symlink_to(os.path.relpath(src, dst.parent))
        elif mode == 'hardlink':
            os.link(src, dst)
        else:
            fd, tmp = tempfile.mkstemp(prefix='c8_pack_', dir=dst.parent)
            try:
                os.fchmod(fd, umask_mode())
                with os.fdopen(fd, 'wb') as out, src.open('rb') as inp:
                    shutil.copyfileobj(inp, out, 1 << 20)
                    out.flush()
                    os.fsync(out.fileno())
                checked(Path(tmp), sha)
                os.link(tmp, dst)
            finally:
                os.unlink(tmp)
        created.append(relative.as_posix())
    return {'source_inputs': str(source), 'destination_inputs': str(destination),
            'mode': mode, 'created': created, 'retained': retained,
            'verified_packs': len(packs)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_inputs', type=Path)
    parser.add_argument('--mode', choices=('symlink', 'hardlink', 'copy'), default='symlink')
    args = parser.parse_args()
    import json
    print(json.dumps(attach(args.source_inputs, ROOT / 'inputs', args.mode), indent=2))


if __name__ == '__main__':
    main()
