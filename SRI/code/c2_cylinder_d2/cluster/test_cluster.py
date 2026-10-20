#!/usr/bin/env python3
"""Small regression tests for cluster wrappers; no large production runs."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_task import exclusive, load_plan, verify_grid, grid_key
from resource_estimate import estimate
from collect_records import index_records


class ClusterTests(unittest.TestCase):
    def test_plans(self):
        for name, count in [('extension_plan.json', 9), ('smoke_plan.json', 1)]:
            plan, jobs = load_plan(HERE / name)
            self.assertEqual(len(jobs), count)
            self.assertEqual(plan['physical_delta'], 0)
            self.assertTrue(all('workers' not in j for j in jobs))

    def test_bad_plan(self):
        obj = json.loads((HERE / 'smoke_plan.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'bad.json'
            for value in [0, -1, float('inf')]:
                bad = copy.deepcopy(obj)
                bad['jobs'][0]['lambda'] = [value]
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    load_plan(path)
            obj['physical_delta'] = .05
            path.write_text(json.dumps(obj))
            with self.assertRaises(ValueError):
                load_plan(path)

    def test_optional_plan_keys(self):
        obj = json.loads((HERE / 'smoke_plan.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'plan.json'
            good = copy.deepcopy(obj)
            good['jobs'][0].update(tail_cutoff=4096, stage='P1')
            path.write_text(json.dumps(good))
            self.assertEqual(load_plan(path)[1][0]['tail_cutoff'], 4096)
            for key, value in [('tail_cutoff', 32), ('tail_cutoff', 2048.0), ('tail_cutoff', True), ('stage', 'a b')]:
                bad = copy.deepcopy(obj)
                bad['jobs'][0][key] = value
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    load_plan(path)

    def test_lock(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            with exclusive(path):
                with self.assertRaises(RuntimeError):
                    with exclusive(path):
                        self.fail('Second writer acquired lock')
            self.assertFalse((path / '.writer.lock').exists())

    def test_resource_formula(self):
        row = estimate(384, 4)
        self.assertEqual(row['coefficient_bytes'], 6 * 385**3 * 8)
        self.assertEqual(row['temporary_bytes'], 6 * (row['M'] // 2 + 1) * 385**2 * 16)
        self.assertEqual(row['M'] % 2, 0)
        self.assertEqual(grid_key(512, 4, 4.5), 'N512_o4_r4p5')

    def test_cache_metadata_and_shape(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'array.npy'
            np.save(path, np.zeros((6, 5, 5, 5)))
            path.with_suffix('.json').write_text(json.dumps({'K': 5, 'oversample': 4, 'radius_cost': 4.5}))
            verify_grid(path, 4, 4, 4.5)
            with self.assertRaises(ValueError):
                verify_grid(path, 5, 4, 4.5)
            path.with_suffix('.json').unlink()
            with self.assertRaises(ValueError):
                verify_grid(path, 4, 4, 4.5)

    def test_collector_keeps_variants(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            for n, name in [(8, 'a'), (12, 'b')]:
                # Records of the solver's shape: the collector validates sequence lengths,
                # embedded cutoffs and the order/lambda/N in the file name.
                seq = list(range(n))
                row = {'N': n, 'order': 2, 'lam': .1, 'coefficient_file': f'{name}.npy',
                       'raw': {'lam': .1, 'order': 2, 'Nmax': n, 'Xchain': seq,
                               'parts': [{'pairing': 'adjacent', 'X': seq}]},
                       'mixed': {'lam': .1, 'order': 2, 'Nmax': 32, 'Xmixed': [0.0] * 32},
                       'two_point': {'lam': .1, 'N': 2000}}
                (directory / f'cluster_k2_a0.1_N{n}.json').write_text(json.dumps(row))
            report = index_records([directory], '*.json', True)
            self.assertEqual(len(report['records']), 2)
            self.assertEqual(len(report['overlap_comparisons']), 1)
            self.assertEqual(report['overlap_comparisons'][0]['max_abs_raw_chain_difference'], 0.)
            self.assertEqual(report['overlap_comparisons'][0]['overlap_N'], 8)

    def test_dry_run_creates_no_work(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            command = [sys.executable, str(HERE / 'run_task.py'), 'run', '--plan', str(HERE / 'smoke_plan.json'),
                       '--task-index', '0', '--work-root', str(directory / 'work'),
                       '--output-root', str(directory / 'out'), '--dry-run']
            result = subprocess.run(command, text=True, capture_output=True, check=True)
            data = json.loads(result.stdout)
            self.assertFalse(data['physical_C2_claimed'])
            self.assertFalse((directory / 'work').exists())
            self.assertFalse((directory / 'out').exists())

    def test_slurm_script_syntax(self):
        subprocess.run(['bash', '-n', str(HERE / 'slurm_array.sh')], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ClusterTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'tests_run': result.testsRun, 'successful': result.wasSuccessful(),
              'failures': [str(x[0]) for x in result.failures], 'errors': [str(x[0]) for x in result.errors],
              'scope': 'Cluster-wrapper unit tests, plan validation (including the optional tail_cutoff/stage keys), dry-run isolation, metadata checks, record indexing, resource formulas and shell syntax. No large spectral grids or cluster scheduling were exercised.'}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == '__main__':
    main()
