#!/usr/bin/env python3
"""Verify the package's own checksum lists in the public release (make -f public.mk verify-lists; run after setup).

SHA256SUMS (10,871 files) and DELIVERY_MANIFEST.json (path, bytes, sha256 of every file) ship verbatim. The public
release replaced user names, cluster paths, node names and session ids by tokens in some files that only these lists name
(the release's SCRUBBED-list mode); those files are listed one path per line in public/SCRUBBED.txt and are checked here
for presence only. Files the release does not ship may be listed in public/NOT_SHIPPED.txt (one path or directory prefix
ending in '/' per line); they must be absent. (The release prunes the lines of unshipped files from both lists instead,
when it can; then NOT_SHIPPED.txt is not needed.) Every other listed file must have its listed sha256 (and
DELIVERY_MANIFEST.json's byte count).
The files `setup` restores (the C7(2) reference trees, the L7 packs) are checked like the others, so run setup first.
Exit 0 when every listed file is present and every non-scrubbed file matches; 1 otherwise."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    scrubbed_file = PKG / 'public/SCRUBBED.txt'
    scrubbed = set()
    if scrubbed_file.is_file():
        scrubbed = {ln.strip() for ln in scrubbed_file.read_text().splitlines() if ln.strip() and not ln.startswith('#')}
    ns_file = PKG / 'public/NOT_SHIPPED.txt'
    not_shipped = []
    if ns_file.is_file():
        not_shipped = [ln.strip() for ln in ns_file.read_text().splitlines() if ln.strip() and not ln.startswith('#')]
    absent = lambda n: any(n == x or (x.endswith('/') and n.startswith(x)) for x in not_shipped)  # noqa: E731
    problems, checked, skipped, gone = [], 0, 0, 0
    sums = {}
    for line in (PKG / 'SHA256SUMS').read_text().splitlines():
        h, sep, name = line.partition('  ')
        if sep:
            sums[name] = h
    dm = json.loads((PKG / 'DELIVERY_MANIFEST.json').read_bytes())
    files = {f['path']: f for f in dm['files']}
    for name in sorted(set(sums) | set(files)):
        p = PKG / name
        if absent(name):
            if p.exists():
                problems.append(f'listed in public/NOT_SHIPPED.txt but present: {name}')
            gone += 1
            continue
        if not p.is_file():
            problems.append(f'missing: {name}')
            continue
        if name in scrubbed:
            skipped += 1
            continue
        h = sha(p)
        if name in sums and sums[name] != h:
            problems.append(f'sha256 differs from SHA256SUMS: {name}')
        if name in files and (files[name]['sha256'] != h or files[name]['bytes'] != p.stat().st_size):
            problems.append(f'differs from DELIVERY_MANIFEST.json: {name}')
        checked += 1
    unknown = sorted(scrubbed - set(sums) - set(files))
    print(f'SHA256SUMS {len(sums)} entries, DELIVERY_MANIFEST.json {len(files)} files: {checked} verified, '
          f'{skipped} scrubbed for the release (public/SCRUBBED.txt; presence only), {gone} not shipped (public/NOT_SHIPPED.txt)')
    if unknown:
        print(f'note: {len(unknown)} SCRUBBED.txt entries are not in the lists (e.g. {unknown[0]})')
    for p in problems[:20]:
        print('PROBLEM', p)
    print('verify-lists', 'PASSED' if not problems else f'FAILED ({len(problems)} problems)')
    return 0 if not problems else 1


if __name__ == '__main__':
    sys.exit(main())
