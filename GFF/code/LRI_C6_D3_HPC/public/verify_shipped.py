#!/usr/bin/env python3
"""Verify the public copy of LRI_C6_D3_HPC against the package's own SHA256SUMS_HPC.json (commit 1c6dfb3).

Public-release overlay (2026-10-13). The public copy is pruned, so `tools/checksums.py verify` (and `make check-delivery`)
would report the pruned files as missing. This check is `verify --ignore-missing`, restricted to a documented list:
  * every listed file that is present must have its listed SHA-256 (files named in public/SCRUBBED.txt, if that file
    exists, are reported as scrubbed for publication instead);
  * a listed file may be absent only if public/NOT_SHIPPED.txt names it (dropped from the public copy), or if
    public/dropped_paths.txt names it: the TeX notes of the shared reference/ tree (the link to
    ../LRI_C6_D2_HPC/reference), which that package's export leaves out because they are merged into the condensed
    note (author rule 2026-10-16: one TeX note per direction); a path named there must be absent (one INFO line);
  * every file named in public/REFERENCE_REQUIRED.txt must be present with its listed hash (the tests and the replay
    read them);
  * a file that is not listed must be part of the overlay (public.mk, public/) or a build or run product.
Prints a summary and exits 1 on any failure. Runs in about 2 s.
"""
from __future__ import annotations
import hashlib, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ('public.mk', 'public/')
PRODUCTS = ('bin/c6_integrate', '.work/', '.venv/', 'runs/')


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def lines(name: str) -> set[str]:
    p = ROOT / 'public' / name
    return {l.strip() for l in p.read_text().splitlines() if l.strip() and not l.startswith('#')} if p.exists() else set()


def present_files() -> set[str]:
    out = set()
    for d, dirs, files in os.walk(ROOT, followlinks=False):
        rel = Path(d).relative_to(ROOT)
        dirs[:] = [x for x in dirs if x not in ('.git', '__pycache__')]
        for f in files:
            if f == '.DS_Store' or f.endswith('.pyc'):
                continue
            out.add(str(rel / f) if str(rel) != '.' else f)
    return out


def main() -> int:
    listed = json.loads((ROOT / 'SHA256SUMS_HPC.json').read_text())['files']
    not_shipped, required, scrubbed = lines('NOT_SHIPPED.txt'), lines('REFERENCE_REQUIRED.txt'), lines('SCRUBBED.txt')
    dropped = lines('dropped_paths.txt')
    bad, ok, skipped, ref_absent, scrub = [], 0, 0, 0, []
    for f, h in listed.items():
        p = ROOT / f
        if f in dropped:
            if p.is_file():
                bad.append(f'named in public/dropped_paths.txt but present: {f}')
            else:
                ref_absent += 1
        elif p.is_file():
            if f in not_shipped:
                bad.append(f'declared not shipped but present: {f}')
            elif sha256(p) == h:
                ok += 1
            elif f in scrubbed:
                scrub.append(f)
            else:
                bad.append(f'changed: {f}')
        elif f in not_shipped:
            skipped += 1
        else:
            bad.append(f'missing: {f}' + (' (needed by the tests or the replay; is ../LRI_C6_D2_HPC/reference present?)' if f in required else ''))
    for f in sorted(required - set(listed)):
        bad.append(f'REFERENCE_REQUIRED names an unlisted file: {f}')
    for f in sorted(not_shipped - set(listed)):
        bad.append(f'NOT_SHIPPED names an unlisted file: {f}')
    for f in sorted(dropped - set(listed)):
        bad.append(f'dropped_paths.txt names an unlisted file: {f}')
    for f in sorted(dropped & (required | not_shipped)):
        bad.append(f'dropped_paths.txt names a file that REFERENCE_REQUIRED or NOT_SHIPPED also names: {f}')
    for f in sorted(present_files() - set(listed) - {'SHA256SUMS_HPC.json'}):
        if not f.startswith(OVERLAY) and not f.startswith(PRODUCTS) and f != 'reference':
            bad.append(f'unlisted file: {f}')
    if not (ROOT / 'reference').exists():
        bad.append('reference/ is missing: run `make -f public.mk setup` (needs ../LRI_C6_D2_HPC/reference)')
    if dropped:
        print(f'INFO merged notes of the shared reference/ tree not shipped (public/dropped_paths.txt): {ref_absent} of '
              f'{len(dropped)} absent as declared')
    for b in bad[:60]:
        print('FAIL', b)
    if len(bad) > 60:
        print(f'FAIL ... {len(bad) - 60} more')
    print(f'SHA256SUMS_HPC.json: {len(listed)} listed; {ok} verified; {len(scrub)} scrubbed for publication; '
          f'{skipped} not shipped (public/NOT_SHIPPED.txt); {ref_absent} merged notes not shipped '
          f'(public/dropped_paths.txt); {len(bad)} failures')
    print('VERIFY ' + ('PASSED' if not bad else 'FAILED'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
