#!/usr/bin/env python3
"""Package the separate optimized source release without full graph packs.

The archive is built from explicit project subtrees, includes a SHA-256 manifest,
and is checked by reading every member before publication. Native executables,
cache files, run directories and symlinks are excluded. Rebuild native workers
on the destination cluster; original build records remain as provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TREES = ('src', 'tools', 'tests', 'docs', 'slurm', 'inputs',
         'verification', 'optimization_work')
TOP = ('Makefile', 'README.md', 'RESULTS.md', 'requirements.txt')
EXCLUDED_PARTS = {'__pycache__', '.pytest_cache'}
EXCLUDED_SUFFIXES = {'.pyc', '.o', '.so', '.a', '.log', '.sqlite', '.sqlite-journal', '.sqlite-wal', '.sqlite-shm'}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def files():
    chosen = [ROOT / name for name in TOP]
    for tree in TREES:
        for path in (ROOT / tree).rglob('*'):
            relative = path.relative_to(ROOT)
            if path.is_symlink() or not path.is_file():
                continue
            if EXCLUDED_PARTS.intersection(relative.parts):
                continue
            if path.suffix in EXCLUDED_SUFFIXES:
                continue
            if relative.parts[:2] == ('inputs', 'packs'):
                continue
            # Extensionless compiled test workers must not be mistaken for
            # source. Executable script permissions alone are not a filter.
            with path.open('rb') as stream:
                if stream.read(4) == b'\x7fELF':
                    continue
            chosen.append(path)
    chosen += sorted((ROOT / 'bin').glob('*.build.json'))
    return sorted(set(chosen), key=lambda p: p.relative_to(ROOT).as_posix())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError('Refusing to replace an existing delivery: ' + str(output))
    required = ('verification/performance_summary.json',
                'verification/final_release_checks.json',
                'verification/final_native_release_checks.json',
                'verification/final_default_kernel_checks.json',
                'verification/final_default_kernel_points.json',
                'verification/attach_inputs_checks.json',
                'verification/hpc_scheduler_tests.json',
                'verification/hpc_cli_tests.json',
                'verification/optimized_hpc_workflow.json',
                'verification/optimized_graph_scheduling.json',
                'verification/hpc_schedule_model_comparison.json',
                'verification/kernel_optimization_checks.json')
    for name in required:
        record = json.loads((ROOT / name).read_text())
        if record.get('status') not in ('passed', 'correctness_checks_passed'):
            raise ValueError('Incomplete release evidence: ' + name)
    selected = files()
    manifest = {
        'schema': 'c8-d2-optimized-source-release-1',
        'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'folder': ROOT.name,
        'full_graph_packs_included': False,
        'requires_inputs': 'Original LRI_C8_D2_HPC/inputs, attached with tools/attach_inputs.py',
        'native_executables_included': False,
        'new_full_scientific_campaign': False,
        'files': {p.relative_to(ROOT).as_posix(): {
            'bytes': p.stat().st_size, 'sha256': digest(p)} for p in selected},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='c8_optimized_', suffix='.zip', dir=output.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as archive:
            for path in selected:
                archive.write(path, f'{ROOT.name}/{path.relative_to(ROOT).as_posix()}')
            archive.writestr(f'{ROOT.name}/RELEASE_MANIFEST.json',
                             json.dumps(manifest, indent=2, sort_keys=True) + '\n')
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError('Archive CRC verification failed')
            for name, expected in manifest['files'].items():
                member = archive.getinfo(f'{ROOT.name}/{name}')
                if Path(member.filename).is_absolute() or '..' in Path(member.filename).parts:
                    raise ValueError('Unsafe archive path')
                with archive.open(member) as stream:
                    h = hashlib.sha256()
                    for chunk in iter(lambda: stream.read(1 << 20), b''):
                        h.update(chunk)
                if member.file_size != expected['bytes'] or h.hexdigest() != expected['sha256']:
                    raise ValueError('Archive identity mismatch: ' + name)
        with open(temporary, 'rb') as stream:
            os.fsync(stream.fileno())
        os.link(temporary, output)
    finally:
        os.unlink(temporary)
    print(json.dumps({'status': 'passed', 'output': str(output),
                      'files': len(selected) + 1, 'bytes': output.stat().st_size,
                      'sha256': digest(output), 'crc_and_member_hashes_verified': True},
                     indent=2))


if __name__ == '__main__':
    main()
