#!/usr/bin/env python3
"""Check the shared eighth-order inputs (make -f public.mk test; a few seconds; standard library only).

1. inventory/inventory8_d2: sha256(MANIFEST.json) equals the external pin C8_H1_PIN (the value both eighth-order packages
   pin: LRI_C8_D2_HPC inputs/manifest.json, LRI_C8_D3_HPC's job scripts); sha256(SHA256SUMS) equals MANIFEST.json's
   sha256sums_sha256; every file SHA256SUMS lists is present at its sha256, except the four payload tars when they have
   not been fetched (reported, not failed); no unlisted file in the tree. With the payload tars in place it then runs the
   tree's own verifier (src/gen/verify_inventory.py --pin), which also checks every tar member against MEMBERS.sha256.
2. assembly/: every file HANDOFF_assembly.json delivers is present at its sha256 and byte count; the handoff itself has
   the sha256 the packages pin (f5ff6a35...).
Exit 0 when everything present is correct; 1 otherwise."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TREE = ROOT / 'inventory/inventory8_d2'
C8_H1_PIN = '46341a3c0f11d74f0cf7c08cdd685d9cf073a142160de5a0ca408e021b4ff099'
HANDOFF_SHA = 'f5ff6a353371abdc22a296d106e83af03885dfa672a25662fa59f468b9948437'
RESERVED = ('MANIFEST.json', 'SHA256SUMS')


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    problems, notes = [], []
    man = TREE / 'MANIFEST.json'
    if sha(man) != C8_H1_PIN:
        problems.append('sha256(MANIFEST.json) differs from C8_H1_PIN')
    m = json.loads(man.read_bytes())
    sums = (TREE / 'SHA256SUMS').read_bytes()
    if hashlib.sha256(sums).hexdigest() != m['sha256sums_sha256']:
        problems.append('sha256(SHA256SUMS) differs from MANIFEST.json sha256sums_sha256')
    listed = {}
    for line in sums.decode().splitlines():
        h, _, name = line.partition('  ')
        listed[name] = h
    present = {p.relative_to(TREE).as_posix() for p in TREE.rglob('*') if p.is_file() or p.is_symlink()}
    for name in sorted(present - set(listed) - set(RESERVED)):
        problems.append(f'unlisted file in the pinned tree: {name} (the tree verifier refuses it)')
    missing_payload = []
    for name, h in sorted(listed.items()):
        p = TREE / name
        if not p.is_file():
            (missing_payload if name.startswith('payload/') else problems).append(name if name.startswith('payload/') else f'missing {name}')
        elif not name.startswith('payload/') and sha(p) != h:
            problems.append(f'sha256 mismatch: {name}')
    nonpayload = len([n for n in listed if not n.startswith('payload/')])
    print(f'inventory8_d2: MANIFEST pin {C8_H1_PIN[:12]}, {nonpayload} non-payload files checked, '
          f'{4 - len(missing_payload)} of 4 payload tars present')
    if missing_payload:
        notes.append('payload tars not fetched (hosted; make -f public.mk fetch-data): ' + ', '.join(missing_payload))
    elif not problems:
        r = subprocess.run([sys.executable, '-B', str(TREE / 'src/gen/verify_inventory.py'), str(TREE), '--pin', C8_H1_PIN],
                           capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode != 0:
            problems.append('verify_inventory.py failed')
    hand = ROOT / 'assembly/HANDOFF_assembly.json'
    if sha(hand) != HANDOFF_SHA:
        problems.append('assembly/HANDOFF_assembly.json differs from the pinned handoff')
    files = json.loads(hand.read_bytes())['files']
    for f in files:
        p = ROOT / 'assembly' / f['path']
        if not p.is_file() or sha(p) != f['sha256'] or p.stat().st_size != f['bytes']:
            problems.append(f'assembly/{f["path"]}: not the delivered file')
    print(f'assembly: HANDOFF {HANDOFF_SHA[:12]}, {len(files)} delivered files checked')
    for n in notes:
        print('NOTE', n)
    for p in problems:
        print('PROBLEM', p)
    print('check', 'PASSED' if not problems else 'FAILED')
    return 0 if not problems else 1


if __name__ == '__main__':
    sys.exit(main())
