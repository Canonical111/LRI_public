#!/usr/bin/env python3
"""In-job stage runner for one HT3D campaign (Expanse and symmetry).

  ht3d_stage.py run    --campaign DIR --cutoff L --stages S1,S2,... [--lanes K] [--shard I/N]
                       [--threads T] [--solve-cutoffs C ...] [--schemes raw consistent]
  ht3d_stage.py task   KIND ITEM --campaign DIR --cutoff L     (one subprocess; used by run)
  ht3d_stage.py status --campaign DIR --cutoff L               (light: manifests only)

Stages in pipeline order (all idempotent; a completed target is verified, never rebuilt):
  prepare     graph, SO(3) projectors and projected inputs  -> prepared/L<L>/
  images      one task per particle sector                   -> prepared/L<L>/images/p<p>/
  matrix      one task per (k, r), largest first             -> prepared/L<L>/tasks/k<k>-r<r>/
  finalize    combine the 4*(degree+1) tasks (full checksums)-> stores/L<L>/
  verify      full checksum load of the store                -> records/L<L>/verify/store.json
  gate        cutoff-14 solves vs the saved reference        -> gates/L<L>/<scheme>_c14.json
  solve       production solves from this store             -> results/L<L>/c<C>_<scheme>.json
  crosscheck  recurrence-strategy solves vs stationary       -> crosscheck/L<L>/c<C>_<scheme>.json
                                                                + c<C>_<scheme>.compare.json
Production solves and crosschecks run only from a store whose raw and consistent cutoff-14
gates passed against the shipped reference with this code. A crosscheck is complete only
when its comparison record (bound to both result files' sha256 and the limit) exists.
Every command first checks that the staged release is the one the campaign was frozen for
and that the campaign lock directory has cluster-wide flock semantics for its site.

Every task holds an flock on a per-target lock in the campaign lock directory (cluster-wide:
Lustre on Expanse, NFS /home on symmetry), removes stale '<target>.partial-*' directories of
dead attempts only while holding it, turns SIGTERM/SIGUSR1 into an exception so the
pipeline's own cleanup runs, fsyncs a published directory before reporting success, and
writes a per-task record (host, CPU, job ids, threads, wall time, peak RSS).
Exit codes: 0 done, 75 a target is busy in another job (retry later), 65 an existing
target fails verification (move it aside by hand), 1 failure, 3 wrong node class or
allocation, 2 usage.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'code'), str(ROOT/'vendor')]

STAGES = ('prepare', 'images', 'matrix', 'finalize', 'verify', 'gate', 'solve', 'crosscheck')
SCHEMES = ('raw', 'consistent')
GATE_CUTOFF = 14
# Largest accepted scaled difference between the recurrence and stationary strategies (and
# between MPI and serial solves), by arithmetic: x87 roundoff differences are ~1e-17.
CROSSCHECK_LIMIT = {'longdouble': '1e-15', 'float64': '1e-12'}
REFERENCE = ROOT/'results'/'reference_coefficients_L14.json'
EXIT_BUSY, EXIT_BAD_TARGET, EXIT_NODE = 75, 65, 3


class Interrupted(BaseException):
    """Raised from a signal handler so `except BaseException` cleanup runs."""


class Busy(Exception):
    pass


class BadTarget(Exception):
    pass


class AllocationTooSmall(Exception):
    pass


def _interrupt(signum, frame):
    raise Interrupted(f'signal {signum}')


# ---------------------------------------------------------------- campaign and paths

def load_campaign(path):
    path = Path(path).resolve()
    campaign = json.loads((path/'campaign.json').read_text())
    if campaign.get('format') != 'ht3d-campaign-v1':
        raise ValueError(f'{path} is not an ht3d campaign')
    return path, campaign


class Layout:
    def __init__(self, root, cutoff, campaign=None):
        self.root, self.L = Path(root), int(cutoff)
        self.campaign = campaign if campaign is not None else load_campaign(root)[1]
        tag = f'L{self.L}'
        self.prepared = self.root/'prepared'/tag
        self.store = self.root/'stores'/tag
        self.records = self.root/'records'/tag
        self.verified = self.records/'verify'/'store.json'
        self.gates = self.root/'gates'/tag
        self.results = self.root/'results'/tag
        self.crosscheck = self.root/'crosscheck'/tag

    def image(self, particle):
        return self.prepared/'images'/f'p{particle}'

    def matrix(self, k, r):
        return self.prepared/'tasks'/f'k{k}-r{r}'

    def gate(self, scheme):
        return self.gates/f'{scheme}_c{min(GATE_CUTOFF, self.L)}.json'

    def solve(self, cutoff, scheme):
        return self.results/f'c{cutoff}_{scheme}.json'

    def recurrence(self, cutoff, scheme):
        return self.crosscheck/f'c{cutoff}_{scheme}.json'


def check_cutoff(value):
    if not (isinstance(value, int) and value >= 0 and value % 2 == 0):
        raise ValueError(f'cutoff must be an even nonnegative integer, not {value!r}')
    return value


def mount_of(path):
    """(fstype, options, mountpoint) of the file system holding path, from /proc/mounts."""
    path = os.path.realpath(path)
    best = None
    try:
        mounts = Path('/proc/mounts').read_text().splitlines()
    except OSError:
        return None
    for line in mounts:
        device, point, fstype, options = line.split()[:4]
        if (path == point or path.startswith(point.rstrip('/') + '/')) and \
                (best is None or len(point) > len(best[2])):
            best = (fstype, options, point)
    return best


def lock_filesystem_problem(site, path):
    """None if flock on `path` is cluster-wide on this site, else the reason.

    Expanse: Lustre mounted with 'flock' (not 'localflock'). symmetry: NFS with
    local_lock=none (BeeGFS flock there is node-local). Other sites have no rule; they
    only occur in hand-made test campaigns.
    """
    if site not in ('expanse', 'symmetry'):
        return None
    Path(path).mkdir(parents=True, exist_ok=True)
    found = mount_of(path)
    if found is None:
        return f'no mount found for {path}'
    fstype, options = found[0], found[1].split(',')
    if site == 'expanse' and not (fstype == 'lustre' and 'flock' in options and 'localflock' not in options):
        return f'{path} is on {found}; Expanse locks need Lustre mounted with flock'
    if site == 'symmetry' and not (fstype.startswith('nfs') and 'local_lock=none' in options):
        return f'{path} is on {found}; symmetry locks need NFS with local_lock=none'
    return None


def _file_digest(path):
    try:
        real = os.path.realpath(path)
        return dict(path=real, sha256=hashlib.sha256(Path(real).read_bytes()).hexdigest())
    except OSError as exc:
        return dict(path=str(path), error=type(exc).__name__)


def ldd_dependencies(path):
    """{soname: resolved path or 'not found'} of every shared library `path` loads (ldd)."""
    try:
        text = subprocess.run(['ldd', str(path)], capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    out = {}
    for line in text.splitlines():
        name, arrow, rest = line.strip().partition(' => ')
        if arrow:
            out[name] = rest.split(' (')[0].strip() or 'not found'
    return out


def mpi_runtime_identity():
    """The MPI runtime that would actually run, without initialising MPI: the mpi4py extension
    module (build artifact) and every shared library it resolves (ldd, no name filter: MPI,
    PMI(x), UCX's libucp/libuct/libucm/libucs, fabrics, libc, ...), by real path and sha256;
    plus each site launcher's resolved binary and --version banner (HT3D_MPI_LAUNCHERS)."""
    import importlib.util
    import shlex
    import shutil
    out = {}
    try:
        origin = importlib.util.find_spec('mpi4py.MPI').origin
    except (ImportError, AttributeError, ValueError):
        origin = None
    if origin:
        out['mpi4py_extension'] = _file_digest(origin)
        out['libraries'] = {name: (_file_digest(target) if target != 'not found' else 'not found')
                            for name, target in sorted(ldd_dependencies(origin).items())}
    launchers = {}
    for launcher in filter(None, (x.strip() for x in os.environ.get('HT3D_MPI_LAUNCHERS', '').split(';'))):
        command = shlex.split(launcher)[0]
        found = shutil.which(command)
        try:
            banner = subprocess.run([found or command, '--version'], capture_output=True, text=True,
                                    timeout=60).stdout.strip().splitlines()[:1] if found else None
        except (OSError, subprocess.SubprocessError):
            banner = None
        launchers[launcher] = dict(binary=_file_digest(found) if found else None, version=banner)
    out['launchers'] = launchers
    return out


def environment_identity():
    """(identity, fingerprint) of the Python environment, compiler and mpi4py build that run
    this process: a campaign is bound to the identity its validation receipt recorded."""
    from importlib import metadata
    import platform
    packages = sorted({(d.metadata['Name'] or '?').lower(): d.version for d in metadata.distributions()}.items())
    try:
        banner = subprocess.run([os.environ.get('CXX', 'c++'), '--version'], capture_output=True,
                                text=True, timeout=60).stdout.splitlines()[:1]
    except (OSError, subprocess.SubprocessError):
        banner = None
    try:
        import mpi4py
        mpi = mpi4py.get_config()
    except Exception as exc:
        mpi = f'unavailable: {type(exc).__name__}'
    identity = dict(python=platform.python_version(), executable=sys.executable, prefix=sys.prefix,
                    packages=packages, compiler=banner, mpi4py_config=mpi, mpi_runtime=mpi_runtime_identity())
    return identity, hashlib.sha256(json.dumps(identity, sort_keys=True, default=str).encode()).hexdigest()


def runtime_problems(campaign):
    """Reasons this job must not touch the campaign: wrong release, another environment than
    the validated one, or unsafe locks."""
    problems = []
    want = (campaign.get('release') or {}).get('fingerprint')
    staged = ROOT/'RELEASE.sha256'
    have = hashlib.sha256(staged.read_bytes()).hexdigest() if staged.exists() else None
    if want is not None or have is not None:
        if want != have:
            problems.append(f'staged release fingerprint {have} differs from the campaign\'s {want}')
        elif os.environ.get('HT3D_RELEASE_FINGERPRINT', have) != have:
            problems.append('HT3D_RELEASE_FINGERPRINT differs from the staged RELEASE.sha256')
    frozen = (campaign.get('environment') or {}).get('fingerprint')
    if frozen is not None:
        identity, fingerprint = environment_identity()
        if fingerprint != frozen:
            problems.append(f'environment {fingerprint[:16]} differs from the validated {frozen[:16]} '
                            '(validate this environment and start a new campaign)')
    lock = lock_filesystem_problem(campaign.get('site'), campaign['lock_dir'])
    if lock:
        problems.append(lock)
    return problems


# ---------------------------------------------------------------- locks, records, fsync

@contextlib.contextmanager
def target_lock(campaign_root, campaign, target):
    """Cluster-wide exclusive claim of one target; released automatically on death."""
    lock_dir = Path(campaign['lock_dir'])
    lock_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(str(Path(target).resolve()).encode()).hexdigest()[:32]
    with (lock_dir/f'target-{key}.lock').open('a+b') as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Busy(f'{target} is being built by another job') from None
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps(dict(target=str(target), host=socket.gethostname(),
                                     pid=os.getpid(), job=job_ids())).encode())
        handle.flush()
        yield


