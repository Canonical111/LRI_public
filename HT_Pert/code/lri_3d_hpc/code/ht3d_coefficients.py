"""Command-line build, preflight and serial/OpenMP/MPI coefficient calculation."""
from __future__ import annotations

import argparse
import contextlib
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import socket
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor'))

import numpy as np
import scipy

from vertex_store import _jsonable, load_vertex_store, sha256_file

# Largest accepted max_scaled_seed_recursion_residual by arithmetic.  Every
# x87 reference run (64-bit significand, L <= 14) stays at or below 6.9e-18,
# while the same solves in binary64 give 4.4e-16 to 2.6e-15, so this gate
# detects a silent loss of extended precision that the 5e-13 coefficient
# comparison does not.
DEFAULT_MAX_RESIDUAL = {'longdouble': '1e-16', 'float64': '1e-12'}


def source_hashes():
    paths = sorted((ROOT / 'code').glob('*.py')) + sorted((ROOT / 'code').glob('*.cpp'))
    return {p.name: sha256_file(p) for p in paths}


def reference_entry(reference_path, cutoff, scheme, order):
    """The single reference row for one case; refused before any solve work."""
    reference = json.loads(Path(reference_path).read_text())
    candidates = reference.get('results', [reference.get('result', reference)])
    matches = [r for r in candidates if r.get('cutoff') == cutoff and
               r.get('scheme') == scheme and r.get('order') == order]
    if len(matches) != 1:
        raise ValueError('Reference must contain exactly one matching cutoff/scheme/order')
    return matches[0]


def validate_coefficients(result, reference_path, tolerance='5e-13'):
    """Compare every energy and coupling series, not only thermal C_n."""
    limit = np.longdouble(tolerance)
    if not np.isfinite(limit) or limit <= 0:
        raise ValueError('Validation tolerance must be finite and positive')
    target = reference_entry(reference_path, result['cutoff'], result['scheme'], result['order'])
    errors = {}
    for field in ('C', 'r', 'g', 'energies_by_seed', 'vacuum_energies_by_subcutoff'):
        actual, expected = result[field], target[field]
        if isinstance(actual, dict):
            if set(actual) != set(expected):
                raise ValueError('Reference series keys differ: ' + field)
            pairs = [(key, actual[key], expected[key]) for key in actual]
        else:
            pairs = [('', actual, expected)]
        for key, a, b in pairs:
            x, y = np.asarray(a, dtype=np.longdouble), np.asarray(b, dtype=np.longdouble)
            if (x.shape != y.shape or not np.all(np.isfinite(x)) or
                    not np.all(np.isfinite(y))):
                raise ValueError('Invalid comparison series: ' + field)
            scaled = np.max(np.abs(x-y) / np.maximum(np.longdouble(1), np.abs(y)))
            errors[field + ('.' + key if key else '')] = str(scaled)
    worst = max(np.longdouble(v) for v in errors.values())
    if worst > limit:
        raise ArithmeticError(f'Coefficient validation failed: {worst} > {tolerance}')
    return dict(reference_sha256=sha256_file(reference_path), tolerance=tolerance,
                max_scaled_error=str(worst), per_series_scaled_errors=errors)


def _lock_path(path, lock_dir=None):
    """Lock file for one output.  ``lock_dir`` (or HT3D_LOCK_DIR) must be on a
    file system whose flock is cluster-wide (for example NFS /home on symmetry,
    where BeeGFS flock is node-local); otherwise the lock sits next to the output."""
    lock_dir = lock_dir or os.environ.get('HT3D_LOCK_DIR')
    if not lock_dir:
        return path.with_name(path.name + '.lock')
    key = hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:32]
    return Path(lock_dir) / f'output-{key}.lock'


@contextlib.contextmanager
def output_claim(path, lock_dir=None):
    """One output writer; POSIX locks release automatically if a job is killed."""
    import fcntl
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _lock_path(path, lock_dir)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a+b') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise FileExistsError(f'Another job is writing {path}') from exc
        yield


