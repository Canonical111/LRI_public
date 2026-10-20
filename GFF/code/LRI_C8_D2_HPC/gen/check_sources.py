#!/usr/bin/env python3
"""Verify the source pins in gen/SOURCES.json (G0: "the c8-rb hashes verify").

Checks, standard library only:
  1. every reference copy (reference/c8d1_inputs8, reference/c7d2_hpc_a55958f, reference/c7d2_production_2026)
     has its pinned sha256 and byte count in the working tree, and reference/SHA256SUMS_c8 lists exactly these
     files with the same hashes;
  2. every verbatim port copy has its pinned sha256 in the review base (git show c8-rb:<dest>), because the
     port copies are edited after c8-rb (skipped, and reported as skipped, outside a git checkout);
  3. with --origins DIR (the directory that holds LRI_C8_HPC, LRI_C7_D2_HPC, LRI_C7_D3_HPC and the production
     records), every pin also equals the original: `git show <commit>:<path>` or the recorded source file.

Usage: python3 -B gen/check_sources.py [--origins /Users/zheng/Documents/Agent_LRI] [--output FILE]
Exit status 0 when every performed check passes, 1 otherwise."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_show(repo: Path, rev: str, path: str) -> bytes | None:
    r = subprocess.run(['git', '-C', str(repo), 'show', f'{rev}:{path}'], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--origins', type=Path, help='directory holding the source repositories (optional)')
    ap.add_argument('--output', type=Path, help='write a JSON record here')
    a = ap.parse_args()
    src = json.loads((ROOT / 'gen/SOURCES.json').read_text())
    errors: list[str] = []
    notes: list[str] = []
    # 1. reference copies in the working tree, and reference/SHA256SUMS_c8
    listed = {}
    for line in (ROOT / 'reference/SHA256SUMS_c8').read_text().splitlines():
        h, sep, name = line.partition('  ')
        if not sep or len(h) != 64 or name in listed:
            errors.append(f'malformed or duplicate SHA256SUMS_c8 row: {line[:120]}')
            continue
        listed[name] = h
    expect = {}
    for r in src['reference_copies']:
        p = ROOT / r['dest']
        if not p.is_file() or p.is_symlink():
            errors.append(f'missing reference copy {r["dest"]}')
            continue
        data = p.read_bytes()
        if sha(data) != r['sha256'] or len(data) != r['bytes']:
            errors.append(f'reference copy differs from its pin: {r["dest"]}')
        expect[r['dest'][len('reference/'):]] = r['sha256']
    if listed != expect:
        errors.append('reference/SHA256SUMS_c8 does not list exactly the pinned reference copies: '
                      f'{sorted(set(listed) ^ set(expect))[:5]}')
    # 2. port copies in the review base
    rb = src['review_base']['commit']
    if (ROOT / '.git').exists():
        for r in src['verbatim_ports']:
            data = git_show(ROOT, rb, r['dest'])
            if data is None or sha(data) != r['sha256']:
                errors.append(f'port copy in c8-rb differs from its pin: {r["dest"]}')
        tag = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'c8-rb^{commit}'], capture_output=True, text=True)
        if tag.returncode != 0 or tag.stdout.strip() != rb:
            errors.append('tag c8-rb does not name the pinned review-base commit')
    else:
        notes.append('no .git: port copies in c8-rb not checked (export)')
    # 3. the originals
    if a.origins:
        for r in src['reference_copies'] + src['verbatim_ports']:
            if 'source_commit' in r:
                data = git_show(a.origins / r['source_repo'], r['source_commit'], r['source_path'])
            else:
                f = a.origins / r['source_file']
                data = f.read_bytes() if f.is_file() else None
            if data is None or sha(data) != r['sha256']:
                errors.append(f'pin differs from its original: {r["dest"]}')
    rec = dict(schema='c8-d2-check-sources-1', reference_copies=len(src['reference_copies']),
               verbatim_ports=len(src['verbatim_ports']), review_base=rb, origins_checked=bool(a.origins),
               errors=errors, notes=notes, status='passed' if not errors else 'failed')
    if a.output:
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec, indent=1))
    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())
