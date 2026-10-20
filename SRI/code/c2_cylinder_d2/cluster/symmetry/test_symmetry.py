#!/usr/bin/env python3
"""Symmetry-profile tests: the standing rules for symmetry (amdq first, defq as
the only fallback, never longq or unprotected preemptible queues, whole nodes,
--exclude=cn112, <= 24 h, <= 32/20 threads per process, mem <= 245G AMD and
<= 180G when Intel is allowed, BeeGFS + /local1, c2ham- job names), the launch
commands in cluster/symmetry/README.md (dry runs against a fake site) and
bash -n of the site scripts. Run cluster/sitekit/test_sitekit.py for the shared layer."""
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


class SymmetryProfileTests(unittest.TestCase):
    def setUp(self):
        self.p = submit.load_profile('symmetry')

    def test_facts(self):
        p = self.p
        self.assertIsNone(p['scheduler']['account'])
        self.assertEqual(p['scheduler']['slurm_path'], '/cm/shared/apps/slurm/current/bin')
        self.assertEqual(p['scheduler']['job_prefix'], 'c2ham-')
        self.assertEqual(p['paths']['persistent_root'], '/mnt/beegfs/{user}/lri_c2')
        self.assertEqual(p['paths']['node_scratch_base'], '/local1/{user}')
        self.assertTrue(p['paths']['clean_node_scratch'])
        self.assertTrue(p['paths']['env'].startswith('{home}/'))
        self.assertEqual(p['modules'], ['python/3.13-mamba'])
        for bad in ['longq', 'amdpreq', 'preq']:
            self.assertIn(bad, p['forbidden_partitions'])
        amd, intel = p['partitions']['amdq'], p['partitions']['defq']
        self.assertEqual((amd['cores_per_package'], amd['max_mem_gb'], amd['exclude']), (32, 245, 'cn112'))
        self.assertEqual((intel['cores_per_package'], intel['max_mem_gb']), (20, 180))
        for name, part in p['partitions'].items():
            self.assertTrue(part['whole_node'], name)
            self.assertLessEqual(part['max_hours'], 24, name)

    def test_profiles_follow_the_rules(self):
        for n, prof in self.p['profiles'].items():
            for kind, r in prof.items():
                parts = r['partition'].split(',')
                if parts[0] not in ('amdq', 'amddebugq'):          # AMD first unless the profile says why not
                    self.assertIn('84 GB', r.get('vendor_reason', ''), f'{n} {kind}: AMD first or a reason')
                self.assertTrue(set(parts) <= {'amdq', 'defq', 'amddebugq', 'debugq'}, (n, kind))
                limit = min(self.p['partitions'][x]['max_mem_gb'] for x in parts)
                self.assertLessEqual(r['mem_gb'], limit, (n, kind))
                self.assertLessEqual(submit.hours(r['time']), min(self.p['partitions'][x]['max_hours'] for x in parts))
                if kind == 'task':
                    self.assertEqual(r['pin'], 'package')
                    self.assertEqual(r['rows_per_job'], 1 if n in ('1024', 'smoke') else 2, n)
        # Every production job ends well inside the 24 h wall (at most half of it).
        for n in ('512', '768', '1024'):
            for kind in ('grid', 'task'):
                self.assertLessEqual(submit.hours(self.p['profiles'][n][kind]['time']), 12)

    def test_grids_that_do_not_fit_amd_local_disk_use_intel(self):
        self.assertEqual(self.p['partitions']['amdq']['tmp_gb'], 84)
        for n in ('768', '1024'):
            self.assertEqual(self.p['profiles'][n]['grid']['partition'], 'defq')
        self.assertEqual(self.p['profiles']['512']['grid']['partition'], 'amdq,defq')
        problems, notes = [], []
        job = {'cutoff': 768, 'oversample': 4, 'mixed_cutoff': 16384, 'tail_cutoff': 8192}
        submit.check_profile(self.p, 'grid', job, dict(self.p['profiles']['768']['grid'], partition='amdq'), problems, notes)
        self.assertTrue(any('scratch' in x for x in problems))

    def test_p1_packs_two_rows_per_node(self):
        r, cmds = dry_run_submit('symmetry', '--stage', 'P1')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(cmds), 3)
        grid, pair, single = cmds
        self.assertEqual(grid[grid.index('-p') + 1], 'defq')
        self.assertNotIn('--exclude=cn112', grid)
        for cmd in (pair, single):
            self.assertIn('--exclude=cn112', cmd)
            self.assertEqual(cmd[cmd.index('-p') + 1], 'amdq,defq')
        for cmd in cmds:
            self.assertIn('--exclusive', cmd)
            self.assertIn('--mem=180G', cmd)
            self.assertNotIn('-A', cmd)
            self.assertTrue(cmd[cmd.index('-J') + 1].startswith('c2ham-'))
            exp = export_of(cmd)
            self.assertEqual(exp['LRI_SITE'], 'symmetry')
            self.assertEqual(exp['LRI_CLEAN_STAGE'], '1')
            self.assertEqual(exp['LRI_MODULES'], 'python/3.13-mamba')
            self.assertTrue(exp['LRI_NODE_SCRATCH_BASE'].startswith('/local1/'))
            self.assertTrue(exp['LRI_ROOT'])
        self.assertEqual(export_of(grid)['LRI_GRID_WORKERS'], 'auto')
        self.assertEqual(export_of(grid)['LRI_PIN'], 'package')
        self.assertEqual(export_of(pair)['LRI_ROWS'], '1:2')
        self.assertEqual(export_of(single)['LRI_ROWS'], '3')
        for cmd in (pair, single):
            self.assertIn('--dependency=afterok:DRYRUN', cmd)
            self.assertTrue(cmd[-1].endswith('rows_job.sbatch'))
        self.assertFalse(any(c.startswith('--array') for c in pair + single))

    def test_p2_one_row_per_node(self):
        r, cmds = dry_run_submit('symmetry', '--stage', 'P2')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        grid, rows = cmds
        self.assertIn('--array=4,5%2', rows)
        self.assertEqual(export_of(rows)['LRI_PIN'], 'package')
        self.assertEqual(export_of(rows)['LRI_ROWS'], '')
        self.assertEqual(export_of(rows)['LRI_ROW_MODE'], 'array')

    def test_debug_partitions_for_smoke_and_probe(self):
        r, cmds = dry_run_submit('symmetry', '--plan', str(PKG / 'cluster/smoke_plan.json'), '--resources-profile', 'smoke')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for cmd in cmds:
            self.assertEqual(cmd[cmd.index('-p') + 1], 'amddebugq,debugq')
        r, cmds = dry_run_submit('symmetry', '--probe')
        self.assertEqual(cmds[0][cmds[0].index('-p') + 1], 'amddebugq,debugq')

    def test_site_scripts(self):
        for f in ['make_tarball.sh', 'collect.sh', 'setup_env.sh']:
            self.assertEqual(subprocess.run(['bash', '-n', str(HERE / f)]).returncode, 0, f)
        text = (HERE / 'setup_env.sh').read_text()
        self.assertIn('module load', text)
        self.assertNotIn('--user', text)            # no system or user-site installs
        self.assertIn('-m venv', text)
        r = subprocess.run([sys.executable, str(HERE / 'submit.py'), '--check'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('SITE symmetry', r.stdout)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    run_cases([SymmetryProfileTests], parser.parse_args().output,
              'Symmetry profile rules, documented launch commands (dry runs against a fake site), bash -n of the site scripts.')
