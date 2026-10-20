#!/usr/bin/env python3
"""Verify a published d=3 payload tree d3_payload/ against its external pin (PLAN.md A.2 step 6, A-INV-5).

The checksum hierarchy is acyclic, as H1's (C62d's R02, D2PLAN:425-444): tar members -> MEMBERS_d3.sha256; every file
except MANIFEST_d3.json and SHA256SUMS -> SHA256SUMS; SHA256SUMS -> MANIFEST_d3.json (its sha256 and md5);
MANIFEST_d3.json -> the external pin, which lives outside the payload and the package (the A.5 gate record and its
DECISIONS log line). Four steps, in this order:
  1. sha256(MANIFEST_d3.json) equals --pin, and the manifest parses with schema c8-d3-d3-payload-1;
  2. sha256 and md5 of SHA256SUMS equal the manifest's sha256sums_sha256 and sha256sums_md5;
  3. SHA256SUMS lists every regular file of the tree except MANIFEST_d3.json and itself, exactly once, each hash
     matching; no unlisted file, no missing file, no symlink or special file;
  4. every member of every payload/*.tar is a regular file "<stem>/G<id>.txt" whose sha256 matches MEMBERS_d3.sha256,
     which lists exactly the tar members; each tar's sha256, md5, size and member count equal the manifest's.
Checksum lists are parsed from their exact bytes: UTF-8, rows "<64 hex>  <relative path>" each ending in one LF, no
control character. Standard library only.
Usage: python3 -B gen3/verify_d3.py TREE --pin <sha256 of MANIFEST_d3.json> [--output FILE]
Exit 0 when all four steps pass, 1 otherwise (2 on bad arguments).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tarfile
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g3common as c  # noqa: E402

SCHEMA = 'c8-d3-d3-payload-1'
RESERVED = ('MANIFEST_d3.json', 'SHA256SUMS')
ROW = re.compile(r'([0-9a-f]{64})  (\S.*)')
MEMBER = re.compile(r'(L[78]_(free|power))/G(0|[1-9][0-9]*)\.txt')


def safe(name: str) -> bool:
    p = PurePosixPath(name)
    return bool(name) and not p.is_absolute() and '..' not in p.parts and p.as_posix() == name and '\\' not in name


def parse_sums(data: bytes, what: str, errors: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError as exc:
        errors.append(f'{what}: not UTF-8 ({exc})')
        return out
    if text and not text.endswith('\n'):
        errors.append(f'{what}: no final newline')
    for line in ((text[:-1] if text.endswith('\n') else text).split('\n') if text else []):
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in line):
            errors.append(f'{what}: control character in row {line[:120]!r}')
            continue
        m = ROW.fullmatch(line)
        if not m or not safe(m.group(2)) or m.group(2) in out:
            errors.append(f'{what}: malformed, unsafe or duplicate row {line[:120]!r}')
            continue
        out[m.group(2)] = m.group(1)
    return out


def verify(tree: Path, pin: str) -> dict[str, list[str]]:
    tree = tree.resolve()
    steps: dict[str, list[str]] = {'1_external_pin': [], '2_manifest_pins_sha256sums': [], '3_sha256sums': [],
                                   '4_members': []}
    for name in RESERVED:
        p = tree / name
        if p.is_symlink() or not p.is_file():
            steps['1_external_pin' if name == RESERVED[0] else '2_manifest_pins_sha256sums'].append(f'missing or non-regular {name}')
    if any(steps.values()):
        return steps
    # 1
    mbytes = (tree / 'MANIFEST_d3.json').read_bytes()
    if not re.fullmatch(r'[0-9a-f]{64}', pin or ''):
        steps['1_external_pin'].append('no valid external pin (--pin <sha256 of MANIFEST_d3.json>)')
    elif hashlib.sha256(mbytes).hexdigest() != pin:
        steps['1_external_pin'].append('sha256(MANIFEST_d3.json) differs from the external pin')
    try:
        man = json.loads(mbytes)
    except ValueError as exc:
        steps['1_external_pin'].append(f'MANIFEST_d3.json does not parse: {exc}')
        man = {}
    if not isinstance(man, dict):
        steps['1_external_pin'].append('MANIFEST_d3.json is not a JSON object')
        man = {}
    if man.get('schema') != SCHEMA:
        steps['1_external_pin'].append(f'unexpected schema {man.get("schema")!r}')
    if steps['1_external_pin']:
        return steps   # a failed external pin stops here: no SHA256SUMS check, no tar is opened (no member read)
    # 2
    sums_bytes = (tree / 'SHA256SUMS').read_bytes()
    if man.get('sha256sums_sha256') != hashlib.sha256(sums_bytes).hexdigest():
        steps['2_manifest_pins_sha256sums'].append('sha256(SHA256SUMS) differs from MANIFEST_d3.json sha256sums_sha256')
    if man.get('sha256sums_md5') != hashlib.md5(sums_bytes).hexdigest():
        steps['2_manifest_pins_sha256sums'].append('md5(SHA256SUMS) differs from MANIFEST_d3.json sha256sums_md5')
    # 3
    e = steps['3_sha256sums']
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
        if c.sha256_file(tree / rel) != listed[rel]:
            e.append(f'sha256 mismatch: {rel}')
    if man.get('files_listed') != len(listed):
        e.append(f'SHA256SUMS lists {len(listed)} files, MANIFEST_d3.json says {man.get("files_listed")}')
    # 4
    e4 = steps['4_members']
    mpath = tree / 'MEMBERS_d3.sha256'
    members = parse_sums(mpath.read_bytes(), 'MEMBERS_d3.sha256', e4) if mpath.is_file() else {}
    if not mpath.is_file():
        e4.append('missing MEMBERS_d3.sha256')
    seen: dict[str, str] = {}
    tars = sorted((tree / 'payload').glob('*.tar')) if (tree / 'payload').is_dir() else []
    if not tars:
        e4.append('no payload tars')
    for tp in tars:
        stem = tp.name[:-4]
        n = 0
        try:
            with tarfile.open(tp, 'r:') as tf:
                for mem in tf:
                    mm = MEMBER.fullmatch(mem.name)
                    if not mem.isfile() or not safe(mem.name) or not mm or mm.group(1) != stem:
                        e4.append(f'{tp.name}: unsafe, misplaced or non-regular member {mem.name!r}')
                        continue
                    if mem.name in seen:
                        e4.append(f'duplicate member {mem.name}')
                    seen[mem.name] = hashlib.sha256(tf.extractfile(mem).read()).hexdigest()
                    n += 1
        except (tarfile.TarError, OSError) as exc:
            e4.append(f'{tp.name}: unreadable tar ({exc})')
        rec = (man.get('payload') or {}).get(stem)
        if not rec:
            e4.append(f'{tp.name} not recorded in MANIFEST_d3.json')
        elif (rec.get('sha256') != c.sha256_file(tp) or rec.get('md5') != c.md5_file(tp)
              or rec.get('bytes') != tp.stat().st_size or rec.get('members') != n):
            e4.append(f'{tp.name}: sha256, md5, size or member count differs from MANIFEST_d3.json')
    if set(man.get('payload') or {}) != {t.name[:-4] for t in tars}:
        e4.append('MANIFEST_d3.json payload list differs from payload/*.tar')
    for name in sorted(set(seen) ^ set(members)):
        e4.append(f'{"not in MEMBERS_d3.sha256" if name in seen else "not in any tar"}: {name}')
    for name in sorted(set(seen) & set(members)):
        if seen[name] != members[name]:
            e4.append(f'member sha256 mismatch: {name}')
    return steps


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('tree', type=Path)
    ap.add_argument('--pin', required=True, help='sha256 of MANIFEST_d3.json, from outside the tree')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args(argv)
    steps = verify(a.tree, a.pin)
    ok = not any(steps.values())
    rec = dict(schema='c8-d3-verify-d3-1', tree=str(a.tree), pin=a.pin, passed=ok,
               steps={k: dict(passed=not v, errors=v[:50], error_count=len(v)) for k, v in steps.items()})
    if a.output:
        c.write_json(a.output, rec, 'verification record')
    for k, v in steps.items():
        print(f'{k}: {"PASS" if not v else "FAIL"}' + ('' if not v else f' ({len(v)}): ' + '; '.join(v[:5])))
    print('verify_d3', 'PASSED' if ok else 'FAILED', a.tree)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
