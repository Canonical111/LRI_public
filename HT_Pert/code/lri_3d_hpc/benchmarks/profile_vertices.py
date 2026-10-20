"""Measure optimized Taylor builds and compare against a trusted local cache."""
from pathlib import Path
import argparse
import cProfile
import json
import os
import pickle
import platform
import pstats
import resource
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code'))
sys.path.insert(0, str(ROOT / 'vendor'))
from taylor_vertices import build_taylor_vertices


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cutoff', type=int, default=14)
    p.add_argument('--degree', type=int, default=6)
    p.add_argument('--store', type=Path)
    p.add_argument('--spill', type=Path)
    p.add_argument('--reference-cache', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--no-profile', action='store_true')
    p.add_argument('--no-layout-cache', action='store_true')
    args = p.parse_args()
    report = dict(cutoff=args.cutoff, degree=args.degree,
                  mode='stream' if args.store else 'memory',
                  profiled=not args.no_profile, numpy=np.__version__,
                  python=platform.python_version(),
                  cpu_affinity=sorted(os.sched_getaffinity(0)),
                  precision_significand_bits=np.finfo(np.longdouble).nmant + 1,
                  environment_threads={k: os.environ.get(k) for k in
                                       ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'NUMBA_NUM_THREADS']})
    profiler = cProfile.Profile()
    started = time.perf_counter()
    start_usage = resource.getrusage(resource.RUSAGE_SELF)
    if not args.no_profile:
        profiler.enable()
    N, P, W, metadata = build_taylor_vertices(args.cutoff, args.degree, dtype=np.longdouble,
                                              return_metadata=True, store_path=args.store,
                                              spill_path=args.spill,
                                              cache_layouts=not args.no_layout_cache)
    if not args.no_profile:
        profiler.disable()
    report['wall_seconds'] = time.perf_counter() - started
    usage = resource.getrusage(resource.RUSAGE_SELF)
    report['build_cpu_seconds'] = (usage.ru_utime + usage.ru_stime -
                                    start_usage.ru_utime - start_usage.ru_stime)
    report['process_cpu_seconds'] = usage.ru_utime + usage.ru_stime
    report['build_peak_rss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report['vertex_metadata'] = metadata
    if not args.no_profile:
        stats = pstats.Stats(profiler)
        rows = [dict(file=k[0], line=k[1], function=k[2], primitive_calls=v[0],
                      total_calls=v[1], self_seconds=v[2], cumulative_seconds=v[3])
                for k, v in stats.stats.items()]
        report['top_cumulative'] = sorted(rows, key=lambda r: r['cumulative_seconds'], reverse=True)[:40]
        report['top_self'] = sorted(rows, key=lambda r: r['self_seconds'], reverse=True)[:25]
        stats.dump_stats(str(args.output.with_suffix('.prof')))
    if args.reference_cache is not None:
        with args.reference_cache.open('rb') as source:
            ref = pickle.load(source)
        if not (np.array_equal(N, ref['N']) and np.array_equal(P, ref['P'])):
            raise RuntimeError('Basis arrays do not match reference')
        checks = []
        for k, (series, old) in enumerate(zip(W, ref['W']), 1):
            for r, (a, b) in enumerate(zip(series, old)):
                d = a - b
                error = float(np.max(np.abs(d.data), initial=0))
                scale = max(1.0, float(np.max(np.abs(b.data), initial=0)))
                checks.append(dict(k=k, r=r, max_absolute_error=error,
                                   max_scaled_error=error/scale,
                                   values_identical=error == 0,
                                   indices_identical=np.array_equal(a.indices, b.indices),
                                   indptr_identical=np.array_equal(a.indptr, b.indptr)))
        report['reference_checks'] = checks
        report['max_scaled_vertex_error'] = max(c['max_scaled_error'] for c in checks)
        report['reference_comparison_peak_rss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=lambda v: v.item()) + '\n')
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ['vertex_metadata', 'top_self', 'top_cumulative', 'reference_checks']}, indent=2))


if __name__ == '__main__':
    main()
