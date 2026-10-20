#!/usr/bin/env python3
"""Restore the d=3 kernel inputs of LRI_C7_D3_HPC that git carries in compressed form (make -f public.mk setup).

Run from the package folder (GFF/code/LRI_C7_D3_HPC). Standard library only; idempotent.

1. inputs/packs/*.pack (10 files, 321.8 MB) are unpacked from public/kernels/inputs_packs.tar.gz unless already present.
   Each pack must match the sha256 in inputs/manifest.json, the inputs manifest that the run1 manifest binds
   (inputs_manifest_sha256 5048b336...).
2. reference/inputs/{free,power}/L3..L7/G<id>.txt (3,511 graph payloads of the previous calculation, 323 MB) are the
   members of those packs: they are cut out at the offsets of inputs/inventory.json. Each must match its sha256 in
   inputs/inventory.json and in the delivered SHA256SUMS (the review found all 3,511 members byte-identical to
   reference/inputs).
The restored files are build products of the checkout (git-ignored). Exits 1 on any mismatch.
"""
from __future__ import annotations
import hashlib, json, sys, tarfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
TARBALL = PKG / 'public/kernels/inputs_packs.tar.gz'


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    im = json.loads((PKG / 'inputs/manifest.json').read_text())
    packs = sorted(k for k in im['sha256'] if k.startswith('packs/'))
    missing = [k for k in packs if not (PKG / 'inputs' / k).exists()]
    if missing:
        if not TARBALL.exists():
            print(f'setup: {TARBALL.relative_to(PKG)} is missing and so are inputs/{missing[0]} ...', file=sys.stderr)
            return 1
        with tarfile.open(TARBALL, 'r:gz') as t:
            names = t.getnames()
            want = {'inputs/' + k for k in packs}
            if not set(names) <= want | {'inputs', 'inputs/packs'} or not want <= set(names):
                print(f'setup: unexpected members in {TARBALL.name}: {sorted(set(names) ^ want)[:5]}', file=sys.stderr)
                return 1
            for k in missing:
                m = t.getmember('inputs/' + k)
                if not m.isfile():
                    print(f'setup: {m.name} is not a regular file', file=sys.stderr)
                    return 1
                dest = PKG / 'inputs' / k
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_name(dest.name + '.part')
                with t.extractfile(m) as src, tmp.open('wb') as out:
                    for b in iter(lambda: src.read(1 << 20), b''):
                        out.write(b)
                tmp.replace(dest)
        print(f'setup: unpacked {len(missing)} packs from {TARBALL.relative_to(PKG)}')
    bad = [k for k in packs if sha(PKG / 'inputs' / k) != im['sha256'][k]]
    if bad:
        print(f'setup: FAIL, packs differ from inputs/manifest.json: {bad}', file=sys.stderr)
        return 1
    print(f'setup: {len(packs)} packs match inputs/manifest.json')

    inv = json.loads((PKG / 'inputs/inventory.json').read_text())
    sums = {}
    for line in (PKG / 'SHA256SUMS').read_text().splitlines():
        h, _, name = line.partition('  ')
        sums[name] = h
    written = checked = 0
    errors = []
    for sector, loops in inv.items():
        for L, rows in loops.items():
            data = (PKG / f'inputs/packs/{sector}_L{L}.pack').read_bytes()
            for r in rows:
                rel = f'reference/inputs/{sector}/L{L}/G{r["id"]}.txt'
                payload = data[r['offset']:r['offset'] + r['length']]
                h = hashlib.sha256(payload).hexdigest()
                if h != r['sha256'] or sums.get(rel) != h:
                    errors.append(rel)
                    continue
                dest = PKG / rel
                if dest.exists():
                    if sha(dest) != h:
                        errors.append(rel + ' (existing file differs)')
                    checked += 1
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_name(dest.name + '.part')
                tmp.write_bytes(payload)
                tmp.replace(dest)
                written += 1
    if errors:
        print(f'setup: FAIL, {len(errors)} graph payloads do not match inputs/inventory.json and SHA256SUMS: {errors[:5]}', file=sys.stderr)
        return 1
    print(f'setup: {written + checked} graph payloads in reference/inputs ({written} written, {checked} already present), '
          'all matching inputs/inventory.json and SHA256SUMS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