def publish_new_json(path, value):
    """Publish a complete JSON file that must not exist yet; never overwrite.

    A hard link fails atomically if the target exists, so even writers that
    the lock cannot see (node-local flock) cannot replace a published result.
    File systems without hard links fall back to an existence check plus an
    atomic rename, which then relies on the output lock alone.
    """
    path = Path(path)
    temp = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    try:
        with temp.open('x', encoding='utf8') as out:
            json.dump(value, out, indent=2, sort_keys=True, default=_jsonable,
                      allow_nan=False)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        try:
            os.link(temp, path)
            method = 'link'
        except FileExistsError:
            raise FileExistsError(f'{path} appeared while this job ran; not overwritten') from None
        except OSError as exc:
            if exc.errno not in (errno.EPERM, errno.ENOTSUP, errno.EOPNOTSUPP, errno.EXDEV, errno.EMLINK):
                raise
            if path.exists():
                raise FileExistsError(f'{path} appeared while this job ran; not overwritten') from None
            os.rename(temp, path)
            method = 'rename'
    finally:
        temp.unlink(missing_ok=True)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    except OSError:
        pass
    finally:
        os.close(directory)
    return method


def check_arithmetic(name, allow_reduced=False):
    """Refuse a long double narrower than x87 (64-bit significand) unless
    explicitly allowed, and probe NumPy's arithmetic at run time: a process
    whose x87 precision control was lowered passes every static ABI check.
    ``name`` is the requested arithmetic, 'longdouble' or 'float64'."""
    dtype = np.dtype(name)
    f = np.finfo(dtype)
    one = dtype.type(1)
    tiny = np.ldexp(one, -int(f.nmant))
    probe = bool((one + tiny) - one == tiny)
    record = dict(requested=name, dtype=dtype.str, significand_bits=int(f.nmant)+1,
                  runtime_probe=probe)
    if not probe:
        raise ArithmeticError(f'{name} arithmetic does not deliver its {int(f.nmant)+1}-bit significand')
    if name == 'longdouble' and f.nmant < 63 and not allow_reduced:
        raise ArithmeticError(
            f'long double has only {int(f.nmant)+1} significand bits on this platform; '
            'use an x87 (64-bit) or wider long double, --dtype float64, or --allow-reduced-precision')
    return record


