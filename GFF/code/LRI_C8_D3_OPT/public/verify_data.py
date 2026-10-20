#!/usr/bin/env python3
"""Check the public copy of LRI_C8_D3_OPT against the package's own SHA256SUMS (make -f public.mk verify-data).

Public-release overlay (2026-10-16); not part of the package. Run from the package folder; standard library only.
SHA256SUMS (commit d5deeb9, 31,992 lines) ships unchanged. Every listed file that is present must have its listed
SHA-256, except the files the release's privacy scrub changed (public/SCRUBBED.txt), which are counted as scrubbed.
A listed file may be absent only if it is
  hosted   in one of the four bundles of `make -f public.mk fetch-data`: the graph payloads inputs/free/ and
           inputs/power/ (179 test fixtures are in git), the delivered pilot results/pilot_20261008/, and regeneration/
           with inputs/complete_inventory_L*.json; with --require-hosted (used by fetch-data) these must be present too;
  dropped  named in public/dropped_paths.txt: the code author's derivation and calculation notes and the copy of an
           earlier condensed note, merged into the condensed note (author rule 2026-10-16: one TeX note per direction);
           they must be absent (one INFO line).
Any other missing or changed file fails. Prints a summary and exits 1 on failure.
"""
import hashlib
import re
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
HOSTED = re.compile(r'(inputs/(free|power)/|results/pilot_20261008/|regeneration/|inputs/complete_inventory_L\d+\.json$)')


def listed_paths(name):
    f = PKG / 'public' / name
    if not f.is_file():
        return set()
    return {l.split('#', 1)[0].strip() for l in f.read_text().splitlines() if l.split('#', 1)[0].strip()}


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    require_hosted = '--require-hosted' in sys.argv[1:]
    scrubbed, dropped = listed_paths('SCRUBBED.txt'), listed_paths('dropped_paths.txt')
    n = dict(verified=0, scrubbed=0, hosted_absent=0, dropped=0)
    bad, listed = [], set()
    for line in (PKG / 'SHA256SUMS').read_text().splitlines():
        digest, sep, rel = line.partition('  ')
        if not sep:
            bad.append(f'malformed line: {line[:80]}')
            continue
        listed.add(rel)
        p = PKG / rel
        if rel in dropped:
            if p.exists():
                bad.append(f'{rel}: named in public/dropped_paths.txt but present')
            else:
                n['dropped'] += 1
        elif not p.is_file():
            if HOSTED.match(rel) and not require_hosted:
                n['hosted_absent'] += 1
            else:
                bad.append(f'{rel}: missing' + (' (hosted: make -f public.mk fetch-data)' if HOSTED.match(rel) else ''))
        elif rel in scrubbed:
            n['scrubbed'] += 1
        elif sha256(p) == digest:
            n['verified'] += 1
        else:
            bad.append(f'{rel}: sha256 differs')
    bad += [f'{d}: named in public/dropped_paths.txt but not in SHA256SUMS' for d in sorted(dropped - listed)]
    for b in bad[:50]:
        print('FAIL', b)
    if dropped:
        print(f'INFO merged notes not shipped (public/dropped_paths.txt): {n["dropped"]} of {len(dropped)} absent as declared')
    payloads = sum(1 for d in ('inputs/free', 'inputs/power') if (PKG / d).is_dir() for _ in (PKG / d).rglob('G*.txt'))
    print(f'verify-data: {len(listed)} lines of SHA256SUMS; {n["verified"]} files verified, {n["scrubbed"]} scrubbed '
          f'(public/SCRUBBED.txt), {n["hosted_absent"]} hosted files not fetched, {n["dropped"]} dropped; '
          f'{payloads} graph payloads present (24173 when complete); {len(bad)} failures')
    print('verify-data:', 'FAIL' if bad else 'PASS')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
