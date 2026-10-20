#!/usr/bin/env python3
"""Restore the two parts of LRI_C8_D2_HPC that the public release does not ship twice (run: make -f public.mk setup).

1. The C7(2) reference trees. reference/{LRI_C7_d2_progress, power_mass, code, notes, verification} and the files
   reference/{Makefile, README.md, RESULT.json, SHA256SUMS, requirements.txt} are byte-identical to
   ../LRI_C7_D2_HPC/reference/ (that package at its production commit fb64c47; identical git tree hashes), so they ship
   once, there. This step checks every one of those 4,329 files against this package's own checksum list (the
   top-level SHA256SUMS, which lists each of them) and then puts it in place under reference/ as a hard link (no disk
   space; a copy where hard links are not possible, e.g. across file systems). Not a symlink: the package's own tests
   refuse symlinks (tests/check_vendored.py "no symlink is tracked anywhere in the package"; tools/verify_delivery.py
   rejects symlinked path components) and tests/vendored_isolated.py fails on any file opened outside the package.
2. The L7 graph packs inputs/packs/free_L7.pack (231 MB) and power_L7.pack (57 MB), larger than a git file may be.
   They are the selected L7 G-files of the reference trees concatenated in ascending id order. This step rebuilds them
   with the package's own reader and writer (tools/prepare_inputs.reference_items and write_pack, the code that made
   them), checks each row against inputs/inventory.json and each pack against the sha256 pinned in inputs/manifest.json,
   and installs it atomically. (The C7(2) package's own L7 packs are different files: order 8 integrates 262 more L7
   classes, so they are not reused.)

Files listed in public/NOT_SHIPPED.txt (the merged TeX notes of the reference trees, which the release does not ship) are
accepted as absent here and in the source, and reported in one INFO line; any other missing file is an error.
Idempotent: files already in place with the right content are left alone; anything else in the way is an error.
Options: --check (verify only, change nothing; exit 1 if something is missing), --copy (copy instead of hard links),
--source DIR (another location of the C7(2) reference tree). Exit 0 when everything is in place and verified."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
SHARED_DIRS = ('LRI_C7_d2_progress', 'power_mass', 'code', 'notes', 'verification')
SHARED_FILES = ('Makefile', 'README.md', 'RESULT.json', 'SHA256SUMS', 'requirements.txt')
EXPECTED_FILES = 4329
PACKS = ('free', 'power')


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def shared_listing() -> dict[str, str]:
    """reference/<shared>/... rows of the package's own SHA256SUMS (path relative to the package -> sha256)."""
    rows = {}
    for line in (PKG / 'SHA256SUMS').read_text().splitlines():
        h, sep, name = line.partition('  ')
        if not sep:
            continue
        parts = name.split('/')
        if parts[0] == 'reference' and ((len(parts) > 2 and parts[1] in SHARED_DIRS) or (len(parts) == 2 and parts[1] in SHARED_FILES)):
            rows[name] = h
    return rows


def not_shipped() -> list[str]:
    """public/NOT_SHIPPED.txt: one package-relative path, or a directory prefix ending in '/', per line."""
    f = PKG / 'public/NOT_SHIPPED.txt'
    if not f.is_file():
        return []
    return [ln.strip() for ln in f.read_text().splitlines() if ln.strip() and not ln.lstrip().startswith('#')]


