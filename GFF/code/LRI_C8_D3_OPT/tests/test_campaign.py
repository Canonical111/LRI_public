#!/usr/bin/env python3
"""Independent covariance, complete-net and coverage failure regression tests."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import assemble
from campaign import SCHEMA, LOOPS, SECTORS
from io_utils import digest, object_hash, save
from rg import coefficients


def empty_arrays(replicates=8):
    return {s: {t: {loop: np.zeros((replicates, 2*(9-loop))) for loop in LOOPS}
                for t in ('a', 'b')} for s in SECTORS}


def synthetic_checkpoint(root, *, problem=None):
    """Small complete work ledger; no integration or physical reference used."""
    inputs, directory = root/'inputs', root/'campaign'
    inputs.mkdir()
    (directory/'jobs').mkdir(parents=True)
    inventory = {s: {str(loop): [{'id': 1}] for loop in LOOPS} for s in SECTORS}
    if problem == 'omitted_graph':
        inventory['free']['8'].append({'id': 2})
    save(inputs/'inventory.json', inventory)
    (inputs/'gamma_d3_8.txt').write_text('test-only data; no native worker invocation\n')
    save(inputs/'two_loop.json', {'dimension': 3, 'order': 8, 'B2': [0]*7})
    coverage = {'complete': problem != 'incomplete_coverage',
                'inventory_sha256': digest(inputs/'inventory.json')}
    if problem == 'stale_coverage':
        coverage['inventory_sha256'] = '0'*64
    save(inputs/'coverage.json', coverage)
    groups, jobs, data_records = [], [], []
    evaluations = 0
    for tag in ('a', 'b'):
        for sector in SECTORS:
            for loop in LOOPS:
                name = f'{tag}_{sector}_L{loop}'
                group = {'name': name, 'campaign': tag, 'sector': sector, 'L': loop,
                         'rate': .8 if tag == 'a' else .7, 'bits': 52 if tag == 'a' else 60,
                         'seeds': {'shift': 7000+len(groups)}, 'graphs': [{'id': 1, 'points': 4}]}
                groups.append(group)
                tasks, native_rows = [], []
                for rep in range(4):
                    bounds = [(0, 2), (2, 4)]
                    if name == 'a_free_L3' and rep == 0:
                        if problem == 'chunk_gap':
                            bounds = [(0, 1), (2, 4)]
                        elif problem == 'chunk_overlap':
                            bounds = [(0, 3), (2, 4)]
                        elif problem == 'changed_net_size':
                            bounds = [(0, 2), (2, 3)]
                    for begin, end in bounds:
                        uid = len(tasks)
                        tasks.append([uid, rep, 1, begin, end, 4])
                        native_rows.append({'uid': uid, 'rep': rep, 'graph': 1,
                                            'begin': begin, 'end': end, 'total': 4,
                                            'values': [str((rep+1)/2)]*(2*(9-loop)),
                                            'quad': 0, 'mp': 0, 'seconds': .001})
                        evaluations += end-begin
                index = len(jobs)
                job = {'index': index, 'group': name, 'L': loop, 'tasks': tasks}
                base = directory/'jobs'/f'{index:06d}'
                save(base.with_suffix('.job.json'), job)
                entry = {'index': index, 'group': name, 'sha256': object_hash(job)}
                jobs.append(entry)
                data = {'schema': 'c8-d3-hpc-native-1', 'L': loop, 'seed': group['seeds']['shift'],
                        'bits': group['bits'], 'layout': 0, 'sum_mode': 'compensated',
                        'rate': str(group['rate']), 'mp_backend': 'gmp350', 'rows': native_rows}
                if name == 'a_free_L3':
                    if problem == 'changed_rate':
                        data['rate'] = '0.75'
                    elif problem == 'missing_jet':
                        data['rows'][0]['values'].pop()
                save(base.with_suffix('.native.json'), data)
                data_records.append((base, entry))
    if problem == 'duplicate_group':
        groups.append(copy.deepcopy(groups[0]))
    if problem == 'duplicate_graph':
        groups[0]['graphs'].append(copy.deepcopy(groups[0]['graphs'][0]))
    if problem == 'changed_group_label':
        groups[0]['sector'] = 'power'
    manifest = {'schema': SCHEMA, 'campaign_weights': {'a': .5, 'b': .5},
                'loops': list(LOOPS), 'all_loops': True,
                'coverage_verified': problem != 'unverified_coverage',
                'inputs': {name: digest(inputs/name) for name in
                           ('inventory.json', 'gamma_d3_8.txt', 'two_loop.json', 'coverage.json')},
                'groups': groups, 'jobs': jobs, 'replicates': 4, 'evaluations': evaluations,
                'executable': {'description': {'mp_backend': 'gmp350'}}}
    save(directory/'manifest.json', manifest)
    manifest_hash = digest(directory/'manifest.json')
    for base, entry in data_records:
        save(base.with_suffix('.done.json'), {'manifest_sha256': manifest_hash,
             'job_sha256': entry['sha256'], 'native_sha256': digest(base.with_suffix('.native.json'))})
    return directory


class CovarianceChecks(unittest.TestCase):
    def test_top_loop_correlated_channels_and_campaign_weights(self):
        arrays = empty_arrays()
        projected = []
        for n, (sector, tag) in enumerate((s, t) for s in SECTORS for t in ('a', 'b')):
            x = np.array([-4, -2, -1, 0, 1, 2, 3, 7.], float)*(n+1)
            arrays[sector][tag][8][:, 0] = 5+2*x
            arrays[sector][tag][8][:, 1] = 1+3*x
            projected.append((3*arrays[sector][tag][8][:, 1]-arrays[sector][tag][8][:, 0])/19683)
        result, _ = assemble.calculate(arrays, b2=np.zeros(7), bootstrap=0)
        expected_mean = sum(x.mean() for x in projected)/2
        expected_variance = sum(x.var(ddof=1)/len(x) for x in projected)/4
        self.assertAlmostEqual(result['C8_estimate'], expected_mean, delta=abs(expected_mean)*1e-13)
        self.assertAlmostEqual(result['sampling_standard_error']**2, expected_variance, delta=expected_variance*1e-13)
        # All values fluctuate on one common direction per b/c pair; ignoring
        # their covariance gives an observably different uncertainty.
        diagonal_only = sum((x[:, 0].var(ddof=1)+9*x[:, 1].var(ddof=1))/len(x)
                            for s in SECTORS for t in ('a', 'b') for x in (arrays[s][t][8],))/4/19683**2
        self.assertGreater(abs(diagonal_only-expected_variance), expected_variance*.5)

    def test_nonlinear_power_difference_and_covariance_decomposition(self):
        rng = np.random.default_rng(392705)
        arrays = {s: {t: {loop: rng.normal(size=(12, 2*(9-loop)))*.2
                         for loop in LOOPS} for t in ('a', 'b')} for s in SECTORS}
        b2 = np.array([-9.7, 13.1, -16.3, 19.5, -22.7, 26.0, -29.2])
        result, _ = assemble.calculate(arrays, b2, bootstrap=0)
        means = {s: {loop: sum(arrays[s][t][loop].mean(0) for t in ('a', 'b'))/2
                     for loop in LOOPS} for s in SECTORS}
        full = coefficients({loop: means['free'][loop]+means['power'][loop] for loop in LOOPS}, b2)
        free = coefficients(means['free'], b2)
        self.assertAlmostEqual(result['power_correction'], (full-free)[8], delta=1e-12)
        raw_top = (3*means['power'][8][1]-means['power'][8][0])/19683
        self.assertGreater(abs(result['power_correction']-raw_top), 1e-5)
        variance = result['power_free_se']**2+result['power_correction_se']**2+2*result['power_free_correction_covariance']
        self.assertAlmostEqual(variance, result['sampling_standard_error']**2, delta=max(1e-15, abs(variance)*1e-12))


class CoverageChecks(unittest.TestCase):
    def read_fixture(self, problem=None):
        with tempfile.TemporaryDirectory(prefix='campaign-test-', dir=ROOT/'tests') as name:
            root = Path(name)
            directory = synthetic_checkpoint(root, problem=problem)
            with patch.object(assemble, 'ROOT', root):
                return assemble.read_replicates(directory)

    def test_complete_chunks_are_summed_before_replicate_statistics(self):
        arrays, graph_arrays, _, manifest, _ = self.read_fixture()
        self.assertEqual(manifest['evaluations'], 24*4*4)
        for sector in SECTORS:
            for tag in ('a', 'b'):
                for loop in LOOPS:
                    value = arrays[sector][tag][loop]
                    self.assertEqual(value.shape, (4, 2*(9-loop)))
                    np.testing.assert_array_equal(value[:, 0], [1, 2, 3, 4])
        self.assertEqual(len(graph_arrays), 24)

    def test_incomplete_or_stale_coverage_fails(self):
        for problem in ('unverified_coverage', 'incomplete_coverage', 'stale_coverage', 'omitted_graph'):
            with self.subTest(problem=problem), self.assertRaises(ValueError):
                self.read_fixture(problem)

    def test_duplicate_or_mislabelled_work_fails(self):
        for problem in ('duplicate_group', 'duplicate_graph', 'changed_group_label'):
            with self.subTest(problem=problem), self.assertRaises(ValueError):
                self.read_fixture(problem)

    def test_complete_net_gaps_overlaps_or_changes_fail(self):
        for problem in ('chunk_gap', 'chunk_overlap', 'changed_net_size'):
            with self.subTest(problem=problem), self.assertRaises(ValueError):
                self.read_fixture(problem)

    def test_changed_native_configuration_or_missing_jet_fails(self):
        for problem in ('changed_rate', 'missing_jet'):
            with self.subTest(problem=problem), self.assertRaises(ValueError):
                self.read_fixture(problem)

    def test_manifest_input_and_output_mutations_fail(self):
        for target in ('manifest', 'input', 'native'):
            with self.subTest(target=target), tempfile.TemporaryDirectory(prefix='campaign-test-', dir=ROOT/'tests') as name:
                root = Path(name)
                directory = synthetic_checkpoint(root)
                if target == 'manifest':
                    path = directory/'manifest.json'
                    value = json.loads(path.read_text())
                    value['replicates'] = 6
                    path.write_text(json.dumps(value))
                elif target == 'input':
                    (root/'inputs'/'gamma_d3_8.txt').write_text('altered gamma input\n')
                else:
                    path = directory/'jobs'/'000000.native.json'
                    value = json.loads(path.read_text())
                    value['rows'][0]['values'][0] = '1000000'
                    path.write_text(json.dumps(value))
                with patch.object(assemble, 'ROOT', root), self.assertRaises(ValueError):
                    assemble.read_replicates(directory)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'status': 'passed' if result.wasSuccessful() else 'failed',
              'tests': result.testsRun,
              'scope': 'Synthetic independent covariance and fail-closed complete-net/coverage checks; no physical samples.'}
    (ROOT/'verification').mkdir(exist_ok=True)
    (ROOT/'verification'/'campaign_checks.json').write_text(json.dumps(report, indent=2)+'\n')
    sys.exit(0 if result.wasSuccessful() else 1)
