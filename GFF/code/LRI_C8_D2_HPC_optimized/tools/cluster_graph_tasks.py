#!/usr/bin/env python3
"""Clone an unstarted C8 plan with graph-local, cost-balanced scheduling.

All tasks for a graph stay on one shard and are adjacent. This avoids loading
the same graph separately for each replicate. Task coordinates, costs, point
counts, random streams, inputs, executable and numerical tools are unchanged.
The source plan is read only; the destination is published atomically after
verification and must not already exist. Execute the destination, not both
copies: they describe the same statistical samples.
"""
from __future__ import annotations

import argparse
import copy
import ctypes
import errno
import hashlib
import heapq
import itertools
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile

from common import ROOT, canon, checked, digest, load, object_hash
import production as prod

SCHEMA = 'c8-d2-graph-scheduling-1'
TOOL = Path(__file__).name
BLOCK_ORDER = 'graph bundles: descending total estimated cost, graph id, replicate, begin, uid'


def write_json(path: Path, data: dict) -> None:
    # Used only in the private, unpublished clone.
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def plan_files(source: Path, manifest: dict) -> dict[str, str]:
    """Require the exact file set made by production.plan; any run is refused."""
    expected = {'manifest.json'}
    if manifest.get('cost_model_sha256'):
        expected.add('cost_model.json')
    if manifest.get('allocation_file_sha256'):
        expected.add('allocation.json')
    for group in manifest['groups']:
        name = group['name']
        if Path(name).name != name or name in ('.', '..'):
            raise ValueError('Unsafe group name')
        expected.update(f'groups/{name}/{leaf}' for leaf in ('config.json', 'sobol.bin', 'tasks.sqlite'))
    allowed_dirs = {'groups'} | {f'groups/{g["name"]}' for g in manifest['groups']}
    actual = set()
    for path in source.rglob('*'):
        rel = path.relative_to(source).as_posix()
        if path.is_symlink():
            raise ValueError(f'Symlinks are not allowed in an unstarted source plan: {rel}')
        if path.is_dir():
            if rel not in allowed_dirs:
                raise ValueError(f'Source is not an untouched, unstarted plan: {rel}')
        elif path.is_file():
            actual.add(rel)
        else:
            raise ValueError(f'Unexpected source entry: {rel}')
    if actual != expected:
        raise ValueError('Source is not an untouched, unstarted plan; unexpected or missing files: ' +
                         ', '.join(sorted(actual ^ expected)))
    return {name: digest(source / name) for name in sorted(expected)}


def task_identity(db, cfg: dict) -> dict:
    """Hash exact scientific rows and validate complete stream coordinates."""
    if db.execute('PRAGMA quick_check').fetchone() != ('ok',):
        raise ValueError('Task database integrity check failed')
    task_hash, expected_hash = hashlib.sha256(), hashlib.sha256()
    tasks = samples = 0
    for row in db.execute('SELECT uid,rep,gi,lo,hi,total,cost FROM tasks ORDER BY uid'):
        uid, rep, gi, lo, hi, total, cost = row
        if not (all(type(v) is int for v in row[:6]) and uid >= 0 and rep >= 0 and
                gi >= 0 and 0 <= lo < hi <= total and math.isfinite(cost) and cost >= 0):
            raise ValueError('Invalid task coordinates or cost')
        task_hash.update((canon(row) + '\n').encode())
        tasks += 1
        samples += hi - lo
    # Keep only O(G) graph-count metadata, never an R*G expected-coordinate
    # list. Both database streams are consumed in their deterministic order.
    counts = sorted(((int(gi), count) for gi, count in cfg['counts'].items()))
    expected_cfg = ((rep, gi, count) for rep in range(cfg['replicates']) for gi, count in counts)
    expected = db.execute('SELECT rep,gi,total FROM expected ORDER BY rep,gi')
    actual = iter(db.execute('SELECT rep,gi,lo,hi,total FROM tasks ORDER BY rep,gi,lo,uid'))
    current = next(actual, None)
    expected_streams = 0
    for row, planned in itertools.zip_longest(expected, expected_cfg):
        if row != planned:
            raise ValueError('Expected stream table disagrees with frozen counts')
        rep, gi, total = row
        expected_streams += 1
        expected_hash.update((canon((rep, gi, total)) + '\n').encode())
        end = 0
        while current is not None and current[:2] == (rep, gi):
            _, _, lo, hi, row_total = current
            if lo != end or row_total != total:
                raise ValueError('Task stream has a gap, overlap, or wrong total')
            end = hi
            current = next(actual, None)
        if end != total:
            raise ValueError('Task stream is incomplete')
    if current is not None or tasks != cfg['tasks'] or samples != cfg['samples']:
        raise ValueError('Task coverage disagrees with group metadata')
    return {'tasks_sha256_without_placement': task_hash.hexdigest(),
            'expected_streams_sha256': expected_hash.hexdigest(),
            'tasks': tasks, 'samples': samples, 'expected_streams': expected_streams}


