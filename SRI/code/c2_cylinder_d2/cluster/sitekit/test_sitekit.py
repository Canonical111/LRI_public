#!/usr/bin/env python3
"""Tests of the site-independent launch layer (cluster/sitekit) and the
site-neutral plan: plan contents and science rules, profile checks, Slurm
command construction, dry-run submission planning, job helpers, tail-cutoff
plumbing, comparisons, merging, shell syntax, publish/fetch and the tarball.
No scheduler is contacted and no large array is generated. Site-specific tests:
cluster/expanse/test_expanse.py and cluster/symmetry/test_symmetry.py."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
PKG = HERE.parents[1]
sys.path.insert(0, str(PKG / 'cluster'))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PKG / 'code' / 'hamiltonian'))
import run_task                      # noqa: E402
import submit                        # noqa: E402
import jobtools                      # noqa: E402
import compare                       # noqa: E402

PLAN = PKG / 'cluster' / 'production_plan.json'
SITES = ('expanse', 'symmetry')
GNU = shutil.which('sha256sum') is not None and \
    subprocess.run(['mv', '--version'], capture_output=True).returncode == 0


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


_BUILT: dict = {}


def built_package() -> tuple[Path, Path]:
    """(code copy, tarball) of this package, built once per test process, exactly as
    make_tarball.sh --upload produces them: from git when this is a checkout, else
    by re-tarring this code copy (which carries its own STAGE_MANIFEST)."""
    if 'pkg' in _BUILT:
        return _BUILT['pkg']
    d = Path(tempfile.mkdtemp(prefix='lri_pkg_'))
    if (PKG / '.git').exists():
        r = run(['bash', str(HERE / 'make_tarball.sh'), '--allow-dirty', '--out', str(d / 'pkg')])
        assert r.returncode == 0, r.stdout + r.stderr
        tar = next((d / 'pkg').glob('lri_c2_*.tar'))
    else:
        import tarfile
        info = json.loads((PKG / 'STAGE_INFO.json').read_text())
        (d / 'pkg').mkdir()
        tar = d / 'pkg' / f"{info['name']}.tar"
        listed = [line.split('  ', 1)[1] for line in (PKG / 'STAGE_MANIFEST.sha256').read_text().splitlines()]
        with tarfile.open(tar, 'w') as t:
            for rel in listed + ['STAGE_MANIFEST.sha256']:
                t.add(PKG / rel, arcname=f'lri_c2/{rel}')
        (Path(str(tar) + '.sha256')).write_text(f'{jobtools_sha(tar)}  {tar.name}\n')
    (d / 'code').mkdir()
    subprocess.run(['tar', '-xf', str(tar), '-C', str(d / 'code')], check=True)
    _BUILT['pkg'] = (d / 'code' / 'lri_c2', tar)
    return _BUILT['pkg']


def jobtools_sha(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


FAKE_SQUEUE = """#!/usr/bin/env python3
import os, sys
if os.environ.get('FAKE_SQ_FAIL'):
    sys.exit(1)
which = 'FAKE_SQ_ACCOUNT' if '-A' in sys.argv else 'FAKE_SQ_USER'
path = os.environ.get(which)
if path:
    sys.stdout.write(open(path).read())
