#!/usr/bin/env python3
"""Verify the public tree of LRI_C7_D3_HPC against the delivered checksum lists (make -f public.mk checksums).

Run from the package folder. Standard library only.

The production commit's SHA256SUMS lists all 4,980 files of the delivery (it is shipped verbatim, never pruned or
regenerated); reference/DELIVERY_MANIFEST.json lists the files of the previous calculation. Every listed file that is
present must match. Absent files are classified, and only an absent file of the "git" class is a failure:
  setup    inputs/packs/*.pack and reference/inputs/{free,power}/L*/G*.txt, restored by `make -f public.mk setup`
  hosted   reference/records/**, restored by `make -f public.mk records` after `make -f public.mk fetch-data`
  dropped  benchmarks/** except the eight delivered validation records docs/NUMERICS.md cites, and experiments/**
           (delivery timings, profiles and a design probe that never ran in production)
  merged   the paths of public/dropped_paths.txt: reference/reference/C7_d2_complete.tex, a copy of the earlier d = 2
           method note, merged into the condensed note (author rule 2026-10-16: one TeX note per direction); it must
           be absent (one INFO row), and the lists keep their lines for it
  git      everything else: shipped in git, must be present
With --require-hosted (used by `make -f public.mk records`) an absent hosted file is a failure too.
Prints a PASS/FAIL table and exits 1 on FAIL.
"""
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# The delivered validation records that docs/NUMERICS.md cites; the timing and memory benchmarks are not shipped.
KEPT_BENCHMARKS = {'full_validation.json', 'input_preparation.json', 'kernel_selection.json', 'point_checks.json',
                   'reassembled.json', 'reference_preservation.json', 'staging.json', 'workflow.json'}


_DF = PKG / 'public/dropped_paths.txt'
DROPPED = {l.split('#', 1)[0].strip() for l in _DF.read_text().splitlines() if l.split('#', 1)[0].strip()} \
    if _DF.is_file() else set()


def cls(rel: str) -> str:
    if rel in DROPPED:
        return 'merged'
    if rel.startswith('inputs/packs/') or re.fullmatch(r'reference/inputs/(free|power)/L[3-7]/G\d+\.txt', rel):
        return 'setup'
    if rel.startswith('reference/records/'):
        return 'hosted'
    if rel.startswith('benchmarks/') and rel[len('benchmarks/'):] in KEPT_BENCHMARKS:
        return 'git'
    if rel.startswith(('benchmarks/', 'experiments/')):
        return 'dropped'
    return 'git'


REQUIRED = {'git'}
# Files the public export's privacy scrub changed (public/SCRUBBED.txt: one package-relative path per line, '#'
# comments). They are bound only by checksum lists, so a listed file is counted as verified-scrubbed, not compared.
_SF = PKG / 'public/SCRUBBED.txt'
SCRUBBED = {l.split('#', 1)[0].strip() for l in _SF.read_text().splitlines() if l.split('#', 1)[0].strip()} \
    if _SF.is_file() else set()


def verify(listing: dict, base: Path, prefix: str, stats: dict, bad: list) -> None:
    for rel, h in listing.items():
        full = prefix + rel
        p = base / rel
        c = cls(full)
        s = stats.setdefault(c, {'verified': 0, 'absent': 0})
        if p.is_file():
            if c == 'merged':
                bad.append(f'{full}: named in public/dropped_paths.txt but present')
            elif full not in SCRUBBED and sha(p) != h:
                bad.append(f'{full}: sha256 differs')
            s['verified'] += 1
        else:
            s['absent'] += 1
            if c in REQUIRED:
                bad.append(f'{full}: missing')


def main() -> int:
    if '--require-hosted' in sys.argv[1:]:
        REQUIRED.add('hosted')
    stats, bad = {}, []
    sums = {}
    for line in (PKG / 'SHA256SUMS').read_text().splitlines():
        h, sep, name = line.partition('  ')
        if sep:
            sums[name] = h
    verify(sums, PKG, '', stats, bad)
    ref = json.loads((PKG / 'reference/DELIVERY_MANIFEST.json').read_text())
    rstats = {}
    verify({f['path']: f['sha256'] for f in ref['files']}, PKG / 'reference', 'reference/', rstats, bad)
    listed = set(sums) | {'reference/' + f['path'] for f in ref['files']}
    bad += [f'{d}: named in public/dropped_paths.txt but listed by neither checksum list' for d in sorted(DROPPED - listed)]
    print(f'{"list":32s} {"class":8s} {"verified":>9s} {"absent":>7s}')
    for name, st in (('SHA256SUMS (4de9412)', stats), ('reference/DELIVERY_MANIFEST.json', rstats)):
        for c in ('git', 'setup', 'hosted', 'dropped', 'merged'):
            if c in st:
                print(f'{name:32s} {c:8s} {st[c]["verified"]:9d} {st[c]["absent"]:7d}')
    if DROPPED:
        print(f'INFO merged notes not shipped (public/dropped_paths.txt): {", ".join(sorted(DROPPED))}')
    for b in bad[:50]:
        print('FAIL', b)
    ok_absent = 'setup/dropped/merged' if 'hosted' in REQUIRED else 'setup/hosted/dropped/merged'
    print('checksums:', 'FAIL' if bad else 'PASS', f'({len(bad)} problems)' if bad else f'(absent files are {ok_absent} only)')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