def schedule_statistics(db, shards: int, block_size: int, inventory: dict) -> dict:
    blocks = loads = max_graphs = max_blob_bytes = 0
    by_shard = []
    for shard in range(shards):
        count = 0
        cost = 0.0
        shard_blocks = 0
        for block in prod.task_blocks(db, shard, block_size, with_cost=True):
            graph_ids = {row[2] for row in block}
            count += len(block)
            cost += math.fsum(row[6] for row in block)
            shard_blocks += 1
            loads += len(graph_ids)
            max_graphs = max(max_graphs, len(graph_ids))
            max_blob_bytes = max(max_blob_bytes, sum(inventory[gi]['length'] for gi in graph_ids))
        blocks += shard_blocks
        by_shard.append({'shard': shard, 'tasks': count, 'blocks': shard_blocks, 'cost_units': cost})
    return {'blocks': blocks, 'graph_loads': loads, 'max_graphs_per_block': max_graphs,
            'max_staged_graph_bytes_per_block': max_blob_bytes, 'shards': by_shard}


def reschedule_group(db, shards: int) -> int:
    """LPT on whole graphs; within a shard, keep graph tasks contiguous."""
    nshards, _ = prod.assign_graph_bundles(db, shards)
    # The scientific stream index is already present in production plans.
    for shard in range(nshards):
        row = db.execute('SELECT COUNT(*),COUNT(DISTINCT pos),MIN(pos),MAX(pos) FROM tasks WHERE shard=?', (shard,)).fetchone()
        count = row[0]
        if row != (count, count, 0, count - 1):
            raise ValueError('Invalid shard positions')
    if db.execute('SELECT gi FROM tasks GROUP BY gi HAVING COUNT(DISTINCT shard) != 1 LIMIT 1').fetchone():
        raise ValueError('A graph spans multiple shards')
    return nshards


def publish_directory(source: Path, destination: Path) -> None:
    """Linux atomic, no-clobber directory publication; no non-atomic fallback."""
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, 'renameat2', None)
    if renameat2 is None:
        raise OSError('Atomic no-clobber directory publication requires renameat2')
    renameat2.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    renameat2.restype = ctypes.c_int
    if renameat2(-100, os.fsencode(source), -100, os.fsencode(destination), 1):
        code = ctypes.get_errno()
        if code == errno.EEXIST:
            raise FileExistsError(destination)
        raise OSError(code, os.strerror(code), str(destination))