def sweep_partials(target):
    """Remove '<target>.partial-*' (and '<target>.tmp-*') of dead attempts; lock held."""
    removed = []
    for stale in Path(target).parent.glob(Path(target).name + '.partial-*'):
        shutil.rmtree(stale, ignore_errors=True)
        removed.append(stale.name)
    for stale in Path(target).parent.glob(Path(target).name + '.tmp-*'):
        stale.unlink(missing_ok=True)
        removed.append(stale.name)
    return removed


def fsync_tree(path):
    path = Path(path)
    files = [path] if path.is_file() else sorted(p for p in path.rglob('*') if p.is_file())
    for item in files:
        fd = os.open(item, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    for directory in ([path] if path.is_dir() else []) + [path.parent]:
        fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        except OSError:
            pass
        finally:
            os.close(fd)


def job_ids():
    return {k: os.environ[k] for k in ('SLURM_JOB_ID', 'SLURM_ARRAY_JOB_ID', 'SLURM_ARRAY_TASK_ID',
                                        'SLURM_JOB_PARTITION', 'SLURM_JOB_NAME') if k in os.environ}


def node_facts():
    from ht3d_coefficients import node_provenance
    return node_provenance()


def write_record(layout, stage, key, record, env=None):
    """Calibration record. A caller's own fields (for example its requested 'threads') are
    kept; `env` is the environment the measured process ran with (default: this process)."""
    folder = layout.records/stage
    folder.mkdir(parents=True, exist_ok=True)
    job = os.environ.get('SLURM_JOB_ID', 'nojob')
    path = folder/f'{key}.{job}.{os.getpid()}.json'
    env = os.environ if env is None else env
    record = dict(record, stage=stage, key=key, job=job_ids(), node=node_facts(),
                  release=os.environ.get('HT3D_RELEASE_FINGERPRINT'),
                  thread_environment={k: env.get(k) for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                                                              'NUMBA_NUM_THREADS', 'MKL_NUM_THREADS')},
                  written=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
    path.write_text(json.dumps(record, indent=1, sort_keys=True, default=str) + '\n')
    return path


# ---------------------------------------------------------------- allocation / node checks

def allowed_cpus():
    if hasattr(os, 'sched_getaffinity'):   # Linux: the job's cgroup/affinity CPU set
        return len(os.sched_getaffinity(0))
    return os.cpu_count() or 1            # local tests on other platforms


def cgroup_memory_limit():
    """Effective memory ceiling in bytes for this process, or None if nothing limits it.

    The minimum over the memory limits of the process's cgroup and every ancestor (cgroup v2
    memory.max, or v1 memory.limit_in_bytes) and, inside a Slurm job, the allocation itself
    (SLURM_MEM_PER_NODE, in MB). An unlimited or unreadable leaf therefore never hides a
    finite parent limit or the requested allocation.
    """
    limits = []
    slurm = os.environ.get('SLURM_MEM_PER_NODE', '')
    if slurm.isdigit() and int(slurm) > 0:
        limits.append(int(slurm) * 1024**2)
    try:
        lines = Path('/proc/self/cgroup').read_text().splitlines()
    except OSError:
        lines = []
    for line in lines:
        _, controllers, rel = line.split(':', 2)
        if controllers == '':                       # cgroup v2: memory.max in each ancestor
            base, name = Path('/sys/fs/cgroup'), 'memory.max'
        elif 'memory' in controllers.split(','):    # cgroup v1: hierarchical limit_in_bytes
            base, name = Path('/sys/fs/cgroup/memory'), 'memory.limit_in_bytes'
        else:
            continue
        node = base/rel.lstrip('/')
        while True:
            try:
                text = (node/name).read_text().strip()
                if text != 'max' and int(text) < 2**60:
                    limits.append(int(text))
            except (OSError, ValueError):
                pass
            if node == base or base not in node.parents:
                break
            node = node.parent
    return min(limits) if limits else None


# ---------------------------------------------------------------- one task (subprocess)

def verify_image(layout, inputs, input_hash, particle):
    from taylor_pipeline import IMAGE_FORMAT
    from vertex_store import load_sparse
    folder = layout.image(particle)
    record = json.loads((folder/'manifest.json').read_text())
    expected = dict(format=IMAGE_FORMAT, particle=particle, inputs_sha256=input_hash,
                    degree=inputs['degree'], precision=inputs['precision'])
    if any(record.get(k) != v for k, v in expected.items()):
        raise BadTarget(f'existing image task has incompatible inputs: {folder}')
    keys = {f'{k}:{r}' for k in range(1, min(4, particle)+1) for r in range(inputs['degree']+1)}
    if set(record.get('images', {})) != keys:
        raise BadTarget(f'existing image task has incomplete layers: {folder}')
    for array in record['images'].values():
        load_sparse(folder, array, verify=True)


def verify_matrix(layout, inputs, input_hash, k, r):
    from taylor_pipeline import TASK_FORMAT
    from vertex_store import load_sparse
    folder = layout.matrix(k, r)
    record = json.loads((folder/'manifest.json').read_text())
    expected = dict(format=TASK_FORMAT, k=k, r=r, inputs_sha256=input_hash,
                    precision=inputs['precision'])
    if any(record.get(key) != value for key, value in expected.items()):
        raise BadTarget(f'existing matrix task has incompatible inputs: {folder}')
    load_sparse(folder, record['matrix'], verify=True)


def matrix_items(degree):
    # Largest first: k=4 dominates memory and time, then low Taylor orders.
    return [f'{k}-{r}' for k in (4, 3, 2, 1) for r in range(degree+1)]


def build_target(kind, item, layout, campaign):
    """Returns (target, status, details). Raises Busy/BadTarget."""
    import numpy as np
    from taylor_pipeline import (_read_inputs, prepare_vertex_inputs, build_particle_images,
                                 assemble_vertex_task, finalize_vertex_store)
    from vertex_store import load_vertex_store, sha256_file
    if kind == 'prepare':
        target = layout.prepared
    elif kind == 'images':
        target = layout.image(int(item))
    elif kind == 'matrix':
        k, r = map(int, item.split('-'))
        target = layout.matrix(k, r)
    elif kind == 'finalize':
        target = layout.store
    elif kind == 'verify':
        target = layout.verified
    else:
        raise ValueError(kind)
    with target_lock(layout.root, campaign, target):
        swept = sweep_partials(target)
        details = dict(swept=swept)
        if kind == 'prepare':
            if target.exists():
                _read_inputs(target)
                return target, 'verified-existing', details
            from ht3d.basis import graph_requirements
            need = graph_requirements(layout.L)
            limit = cgroup_memory_limit()
            details.update(graph=need, cgroup_memory_limit=limit,
                           blas_threads=os.environ.get('OPENBLAS_NUM_THREADS'))
            if limit is not None and limit < 2*need['graph_array_bytes']:
                raise AllocationTooSmall(f'prepare L{layout.L}: memory limit {limit} B is below twice the '
                                         f"graph arrays ({need['graph_array_bytes']} B); request more memory")
            projector_log = layout.records/'prepare'/f'projector.{os.environ.get("SLURM_JOB_ID", "nojob")}.jsonl'
            projector_log.parent.mkdir(parents=True, exist_ok=True)
            os.environ['HT3D_PROJECTOR_LOG'] = str(projector_log)
            os.environ['HT3D_PROJECTOR_DUMP_DIR'] = str(layout.records/'prepare'/'projector_dumps')
            manifest = prepare_vertex_inputs(target, layout.L, campaign['degree'],
                                             np.longdouble if campaign['dtype'] == 'longdouble' else np.float64,
                                             max_states=need['states'],
                                             max_bytes=need['graph_array_bytes'])
            details.update(metadata=manifest['metadata'])
        elif kind in ('images', 'matrix'):
            inputs = _read_inputs(layout.prepared)
            input_hash = sha256_file(layout.prepared/'manifest.json')
            check = ((lambda: verify_image(layout, inputs, input_hash, int(item))) if kind == 'images'
                     else (lambda: verify_matrix(layout, inputs, input_hash, k, r)))
            if target.exists():
                try:
                    check()
                except (OSError, ValueError, KeyError) as exc:
                    raise BadTarget(str(exc)) from None
                return target, 'verified-existing', details
            if kind == 'images':
                manifest = build_particle_images(layout.prepared, int(item))
            else:
                manifest = assemble_vertex_task(layout.prepared, k, r,
                                                cache_layouts=not campaign.get('no_layout_cache', False))
            details.update({key: value for key, value in manifest.items()
                            if key in ('seconds', 'nnz', 'array_bytes', 'sparse_products_executed',
                                       'zero_sparse_products_skipped', 'shape')})
        elif kind == 'finalize':
            if target.exists():
                load_vertex_store(target, verify=False)
                return target, 'verified-existing', details
            metadata = finalize_vertex_store(layout.prepared, target, verify=True)
            details.update(vertex_nnz=metadata['vertex_nnz'],
                           vertex_array_bytes=metadata['vertex_array_bytes'])
        else:  # verify: always a full checksum pass, also when the marker already exists
            store_hash = sha256_file(layout.store/'manifest.json')
            if target.exists():
                old = json.loads(target.read_text())
                if old.get('store_manifest_sha256') != store_hash or old.get('passed') is not True:
                    raise BadTarget(f'{target} records another store; move it aside')
            started = time.perf_counter()
            try:
                N, P, W, metadata = load_vertex_store(layout.store, verify=True)
            except ValueError as exc:
                raise BadTarget(f'store {layout.store} fails verification: {exc}') from None
            details.update(store_manifest_sha256=store_hash, verify_seconds=time.perf_counter()-started)
            if target.exists():
                return target, 'reverified', details
            value = dict(passed=True, store=str(layout.store), store_manifest_sha256=store_hash,
                         cutoff=metadata['cutoff'], scalar_bath_states=len(N),
                         store_array_bytes=metadata['store_array_bytes'],
                         seconds=time.perf_counter()-started, job=job_ids(), host=socket.gethostname())
            del N, P, W
            target.parent.mkdir(parents=True, exist_ok=True)
            from ht3d_coefficients import publish_new_json
            publish_new_json(target, value)
        fsync_tree(target)
        return target, 'built', details


def run_task(kind, item, campaign_dir, cutoff):
    root, campaign = load_campaign(campaign_dir)
    layout = Layout(root, cutoff)
    problems = runtime_problems(campaign)
    if problems:
        print('refused: ' + '; '.join(problems), file=sys.stderr)
        return EXIT_NODE
    signal.signal(signal.SIGTERM, _interrupt)
    signal.signal(signal.SIGUSR1, _interrupt)
    started = time.perf_counter()
    if kind == 'prepare':
        mismatch = node_class_mismatch(campaign)
        if mismatch:
            print(f'prepare refused on this node class: {mismatch}', file=sys.stderr)
            return EXIT_NODE
    record = dict(kind=kind, item=item, cutoff=layout.L)
    try:
        target, status, details = build_target(kind, item, layout, campaign)
        record.update(status=status, target=str(target), **details)
        code = 0
    except Busy as exc:
        record.update(status='busy', error=str(exc))
        code = EXIT_BUSY
    except BadTarget as exc:
        record.update(status='bad-target', error=str(exc))
        code = EXIT_BAD_TARGET
    except AllocationTooSmall as exc:
        record.update(status='allocation-too-small', error=str(exc))
        code = EXIT_NODE
    except Interrupted as exc:
        record.update(status='interrupted', error=str(exc))
        code = 143
    except Exception as exc:
        record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        code = 1
    record.update(seconds=time.perf_counter()-started,
                  self_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    write_record(layout, kind, str(item).replace('/', '_'), record)
    print(json.dumps(dict(kind=kind, item=item, status=record['status'],
                          seconds=round(record['seconds'], 3), error=record.get('error'))), flush=True)
    return code


def node_class_mismatch(campaign):
    """prepare depends on BLAS kernels and libm at the last bit: one CPU class per campaign."""
    want = campaign.get('cpu_class') or {}
    have = node_facts()
    return {k: dict(campaign=v, node=have.get(k)) for k, v in want.items() if have.get(k) != v}


# ---------------------------------------------------------------- solves (driver subprocess)

def result_state(path, store_hash, campaign, cutoff, scheme, strategy, *, mpi_ranks=None):
    """'missing', 'done', or 'incompatible: <why>' for a published coefficient job.

    'done' requires the exact case this campaign asks for: store, cutoff, scheme, order, the
    driver's default nz/local mode/residual gate, strategy, arithmetic, native backend, the
    current solver source, and serial versus the given MPI rank count. An incompatible file is
    never silently accepted or replaced; it has to be moved aside by hand.
    """
    import numpy as np
    from ht3d_coefficients import DEFAULT_MAX_RESIDUAL, source_hashes
    path = Path(path)
    if not path.exists():
        return 'missing'
    try:
        job = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return f'incompatible: {path} is unreadable ({exc})'
    order = campaign['order']
    want = dict(store_manifest_sha256=store_hash, cutoff=cutoff, order=order, nz=(3+4*(order//2)+2)//2,
                scheme=scheme, dtype=np.dtype(campaign['dtype']).str, strategy=strategy, backend='native',
                local_mode='banded', mpi_enabled=mpi_ranks is not None, ranks=mpi_ranks or 1,
                source_sha256=source_hashes(), max_residual=DEFAULT_MAX_RESIDUAL[campaign['dtype']],
                allow_reduced_precision=False)
    request = job.get('request') or {}
    bad = [key for key, value in want.items() if request.get(key) != value]
    result = job.get('result') or {}
    if job.get('format') != 'ht3d-coefficients-job-v1' or job.get('complete') is not True:
        bad.append('format/complete')
    if (result.get('cutoff'), result.get('scheme'), result.get('order')) != (cutoff, scheme, order):
        bad.append('result case')
    return 'done' if not bad else f'incompatible: {path} differs in {bad}'


def driver_command(layout, campaign, cutoff, scheme, output, threads, *, strategy='stationary',
                   reference=False, trust=False):
    command = [sys.executable, str(ROOT/'code'/'ht3d_coefficients.py'), 'solve',
               '--store', str(layout.store), '--cutoff', str(cutoff), '--order', str(campaign['order']),
               '--scheme', scheme, '--strategy', strategy, '--dtype', campaign['dtype'], '--backend', 'native',
               '--threads', str(threads), '--output', str(output), '--lock-dir', campaign['lock_dir'],
               '--progress']
    if reference:
        command += ['--compare-reference', str(REFERENCE)]
    if trust:
        command += ['--trust-staged-arrays']
    return command


def verify_store_once(layout, store_hash):
    """Full checksum pass over the store, once per consuming job: the arrays are ordinary
    writable files, so an earlier verification never vouches for this job's reads. Driver
    subprocesses of this job then skip re-hashing (--trust-staged-arrays). Returns seconds."""
    from vertex_store import load_vertex_store, sha256_file
    started = time.perf_counter()
    N, P, W, metadata = load_vertex_store(layout.store, verify=True)
    del N, P, W
    if sha256_file(layout.store/'manifest.json') != store_hash:
        raise ValueError('store manifest changed during verification')
    return time.perf_counter() - started


def store_verified(layout):
    from vertex_store import sha256_file
    try:
        record = json.loads(layout.verified.read_text())
        return (record.get('passed') is True and
                record.get('store_manifest_sha256') == sha256_file(layout.store/'manifest.json'))
    except (OSError, ValueError):
        return False


def scaled_difference(a, b):
    """max |a-b|/max(1,|b|) over every compared series of two results of the same case.
    Refuses different cases, different series structure and any nonfinite entry."""
    import numpy as np
    for key in ('cutoff', 'scheme', 'order'):
        if a.get(key) != b.get(key):
            raise ValueError(f'results are for different cases ({key}: {a.get(key)} vs {b.get(key)})')
    worst = np.longdouble(0)
    for field in ('C', 'r', 'g', 'energies_by_seed', 'vacuum_energies_by_subcutoff'):
        x, y = a[field], b[field]
        if isinstance(x, dict) != isinstance(y, dict):
            raise ValueError(f'series structure differs in {field}')
        if isinstance(x, dict) and set(x) != set(y):
            raise ValueError(f'series keys differ in {field}')
        pairs = [(x[key], y[key]) for key in sorted(x)] if isinstance(x, dict) else [(x, y)]
        for p, q in pairs:
            p, q = np.asarray(p, np.longdouble), np.asarray(q, np.longdouble)
            if p.shape != q.shape or p.ndim != 1 or not len(p):
                raise ValueError(f'series shapes differ or are empty in {field}')
            if not (np.all(np.isfinite(p)) and np.all(np.isfinite(q))):
                raise ValueError(f'nonfinite entry in {field}')
            d = np.max(np.abs(p-q)/np.maximum(np.longdouble(1), np.abs(q)))
            if not np.isfinite(d):
                raise ValueError(f'nonfinite difference in {field}')
            worst = max(worst, d)
    return worst


def reference_sha256():
    from vertex_store import sha256_file
    return sha256_file(REFERENCE)


def gate_state(layout, store_hash, scheme):
    """result_state of one cutoff-14 gate, plus its reference evidence: 'done' only if the
    driver validated it against the shipped reference (sha256) at tolerance 5e-13."""
    path = layout.gate(scheme)
    state = result_state(path, store_hash, layout.campaign, min(GATE_CUTOFF, layout.L), scheme, 'stationary')
    if state != 'done':
        return state
    validation = (json.loads(path.read_text()).get('execution') or {}).get('validation') or {}
    if validation.get('reference_sha256') != reference_sha256() or validation.get('tolerance') != '5e-13':
        return f'incompatible: {path} was not validated against the shipped reference at 5e-13'
    return 'done'


def gate_problem(layout, store_hash):
    """None if both cutoff-14 gates passed for this store, reference and code, else why."""
    for scheme in SCHEMES:
        state = gate_state(layout, store_hash, scheme)
        if state != 'done':
            return f'no valid {scheme} gate for this store ({state})'
    return None


def comparison_path(output):
    output = Path(output)
    return output.with_name(output.stem + '.compare.json')


def comparison_done(output, other, limit):
    """A passing comparison record bound to the current bytes of both results and the limit."""
    from vertex_store import sha256_file
    try:
        record = json.loads(comparison_path(output).read_text())
        return (record.get('passed') is True and record.get('limit') == limit and
                record.get('result_sha256') == sha256_file(output) and
                record.get('other') == str(other) and record.get('other_sha256') == sha256_file(other))
    except (OSError, ValueError):
        return False


def compare_and_record(output, other, limit):
    """Compare two published results; publish a passing record (never overwritten).
    Returns (passed, difference string)."""
    import numpy as np
    from vertex_store import sha256_file
    from ht3d_coefficients import publish_new_json
    try:
        diff = scaled_difference(json.loads(Path(output).read_text())['result'],
                                 json.loads(Path(other).read_text())['result'])
    except (OSError, ValueError, KeyError) as exc:
        return False, f'{type(exc).__name__}: {exc}'
    passed = bool(diff <= np.longdouble(limit))
    if passed and not comparison_done(output, other, limit):
        record = dict(passed=True, limit=limit, max_scaled_difference=str(diff),
                      result=str(output), result_sha256=sha256_file(output),
                      other=str(other), other_sha256=sha256_file(other), job=job_ids(),
                      host=socket.gethostname())
        target = comparison_path(output)
        if target.exists():
            raise BadTarget(f'{target} exists but does not match the current results; move it aside')
        publish_new_json(target, record)
    return passed, str(diff)


STORE_VALUE_FINGERPRINT = 'ht3d-store-values-v2'


def store_value_fingerprint(store):
    """Fingerprint of everything that defines a store's vertices, ignoring the 6 uninitialised
    padding bytes of each 16-byte x87 long double (so value-identical builds agree although
    their file checksums differ): format version, cutoff, degree, precision, N, P, every
    pattern's indices/indptr under its id, and every matrix's key, shape, pattern id and data."""
    import numpy as np
    store = Path(store)
    m = json.loads((store/'manifest.json').read_text())
    h = hashlib.sha256()
    h.update(json.dumps(dict(format=STORE_VALUE_FINGERPRINT, store_format=m.get('format'), cutoff=m['cutoff'],
                             degree=m['degree'], precision=m['precision']), sort_keys=True).encode())

    def add(label, record):
        a = np.load(store/record['file'], mmap_mode='r', allow_pickle=False)
        h.update(f'|{label}|{a.dtype.str}|{a.shape}|'.encode())
        padded = a.dtype.kind == 'f' and a.dtype.itemsize == 16 and np.finfo(a.dtype).nmant == 63
        step = 1 << (22 if padded else 24)
        for start in range(0, len(a), step):
            chunk = np.ascontiguousarray(a[start:start + step]).view(np.uint8)
            h.update((chunk.reshape(-1, 16)[:, :10] if padded else chunk).tobytes())

    add('N', m['N'])
    add('P', m['P'])
    for pid in sorted(m['patterns']):
        add(f'pattern {pid} indices', m['patterns'][pid]['indices'])
        add(f'pattern {pid} indptr', m['patterns'][pid]['indptr'])
    for key in sorted(m['matrices']):
        record = m['matrices'][key]
        h.update(f'|matrix {key}|shape {record["shape"]}|pattern {record["pattern"]}|'.encode())
        add(f'matrix {key} data', record['data'])
    return f'{STORE_VALUE_FINGERPRINT}:{h.hexdigest()}'


# ---------------------------------------------------------------- parent: stage runner

class Lanes:
    """Bounded concurrent subprocesses with per-child rusage (os.wait4).

    `stop` is the runner's shared stop state: a signal that arrives while start() waits for a
    free lane is honoured before anything new is spawned."""

    def __init__(self, width, stop=None):
        self.width, self.running, self.done = int(width), {}, []
        self.stop = stop if stop is not None else {'flag': False}

    def start(self, label, command, env=None):
        """Spawn one task when a lane is free; False (nothing spawned) once a stop was requested."""
        if self.stop['flag']:
            return False
        while len(self.running) >= self.width:
            self.reap()
        if self.stop['flag']:
            return False
        print(f'[{time.strftime("%H:%M:%S")}] start {label}', flush=True)
        proc = subprocess.Popen(command, env=env)
        self.running[proc.pid] = (label, proc, time.perf_counter())
        return True

    def reap(self):
        pid, status, usage = os.wait4(-1, 0)
        if pid not in self.running:
            return
        label, proc, began = self.running.pop(pid)
        proc.returncode = os.waitstatus_to_exitcode(status)
        self.done.append(dict(label=label, rc=proc.returncode, seconds=time.perf_counter()-began,
                              peak_rss_kib=usage.ru_maxrss))
        print(f'[{time.strftime("%H:%M:%S")}] end {label} rc={proc.returncode} '
              f'peak_rss={usage.ru_maxrss/1048576:.2f}GiB', flush=True)

    def drain(self):
        while self.running:
            self.reap()
        return self.done


def run_stages(args):
    root, campaign = load_campaign(args.campaign)
    layout = Layout(root, check_cutoff(args.cutoff))
    stages = args.stages.split(',')
    if any(s not in STAGES for s in stages) or len(set(stages)) != len(stages):
        print(f'stages must be distinct names from {STAGES}', file=sys.stderr)
        return 2
    stages = [s for s in STAGES if s in stages]
    threads = args.threads or allowed_cpus()
    if threads > allowed_cpus():
        print(f'--threads {threads} exceeds the {allowed_cpus()} CPUs of this allocation', file=sys.stderr)
        return EXIT_NODE
    shard, nshard = map(int, args.shard.split('/'))
    if not 0 <= shard < nshard:
        print('--shard must be I/N with 0 <= I < N', file=sys.stderr)
        return 2
    if nshard > 1 and len(stages) != 1 or nshard > 1 and stages[0] not in ('images', 'matrix'):
        # Matrix tasks read images of every particle sector: an image shard is not a barrier.
        print('--shard applies to exactly one of the images or matrix stages', file=sys.stderr)
        return 2
    problems = runtime_problems(campaign)
    if problems:
        print('refused: ' + '; '.join(problems), file=sys.stderr)
        return EXIT_NODE
    stop = {'flag': False}

    def soft_stop(signum, frame):
        stop['flag'] = True
        print(f'[{time.strftime("%H:%M:%S")}] signal {signum}: no new tasks; waiting for running ones',
              flush=True)
    signal.signal(signal.SIGTERM, soft_stop)
    signal.signal(signal.SIGUSR1, soft_stop)
    me = [sys.executable, str(Path(__file__).resolve())]
    outcome = []
    job_verified = {}
    for stage in stages:
        if stop['flag']:
            break
        print(f'== stage {stage} L{layout.L} ({time.strftime("%Y-%m-%dT%H:%M:%S")})', flush=True)
        if stage in ('prepare', 'images', 'matrix', 'finalize', 'verify'):
            if stage in ('images', 'matrix') and not (layout.prepared/'manifest.json').exists():
                print(f'{stage}: no prepared inputs {layout.prepared}', file=sys.stderr)
                outcome.append(dict(stage=stage, label=stage, rc=1))
                break
            if stage == 'images':
                from taylor_pipeline import _read_inputs
                items = [str(p) for p in sorted(int(p) for p in _read_inputs(layout.prepared)['particles'])]
                items = items[::-1]   # high particle number first: the costly sectors
            elif stage == 'matrix':
                items = matrix_items(campaign['degree'])
            else:
                items = ['all']
            if stage in ('images', 'matrix'):
                items = [x for i, x in enumerate(items) if i % nshard == shard]
                # Published tasks are not re-hashed here: matrix tasks verify the images they
                # load and finalize verifies every task array, so a retry only builds the rest.
                target = (lambda x: layout.image(int(x))) if stage == 'images' else \
                    (lambda x: layout.matrix(*map(int, x.split('-'))))
                present = [x for x in items if (target(x)/'manifest.json').exists()]
                if present:
                    print(f'{stage}: {len(present)} task(s) already published; '
                          f'{len(items)-len(present)} to run', flush=True)
                items = [x for x in items if x not in present]
            width = args.lanes if stage in ('images', 'matrix') else 1
            env = dict(os.environ)
            env['OPENBLAS_NUM_THREADS'] = str(args.blas_threads if stage == 'prepare' else 1)
            lanes = Lanes(width, stop)
            for item in items:
                if not lanes.start(f'{stage}:{item}', me + ['task', stage, item, '--campaign', str(root),
                                                            '--cutoff', str(layout.L)], env=env):
                    break
            outcome += [dict(stage=stage, **d) for d in lanes.drain()]
            if any(d['rc'] != 0 for d in outcome if d['stage'] == stage):
                break                      # later stages need this one complete
            continue
        # Driver-based stages: one subprocess at a time, all threads.
        from vertex_store import sha256_file
        if not (layout.store/'manifest.json').exists():
            print(f'{stage}: no store {layout.store}', file=sys.stderr)
            outcome.append(dict(stage=stage, label=stage, rc=1))
            break
        store_hash = sha256_file(layout.store/'manifest.json')
        if not job_verified.get(store_hash):
            try:
                seconds = verify_store_once(layout, store_hash)
            except ValueError as exc:
                print(f'{stage}: store {layout.store} fails verification: {exc}', file=sys.stderr)
                outcome.append(dict(stage=stage, label=stage, rc=EXIT_BAD_TARGET))
                break
            job_verified[store_hash] = True
            print(f'{stage}: store checksums verified in {seconds:.1f} s (once for this job)', flush=True)
        trust = True
        if stage in ('solve', 'crosscheck'):
            problem = gate_problem(layout, store_hash)
            if problem:
                print(f'{stage} refused: {problem}; run the gate stage first', file=sys.stderr)
                outcome.append(dict(stage=stage, label=stage, rc=1))
                break
        cases = []
        if stage == 'gate':
            cutoff = min(GATE_CUTOFF, layout.L)
            cases = [(cutoff, s, layout.gate(s), 'stationary', True) for s in SCHEMES]
        elif stage == 'solve':
            for c in (args.solve_cutoffs or [layout.L]):
                cases += [(c, s, layout.solve(c, s), 'stationary', False) for s in args.schemes]
        else:
            for c in (args.solve_cutoffs or [layout.L]):
                cases += [(c, s, layout.recurrence(c, s), 'recurrence', False) for s in args.schemes]
        for cutoff, scheme, output, strategy, reference in cases:
            if stop['flag']:
                break
            check_cutoff(cutoff)
            if cutoff > layout.L:
                print(f'{stage}: cutoff {cutoff} exceeds store L{layout.L}', file=sys.stderr)
                outcome.append(dict(stage=stage, label=f'c{cutoff}_{scheme}', rc=2))
                continue
            label = f'{stage}:c{cutoff}_{scheme}'
            limit = CROSSCHECK_LIMIT[campaign['dtype']]
            stationary = layout.solve(cutoff, scheme)
            if stage == 'crosscheck':
                base = result_state(stationary, store_hash, campaign, cutoff, scheme, 'stationary')
                if base != 'done':
                    print(f'{label}: stationary result not usable ({base}); run solve first', file=sys.stderr)
                    outcome.append(dict(stage=stage, label=label, rc=1))
                    continue
            state = (gate_state(layout, store_hash, scheme) if stage == 'gate' else
                     result_state(output, store_hash, campaign, cutoff, scheme, strategy))
            if state.startswith('incompatible'):
                print(f'{label}: {state}; move it aside', file=sys.stderr)
                outcome.append(dict(stage=stage, label=label, rc=EXIT_BAD_TARGET))
                continue
            if stage == 'crosscheck' and state == 'done' and comparison_done(output, stationary, limit):
                print(f'{label}: already complete and compared ({output})', flush=True)
                outcome.append(dict(stage=stage, label=label, rc=0))
                continue
            if state == 'done':
                print(f'{label}: already complete ({output})', flush=True)
                rc = 0
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                env = dict(os.environ, OMP_NUM_THREADS=str(threads), OPENBLAS_NUM_THREADS='1')
                lanes = Lanes(1, stop)
                if not lanes.start(label, driver_command(layout, campaign, cutoff, scheme, output, threads,
                                                         strategy=strategy, reference=reference, trust=trust),
                                   env=env):
                    break
                rec = lanes.drain()[0]
                rc = rec['rc']
                write_record(layout, stage, f'c{cutoff}_{scheme}',
                             dict(kind=stage, cutoff=cutoff, scheme=scheme, strategy=strategy,
                                  output=str(output), rc=rc, seconds=rec['seconds'],
                                  child_peak_rss_kib=rec['peak_rss_kib'], threads=threads,
                                  store_manifest_sha256=store_hash, checksums_skipped=trust), env=env)
            if rc == 0 and stage == 'crosscheck':
                try:
                    ok, diff = compare_and_record(output, stationary, limit)
                except BadTarget as exc:
                    ok, diff = False, str(exc)
                print(json.dumps(dict(crosscheck=label, max_scaled_difference=diff,
                                      limit=limit, passed=ok)), flush=True)
                write_record(layout, 'crosscheck-compare', f'c{cutoff}_{scheme}',
                             dict(max_scaled_difference=diff, limit=limit, passed=ok,
                                  recurrence=str(output), stationary=str(stationary)))
                rc = 0 if ok else 1
            outcome.append(dict(stage=stage, label=label, rc=rc))
        if any(d['rc'] != 0 for d in outcome if d['stage'] == stage):
            break
    codes = [d['rc'] for d in outcome]
    print(json.dumps(dict(summary=[(d['label'], d['rc']) for d in outcome], stopped=stop['flag'])), flush=True)
    if stop['flag']:
        return EXIT_BUSY if all(c in (0, EXIT_BUSY) for c in codes) else 1
    for code in (1, EXIT_BAD_TARGET, EXIT_NODE, 143, EXIT_BUSY):
        if code in codes:
            return code
    return 0 if all(c == 0 for c in codes) else 1


# ---------------------------------------------------------------- status (login node)

def stage_status(campaign_dir, cutoff, schemes=SCHEMES, solve_cutoffs=None):
    """Manifest-level completion per stage (no array hashing)."""
    root, campaign = load_campaign(campaign_dir)
    layout = Layout(root, check_cutoff(cutoff))
    out = {}
    try:
        from taylor_pipeline import _read_inputs
        inputs = _read_inputs(layout.prepared)
        out['prepare'] = 'done'
    except FileNotFoundError:
        inputs = None
        out['prepare'] = 'missing'
    except (OSError, ValueError) as exc:
        inputs = None
        out['prepare'] = f'bad: {exc}'
    if inputs is not None:
        particles = sorted(int(p) for p in inputs['particles'])
        missing = [p for p in particles if not (layout.image(p)/'manifest.json').exists()]
        out['images'] = 'done' if not missing else f'missing {len(missing)}/{len(particles)}'
        tasks = [(k, r) for k in range(1, 5) for r in range(inputs['degree']+1)]
        missing = [t for t in tasks if not (layout.matrix(*t)/'manifest.json').exists()]
        out['matrix'] = 'done' if not missing else f'missing {len(missing)}/{len(tasks)}'
    else:
        out['images'] = out['matrix'] = 'missing'
    if (layout.store/'manifest.json').exists():
        from vertex_store import sha256_file
        store_hash = sha256_file(layout.store/'manifest.json')
        out['finalize'] = 'done'
        out['verify'] = 'done' if store_verified(layout) else 'missing'
        gates = [gate_state(layout, store_hash, s) for s in SCHEMES]
        bad = [x for x in gates if x.startswith('incompatible')]
        out['gate'] = ('bad: ' + '; '.join(bad)) if bad else ('done' if all(x == 'done' for x in gates) else 'missing')
        cutoffs = solve_cutoffs or [layout.L]
        limit = CROSSCHECK_LIMIT[campaign['dtype']]
        solves = [result_state(layout.solve(c, s), store_hash, campaign, c, s, 'stationary')
                  for c in cutoffs for s in schemes]
        checks = [result_state(layout.recurrence(c, s), store_hash, campaign, c, s, 'recurrence')
                  for c in cutoffs for s in schemes]
        bad = [x for x in solves if x.startswith('incompatible')]
        out['solve'] = ('bad: ' + '; '.join(bad)) if bad else ('done' if all(x == 'done' for x in solves) else 'missing')
        bad = [x for x in checks if x.startswith('incompatible')]
        done = all(x == 'done' for x in checks) and all(
            comparison_done(layout.recurrence(c, s), layout.solve(c, s), limit) for c in cutoffs for s in schemes)
        out['crosscheck'] = ('bad: ' + '; '.join(bad)) if bad else ('done' if done else 'missing')
    else:
        for s in ('finalize', 'verify', 'gate', 'solve', 'crosscheck'):
            out[s] = 'missing'
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    r = sub.add_parser('run')
    r.add_argument('--campaign', required=True)
    r.add_argument('--cutoff', type=int, required=True)
    r.add_argument('--stages', required=True)
    r.add_argument('--lanes', type=int, default=1)
    r.add_argument('--shard', default='0/1')
    r.add_argument('--threads', type=int)
    r.add_argument('--blas-threads', type=int, default=1)
    r.add_argument('--solve-cutoffs', type=int, nargs='+')
    r.add_argument('--schemes', nargs='+', choices=SCHEMES, default=list(SCHEMES))
    t = sub.add_parser('task')
    t.add_argument('kind', choices=('prepare', 'images', 'matrix', 'finalize', 'verify'))
    t.add_argument('item')
    t.add_argument('--campaign', required=True)
    t.add_argument('--cutoff', type=int, required=True)
    s = sub.add_parser('status')
    s.add_argument('--campaign', required=True)
    s.add_argument('--cutoff', type=int, required=True)
    s.add_argument('--solve-cutoffs', type=int, nargs='+')
    s.add_argument('--schemes', nargs='+', choices=SCHEMES, default=list(SCHEMES))
    args = p.parse_args()
    if args.command == 'run':
        if args.lanes < 1 or args.blas_threads < 1:
            p.error('--lanes and --blas-threads must be positive')
        return run_stages(args)
    if args.command == 'task':
        return run_task(args.kind, args.item, args.campaign, check_cutoff(args.cutoff))
    print(json.dumps(stage_status(args.campaign, args.cutoff, args.schemes, args.solve_cutoffs), indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
