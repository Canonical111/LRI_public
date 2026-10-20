#!/usr/bin/env python3
"""Compare frozen block placement on a private copy of one saved task table.

This is a scheduling-model comparison, not a native integration benchmark.
Every scientific coordinate and frozen cost is checked before and after, and
no file in the supplied run is modified. Kernel core-second estimates retain
the source plan's timing-model limitations.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import tempfile
import time
import tracemalloc

from common import ROOT, checked, digest, load
import cluster_graph_tasks as clustering
import production as production


def stats(db, shards, max_tasks, inventory):
    result = clustering.schedule_statistics(db, shards, max_tasks, inventory)
    count = 0
    largest = 0.0
    def costs():
        nonlocal count, largest
        for shard in range(shards):
            for block in production.task_blocks(db, shard, max_tasks, with_cost=True):
                cost = math.fsum(row[-1] for row in block)
                count += 1
                largest = max(largest, cost)
                yield cost
    total = math.fsum(costs())
    result['max_modeled_block_core_seconds'] = largest
    result['mean_modeled_block_core_seconds'] = total / count if count else 0.0
    return result


def benchmark(run, group, output, max_tasks=None, max_graphs=None, seconds=120.0):
    run = Path(run).resolve()
    manifest = load(run / 'manifest.json')
    if not manifest.get('cost_model_sha256'):
        raise ValueError('This benchmark requires a source plan with a frozen measured cost model')
    checked(run / 'cost_model.json', manifest['cost_model_sha256'])
    checked(ROOT / 'inputs/manifest.json', manifest['inputs_manifest_sha256'])
    group_path, cfg = production.group_of(run, manifest, group)
    input_table = group_path / 'tasks.sqlite'
    input_hash = digest(input_table)
    inventory = {row['id']: row for row in load(ROOT / 'inputs/inventory.json')[cfg['sector']][str(cfg['L'])]}
    max_tasks = max_tasks or manifest['checkpoint_tasks']
    with tempfile.TemporaryDirectory(prefix='c8_schedule_model_', dir=ROOT / 'verification') as temporary:
        copy = Path(temporary) / 'tasks.sqlite'
        shutil.copyfile(input_table, copy)
        db = production.dbopen(copy)
        try:
            identity = clustering.task_identity(db, cfg)
            before = stats(db, cfg['shards'], manifest['checkpoint_tasks'], inventory)
            tracemalloc.start()
            started = time.perf_counter()
            shards, _ = production.assign_graph_bundles(db, cfg['shards'])
            limits = production.freeze_blocks(db, shards, max_tasks, max_graphs, seconds)
            elapsed = time.perf_counter() - started
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            after = stats(db, shards, max_tasks, inventory)
            if clustering.task_identity(db, cfg) != identity:
                raise AssertionError('Scheduling changed a scientific coordinate or cost')
        finally:
            db.close()
    checked(input_table, input_hash)
    report = {'schema': 'c8-d2-scheduling-model-comparison-1', 'status': 'passed',
              'source_manifest_sha256': digest(run / 'manifest.json'), 'group': group,
              'source_tasks_sha256': input_hash, 'source_cost_model_sha256': manifest['cost_model_sha256'],
              'source_run_untouched': True, 'scientific_tasks_and_costs_unchanged': True,
              'scientific_identity': identity, 'before': before, 'after': after, 'frozen_limits': limits,
              'local_schedule_construction_seconds_with_tracemalloc': elapsed,
              'peak_traced_python_bytes_for_placement_and_blocks': peak,
              'scope': 'One saved task table; modeled kernel core-seconds, not measured native runtime. '
                       'The Python memory/timing measurement covers placement and freezing only; '
                       'SQLite/native allocations and previously loaded inventory/configuration are excluded.'}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--group', default='a_free_L8')
    parser.add_argument('--checkpoint-tasks', type=int)
    parser.add_argument('--checkpoint-graphs', type=int)
    parser.add_argument('--checkpoint-seconds', type=float, default=120.0)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.run, args.group, args.output, args.checkpoint_tasks,
                               args.checkpoint_graphs, args.checkpoint_seconds), indent=2))


if __name__ == '__main__': main()
