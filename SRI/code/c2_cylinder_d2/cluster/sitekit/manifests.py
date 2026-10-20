#!/usr/bin/env python3
"""Strict verification of published directories (standard library only).

A published directory (a grid under <root>/grids/ or a row output under
<root>/outputs/<plan>/) is COMPLETE only if
  * SHA256SUMS exists, is non-empty and well formed: one "<64 hex>  <name>" line
    per file, no duplicate names, every name a plain file name (no '/', no '..',
    not absolute, not hidden);
  * every listed file exists and matches its digest;
  * every required file is listed;
  * no regular file other than SHA256SUMS is present without being listed.
A missing directory is ABSENT; anything else is CORRUPT and must be inspected,
never silently skipped or overwritten. Used by submit.py (before deciding to
skip), by the job scripts (through jobtools.py published-check), by
merge_records.py and by transfer_grid.sh.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

MANIFEST = 'SHA256SUMS'
ROW_RECEIPTS = ('task_receipt.json', 'run_receipt.json')
JOB_RECEIPTS = ('job_receipt.json', 'expanse_job.json')   # expanse_job.json: the first Expanse version (pilot)
LINE = re.compile(r'^([0-9a-f]{64}) [ *](.+)$')


class ManifestError(ValueError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 24), b''):
            h.update(block)
    return h.hexdigest()


def read_manifest(directory: Path) -> dict[str, str]:
    """name -> digest; raises ManifestError for every malformed case."""
    path = directory / MANIFEST
    if not path.is_file():
        raise ManifestError(f'{MANIFEST} missing')
    entries: dict[str, str] = {}
    lines = path.read_text().splitlines()
    if not any(line.strip() for line in lines):
        raise ManifestError(f'{MANIFEST} is empty')
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        m = LINE.match(line)
        if not m:
            raise ManifestError(f'{MANIFEST} line {number} is malformed')
        digest, name = m.groups()
        if (name in ('', '.', '..', MANIFEST) or '/' in name or '\\' in name or name.startswith('.')
                or name != name.strip()):
            raise ManifestError(f'{MANIFEST} line {number}: unsafe or reserved name {name!r}')
        if name in entries:
            raise ManifestError(f'{MANIFEST} lists {name!r} twice')
        entries[name] = digest
    return entries


def verify_dir(directory: Path, required: tuple[str, ...] = (), any_of: tuple[tuple[str, ...], ...] = (),
               hash_large: bool = True, large_bytes: int = 1 << 30) -> tuple[dict[str, str], list[str]]:
    """Return (manifest, problems). With hash_large=False, files of at least
    large_bytes are size-checked only by the caller (their digests are left to
    the compute-node consumer); all other files are hashed."""
    try:
        entries = read_manifest(directory)
    except ManifestError as exc:
        return {}, [str(exc)]
    problems = []
    for name, digest in sorted(entries.items()):
        f = directory / name
        if not f.is_file() or f.is_symlink():
            problems.append(f'listed file missing: {name}')
        elif hash_large or f.stat().st_size < large_bytes:
            if sha256(f) != digest:
                problems.append(f'checksum mismatch: {name}')
    for name in required:
        if name not in entries:
            problems.append(f'required file not listed: {name}')
    for group in any_of:
        if not any(name in entries for name in group):
            problems.append(f'none of {list(group)} is listed')
    for f in sorted(directory.iterdir()):        # a published directory holds exactly its listed files
        if f.name == MANIFEST or f.name in entries:
            continue
        kind = 'subdirectory' if f.is_dir() and not f.is_symlink() else 'file'
        problems.append(f'unlisted {kind}: {f.name}')
    return entries, problems


def row_record_names(job: dict) -> tuple[str, ...]:
    """File names run_task.py checks for one plan row (one record per lambda)."""
    return tuple(f'cluster_k{job["order"]}_a{float(lam)}_N{job["cutoff"]}.json' for lam in job['lambda'])


def row_status(directory: Path, job: dict) -> tuple[str, list[str]]:
    """'absent' | 'complete' | 'corrupt' for a published plan row."""
    if not directory.exists():
        return 'absent', []
    if not directory.is_dir():
        return 'corrupt', ['not a directory']
    _, problems = verify_dir(directory, required=ROW_RECEIPTS + row_record_names(job), any_of=(JOB_RECEIPTS,))
    if not problems:
        receipt = json.loads((directory / 'task_receipt.json').read_text())
        if receipt.get('job') != job:
            problems.append('task_receipt.json describes a different plan row')
    return ('corrupt' if problems else 'complete'), problems


def grid_status(directory: Path, hash_array: bool = True) -> tuple[str, list[str]]:
    """'absent' | 'complete' | 'corrupt' for a published grid. With
    hash_array=False the array is checked against the receipt's byte count only
    (submit.py on a login node); every consumer hashes it on a compute node."""
    if not directory.exists():
        return 'absent', []
    if not directory.is_dir():
        return 'corrupt', ['not a directory']
    try:
        receipt = json.loads((directory / 'grid_receipt.json').read_text())
        array = receipt['array']
        required = ('grid_receipt.json', array, array[:-len('.npy')] + '.json')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return 'corrupt', [f'grid_receipt.json unreadable: {exc}']
    _, problems = verify_dir(directory, required=required, hash_large=hash_array)
    f = directory / array
    if f.is_file() and f.stat().st_size != receipt.get('array_bytes'):
        problems.append(f'{array}: {f.stat().st_size} bytes, receipt says {receipt.get("array_bytes")}')
    return ('corrupt' if problems else 'complete'), problems


def verify_rows(directory: Path) -> tuple[list[Path], list[str]]:
    """Strictly verify every task directory of an outputs/<plan> directory and
    return the verified record paths (exactly the records each row requires) and
    the problems. Anything else under the plan directory is a problem, except
    hidden partial directories left by an interrupted publish."""
    records, problems = [], []
    if not directory.is_dir():
        return [], [f'{directory} is not a directory']
    tasks = []
    for entry in sorted(directory.iterdir()):
        if entry.name.startswith('.') and entry.is_dir() and '.partial.' in entry.name:
            continue
        if entry.is_dir() and not entry.is_symlink() and not entry.name.startswith('.'):
            tasks.append(entry)
        else:
            problems.append(f'{entry}: unexpected entry in the plan directory')
    if not tasks:
        problems.append(f'no task directories in {directory}')
    for task in tasks:
        try:
            job = json.loads((task / 'task_receipt.json').read_text())['job']
            status, why = row_status(task, job)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            status, why = 'corrupt', [f'task_receipt.json unreadable: {exc}']
        problems += [f'{task.name}: {x}' for x in why]
        if status == 'complete':
            records += [task / name for name in row_record_names(job)]
    return records, problems


def main() -> None:
    """python manifests.py verify-rows OUTPUTS_PLAN_DIR [--list-records FILE]: strict
    check of every task directory (the row is taken from its task_receipt.json);
    exit 74 on any problem; FILE receives the verified record paths.
    python manifests.py grid-status GRID_DIR [--size-only]: exit 0 complete, 3 absent,
    74 corrupt. python manifests.py names DIR: validate DIR/SHA256SUMS and print its
    file names, one per line (exit 74 if invalid). Standard library only, so the
    last two also run remotely (transfer_grid.sh) and before any copy (lib.sh)."""
    import argparse
    import sys
    p = argparse.ArgumentParser(description=main.__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    v = sub.add_parser('verify-rows')
    v.add_argument('directory', type=Path)
    v.add_argument('--list-records', type=Path)
    g = sub.add_parser('grid-status')
    g.add_argument('directory', type=Path)
    g.add_argument('--size-only', action='store_true', help='check the array size, not its hash')
    n = sub.add_parser('names')
    n.add_argument('directory', type=Path)
    a = p.parse_args()
    if a.action == 'grid-status':
        status, problems = grid_status(a.directory, hash_array=not a.size_only)
        print(status)
        for x in problems:
            print(f'  {a.directory}: {x}', file=sys.stderr)
        sys.exit({'complete': 0, 'absent': 3}.get(status, 74))
    if a.action == 'names':
        try:
            names = sorted(read_manifest(a.directory))
        except ManifestError as exc:
            print(f'{a.directory}/{MANIFEST}: {exc}', file=sys.stderr)
            sys.exit(74)
        sys.stdout.write(''.join(f'{x}\n' for x in names))
        sys.exit(0)
    records, problems = verify_rows(a.directory)
    for x in problems:
        print(f'PROBLEM {x}')
    print(f'{len(records)} verified records, {len(problems)} problems in {a.directory}')
    if a.list_records and not problems:
        a.list_records.write_text(''.join(f'{r}\n' for r in records))
    sys.exit(74 if problems else 0)


if __name__ == '__main__':
    main()
