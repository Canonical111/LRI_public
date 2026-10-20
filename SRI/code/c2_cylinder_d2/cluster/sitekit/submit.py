#!/usr/bin/env python3
"""Check the production plan against a site profile and submit it with Slurm.

Site-independent driver; use it through the site wrappers, which add --site:

  PY=<site environment>/bin/python
  $PY cluster/<site>/submit.py --check                 # plan + profile checks (works anywhere)
  $PY cluster/<site>/submit.py --stage P1              # dry run: checks + exact sbatch commands
  $PY cluster/<site>/submit.py --stage P1 --submit     # submit
  $PY cluster/<site>/submit.py --probe [--probe-aux] --submit   # node probe

<site> is expanse or symmetry; the profile is cluster/<site>/profile.json (paths,
partitions, limits, billing, per-N resource sizing). The plan
(cluster/production_plan.json by default) carries only the physics rows and the
science rules, so both sites run identical rows and produce records of the same
format under outputs/<plan name>/<task name>/.

Run from a verified code copy of the package tarball on the site's login node
(make_tarball.sh --upload puts one in ~/lri_c2/pkgs/<name>/). For every selected
row it submits, unless already done:
  * one grid job per distinct coefficient grid (skipped when the grid is
    published or a grid job with the same name is already queued);
  * row jobs depending afterok on the grid job (cancelled if it fails): a
    throttled array of one-row jobs when the profile has rows_per_job = 1
    (Expanse), otherwise whole-node jobs packing rows_per_job rows, one per CPU
    package (symmetry).
Published rows are left out. Nothing is submitted without --submit.
--grid-resources/--task-resources override profile values (key=value,...);
--resources-profile smoke uses the profile's "smoke" sizing for tiny test plans.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
PKG = HERE.parents[1]
sys.path.insert(0, str(PKG / 'cluster'))
sys.path.insert(0, str(HERE))
import run_task                                                   # noqa: E402
from resource_estimate import estimate                            # noqa: E402
from jobtools import grid_dir_name, grid_workers_cap, sources_digest, MAX_THREADS_PER_PROCESS   # noqa: E402
import manifests                                                  # noqa: E402

DEFAULT_PLAN = PKG / 'cluster' / 'production_plan.json'
# Every LRI_* variable a job script reads. Each submission sets all of them
# explicitly (empty when unused) and the sbatch process gets no other LRI_*
# variable, so nothing inherited from the login shell can steer a job.
RESERVED_EXPORTS = (
    'LRI_SITE', 'LRI_PKG_TAR', 'LRI_PKG_SHA256', 'LRI_PLAN_SHA256', 'LRI_SOURCES_SHA256', 'LRI_ROOT',
    'LRI_LUSTRE_ROOT', 'LRI_ENV', 'LRI_NODE_SCRATCH_BASE', 'LRI_CLEAN_STAGE', 'LRI_STRIPE', 'LRI_MODULES',
    'LRI_N', 'LRI_OVERSAMPLE', 'LRI_RADIUS_COST', 'LRI_GRID_WORKERS', 'LRI_PIN', 'LRI_PLAN', 'LRI_ROWS',
    'LRI_ROW_MODE', 'LRI_TASK_INDEX', 'LRI_WORKERS', 'LRI_FFT_WORKERS', 'LRI_TAIL_CUTOFF', 'LRI_PROBE_AUX',
    'LRI_PROBE_LAM', 'LRI_PROBE_ORDER', 'LRI_PROBE_MIXED', 'LRI_PROBE_TAIL', 'LRI_VERIFY_PUBLISH',
    'LRI_ALLOW_SCRIPT_MISMATCH')
COMMENT_TAG = 'lri1'          # --comment format version: lri1;g=<grid token> or lri1;t=<token>+<token>...
PROFILE_KEYS = {'partition', 'cpus', 'mem_gb', 'time', 'workers', 'pin', 'rows_per_job', 'max_concurrent',
                'projected_hours', 'basis', 'vendor_reason'}
INT_KEYS = {'cpus', 'mem_gb', 'rows_per_job', 'max_concurrent'}


def load_profile(site: str) -> dict:
    path = PKG / 'cluster' / site / 'profile.json'
    if not path.is_file():
        raise ValueError(f'no site profile {path}')
    prof = json.loads(path.read_text())
    if prof.get('site') != site:
        raise ValueError(f'{path} describes site {prof.get("site")!r}, not {site!r}')
    return prof


def expand(template: str) -> str:
    return template.format(user=os.environ.get('USER', 'user'), home=os.environ.get('HOME', '~'))


# ---------------------------------------------------------------- memory models
# Approximate peak-memory models used only for the sanity checks below. They
# follow the array shapes allocated by the unchanged solver and were checked
# against the Expanse pilot (cluster/expanse/profile.json -> calibration).

def fft_length(cutoff: int, oversample: int) -> int:
    return estimate(cutoff, oversample)['M']


def grid_memory_bytes(cutoff: int, oversample: int, workers: int) -> int:
    """Anonymous memory of parallel_coefficients: ~21 complex (M, M) slice arrays
    per worker at its peak plus ~4 in the parent (phase tables, index array).
    Pilot N=512, 16 workers: model 23.0 GB, measured cgroup anon peak 22.2 GB.
    Page cache of the memory-mapped temporary array comes on top; it is
    reclaimable and needs headroom in the request, not a hard reservation."""
    m = fft_length(cutoff, oversample)
    return int((21 * workers + 4) * 16 * m * m)


def task_memory_bytes(cutoff: int, mixed_cutoff: int, tail_cutoff: int) -> int:
    """Largest of the three sequential stages of one lambda value:
    raw cube sums (lowmemory.raw_sequence: two (3, K, K, K) float arrays plus up
    to three grid fields of page cache, plus two (N, N, N) work arrays),
    mixed sums (~6 float (K_mix, K_mix) matrices) and the leading tail (~8).
    Measured: mixed 16384 10.9 GB, tail 8192 3.4 GB (probe); pilot N=512 peak
    10.9 GB (mixed stage) against a model of 12.9 GB."""
    k = cutoff + 1
    raw = 8 * (6 * k**3 + 3 * k**3 + 2 * cutoff**3)
    mixed = 6 * 8 * (mixed_cutoff + 1) ** 2
    tail = 8 * 8 * (tail_cutoff + 1) ** 2 if mixed_cutoff >= 4096 else 0   # sidecar only (reproduce.py)
    return int(max(raw, mixed, tail))


def hours(text: str) -> float:
    m = re.fullmatch(r'(?:(\d+)-)?(\d+):(\d\d):(\d\d)', text)
    if not m:
        raise ValueError(f'time must be [D-]HH:MM:SS, got {text!r}')
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return 24 * d + h + mi / 60 + s / 3600


def parse_resources(spec: str | None) -> dict:
    out: dict = {}
    for item in filter(None, (spec or '').split(',')):
        key, _, value = item.partition('=')
        if key not in PROFILE_KEYS:
            raise ValueError(f'unknown resource key {key!r}')
        if key == 'vendor_reason':
            raise ValueError('vendor_reason is documentation for profile.json, not an override')
        if key in INT_KEYS or (key == 'workers' and value != 'auto'):
            if not re.fullmatch(r'[1-9][0-9]*', value):
                raise ValueError(f'{key} must be a positive integer, got {value!r}')
            out[key] = int(value)
        elif key == 'projected_hours':
            out[key] = float(value)
        else:
            out[key] = value
    return out


# ---------------------------------------------------------------- checks

def select_rows(jobs: list[dict], stages: list[str] | None, tasks: str | None) -> list[int]:
    rows = list(range(len(jobs)))
    if tasks:
        wanted = set()
        for part in tasks.split(','):
            lo, _, hi = part.partition('-')
            wanted.update(range(int(lo), int(hi or lo) + 1))
        bad = wanted - set(rows)
        if bad:
            raise ValueError(f'task indices outside the plan: {sorted(bad)}')
        rows = sorted(wanted)
    if stages:
        rows = [i for i in rows if jobs[i].get('stage') in stages]
    if not rows:
        raise ValueError('no plan rows selected')
    return rows


def profile_for(site: dict, job: dict | None, kind: str, override: dict, named: str | None = None) -> dict:
    key = named or str(job['cutoff'])
    prof = dict(site.get('profiles', {}).get(key, {}).get(kind, {}))
    prof.update(override)
    missing = {'partition', 'mem_gb', 'time'} - set(prof)
    if missing:
        raise ValueError(f"no complete {kind} profile for {key} at site {site['site']} (missing {sorted(missing)}); "
                         f'add it to cluster/{site["site"]}/profile.json or pass --{kind}-resources')
    return prof


def partitions_of(site: dict, prof: dict, problems: list[str], label: str) -> list[dict]:
    out = []
    for name in prof['partition'].split(','):
        if name in site.get('forbidden_partitions', []):
            problems.append(f'{label}: partition {name} is not allowed at {site["site"]}')
        elif name not in site['partitions']:
            problems.append(f'{label}: unknown partition {name}')
        else:
            out.append(dict(site['partitions'][name], name=name))
    if out and len({p.get('whole_node', False) for p in out}) > 1:
        problems.append(f'{label}: mixes whole-node and shared partitions')
    return out


def check_limits(site: dict, prof: dict, label: str, problems: list[str]) -> tuple[list[dict], bool, int | None]:
    """Partition, memory, wall-time and CPU limits common to every job kind
    (grid, task and probe). Returns (partitions, whole_node, cpus)."""
    bad = [k for k in sorted(INT_KEYS | {'workers'}) if k in prof and not (
        (k == 'workers' and prof[k] == 'auto') or (isinstance(prof[k], int) and not isinstance(prof[k], bool) and prof[k] > 0))]
    if bad:     # rows_per_job, workers, cpus, mem_gb, max_concurrent (R2-005): nothing else is checked then
        problems += [f'{label}: {k} must be a positive integer (got {prof[k]!r})' for k in bad]
        return [], False, None
    parts = partitions_of(site, prof, problems, label)
    if not parts:
        return [], False, None
    whole = parts[0].get('whole_node', False)
    mem = prof.get('mem_gb')
    if not isinstance(mem, int) or mem < 1:
        problems.append(f'{label}: mem_gb must be a positive integer')
    elif mem > min(p['max_mem_gb'] for p in parts):
        problems.append(f'{label}: memory above the limit of {min(p["max_mem_gb"] for p in parts)} GB')
    try:
        if hours(prof['time']) > min(p['max_hours'] for p in parts):
            problems.append(f'{label}: wall time above {min(p["max_hours"] for p in parts)} h')
    except ValueError as exc:
        problems.append(f'{label}: {exc}')
    if whole:
        cpus = max(p['packages'] * p['cores_per_package'] for p in parts)
    else:
        cpus = prof.get('cpus')
        if not isinstance(cpus, int) or not 1 <= cpus <= min(p['max_cpus'] for p in parts):
            problems.append(f'{label}: cpus missing or outside the partition limit')
            cpus = 1
    return parts, whole, cpus


def billing_rate(part: dict, cpus: int, mem: float) -> tuple[float, str]:
    b = part.get('billing', {})
    if 'per_node' in b:
        return float(b['per_node']), b.get('unit', 'SU')
    return max(b.get('per_cpu', 0) * cpus, b.get('per_gb', 0) * mem), b.get('unit', 'SU')


def check_profile(site: dict, kind: str, job: dict, prof: dict, problems: list[str], notes: list[str]) -> dict:
    label = f"{kind} N={job['cutoff']} ({prof['partition']}, {prof.get('cpus', 'node')} cpus, {prof['mem_gb']} GB, {prof['time']})"
    parts, whole, cpus = check_limits(site, prof, label, problems)
    if not parts:
        return {}
    mem = prof['mem_gb'] if isinstance(prof['mem_gb'], int) else 1
    if whole:
        package_min = min(p['cores_per_package'] for p in parts)
        package_max = max(p['cores_per_package'] for p in parts)
    else:
        package_min = package_max = min(cpus, MAX_THREADS_PER_PROCESS)
    o = job['oversample']
    pin = prof.get('pin', 'none')
    rows = prof.get('rows_per_job', 1) if kind == 'task' else 1
    if pin not in ('none', 'package'):
        problems.append(f'{label}: pin must be none or package')
    if pin == 'package' and not whole:
        problems.append(f'{label}: pin=package needs whole-node partitions')
    if kind == 'grid':
        workers = prof.get('workers', 'auto' if whole else cpus)
        if workers == 'auto':
            cap = grid_workers_cap(job['cutoff'], o, mem * 1e9)
            workers = min(package_max, cap)
            if workers < 1:
                problems.append(f'{label}: memory request too small for even one grid worker')
                workers = 1
        elif workers > package_min:
            problems.append(f'{label}: {workers} grid workers exceed one CPU package ({package_min} cores)')
        if not whole and workers > cpus:
            problems.append(f'{label}: workers exceed cpus')
        model = grid_memory_bytes(job['cutoff'], o, workers)
        e = estimate(job['cutoff'], o)
        scratch = e['coefficient_bytes'] + e['temporary_bytes']
        threads = workers
    else:
        if rows > 1 and pin != 'package':
            problems.append(f'{label}: rows_per_job > 1 needs pin=package')
        if whole and rows > min(p.get('packages', 1) for p in parts):
            problems.append(f'{label}: more rows per job than CPU packages')
        one = task_memory_bytes(job['cutoff'], job['mixed_cutoff'], job.get('tail_cutoff', run_task.DEFAULT_TAIL_CUTOFF))
        model = rows * one
        if rows > 1:
            per_package = min(p['mem_per_package_gb'] for p in parts) * 1e9
            if one > per_package:
                problems.append(f'{label}: one row ({one / 1e9:.0f} GB model) does not fit one package\'s memory under --membind')
        scratch = estimate(job['cutoff'], o)['coefficient_bytes']
        threads = package_max if whole else cpus
    if threads > MAX_THREADS_PER_PROCESS:
        problems.append(f'{label}: {threads} threads/workers in one process exceed one 64-core package')
    if model > mem * 1e9:
        problems.append(f'{label}: memory model {model / 1e9:.0f} GB exceeds the request')
    elif model > 0.8 * mem * 1e9:
        notes.append(f'{label}: memory model {model / 1e9:.0f} GB is above 80% of the request')
    scratch_need = scratch * 1.1 + 2e9
    tmp = min(p['tmp_gb'] for p in parts)
    if scratch_need > tmp * 1e9 * (1.0 if whole else 0.9):
        problems.append(f'{label}: node-local scratch need {scratch_need / 1e9:.0f} GB too large for this partition')
    elif not whole and scratch_need > 0.25 * tmp * 1e9:
        notes.append(f'{label}: needs {scratch_need / 1e9:.0f} GB of node-local NVMe that co-located jobs share; '
                     'the job fails early (exit 75) if the node has less free')
    rates = [billing_rate(p, cpus, mem) for p in parts]
    rate, unit = max(rates)
    try:
        wall = hours(prof['time'])
    except ValueError:
        wall = 0.0
    return {'label': label, 'rate': rate, 'unit': unit, 'cost_at_wall_limit': rate * wall,
            'cost_projected': rate * prof['projected_hours'] if 'projected_hours' in prof else None,
            'memory_model_GB': round(model / 1e9, 1), 'scratch_need_GB': round(scratch_need / 1e9, 1),
            'workers_or_threads': threads, 'rows_per_job': rows}


def check_science(plan: dict, rows: list[int], jobs: list[dict], problems: list[str]) -> None:
    rules = plan.get('science_rules', {})
    lam_n = {int(k): v for k, v in rules.get('lambda_N_minimum', {}).items()}
    min_mixed = rules.get('minimum_mixed_cutoff')
    for i in rows:
        job = jobs[i]
        for lam in job['lambda']:
            need = lam_n.get(job['order'])
            if need is not None and lam * job['cutoff'] < need - 1e-9:
                problems.append(f"row {i} {job['id']}: lambda*N = {lam * job['cutoff']:g} < {need} for order {job['order']}")
        if min_mixed and job['mixed_cutoff'] < min_mixed:
            problems.append(f"row {i} {job['id']}: mixed_cutoff {job['mixed_cutoff']} < {min_mixed}")


# ---------------------------------------------------------------- Slurm helpers

def slurm_env(site: dict) -> dict:
    """Environment for squeue/sbatch: Slurm on PATH, no inherited LRI_* variables
    (sbatch --export=ALL would otherwise pass them to the jobs)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith('LRI_')}
    path = site['scheduler'].get('slurm_path')
    if path:        # appended: Slurm is not on symmetry's PATH; an earlier squeue (tests) wins
        env['PATH'] = env.get('PATH', '') + os.pathsep + path
    return env


