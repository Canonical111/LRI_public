#!/usr/bin/env python3
"""Multi-node MPI orchestration inside an mpi.sbatch allocation (batch step).

  ht3d_mpi.py validate   multi-node receipt: native prebuild on every node, launcher world
                         check (N*R ranks on N distinct hosts, R ranks per node), cross-node
                         flock on the lock root (must block) and on the data file system
                         (recorded), tests/check_mpi_backend.py on all ranks, and MPI solves at
                         cutoff 14 from HT3D_STORE compared with the serial gate results in
                         HT3D_SERIAL_GATES (<= 1e-15), and an abort drill (one rank exits
                         abnormally; the launcher must end the step within 300 s)
                         -> $HT3D_DATA/validation/mpi_<git12>_<job>/
  ht3d_mpi.py solve      production MPI solves for HT3D_CAMPAIGN / HT3D_CUTOFF (store) at
                         HT3D_SOLVE_CUTOFFS x HT3D_SCHEMES -> results/L<L>/c<C>_<scheme>_mpi<N>x<R>.json,
                         each compared with the serial result when one exists (<= 1e-15; a passing
                         comparison record is published next to it). Requires the store's passing
                         cutoff-14 gates, the campaign's release and cluster-wide locks.
Launch prefixes come from cluster/launch.py: srun (--kill-on-bad-exit=1) on Expanse, Open MPI
mpirun inside the allocation on symmetry (its Debian Open MPI cannot use Slurm's PMI plugins).
Per-node steps that are not MPI (prebuild, flock drill) always use plain srun.
"""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT/'code'), str(ROOT/'vendor'), str(HERE)]
from ht3d_stage import CROSSCHECK_LIMIT  # noqa: E402
import launch  # noqa: E402
LIMIT = CROSSCHECK_LIMIT['longdouble']    # MPI campaigns are x87 long double


def env_int(name):
    value = os.environ[name]
    if not value.isdigit():
        raise SystemExit(f'{name}={value!r} is not a positive integer')
    return int(value)


def srun(launcher, nodes, per_node, cpus, command, *, bind=True, timeout=None):
    """Run one launcher step; a timeout is reported as rc 124 instead of raising."""
    full = launch.prefix(launcher, nodes=nodes, per_node=per_node, cpus=cpus, bind=bind) + \
        [str(c) for c in command]
    print('$ ' + ' '.join(shlex.quote(c) for c in full), flush=True)
    started = time.perf_counter()
    try:
        proc = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        proc = subprocess.CompletedProcess(full, 124, exc.stdout or '', exc.stderr or '')
        if isinstance(proc.stdout, bytes):
            proc.stdout, proc.stderr = proc.stdout.decode(errors='replace'), (proc.stderr or b'').decode(errors='replace')
    sys.stdout.write(proc.stdout[-4000:])
    sys.stderr.write(proc.stderr[-4000:])
    return proc, time.perf_counter()-started


def layout():
    """(nodes, ranks per node, cpus per rank) of this allocation; ranks are spread evenly."""
    nodes, tasks, cpus = env_int('SLURM_JOB_NUM_NODES'), env_int('SLURM_NTASKS'), env_int('SLURM_CPUS_PER_TASK')
    if tasks % nodes:
        raise SystemExit(f'{tasks} tasks do not divide evenly over {nodes} nodes')
    return nodes, tasks//nodes, cpus


def prebuild(nodes, cpus, want_environment=None):
    """Compile/load the native library once per node outside MPI (no fork after MPI_Init) and
    report each node's environment fingerprint (interpreter, packages, compiler, MPI runtime);
    with want_environment, every node must match it."""
    code = ('import socket,sys; sys.path[:0] = [%r, %r, %r]; from native_backend import load_backend; '
            'from ht3d_stage import environment_identity; '
            'b = load_backend("native", threads=%d); '
            'print("NATIVE", socket.gethostname(), b.backend_name, environment_identity()[1])'
            % (str(ROOT/'code'), str(ROOT/'vendor'), str(HERE), cpus))
    proc, _ = srun('srun', nodes, 1, cpus, [sys.executable, '-E', '-c', code], bind=False, timeout=1800)
    lines = [l.split() for l in proc.stdout.splitlines() if l.startswith('NATIVE')]
    fingerprints = {l[3] for l in lines if len(l) > 3}
    ok = (proc.returncode == 0 and len(lines) == nodes and len({l[1] for l in lines}) == nodes
          and all(l[2] == 'native-openmp' for l in lines) and len(fingerprints) == 1
          and (want_environment is None or fingerprints == {want_environment}))
    return dict(rc=proc.returncode, nodes=lines, environments=sorted(fingerprints), passed=ok)


