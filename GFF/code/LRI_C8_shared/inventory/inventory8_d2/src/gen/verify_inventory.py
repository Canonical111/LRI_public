#!/usr/bin/env python3
"""Verify a copy of the frozen inventory tree inventory8_d2/ (PLAN.md R02, A-INV-5). Standard library only.

Four steps, in the order of the acyclic checksum hierarchy:
  1. SHA256SUMS: well-formed, lists neither MANIFEST.json nor itself, lists every other regular file of the tree
     exactly once (no unlisted file, no symlink or special file), and every listed hash matches
     (the equivalent of `sha256sum -c SHA256SUMS` plus completeness);
  2. sha256(SHA256SUMS) equals MANIFEST.json's sha256sums_sha256;
  3. every G-file member of every payload tar matches MEMBERS.sha256, which lists exactly the tar members; the tars'
     sha256, md5, sizes and member counts equal MANIFEST.json's;
  4. sha256(MANIFEST.json) equals the external pin given with --pin.
Every hash is taken over the exact bytes of a file, and the two checksum lists are parsed from those bytes: UTF-8,
rows "<64 hex>  <relative path>" each ending in one LF, no CR or other control character. So a one-byte change
anywhere (a newline turned into CR included) fails a step.
Usage: python3 -B gen/verify_inventory.py TREE --pin <sha256 of MANIFEST.json> [--output FILE]
Exit status 0 when all four steps pass, 1 otherwise."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tarfile
from pathlib import Path, PurePosixPath

RESERVED = ('MANIFEST.json', 'SHA256SUMS')
ROW = re.compile(r'([0-9a-f]{64})  (\S.*)')


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


def safe(name: str) -> bool:
    p = PurePosixPath(name)
    return bool(name) and not p.is_absolute() and '..' not in p.parts and p.as_posix() == name and '\\' not in name


def parse_sums(data: bytes, what: str, errors: list[str]) -> dict[str, str]:
    """Rows of a checksum list, parsed from its exact bytes (never through universal-newline text mode, which would
    read CR or CRLF as LF): UTF-8, every row '<64 hex>  <relative path>' ending in one LF, no control character."""
    out: dict[str, str] = {}
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError as exc:
        errors.append(f'{what}: not UTF-8 ({exc})')
        return out
    if text and not text.endswith('\n'):
        errors.append(f'{what}: no final newline')
    for line in (text[:-1] if text.endswith('\n') else text).split('\n') if text else []:
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in line):
            errors.append(f'{what}: control character (CR, tab, ...) in row {line[:120]!r}')
            continue
        m = ROW.fullmatch(line)
        if not m or not safe(m.group(2)) or m.group(2) in out:
            errors.append(f'{what}: malformed, unsafe or duplicate row {line[:120]!r}')
            continue
        out[m.group(2)] = m.group(1)
    return out


def verify(tree: Path, pin: str) -> dict:
    tree = tree.resolve()
    steps: dict[str, list[str]] = {'1_sha256sums': [], '2_manifest_pins_sha256sums': [], '3_members': [],
                                   '4_external_pin': []}
    for name in RESERVED:
        p = tree / name
        if p.is_symlink() or not p.is_file():
            steps['1_sha256sums'].append(f'missing or non-regular {name}')
    if steps['1_sha256sums']:
        return steps
    # 1
    e = steps['1_sha256sums']
    sums_bytes = (tree / 'SHA256SUMS').read_bytes()
    listed = parse_sums(sums_bytes, 'SHA256SUMS', e)
    for name in RESERVED:
        if name in listed:
            e.append(f'SHA256SUMS lists {name}')
    present = set()
    for p in tree.rglob('*'):
        rel = p.relative_to(tree).as_posix()
        if p.is_symlink() or not (p.is_file() or p.is_dir()):
            e.append(f'symlink or special file in the tree: {rel}')
        elif p.is_file() and rel not in RESERVED:
            present.add(rel)
    for rel in sorted(present - set(listed)):
        e.append(f'unlisted file: {rel}')
    for rel in sorted(set(listed) - present - set(RESERVED)):
        e.append(f'listed file missing: {rel}')
    for rel in sorted(set(listed) & present):
        if sha256_file(tree / rel) != listed[rel]:
            e.append(f'sha256 mismatch: {rel}')
    # 2
    try:
        man = json.loads((tree / 'MANIFEST.json').read_bytes())
    except ValueError as exc:
        steps['2_manifest_pins_sha256sums'].append(f'MANIFEST.json does not parse: {exc}')
        man = {}
    if not isinstance(man, dict):
        steps['2_manifest_pins_sha256sums'].append('MANIFEST.json is not a JSON object')
        man = {}
    if man.get('sha256sums_sha256') != hashlib.sha256(sums_bytes).hexdigest():
        steps['2_manifest_pins_sha256sums'].append('sha256(SHA256SUMS) differs from MANIFEST.json sha256sums_sha256')
    if man.get('schema') != 'c8-inventory-d2-1':
        steps['2_manifest_pins_sha256sums'].append(f'unexpected schema {man.get("schema")!r}')
    # 3
    e3 = steps['3_members']
    mpath = tree / 'MEMBERS.sha256'
    members = parse_sums(mpath.read_bytes(), 'MEMBERS.sha256', e3) if mpath.is_file() else {}
    if not mpath.is_file():
        e3.append('missing MEMBERS.sha256')
    seen: dict[str, str] = {}
    tars = sorted((tree / 'payload').glob('*.tar')) if (tree / 'payload').is_dir() else []
    if not tars:
        e3.append('no payload tars')
    for tp in tars:
        stem = tp.name[:-4]
        n = 0
        try:
            with tarfile.open(tp, 'r:') as tf:
                for m in tf:
                    if not m.isfile() or not safe(m.name) or not m.name.startswith(stem + '/'):
                        e3.append(f'{tp.name}: unsafe, misplaced or non-regular member {m.name!r}')
                        continue
                    if m.name in seen:
                        e3.append(f'duplicate member {m.name}')
                    seen[m.name] = hashlib.sha256(tf.extractfile(m).read()).hexdigest()
                    n += 1
        except (tarfile.TarError, OSError) as exc:
            e3.append(f'{tp.name}: unreadable tar ({exc})')
        rec = man.get('payload', {}).get(stem)
        if not rec:
            e3.append(f'{tp.name} not recorded in MANIFEST.json')
        elif (rec.get('sha256') != sha256_file(tp) or rec.get('md5') != md5_file(tp)
              or rec.get('bytes') != tp.stat().st_size or rec.get('members') != n):
            e3.append(f'{tp.name}: sha256, md5, size or member count differs from MANIFEST.json')
    if set(man.get('payload', {})) != {t.name[:-4] for t in tars}:
        e3.append('MANIFEST.json payload list differs from payload/*.tar')
    for name in sorted(set(seen) ^ set(members)):
        e3.append(f'{"not in MEMBERS.sha256" if name in seen else "not in any tar"}: {name}')
    for name in sorted(set(seen) & set(members)):
        if seen[name] != members[name]:
            e3.append(f'member sha256 mismatch: {name}')
    # 4
    if not re.fullmatch(r'[0-9a-f]{64}', pin or ''):
        steps['4_external_pin'].append('no valid external pin (--pin <sha256 of MANIFEST.json>)')
    elif sha256_file(tree / 'MANIFEST.json') != pin:
        steps['4_external_pin'].append('sha256(MANIFEST.json) differs from the external pin')
    return steps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('tree', type=Path)
    ap.add_argument('--pin', required=True, help='sha256 of MANIFEST.json, from outside the tree')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    steps = verify(a.tree, a.pin)
    ok = not any(steps.values())
    rec = dict(schema='c8-d2-verify-inventory-1', tree=str(a.tree), pin=a.pin, passed=ok,
               steps={k: dict(passed=not v, errors=v[:50], error_count=len(v)) for k, v in steps.items()})
    if a.output:
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    for k, v in steps.items():
        print(f'{k}: {"PASS" if not v else "FAIL"}' + ('' if not v else f' ({len(v)}): ' + '; '.join(v[:5])))
    print('verify_inventory', 'PASSED' if ok else 'FAILED', a.tree)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
