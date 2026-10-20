#!/usr/bin/env python3
"""Validation receipt for one staged release on one node class (run by validate.sbatch).

Every stage runs in a subprocess with its own log; the receipt passes only if every gate
stage exits 0. Stages:
  environment      pinned packages, x87 long double, compiler, release fingerprint, venv path
  filesystems      data and lock file systems: type, mount options (Expanse Lustre must not be
                   'localflock'; symmetry NFS needs local_lock=none), hard links on the data FS
  test_*           the package's own checks, writing only to node-local scratch
  mpi_launcher     first site launcher (sites/<site>.sh, cluster/launch.py) giving a correct
                   2-rank world
  test_mpi2/4      tests/check_mpi_backend.py on 2 and 4 ranks through that launcher
  test_driver      tests/check_hpc_driver.py on the L4 fixture, including real 2-rank MPI
  fixture_x87      the shipped L4 fixture, both schemes, tolerance 1e-16 (x87 evidence)
  pipeline_L14     an L14 store built through the production stage runner on the data file
                   system (prepare..verify), then the cutoff-14 reference gate (both schemes)
  pipeline_L4      an L4 store built the same way; its arrays are compared bitwise with the
                   shipped fixture (informational: BLAS/libm may legitimately differ)
  grid_L14         tests/check_saved_coefficients.py on that store: 8 cutoffs x 2 schemes x
                   2 strategies vs the saved reference, plus every recursion residual <= 1e-16
  mpi_L14          2-rank MPI solves at cutoff 14 vs the serial gate results (<= 1e-15)
  drill_*          srun without --mpi refused; busy target refused (exit 75); stale partials
                   swept; SIGTERM during prepare leaves no partial directory; SIGTERM to a
                   runner with a busy lane and queued tasks starts nothing more (exit 75)
The receipt also records lscpu, NUMA, cgroup limits, BLAS/thread pools, the job allocation,
the lock root and its mount, the environment identity (interpreter, every installed package
version, compiler, mpi4py build) that campaigns are bound to, and a value fingerprint of the L14 store (padding bytes of x87
long doubles excluded) for comparing builds across sites. JSON reports of every test are kept
under <out>/reports on the shared file system.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT/'code'), str(ROOT/'vendor'), str(HERE)]

PY = [sys.executable, '-E']
RESIDUAL_LIMIT = '1e-16'
MPI_LIMIT = '1e-15'


class Receipt:
    def __init__(self, out, work):
        self.out, self.work = Path(out), Path(work)
        self.logs = self.out/'logs'
        self.logs.mkdir(parents=True, exist_ok=True)
        self.work.mkdir(parents=True, exist_ok=True)
        self.stages = []

    def run(self, name, command, *, cwd=None, env=None, gate=True, timeout=None, expect_fail=None):
        """expect_fail: a phrase that must appear in a failing run (the stage passes then)."""
        log = self.logs/f'{name}.log'
        started = time.perf_counter()
        with open(log, 'w') as handle:
            handle.write('$ ' + ' '.join(shlex.quote(str(c)) for c in command) + '\n')
            handle.flush()
            try:
                rc = subprocess.run([str(c) for c in command], cwd=cwd or self.work, stdout=handle,
                                    stderr=subprocess.STDOUT, env=env or clean_env(),
                                    timeout=timeout).returncode
            except subprocess.TimeoutExpired:
                rc = 124
        text = log.read_text(errors='replace')
        record = dict(stage=name, rc=rc, seconds=round(time.perf_counter()-started, 2),
                      log=str(log), tail=text.splitlines()[-4:], gate=gate)
        if expect_fail is not None:
            record['expected_failure'] = expect_fail
            record['rc'] = 0 if (rc != 0 and expect_fail in text) else 1
        self.stages.append(record)
        print(json.dumps(dict(stage=name, rc=record['rc'], seconds=record['seconds'])), flush=True)
        return record

    def check(self, name, function, gate=True):
        """In-process check; function returns a dict of facts or raises."""
        started = time.perf_counter()
        try:
            facts = function()
            rc = 0
        except Exception as exc:
            facts = dict(error=f'{type(exc).__name__}: {exc}')
            rc = 1
        record = dict(stage=name, rc=rc, seconds=round(time.perf_counter()-started, 2), gate=gate,
                      facts=facts)
        self.stages.append(record)
        print(json.dumps(dict(stage=name, rc=rc, seconds=record['seconds'])), flush=True)
        return record


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('PYTHONOPTIMIZE', 'PYTHONWARNINGS', 'PYTHONSTARTUP', 'PYTHONPATH',
                                'PYTHONHOME', 'PYTEST_'))}
    env.update({k: str(v) for k, v in extra.items()})
    return env


def sh(command):
    try:
        return subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120).stdout
    except subprocess.TimeoutExpired:
        return ''


# ---------------------------------------------------------------- stages

def environment():
    import numpy as np
    from importlib import metadata
    lock = (HERE/'requirements.lock').read_text()
    pins = dict(re.findall(r'^([A-Za-z0-9_.-]+)==([^\s\\]+)', lock, re.M))
    pins['mpi4py'] = '4.1.2'
    have = {name: metadata.version(name) for name in pins}
    bad = {n: (pins[n], have[n]) for n in pins if have[n] != pins[n]}
    venv = os.environ.get('HT3D_VENV', '')
    facts = dict(python=sys.version, executable=sys.executable, packages=have,
                 longdouble_nmant=int(np.finfo(np.longdouble).nmant),
                 compiler=sh(f'{shlex.quote(os.environ.get("CXX", "c++"))} --version').splitlines()[:1],
                 release_fingerprint=os.environ.get('HT3D_RELEASE_FINGERPRINT'),
                 git_sha=os.environ.get('HT3D_GIT_SHA'), site=os.environ.get('HT3D_SITE'))
    actual = hashlib.sha256((ROOT/'RELEASE.sha256').read_bytes()).hexdigest()
    problems = []
    if bad:
        problems.append(f'package pins {bad}')
    if facts['longdouble_nmant'] != 63:
        problems.append('long double is not x87 (nmant != 63)')
    if not sys.version.startswith('3.12.9'):
        problems.append('python is not 3.12.9')
    if not venv or not sys.executable.startswith(venv):
        problems.append(f'python {sys.executable} is not in HT3D_VENV {venv}')
    if facts['release_fingerprint'] != actual:
        problems.append('HT3D_RELEASE_FINGERPRINT does not match the staged RELEASE.sha256')
    if problems:
        raise AssertionError('; '.join(problems))
    return facts


def filesystems():
    from ht3d_stage import lock_filesystem_problem, mount_of
    site = os.environ['HT3D_SITE']
    data, locks = os.environ['HT3D_DATA'], os.environ['HT3D_LOCK_ROOT']
    Path(locks).mkdir(parents=True, exist_ok=True)
    facts = dict(data=mount_of(data), locks=mount_of(locks), lock_root=str(Path(locks).resolve()))
    problem = lock_filesystem_problem(site, locks)
    if problem:
        raise AssertionError(problem)
    probe = Path(data)/'validation'/f'.linkprobe-{socket.gethostname()}-{os.getpid()}'
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text('x')
    try:
        os.link(probe, str(probe) + '.link')
        try:
            os.link(probe, str(probe) + '.link')
            raise AssertionError('hard link onto an existing name succeeded')
        except FileExistsError:
            facts['hard_link_no_clobber'] = True
    finally:
        probe.unlink(missing_ok=True)
        Path(str(probe) + '.link').unlink(missing_ok=True)
    return facts


def node_facts():
    from ht3d_coefficients import library_provenance, node_provenance
    from ht3d_stage import allowed_cpus, cgroup_memory_limit
    return dict(node=node_provenance(), libraries=library_provenance(),
                allowed_cpus=allowed_cpus(), cgroup_memory_limit=cgroup_memory_limit(),
                lscpu=sh('lscpu'), numa=sh('numactl -H 2>/dev/null || true'), free=sh('free -g'),
                uname=platform.uname()._asdict(),
                slurm={k: v for k, v in os.environ.items() if k.startswith('SLURM_')})


def make_campaign(root, name):
    """A throwaway campaign on the data file system, pinned to this node's CPU class."""
    from ht3d_coefficients import node_provenance
    node = node_provenance()
    root.mkdir(parents=True, exist_ok=True)
    campaign = dict(format='ht3d-campaign-v1', name=name, site=os.environ['HT3D_SITE'],
                    order=8, degree=6, dtype='longdouble',
                    lock_dir=str(Path(os.environ['HT3D_LOCK_ROOT'])/name),
                    cpu_class={k: node.get(k) for k in ('vendor_id', 'model name')},
                    release=dict(fingerprint=os.environ.get('HT3D_RELEASE_FINGERPRINT')))
    (root/'campaign.json').write_text(json.dumps(campaign, indent=1) + '\n')
    return campaign


