#!/usr/bin/env python3
"""Expanse-profile tests: profile facts, the launch commands documented in
cluster/expanse/README.md (dry runs against a fake site), wrapper syntax.
Run cluster/sitekit/test_sitekit.py for the shared layer."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
PKG = HERE.parents[1]
sys.path.insert(0, str(PKG / 'cluster' / 'sitekit'))
from test_sitekit import dry_run_submit, export_of, run_cases   # noqa: E402
import submit                                                    # noqa: E402


class ExpanseProfileTests(unittest.TestCase):
    def setUp(self):
        self.p = submit.load_profile('expanse')

    def test_facts(self):
        p = self.p
        self.assertEqual(p['scheduler']['account'], '<ACCOUNT>')
        self.assertEqual(p['scheduler']['job_prefix'], 'lri_c2_')
        self.assertEqual(p['paths']['persistent_root'], '/expanse/lustre/scratch/{user}/temp_project/lri_c2')
        self.assertEqual(p['paths']['node_scratch_base'], '/scratch/{user}')
        self.assertFalse(p['paths']['clean_node_scratch'])          # Slurm removes /scratch/$USER/job_<id>
        self.assertEqual(p['partitions']['large-shared']['running_per_user'], 2)
        self.assertEqual((p['scheduler']['normal_qos_running_cap'], p['scheduler']['normal_qos_keep_free']), (32, 10))
        for name, part in p['partitions'].items():
            self.assertLessEqual(part['max_hours'], 48, name)

    def test_profiles_respect_limits(self):
        for n, prof in self.p['profiles'].items():
            for kind, r in prof.items():
                part = self.p['partitions'][r['partition']]
                self.assertLessEqual(r['mem_gb'], part['max_mem_gb'], (n, kind))
                self.assertLessEqual(submit.hours(r['time']), part['max_hours'], (n, kind))
                if not part.get('whole_node'):
                    self.assertLessEqual(r['cpus'], 64, (n, kind))
                if kind == 'task':
                    self.assertEqual(r.get('rows_per_job', 1), 1)

    def test_documented_launch_commands(self):
        r, cmds = dry_run_submit('expanse', '--stage', 'P2')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        grid, rows = cmds
        self.assertEqual(grid[grid.index('-p') + 1], 'large-shared')
        self.assertIn('--array=4,5%2', rows)                      # large-shared: 2 running per user
        self.assertEqual(export_of(grid)['LRI_STRIPE'], '8')
        self.assertEqual(export_of(grid)['LRI_GRID_WORKERS'], '32')
        self.assertTrue(grid[grid.index('-J') + 1].startswith('lri_c2_grid_N1024'))
        r, cmds = dry_run_submit('expanse', '--tasks', '2')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('--array=2%3', cmds[-1])
        r, cmds = dry_run_submit('expanse', '--plan', str(PKG / 'cluster/smoke_plan.json'), '--resources-profile', 'smoke')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(cmds[0][cmds[0].index('-p') + 1], 'debug')

    def test_wrappers(self):
        for f in ['make_tarball.sh', 'collect.sh', 'setup_env.sh']:
            self.assertEqual(subprocess.run(['bash', '-n', str(HERE / f)]).returncode, 0, f)
        r = subprocess.run([sys.executable, str(HERE / 'submit.py'), '--check'], capture_output=True, text=True)
        self.assertIn('SITE expanse', r.stdout)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    run_cases([ExpanseProfileTests], parser.parse_args().output,
              'Expanse profile, documented launch commands (dry runs against a fake site), wrapper syntax.')