"""


class FakeSite:
    """A temporary site root with the uploaded tarball, a fake environment and a
    fake squeue, plus a private copy of the code copy that tests may edit."""

    def __init__(self):
        code, tar = built_package()
        self.d = Path(tempfile.mkdtemp(prefix='lri_site_'))
        self.root = self.d / 'root'
        (self.root / 'pkg').mkdir(parents=True)
        shutil.copy(tar, self.root / 'pkg' / tar.name)
        shutil.copy(str(tar) + '.sha256', self.root / 'pkg' / (tar.name + '.sha256'))
        self.code = self.d / 'code'
        shutil.copytree(code, self.code, ignore=shutil.ignore_patterns('__pycache__'))
        (self.d / 'env' / 'bin').mkdir(parents=True)
        (self.d / 'env' / 'bin' / 'python').write_text('')
        (self.d / 'env' / 'lri_env_receipt.json').write_text('{}')
        (self.d / 'bin').mkdir()
        (self.d / 'bin' / 'squeue').write_text(FAKE_SQUEUE)
        (self.d / 'bin' / 'squeue').chmod(0o755)
        self.squeue_user = ''
        self.squeue_account = ''
        self.squeue_fail = False

    def submit(self, site: str, *args: str, env: dict | None = None):
        (self.d / 'sq_user').write_text(self.squeue_user)
        (self.d / 'sq_account').write_text(self.squeue_account)
        e = dict(os.environ, PATH=str(self.d / 'bin') + os.pathsep + os.environ['PATH'],
                 FAKE_SQ_USER=str(self.d / 'sq_user'), FAKE_SQ_ACCOUNT=str(self.d / 'sq_account'))
        if self.squeue_fail:
            e['FAKE_SQ_FAIL'] = '1'
        e.update(env or {})
        args = [str(self.code) + a[len(str(PKG)):] if a.startswith(str(PKG) + os.sep) else a for a in args]
        r = run([sys.executable, str(self.code / 'cluster' / site / 'submit.py'), *args, '--root', str(self.root),
                 '--pkg-root', str(self.root), '--env', str(self.d / 'env')], env=e)
        cmds = [shlex.split(line.strip()) for line in r.stdout.splitlines() if line.strip().startswith('sbatch ')]
        return r, cmds

    def task_name(self, row: int, plan: str = 'cluster/production_plan.json') -> str:
        r = run([sys.executable, str(self.code / 'cluster/sitekit/jobtools.py'), 'task-info', '--plan',
                 str(self.code / plan), '--index', str(row)])
        return next(l.split('=', 1)[1] for l in r.stdout.splitlines() if l.startswith('TASK_NAME='))

    def grid_dir(self, n: int) -> str:
        r = run([sys.executable, str(self.code / 'cluster/sitekit/jobtools.py'), 'grid-info', '--cutoff', str(n),
                 '--oversample', '4', '--radius-cost', '4.5'])
        return next(l.split('=', 1)[1] for l in r.stdout.splitlines() if l.startswith('GRID_DIR='))

    def close(self):
        shutil.rmtree(self.d, ignore_errors=True)


def fake_record(job: dict, lam: float, shift: float = 0.0, length: int | None = None) -> dict:
    """A raw solver record of the solver's shape with sequences of the declared
    lengths (N, mixed cutoff); length shortens Xchain for negative tests."""
    n, nm = job['cutoff'], job['mixed_cutoff']
    x = [1000.0 + 1e-3 * i + shift for i in range(n if length is None else length)]
    parts = [{'pairing': name, 'X': [v / 3 for v in x[:n]] + [0.0] * (n - len(x[:n]))}
             for name in ('adjacent', 'crossed', 'nested')]
    return {'order': job['order'], 'lam': lam, 'N': n,
            'raw': {'lam': lam, 'order': job['order'], 'Nmax': n, 'parts': parts, 'Xchain': x},
            'two_point': {'lam': lam, 'N': job['collapsed_cutoff'], 'states': [], 'Xdisc': 1.0, 'Dmixed': 0.0, 'X2': 0.0},
            'mixed': {'lam': lam, 'order': job['order'], 'Nmax': nm, 'parts': [], 'Xmixed': [0.5] * nm, 'fits': []},
            'planar': {}, 'curvature': {}, 'coefficient_file': 'g.npy', 'seconds': 0.1, 'physical_C2_claimed': False}


def write_sums(directory: Path) -> None:
    import hashlib
    names = sorted(f.name for f in directory.iterdir() if f.is_file() and f.name != 'SHA256SUMS')
    (directory / 'SHA256SUMS').write_text(''.join(
        f'{hashlib.sha256((directory / n).read_bytes()).hexdigest()}  {n}\n' for n in names))


def publish_row(directory: Path, job: dict, extra: dict | None = None, site: str = 'expanse',
                shift: float = 0.0, length: int | None = None) -> None:
    """A complete published row as rows_job.sbatch writes it."""
    directory.mkdir(parents=True)
    for lam in job['lambda']:
        (directory / f"cluster_k{job['order']}_a{float(lam)}_N{job['cutoff']}.json").write_text(
            json.dumps(fake_record(job, lam, shift, length)))
    receipt = {'job': job, 'source_hashes': {'reproduce.py': 'a' * 64}, 'plan_sha256': 'b' * 64, 'plan_name': 'p'}
    receipt.update(extra or {})
    (directory / 'task_receipt.json').write_text(json.dumps(receipt))
    (directory / 'run_receipt.json').write_text('{}')
    (directory / 'job_receipt.json').write_text(json.dumps({'site': site, 'host': 'h', 'cpu_vendor': 'v'}))
    write_sums(directory)


def publish_grid(directory: Path, array_bytes: bytes = b'0123456789') -> None:
    import hashlib
    directory.mkdir(parents=True)
    (directory / 'g.npy').write_bytes(array_bytes)
    (directory / 'g.json').write_text('{}')
    (directory / 'grid_receipt.json').write_text(json.dumps({'array': 'g.npy', 'array_bytes': len(array_bytes)}))
    names = sorted(f.name for f in directory.iterdir())
    (directory / 'SHA256SUMS').write_text(''.join(
        f'{hashlib.sha256((directory / n).read_bytes()).hexdigest()}  {n}\n' for n in names))


def dry_run_submit(site: str, *args: str) -> tuple[subprocess.CompletedProcess, list[list[str]]]:
    """Dry run of cluster/<site>/submit.py against a fresh fake site."""
    fake = FakeSite()
    try:
        return fake.submit(site, *args)
    finally:
        fake.close()


def export_of(cmd: list[str]) -> dict:
    exp = next(c for c in cmd if c.startswith('--export='))[len('--export='):]
    return dict(item.split('=', 1) for item in exp.split(',')[1:])


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.plan, self.jobs = run_task.load_plan(PLAN)

    def test_stages_and_lambda_sets(self):
        got = {(j['stage'], j['cutoff'], j['order']): j['lambda'] for j in self.jobs}
        self.assertEqual(got, {
            ('PILOT', 512, 1): [0.1],
            ('P1', 768, 1): [0.075, 0.0875, 0.1],
            ('P1', 768, 2): [0.1, 0.125, 0.15],
            ('P1', 768, 3): [0.1, 0.125, 0.15, 0.175],
            ('P2', 1024, 1): [0.05, 0.0625],
            ('P2', 1024, 2): [0.0625, 0.075]})

    def test_dropped_points(self):
        for j in self.jobs:
            self.assertNotIn(0.04, j['lambda'])
            if j['cutoff'] == 1024:
                self.assertNotEqual(j['order'], 3)

    def test_grid_and_aux_cutoffs(self):
        for j in self.jobs:
            self.assertEqual((j['oversample'], j['radius_cost']), (4, 4.5))   # same grid family as the N=384 records
            self.assertEqual(j['mixed_cutoff'], 16384)
            self.assertEqual(j['collapsed_cutoff'], 800000)
            self.assertEqual(j['tail_cutoff'], 8192)
            self.assertNotIn('workers', j)

    def test_lambda_n_rule(self):
        rule = {int(k): v for k, v in self.plan['science_rules']['lambda_N_minimum'].items()}
        self.assertEqual(rule, {1: 50, 2: 60, 3: 75})
        for j in self.jobs:
            for lam in j['lambda']:
                self.assertGreaterEqual(lam * j['cutoff'], rule[j['order']] - 1e-9, j['id'])

    def test_plan_is_site_neutral(self):
        text = PLAN.read_text().lower()
        for word in ('partition', 'mem_gb', 'large-shared', 'amdq', '"cpus"'):
            self.assertNotIn(word, text)
        self.assertNotIn('expanse', self.plan)

    def test_pilot_task_name_unchanged(self):
        # The Expanse pilot was published under this name (fingerprint of row + sources).
        dry = run([sys.executable, str(PKG / 'cluster/run_task.py'), 'run', '--plan', str(PLAN), '--task-index', '0',
                   '--work-root', '/x/w', '--output-root', '/x/o', '--dry-run'])
        self.assertEqual(json.loads(dry.stdout)['task'], 'PILOT_N512_order1_2539070471a0')

    def test_old_plan_kept(self):
        _, old = run_task.load_plan(PKG / 'cluster' / 'extension_plan.json')
        self.assertEqual(len(old), 9)
        self.assertTrue(all('stage' not in j and 'tail_cutoff' not in j for j in old))

    def test_check_passes_on_both_sites(self):
        for site in SITES:
            for stage in [None, 'PILOT', 'P1', 'P2']:
                args = ['--check'] + (['--stage', stage] if stage else [])
                r = run([sys.executable, str(PKG / 'cluster' / site / 'submit.py'), *args])
                self.assertEqual(r.returncode, 0, f'{site} {stage}: {r.stdout}{r.stderr}')
                self.assertIn('CHECK OK', r.stdout)

    def test_smoke_plan_needs_resources(self):
        smoke = str(PKG / 'cluster/smoke_plan.json')
        for site in SITES:
            r = run([sys.executable, str(PKG / 'cluster' / site / 'submit.py'), '--plan', smoke, '--check'])
            self.assertNotEqual(r.returncode, 0)
            r = run([sys.executable, str(PKG / 'cluster' / site / 'submit.py'), '--plan', smoke, '--check',
                     '--resources-profile', 'smoke'])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_plan_outside_package_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'plan.json'
            shutil.copy(PLAN, path)
            r = run([sys.executable, str(HERE / 'submit.py'), '--site', 'expanse', '--plan', str(path), '--check'])
            self.assertEqual(r.returncode, 64)

    def test_unknown_site(self):
        r = run([sys.executable, str(HERE / 'submit.py'), '--site', 'nowhere', '--check'])
        self.assertEqual(r.returncode, 64)


class CheckTests(unittest.TestCase):
    job = {'id': 'x', 'cutoff': 1024, 'order': 1, 'lambda': [0.05], 'oversample': 4, 'radius_cost': 4.5,
           'mixed_cutoff': 16384, 'collapsed_cutoff': 800000, 'tail_cutoff': 8192}

    def setUp(self):
        self.expanse = submit.load_profile('expanse')
        self.symmetry = submit.load_profile('symmetry')

    def problems(self, site, kind, prof, job=None):
        problems, notes = [], []
        submit.check_profile(site, kind, job or self.job, prof, problems, notes)
        return problems

    def test_thread_cap(self):
        prof = {'partition': 'large-shared', 'cpus': 96, 'mem_gb': 400, 'time': '04:00:00'}
        self.assertTrue(any('64-core package' in p for p in self.problems(self.expanse, 'task', prof)))

    def test_memory_and_partition_limits(self):
        e = self.expanse
        self.assertTrue(self.problems(e, 'task', {'partition': 'shared', 'cpus': 16, 'mem_gb': 300, 'time': '01:00:00'}))
        self.assertTrue(any('memory model' in p for p in self.problems(
            e, 'grid', {'partition': 'large-shared', 'cpus': 32, 'mem_gb': 100, 'time': '01:00:00', 'workers': 32})))
        self.assertTrue(self.problems(e, 'task', {'partition': 'debug', 'cpus': 4, 'mem_gb': 200, 'time': '01:00:00'}))
        self.assertTrue(self.problems(e, 'task', {'partition': 'nope', 'cpus': 4, 'mem_gb': 8, 'time': '01:00:00'}))

    def test_whole_node_rules(self):
        s = self.symmetry
        # auto workers shrink to the memory cap; explicit ones may not exceed the smaller package
        self.assertFalse(self.problems(s, 'grid', {'partition': 'defq', 'mem_gb': 180, 'time': '03:00:00',
                                                   'workers': 'auto', 'pin': 'package'}))
        # ... but the N=1024 grid does not fit the 84 GB node-local disk of the AMD nodes
        self.assertTrue(any('scratch' in p for p in self.problems(
            s, 'grid', {'partition': 'amdq,defq', 'mem_gb': 180, 'time': '03:00:00', 'workers': 'auto', 'pin': 'package'})))
        self.assertTrue(any('package' in p for p in self.problems(
            s, 'grid', {'partition': 'amdq,defq', 'mem_gb': 180, 'time': '03:00:00', 'workers': 32})))
        # two N=1024 rows do not fit one package's memory under --membind
        self.assertTrue(any('membind' in p for p in self.problems(
            s, 'task', {'partition': 'amdq,defq', 'mem_gb': 180, 'time': '08:00:00', 'rows_per_job': 2, 'pin': 'package'})))
        # several rows need pinning; more rows than packages is refused
        self.assertTrue(self.problems(s, 'task', {'partition': 'amdq', 'mem_gb': 240, 'time': '01:00:00',
                                                  'rows_per_job': 2, 'pin': 'none'}, dict(self.job, cutoff=512)))
        self.assertTrue(self.problems(s, 'task', {'partition': 'amdq', 'mem_gb': 240, 'time': '01:00:00',
                                                  'rows_per_job': 3, 'pin': 'package'}, dict(self.job, cutoff=512)))
        # wall time, forbidden partitions, memory above the smaller vendor
        self.assertTrue(self.problems(s, 'task', {'partition': 'amdq', 'mem_gb': 240, 'time': '1-01:00:00'}))
        self.assertTrue(any('not allowed' in p for p in self.problems(
            s, 'task', {'partition': 'longq', 'mem_gb': 100, 'time': '01:00:00'})))
        self.assertTrue(self.problems(s, 'task', {'partition': 'amdq,defq', 'mem_gb': 240, 'time': '01:00:00'}))
        # pinning packages is impossible in a partial (shared) allocation
        self.assertTrue(self.problems(self.expanse, 'task', {'partition': 'shared', 'cpus': 16, 'mem_gb': 64,
                                                             'time': '01:00:00', 'pin': 'package'}))

    def test_grid_scratch_too_big_for_shared_node(self):
        job = dict(self.job, cutoff=1536)
        self.assertTrue(any('scratch' in p for p in self.problems(
            self.expanse, 'grid', {'partition': 'shared', 'cpus': 8, 'mem_gb': 240, 'time': '01:00:00', 'workers': 1}, job)))

    def test_science_rules(self):
        plan = {'science_rules': {'lambda_N_minimum': {'1': 50}, 'minimum_mixed_cutoff': 16384}}
        bad = [dict(self.job, **{'lambda': [0.04], 'mixed_cutoff': 4096})]
        problems = []
        submit.check_science(plan, [0], bad, problems)
        self.assertEqual(len(problems), 2)

    def test_billing(self):
        e = self.expanse['partitions']
        self.assertEqual(submit.billing_rate(e['shared'], 16, 96), (48, 'SU'))
        self.assertEqual(submit.billing_rate(e['large-shared'], 16, 256), (64, 'SU'))
        self.assertEqual(submit.billing_rate(e['compute'], 128, 240), (128, 'SU'))
        self.assertEqual(submit.billing_rate(self.symmetry['partitions']['amdq'], 64, 180), (1, 'node-h'))

    def test_parsing(self):
        self.assertAlmostEqual(submit.hours('1-02:30:00'), 26.5)
        self.assertEqual(submit.parse_resources('partition=shared,cpus=2,mem_gb=4,time=00:15:00,workers=2'),
                         {'partition': 'shared', 'cpus': 2, 'mem_gb': 4, 'time': '00:15:00', 'workers': 2})
        self.assertEqual(submit.parse_resources('workers=auto,rows_per_job=2,pin=package'),
                         {'workers': 'auto', 'rows_per_job': 2, 'pin': 'package'})
        with self.assertRaises(ValueError):
            submit.parse_resources('gpus=1')
        with self.assertRaises(ValueError):
            submit.hours('90 minutes')
        jobs = [{'stage': 'A'}, {'stage': 'B'}, {'stage': 'B'}]
        self.assertEqual(submit.select_rows(jobs, ['B'], None), [1, 2])
        self.assertEqual(submit.select_rows(jobs, None, '0,2'), [0, 2])
        self.assertEqual(submit.select_rows(jobs, ['B'], '0-1'), [1])
        with self.assertRaises(ValueError):
            submit.select_rows(jobs, ['C'], None)

    def test_sbatch_commands(self):
        script = HERE / 'rows_job.sbatch'
        shared = submit.sbatch_command(self.expanse, {'partition': 'shared', 'cpus': 16, 'mem_gb': 96, 'time': '06:00:00'},
                                       'n', '/l/%x_%A_%a.out', {'LRI_PLAN': 'cluster/production_plan.json'},
                                       script, array='1,2,3%2', dependency='123')
        for flag in ['--ntasks-per-node=1', '--cpus-per-task=16', '--mem=96G', '--nodes=1', '--array=1,2,3%2',
                     '--dependency=afterok:123', '--kill-on-invalid-dep=yes']:
            self.assertIn(flag, shared)
        self.assertEqual(export_of(shared)['LRI_PLAN'], 'cluster/production_plan.json')
        self.assertEqual(export_of(shared)['LRI_ROWS'], '')
        self.assertEqual(shared[shared.index('-A') + 1], '<ACCOUNT>')
        self.assertEqual(shared[-1], str(script))
        whole = submit.sbatch_command(self.expanse, {'partition': 'compute', 'cpus': 128, 'mem_gb': 240, 'time': '01:00:00'},
                                      'n', 'log', {}, script)
        self.assertIn('--exclusive', whole)
        self.assertFalse(any(c.startswith('--ntasks-per-node') for c in whole))
        self.assertNotIn('--dependency', ' '.join(whole))
        sym = submit.sbatch_command(self.symmetry, {'partition': 'amdq,defq', 'mem_gb': 180, 'time': '06:00:00'},
                                    'c2ham-x', 'log', {'LRI_ROWS': '1:2'}, script)
        self.assertNotIn('-A', sym)
        self.assertIn('--exclusive', sym)
        self.assertIn('--exclude=cn112', sym)
        self.assertIn('amdq,defq', sym)

    def test_site_exports(self):
        for site in SITES:
            prof = submit.load_profile(site)
            exp = submit.site_exports(prof, Path('/p/pkg/x.tar'), Path('/p'), Path('/e'))
            self.assertEqual(exp['LRI_SITE'], site)
            self.assertTrue(all(',' not in str(v) for v in exp.values()))   # --export uses commas as separators
            self.assertIn('/job_', '/'.join([exp['LRI_NODE_SCRATCH_BASE'], 'job_1']))


class DryRunTests(unittest.TestCase):
    def setUp(self):
        self.site = FakeSite()

    def tearDown(self):
        self.site.close()

    def test_expanse_p1(self):
        r, cmds = self.site.submit('expanse', '--stage', 'P1')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(cmds), 2)
        grid, rows = cmds
        self.assertEqual(export_of(grid)['LRI_N'], '768')
        self.assertTrue(rows[-1].endswith('rows_job.sbatch'))
        self.assertIn('--array=1,2,3%3', rows)
        self.assertIn('--dependency=afterok:DRYRUN', rows)
        self.assertEqual(export_of(rows)['LRI_SITE'], 'expanse')
        self.assertEqual(export_of(rows)['LRI_PIN'], 'none')
        self.assertEqual(export_of(rows)['LRI_ROW_MODE'], 'array')

    def test_probe(self):
        for site in SITES:
            r, cmds = self.site.submit(site, '--probe', '--probe-aux')
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(len(cmds), 1)
            self.assertTrue(cmds[0][-1].endswith('probe_job.sbatch'))
            self.assertEqual(export_of(cmds[0])['LRI_PROBE_AUX'], '1')


class R001BindingTests(unittest.TestCase):
    """The submission is bound to the uploaded tarball and the jobs re-check it."""

    def setUp(self):
        self.site = FakeSite()

    def tearDown(self):
        self.site.close()

    def test_exports_bind_tarball_plan_and_sources(self):
        r, cmds = self.site.submit('expanse', '--stage', 'P1')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        tar = next((self.site.root / 'pkg').glob('*.tar'))
        for cmd in cmds:
            exp = export_of(cmd)
            self.assertEqual(exp['LRI_PKG_SHA256'], jobtools_sha(tar))
            self.assertEqual(exp['LRI_SOURCES_SHA256'], jobtools.sources_digest(run_task))
        self.assertEqual(export_of(cmds[1])['LRI_PLAN_SHA256'], jobtools_sha(self.site.code / 'cluster/production_plan.json'))

    def test_edited_plan_in_login_copy_is_refused(self):
        plan = self.site.code / 'cluster/production_plan.json'
        plan.write_text(plan.read_text().replace('"lambda": [0.075, 0.0875, 0.1]', '"lambda": [0.076, 0.0875, 0.1]'))
        r, cmds = self.site.submit('expanse', '--stage', 'P1')
        self.assertEqual(r.returncode, 65, r.stdout + r.stderr)
        self.assertIn('production_plan.json', r.stdout)
        self.assertEqual(cmds, [])

    def test_edited_code_extra_file_or_other_tarball_is_refused(self):
        (self.site.code / 'cluster/sitekit/rows_job.sbatch').write_text('#!/bin/bash\n')
        r, _ = self.site.submit('expanse', '--stage', 'P1')
        self.assertEqual(r.returncode, 65)
        site = FakeSite()
        try:
            (site.code / 'cluster/new_plan.json').write_text((site.code / 'cluster/production_plan.json').read_text())
            r, _ = site.submit('expanse', '--stage', 'P1', '--plan', str(site.code / 'cluster/new_plan.json'))
            self.assertEqual(r.returncode, 65)
            self.assertIn('not in the tarball', r.stdout)
            tar = next((site.root / 'pkg').glob('*.tar'))
            tar.write_bytes(tar.read_bytes() + b'\0' * 512)       # same name, other content
            r, _ = site.submit('expanse', '--stage', 'P1')
            self.assertEqual(r.returncode, 65)
        finally:
            site.close()

    def test_jobs_recheck_the_binding_before_computing(self):
        for name in ('grid_job.sbatch', 'rows_job.sbatch', 'probe_job.sbatch'):
            text = (HERE / name).read_text()
            check = text.index('"$LRI_PKG_SHA256" ]]')
            self.assertLess(check, text.index('source "$PKG/cluster/sitekit/lib.sh"'), name)
            self.assertIn('LRI_PKG_SHA256', text.split('do\n')[0], name)        # required variable
        grid = (HERE / 'grid_job.sbatch').read_text()
        self.assertLess(grid.index('lri_check_binding'), grid.index('prepare-grid'))
        rows = (HERE / 'rows_job.sbatch').read_text()
        self.assertLess(rows.index('lri_check_binding "$PLAN"'), rows.index('lri_select_rows'))
        self.assertLess(rows.index('lri_check_binding "$PLAN"'), rows.index('run_task.py" run'))

    @unittest.skipUnless(GNU, 'needs GNU coreutils (Linux)')
    def test_check_binding_fails_closed(self):
        plan = PKG / 'cluster/production_plan.json'
        good = jobtools.sources_digest(run_task)
        base = f'STAGE=$(mktemp -d); PKG={PKG}; PY={sys.executable}; source {HERE / "lib.sh"}; '
        ok = run(['bash', '-c', base + f'LRI_SOURCES_SHA256={good} LRI_PLAN_SHA256=$(sha256sum {plan} | cut -d" " -f1) '
                                      f'lri_check_binding {plan}'])
        self.assertEqual(ok.returncode, 0, ok.stderr)
        for env in (f'LRI_SOURCES_SHA256={"0" * 64}', f'LRI_SOURCES_SHA256={good} LRI_PLAN_SHA256={"0" * 64}',
                    f'LRI_SOURCES_SHA256= '):
            bad = run(['bash', '-c', base + f'{env} lri_check_binding {plan}'])
            self.assertEqual(bad.returncode, 65, env)


class R002RowSelectionTests(unittest.TestCase):
    def test_reserved_variables_are_cleared_in_every_export(self):
        site = FakeSite()
        try:
            env = {'LRI_ROWS': '0', 'LRI_TASK_INDEX': '0', 'LRI_ROW_MODE': 'packed', 'LRI_WORKERS': '99',
                   'LRI_TAIL_CUTOFF': '64', 'LRI_SOMETHING_ELSE': 'x'}
            r, cmds = site.submit('expanse', '--stage', 'P2', env=env)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            rows = export_of(cmds[-1])
            self.assertEqual(rows['LRI_ROW_MODE'], 'array')
            for k in ('LRI_ROWS', 'LRI_TASK_INDEX', 'LRI_WORKERS', 'LRI_TAIL_CUTOFF'):
                self.assertEqual(rows[k], '', k)
            for cmd in cmds:
                self.assertEqual(set(export_of(cmd)), set(submit.RESERVED_EXPORTS))
            r, cmds = site.submit('symmetry', '--stage', 'P1', env=env)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(export_of(cmds[1])['LRI_ROW_MODE'], 'packed')
            self.assertEqual(export_of(cmds[1])['LRI_ROWS'], '1:2')
        finally:
            site.close()

    def test_sbatch_process_gets_no_inherited_lri_variables(self):
        os.environ['LRI_ROWS'] = '0'
        try:
            self.assertNotIn('LRI_ROWS', submit.slurm_env(submit.load_profile('expanse')))
            path = submit.slurm_env(submit.load_profile('symmetry'))['PATH']
            self.assertTrue(path.endswith(os.pathsep + '/cm/shared/apps/slurm/current/bin'))   # appended
        finally:
            os.environ.pop('LRI_ROWS')
        with self.assertRaises(ValueError):
            submit.sbatch_command(submit.load_profile('expanse'), {'partition': 'shared', 'cpus': 1, 'mem_gb': 1,
                                  'time': '00:10:00'}, 'n', 'l', {'LRI_UNKNOWN': '1'}, HERE / 'rows_job.sbatch')

    def test_cleared_variables_mean_unset_for_the_launcher(self):
        # Found by the Expanse smoke run: run_task.py parsed LRI_WORKERS='' as an integer.
        env = {k: '' for k in submit.RESERVED_EXPORTS}
        r = run([sys.executable, str(PKG / 'cluster/run_task.py'), 'run', '--plan', str(PKG / 'cluster/smoke_plan.json'),
                 '--task-index', '0', '--work-root', '/x/w', '--output-root', '/x/o', '--dry-run'],
                env=dict(os.environ, **env))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['command'][json.loads(r.stdout)['command'].index('--workers') + 1], '1')
        r = run([sys.executable, str(PKG / 'cluster/run_task.py'), 'prepare-grid', '--cutoff', '12', '--oversample', '3',
                 '--radius-cost', '4', '--cache-root', '/x/c', '--dry-run'], env=dict(os.environ, **env))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn('LRI_TAIL_CUTOFF', run_task.environment(1, None))
        os.environ['LRI_TAIL_CUTOFF'] = ''
        try:
            import exact_leading_tail
            self.assertEqual(exact_leading_tail.configured_tail_cutoff(), 2048)
        except ImportError:
            pass
        finally:
            os.environ.pop('LRI_TAIL_CUTOFF')

    def select(self, env: str) -> subprocess.CompletedProcess:
        return run(['bash', '-c', f'source {HERE / "lib.sh"}; {env} ; lri_select_rows; echo "ROWS=${{ROWS[*]}}"'])

    def test_array_row_comes_only_from_slurm(self):
        r = self.select('export LRI_ROW_MODE=array SLURM_ARRAY_TASK_ID=4 LRI_ROWS= LRI_TASK_INDEX=0')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('ROWS=4', r.stdout)
        self.assertEqual(self.select('export LRI_ROW_MODE=array SLURM_ARRAY_TASK_ID=4 LRI_ROWS=0').returncode, 64)
        self.assertEqual(self.select('export LRI_ROW_MODE=array SLURM_ARRAY_TASK_ID=').returncode, 64)
        r = self.select('export LRI_ROW_MODE=packed LRI_ROWS=1:2 SLURM_ARRAY_TASK_ID=')
        self.assertIn('ROWS=1 2', r.stdout)
        self.assertEqual(self.select('export LRI_ROW_MODE=packed LRI_ROWS=1 SLURM_ARRAY_TASK_ID=3').returncode, 64)
        self.assertEqual(self.select('export LRI_ROW_MODE= LRI_ROWS=1 LRI_TASK_INDEX=1').returncode, 64)
        self.assertNotIn('LRI_TASK_INDEX', (HERE / 'rows_job.sbatch').read_text().split('lri_select_rows')[0]
                         .split('set -o pipefail')[1])


class R003PublishedTests(unittest.TestCase):
    def setUp(self):
        self.site = FakeSite()
        self.plan, self.jobs = run_task.load_plan(PLAN)
        self.row = self.site.root / 'outputs' / 'production_plan' / self.site.task_name(0)

    def tearDown(self):
        self.site.close()

    def test_complete_row_is_skipped(self):
        publish_row(self.row, self.jobs[0])
        r, cmds = self.site.submit('expanse', '--stage', 'PILOT')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('published and verified, skipped', r.stdout)
        # R2-008: no unfinished row needs the (deleted or never built) grid, so nothing is submitted
        self.assertEqual(cmds, [])
        self.assertIn('NOTHING TO SUBMIT', r.stdout)

    def test_grid_only_for_unfinished_rows(self):
        p2 = [self.site.root / 'outputs' / 'production_plan' / self.site.task_name(i) for i in (4, 5)]
        publish_row(p2[0], self.jobs[4])
        r, cmds = self.site.submit('expanse', '--stage', 'P2')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(cmds), 2)                           # grid job + row 5 only
        self.assertIn('--array=5%2', cmds[1])
        publish_row(p2[1], self.jobs[5])
        r, cmds = self.site.submit('expanse', '--stage', 'P2')
        self.assertEqual((r.returncode, cmds), (0, []))

    def corrupt_row(self, how) -> subprocess.CompletedProcess:
        publish_row(self.row, self.jobs[0])
        how(self.row)
        r, cmds = self.site.submit('expanse', '--stage', 'PILOT')
        self.assertEqual(cmds, [])
        return r

    def test_empty_manifest_fails_loudly(self):
        r = self.corrupt_row(lambda d: (d / 'SHA256SUMS').write_text(''))
        self.assertEqual(r.returncode, 1)
        self.assertIn('empty', r.stdout)

    def test_missing_or_changed_record_fails_loudly(self):
        rec = 'cluster_k1_a0.1_N512.json'
        self.assertEqual(self.corrupt_row(lambda d: (d / rec).unlink()).returncode, 1)
        self.tearDown(); self.setUp()
        r = self.corrupt_row(lambda d: (d / rec).write_text('{}'))
        self.assertEqual(r.returncode, 1)
        self.assertIn('checksum mismatch', r.stdout)

    def test_unlisted_or_unrequired_manifest_fails_loudly(self):
        r = self.corrupt_row(lambda d: (d / 'stray.json').write_text('{}'))
        self.assertIn('unlisted file', r.stdout)
        self.tearDown(); self.setUp()

        def drop_record(d):
            lines = [l for l in (d / 'SHA256SUMS').read_text().splitlines() if 'cluster_k' not in l]
            (d / 'SHA256SUMS').write_text('\n'.join(lines) + '\n')
            (d / 'cluster_k1_a0.1_N512.json').unlink()
        r = self.corrupt_row(drop_record)
        self.assertEqual(r.returncode, 1)
        self.assertIn('required file not listed', r.stdout)

    def test_grids(self):
        gdir = self.site.root / 'grids' / self.site.grid_dir(512)
        publish_grid(gdir)
        r, cmds = self.site.submit('expanse', '--stage', 'PILOT')
        self.assertIn('published and verified, no job', r.stdout)
        self.assertEqual(len(cmds), 1)          # the row job only
        (gdir / 'g.json').write_text('{"x": 1}')
        r, cmds = self.site.submit('expanse', '--stage', 'PILOT')
        self.assertEqual(r.returncode, 1)
        self.assertEqual(cmds, [])
        shutil.rmtree(gdir)
        publish_grid(gdir)
        (gdir / 'g.npy').write_bytes(b'012345678')           # truncated array: size check on the login node
        self.assertEqual(self.site.submit('expanse', '--stage', 'PILOT')[0].returncode, 1)

    def test_manifest_parser(self):
        import manifests
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / 'a').write_text('x')
            digest = jobtools_sha(d / 'a')
            for text in ('', f'{digest}  a\n{digest}  a\n', f'{digest}  ../a\n', f'{digest}  /etc/a\n',
                         f'{digest}  sub/a\n', 'nonsense\n', f'{digest}  .hidden\n'):
                (d / 'SHA256SUMS').write_text(text)
                with self.assertRaises(manifests.ManifestError, msg=text):
                    manifests.read_manifest(d)
            (d / 'SHA256SUMS').write_text(f'{digest}  a\n')
            self.assertEqual(manifests.verify_dir(d)[1], [])

    def test_job_side_and_transfer_use_the_strict_check(self):
        self.assertIn('published-check --kind grid', (HERE / 'grid_job.sbatch').read_text())
        self.assertIn('published-check --kind row', (HERE / 'rows_job.sbatch').read_text())
        transfer = (HERE / 'transfer_grid.sh').read_text()
        self.assertIn('grid-status', transfer)
        self.assertNotIn('test -s', transfer)
        gdir = self.site.root / 'grids' / 'G'
        publish_grid(gdir)
        cli = [sys.executable, str(HERE / 'jobtools.py'), 'published-check', '--kind', 'grid', '--dir', str(gdir)]
        self.assertEqual(run(cli).returncode, 0)
        (gdir / 'g.npy').write_bytes(b'9123456789')            # same size, other content: hashed on the node
        self.assertEqual(run(cli).returncode, 74)
        self.assertEqual(run(cli[:-1] + [str(gdir) + '_absent']).returncode, 3)
        self.assertEqual(run([sys.executable, str(HERE / 'manifests.py'), 'grid-status', str(gdir)]).returncode, 74)


class R004R005QueueTests(unittest.TestCase):
    def setUp(self):
        self.site = FakeSite()

    def tearDown(self):
        self.site.close()

    def grid_token(self, root: Path, n: int) -> str:
        return submit.grid_token(root.resolve() / 'grids' / self.site.grid_dir(n))

    def test_grid_job_matched_by_destination(self):
        tok = self.grid_token(self.site.root, 768)
        self.site.squeue_user = f'777|lri_c2_grid_{self.site.grid_dir(768)}|PENDING|lri1;g={tok}\n'
        r, cmds = self.site.submit('expanse', '--stage', 'P1')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(cmds), 1)
        self.assertIn('--dependency=afterok:777', cmds[0])
        other = self.grid_token(self.site.d / 'another_root', 768)   # same grid key, other root
        self.site.squeue_user = f'778|lri_c2_grid_{self.site.grid_dir(768)}|PENDING|lri1;g={other}\n'
        r, cmds = self.site.submit('expanse', '--stage', 'P1')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(cmds), 2)                                 # its own grid job
        self.assertNotIn('afterok:778', ' '.join(cmds[1]))
        self.assertTrue(any(c.startswith('--comment=lri1;g=') for c in cmds[0]))
        self.site.squeue_user = '779|lri_c2_grid_N768_o4_r4p5|PENDING|\n'     # legacy job, destination unknown
        r, cmds = self.site.submit('expanse', '--stage', 'P1')
        self.assertEqual(r.returncode, 1)
        self.assertIn('no destination comment', r.stdout)

    def tokens(self, row: int) -> str:
        root = self.site.root.resolve()
        name = self.site.task_name(row)
        plan_sha = jobtools_sha(self.site.code / 'cluster/production_plan.json')
        return '+'.join(submit.task_tokens(root / 'outputs' / 'production_plan' / name, root, plan_sha, name))

    def test_duplicates_by_task_identity_across_packed_and_array_jobs(self):
        self.site.squeue_user = f'800|c2ham-rows_production_plan_r1-2|RUNNING|lri1;t={self.tokens(1)}+{self.tokens(2)}\n'
        r, cmds = self.site.submit('symmetry', '--tasks', '1')
        self.assertEqual(r.returncode, 1)
        self.assertIn('already queued or running in job 800', r.stdout)
        r, cmds = self.site.submit('expanse', '--tasks', '2')          # another site's job name, same root and task
        self.assertEqual(r.returncode, 1)
        r, cmds = self.site.submit('symmetry', '--tasks', '3')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        comment = next(c for c in cmds[-1] if c.startswith('--comment='))
        self.assertIn(self.tokens(3), comment)
        self.site.squeue_user = f'801_5|lri_c2_task_production_plan_N1024|PENDING|lri1;t={self.tokens(5)}\n'
        r, _ = self.site.submit('expanse', '--stage', 'P2')
        self.assertEqual(r.returncode, 1)
        self.assertIn('801_5', r.stdout)


class R009HeadroomTests(unittest.TestCase):
    COMPUTE = ['--grid-resources', 'partition=compute,cpus=128,mem_gb=240,time=03:00:00,workers=32',
               '--task-resources', 'partition=compute,cpus=128,mem_gb=240,time=06:00:00']

    def setUp(self):
        self.site = FakeSite()

    def tearDown(self):
        self.site.close()

    def test_running_plus_pending_against_22(self):
        self.site.squeue_account = ''.join(f'{i}\n' for i in range(10)) + ''.join(f'{i}_1\n' for i in range(10, 19))
        r, cmds = self.site.submit('expanse', '--stage', 'P1', *self.COMPUTE)          # 19 + 4 > 22
        self.assertEqual(r.returncode, 1)
        self.assertIn('would exceed 22', r.stderr)
        self.assertEqual(cmds, [])
        self.site.squeue_account = ''.join(f'{i}\n' for i in range(18))                 # 18 + 4 = 22
        r, cmds = self.site.submit('expanse', '--stage', 'P1', *self.COMPUTE)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_no_force_and_unknown_queue(self):
        r, _ = self.site.submit('expanse', '--stage', 'P1', '--force', *self.COMPUTE)
        self.assertEqual(r.returncode, 2)                     # the option no longer exists
        self.site.squeue_fail = True
        r, cmds = self.site.submit('expanse', '--stage', 'P1', *self.COMPUTE)
        self.assertEqual(r.returncode, 75)
        self.assertEqual(cmds, [])


class R010ProbeTests(unittest.TestCase):
    def test_aux_probe_failure_propagates(self):
        try:
            import scipy  # noqa: F401
        except ImportError as exc:
            self.skipTest(str(exc))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'aux.json'
            r = run([sys.executable, str(HERE / 'aux_cost_probe.py'), '--lam', '0.25', '--order', '1',
                     '--collapsed-cutoff', '2000', '--mixed', '64', '--tail', '-5', '--out', str(out)])
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            obj = json.loads(out.read_text())
            self.assertEqual(obj['status'], 'failed')
            self.assertEqual(obj['failed'], ['tail -5'])
            self.assertEqual([x['kind'] for x in obj['rows'] if not x.get('error')], ['two_point', 'mixed'])

    def test_probe_job_records_failures_and_checks_space_first(self):
        text = (HERE / 'probe_job.sbatch').read_text()
        self.assertNotIn('lri_phase_end 0', text)
        self.assertLess(text.index('avail >= DD_BYTES'), text.index('of="$STAGE/ddtest"'))
        self.assertIn('lri_die 70', text)
        self.assertIn('AUX_RC', text)


class R011RegressionTests(unittest.TestCase):
    FAKE_RUN = """import json, sys