def compare_results(a_path, b_path, limit):
    import numpy as np
    from ht3d_stage import scaled_difference
    diff = scaled_difference(json.loads(Path(a_path).read_text())['result'],
                             json.loads(Path(b_path).read_text())['result'])
    if not diff <= np.longdouble(limit):
        raise AssertionError(f'{a_path} vs {b_path}: {diff} > {limit}')
    return dict(max_scaled_difference=str(diff), limit=limit)


def grid_facts(path):
    import numpy as np
    report = json.loads(Path(path).read_text())
    residuals = [r['result']['max_scaled_seed_recursion_residual'] for r in report['rows']]
    worst = max(residuals)
    if not (report.get('passed') is True and report.get('cases') == 32):
        raise AssertionError(f'grid report not passed or not 32 cases: {report.get("cases")}')
    if not worst <= float(RESIDUAL_LIMIT):
        raise AssertionError(f'recursion residual {worst} > {RESIDUAL_LIMIT}')
    return dict(cases=report['cases'], max_scaled_error=report['max_scaled_error'],
                max_recursion_residual=worst, store_manifest_sha256=report['store_manifest_sha256'],
                limit_coefficients='5e-13', limit_residual=RESIDUAL_LIMIT,
                significand_bits=report['precision_significand_bits'],
                max_error_by_strategy={s: str(max(np.longdouble(r['validation']['max_scaled_error'])
                                                  for r in report['rows'] if r['strategy'] == s))
                                       for s in ('stationary', 'recurrence')})