def slurm(cmd: list[str], env: dict) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, env=env).stdout


def queued_jobs(env: dict) -> list[dict]:
    """This user's pending/running jobs (one entry per array element) with their
    --comment. Raises on failure: an unreadable queue is UNKNOWN, never empty."""
    out = slurm(['squeue', '-h', '-r', '-u', os.environ.get('USER', ''), '-t', 'PENDING,RUNNING',
                 '-o', '%i|%j|%T|%k'], env)
    jobs = []
    for line in out.splitlines():
        if not line.strip():
            continue
        jid, name, state, comment = (line.split('|', 3) + ['', '', ''])[:4]
        base, _, element = jid.strip().partition('_')
        jobs.append({'id': jid.strip(), 'base_id': base, 'element': element if element.isdigit() else None,
                     'name': name.strip(), 'state': state.strip(), 'comment': comment.strip()})
    return jobs


def token(*parts: str) -> str:
    return hashlib.sha256('|'.join(parts).encode()).hexdigest()[:16]


def comment_tokens(comment: str, element: str | None = None) -> dict[str, set[str]]:
    """Tokens of a job comment as {'g': grid tokens, 't': task tokens}.
      lri1;g=<tok>                      grid job
      lri1;t=<tok>+<tok>...             packed row job: every token belongs to the job
      lri1;a=<row>:<tok>.<tok>+...      row array: tokens per array index (R2-007);
                                        an element (squeue -r id <job>_<row>) holds only
                                        its own row's tokens, an unexpanded record all."""
    out: dict[str, set[str]] = {'g': set(), 't': set()}
    fields = comment.split(';')
    if not fields or fields[0] != COMMENT_TAG:
        return out
    for field in fields[1:]:
        key, _, value = field.partition('=')
        if key in out:
            out[key].update(x for x in value.split('+') if x)
        elif key == 'a':
            for entry in filter(None, value.split('+')):
                index, _, toks = entry.partition(':')
                if element is None or index == element:
                    out['t'].update(x for x in toks.split('.') if x)
    return out