from pathlib import Path
cmd = sys.argv[1]; out = Path(sys.argv[sys.argv.index('--output') + 1]); out.mkdir(parents=True)
bad = Path(__file__).with_name('bad_' + cmd).exists()
(out / f'{cmd}.json').write_text('{not json' if bad else json.dumps({'value': 1.0, 'seconds': 0.1}))
"""
    FAKE_TASK = """import json, sys
from pathlib import Path
if sys.argv[1] == 'run':
    out = Path(sys.argv[sys.argv.index('--output-root') + 1]) / 'smoke_x'; out.mkdir(parents=True)
    (out / 'cluster_k1_a0.25_N12.json').write_text(json.dumps({'raw': [1.0]}))
"""

    def tree(self, d: Path, name: str, new: bool) -> Path:
        root = d / name
        (root / 'scripts').mkdir(parents=True)
        (root / 'cluster').mkdir()
        (root / 'scripts' / 'run.py').write_text(self.FAKE_RUN)
        (root / 'cluster' / 'run_task.py').write_text(self.FAKE_TASK)
        if new:
            (root / 'cluster' / 'sitekit').mkdir()
            shutil.copy(HERE / 'compare.py', root / 'cluster' / 'sitekit' / 'compare.py')
            for sub, cmd in [('validation', 'validate'), ('hamiltonian', 'analyze'),
                             ('hamiltonian_recorded', 'analyze-recorded'), ('demo', 'demo')]:
                (root / 'results' / sub).mkdir(parents=True)
                (root / 'results' / sub / f'{cmd}.json').write_text(json.dumps({'value': 1.0}))
            (root / 'results/revision/cluster_smoke/smoke_1').mkdir(parents=True)
            (root / 'results/revision/cluster_smoke/smoke_1/cluster_k1_a0.25_N12.json').write_text('{"raw": [1.0]}')
        return root

    def regression(self, d: Path, out: Path) -> subprocess.CompletedProcess:
        return run(['bash', str(HERE / 'regression.sh'), str(d / 'old'), str(d / 'new'), str(out), sys.executable])

    def test_pass_fail_and_fresh_directory(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.tree(d, 'old', False)
            new = self.tree(d, 'new', True)
            r = self.regression(d, d / 'out1')
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn('REGRESSION PASSED', r.stdout)
            r = self.regression(d, d / 'out1')                      # stale reports must not be reused
            self.assertEqual(r.returncode, 64)
            (new / 'scripts' / 'bad_analyze').write_text('')        # unreadable output: the comparison crashes
            r = self.regression(d, d / 'out2')
            self.assertNotEqual(r.returncode, 0, r.stdout)
            self.assertIn('FAILED comparison old_vs_new_analyze', r.stdout)

    def test_summary_requires_every_report(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for name in ['validate', 'analyze', 'analyze-recorded', 'demo']:     # cluster_smoke missing
                (d / f'compare_old_vs_new_{name}.json').write_text(json.dumps({'all_identical': True, 'files': []}))
            r = run([sys.executable, str(HERE / 'compare.py'), 'regression-summary', str(d), '--runs-status', '0',
                     '--expect-old-vs-new', 'validate', 'analyze', 'analyze-recorded', 'demo', 'cluster_smoke'])
            self.assertEqual(r.returncode, 1)
            self.assertIn('MISSING', r.stdout)
            s = json.loads((d / 'regression_summary.json').read_text())
            self.assertFalse(s['passed'])
            self.assertFalse(s['old_vs_new_identical'])


class R012ProbeLimitTests(unittest.TestCase):
    def test_probe_overrides_are_validated(self):
        for site, args in [('symmetry', 'mem_gb=500,time=48:00:00'), ('expanse', 'cpus=500'),
                           ('expanse', 'time=72:00:00'), ('symmetry', 'partition=longq')]:
            r = run([sys.executable, str(PKG / 'cluster' / site / 'submit.py'), '--probe', '--check',
                     '--task-resources', args])
            self.assertEqual(r.returncode, 1, f'{site} {args}: {r.stdout}')
            self.assertIn('PROBLEM', r.stdout)
        r = run([sys.executable, str(PKG / 'cluster/symmetry/submit.py'), '--probe', '--check'])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class JobtoolsTests(unittest.TestCase):
    def test_task_info_matches_run_task(self):
        r = run([sys.executable, str(HERE / 'jobtools.py'), 'task-info', '--plan', str(PLAN), '--index', '1'])
        self.assertEqual(r.returncode, 0, r.stderr)
        values = dict(line.split('=', 1) for line in r.stdout.splitlines())
        values = {k: shlex.split(v)[0] if v else '' for k, v in values.items()}
        dry = run([sys.executable, str(PKG / 'cluster/run_task.py'), 'run', '--plan', str(PLAN), '--task-index', '1',
                   '--work-root', '/x/w', '--output-root', '/x/o', '--dry-run'])
        self.assertEqual(values['TASK_NAME'], json.loads(dry.stdout)['task'])
        self.assertEqual(values['GRID_KEY'], 'N768_o4_r4p5')
        self.assertTrue(values['GRID_DIR'].startswith('N768_o4_r4p5_src'))
        self.assertEqual(values['TASK_STAGE'], 'P1')

    def test_grid_dir_tracks_sources(self):
        a = jobtools.grid_dir_name(run_task, 768, 4, 4.5)
        self.assertEqual(a, jobtools.grid_dir_name(run_task, 768, 4, 4.5))
        self.assertRegex(a.rsplit('_src', 1)[1], r'^[0-9a-f]{12}$')

    def test_scratch_need(self):
        def need(kind):
            r = run([sys.executable, str(HERE / 'jobtools.py'), 'scratch-need', '--kind', kind,
                     '--cutoff', '1024', '--oversample', '4'])
            return int(r.stdout)
        self.assertGreater(need('grid'), 260e9)
        self.assertGreater(need('task'), 52e9)
        self.assertLess(need('task'), need('grid'))

    def test_grid_workers(self):
        cap = jobtools.grid_workers_cap(1024, 4, 180 * 2**30)
        self.assertTrue(20 <= cap < 32)
        self.assertGreaterEqual(jobtools.grid_workers_cap(768, 4, 180 * 2**30), 32)
        r = run([sys.executable, str(HERE / 'jobtools.py'), 'grid-workers', '--cutoff', '1024', '--oversample', '4',
                 '--mem-mb', str(180 * 1024), '--cores', '20'])
        self.assertEqual(int(r.stdout), 20)
        r = run([sys.executable, str(HERE / 'jobtools.py'), 'grid-workers', '--cutoff', '1024', '--oversample', '4',
                 '--mem-mb', '4096', '--cores', '20'])
        self.assertEqual(int(r.stdout), 0)

    def test_topology(self):
        topo = jobtools.topology()
        self.assertGreaterEqual(topo['physical_cores'], 1)
        self.assertEqual(sum(p['allowed_cores'] for p in topo['packages']), topo['physical_cores'])
        r = run([sys.executable, str(HERE / 'jobtools.py'), 'topology'])
        values = dict(line.split('=', 1) for line in r.stdout.splitlines())
        for key in ['TOPO_VENDOR', 'TOPO_PACKAGES', 'TOPO_PER_PROCESS', 'TOPO_PKG0_CORES', 'TOPO_PKG0_NODES']:
            self.assertIn(key, values)
        self.assertLessEqual(int(values['TOPO_PER_PROCESS']), 64)

    def test_check_env(self):
        from importlib import metadata
        with tempfile.TemporaryDirectory() as d:
            ok = Path(d) / 'ok.txt'
            ok.write_text(f"numpy=={metadata.version('numpy')}\n# comment\n")
            r = run([sys.executable, str(HERE / 'jobtools.py'), 'check-env', '--requirements', str(ok)])
            self.assertEqual(r.returncode, 0, r.stdout)
            bad = Path(d) / 'bad.txt'
            bad.write_text('numpy==0.0.1\n')
            r = run([sys.executable, str(HERE / 'jobtools.py'), 'check-env', '--requirements', str(bad),
                     '--out', str(Path(d) / 'env.json')])
            self.assertEqual(r.returncode, 78)
            self.assertIn('numpy', json.loads((Path(d) / 'env.json').read_text())['mismatches'])

    def test_cores(self):
        r = run([sys.executable, str(HERE / 'jobtools.py'), 'cores', '--per-process'],
                env=dict(os.environ, SLURM_CPUS_ON_NODE='3'))
        self.assertTrue(1 <= int(r.stdout) <= 3)

    def test_monitor_exit_code_and_summary(self):
        with tempfile.TemporaryDirectory() as d:
            summary = Path(d) / 'm.json'
            r = run([sys.executable, str(HERE / 'jobtools.py'), 'monitor', '--label', 't', '--interval', '0.2',
                     '--summary', str(summary), '--samples', str(Path(d) / 's.jsonl'), '--watch', d, '--',
                     sys.executable, '-c', 'import time,sys; time.sleep(0.5); sys.exit(3)'])
            self.assertEqual(r.returncode, 3)
            s = json.loads(summary.read_text())
            self.assertEqual(s['exit_code'], 3)
            self.assertGreater(s['wall_seconds'], 0.4)
            self.assertGreater(s['largest_process_maxrss_bytes'], 0)

    def test_receipt_records_site_cpu_and_threads(self):
        with tempfile.TemporaryDirectory() as d:
            phases = Path(d) / 'phases.txt'
            phases.write_text('stage 1.0 3.5 0\nrun 3.5 10.0 0\n')
            out = Path(d) / 'r' / 'receipt.json'
            r = run([sys.executable, str(HERE / 'jobtools.py'), 'receipt', '--kind', 'rows', '--status', 'ok',
                     '--out', str(out), '--phases', str(phases), '--extra', 'a=b'],
                    env=dict(os.environ, SLURM_JOB_ID='42', LRI_N='12', LRI_SITE='symmetry', OMP_NUM_THREADS='1'))
            self.assertEqual(r.returncode, 0, r.stderr)
            obj = json.loads(out.read_text())
            self.assertEqual(obj['site'], 'symmetry')
            for key in ['host', 'cpu_vendor', 'cpu_model', 'topology', 'thread_environment']:
                self.assertIn(key, obj)
            self.assertEqual(obj['thread_environment']['OMP_NUM_THREADS'], '1')
            self.assertEqual(obj['slurm']['SLURM_JOB_ID'], '42')
            self.assertEqual([p['seconds'] for p in obj['phases']], [2.5, 6.5])
            self.assertEqual(obj['extra'], {'a': 'b'})


class TailCutoffTests(unittest.TestCase):
    def test_configured_tail_cutoff(self):
        try:
            import exact_leading_tail as elt
        except ImportError as exc:       # numpy/scipy missing
            self.skipTest(str(exc))
        old = os.environ.pop('LRI_TAIL_CUTOFF', None)
        try:
            self.assertEqual(elt.configured_tail_cutoff(), 2048)
            os.environ['LRI_TAIL_CUTOFF'] = '8192'
            self.assertEqual(elt.configured_tail_cutoff(), 8192)
            for bad in ['12', 'x', '-5', '1e4']:
                os.environ['LRI_TAIL_CUTOFF'] = bad
                with self.assertRaises(ValueError):
                    elt.configured_tail_cutoff()
        finally:
            os.environ.pop('LRI_TAIL_CUTOFF', None)
            if old is not None:
                os.environ['LRI_TAIL_CUTOFF'] = old

    def test_launcher_passes_tail_cutoff_only_from_plan(self):
        env = dict(os.environ, LRI_TAIL_CUTOFF='4096')   # must not leak into a plan row without tail_cutoff
        smoke = run([sys.executable, str(PKG / 'cluster/run_task.py'), 'run', '--plan', str(PKG / 'cluster/smoke_plan.json'),
                     '--task-index', '0', '--work-root', '/x/w', '--output-root', '/x/o', '--dry-run'], env=env)
        self.assertNotIn('--tail-cutoff', json.loads(smoke.stdout)['command'])
        new = run([sys.executable, str(PKG / 'cluster/run_task.py'), 'run', '--plan', str(PLAN),
                   '--task-index', '4', '--work-root', '/x/w', '--output-root', '/x/o', '--dry-run'])
        cmd = json.loads(new.stdout)['command']
        _, jobs = run_task.load_plan(PLAN)
        self.assertEqual(cmd[cmd.index('--tail-cutoff') + 1], str(jobs[4]['tail_cutoff']))
        self.assertEqual(cmd[cmd.index('--mixed-cutoff') + 1], str(jobs[4]['mixed_cutoff']))

    def test_environment_drops_tail_variable(self):
        os.environ['LRI_TAIL_CUTOFF'] = '4096'
        try:
            self.assertNotIn('LRI_TAIL_CUTOFF', run_task.environment(2, 3))
            self.assertEqual(run_task.environment(2, 3)['LRI_FFT_WORKERS'], '3')
            self.assertEqual(run_task.environment(2, None)['LRI_FFT_WORKERS'], '2')
        finally:
            os.environ.pop('LRI_TAIL_CUTOFF')


class CompareAndMergeTests(unittest.TestCase):
    def test_outputs_volatile_keys(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / 'a', Path(d) / 'b'
            a.mkdir(), b.mkdir()
            (a / 'x.json').write_text(json.dumps({'v': [1.0, 2.0], 'seconds': 1.0}))
            (b / 'x.json').write_text(json.dumps({'v': [1.0, 2.0], 'seconds': 9.0}))
            (a / 'run_receipt.json').write_text('{}')
            self.assertTrue(compare.compare_outputs(a, b, compare.VOLATILE)['all_identical'])
            (b / 'x.json').write_text(json.dumps({'v': [1.0, 2.0000001], 'seconds': 9.0}))
            res = compare.compare_outputs(a, b, compare.VOLATILE)
            self.assertFalse(res['all_identical'])
            self.assertAlmostEqual(res['files'][0]['max_abs_difference'], 1e-7)

    def test_raw_overlap_reproduces_recorded_grid_comparison(self):
        raw = PKG / 'data/hamiltonian/raw'
        c = compare.compare_raw(raw / 'extended_k1_a0.1.json', [raw / 'fine_k1_a0.1.json'])['comparisons'][0]
        rec = json.loads((raw / 'extended_k1_a0.1.json').read_text())['cauchy_grid_comparison']
        self.assertEqual(c['overlap_N'], 256)
        self.assertAlmostEqual(c['max_abs_difference'], rec['maximum_overlap_difference'], delta=1e-12)
        self.assertAlmostEqual(c['last_overlap_difference'], rec['overlap_last_difference'], delta=1e-12)

    def merge(self, d: Path, *extra: str) -> tuple[subprocess.CompletedProcess, dict]:
        out = d / 'merged.json'
        r = run([sys.executable, str(HERE / 'merge_records.py'), '--site-dir', f'expanse={d}/expanse',
                 '--site-dir', f'symmetry={d}/symmetry', '--output', str(out), *extra])
        return r, (json.loads(out.read_text()) if out.is_file() else {})

    def two_sites(self, d: Path, symmetry_job: dict | None = None, symmetry_sources: dict | None = None):
        job = {'id': 'R', 'stage': 'X', 'cutoff': 384, 'order': 1, 'lambda': [0.1], 'mixed_cutoff': 16384,
               'collapsed_cutoff': 800000, 'tail_cutoff': 8192, 'oversample': 4, 'radius_cost': 4.5}
        publish_row(d / 'expanse/outputs/production_plan/R_x', job, site='expanse')
        extra = {'source_hashes': symmetry_sources} if symmetry_sources else None
        publish_row(d / 'symmetry/outputs/production_plan/R_x', symmetry_job or job, extra, site='symmetry')

    def test_merge_two_sites_replica(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.two_sites(d)
            r, m = self.merge(d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(sorted(x['site'] for x in m['records']), ['expanse', 'symmetry'])
            (c,) = m['overlap_comparisons']
            self.assertTrue(c['cross_site'])
            self.assertEqual(c['classification'], 'replica')
            for key in ('source_hashes', 'plan_sha256', 'config', 'cpu_vendor'):
                self.assertIn(key, m['records'][0])
            self.assertEqual(m['records'][0]['config']['mixed_cutoff'], 16384)

    def test_merge_variant_and_incompatible(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            job = {'id': 'R', 'stage': 'X', 'cutoff': 384, 'order': 1, 'lambda': [0.1], 'mixed_cutoff': 4096,
                   'collapsed_cutoff': 800000, 'tail_cutoff': 8192, 'oversample': 4, 'radius_cost': 4.5}
            self.two_sites(d, symmetry_job=job)
            r, m = self.merge(d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(m['overlap_comparisons'][0]['classification'], 'variant')
            self.assertEqual(m['overlap_comparisons'][0]['differing'], ['mixed_cutoff'])
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.two_sites(d, symmetry_sources={'reproduce.py': 'c' * 64})
            r, m = self.merge(d)
            self.assertEqual(r.returncode, 1)
            self.assertEqual(len(m['incompatibilities']), 1)
            self.assertFalse(m['all_verified_and_compatible'])
            r, m = self.merge(d, '--allow-mixed-sources')
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertEqual(m['overlap_comparisons'][0]['classification'], 'incompatible')

    def test_merge_rejects_unverified_input(self):
        def damage(fn):
            with tempfile.TemporaryDirectory() as d:
                d = Path(d)
                self.two_sites(d)
                fn(d / 'symmetry/outputs/production_plan/R_x')
                r, m = self.merge(d)
                self.assertEqual(r.returncode, 1, fn)
                self.assertTrue(m['problems'])
                self.assertEqual(len(m['records']), 1)       # only the verified site's record is indexed
        damage(lambda t: (t / 'SHA256SUMS').write_text(''))
        damage(lambda t: (t / 'cluster_k1_a0.1_N999.json').write_text('{}'))          # unlisted record
        damage(lambda t: (t / 'SHA256SUMS').write_text((t / 'SHA256SUMS').read_text() + 'a' * 64 + '  ../x\n'))
        damage(lambda t: (t / 'SHA256SUMS').write_text((t / 'SHA256SUMS').read_text() * 2))      # duplicates

        def no_job_receipt(t):
            (t / 'job_receipt.json').unlink()
            lines = [l for l in (t / 'SHA256SUMS').read_text().splitlines() if 'job_receipt' not in l]
            (t / 'SHA256SUMS').write_text('\n'.join(lines) + '\n')
        damage(no_job_receipt)


class ShellTests(unittest.TestCase):
    def test_shell_syntax(self):
        paths = sorted(HERE.glob('*.sh')) + sorted(HERE.glob('*.sbatch'))
        for site in SITES:
            paths += sorted((PKG / 'cluster' / site).glob('*.sh'))
        for path in paths:
            r = run(['bash', '-n', str(path)])
            self.assertEqual(r.returncode, 0, f'{path}: {r.stderr}')

    def test_job_scripts(self):
        for path in sorted(HERE.glob('*.sbatch')):
            text = path.read_text()
            self.assertNotRegex(text, r'(?m)^\s*set\s+-[a-z]*u', path.name)
            self.assertIn('#SBATCH --nodes=1', text)
            sb = '\n'.join(l for l in text.splitlines() if l.startswith('#SBATCH'))
            for site_specific in ('--ntasks-per-node', '-A ', '-p ', '--partition', '--mem', '-t '):
                self.assertNotIn(site_specific, sb, path.name)
            self.assertIn('sha256sum -c', text)
            self.assertIn('$LRI_NODE_SCRATCH_BASE/job_$SLURM_JOB_ID', text)
            self.assertIn('lri_require_shipped_script ' + path.name, text)
        self.assertNotRegex((HERE / 'lib.sh').read_text(), r'(?m)^\s*set\s+-')

    @unittest.skipUnless(GNU, 'needs GNU coreutils/findutils (Linux)')
    def test_publish_and_fetch(self):
        with tempfile.TemporaryDirectory() as d:
            script = f'''
            STAGE={d}; SLURM_JOB_ID=7; PKG={PKG}; PY={sys.executable}; source {HERE / 'lib.sh'}
            mkdir -p {d}/src && echo a > {d}/src/a.npy && echo b > {d}/src/a.json
            echo '{{"array": "a.npy", "array_bytes": 2}}' > {d}/src/grid_receipt.json
            lri_write_sums {d}/src || exit 11
            lri_publish_dir {d}/src {d}/shared/grids/G || exit 12
            lri_publish_dir {d}/src {d}/shared/grids/G && exit 13
            lri_fetch_grid {d}/shared/grids/G {d}/node/G || exit 14
            echo corrupt >> {d}/shared/grids/G/a.npy
            lri_fetch_grid {d}/shared/grids/G {d}/node/G2 && exit 15
            ls -a {d}/shared/grids | grep -q partial && exit 16
            exit 0
            '''
            r = run(['bash', '-c', script])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class TarballTests(unittest.TestCase):
    @unittest.skipUnless((PKG / '.git').exists() and shutil.which('git'), 'needs the git checkout')
    def test_make_tarball_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            r = run(['bash', str(HERE / 'make_tarball.sh'), '--allow-dirty', '--out', d])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            tars = list(Path(d).glob('lri_c2_*.tar'))
            self.assertEqual(len(tars), 1)
            subprocess.run(['tar', '-xf', str(tars[0]), '-C', d], check=True)
            root = Path(d) / 'lri_c2'
            info = json.loads((root / 'STAGE_INFO.json').read_text())
            self.assertEqual(info['name'] + '.tar', tars[0].name)
            listed = {line.split('  ', 1)[1] for line in (root / 'STAGE_MANIFEST.sha256').read_text().splitlines()}
            files = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()} - {'STAGE_MANIFEST.sha256'}
            self.assertEqual(listed, files)
            self.assertIn('cluster/sitekit/rows_job.sbatch', files)

    @unittest.skipUnless((PKG / '.git').exists() and shutil.which('git'), 'needs the git checkout')
    def test_clean_builds_are_reproducible(self):
        commit = run(['git', '-C', str(PKG), 'rev-parse', 'HEAD']).stdout.strip()
        sums = []
        for i in range(2):
            with tempfile.TemporaryDirectory() as d:
                r = run(['bash', str(HERE / 'make_tarball.sh'), '--commit', commit, '--out', d])
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                sums.append((Path(d) / f'lri_c2_{commit[:12]}.tar.sha256').read_text())
                info = subprocess.run(['tar', '-xOf', str(Path(d) / f'lri_c2_{commit[:12]}.tar'),
                                       'lri_c2/STAGE_INFO.json'], capture_output=True, text=True).stdout
                ctime = run(['git', '-C', str(PKG), 'show', '-s', '--format=%ct', commit]).stdout.strip()
                import datetime
                want = datetime.datetime.fromtimestamp(int(ctime), datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                self.assertEqual(json.loads(info)['created_utc'], want)
            if i == 0:
                import time
                time.sleep(1.1)
        self.assertEqual(sums[0], sums[1])


class R2FetchTests(unittest.TestCase):
    """R2-001: no manifest entry can make a copy write outside its target."""

    def setup_grid(self, d: Path) -> tuple[Path, Path, Path]:
        stage = d / 'stage'
        victim = stage / 'lri_c2' / 'cluster' / 'run_task.py'
        victim.parent.mkdir(parents=True)
        victim.write_text('verified launcher\n')
        src = d / 'shared' / 'grids' / 'G'
        publish_grid(src)
        return stage, victim, src

    def lib(self, d: Path, stage: Path, body: str) -> subprocess.CompletedProcess:
        return run(['bash', '-c', f'STAGE={stage}; SLURM_JOB_ID=7; PKG={PKG}; PY={sys.executable}; '
                                  f'source {HERE / "lib.sh"}; {body}'])

    def test_traversal_manifest_cannot_overwrite_the_staged_launcher(self):
        import hashlib
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            stage, victim, src = self.setup_grid(d)
            evil = d / 'shared' / 'lri_c2' / 'cluster' / 'run_task.py'      # src/../../lri_c2/cluster/run_task.py
            evil.parent.mkdir(parents=True)
            evil.write_text('evil launcher\n')
            digest = hashlib.sha256(evil.read_bytes()).hexdigest()
            with (src / 'SHA256SUMS').open('a') as f:
                f.write(f'{digest}  ../../lri_c2/cluster/run_task.py\n')
            r = self.lib(d, stage, f'lri_fetch_grid {src} {stage}/grid_cache/G')
            self.assertEqual(r.returncode, 74, r.stdout + r.stderr)
            self.assertEqual(victim.read_text(), 'verified launcher\n')
            self.assertEqual(sorted(x.name for x in (stage / 'grid_cache' / 'G').iterdir()), ['SHA256SUMS'])
            out = d / 'pub'
            r = self.lib(d, stage, f'lri_publish_dir {src} {out}')                     # same rule when publishing
            self.assertEqual(r.returncode, 74)
            self.assertFalse(out.exists())

    def test_only_listed_regular_files_and_a_complete_grid(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            stage, _, src = self.setup_grid(d)
            (src / '.hidden').write_text('x')                     # unlisted entries are never copied ...
            r = self.lib(d, stage, f'lri_fetch_grid {src} {stage}/A')
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(sorted(x.name for x in (stage / 'A').iterdir()),
                             ['SHA256SUMS', 'g.json', 'g.npy', 'grid_receipt.json'])
            (src / 'g.json').unlink()
            (src / 'g.json').symlink_to(src / 'grid_receipt.json')   # ... and listed symlinks are rejected
            self.assertEqual(self.lib(d, stage, f'lri_fetch_grid {src} {stage}/B').returncode, 74)
            (src / 'g.json').unlink()
            (src / 'g.json').write_text('{}')
            lines = [l for l in (src / 'SHA256SUMS').read_text().splitlines() if 'grid_receipt' not in l]
            (src / 'SHA256SUMS').write_text('\n'.join(lines) + '\n')         # incomplete grid manifest
            self.assertEqual(self.lib(d, stage, f'lri_fetch_grid {src} {stage}/C').returncode, 74)

    def test_transfer_copies_only_validated_names(self):
        text = (HERE / 'transfer_grid.sh').read_text()
        self.assertNotIn("awk '{print", text)
        self.assertLess(text.index('names $PART'), text.index('while IFS= read -r f'))
        lib = (HERE / 'lib.sh').read_text()
        self.assertNotIn('read -r _ f', lib)
        self.assertNotIn('lri_fetch_dir', (HERE / 'rows_job.sbatch').read_text())


class R2CollectionTests(unittest.TestCase):
    """R2-002 and R2-004: collection consumes only verified, listed, valid records."""
    JOB = {'id': 'R', 'stage': 'X', 'cutoff': 512, 'order': 1, 'lambda': [0.1], 'mixed_cutoff': 64,
           'collapsed_cutoff': 1000, 'tail_cutoff': 8192, 'oversample': 4, 'radius_cost': 4.5}

    def plan_dir(self, d: Path) -> Path:
        plan = d / 'root' / 'outputs' / 'production_plan'
        publish_row(plan / 'R_x', self.JOB)
        (d / 'root' / 'receipts').mkdir()
        return plan

    def collect(self, d: Path) -> subprocess.CompletedProcess:
        return run(['bash', str(HERE / 'collect.sh'), '--site', 'expanse', '--host', '', '--root', str(d / 'root'),
                    '--dest', str(d / 'dest'), '--python', sys.executable])

    def test_collect_indexes_exactly_the_verified_records(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            plan = self.plan_dir(d)
            (plan / '.R_y.partial.123').mkdir()                    # interrupted publish: ignored
            r = self.collect(d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            index = json.loads((d / 'dest' / 'record_index.json').read_text())
            self.assertEqual([Path(x['path']).name for x in index['records']], ['cluster_k1_a0.1_N512.json'])
            listed = (d / 'dest' / 'verified_records.txt').read_text().split()
            self.assertEqual(len(listed), 1)

    def test_stray_records_fail_collection(self):
        for where in ('plan', 'nested'):
            with tempfile.TemporaryDirectory() as d:
                d = Path(d)
                plan = self.plan_dir(d)
                stray = fake_record(self.JOB, 0.1, shift=5.0)
                if where == 'plan':
                    (plan / 'cluster_k1_a0.1_N512.json').write_text(json.dumps(stray))
                else:
                    (plan / 'R_x' / 'backup').mkdir()
                    (plan / 'R_x' / 'backup' / 'cluster_k1_a0.1_N512.json').write_text(json.dumps(stray))
                r = self.collect(d)
                self.assertEqual(r.returncode, 74, where + r.stdout + r.stderr)
                self.assertFalse((d / 'dest' / 'record_index.json').exists())

    def test_records_from_restricts_indexing(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            plan = self.plan_dir(d)
            other = plan / 'R_x' / 'cluster_k1_a0.2_N512.json'
            other.write_text(json.dumps(fake_record(dict(self.JOB, **{'lambda': [0.2]}), 0.2)))
            listing = d / 'list.txt'
            listing.write_text(str(plan / 'R_x' / 'cluster_k1_a0.1_N512.json') + '\n')
            out = d / 'index.json'
            r = run([sys.executable, str(PKG / 'cluster/collect_records.py'), '--records-from', str(listing),
                     '--compare-overlaps', '--output', str(out)])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(len(json.loads(out.read_text())['records']), 1)
            r = run([sys.executable, str(HERE / 'compare.py'), 'archive-overlaps', str(plan), str(PKG / 'data/hamiltonian/raw'),
                     '--records-from', str(listing), '--out', str(d / 'ov.json')])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(len(json.loads((d / 'ov.json').read_text())['records']), 1)

    def test_semantic_validator(self):
        sys.path.insert(0, str(PKG / 'cluster'))
        from collect_records import validate_record
        name = Path('cluster_k1_a0.1_N512.json')
        self.assertEqual(validate_record(name, fake_record(self.JOB, 0.1)), [])
        short = fake_record(self.JOB, 0.1, length=384)                     # N=512 declared, 384 entries
        self.assertTrue(any('384 values, declared 512' in x for x in validate_record(name, short)))
        bad = fake_record(self.JOB, 0.1)
        bad['raw']['Xchain'][7] = float('nan')
        self.assertTrue(validate_record(name, bad))
        bad = fake_record(self.JOB, 0.1)
        bad['mixed']['Nmax'] = 65
        self.assertTrue(validate_record(name, bad))
        self.assertTrue(validate_record(Path('cluster_k1_a0.2_N512.json'), fake_record(self.JOB, 0.1)))
        self.assertTrue(validate_record(Path('cluster_k1_a0.1_N384.json'), fake_record(self.JOB, 0.1)))
        bad = fake_record(self.JOB, 0.1)
        bad['raw']['lam'] = 0.2
        self.assertTrue(validate_record(name, bad))
        for real in sorted((PKG / 'data/hamiltonian/raw').glob('*.json')):          # every archived record passes
            value = json.loads(real.read_text())
            value = value.get('data', value)
            self.assertEqual(validate_record(real, value), [], real.name)

    def test_short_sequence_rejected_by_collector_and_merger(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            plan = d / 'site' / 'outputs' / 'production_plan'
            publish_row(plan / 'R_x', self.JOB, length=384)
            out = d / 'index.json'
            r = run([sys.executable, str(PKG / 'cluster/collect_records.py'), '--input-root', str(plan),
                     '--output', str(out)])
            self.assertEqual(r.returncode, 1)
            self.assertIn('384 values, declared 512', r.stderr)
            r = run([sys.executable, str(HERE / 'merge_records.py'), '--site-dir', f'a={d}/site', '--output', str(out)])
            self.assertEqual(r.returncode, 1)
            self.assertEqual(json.loads(out.read_text())['records'], [])


class R2SubmitTests(unittest.TestCase):
    def setUp(self):
        self.site = FakeSite()

    def tearDown(self):
        self.site.close()

    def test_r2_005_positive_integers_before_any_submission(self):
        for spec in ('rows_per_job=-1', 'rows_per_job=0', 'max_concurrent=0', 'cpus=-4', 'mem_gb=0', 'workers=0',
                     'workers=-2', 'cpus=1.5'):
            r, cmds = self.site.submit('symmetry', '--stage', 'P1', '--task-resources', spec)
            self.assertEqual(r.returncode, 64, spec + r.stdout + r.stderr)
            self.assertEqual(cmds, [], spec)
        problems = []
        for prof in ({'rows_per_job': -1}, {'workers': 0}, {'cpus': 0}, {'mem_gb': -5}, {'max_concurrent': 0},
                     {'cpus': True}):
            problems.clear()
            submit.check_limits(submit.load_profile('expanse'), dict({'partition': 'shared', 'cpus': 2, 'mem_gb': 4,
                                                                      'time': '01:00:00'}, **prof), 'x', problems)
            self.assertTrue(any('positive integer' in x for x in problems), prof)

    def test_r2_006_probe_counts_against_the_normal_qos_ceiling(self):
        compute = ['--probe', '--task-resources', 'partition=compute,cpus=128,mem_gb=240,time=00:30:00']
        self.site.squeue_account = ''.join(f'{i}\n' for i in range(22))
        r, cmds = self.site.submit('expanse', *compute)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn('would exceed 22', r.stderr)
        self.assertEqual(cmds, [])
        self.site.squeue_account = ''.join(f'{i}\n' for i in range(21))
        r, cmds = self.site.submit('expanse', *compute)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(cmds), 1)

    def test_r2_007_array_elements_hold_only_their_own_row(self):
        r, cmds = self.site.submit('expanse', '--stage', 'P2')
        comment = next(c for c in cmds[-1] if c.startswith('--comment='))[len('--comment='):]
        self.assertTrue(comment.startswith('lri1;a=4:') and '+5:' in comment)
        # element 4 failed (gone from the queue), element 5 still pending: retrying row 4 is allowed
        self.site.squeue_user = f'801_5|lri_c2_task_production_plan_N1024|PENDING|{comment}\n'
        r, cmds = self.site.submit('expanse', '--tasks', '4')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('--array=4%2', cmds[-1])
        r, cmds = self.site.submit('expanse', '--tasks', '5')
        self.assertEqual(r.returncode, 1)
        self.assertIn('801_5', r.stdout)
        self.site.squeue_user = f'801_[4-5%2]|lri_c2_task_production_plan_N1024|PENDING|{comment}\n'   # unexpanded
        self.assertEqual(self.site.submit('expanse', '--tasks', '4')[0].returncode, 1)


class R2MergeProvenanceTests(unittest.TestCase):
    def job(self, lam: float) -> dict:
        return {'id': 'R', 'stage': 'X', 'cutoff': 64, 'order': 1, 'lambda': [lam], 'mixed_cutoff': 32,
                'collapsed_cutoff': 1000, 'tail_cutoff': 8192, 'oversample': 4, 'radius_cost': 4.5}

    def merge(self, d: Path, *extra: str) -> tuple[subprocess.CompletedProcess, dict]:
        out = d / 'm.json'
        r = run([sys.executable, str(HERE / 'merge_records.py'), '--site-dir', f'a={d}/a', '--site-dir', f'b={d}/b',
                 '--output', str(out), *extra])
        return r, json.loads(out.read_text())

    def test_disjoint_rows_with_different_sources_fail(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            publish_row(d / 'a/outputs/production_plan/R1', self.job(0.1))
            publish_row(d / 'b/outputs/production_plan/R2', self.job(0.2), {'source_hashes': {'reproduce.py': 'c' * 64}})
            r, m = self.merge(d)
            self.assertEqual(r.returncode, 1)
            self.assertEqual(m['overlap_comparisons'], [])            # no (order, lambda) overlap at all
            self.assertTrue(any('different scientific source sets' in x for x in m['problems']))
            r, m = self.merge(d, '--allow-mixed-sources')
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertEqual(len(m['source_sets']), 2)

    def test_missing_provenance_fails_without_a_partner(self):
        for extra in ({'source_hashes': {}}, {'source_hashes': None}, {'plan_sha256': None}, {'plan_sha256': 'x'}):
            with tempfile.TemporaryDirectory() as d:
                d = Path(d)
                publish_row(d / 'a/outputs/production_plan/R1', self.job(0.1))
                publish_row(d / 'b/outputs/production_plan/R2', self.job(0.2), extra)
                r, m = self.merge(d)
                self.assertEqual(r.returncode, 1, extra)
                self.assertTrue(any('task_receipt.json lacks' in x for x in m['problems']), extra)


class R2UploadTests(unittest.TestCase):
    FAKE_SSH = """#!/bin/bash