def mpi_identity_coverage():
    """Every library the mpi4py extension resolves (an independent ldd parse) is in the
    environment identity with a sha256, so changing any of them (UCX included) changes the
    fingerprint; and the launchers are recorded."""
    import importlib.util
    from ht3d_stage import environment_identity
    origin = importlib.util.find_spec('mpi4py.MPI').origin
    listed = subprocess.run(['ldd', origin], capture_output=True, text=True, timeout=60).stdout
    names = {l.strip().split(' => ')[0] for l in listed.splitlines() if ' => ' in l}
    identity = environment_identity()[0]['mpi_runtime']
    recorded = identity.get('libraries', {})
    missing = sorted(names - set(recorded))
    unhashed = sorted(n for n, v in recorded.items() if not (isinstance(v, dict) and v.get('sha256')))
    if missing or unhashed or not names or not identity.get('launchers'):
        raise AssertionError(dict(missing=missing, unhashed=unhashed, launchers=identity.get('launchers')))
    return dict(libraries=len(names), ucx=sorted(n for n in names if n.startswith('libuc')),
                launchers=sorted(identity['launchers']))


def mpi_store_check(store, gates):
    """Regression coverage for ht3d_mpi.validated_store (the multi-node receipt's store check)."""
    import ht3d_mpi
    record = ht3d_mpi.validated_store(store, gates)
    if not record.get('passed'):
        raise AssertionError(record)
    return record


def fixture_bitwise(store, fixture):
    mine = json.loads((Path(store)/'manifest.json').read_text())
    ref = json.loads((Path(fixture)/'manifest.json').read_text())
    def arrays(m):
        out = {'N': m['N']['sha256'], 'P': m['P']['sha256']}
        for key, rec in m['matrices'].items():
            out[f'W{key}.data'] = rec['data']['sha256']
            out[f'W{key}.pattern'] = rec['pattern']
        return out
    a, b = arrays(mine), arrays(ref)
    differ = sorted(k for k in b if a.get(k) != b[k])
    return dict(bitwise_identical=not differ, differing=differ, compared=len(b))