def world(launcher, nodes, per_node, cpus):
    code = ('import os; from mpi4py import MPI; c = MPI.COMM_WORLD; '
            'print("WORLD", c.Get_rank(), c.Get_size(), MPI.Get_processor_name(), '
            'len(os.sched_getaffinity(0)), flush=True)')
    proc, _ = srun(launcher, nodes, per_node, cpus, [sys.executable, '-E', '-c', code], timeout=600)
    rows = [l.split() for l in proc.stdout.splitlines() if l.startswith('WORLD')]
    total = nodes*per_node
    ranks = sorted(int(r[1]) for r in rows)
    hosts = {r[3] for r in rows}
    ok = (proc.returncode == 0 and ranks == list(range(total)) and all(int(r[2]) == total for r in rows)
          and len(hosts) == nodes and all(int(r[4]) == cpus for r in rows))
    return dict(rc=proc.returncode, ranks=len(rows), hosts=sorted(hosts),
                affinity=sorted({int(r[4]) for r in rows}), passed=ok)


def compare(a, b):
    """Compare two published results; a passing comparison is published next to `a`."""
    from ht3d_stage import BadTarget, compare_and_record
    try:
        passed, diff = compare_and_record(a, b, LIMIT)
    except BadTarget as exc:
        passed, diff = False, str(exc)
    return dict(max_scaled_difference=diff, limit=LIMIT, passed=passed)


def abort_drill(launcher, nodes, per_node):
    """The last rank exits abnormally without MPI_Finalize; the step must end, non-zero."""
    code = ('import os, time; from mpi4py import MPI; c = MPI.COMM_WORLD; '
            'os._exit(3) if c.Get_rank() == c.Get_size()-1 else c.Barrier(); time.sleep(600)')
    proc, seconds = srun(launcher, nodes, per_node, 1, [sys.executable, '-E', '-c', code],
                         bind=False, timeout=300)
    return dict(rc=proc.returncode, seconds=round(seconds, 1),
                passed=proc.returncode not in (0, 124) and seconds < 300)


def validated_store(store, gates):
    """This job's full checksum pass over `store`, and both serial cutoff-14 gates in `gates`
    bound to exactly that store manifest and validated at 5e-13. Returns a stage record with
    'passed'. (The single-node receipt runs it on its own L14 store as regression coverage.)"""
    from vertex_store import load_vertex_store, sha256_file
    store, gates = Path(store), Path(gates)
    started = time.perf_counter()
    try:
        store_hash = sha256_file(store/'manifest.json')
        load_vertex_store(store, verify=True)
        problems = []
        for scheme in ('raw', 'consistent'):
            gate_job = json.loads((gates/f'{scheme}_c14.json').read_text())
            validation = (gate_job.get('execution') or {}).get('validation') or {}
            result = gate_job.get('result') or {}
            if (gate_job.get('request', {}).get('store_manifest_sha256') != store_hash or
                    result.get('cutoff') != 14 or result.get('scheme') != scheme or
                    validation.get('tolerance') != '5e-13'):
                problems.append(f'{scheme} gate is not a validated cutoff-14 result of this store')
        if sha256_file(store/'manifest.json') != store_hash:
            problems.append('store manifest changed during verification')
    except (OSError, ValueError, KeyError) as exc:
        return dict(passed=False, problems=[f'{type(exc).__name__}: {exc}'])
    return dict(passed=not problems, problems=problems, store_manifest_sha256=store_hash,
                seconds=time.perf_counter()-started)