def native_precision_probe(backend, dtype, threads):
    """Every native thread must add with the full significand of ``dtype``."""
    from scipy.sparse import csr_matrix
    dtype = np.dtype(dtype)
    one = dtype.type(1)
    tiny = np.ldexp(one, -int(np.finfo(dtype).nmant))
    rows = max(1024, backend.serial_work_threshold//2 + 1, 64*int(threads))
    matrix = csr_matrix((np.ones(2*rows, dtype=dtype), np.tile(np.array([0, 1], np.int32), rows),
                         np.arange(0, 2*rows+1, 2, dtype=np.int32)), shape=(rows, 2))
    image = backend.csr_spmm(matrix, np.array([[one], [tiny]], dtype=dtype), threads=threads)
    if not bool(np.all(image[:, 0] - one == tiny)):
        raise ArithmeticError('Native kernels lose precision of ' + dtype.str)
    return dict(rows=rows, threads=int(threads), passed=True)


def node_provenance():
    """Host, scheduler and library facts that explain cross-site differences."""
    info = dict(host=socket.gethostname(), libc=' '.join(platform.libc_ver()),
                slurm={k: os.environ[k] for k in
                       ('SLURM_CLUSTER_NAME', 'SLURM_JOB_ID', 'SLURM_ARRAY_JOB_ID',
                        'SLURM_ARRAY_TASK_ID', 'SLURM_JOB_PARTITION', 'SLURM_JOB_NODELIST',
                        'SLURM_PROCID', 'SLURM_STEP_ID') if k in os.environ})
    try:
        with open('/proc/cpuinfo', encoding='utf8', errors='replace') as src:
            for line in src:
                key, _, value = line.partition(':')
                key = key.strip()
                if key in ('vendor_id', 'model name', 'cpu family', 'model') and key not in info:
                    info[key] = value.strip()
                if key == 'flags':
                    flags = set(value.split())
                    info['avx512f'] = 'avx512f' in flags
                    info['avx2'] = 'avx2' in flags
                    break
    except OSError:
        pass
    return info


def library_provenance():
    """Build-time BLAS/LAPACK configuration and the run-time thread pools."""
    out = {}
    for name, module in (('numpy', np), ('scipy', scipy)):
        try:
            out[name] = json.loads(json.dumps(module.show_config(mode='dicts'), default=str))
        except Exception as exc:
            out[name] = f'unavailable: {type(exc).__name__}: {exc}'
    try:
        from threadpoolctl import threadpool_info
        out['threadpools'] = json.loads(json.dumps(threadpool_info(), default=str))
    except Exception as exc:
        out['threadpools'] = f'unavailable: {type(exc).__name__}: {exc}'
    return out


def launched_processes():
    """Process count of a launcher that started this process without --mpi."""
    counts = [int(os.environ.get(k, '1') or '1')
              for k in ('OMPI_COMM_WORLD_SIZE', 'PMI_SIZE', 'MPI_LOCALNRANKS')]
    # srun steps (any PMI plugin, or none) export the step's task count; the
    # batch step does not count, since it runs a single copy of the script.
    if os.environ.get('SLURM_STEP_ID', 'batch').isdigit():
        counts.append(int(os.environ.get('SLURM_STEP_NUM_TASKS', '1') or '1'))
    if os.environ.get('PMIX_RANK') not in (None, '', '0'):
        counts.append(2)
    return max(counts)


def _existing_result(path, request, resume):
    path = Path(path)
    if not path.exists():
        return None
    if not resume:
        raise FileExistsError(f'{path} exists; use --resume to accept an identical completed job')
    old = json.loads(path.read_text())
    if old.get('format') != 'ht3d-coefficients-job-v1' or old.get('request') != request:
        raise ValueError('Existing output was made with different inputs, code or execution settings')
    if not old.get('complete') or 'result' not in old:
        raise ValueError('Existing output is incomplete')
    return old


def solve_job(args, comm=None):
    from native_backend import load_backend, precision_metadata
    from optimized_solver import solve_coefficients

    rank, nranks = (0, 1) if comm is None else (comm.Get_rank(), comm.Get_size())
    dtype = np.dtype(args.dtype)
    manifest_path = Path(args.store) / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    cutoff = manifest['cutoff'] if args.cutoff is None else args.cutoff
    if cutoff > manifest['cutoff'] or cutoff < 0 or cutoff % 2:
        raise ValueError('Requested cutoff must be even and covered by the vertex store')
    if args.order < 2 or manifest['degree'] < args.order-2:
        raise ValueError('Vertex Taylor degree is insufficient for the requested coefficient order')
    if np.dtype(manifest['precision']['dtype']) != dtype:
        raise ValueError('Requested arithmetic differs from stored vertices; rebuild in that precision')
    nz = args.nz if args.nz is not None else (3+4*(args.order//2)+2)//2
    threshold = (int(os.environ.get('HT3D_SERIAL_WORK_THRESHOLD', '10000'))
                 if args.serial_work_threshold is None else args.serial_work_threshold)
    if threshold < 0:
        raise ValueError('serial-work-threshold must be nonnegative')
    arithmetic = check_arithmetic(args.dtype, args.allow_reduced_precision)
    max_residual = (DEFAULT_MAX_RESIDUAL[args.dtype] if args.max_residual is None
                    else args.max_residual)
    residual_limit = np.longdouble(max_residual)
    if not np.isfinite(residual_limit) or residual_limit <= 0:
        raise ValueError('max-residual must be finite and positive')
    request = dict(store_manifest_sha256=sha256_file(manifest_path), cutoff=cutoff,
                   order=args.order, nz=nz, scheme=args.scheme, dtype=dtype.str,
                   strategy=args.strategy, backend=args.backend, threads=args.threads,
                   local_mode=args.local_mode, serial_work_threshold=threshold,
                   ranks=nranks, mpi_enabled=comm is not None, source_sha256=source_hashes(),
                   numpy=np.__version__, scipy=scipy.__version__,
                   requested_precision=precision_metadata(), max_residual=max_residual,
                   allow_reduced_precision=bool(args.allow_reduced_precision))
    if comm is not None:
        records = comm.allgather(request)
        if any(r != request for r in records):
            raise ValueError('MPI ranks disagree on source code, cache, parameters or precision')
    token = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    with (output_claim(args.output, args.lock_dir) if rank == 0 else contextlib.nullcontext()):
        decision = None
        if rank == 0:
            try:
                if args.compare_reference:
                    # An uncovered case would otherwise fail only after the solve.
                    reference_entry(args.compare_reference, cutoff, args.scheme, args.order)
                previous = _existing_result(args.output, request, args.resume)
                decision = dict(skip=previous is not None)
                if previous is not None and args.compare_reference:
                    decision['validation'] = validate_coefficients(
                        previous['result'], args.compare_reference, args.tolerance)
            except Exception as exc:
                decision = dict(error=f'{type(exc).__name__}: {exc}')
        if comm is not None:
            decision = comm.bcast(decision, root=0)
        if 'error' in decision:
            raise ValueError(decision['error'])
        if decision['skip']:
            if rank == 0:
                print(json.dumps(dict(status='already complete', output=str(args.output),
                                      request_sha256=token,
                                      validation=decision.get('validation'))), flush=True)
            return
        started = time.perf_counter()
        # One full checksum pass per MPI job.  Rank zero verifies first, then
        # every other rank opens the same immutable arrays without rehashing.
        data = None
        status = None
        if rank == 0:
            try:
                data = load_vertex_store(args.store, verify=not args.trust_staged_arrays)
                status = dict(ok=True)
            except Exception as exc:
                status = dict(error=f'{type(exc).__name__}: {exc}')
        if comm is not None:
            status = comm.bcast(status, root=0)
        if 'error' in status:
            raise ValueError(status['error'])
        if rank:
            data = load_vertex_store(args.store, verify=False)
        N, P, W, metadata = data
        del data
        local_backend = load_backend(args.backend, threads=args.threads,
                                     cache_dir=args.native_cache, serial_work_threshold=threshold)
        if args.backend == 'native' and args.threads > 1 and local_backend.backend_name != 'native-openmp':
            raise ValueError(f'--backend native with {args.threads} threads built '
                             f'{local_backend.backend_name}, not native-openmp: '
                             f'{local_backend.metadata.get("openmp_build_failure", "no OpenMP")}')
        native_probe = (native_precision_probe(local_backend, dtype, args.threads)
                        if local_backend.lib is not None else None)
        mpi_backend = None
        full_array_bytes = sum(m.data.nbytes+m.indices.nbytes+m.indptr.nbytes
                               for row in W for m in row)
        if comm is not None:
            from mpi_backend import (DistributedSparseBackend, balanced_row_partition,
                                     shard_vertices)
            nb = int(np.searchsorted(N, cutoff, side='right'))
            bounds = balanced_row_partition(W[3][0], nranks, nb)
            W = shard_vertices(W, bounds, rank, nb)
            N, P = np.asarray(N[:nb]).copy(), np.asarray(P[:nb]).copy()
            mpi_backend = DistributedSparseBackend(comm, bounds, local_backend, dtype)
            spmm = mpi_backend.csr_spmm
        else:
            spmm = local_backend.csr_spmm if local_backend.lib is not None else None
        stored_local_bytes = sum(m.data.nbytes+m.indices.nbytes+m.indptr.nbytes
                                 for row in W for m in row)
        loading_seconds = time.perf_counter()-started
        if comm is not None:
            comm.Barrier()
        started = time.perf_counter()
        result = solve_coefficients(N, P, W, cutoff, args.order, nz, args.scheme, dtype,
                                     strategy=args.strategy, spmm=spmm,
                                     distributed=comm is not None,
                                     synchronize_coefficients=(mpi_backend.synchronize_coefficients
                                                               if mpi_backend else None),
                                     hamiltonian_apply=(mpi_backend.apply_hamiltonian
                                                        if mpi_backend else None),
                                     local_mode=args.local_mode,
                                     threads=args.threads, progress=args.progress and rank == 0)
        solve_seconds = time.perf_counter()-started
        stats = dict(rank=rank, node=node_provenance(), native_precision_probe=native_probe,
                     load_and_setup_seconds=loading_seconds,
                     solve_wall_seconds=solve_seconds,
                     peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                     full_vertex_logical_array_bytes=full_array_bytes,
                     rank_vertex_logical_array_bytes=stored_local_bytes,
                     backend=mpi_backend.diagnostics() if mpi_backend else local_backend.metadata)
        records = [stats] if comm is None else comm.gather(stats, root=0)
        if rank == 0:
            residual = np.longdouble(result['max_scaled_seed_recursion_residual'])
            if not np.isfinite(residual) or residual > residual_limit:
                raise ArithmeticError(f'Seed recursion residual {residual} exceeds {max_residual}; '
                                      'not published (lost precision?)')
            validation = (validate_coefficients(result, args.compare_reference, args.tolerance)
                          if args.compare_reference else None)
            execution = dict(python=platform.python_version(), numpy=np.__version__,
                             scipy=scipy.__version__, platform=platform.platform(),
                             arithmetic=arithmetic,
                             residual_gate=dict(limit=max_residual, value=str(residual)),
                             libraries=library_provenance(), ranks=records,
                             max_solve_wall_seconds=max(r['solve_wall_seconds'] for r in records),
                             max_rank_peak_rss_kib=max(r['peak_rss_kib'] for r in records),
                             vertex_metadata=metadata,
                             input_checksums_verified=not args.trust_staged_arrays,
                             validation=validation,
                             thread_environment={k: os.environ.get(k) for k in
                                ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS',
                                 'OMP_PROC_BIND', 'OMP_PLACES', 'NUMBA_NUM_THREADS',
                                 'OMP_WAIT_POLICY', 'GOMP_SPINCOUNT')})
            output = dict(format='ht3d-coefficients-job-v1', complete=True,
                          request=request, request_sha256=token,
                          execution=execution, result=result)
            publish_new_json(args.output, output)
            print(json.dumps(dict(status='complete', output=str(args.output),
                                   cutoff=cutoff, scheme=args.scheme, C=result['C'],
                                   solve_seconds=execution['max_solve_wall_seconds'],
                                   peak_rank_rss_kib=execution['max_rank_peak_rss_kib'],
                                   validation=validation)), flush=True)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    pre = sub.add_parser('preflight', help='Count graph arrays without building the basis')
    pre.add_argument('--cutoff', required=True, type=int)
    pre.add_argument('--order', type=int, default=8)
    build = sub.add_parser('build', help='Construct streamed, precision-checked Taylor vertices')
    build.add_argument('--cutoff', type=int, required=True)
    build.add_argument('--order', type=int, default=8)
    build.add_argument('--store', type=Path, required=True)
    build.add_argument('--spill', type=Path)
    build.add_argument('--dtype', choices=('longdouble', 'float64'), default='longdouble')
    build.add_argument('--max-states', type=int, default=2_000_000)
    build.add_argument('--max-bytes', type=int, default=2*1024**3)
    build.add_argument('--no-layout-cache', action='store_true',
                       help='Reduce vertex construction memory at the cost of repeated format conversions')
    run = sub.add_parser('solve', help='Solve one cutoff and one window prescription')
    run.add_argument('--store', type=Path, required=True)
    run.add_argument('--output', type=Path, required=True)
    run.add_argument('--cutoff', type=int)
    run.add_argument('--order', type=int, default=8)
    run.add_argument('--nz', type=int)
    run.add_argument('--scheme', choices=('raw', 'consistent'), default='consistent')
    run.add_argument('--dtype', choices=('longdouble', 'float64'), default='longdouble')
    run.add_argument('--strategy', choices=('stationary', 'recurrence'), default='stationary')
    run.add_argument('--backend', choices=('native', 'auto', 'scipy'), default='native')
    run.add_argument('--threads', type=int, default=1)
    run.add_argument('--local-mode', choices=('dense', 'banded'), default='banded')
    run.add_argument('--serial-work-threshold', type=int,
                     help='Native tiny-work serial threshold; default environment value or 10000, zero disables')
    run.add_argument('--native-cache', type=Path)
    run.add_argument('--mpi', action='store_true')
    run.add_argument('--resume', action='store_true')
    run.add_argument('--progress', action='store_true')
    run.add_argument('--trust-staged-arrays', action='store_true',
                     help='Explicitly skip file checksums after an independently verified staging step')
    run.add_argument('--compare-reference', type=Path)
    run.add_argument('--tolerance', default='5e-13')
    run.add_argument('--max-residual',
                     help='Largest accepted scaled seed-recursion residual; default 1e-16 '
                          'for longdouble, 1e-12 for float64')
    run.add_argument('--allow-reduced-precision', action='store_true',
                     help='Accept a long double narrower than x87 (portability tests only)')
    run.add_argument('--lock-dir', type=Path,
                     help='Directory with cluster-wide flock for the output lock '
                          '(default: HT3D_LOCK_DIR, else next to the output)')
    return p


def main():
    args = parser().parse_args()
    if args.command == 'preflight':
        if args.cutoff < 0 or args.cutoff % 2 or args.order < 2:
            raise ValueError('Require an even nonnegative cutoff and order >= 2')
        from ht3d.basis import graph_requirements
        value = graph_requirements(args.cutoff)
        value.update(order=args.order, vertex_taylor_degree=args.order-2,
                     required_local_occupation_max=3+4*(args.order//2),
                     note='Projectors, sparse vertices, workspace and replicated vectors are additional.')
        print(json.dumps(value, indent=2))
    elif args.command == 'build':
        from taylor_vertices import build_taylor_vertices
        if args.order < 2:
            raise ValueError('Require order >= 2')
        N, P, W, metadata = build_taylor_vertices(
            args.cutoff, args.order-2, dtype=np.dtype(args.dtype),
            max_states=args.max_states, max_bytes=args.max_bytes,
            return_metadata=True, store_path=args.store, spill_path=args.spill,
            cache_layouts=not args.no_layout_cache)
        print(json.dumps(dict(store=str(args.store), metadata=metadata), default=str, indent=2))
    else:
        if args.threads < 1:
            raise ValueError('threads must be positive')
        comm = None
        if args.mpi:
            from mpi4py import MPI
            comm = MPI.COMM_WORLD
        elif launched_processes() > 1:
            raise ValueError('MPI launcher detected; add --mpi or launch only one Python process')
        try:
            solve_job(args, comm)
        except BaseException as exc:
            if comm is not None and comm.Get_size() > 1:
                print(f'Rank {comm.Get_rank()} failed: {type(exc).__name__}: {exc}',
                      file=sys.stderr, flush=True)
                comm.Abort(1)
            raise


if __name__ == '__main__':
    main()