def sigterm_drill(campaign_root, cutoff):
    """SIGTERM during prepare: the task must clean its partial directory and exit 143."""
    from ht3d_stage import Layout
    layout = Layout(campaign_root, cutoff)
    proc = subprocess.Popen(PY + [str(HERE/'ht3d_stage.py'), 'task', 'prepare', 'all',
                                  '--campaign', str(campaign_root), '--cutoff', str(cutoff)],
                            env=clean_env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    seen, began = False, time.time()
    while proc.poll() is None and time.time()-began < 600:
        if list(layout.prepared.parent.glob(layout.prepared.name + '.partial-*')):
            seen = True
            time.sleep(1.0)
            proc.send_signal(signal.SIGTERM)
            break
        time.sleep(0.05)
    try:
        output, _ = proc.communicate(timeout=300)
    except subprocess.TimeoutExpired:
        proc.kill()
        output, _ = proc.communicate()
        raise AssertionError('prepare did not exit within 300 s of SIGTERM')
    leftovers = list(layout.prepared.parent.glob(layout.prepared.name + '.partial-*'))
    if not seen:
        raise AssertionError(f'prepare finished before a partial directory was seen: {output[-500:]}')
    if proc.returncode != 143 or leftovers or layout.prepared.exists():
        raise AssertionError(f'rc={proc.returncode} leftovers={leftovers} published={layout.prepared.exists()} '
                             f'output={output[-500:]}')
    return dict(rc=proc.returncode, output_tail=output.splitlines()[-2:])


def runner_stop_drill(campaign_root, cutoff):
    """SIGTERM to a stage runner (parent only) while one lane is busy and more tasks are queued:
    it must log the stop, start nothing afterwards, let the running task finish, exit 75."""
    proc = subprocess.Popen(PY + [str(HERE/'ht3d_stage.py'), 'run', '--campaign', str(campaign_root),
                                  '--cutoff', str(cutoff), '--stages', 'prepare,images,matrix', '--lanes', '1'],
                            env=clean_env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines, signalled, starts = [], False, 0
    for line in proc.stdout:
        lines.append(line.rstrip())
        if ' start matrix:' in line:
            starts += 1
            if starts == 2 and not signalled:
                proc.send_signal(signal.SIGTERM)
                signalled = True
    proc.wait(timeout=600)
    if not signalled:
        raise AssertionError('the matrix stage finished before the drill could signal: ' + ' | '.join(lines[-5:]))
    stop = next((i for i, l in enumerate(lines) if 'no new tasks' in l), None)
    later = [l for l in lines[stop+1:] if ' start ' in l] if stop is not None else ['(no stop line)']
    if stop is None or later or proc.returncode != 75:
        raise AssertionError(f'rc={proc.returncode} started after stop: {later} tail: {lines[-4:]}')
    return dict(rc=proc.returncode, matrix_tasks_started=starts, stop_line=lines[stop])


def busy_drill(campaign_root, campaign, cutoff):
    from ht3d_stage import Layout, target_lock
    layout = Layout(campaign_root, cutoff)
    with target_lock(campaign_root, campaign, layout.store):
        proc = subprocess.run(PY + [str(HERE/'ht3d_stage.py'), 'task', 'finalize', 'all',
                                    '--campaign', str(campaign_root), '--cutoff', str(cutoff)],
                              env=clean_env(), capture_output=True, text=True, timeout=600)
    if proc.returncode != 75:
        raise AssertionError(f'expected exit 75 while the target is locked, got {proc.returncode}: '
                             f'{proc.stdout[-400:]} {proc.stderr[-400:]}')
    return dict(rc=proc.returncode)


def sweep_drill(campaign_root, cutoff):
    from ht3d_stage import Layout
    layout = Layout(campaign_root, cutoff)
    stale = layout.image(3).parent/(layout.image(3).name + '.partial-drill')
    stale.mkdir()
    (stale/'junk.npy').write_bytes(b'0')
    proc = subprocess.run(PY + [str(HERE/'ht3d_stage.py'), 'task', 'images', '3',
                                '--campaign', str(campaign_root), '--cutoff', str(cutoff)],
                          env=clean_env(), capture_output=True, text=True, timeout=600)
    if proc.returncode != 0 or stale.exists() or 'verified-existing' not in proc.stdout:
        raise AssertionError(f'rc={proc.returncode} stale_exists={stale.exists()} {proc.stdout[-400:]}')
    return dict(rc=proc.returncode)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--work', required=True, type=Path)
    a = p.parse_args()
    if a.out.exists() and any(a.out.iterdir()):
        sys.exit(f'{a.out} exists and is not empty')
    r = Receipt(a.out, a.work)
    native = Path(os.environ['HT3D_NATIVE_CACHE'])
    work = a.work
    reports = a.out/'reports'      # JSON reports stay on the shared file system
    reports.mkdir()
    threads = min(4, len(os.sched_getaffinity(0)))
    started = time.time()

    r.check('environment', environment)
    r.check('filesystems', filesystems)
    r.check('node', node_facts, gate=False)
    r.check('mpi_identity_coverage', mpi_identity_coverage)
    r.run('test_native', PY + [ROOT/'tests/check_native_backend.py', '--cache-dir', native,
                               '--output', reports/'native.json'])
    r.run('test_stationary', PY + [ROOT/'tests/check_stationary_independent.py', '--cache-dir', native,
                                   '--output', reports/'stationary.json'])
    r.run('test_solver', PY + [ROOT/'tests/check_optimized_solver.py', '--backend', 'native',
                               '--native-cache', native, '--output', reports/'solver.json'])
    r.run('test_local_bands', PY + [ROOT/'tests/check_local_bands.py', '--native-cache', native,
                                    '--output', reports/'local_bands.json'])
    r.run('test_vertex_store', PY + [ROOT/'tests/check_vertex_store.py'])

    # MPI launcher: the first site candidate that yields a genuine 2-rank world.
    launcher = None
    hello = ('from mpi4py import MPI; c = MPI.COMM_WORLD; '
             'print("WORLD", c.Get_rank(), c.Get_size(), MPI.Get_processor_name(), flush=True)')
    tried = []
    import launch
    for candidate in os.environ.get('HT3D_MPI_LAUNCHERS', '').split(';'):
        if not candidate.strip():
            continue
        command = launch.prefix(candidate, nodes=1, per_node=2, cpus=1, bind=False) + \
            [sys.executable, '-E', '-c', hello]
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=300, env=clean_env())
        except subprocess.TimeoutExpired:
            tried.append(dict(launcher=candidate, rc=124, worlds=[], stderr='timeout'))
            continue
        worlds = sorted(l.split()[1:3] for l in proc.stdout.splitlines() if l.startswith('WORLD'))
        tried.append(dict(launcher=candidate, rc=proc.returncode, worlds=worlds, stderr=proc.stderr[-300:]))
        if proc.returncode == 0 and worlds == [['0', '2'], ['1', '2']]:
            launcher = candidate
            break
    r.stages.append(dict(stage='mpi_launcher', rc=0 if launcher else 1, gate=True,
                         facts=dict(chosen=launcher, tried=tried)))
    print(json.dumps(dict(stage='mpi_launcher', chosen=launcher)), flush=True)
    wrapper = work/'mpiexec.sh'
    if launcher:
        # tests/check_hpc_driver.py and the stages below call "<wrapper> -n N command ...".
        extra = '--kill-on-bad-exit=1 -c 1' if launcher.startswith('srun') else '--bind-to none'
        wrapper.write_text('#!/bin/bash\nexec ' + launcher + ' ' + extra + ' "$@"\n')
        wrapper.chmod(0o755)
        for n in (2, 4):
            r.run(f'test_mpi{n}', [wrapper, '-n', n, sys.executable, '-E', '-m', 'mpi4py',
                                   ROOT/'tests/check_mpi_backend.py', '--native-cache', native,
                                   '--output', reports/f'mpi{n}.json'])
    fixture = ROOT/'fixtures'/'vertices_L4'
    driver = [ROOT/'tests/check_hpc_driver.py', '--store', fixture, '--native-cache', native,
              '--work', work/'driver', '--output', reports/'driver.json']
    r.run('test_driver', PY + driver + (['--mpiexec', wrapper] if launcher else []))
    for scheme in ('raw', 'consistent'):
        r.run(f'fixture_x87_{scheme}', PY + [ROOT/'code/ht3d_coefficients.py', 'solve', '--store', fixture,
                                             '--cutoff', 4, '--scheme', scheme, '--threads', threads,
                                             '--native-cache', native, '--output', reports/f'fixture_{scheme}.json',
                                             '--compare-reference', ROOT/'results/reference_coefficients_L14.json',
                                             '--tolerance', '1e-16', '--lock-dir', work/'locks'])

    # Production path on the data file system.
    job = os.environ.get('SLURM_JOB_ID', 'nojob')
    camp_root = a.out/'campaign'
    campaign = make_campaign(camp_root, f'validation_{job}')
    stage = PY + [HERE/'ht3d_stage.py', 'run', '--campaign', camp_root, '--threads', threads]
    r.run('pipeline_L14', stage + ['--cutoff', 14, '--lanes', threads,
                                   '--stages', 'prepare,images,matrix,finalize,verify,gate'])
    r.run('pipeline_L4', stage + ['--cutoff', 4, '--lanes', threads,
                                  '--stages', 'prepare,images,matrix,finalize,verify,gate'])
    r.check('fixture_bitwise_L4', lambda: fixture_bitwise(camp_root/'stores/L4', fixture), gate=False)
    store14 = camp_root/'stores'/'L14'
    r.run('grid_L14_run', PY + [ROOT/'tests/check_saved_coefficients.py', '--store', store14,
                                '--threads', threads, '--strategies', 'stationary', 'recurrence',
                                '--output', reports/'grid.json'], env=clean_env(OMP_NUM_THREADS=threads))
    r.check('grid_L14', lambda: grid_facts(reports/'grid.json'))
    r.check('mpi_validated_store', lambda: mpi_store_check(store14, camp_root/'gates'/'L14'))
    if launcher:
        for scheme in ('raw', 'consistent'):
            out = reports/f'mpi_L14_{scheme}.json'
            r.run(f'mpi_L14_{scheme}_run', [wrapper, '-n', 2, sys.executable, '-E', '-m', 'mpi4py',
                                            ROOT/'code/ht3d_coefficients.py', 'solve', '--mpi', '--store', store14,
                                            '--cutoff', 14, '--scheme', scheme, '--threads', 1,
                                            '--native-cache', native, '--output', out,
                                            '--compare-reference', ROOT/'results/reference_coefficients_L14.json',
                                            '--trust-staged-arrays', '--lock-dir', work/'locks'])
            r.check(f'mpi_L14_{scheme}', lambda s=scheme, o=out: compare_results(
                o, camp_root/'gates'/'L14'/f'{s}_c14.json', MPI_LIMIT))
        r.run('drill_srun_without_mpi', [wrapper, '-n', 2, sys.executable, '-E',
                                         ROOT/'code/ht3d_coefficients.py', 'solve', '--store', fixture,
                                         '--cutoff', 4, '--native-cache', native,
                                         '--output', work/'unmarked.json', '--lock-dir', work/'locks'],
              expect_fail='add --mpi')
    r.check('drill_busy_target', lambda: busy_drill(camp_root, campaign, 14))
    r.check('drill_sweep_partials', lambda: sweep_drill(camp_root, 14))
    r.check('drill_sigterm_prepare', lambda: sigterm_drill(camp_root, 16))
    r.check('drill_runner_stop', lambda: runner_stop_drill(camp_root, 12))

    from ht3d_stage import environment_identity
    env_identity, env_fp = environment_identity()
    value_fp = None
    if (store14/'manifest.json').exists():
        from ht3d_stage import store_value_fingerprint
        value_fp = store_value_fingerprint(store14)
    gates = [s for s in r.stages if s.get('gate', True)]
    passed = bool(gates) and all(s['rc'] == 0 for s in gates) and launcher is not None
    from ht3d_coefficients import node_provenance
    node = node_provenance()
    receipt = dict(format='ht3d-receipt-v1', passed=passed, site=os.environ.get('HT3D_SITE'),
                   release=dict(git_sha=os.environ.get('HT3D_GIT_SHA'),
                                fingerprint=os.environ.get('HT3D_RELEASE_FINGERPRINT'),
                                tar=os.environ.get('HT3D_RELEASE_TAR'),
                                tar_sha256=os.environ.get('HT3D_RELEASE_SHA256')),
                   cpu_class={k: node.get(k) for k in ('vendor_id', 'model name')},
                   partition=os.environ.get('SLURM_JOB_PARTITION'), job=job, host=socket.gethostname(),
                   mpi_launcher=launcher, venv=os.environ.get('HT3D_VENV'),
                   store_L14_manifest_sha256=hashlib.sha256((store14/'manifest.json').read_bytes()).hexdigest()
                   if (store14/'manifest.json').exists() else None,
                   store_L14_value_fingerprint=value_fp,
                   environment=dict(fingerprint=env_fp, identity=env_identity),
                   lock_root=str(Path(os.environ['HT3D_LOCK_ROOT']).resolve()),
                   seconds=round(time.time()-started, 1), stages=r.stages,
                   failed=[s['stage'] for s in gates if s['rc'] != 0])
    (a.out/'receipt.json').write_text(json.dumps(receipt, indent=1, default=str) + '\n')
    shutil.rmtree(camp_root/'prepared', ignore_errors=True)   # keep stores/gates/records only
    print(json.dumps(dict(passed=passed, failed=receipt['failed'], receipt=str(a.out/'receipt.json'))))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
