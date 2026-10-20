#!/usr/bin/env python3
"""Launch one independent endpoint calculation without fixing cluster resources.

This wrapper does not change any scientific solver formula. It never launches
jobs remotely: invoke it inside an allocation, a batch job, or a local shell.
The historical continuum analysis is deliberately NOT run on new records.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
SCIENCE = ROOT / 'code' / 'hamiltonian'
# Historical two-index cutoff of the leading-tail sidecar written by reproduce.py.
# A plan row may set 'tail_cutoff'; rows without it keep this value.
DEFAULT_TAIL_CUTOFF = 2048


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: object) -> None:
    """Atomically publish a small JSON record in an existing output directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.writing')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    os.replace(temp, path)


def source_hashes() -> dict[str, str]:
    return {p.name: sha256(p) for p in sorted(SCIENCE.glob('*.py'))}


def grid_key(cutoff: int, oversample: int, radius_cost: float) -> str:
    r = format(radius_cost, '.12g').replace('.', 'p')
    return f'N{cutoff}_o{oversample}_r{r}'


@contextmanager
def exclusive(directory: Path) -> Iterator[None]:
    """Fail on simultaneous writers. A hard-kill can leave a stale lock."""
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / '.writer.lock'
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise RuntimeError(
            f'Writer lock exists: {lock}. Do not remove it until you have '
            'verified no process is using this directory.'
        ) from exc
    (lock / 'owner.json').write_text(json.dumps({
        'pid': os.getpid(), 'host': os.uname().nodename if hasattr(os, 'uname') else 'unknown',
        'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
    }, indent=2))
    try:
        yield
    finally:
        shutil.rmtree(lock)


