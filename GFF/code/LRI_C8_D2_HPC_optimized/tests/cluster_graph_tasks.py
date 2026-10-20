#!/usr/bin/env python3
"""Verify graph-local scheduling preserves actual native C8 sample results."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import cluster_graph_tasks as clustering
import production as prod
from common import digest, load


def file_hashes(directory: Path) -> dict:
    return {path.relative_to(directory).as_posix(): digest(path)
            for path in directory.rglob('*') if path.is_file()}


def scientific_rows(directory: Path) -> dict:
    result = {}
    for entry in load(directory / 'manifest.json')['groups']:
        rows = {}
        for path in (directory / 'groups' / entry['name'] / 'checkpoints').glob('*.json'):
            for row in load(path)['native']['rows']:
                if row['uid'] in rows:
                    raise AssertionError('Repeated native task uid')
                rows[row['uid']] = {key: row[key] for key in prod.SCIENTIFIC}
        result[entry['name']] = rows
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', OMP_NUM_THREADS='1')

    def run(script, *arguments):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'tools' / script), *map(str, arguments)],
                                cwd=ROOT, env=env, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(f'{script} failed: {result.stdout}\n{result.stderr}')

    with tempfile.TemporaryDirectory(prefix='c8_cluster_', dir=ROOT / 'verification') as temporary:
        base = Path(temporary)
        original, clustered = base / 'original', base / 'clustered'
        run('production.py', 'plan', original, '--seed', '84623598257191697', '--backend', 'gmp',
            '--replicates', '4', '--points', '8', '--test-graphs', '2', '--shards', '2',
                '--shard-policy', 'uniform', '--task-order', 'legacy', '--threads', '1', '--checkpoint-tasks', '4', '--chunk-points', '4')
        original_hashes = file_hashes(original)
        # A failure after cloning must publish nothing and leave the source exact.
        with patch.object(clustering, 'reschedule_group', side_effect=RuntimeError('injected staging failure')):
            try:
                clustering.cluster(original, base / 'failed')
            except RuntimeError as exc:
                if str(exc) != 'injected staging failure':
                    raise
            else:
                raise AssertionError('Injected scheduling failure was ignored')
        if (base / 'failed').exists() or list(base.glob('failed.staging_*')):
            raise AssertionError('Failed clone left a partial destination')
        if file_hashes(original) != original_hashes:
            raise AssertionError('Failure changed the source plan')
        summary = clustering.cluster(original, clustered, shards=2, checkpoint_tasks=16)
        if file_hashes(original) != original_hashes:
            raise AssertionError('Successful clone changed the source plan')
        original_manifest = load(original / 'manifest.json')
        clustered_manifest = load(clustered / 'manifest.json')
        for key in ('seed', 'seed_scheme', 'inputs_manifest_sha256', 'executable_sha256', 'build_record',
                    'campaign_weights', 'allocation', 'purpose', 'backend', 'threads'):
            if original_manifest[key] != clustered_manifest[key]:
                raise AssertionError(f'Scientific run identity changed: {key}')
        for group in original_manifest['groups']:
            _, old_cfg = prod.group_of(original, original_manifest, group['name'])
            _, new_cfg = prod.group_of(clustered, clustered_manifest, group['name'])
            allowed = {'shards', 'block_order', 'tasks_sha256', 'checkpoint_layout'}
            if {key: value for key, value in old_cfg.items() if key not in allowed} != {
                    key: value for key, value in new_cfg.items() if key not in allowed}:
                raise AssertionError('Scientific group configuration changed')
        existing_hashes = file_hashes(clustered)
        try:
            clustering.cluster(original, clustered)
        except FileExistsError:
            pass
        else:
            raise AssertionError('An existing destination was overwritten')
        if file_hashes(clustered) != existing_hashes:
            raise AssertionError('Refused duplicate changed the destination')
        if summary['totals']['schedule']['graph_loads'] >= summary['totals']['source_schedule']['graph_loads']:
            raise AssertionError('Test schedule did not reduce graph loading')
        for directory in (original, clustered):
            run('run_local.py', directory, '--workers', '2', '--threads', '1')
            run('production.py', 'merge', directory, '--scratch', directory / 'local_scratch')
            run('assemble.py', directory, '--bootstrap', '16')
            result = load(directory / 'C8_test_result.json')
            if result['C8_full'] is not None or result['coefficients'] is not None or not result['test_only']:
                raise AssertionError('Incomplete test emitted a physical C8 result')
        original_rows, clustered_rows = scientific_rows(original), scientific_rows(clustered)
        if original_rows != clustered_rows:
            raise AssertionError('Scheduling changed native sample coordinates, values, promotion counters, or maximum')
        for entry in original_manifest['groups']:
            old = original / 'groups' / entry['name']
            new = clustered / 'groups' / entry['name']
            if load(old / 'merged.json')['batches'] != load(new / 'merged.json')['batches']:
                raise AssertionError('Scheduling changed graph-summed replicate jets')
            if (old / 'graph_replicates.csv').read_bytes() != (new / 'graph_replicates.csv').read_bytes():
                raise AssertionError('Scheduling changed merged graph replicate data')
        for directory in (original, clustered):
            try:
                clustering.cluster(directory, base / 'refused_started')
            except ValueError:
                pass
            else:
                raise AssertionError('An executed campaign was accepted for rescheduling')
        report = {'status': 'passed', 'schema': 'c8-d2-graph-scheduling-test-1',
                  'native_executable_sha256': original_manifest['executable_sha256'],
                  'groups': len(original_rows), 'native_tasks_compared': sum(len(rows) for rows in original_rows.values()),
                  'exact_native_scientific_rows_equal': True, 'exact_merged_replicate_jets_equal': True,
                  'exact_graph_replicates_csv_equal': True, 'scientific_manifest_and_group_configuration_preserved': True,
                  'source_untouched': True, 'staging_failure_left_no_partial_destination': True,
                  'existing_destination_refused': True, 'executed_campaign_refused': True,
                  'physical_result_keys_null': True, 'placement_summary': summary,
                  'scope': 'Actual native integration of 2 inexpensive graphs per group (1 where only 1 exists), '
                           '4 replicates and 8 points per graph, split into 4-point chunks; incomplete physical calculation.'}
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