def place_reference(source: Path, check: bool, copy: bool) -> tuple[int, int, list[str]]:
    rows = shared_listing()
    problems, placed, present = [], 0, 0
    ns = not_shipped()
    skipped = []
    if len(rows) != EXPECTED_FILES:
        problems.append(f'SHA256SUMS lists {len(rows)} shared reference files, expected {EXPECTED_FILES}')
    for name, h in sorted(rows.items()):
        dst = PKG / name
        if dst.is_symlink():
            problems.append(f'{name}: is a symlink (the package tests refuse symlinks); remove it and rerun')
            continue
        if dst.exists():
            if sha(dst) != h:
                problems.append(f'{name}: present but its sha256 differs from SHA256SUMS')
            else:
                present += 1
            continue
        src = source / Path(name).relative_to('reference')
        if any(name == x or (x.endswith('/') and name.startswith(x)) for x in ns):
            if src.exists():
                problems.append(f'{name}: listed in public/NOT_SHIPPED.txt but present in {source}')
            else:
                skipped.append(name)
            continue
        if not src.is_file():
            problems.append(f'{name}: missing here and in {source}')
            continue
        if sha(src) != h:
            problems.append(f'{src}: sha256 differs from this package\'s SHA256SUMS entry for {name}')
            continue
        if check:
            problems.append(f'{name}: not in place (run make -f public.mk setup)')
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if copy:
            shutil.copy2(src, dst)
        else:
            try:
                os.link(src, dst)
            except OSError:
                shutil.copy2(src, dst)
        placed += 1
    if skipped:
        print(f'INFO: {len(skipped)} files of public/NOT_SHIPPED.txt not shipped (merged TeX notes): ' + ', '.join(skipped))
    return placed, present, problems


def build_packs(check: bool) -> tuple[list[str], list[str]]:
    sys.path.insert(0, str(PKG / 'tools'))
    import prepare_inputs as prep  # the package's own input tool (reference_items, write_pack)
    man = json.loads((PKG / 'inputs/manifest.json').read_bytes())
    inv = json.loads((PKG / 'inputs/inventory.json').read_bytes())
    done, problems = [], []
    for sector in PACKS:
        rel = f'packs/{sector}_L7.pack'
        dst, want = PKG / 'inputs' / rel, man['sha256'][rel]
        if dst.is_file() and not dst.is_symlink() and sha(dst) == want:
            done.append(f'{rel} present ({want[:12]})')
            continue
        if check:
            problems.append(f'inputs/{rel}: missing or different (run make -f public.mk setup)')
            continue
        if dst.exists() or dst.is_symlink():
            problems.append(f'inputs/{rel}: exists with another sha256; remove it and rerun')
            continue
        items = prep.reference_items(sector, 7)
        fd, tmp = tempfile.mkstemp(prefix=f'.{sector}_L7.pack.', dir=dst.parent)
        os.close(fd)
        tmp = Path(tmp)
        try:
            rows = prep.write_pack(tmp, items)
            ref = {r['id']: r for r in inv[sector]['7']}
            bad = [r['id'] for r in rows if r['id'] not in ref or any(r[k] != ref[r['id']][k] for k in ('offset', 'length', 'sha256'))]
            if len(rows) != len(ref) or bad:
                raise ValueError(f'{rel}: {len(rows)} rows against {len(ref)} in inputs/inventory.json, {len(bad)} differ')
            got = sha(tmp)
            if got != want:
                raise ValueError(f'{rel}: rebuilt sha256 {got[:12]} differs from inputs/manifest.json {want[:12]}')
            os.chmod(tmp, prep.umask_mode(0o644))  # mkstemp creates 0600; packs are ordinary read-only inputs
            os.replace(tmp, dst)
            done.append(f'{rel} rebuilt from {len(rows)} reference G-files ({want[:12]}, {dst.stat().st_size} bytes)')
        except Exception as e:  # noqa: BLE001
            problems.append(str(e))
        finally:
            if tmp.exists():
                tmp.unlink()
    return done, problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--source', type=Path, default=PKG.parent / 'LRI_C7_D2_HPC' / 'reference')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--copy', action='store_true')
    a = ap.parse_args()
    placed, present, problems = place_reference(a.source.resolve(), a.check, a.copy)
    print(f'reference: {placed} placed, {present} already in place, of {EXPECTED_FILES} (source {a.source})')
    if not problems:
        done, p2 = build_packs(a.check)
        for d in done:
            print('L7 pack:', d)
        problems += p2
    for p in problems[:20]:
        print('PROBLEM:', p)
    print('setup', 'OK' if not problems else f'FAILED ({len(problems)} problems)')
    return 0 if not problems else 1


if __name__ == '__main__':
    sys.exit(main())