def stage(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for source in SCIENCE.glob('*.py'):
        shutil.copy2(source, path / source.name)


def checked_int(value: object, label: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f'{label} must be an integer >= {minimum}.')
    return value


def load_plan(path: Path) -> tuple[dict, list[dict]]:
    plan = json.loads(path.read_text())
    if plan.get('physical_delta') != 0:
        raise ValueError('This launcher only supports physical_delta = 0.')
    jobs = plan.get('jobs')
    if not isinstance(jobs, list) or not jobs:
        raise ValueError('The plan must contain a nonempty jobs list.')
    seen: set[str] = set()
    for i, job in enumerate(jobs):
        label = job.get('id', '')
        if not isinstance(label, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', label) or label in seen:
            raise ValueError(f'Job {i}: id must be unique and use only letters, digits, _ or -.')
        seen.add(label)
        checked_int(job.get('cutoff'), 'cutoff', 4)
        checked_int(job.get('mixed_cutoff'), 'mixed_cutoff', 16)
        checked_int(job.get('collapsed_cutoff'), 'collapsed_cutoff', 1000)
        checked_int(job.get('oversample'), 'oversample', 3)
        if job.get('order') not in [1, 2, 3]:
            raise ValueError(f'Job {i}: order must be 1, 2, or 3.')
        radius = job.get('radius_cost')
        if not isinstance(radius, (int, float)) or not math.isfinite(radius) or radius <= 0:
            raise ValueError(f'Job {i}: radius_cost must be finite and positive.')
        values = job.get('lambda')
        if not isinstance(values, list) or not values:
            raise ValueError(f'Job {i}: lambda must be a nonempty list.')
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x <= 0 for x in values):
            raise ValueError(f'Job {i}: lambda values must be finite and positive.')
        if len(set(values)) != len(values):
            raise ValueError(f'Job {i}: repeated lambda value.')
        # Optional keys (absent in the historical plans, so their commands are unchanged).
        if 'tail_cutoff' in job:
            checked_int(job['tail_cutoff'], f'Job {i}: tail_cutoff', 64)
        stage_name = job.get('stage', 'none')
        if not isinstance(stage_name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', stage_name):
            raise ValueError(f'Job {i}: stage must use only letters, digits, _ or -.')
    return plan, jobs


def environment(workers: int, fft_workers: int | None) -> dict[str, str]:
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               OMP_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', MPLBACKEND='Agg',
               LRI_FFT_WORKERS=str(fft_workers or workers))
    # The plan row is the only source of the tail cutoff for launched tasks,
    # so that every task receipt records the value actually used.
    env.pop('LRI_TAIL_CUTOFF', None)
    return env


def verify_grid(path: Path, cutoff: int, oversample: int, rc: float) -> None:
    import numpy as np
    if not path.is_file() or not path.with_suffix('.json').is_file():
        raise ValueError(f'A grid requires both its .npy array and JSON metadata: {path}')
    metadata = json.loads(path.with_suffix('.json').read_text())
    if metadata.get('K') != cutoff + 1 or metadata.get('oversample') != oversample:
        raise ValueError(f'Grid metadata does not match cutoff/oversampling: {path}')
    if not math.isclose(float(metadata.get('radius_cost', float('nan'))), rc, rel_tol=0, abs_tol=1e-12):
        raise ValueError(f'Grid radius does not match the requested radius: {path}')
    a = np.load(path, mmap_mode='r', allow_pickle=False)
    if a.shape != (6,) + (cutoff + 1,) * 3 or a.dtype != np.dtype('float64'):
        raise ValueError(f'Invalid grid shape/dtype: {a.shape}, {a.dtype}')
    del a


def cache_grid(cache_root: Path, cutoff: int, oversample: int, rc: float) -> Path:
    directory = cache_root.resolve() / grid_key(cutoff, oversample, rc)
    receipt = directory / 'grid_receipt.json'
    if not receipt.is_file():
        raise ValueError(f'Grid is not prepared: {directory}; run prepare-grid first.')
    obj = json.loads(receipt.read_text())
    if obj.get('generator_source_hashes') != source_hashes():
        raise ValueError('Cached grid was prepared with different scientific source files.')
    path = directory / obj['array']
    verify_grid(path, cutoff, oversample, rc)
    if path.stat().st_size != obj['array_bytes'] or sha256(path.with_suffix('.json')) != obj['metadata_sha256']:
        raise ValueError('Grid size or metadata changed after preparation.')
    # A full hash of a multi-GB array is intentionally not repeated on every read.
    # This checks completion/shape/provenance, not every cached array byte.
    return path


def prepare(args: argparse.Namespace) -> None:
    checked_int(args.cutoff, 'cutoff', 4)
    checked_int(args.oversample, 'oversample', 3)
    if not math.isfinite(args.radius_cost) or args.radius_cost <= 0:
        raise ValueError('radius-cost must be finite and positive.')
    directory = args.cache_root.resolve() / grid_key(args.cutoff, args.oversample, args.radius_cost)
    if args.dry_run:
        print(json.dumps({'action': 'prepare-grid', 'directory': str(directory),
              'N': args.cutoff, 'oversample': args.oversample, 'radius_cost': args.radius_cost,
              'workers': args.workers, 'numerical_grid_generated': False}, indent=2))
        return
    directory.mkdir(parents=True, exist_ok=True)
    with exclusive(directory):
        if (directory / 'grid_receipt.json').exists():
            print('REUSE', cache_grid(args.cache_root, args.cutoff, args.oversample, args.radius_cost))
            return
        stage(directory)
        import multiprocessing as mp
        parallel = args.workers > 1 and 'fork' in mp.get_all_start_methods()
        script = 'parallel_coefficients.py' if parallel else 'fast_coefficients.py'
        command = [sys.executable, str(directory / script), '--size', str(args.cutoff),
                   '--oversample', str(args.oversample), '--radius-cost', str(args.radius_cost)]
        if parallel:
            command += ['--workers', str(args.workers)]
        print('RUN', *command, flush=True)
        subprocess.run(command, cwd=directory, env=environment(args.workers, None), check=True)
        prefix = 'parallel' if parallel else 'fast'
        grid = directory / f'{prefix}_coeff4_K{args.cutoff+1}_o{args.oversample}_r{args.radius_cost}.npy'
        verify_grid(grid, args.cutoff, args.oversample, args.radius_cost)
        write_json(directory / 'grid_receipt.json', {
            'array': grid.name, 'array_bytes': grid.stat().st_size,
            'metadata_sha256': sha256(grid.with_suffix('.json')),
            'generator_source_hashes': source_hashes(), 'workers': args.workers,
            'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'scope': 'Complete numerical grid and metadata; not a physical coefficient.',
        })
        print('GRID', grid)


def run(args: argparse.Namespace) -> None:
    plan, jobs = load_plan(args.plan)
    if args.task_index < 0 or args.task_index >= len(jobs):
        raise ValueError(f'task-index must be between 0 and {len(jobs)-1}.')
    job = jobs[args.task_index]
    sources = source_hashes()
    fingerprint = hashlib.sha256(json.dumps({'job': job, 'source': sources}, sort_keys=True).encode()).hexdigest()[:12]
    task = f'{job["id"]}_{fingerprint}'
    work = args.work_root.resolve() / task
    output = args.output_root.resolve() / task
    grid: Path | None = None
    if args.coefficient_cache:
        if args.dry_run:
            grid = args.coefficient_cache.resolve() / grid_key(job['cutoff'], job['oversample'], job['radius_cost']) / '<prepared-array.npy>'
        else:
            grid = cache_grid(args.coefficient_cache, job['cutoff'], job['oversample'], job['radius_cost'])
    command = [sys.executable, str(ROOT / 'scripts/run.py'), 'hamiltonian', '--work-dir', str(work),
               '--output', str(output), '--', '--cutoff', str(job['cutoff']), '--order', str(job['order']),
               '--lam', *map(str, job['lambda']), '--oversample', str(job['oversample']),
               '--radius-cost', str(float(job['radius_cost'])), '--workers', str(args.workers),
               '--mixed-cutoff', str(job['mixed_cutoff']), '--collapsed-cutoff', str(job['collapsed_cutoff']),
               '--output-prefix', 'cluster']
    if 'tail_cutoff' in job:
        command += ['--tail-cutoff', str(job['tail_cutoff'])]
    if grid:
        command += ['--coefficients', str(grid)]
    if args.dry_run:
        print(json.dumps({'action': 'run', 'task': task, 'plan_sha256': sha256(args.plan),
                         'job': job, 'command': command, 'work_dir': str(work), 'output_dir': str(output),
                         'fixed_regulator_only': True, 'physical_C2_claimed': False}, indent=2))
        return
    # Scientific staging mutates this directory. Protect both the work area and output.
    with exclusive(work), exclusive(output):
        receipt = output / 'task_receipt.json'
        if receipt.exists():
            obj = json.loads(receipt.read_text())
            if not args.skip_completed:
                raise RuntimeError(f'Task is already complete: {output}. Use --skip-completed or choose a new output root.')
            if obj.get('job') != job or obj.get('source_hashes') != sources:
                raise RuntimeError('Completed-task provenance does not match this request.')
            for name, expected in obj['outputs_sha256'].items():
                if not (output / name).is_file() or sha256(output / name) != expected:
                    raise RuntimeError(f'Completed output is missing/changed: {name}')
            print('SKIP VERIFIED COMPLETE', output)
            return
        print('RUN', *command, flush=True)
        subprocess.run(command, cwd=ROOT, env=environment(args.workers, args.fft_workers), check=True)
        for value in job['lambda']:
            name = f'cluster_k{job["order"]}_a{float(value)}_N{job["cutoff"]}.json'
            row = json.loads((output / name).read_text())
            if row['N'] != job['cutoff'] or row['order'] != job['order'] or row['lam'] != value:
                raise ValueError(f'Unexpected raw record: {name}')
        # Record configuration explicitly; scientific historical records do not always retain it.
        write_json(output / 'task_receipt.json', {
            'completed_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'job': job, 'plan_name': plan.get('name'), 'plan_sha256': sha256(args.plan),
            'source_hashes': sources, 'workers': args.workers, 'fft_workers': args.fft_workers or args.workers,
            'tail_cutoff': job.get('tail_cutoff', DEFAULT_TAIL_CUTOFF),
            'python': sys.version, 'command': command, 'shared_grid': str(grid) if grid else None,
            'outputs_sha256': {p.name: sha256(p) for p in sorted(output.iterdir()) if p.is_file() and p.name != 'task_receipt.json'},
            'analysis_scope': 'Fixed-regulator raw records only. Historical continuum analysis was not run.',
            'physical_C2_claimed': False,
        })
        print('COMPLETE', output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    listing = sub.add_parser('list', help='Validate a task plan and print its task indices.')
    listing.add_argument('--plan', type=Path, default=ROOT / 'cluster/extension_plan.json')
    prep = sub.add_parser('prepare-grid', help='Build one reusable, read-only-in-use Ising coefficient grid.')
    prep.add_argument('--cutoff', type=int, required=True)
    prep.add_argument('--oversample', type=int, default=4)
    prep.add_argument('--radius-cost', type=float, default=4.5)
    prep.add_argument('--cache-root', type=Path, required=True)
    task = sub.add_parser('run', help='Run one job. No continuum estimate is generated automatically.')
    task.add_argument('--plan', type=Path, default=ROOT / 'cluster/extension_plan.json')
    task.add_argument('--task-index', type=int, required=True)
    task.add_argument('--work-root', type=Path, required=True)
    task.add_argument('--output-root', type=Path, required=True)
    task.add_argument('--coefficient-cache', type=Path)
    task.add_argument('--fft-workers', type=int)
    task.add_argument('--skip-completed', action='store_true')
    for p in [prep, task]:
        # An empty LRI_WORKERS (submit.py clears unused reserved variables) means unset.
        p.add_argument('--workers', type=int, default=int(os.environ.get('LRI_WORKERS') or '1'),
                       help='Local workers; configure for your allocation. Default: LRI_WORKERS or serial.')
        p.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        if args.action == 'list':
            plan, jobs = load_plan(args.plan)
            print('PLAN', plan.get('name', args.plan.name), 'physical_delta=0')
            for i, job in enumerate(jobs):
                # Staged (Expanse) plans also show their auxiliary cutoffs; older plans print as before.
                extra = [f'{k}={job[k]}' for k in ('stage', 'mixed_cutoff', 'tail_cutoff') if k in job] if 'stage' in job else []
                print(i, job['id'], 'N=', job['cutoff'], 'order=', job['order'], 'lambda=', job['lambda'], *extra)
        else:
            checked_int(args.workers, 'workers', 1)
            if getattr(args, 'fft_workers', None) is not None:
                checked_int(args.fft_workers, 'fft-workers', 1)
            prepare(args) if args.action == 'prepare-grid' else run(args)
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