def solve_command(store, cutoff, scheme, output, threads, lock_dir, *, reference=False, trust=False):
    command = [sys.executable, '-E', '-m', 'mpi4py', ROOT/'code'/'ht3d_coefficients.py', 'solve', '--mpi',
               '--store', store, '--cutoff', cutoff, '--scheme', scheme, '--backend', 'native',
               '--threads', threads, '--output', output, '--lock-dir', lock_dir, '--progress']
    if reference:
        command += ['--compare-reference', ROOT/'results'/'reference_coefficients_L14.json']
    if trust:
        command += ['--trust-staged-arrays']
    return command


def validate():
    nodes, per_node, cpus = layout()
    if nodes < 2:
        raise SystemExit('validate needs at least two nodes')
    job = os.environ['SLURM_JOB_ID']
    out = Path(os.environ['HT3D_DATA'])/'validation'/f'mpi_{os.environ["HT3D_GIT_SHA"][:12]}_{job}'
    out.mkdir(parents=True, exist_ok=False)
    store = Path(os.environ['HT3D_STORE'])
    gates = Path(os.environ['HT3D_SERIAL_GATES'])
    stages = {}
    from ht3d_stage import environment_identity
    stages['prebuild'] = prebuild(nodes, cpus, environment_identity()[1])
    # This job's own checksum pass over the supplied store, and serial gates bound to it,
    # before any solve is allowed to skip hashing.
    stages['store'] = validated_store(store, gates)
    chosen, tried = None, []
    for candidate in os.environ.get('HT3D_MPI_LAUNCHERS', '').split(';'):
        if candidate.strip():
            result = world(candidate, nodes, per_node, cpus)
            tried.append(dict(launcher=candidate, **result))
            if result['passed']:
                chosen = candidate
                break
    stages['launcher'] = dict(chosen=chosen, tried=tried, passed=chosen is not None)
    if chosen:
        stages['abort_drill'] = abort_drill(chosen, nodes, per_node)
    for name, folder in (('lock_root', Path(os.environ['HT3D_LOCK_ROOT'])), ('data_fs', out)):
        folder.mkdir(parents=True, exist_ok=True)
        proc, _ = srun('srun', 2, 1, 1, [sys.executable, '-E', HERE/'flock_drill.py',
                                         folder/f'drill_{job}.lock', 20], bind=False, timeout=300)
        stages[f'flock_{name}'] = dict(rc=proc.returncode, output=proc.stdout.strip().splitlines(),
                                       cross_node=proc.returncode == 0,
                                       passed=proc.returncode == 0 or name == 'data_fs')
    if chosen:
        proc, seconds = srun(chosen, nodes, per_node, 1, [sys.executable, '-E', '-m', 'mpi4py',
                                                         ROOT/'tests'/'check_mpi_backend.py',
                                                         '--output', out/'check_mpi_backend.json'],
                             timeout=3600)
        stages['check_mpi_backend'] = dict(rc=proc.returncode, seconds=seconds, passed=proc.returncode == 0)
        for scheme in ('raw', 'consistent') if stages['store']['passed'] else ():
            output = out/f'mpi_L14_{scheme}.json'
            proc, seconds = srun(chosen, nodes, per_node, cpus,
                                 solve_command(store, 14, scheme, output, cpus, out/'locks',
                                               reference=True, trust=True), timeout=7200)
            entry = dict(rc=proc.returncode, seconds=seconds, passed=False)
            if proc.returncode == 0:
                entry.update(compare(output, gates/f'{scheme}_c14.json'))
            stages[f'mpi_L14_{scheme}'] = entry
    passed = all(s.get('passed') for s in stages.values())
    from ht3d_coefficients import node_provenance
    from ht3d_stage import environment_identity
    env_identity, env_fp = environment_identity()
    receipt = dict(format='ht3d-mpi-receipt-v1', passed=passed, site=os.environ['HT3D_SITE'],
                   release=dict(git_sha=os.environ.get('HT3D_GIT_SHA'),
                                fingerprint=os.environ.get('HT3D_RELEASE_FINGERPRINT'),
                                tar_sha256=os.environ.get('HT3D_RELEASE_SHA256')),
                   job=job, nodelist=os.environ.get('SLURM_JOB_NODELIST'),
                   partition=os.environ.get('SLURM_JOB_PARTITION'), nodes=nodes, ranks_per_node=per_node,
                   cpus_per_task=cpus, mpi_launcher=chosen, store=str(store), node=node_provenance(),
                   environment=dict(fingerprint=env_fp, identity=env_identity),
                   stages=stages)
    (out/'receipt.json').write_text(json.dumps(receipt, indent=1, default=str) + '\n')
    print(json.dumps(dict(passed=passed, receipt=str(out/'receipt.json'),
                          failed=[k for k, v in stages.items() if not v.get('passed')])), flush=True)
    return 0 if passed else 1


