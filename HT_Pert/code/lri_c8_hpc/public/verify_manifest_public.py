#!/usr/bin/env python3
"""tests/verify_manifest.py for the public tree.

MANIFEST_SHA256.json ships verbatim at the production commit 529f208: sha256 of all 164 tracked files except itself.
Files whose bytes the public placeholder scrub changed (cluster user name, scratch path, Expanse account and node names
in README.md, docs/SYMMETRY.md, slurm/ and reference/HPC_CAMPAIGN_REPORT.md; AGENTS.md rule 7) are listed in
public/SCRUBBED.txt and reported, not failed. Any other mismatch or missing file fails. Nothing under src/lri_c8 may be
scrubbed: its source digest dd811aca... binds every record (checked by public/replay_c8.py, row c8.source).
usage: python3 public/verify_manifest_public.py        (exit 0 on success; standard library only)"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
N_EXPECTED = 164


def scrubbed():
    s = ROOT / 'public' / 'SCRUBBED.txt'
    if not s.exists():
        return set()
    return {l.strip() for l in s.read_text().splitlines() if l.strip() and not l.startswith('#')}


def main():
    man = json.loads((ROOT / 'MANIFEST_SHA256.json').read_text())
    scr = scrubbed()
    ok, bad, seen_scr = 0, [], []
    for rel, digest in man.items():
        p = ROOT / rel
        if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == digest:
            ok += 1
        elif rel in scr and p.is_file() and not rel.startswith('src/'):
            seen_scr.append(rel)
            print(f'scrubbed (placeholder tokens): {rel}')
        else:
            bad.append(rel)
    for b in bad:
        print(f"FAIL {'changed' if (ROOT / b).exists() else 'missing'}: {b}")
    n_ok = len(man) == N_EXPECTED
    if not n_ok:
        print(f'FAIL manifest lists {len(man)} files, expected {N_EXPECTED}')
    print(f'{ok}/{len(man)} manifest-listed files byte-identical, {len(seen_scr)} scrubbed '
          f'({len(scr)} listed in public/SCRUBBED.txt), {len(bad)} failures')
    sys.exit(1 if bad or not n_ok else 0)


if __name__ == '__main__':
    main()
