#!/usr/bin/env python3
"""Bounded scheduler, streaming coverage and local pack-cache regression checks."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import tracemalloc
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import cluster_graph_tasks as cluster
import task_schedule as schedule
import stage_runtime as staging


def database(path, graphs=9, replicates=8, chunks=2, legacy_shards=2):
    db = sqlite3.connect(path)
    db.executescript('CREATE TABLE tasks(uid INTEGER PRIMARY KEY,rep INTEGER,gi INTEGER,lo INTEGER,hi INTEGER,total INTEGER,cost REAL,shard INTEGER,pos INTEGER);CREATE TABLE expected(rep INTEGER,gi INTEGER,total INTEGER,PRIMARY KEY(rep,gi));')
    positions = [0] * legacy_shards
    uid = 0
    for rep in range(replicates):
        for graph in range(graphs):
            db.execute('INSERT INTO expected VALUES(?,?,?)', (rep, graph, chunks * 4))
            for chunk in range(chunks):
                shard = uid % legacy_shards
                db.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)',
                           (uid, rep, graph, 4 * chunk, 4 * (chunk + 1), chunks * 4,
                            float(graph + 1), shard, positions[shard]))
                uid += 1; positions[shard] += 1
    db.executescript('CREATE INDEX shard_order ON tasks(shard,pos);CREATE INDEX stream_order ON tasks(rep,gi,lo);')
    db.commit()
    cfg = {'replicates': replicates, 'counts': {str(i): chunks * 4 for i in range(graphs)},
           'tasks': uid, 'samples': graphs * replicates * chunks * 4}
    return db, cfg


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='c8_scheduler_', dir=ROOT / 'verification')
        self.path = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_scientific_identity_limits_and_legacy(self):
        db, cfg = database(self.path / 'tasks.sqlite')
        before = cluster.task_identity(db, cfg)
        # Legacy plans need no descriptor table and retain exact old cuts.
        for shard in range(2):
            rows = list(schedule.rows_for(db, shard))
            self.assertEqual(list(schedule.task_blocks(db, shard, 11)), [rows[i:i + 11] for i in range(0, len(rows), 11)])
        shards, costs = schedule.assign_graph_bundles(db, 3)
        stats = schedule.freeze_blocks(db, shards, 11, max_graphs=2, target_seconds=29.0)
        self.assertEqual(before, cluster.task_identity(db, cfg))
        seen = []
        loads = 0
        for shard in range(shards):
            blocks = list(schedule.task_blocks(db, shard, 11, with_cost=True))
            self.assertEqual(len(blocks), schedule.block_count(db, shard, 11))
            for block in blocks:
                self.assertLessEqual(len(block), 11)
                self.assertLessEqual(len({row[2] for row in block}), 2)
                self.assertLessEqual(sum(row[6] for row in block), 29.0)
                loads += len({row[2] for row in block})
                seen.extend(row[0] for row in block)
        self.assertEqual(sorted(seen), list(range(cfg['tasks'])))
        self.assertEqual(loads, stats['graph_loads'])
        self.assertFalse(db.execute('SELECT gi FROM tasks GROUP BY gi HAVING COUNT(DISTINCT shard)>1').fetchall())
        db.close()

    def test_whole_bundles_and_oversize_task_report(self):
        db, cfg = database(self.path / 'tasks.sqlite', graphs=4, replicates=4, chunks=1)
        shards, _ = schedule.assign_graph_bundles(db, 2)
        stats = schedule.freeze_blocks(db, shards, 12, max_graphs=2, target_seconds=100)
        self.assertEqual(stats['graph_loads'], 4)
        self.assertEqual(stats['graph_bundles_split_for_task_limit'], 0)
        db.execute('UPDATE tasks SET cost=1000 WHERE uid=0'); db.commit()
        stats = schedule.freeze_blocks(db, shards, 12, max_graphs=2, target_seconds=25)
        self.assertEqual(stats['indivisible_tasks_above_time_target'], 1)
        for shard in range(shards):
            for block in schedule.task_blocks(db, shard, 12, with_cost=True):
                if sum(row[-1] for row in block) > 25:
                    self.assertEqual(len(block), 1)
                    self.assertEqual(block[0][0], 0)
        db.close()

    def test_explicit_corruption_and_coordinate_rejection(self):
        db, cfg = database(self.path / 'tasks.sqlite')
        shards, _ = schedule.assign_graph_bundles(db, 2)
        schedule.freeze_blocks(db, shards, 13, max_graphs=2)
        db.execute('UPDATE checkpoint_blocks SET first_pos=first_pos+1 WHERE shard=0 AND part=0')
        with self.assertRaises(ValueError): list(schedule.task_blocks(db, 0, 13))
        db.rollback()
        db.execute('DELETE FROM checkpoint_blocks WHERE shard=0 AND part=(SELECT MAX(part) FROM checkpoint_blocks WHERE shard=0)')
        with self.assertRaises(ValueError): list(schedule.task_blocks(db, 0, 13))
        db.rollback()
        db.execute('UPDATE tasks SET lo=1 WHERE uid=0')
        with self.assertRaises(ValueError): cluster.task_identity(db, cfg)
        db.rollback(); db.close()

    def test_streamed_validation_memory(self):
        db, cfg = database(self.path / 'large.sqlite', graphs=32, replicates=1024, chunks=1)
        tracemalloc.start()
        identity = cluster.task_identity(db, cfg)
        _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
        self.assertEqual(identity['expected_streams'], 32768)
        self.assertLess(peak, 1_000_000, 'Expected-coordinate validation materialized a replicate x graph list')
        self.__class__.stream_validation_peak_bytes = peak
        db.close()

    def test_cache_single_publication_concurrency_reuse_and_corruption(self):
        source = self.path / 'source.pack'; source.write_bytes(bytes(range(256)) * 8192)
        checksum = hashlib.sha256(source.read_bytes()).hexdigest()
        cache = self.path / 'cache'
        with ThreadPoolExecutor(max_workers=8) as pool:
            outputs = list(pool.map(lambda _: staging.cached_pack(source, checksum, cache), range(8)))
        self.assertEqual(sum(copied for path, copied in outputs), 1)
        self.assertEqual(len({path for path, copied in outputs}), 1)
        pack = outputs[0][0]
        with patch.object(staging, 'digest', side_effect=AssertionError('A valid cache hit should not reread the whole pack')):
            same, copied = staging.cached_pack(source, checksum, cache)
        self.assertEqual(same, pack); self.assertFalse(copied)
        os.chmod(pack, 0o644)
        with pack.open('r+b') as output: output.write(b'CORRUPTED')
        repaired, copied = staging.cached_pack(source, checksum, cache)
        self.assertTrue(copied); self.assertEqual(staging.digest(repaired), checksum)
        verified, copied = staging.cached_pack(source, checksum, cache, reverify=True)
        self.assertFalse(copied); self.assertEqual(verified, pack)
        self.assertFalse(list(cache.glob('*.copy_*')))

    def test_cache_symlink_and_unsafe_directory_rejection(self):
        source = self.path / 'source.pack'; source.write_bytes(b'valid source')
        checksum = staging.digest(source)
        cache = self.path / 'cache'; cache.mkdir()
        (cache / (checksum + '.pack')).symlink_to(source)
        with self.assertRaises(ValueError): staging.cached_pack(source, checksum, cache)
        (cache / (checksum + '.pack')).unlink()
        cache.chmod(0o777)
        with self.assertRaises(ValueError): staging.cached_pack(source, checksum, cache)

    def test_interrupted_cache_copy_never_publishes_partial_pack(self):
        source = self.path / 'source.pack'; source.write_bytes(b'complete pack contents')
        checksum = staging.digest(source); cache = self.path / 'cache'
        def interrupted_copy(original, temporary):
            Path(temporary).write_bytes(b'partial')
            raise OSError('injected interrupted transfer')
        with patch.object(staging.shutil, 'copyfile', side_effect=interrupted_copy):
            with self.assertRaises(OSError): staging.cached_pack(source, checksum, cache)
        self.assertFalse((cache / (checksum + '.pack')).exists())
        self.assertFalse(list(cache.glob('*.copy_*')))
        pack, copied = staging.cached_pack(source, checksum, cache)
        self.assertTrue(copied); self.assertEqual(staging.digest(pack), checksum)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SchedulerTests))
    report = {'schema': 'c8-d2-hpc-scheduler-tests-1', 'status': 'passed' if result.wasSuccessful() else 'failed',
              'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'streamed_32768_coordinate_validation_peak_python_bytes': getattr(SchedulerTests, 'stream_validation_peak_bytes', None),
              'coverage': ['exact scientific task and cost identity', 'legacy fixed blocks', 'graph locality',
                           'independent task/graph/time limits', 'indivisible oversized task report',
                           'corrupt/incomplete layout refusal', 'streamed coverage validation',
                           'single concurrent cache publication', 'stat-bound receipt reuse', 'cache corruption recovery',
                           'forced cache rehash', 'interrupted copy never published', 'symlink and unsafe-directory refusal']}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__': main()