def array_comment(rows: list[int], toks: dict[int, tuple[str, str]]) -> str:
    return f"{COMMENT_TAG};a=" + '+'.join(f"{i}:{'.'.join(toks[i])}" for i in rows)


def grid_token(destination: Path) -> str:
    """Identity of a grid job: its resolved destination (root + source-tagged grid key)."""
    return token('grid', str(destination))


def task_tokens(destination: Path, root: Path, plan_sha: str, task_name: str) -> tuple[str, str]:
    """Identities of one plan row: its output directory, and (root, plan sha, task name)."""
    return token('dest', str(destination)), token('task', str(root), plan_sha, task_name)


def sbatch_command(site: dict, prof: dict, name: str, log: str, export: dict, script: Path,
                   array: str | None = None, dependency: str | None = None, comment: str | None = None) -> list[str]:
    parts = [site['partitions'][p] for p in prof['partition'].split(',')]
    cmd = ['sbatch', '--parsable']
    if site['scheduler'].get('account'):
        cmd += ['-A', site['scheduler']['account']]
    cmd += ['-p', prof['partition'], '--nodes=1']
    if all(p.get('whole_node') for p in parts):
        cmd += ['--exclusive']                       # whole node; no --ntasks-per-node (Expanse quirk)
    else:
        cmd += ['--ntasks-per-node=1', f"--cpus-per-task={prof['cpus']}"]
    excludes = sorted({p['exclude'] for p in parts if p.get('exclude')})
    if excludes:
        cmd += ['--exclude=' + ','.join(excludes)]
    cmd += [f"--mem={prof['mem_gb']}G", '-t', prof['time'], '-J', name, '-o', log]
    if array:
        cmd += [f'--array={array}']
    if dependency:
        cmd += [f'--dependency=afterok:{dependency}', '--kill-on-invalid-dep=yes']
    if comment:
        cmd += [f'--comment={comment}']
    unknown = set(export) - set(RESERVED_EXPORTS)
    if unknown:
        raise ValueError(f'export of unreserved variables {sorted(unknown)}')
    values = {k: '' for k in RESERVED_EXPORTS}          # clear everything a job reads ...
    values.update({k: str(v) for k, v in export.items()})   # ... then set what this job needs
    bad = [k for k, v in values.items() if ',' in v]
    if bad:
        raise ValueError(f'commas are not allowed in exported values: {bad}')
    cmd += ['--export=ALL,' + ','.join(f'{k}={v}' for k, v in values.items()), str(script)]
    return cmd