def solve():
    from ht3d_stage import Layout, check_cutoff, load_campaign, result_state, verify_store_once, write_record
    from vertex_store import sha256_file
    nodes, per_node, cpus = layout()
    root, campaign = load_campaign(os.environ['HT3D_CAMPAIGN'])
    if campaign.get('release', {}).get('fingerprint') != os.environ.get('HT3D_RELEASE_FINGERPRINT'):
        raise SystemExit('campaign was frozen for another release')
    launcher = campaign.get('mpi_launcher')
    if not launcher:
        raise SystemExit('campaign has no validated MPI launcher (run validate-mpi first)')
    from ht3d_stage import comparison_done, gate_problem, runtime_problems
    problems = runtime_problems(campaign)
    if problems:
        raise SystemExit('refused: ' + '; '.join(problems))
    lay = Layout(root, check_cutoff(env_int('HT3D_CUTOFF')))
    store_hash = sha256_file(lay.store/'manifest.json')
    problem = gate_problem(lay, store_hash)
    if problem:
        raise SystemExit(f'refused: {problem}; run the gate stage first')
    # Full checksum pass once in this job (batch step), then every MPI solve skips re-hashing.
    print(f'store checksums verified in {verify_store_once(lay, store_hash):.1f} s', flush=True)
    trust = True
    cutoffs = [check_cutoff(int(c)) for c in os.environ.get('HT3D_SOLVE_CUTOFFS', str(lay.L)).split()]
    schemes = os.environ.get('HT3D_SCHEMES', 'raw consistent').split()
    built = prebuild(nodes, cpus, (campaign.get('environment') or {}).get('fingerprint'))
    check = world(launcher, nodes, per_node, cpus)
    print(json.dumps(dict(prebuild=built, world=check)), flush=True)
    if not (built['passed'] and check['passed']):
        return 3
    code = 0
    for cutoff in cutoffs:
        for scheme in schemes:
            if cutoff > lay.L or scheme not in ('raw', 'consistent'):
                raise SystemExit(f'bad case c{cutoff} {scheme}')
            output = lay.results/f'c{cutoff}_{scheme}_mpi{nodes}x{per_node}.json'
            serial = lay.solve(cutoff, scheme)
            have_serial = result_state(serial, store_hash, campaign, cutoff, scheme, 'stationary') == 'done'
            state = result_state(output, store_hash, campaign, cutoff, scheme, 'stationary',
                                 mpi_ranks=nodes*per_node)
            if state.startswith('incompatible'):
                print(f'{state}; move it aside', file=sys.stderr)
                code = 65
                continue
            record = dict(kind='solve-mpi', cutoff=cutoff, scheme=scheme, output=str(output),
                          nodes=nodes, ranks_per_node=per_node, threads=cpus, launcher=launcher,
                          store_manifest_sha256=store_hash)
            if state == 'done':
                if not have_serial or comparison_done(output, serial, LIMIT):
                    print(f'{output} already complete', flush=True)
                    continue
                record.update(rc=0, seconds=0.0, reused=True)   # repeat a missing or failed comparison
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                proc, seconds = srun(launcher, nodes, per_node, cpus,
                                     solve_command(lay.store, cutoff, scheme, output, cpus, campaign['lock_dir'],
                                                   trust=trust))
                record.update(rc=proc.returncode, seconds=seconds)
            if record['rc'] == 0 and have_serial:
                record['vs_serial'] = compare(output, serial)
                if not record['vs_serial']['passed']:
                    code = 1
            write_record(lay, 'solve-mpi', f'c{cutoff}_{scheme}', record)
            if record['rc'] != 0:
                code = 1
    return code


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) == 2 else ''
    if mode == 'validate':
        sys.exit(validate())
    if mode == 'solve':
        sys.exit(solve())
    sys.exit('usage: ht3d_mpi.py validate|solve')
