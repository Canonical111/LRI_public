#!/usr/bin/env python3
"""Plan and mocked Slurm launcher checks; never submits work to a scheduler."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import production as prod
import slurm_submit as slurm
from common import digest, load


class FrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='c8_hpc_cli_', dir=ROOT / 'verification')
        cls.base = Path(cls.temporary.name)
        cls.run_dir = cls.base / 'run'
        cost = cls.base / 'test_cost.json'
        cost.write_text(json.dumps({'schema': 'c8-d2-cost-model-1', 'dimension': 2, 'order': 8,
                                    'backend': 'gmp', 'seconds_per_point': {'free:3:0': 0.0025},
                                    'scope': 'Synthetic parser/layout fixture; not a performance measurement.'}))
        cls.environment = dict(os.environ, OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
        command = [sys.executable, '-B', str(ROOT / 'tools/production.py'), 'plan', str(cls.run_dir),
                   '--seed', '8795672985463472', '--backend', 'gmp', '--points', '4', '--replicates', '4',
                   '--test-graphs', '1', '--shards', '2', '--shard-policy', 'uniform', '--threads', '1',
                   '--checkpoint-tasks', '16', '--checkpoint-graphs', '1', '--checkpoint-seconds', '0.011',
                   '--cost-model', str(cost)]
        result = subprocess.run(command, cwd=ROOT, env=cls.environment, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(f'Plan failed: {result.stdout}\n{result.stderr}')
        cls.manifest = load(cls.run_dir / 'manifest.json')
        cls.fake_python = cls.base / 'fake_python'
        cls.fake_python.write_text('#!/usr/bin/env python3\nimport json,os,sys\n'
                                  'with open(os.environ["C8_TEST_CALL_LOG"],"a") as f:\n'
                                  ' json.dump({"args":sys.argv[1:],"affinity":{k:os.environ.get(k) for k in ("OMP_DYNAMIC","OMP_PLACES","OMP_PROC_BIND")}},f);f.write("\\n")\n')
        cls.fake_python.chmod(0o700)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_plan_layout_and_runtime_helper_pins(self):
        m = self.manifest
        self.assertTrue(m['test_only']); self.assertEqual(m['task_order'], 'graph')
        self.assertTrue({'task_schedule.py', 'stage_runtime.py', 'slurm_submit.py'} <= set(m['tool_sha256']))
        for name, checksum in m['tool_sha256'].items(): self.assertEqual(digest(ROOT / 'tools' / name), checksum)
        for group in m['groups']:
            path, cfg = prod.group_of(self.run_dir, m, group['name'])
            self.assertEqual(cfg['shards'], 1)
            self.assertEqual(cfg['checkpoint_layout']['target_measured_seconds'], 0.011)
            self.assertEqual(cfg['checkpoint_layout']['indivisible_tasks_above_time_target'], 0)
            db = prod.dbopen(path / 'tasks.sqlite', True)
            try:
                blocks = list(prod.task_blocks(db, 0, m['checkpoint_tasks'], with_cost=True))
                self.assertEqual(len(blocks), 4)
                self.assertTrue(all(len(block) == 1 for block in blocks))
                self.assertTrue(all(sum(row[-1] for row in block) <= 0.011 for block in blocks))
            finally: db.close()

    def test_invalid_limits_refused_before_directory_creation(self):
        cases = [('--checkpoint-graphs', '0'), ('--checkpoint-seconds', '0'),
                 ('--checkpoint-seconds', 'nan'), ('--checkpoint-seconds', '120'),
                 ('--task-order', 'legacy', '--checkpoint-graphs', '1')]
        for i, extra in enumerate(cases):
            directory = self.base / f'invalid{i}'
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/production.py'), 'plan', str(directory),
                                     '--seed', '325262345', *extra], capture_output=True, text=True, env=self.environment)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(directory.exists())

    def test_merge_cpu_request_matches_worker_count(self):
        for requested, expected in (('4', 4), ('999', 24)):
            env = dict(self.environment, C8_RUN=str(self.run_dir), C8_MERGE_WORKERS=requested,
                       C8_SBATCH_ARGS='--time=00:10:00 --cpus-per-task=2')
            context = slurm.Context(env, [])
            with patch.object(context, 'sbatch', return_value='TEST_ONLY_NO_SUBMISSION') as submit:
                context.merge(['123'])
            options = submit.call_args.args[0]
            self.assertEqual([arg for arg in options if arg.startswith('--cpus-per-task=')][-1], f'--cpus-per-task={expected}')
            self.assertEqual(context.sbatch_env()['C8_MERGE_WORKERS'], str(expected))
        with self.assertRaises(slurm.Refuse):
            slurm.Context(dict(self.environment, C8_RUN=str(self.run_dir), C8_MERGE_WORKERS='0'), [])

    def launcher(self, script, suffix, **changes):
        log = self.base / f'calls_{suffix}.jsonl'
        env = dict(self.environment, C8_PACKAGE=str(ROOT), C8_RUN=str(self.run_dir), C8_ENV_SETUP='',
                   C8_PYTHON=str(self.fake_python), C8_TEST_CALL_LOG=str(log), C8_STAGE='0',
                   SLURM_ARRAY_TASK_ID='0', C8_INDEX_OFFSET='0', SLURM_CPUS_PER_TASK='1')
        env.pop('OMP_PLACES', None); env.pop('OMP_PROC_BIND', None)
        env.update(changes)
        result = subprocess.run(['bash', str(ROOT / 'slurm' / script)], env=env, capture_output=True, text=True)
        records = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return result, records

    def test_affinity_defaults_and_explicit_override(self):
        for label, variables, expected in (
                ('default', {}, {'OMP_DYNAMIC': 'FALSE', 'OMP_PLACES': 'cores', 'OMP_PROC_BIND': 'close'}),
                ('explicit', {'OMP_PLACES': 'threads', 'OMP_PROC_BIND': 'spread'},
                 {'OMP_DYNAMIC': 'FALSE', 'OMP_PLACES': 'threads', 'OMP_PROC_BIND': 'spread'})):
            result, records = self.launcher('run_array.sh', label, **variables)
            self.assertEqual(result.returncode, 0, result.stderr)
            execution = [row for row in records if 'run' in row['args']][-1]
            self.assertEqual(execution['affinity'], expected)

    def test_merge_launcher_refuses_cpu_oversubscription(self):
        result, records = self.launcher('merge.sh', 'refused', C8_MERGE_WORKERS='4', SLURM_CPUS_PER_TASK='2')
        self.assertEqual(result.returncode, 64)
        self.assertFalse(any('merge' in row['args'] for row in records))
        result, records = self.launcher('merge.sh', 'allowed', C8_MERGE_WORKERS='4', SLURM_CPUS_PER_TASK='4')
        self.assertEqual(result.returncode, 0, result.stderr)
        execution = [row for row in records if 'merge' in row['args']][-1]
        self.assertEqual(execution['args'][-2:], ['--workers', '4'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FrontendTests))
    report = {'schema': 'c8-d2-hpc-cli-tests-1', 'status': 'passed' if result.wasSuccessful() else 'failed',
              'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'native_executable_sha256': digest(prod.exe_for('gmp')),
              'scope': 'Real incomplete plan construction with synthetic cost fixture; Slurm and native launchers mocked. No scheduler submission.',
              'checks': ['default graph scheduling', 'explicit time/graph/task limits wired to plan', 'new helper source hash pins',
                         'invalid limits leave no run directory', 'merge CPU request equals worker count',
                         'merge worker count capped to groups', 'affinity defaults and user overrides',
                         'merge launcher refuses CPU oversubscription']}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__': main()