while [[ $1 == -* ]]; do if [[ $1 == -o ]]; then shift 2; else shift; fi; done
shift
exec bash -c "$*"
"""
    FAKE_SCP = """#!/bin/bash
while [[ $1 == -* ]]; do if [[ $1 == -o ]]; then shift 2; else shift; fi; done
cp "${1#*:}" "${2#*:}"
"""

    @unittest.skipUnless((PKG / '.git').exists() and shutil.which('git'), 'needs the git checkout')
    def test_r2_009_unverifiable_existing_code_copy_fails_the_upload(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / 'bin').mkdir()
            for name, text in (('ssh', self.FAKE_SSH), ('scp', self.FAKE_SCP)):
                (d / 'bin' / name).write_text(text)
                (d / 'bin' / name).chmod(0o755)
            (d / 'home').mkdir()
            env = dict(os.environ, PATH=f"{d / 'bin'}{os.pathsep}{os.environ['PATH']}", HOME=str(d / 'home'))
            commit = run(['git', '-C', str(PKG), 'rev-parse', 'HEAD']).stdout.strip()   # clean, reproducible build
            cmd = ['bash', str(HERE / 'make_tarball.sh'), '--commit', commit, '--out', str(d / 'out'),
                   '--upload', 'expanse', '--remote-root', str(d / 'remote')]
            r = run(cmd, env=env)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            copy = next((d / 'home' / 'lri_c2' / 'pkgs').glob('lri_c2_*'))
            r = run(cmd, env=env)                                              # same build, intact copy: reused
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn('code copy verified', r.stdout)
            (copy / 'cluster' / 'run_task.py').write_text('# modified\n')
            r = run(cmd, env=env)
            self.assertEqual(r.returncode, 74, r.stdout + r.stderr)
            self.assertNotIn('UPLOADED', r.stdout)


CASES = [PlanTests, CheckTests, DryRunTests, R001BindingTests, R002RowSelectionTests, R003PublishedTests,
         R004R005QueueTests, R009HeadroomTests, R010ProbeTests, R011RegressionTests, R012ProbeLimitTests,
         R2FetchTests, R2CollectionTests, R2SubmitTests, R2MergeProvenanceTests, R2UploadTests,
         JobtoolsTests, TailCutoffTests, CompareAndMergeTests, ShellTests, TarballTests]


def run_cases(cases, output: Path | None, scope: str) -> None:
    suite = unittest.TestSuite()
    for case in cases:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'tests_run': result.testsRun, 'successful': result.wasSuccessful(),
              'skipped': [f'{t}: {why}' for t, why in result.skipped],
              'failures': [str(x[0]) for x in result.failures], 'errors': [str(x[0]) for x in result.errors],
              'platform': sys.platform, 'python': sys.version.split()[0], 'scope': scope}
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + '\n')
    if not result.wasSuccessful():
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    run_cases(CASES, parser.parse_args().output,
              'Site-independent launch layer and site-neutral plan: plan rules, profile checks for both sites, sbatch '
              'commands, dry-run submission planning, job helpers, tail-cutoff plumbing, comparisons and cross-site '
              'merging, shell syntax, publish/fetch checksums (GNU only) and the tarball manifest. No scheduler or '
              'large array is exercised.')


if __name__ == '__main__':
    main()