def cluster(source: Path, destination: Path, *, shards: int = 9, checkpoint_tasks: int = 512,
            checkpoint_graphs: int | None = None, checkpoint_seconds: float | None = None) -> dict:
    source = source.resolve(strict=True)
    destination = destination.absolute()
    if not source.is_dir():
        raise ValueError('Source must be a planned run directory')
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    if source == destination or source in destination.parents:
        raise ValueError('Destination must be outside the source plan')
    if shards < 1 or not 1 <= checkpoint_tasks <= 100000:
        raise ValueError('Positive shards and 1..100000 checkpoint tasks required')
    manifest, _, source_manifest_hash, _ = prod.verify_base(source)
    if manifest.get('scheduling'):
        raise ValueError('This utility accepts original, unstarted production.plan output only')
    if checkpoint_tasks < manifest['threads']:
        raise ValueError('Checkpoint block is smaller than the planned thread count')
    if checkpoint_graphs is not None and checkpoint_graphs < 1:
        raise ValueError('Positive checkpoint graph limit required')
    if checkpoint_seconds is not None and (not math.isfinite(checkpoint_seconds) or checkpoint_seconds <= 0 or not manifest.get('cost_model_sha256')):
        raise ValueError('Positive checkpoint seconds and a measured cost model required')
    initial_files = plan_files(source, manifest)
    inventory = load(ROOT / 'inputs/inventory.json')
    destination.parent.mkdir(parents=True, exist_ok=True)
    report = {'schema': SCHEMA, 'source_manifest_sha256': source_manifest_hash,
              'source_directory': str(source), 'same_statistical_samples_as_source': True,
              'execute_both_copies': False,
              'method': BLOCK_ORDER, 'requested_shards_per_group': shards,
              'source_checkpoint_tasks': manifest['checkpoint_tasks'],
              'checkpoint_tasks': checkpoint_tasks, 'tool_sha256': digest(Path(__file__)), 'groups': {}}
    stage = Path(tempfile.mkdtemp(prefix=destination.name + '.staging_', dir=destination.parent))
    try:
        for name, checksum in initial_files.items():
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)
            checked(target, checksum)
        new_manifest = copy.deepcopy(manifest)
        new_manifest['checkpoint_tasks'] = checkpoint_tasks
        new_manifest.update(task_order='graph', checkpoint_graphs=checkpoint_graphs, checkpoint_seconds=checkpoint_seconds)
        new_manifest['tool_sha256'][TOOL] = report['tool_sha256']
        new_manifest['tool_sha256']['task_schedule.py'] = digest(ROOT / 'tools/task_schedule.py')
        new_manifest['jobs'] = []
        new_manifest['shard_policy'] = 'graph_bundle_lpt'
        estimates = new_manifest['estimates']
        for entry in new_manifest['groups']:
            group_dir, cfg = prod.group_of(source, manifest, entry['name'])
            checked(group_dir / 'sobol.bin', cfg['net']['sha256'])
            group_stage = stage / 'groups' / entry['name']
            graph_rows = {row['id']: row for row in inventory[cfg['sector']][str(cfg['L'])]}
            db = prod.dbopen(group_stage / 'tasks.sqlite')
            try:
                before_identity = task_identity(db, cfg)
                before_schedule = schedule_statistics(db, cfg['shards'], manifest['checkpoint_tasks'], graph_rows)
                nshards = reschedule_group(db, shards)
                block_stats = prod.freeze_blocks(db, nshards, checkpoint_tasks, checkpoint_graphs, checkpoint_seconds)
                after_identity = task_identity(db, cfg)
                if after_identity != before_identity:
                    raise ValueError('Scheduling changed a scientific task or cost')
                after_schedule = schedule_statistics(db, nshards, checkpoint_tasks, graph_rows)
            finally:
                db.close()
            new_cfg = copy.deepcopy(cfg)
            new_cfg.update(shards=nshards, block_order=BLOCK_ORDER,
                           tasks_sha256=digest(group_stage / 'tasks.sqlite'), checkpoint_layout=block_stats)
            write_json(group_stage / 'config.json', new_cfg)
            entry['sha256'] = digest(group_stage / 'config.json')
            first_job = len(new_manifest['jobs'])
            new_manifest['jobs'].extend({'id': first_job + shard, 'group': entry['name'], 'shard': shard}
                                        for shard in range(nshards))
            estimate = estimates['groups'][entry['name']]
            longest = max(row['cost_units'] for row in after_schedule['shards'])
            old_cost = estimate['cost_units']
            scale = estimate['core_hours'] * 3600 / old_cost if estimate['core_hours'] is not None and old_cost else None
            estimate.update(shards=nshards, checkpoint_layout=block_stats, max_shard_core_seconds=longest * scale if scale is not None else None,
                            max_shard_wall_seconds=longest * scale / (manifest['threads'] * estimates['assumed_thread_efficiency'])
                            if scale is not None else None)
            report['groups'][entry['name']] = {
                'source_config_sha256': next(g['sha256'] for g in manifest['groups'] if g['name'] == entry['name']),
                'source_tasks_sha256': cfg['tasks_sha256'], 'tasks_sha256': new_cfg['tasks_sha256'],
                'scientific_identity': before_identity, 'identical_after_scheduling': True,
                'source_schedule': before_schedule, 'schedule': after_schedule}
        walls = [item['max_shard_wall_seconds'] for item in estimates['groups'].values()]
        estimates['max_shard_wall_seconds'] = max(walls) if all(value is not None for value in walls) else None
        estimates['suggested_time_seconds'] = max(900, math.ceil(3 * max(walls) / 60) * 60) if all(value is not None for value in walls) else None
        estimates['shard_basis'] += '; whole graph bundles assigned by LPT'
        report['totals'] = {label: {key: sum(group[label][key] for group in report['groups'].values())
                                   for key in ('blocks', 'graph_loads')}
                            for label in ('source_schedule', 'schedule')}
        report['source_files_sha256'] = initial_files
        shutil.copyfile(source / 'manifest.json', stage / 'source_manifest.json')
        write_json(stage / 'scheduling_provenance.json', report)
        new_manifest['scheduling'] = {
            'schema': SCHEMA, 'method': BLOCK_ORDER,
            'source_manifest_sha256': source_manifest_hash,
            'provenance_file': 'scheduling_provenance.json',
            'provenance_sha256': digest(stage / 'scheduling_provenance.json'),
            'same_statistical_samples_as_source': True,
            'note': 'Execute this destination only; source and destination are the same statistical campaign.'}
        write_json(stage / 'manifest.json', new_manifest)
        # Recheck pinned inputs, native executable, tools and every new group.
        verified, _, _, _ = prod.verify_base(stage)
        for entry in verified['groups']:
            group_dir, cfg = prod.group_of(stage, verified, entry['name'])
            checked(group_dir / 'sobol.bin', cfg['net']['sha256'])
        # Refuse if the source started or changed during cloning.
        if plan_files(source, manifest) != initial_files:
            raise ValueError('Source plan changed during scheduling')
        checked(stage / 'source_manifest.json', source_manifest_hash)
        publish_directory(stage, destination)
        return {'directory': str(destination), 'schema': SCHEMA, 'jobs': len(verified['jobs']),
                'scientific_tasks_unchanged': True, 'native_executable_unchanged': True,
                'source_and_destination_are_same_samples': True, 'totals': report['totals'],
                'max_graphs_per_block': max(g['schedule']['max_graphs_per_block'] for g in report['groups'].values()),
                'max_staged_graph_bytes_per_block': max(g['schedule']['max_staged_graph_bytes_per_block'] for g in report['groups'].values())}
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--shards', type=int, default=9)
    parser.add_argument('--checkpoint-tasks', type=int, default=512)
    parser.add_argument('--checkpoint-graphs', type=int)
    parser.add_argument('--checkpoint-seconds', type=float, help='Summed modeled kernel core-seconds; requires a measured cost model')
    args = parser.parse_args()
    print(json.dumps(cluster(args.source, args.destination, shards=args.shards,
                             checkpoint_tasks=args.checkpoint_tasks, checkpoint_graphs=args.checkpoint_graphs,
                             checkpoint_seconds=args.checkpoint_seconds), indent=2))


if __name__ == '__main__':
    main()
