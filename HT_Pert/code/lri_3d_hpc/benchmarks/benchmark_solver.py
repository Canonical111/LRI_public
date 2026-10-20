"""Fresh-process solver benchmark with numerical comparisons and optional profile.

Use the same environment, input arrays, cutoff and profiling setting for timing
comparisons.  --trusted-pickle is only for the original locally generated cache;
portable runs should use --store.  Never load an untrusted pickle.
"""
from pathlib import Path
import argparse
import cProfile
import json
import os
import pickle
import platform
import pstats
import resource
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'code'), str(ROOT/'reference'), str(ROOT/'vendor')]
import numpy as np
import scipy
from ht3d_coefficients import validate_coefficients, source_hashes
from native_backend import load_backend
from vertex_store import load_vertex_store, atomic_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    inputs = p.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--store', type=Path)
    inputs.add_argument('--trusted-pickle', type=Path)
    p.add_argument('--solver', choices=('reference', 'optimized'), default='optimized')
    p.add_argument('--strategy', choices=('recurrence', 'stationary'), default='stationary')
    p.add_argument('--backend', choices=('native', 'scipy'), default='native')
    p.add_argument('--threads', type=int, default=1)
    p.add_argument('--local-mode', choices=('dense', 'banded'), default='banded')
    p.add_argument('--cutoff', type=int, required=True)
    p.add_argument('--order', type=int, default=8)
    p.add_argument('--scheme', choices=('raw', 'consistent'), default='consistent')
    p.add_argument('--nz', type=int, default=10)
    p.add_argument('--repeats', type=int, default=1)
    p.add_argument('--profile', action='store_true')
    p.add_argument('--reference', type=Path, default=ROOT/'results/reference_coefficients_L14.json')
    p.add_argument('--native-cache', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.repeats < 1:
        raise ValueError('repeats must be positive')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(solver=args.solver, strategy=args.strategy, backend=args.backend,
                  threads=args.threads, cutoff=args.cutoff, order=args.order,
                  scheme=args.scheme, nz=args.nz, profile_enabled=args.profile,
                  local_mode=args.local_mode,
                  python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                  dtype=str(np.dtype(np.longdouble)),
                  precision_significand_bits=int(np.finfo(np.longdouble).nmant)+1,
                  source_sha256=source_hashes(),
                  affinity=sorted(os.sched_getaffinity(0)),
                  environment={key: os.environ.get(key) for key in
                    ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS',
                     'OMP_PROC_BIND','OMP_PLACES','NUMBA_CACHE_DIR','OMP_WAIT_POLICY','GOMP_SPINCOUNT')})
    before = time.perf_counter()
    if args.store:
        N, P, W, metadata = load_vertex_store(args.store)
        report['storage'] = 'readonly-mmap'
    else:
        with args.trusted_pickle.open('rb') as src:
            cache = pickle.load(src)
        N, P, W, metadata = cache['N'], cache['P'], cache['W'], cache['metadata']
        del cache
        report['storage'] = 'legacy-in-memory'
    report.update(load_seconds=time.perf_counter()-before, vertex_metadata=metadata,
                  rss_after_load_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    selected = None
    if args.solver == 'reference':
        from perturbative import solve_coefficients
        options = {}
    else:
        from optimized_solver import solve_coefficients
        selected = load_backend(args.backend, threads=args.threads, cache_dir=args.native_cache)
        options = dict(strategy=args.strategy,
                       spmm=selected.csr_spmm if selected.lib is not None else None,
                       threads=args.threads, local_mode=args.local_mode)
        report['native'] = selected.metadata
    samples = []
    for repeat in range(args.repeats):
        print(f"Starting {args.solver}/{args.strategy} L{args.cutoff} threads{args.threads}, repeat{repeat+1}",
              flush=True)
        profile = cProfile.Profile() if args.profile else None
        cpu_before = resource.getrusage(resource.RUSAGE_SELF)
        begin = time.perf_counter()
        if profile:
            profile.enable()
        result = solve_coefficients(N, P, W, args.cutoff, args.order, args.nz,
                                    args.scheme, np.longdouble, **options)
        if profile:
            profile.disable()
        wall = time.perf_counter()-begin
        after = resource.getrusage(resource.RUSAGE_SELF)
        cpu = after.ru_utime+after.ru_stime-cpu_before.ru_utime-cpu_before.ru_stime
        validation = validate_coefficients(result, args.reference) if args.reference else None
        samples.append(dict(wall_seconds=wall, cpu_seconds=cpu,
                            peak_rss_kib=after.ru_maxrss, validation=validation))
        print(json.dumps(samples[-1]), flush=True)
        if profile:
            name = args.output.with_suffix(f'.{repeat+1}.prof')
            profile.dump_stats(str(name))
            rows = []
            for key, item in pstats.Stats(profile).stats.items():
                primitive, calls, own, cumulative, callers = item
                rows.append(dict(file=key[0], line=key[1], function=key[2],
                                 calls=calls, self_seconds=own, cumulative_seconds=cumulative))
            report['top_self'] = sorted(rows,key=lambda r:r['self_seconds'],reverse=True)[:30]
            report['top_cumulative'] = sorted(rows,key=lambda r:r['cumulative_seconds'],reverse=True)[:40]
    report.update(samples=samples, median_wall_seconds=statistics.median(s['wall_seconds'] for s in samples),
                  peak_rss_kib=max(s['peak_rss_kib'] for s in samples), result=result)
    atomic_json(args.output, report)


if __name__ == '__main__':
    main()