def site_exports(site: dict, pkg_tar: Path, root: Path, env_dir: Path, binding: dict | None = None) -> dict:
    paths = site['paths']
    out = {'LRI_SITE': site['site'], 'LRI_PKG_TAR': str(pkg_tar), 'LRI_ROOT': str(root), 'LRI_ENV': str(env_dir),
           'LRI_NODE_SCRATCH_BASE': expand(paths['node_scratch_base']),
           'LRI_CLEAN_STAGE': int(paths.get('clean_node_scratch', False)),
           'LRI_STRIPE': paths.get('stripe_count', 0), 'LRI_MODULES': ':'.join(site.get('modules', []))}
    out.update(binding or {})
    return out


def verify_code_copy(pkg_tar: Path, plan_rel: Path) -> tuple[str, list[str]]:
    """Bind this submission to the uploaded tarball: the tarball matches its .sha256,
    its STAGE_MANIFEST/STAGE_INFO are byte-identical to this code copy's, every
    file of this code copy matches the manifest, no unlisted file was added
    (bytecode caches excepted) and the plan is part of the tarball. Returns the
    tarball's sha256 and the problems found."""
    problems = []
    try:
        expected = Path(str(pkg_tar) + '.sha256').read_text().split()[0]
    except (OSError, IndexError) as exc:
        return '', [f'cannot read {pkg_tar}.sha256: {exc}']
    actual = manifests.sha256(pkg_tar)
    if actual != expected:
        problems.append(f'{pkg_tar} does not match its .sha256')
    try:
        with tarfile.open(pkg_tar) as tar:
            members = {m: tar.extractfile(f'lri_c2/{m}').read() for m in ('STAGE_MANIFEST.sha256', 'STAGE_INFO.json')}
    except (OSError, KeyError, tarfile.TarError, AttributeError) as exc:
        return actual, problems + [f'cannot read the stage manifest in {pkg_tar}: {exc}']
    listed = {}
    for name, content in members.items():
        local = PKG / name
        if not local.is_file() or local.read_bytes() != content:
            problems.append(f'this code copy is not the tarball\'s ({name} differs); submit from the copy unpacked by make_tarball.sh --upload')
    for line in members['STAGE_MANIFEST.sha256'].decode().splitlines():
        digest, _, rel = line.partition('  ')
        listed[rel] = digest
    for rel, digest in listed.items():
        f = PKG / rel
        if not f.is_file() or manifests.sha256(f) != digest:
            problems.append(f'code copy differs from the tarball: {rel}')
    for f in PKG.rglob('*'):
        rel = f.relative_to(PKG).as_posix()
        if f.is_file() and rel not in listed and rel != 'STAGE_MANIFEST.sha256' \
                and '__pycache__' not in f.parts and not rel.endswith('.pyc'):
            problems.append(f'file not in the tarball: {rel}')
    if plan_rel.as_posix() not in listed:
        problems.append(f'plan {plan_rel} is not in the tarball')
    return actual, problems


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--site', required=True, help='expanse or symmetry (the wrappers pass it).')
    p.add_argument('--plan', type=Path, default=DEFAULT_PLAN)
    p.add_argument('--stage', nargs='+', help='Plan stages to select (e.g. PILOT, P1, P2).')
    p.add_argument('--tasks', help='Plan row indices, e.g. "1-3" or "4,5".')
    p.add_argument('--root', '--lustre-root', dest='root',
                   help='Campaign root for grids/, outputs/, receipts/, logs/ (default: the profile).')
    p.add_argument('--pkg-root', help='Root whose pkg/ holds the uploaded tarballs (default: the profile root).')
    p.add_argument('--env', help='Python environment (default: the profile).')
    p.add_argument('--grid-resources', help='Override, e.g. partition=shared,cpus=2,mem_gb=4,time=00:15:00,workers=2')
    p.add_argument('--task-resources', help='Override, e.g. partition=shared,cpus=2,mem_gb=4,time=00:20:00')
    p.add_argument('--resources-profile', help='Use this named profile entry (e.g. smoke) for every row.')
    p.add_argument('--max-concurrent', type=int, help='Throttle for task arrays (default: profile value).')
    p.add_argument('--probe', action='store_true', help='Submit the node probe instead of plan rows.')
    p.add_argument('--probe-aux', action='store_true', help='With --probe: also run the auxiliary-cutoff benchmark.')
    p.add_argument('--check', action='store_true', help='Only validate the plan and profiles.')
    p.add_argument('--submit', action='store_true', help='Actually submit (default: dry run).')
    p.add_argument('--verify-grid-arrays', action='store_true',
                   help='Also hash published grid arrays here (up to 52 GB; by default the login node checks the '
                        'manifest, small files and sizes, and every consumer job hashes the array on its node).')
    a = p.parse_args(argv)

    try:
        site = load_profile(a.site)
    except (ValueError, OSError) as exc:
        p.exit(64, f'ERROR: {exc}\n')
    plan_path = a.plan.resolve()
    try:
        plan_rel = plan_path.relative_to(PKG)
    except ValueError:
        p.exit(64, f'ERROR: the plan must be inside this package ({PKG}) so that jobs find it in the tarball\n')
    problems: list[str] = []
    notes: list[str] = []
    grids: dict[str, dict] = {}
    groups: dict[str, dict] = {}
    costs = []
    try:
        plan, jobs = run_task.load_plan(plan_path)
        overrides = {'grid': parse_resources(a.grid_resources), 'task': parse_resources(a.task_resources)}
        if a.max_concurrent is not None and a.max_concurrent < 1:
            raise ValueError('--max-concurrent must be at least 1')
        if a.probe:
            rows = []
            probe_prof = profile_for(site, None, 'probe', overrides['task'], named='probe')
            check_limits(site, probe_prof, f"probe ({probe_prof['partition']}, {probe_prof['mem_gb']} GB, "
                                           f"{probe_prof['time']})", problems)
        else:
            rows = select_rows(jobs, a.stage, a.tasks)
            check_science(plan, rows, jobs, problems)
        for i in rows:
            job = jobs[i]
            gdir = grid_dir_name(run_task, job['cutoff'], job['oversample'], job['radius_cost'])
            gprof = profile_for(site, job, 'grid', overrides['grid'], a.resources_profile)
            tprof = profile_for(site, job, 'task', overrides['task'], a.resources_profile)
            if gdir not in grids:
                grids[gdir] = {'job': job, 'profile': gprof,
                               'key': run_task.grid_key(job['cutoff'], job['oversample'], job['radius_cost'])}
                grids[gdir]['cost'] = check_profile(site, 'grid', job, gprof, problems, notes)
                costs.append(grids[gdir]['cost'])
            group = groups.setdefault(json.dumps(tprof, sort_keys=True) + gdir,
                                      {'profile': tprof, 'grid': gdir, 'rows': [], 'N': job['cutoff']})
            group['rows'].append(i)
            c = check_profile(site, 'task', job, tprof, problems, notes)
            if c:
                c['label'] = f"row {i} {job['id']}: " + c['label']
            costs.append(c)
            group['cost'] = c
    except (ValueError, KeyError, OSError) as exc:
        p.exit(64, f'ERROR: {exc}\n')

    print(f'SITE {site["site"]}; PLAN {plan_rel} ({plan.get("name", "")}); rows {rows}')
    for c in costs:
        if c:
            proj = f", projected {c['cost_projected']:.1f} {c['unit']}" if c.get('cost_projected') is not None else ''
            per = ' per job' if c['rows_per_job'] > 1 else ''
            print(f"  {c['label']}: {c['rate']:.0f} {c['unit']}/h, <= {c['cost_at_wall_limit']:.0f} {c['unit']}{per} at the wall "
                  f"limit{proj}; {c['workers_or_threads']} workers/threads per process; memory model {c['memory_model_GB']} GB"
                  f"{' for ' + str(c['rows_per_job']) + ' rows' if c['rows_per_job'] > 1 else ''}; "
                  f"node-local scratch {c['scratch_need_GB']} GB")
    # Totals per actual job: one per grid, ceil(rows / rows_per_job) per row group.
    billed = [(1, g['cost']) for g in grids.values() if g.get('cost')] + \
        [(-(-len(g['rows']) // g['cost']['rows_per_job']), g['cost']) for g in groups.values() if g.get('cost')]
    units = {c['unit'] for _, c in billed}
    if len(units) == 1:
        unit = units.pop()
        total = sum(n * c['cost_at_wall_limit'] for n, c in billed)
        proj = sum(n * (c['cost_projected'] or 0) for n, c in billed)
        print(f'  total: {sum(n for n, _ in billed)} jobs, <= {total:.0f} {unit} if every job ran to its wall limit; '
              f'projected about {proj:.1f} {unit}')
    for n in notes:
        print('  NOTE', n)
    for pr in problems:
        print('  PROBLEM', pr)
    if problems:
        p.exit(1, f'ERROR: {len(problems)} plan/profile problem(s); nothing submitted\n')
    if a.check:
        print('CHECK OK')
        return

    # ---------------- submission (login node of the site)
    info_path = PKG / 'STAGE_INFO.json'
    if not info_path.is_file():
        p.exit(64, 'ERROR: run submit.py from a code copy made by make_tarball.sh --upload (STAGE_INFO.json missing)\n')
    info = json.loads(info_path.read_text())
    default_root = expand(site['paths']['persistent_root'])
    root = Path(a.root or default_root).resolve()
    pkg_tar = Path(a.pkg_root or default_root) / 'pkg' / f"{info['name']}.tar"
    if not (pkg_tar.is_file() and Path(str(pkg_tar) + '.sha256').is_file()):
        p.exit(66, f'ERROR: package tarball {pkg_tar} (+ .sha256) not found; run make_tarball.sh --upload\n')
    pkg_sha, bind_problems = verify_code_copy(pkg_tar, plan_rel)
    if bind_problems:
        for x in bind_problems[:20]:
            print('  PROBLEM', x)
        p.exit(65, f'ERROR: this code copy is not bound to {pkg_tar} ({len(bind_problems)} problem(s)); nothing submitted\n')
    env_dir = Path(a.env or expand(site['paths']['env']))
    if not (env_dir / 'bin' / 'python').exists() or not (env_dir / 'lri_env_receipt.json').is_file():
        p.exit(66, f'ERROR: Python environment {env_dir} missing; run cluster/{site["site"]}/setup_env.sh\n')
    if info.get('dirty'):
        print(f"WARNING: {info['name']} was built from uncommitted changes (testing only)")
    plan_name = plan_path.stem
    plan_sha = run_task.sha256(plan_path)
    logs = root / 'logs'
    binding = {'LRI_PKG_SHA256': pkg_sha, 'LRI_PLAN_SHA256': plan_sha, 'LRI_SOURCES_SHA256': sources_digest(run_task)}
    common = site_exports(site, pkg_tar, root, env_dir, binding)
    senv = slurm_env(site)
    prefix = site['scheduler']['job_prefix']
    try:
        queued = queued_jobs(senv)
    except (OSError, subprocess.CalledProcessError) as exc:
        p.exit(75, f'ERROR: squeue failed ({exc}); queue state UNKNOWN, nothing submitted\n')
    queued_tokens = {'g': {}, 't': {}}
    for q in queued:
        for kind, toks in comment_tokens(q['comment'], q['element']).items():
            for t in toks:
                queued_tokens[kind].setdefault(t, q)

    # ---- decide every job first; submit only if nothing is inconsistent.
    # Rows first (R2-008): a grid is considered only if an unfinished row needs it.
    errors: list[str] = []
    row_plan: list[tuple[dict, list[int], dict]] = []
    for g in groups.values():
        todo, toks = [], {}
        for i in g['rows']:
            job = jobs[i]
            info_row = subprocess.run([sys.executable, str(HERE / 'jobtools.py'), 'task-info', '--plan', str(plan_path),
                                       '--index', str(i)], check=True, capture_output=True, text=True).stdout
            task_name = re.search(r'^TASK_NAME=(\S+)$', info_row, re.M).group(1)
            dest = root / 'outputs' / plan_name / task_name
            status, why = manifests.row_status(dest, job)
            if status == 'complete':
                print(f'ROW {i} ({task_name}): published and verified, skipped')
                continue
            if status == 'corrupt':
                errors += [f'published row {dest} is incomplete or corrupt: {x}' for x in why]
                continue
            mine = task_tokens(dest, root, plan_sha, task_name)
            clash = [queued_tokens['t'][t] for t in mine if t in queued_tokens['t']]
            if clash:
                errors.append(f'row {i} ({task_name}) is already queued or running in job {clash[0]["id"]} '
                              f'({clash[0]["name"]}); not submitting a duplicate')
                continue
            legacy = [q for q in queued if not q['comment'].startswith(COMMENT_TAG) and (
                q['name'] == f"{prefix}task_{plan_name}_N{g['N']}" or
                (q['name'].startswith(f"{prefix}rows_{plan_name}_r") and
                 str(i) in q['name'][len(f"{prefix}rows_{plan_name}_r"):].split('-')))]
            if legacy:
                errors.append(f'job {legacy[0]["id"]} ({legacy[0]["name"]}) has no task comment and may run row {i}; '
                              f'wait for it or cancel it')
                continue
            todo.append(i)
            toks[i] = mine
        if todo:
            row_plan.append((g, todo, toks))
    grid_plan: dict[str, dict] = {}
    for gdir in sorted({g['grid'] for g, _, _ in row_plan}):
        g = grids[gdir]
        dest = root / 'grids' / gdir
        status, why = manifests.grid_status(dest, hash_array=a.verify_grid_arrays)
        if status == 'corrupt':
            errors += [f'published grid {dest} is incomplete or corrupt: {x}' for x in why]
            continue
        if status == 'complete':
            grid_plan[gdir] = {'action': 'published'}
            continue
        tok = grid_token(dest)
        legacy = [q for q in queued if q['name'] == f"{prefix}grid_{g['key']}" and not q['comment'].startswith(COMMENT_TAG)]
        if tok in queued_tokens['g']:
            q = queued_tokens['g'][tok]
            grid_plan[gdir] = {'action': 'attach', 'job': q['base_id'], 'state': q['state']}
        elif legacy:
            errors.append(f'job {legacy[0]["id"]} ({legacy[0]["name"]}) has no destination comment, so it may build '
                          f'this grid elsewhere; wait for it or cancel it')
        else:
            grid_plan[gdir] = {'action': 'submit', 'token': tok}
    if errors:
        for x in errors:
            print('  PROBLEM', x)
        p.exit(1, f'ERROR: {len(errors)} problem(s) with published or queued work; nothing submitted\n')
    proposed = [(probe_prof['partition'], 1)] if a.probe else []
    proposed += [(grids[gdir]['profile']['partition'], 1) for gdir, d in grid_plan.items() if d['action'] == 'submit']
    for g, todo, _ in row_plan:
        per_job = g['profile'].get('rows_per_job', 1)
        proposed.append((g['profile']['partition'], len(todo) if per_job == 1 else -(-len(todo) // per_job)))
    if not proposed:
        print('NOTHING TO SUBMIT: every selected row is published and verified')
        return
    compute_guard(site, proposed, senv, p)        # every job, probes included (R2-006)

    if a.submit:
        logs.mkdir(parents=True, exist_ok=True)      # Slurm cannot create the --output directory
    record = {'submitted_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'site': site['site'],
              'plan': str(plan_rel), 'plan_sha256': plan_sha, 'package': info, 'package_tar': str(pkg_tar),
              'package_sha256': pkg_sha, 'sources_sha256': binding['LRI_SOURCES_SHA256'], 'root': str(root),
              'env': str(env_dir), 'rows': rows, 'dry_run': not a.submit, 'jobs': []}

    def submit(cmd: list[str], kind: str, **extra) -> str:
        print(kind.upper(), extra, '\n  ' + ' '.join(shlex.quote(c) for c in cmd))
        jid = slurm(cmd, senv).strip().split(';')[0] if a.submit else 'DRYRUN'
        record['jobs'].append(dict(kind=kind, job_id=jid, command=cmd, **extra))
        return jid

    if a.probe:
        export = dict(common, LRI_PROBE_AUX=int(a.probe_aux))
        submit(sbatch_command(site, probe_prof, f'{prefix}probe', str(logs / '%x_%j.out'), export,
                              HERE / 'probe_job.sbatch'), 'probe')
    grid_job_ids: dict[str, str | None] = {}
    for gdir, decision in grid_plan.items():
        g = grids[gdir]
        if decision['action'] == 'published':
            print(f'GRID {gdir}: published and verified, no job')
            grid_job_ids[gdir] = None
        elif decision['action'] == 'attach':
            grid_job_ids[gdir] = decision['job']
            print(f"GRID {gdir}: job {decision['job']} ({decision['state']}) builds this grid for {root}; "
                  f"row jobs will depend on it")
        else:
            export = dict(common, LRI_N=g['job']['cutoff'], LRI_OVERSAMPLE=g['job']['oversample'],
                          LRI_RADIUS_COST=g['job']['radius_cost'], LRI_GRID_WORKERS=g['profile'].get('workers', 'auto'),
                          LRI_PIN=g['profile'].get('pin', 'none'))
            cmd = sbatch_command(site, g['profile'], f'{prefix}grid_{gdir}', str(logs / '%x_%j.out'), export,
                                 HERE / 'grid_job.sbatch', comment=f"{COMMENT_TAG};g={decision['token']}")
            grid_job_ids[gdir] = submit(cmd, 'grid', grid_dir=gdir)
    for g, todo, toks in row_plan:
        prof = g['profile']
        dep = grid_job_ids.get(g['grid'])
        export = dict(common, LRI_PLAN=str(plan_rel), LRI_PIN=prof.get('pin', 'none'))
        per_job = prof.get('rows_per_job', 1)
        if per_job == 1:
            limit = a.max_concurrent or prof.get('max_concurrent') or len(todo)
            for part in prof['partition'].split(','):
                per_user = site['partitions'][part].get('running_per_user')
                if per_user:
                    limit = min(limit, per_user)
            comment = array_comment(todo, toks)
            cmd = sbatch_command(site, prof, f"{prefix}task_{plan_name}_N{g['N']}", str(logs / '%x_%A_%a.out'),
                                 dict(export, LRI_ROW_MODE='array'), HERE / 'rows_job.sbatch',
                                 array=','.join(map(str, todo)) + f'%{limit}', dependency=dep, comment=comment)
            submit(cmd, 'row_array', rows=todo)
        else:
            for start in range(0, len(todo), per_job):
                chunk = todo[start:start + per_job]
                comment = f"{COMMENT_TAG};t=" + '+'.join(t for i in chunk for t in toks[i])
                cmd = sbatch_command(site, prof, f"{prefix}rows_{plan_name}_r{'-'.join(map(str, chunk))}",
                                     str(logs / '%x_%j.out'),
                                     dict(export, LRI_ROW_MODE='packed', LRI_ROWS=':'.join(map(str, chunk))),
                                     HERE / 'rows_job.sbatch', dependency=dep, comment=comment)
                submit(cmd, 'rows', rows=chunk)
    if not a.submit:
        print('DRY RUN: nothing submitted (add --submit)')
        return
    sub_dir = root / 'submissions'
    sub_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    what = 'probe' if a.probe else '-'.join(a.stage or ['rows'])
    out = sub_dir / f'{stamp}_{plan_name}_{what}.json'
    out.write_text(json.dumps(record, indent=2) + '\n')
    print('SUBMISSION RECORD', out)
    ids = ','.join(j['job_id'] for j in record['jobs'])
    if ids:
        print(f'monitor:  squeue -u $USER -o "%.18i %.9P %.45j %.8T %.10M %.6D %R"\n'
              f'          sacct -j {ids} -o JobID%20,JobName%45,Partition,State,Elapsed,MaxRSS,ExitCode\n'
              f'logs:     {logs}/<job name>_<job id>[_<row>].out and {logs}/<job name>_<job id>_row<row>.log (live)\n'
              f'receipts: {root}/receipts/<job name>_<job id>/receipt.json')


def compute_guard(site: dict, proposed: list[tuple[str, int]], senv: dict, p) -> None:
    """Normal-QOS headroom (Expanse <ACCOUNT> rule): RUNNING + PENDING normal-QOS
    jobs of the whole account plus every proposed job in a normal-QOS partition
    (probes included) must stay at or below cap - keep_free (32 - 10 = 22).
    No override; an unreadable queue is UNKNOWN. proposed: (partition list, jobs)."""
    cap = site['scheduler'].get('normal_qos_running_cap')
    if not cap:
        return
    normal = {name for name, part in site['partitions'].items() if part.get('qos') == 'normal'}
    new = sum(n for partition, n in proposed if set(partition.split(',')) & normal)
    if not new:
        return
    try:
        listed = slurm(['squeue', '-h', '-r', '-A', site['scheduler']['account'], '-q', 'normal',
                        '-t', 'RUNNING,PENDING', '-o', '%i'], senv).split()
    except (OSError, subprocess.CalledProcessError) as exc:
        p.exit(75, f'ERROR: squeue failed ({exc}); normal-QOS load UNKNOWN, nothing submitted\n')
    ceiling = cap - site['scheduler']['normal_qos_keep_free']
    if len(listed) + new > ceiling:
        p.exit(1, f'ERROR: {len(listed)} running or pending normal-QOS jobs for {site["scheduler"]["account"]}; '
                  f'adding {new} would exceed {ceiling} (keep {site["scheduler"]["normal_qos_keep_free"]} of {cap} '
                  f'slots free); nothing submitted\n')


if __name__ == '__main__':
    main()
