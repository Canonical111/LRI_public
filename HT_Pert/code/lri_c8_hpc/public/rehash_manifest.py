#!/usr/bin/env python3
"""Rehash MANIFEST_SHA256.json in a WORKING COPY of lri_c8_hpc, for a production rerun (REPRODUCE, section 5).

Why. scripts/validate_release.py always runs tests/verify_manifest.py, which requires every file listed in
MANIFEST_SHA256.json to match its recorded sha256, and scripts/make_campaign.py accepts only a receipt with status
'pass' ("Passing receipt for current source required"). In the published tree six listed files carry placeholder
tokens (public/SCRUBBED.txt), and a rerun on another cluster edits slurm/ (module line, stack check, #SBATCH lines,
C8_DATA default, the /mnt/beegfs/ output check of submit_defq.sh) and perhaps docs. Either way the original manifest
check fails, so the receipt is 'fail' and no campaign can be frozen. scripts/update_manifest.py would rewrite the
manifest, but it lists the files from `git ls-files` and needs a git checkout, which the public tree is not.

What. In the working copy WORKCOPY this script recomputes the sha256 of exactly the files the manifest already lists
(164 at 529f208; same paths, same serialization as scripts/update_manifest.py: json.dumps(indent=2, sort_keys=True)
plus a newline) and rewrites WORKCOPY/MANIFEST_SHA256.json. It refuses, and writes nothing, when
  - WORKCOPY sits in the published layout (WORKCOPY/../../data/HT_1d/c8 exists): copy the package elsewhere first;
    the shipped tree and its MANIFEST_SHA256.json are never rewritten;
  - the manifest does not list 164 files, or a listed file is missing;
  - any listed file under src/ changed, or the source digest of WORKCOPY/src/lri_c8 (sha256 over the sorted relative
    paths and bytes of **/*.py, the solver's io.source_digest) is not dd811aca...: that digest binds every record and
    gates make_campaign, resume and export, so src/ must stay as shipped.
Files you add (a new batch script) are not listed; tests/verify_manifest.py checks listed files only.

usage: python3 public/rehash_manifest.py WORKCOPY [--dry-run]
       (run it with the public/ of the shipped tree or of the working copy; standard library only; exit 0 on success)
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

SRC = 'dd811aca899543c4533e0c3f5e54cea67ae0cd06e875ceae8d68edaf4247cb81'
N_EXPECTED = 164


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def source_digest(root):
    h = hashlib.sha256()
    for p in sorted(root.rglob('*.py')):
        h.update(str(p.relative_to(root)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('workcopy', type=Path, help='root of the working copy (the folder holding MANIFEST_SHA256.json)')
    ap.add_argument('--dry-run', action='store_true', help='report the changes, write nothing')
    a = ap.parse_args()
    root = a.workcopy.resolve()
    man_path = root / 'MANIFEST_SHA256.json'
    if (root / '..' / '..' / 'data' / 'HT_1d' / 'c8').is_dir():
        sys.exit(f'refusing: {root} sits in the published HT_Pert layout (../../data/HT_1d/c8 exists); copy '
                 f'code/lri_c8_hpc to a working directory elsewhere and run this there')
    if not man_path.is_file():
        sys.exit(f'refusing: {man_path} not found')
    man = json.loads(man_path.read_text())
    if len(man) != N_EXPECTED:
        sys.exit(f'refusing: the manifest lists {len(man)} files, expected {N_EXPECTED}')
    missing = [k for k in man if not (root / k).is_file()]
    if missing:
        sys.exit(f'refusing: listed files missing: {missing}')
    new = {k: sha(root / k) for k in sorted(man)}
    changed = [k for k in sorted(man) if new[k] != man[k]]
    src_changed = [k for k in changed if k.startswith('src/')]
    digest = source_digest(root / 'src' / 'lri_c8')
    if src_changed or digest != SRC:
        sys.exit(f'refusing: src/ differs from the shipped source (changed listed files {src_changed}; source digest '
                 f'{digest[:16]}... vs {SRC[:16]}...). Nothing under src/lri_c8 may be changed or added.')
    for k in changed:
        print(f'rehashed: {k}  {man[k][:12]}... -> {new[k][:12]}...')
    blob = json.dumps(new, indent=2, sort_keys=True) + '\n'
    if a.dry_run:
        print(f'dry run: {len(changed)} of {len(man)} listed files would be rehashed; src/ unchanged, source digest '
              f'{SRC[:16]}...; nothing written')
        return
    tmp = man_path.with_name(man_path.name + f'.tmp.{os.getpid()}')
    tmp.write_text(blob)
    os.replace(tmp, man_path)
    print(f'{man_path}: {len(new)} files listed, {len(changed)} rehashed, src/ unchanged (source digest '
          f'{SRC[:16]}...); sha256 of the new manifest {hashlib.sha256(blob.encode()).hexdigest()[:16]}...')


if __name__ == '__main__':
    main()
