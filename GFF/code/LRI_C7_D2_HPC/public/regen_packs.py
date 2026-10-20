#!/usr/bin/env python3
"""Rebuild inputs/packs/*.pack of LRI_C7_D2_HPC (git commit fb64c47) from the shipped reference kernels.

The ten packs (266 MiB; free_L7.pack alone is 206 MiB) are not in the public repository. Each pack is the plain
concatenation of the reference kernel files reference/LRI_C7_d2_progress/inputs/L<L>/G<id>.txt (power-free sector) or
reference/power_mass/inputs/L<L>/G<id>.txt (power sector), in the order of inputs/inventory.json, exactly as the
delivered tools/prepare_inputs.py wrote them. This script rebuilds them and checks, before a pack is published:
  - every member's offset, length and SHA-256 against inputs/inventory.json;
  - the pack's SHA-256 against inputs/manifest.json (the manifest the 2026 production pinned, sha256 75d95d52...).
A pack that already exists with the pinned SHA-256 is kept. A pack that exists with another hash is an error (it is never
overwritten). Usage, from the package folder:
    python3 public/regen_packs.py            # rebuild the missing packs (about 2 s, 266 MiB written)
    python3 public/regen_packs.py --check    # verify only: members and existing packs
Exit status 0 when all ten packs are present and verified (or, with --check, when every member verifies).
"""
import argparse, hashlib, json, os, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
SOURCE = {'free': PKG / 'reference/LRI_C7_d2_progress/inputs', 'power': PKG / 'reference/power_mass/inputs'}


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true', help='verify only; write nothing')
    a = ap.parse_args()
    manifest = json.loads((PKG / 'inputs/manifest.json').read_text())
    inventory = json.loads((PKG / 'inputs/inventory.json').read_text())
    if sha(PKG / 'inputs/inventory.json') != manifest['sha256']['inventory.json']:
        print('FAIL inputs/inventory.json does not match inputs/manifest.json'); return 1
    (PKG / 'inputs/packs').mkdir(exist_ok=True)
    failures = 0
    for sector in ('free', 'power'):
        for L in range(3, 8):
            name = f'packs/{sector}_L{L}.pack'; want = manifest['sha256'][name]; target = PKG / 'inputs' / name
            rows = inventory[sector][str(L)]
            if target.exists():
                ok = sha(target) == want
                print(f"{'PASS' if ok else 'FAIL'} {name}: present, {'pinned sha256' if ok else 'sha256 differs from inputs/manifest.json'}")
                failures += not ok
                continue
            h = hashlib.sha256(); offset = 0; bad = []
            tmp = target.with_name('.' + target.name + '.tmp')
            out = None if a.check else open(tmp, 'wb')
            try:
                for r in rows:
                    data = (SOURCE[sector] / f'L{L}' / f"G{r['id']}.txt").read_bytes()
                    if r['offset'] != offset or r['length'] != len(data) or hashlib.sha256(data).hexdigest() != r['sha256']:
                        bad.append(r['id'])
                    h.update(data); offset += len(data)
                    if out: out.write(data)
            finally:
                if out: out.close()
            ok = not bad and h.hexdigest() == want
            if a.check:
                print(f"{'PASS' if ok else 'FAIL'} {name}: {len(rows)} members verify, concatenation has the pinned sha256" if ok else
                      f"FAIL {name}: {len(bad)} members differ" + (f' (e.g. G{bad[0]})' if bad else ', pack sha256 differs'))
            elif ok:
                os.replace(tmp, target)
                print(f'PASS {name}: rebuilt from {len(rows)} reference kernels, {offset} bytes, pinned sha256 {want[:12]}')
            else:
                tmp.unlink(missing_ok=True)
                print(f"FAIL {name}: not written; {len(bad)} members differ" + (f' (e.g. G{bad[0]})' if bad else ', pack sha256 differs'))
            failures += not ok
    print(f"{'all ten packs verified' if not failures else f'{failures} of ten packs FAILED'}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
