"""Measure baseline stage times, peak RSS and Python/native call costs."""
from pathlib import Path
import argparse
import cProfile
import hashlib
import io
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
sys.path.insert(0, str(ROOT / "reference"))
sys.path.insert(0, str(ROOT / "vendor"))
from perturbative import solve_coefficients
from taylor_vertices import build_taylor_vertices


def main():
    p = argparse.ArgumentParser()
    p.add_argument("phase", choices=["build", "solve"])
    p.add_argument("--cutoff", type=int, default=14)
    p.add_argument("--order", type=int, default=8)
    p.add_argument("--scheme", choices=["raw", "consistent"], default="consistent")
    p.add_argument("--cache", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.parent.mkdir(exist_ok=True, parents=True)
    report = {"phase": args.phase, "cutoff": args.cutoff, "order": args.order,
              "scheme": args.scheme, "numpy": np.__version__, "python": platform.python_version(),
              "cpu_affinity": sorted(os.sched_getaffinity(0)), "dtype": np.dtype(np.longdouble).name,
              "precision_significand_bits": int(np.finfo(np.longdouble).nmant + 1),
              "environment_threads": {k: os.environ.get(k) for k in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "NUMBA_NUM_THREADS"]}}
    started = time.perf_counter()
    if args.phase == "solve":
        if args.cache is None:
            raise ValueError("A trusted locally generated vertex cache is required")
        with args.cache.open("rb") as f:
            data = pickle.load(f)
        N, P, W = data["N"], data["P"], data["W"]
        report["cache_load_seconds"] = time.perf_counter() - started
        report["vertex_metadata"] = data["metadata"]
        report["rss_before_profile_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    profiler = cProfile.Profile()
    started = time.perf_counter()
    profiler.enable()
    if args.phase == "build":
        N, P, W, metadata = build_taylor_vertices(args.cutoff, degree=args.order - 2,
                                                 dtype=np.longdouble, return_metadata=True)
        report["vertex_metadata"] = metadata
    else:
        result = solve_coefficients(N, P, W, args.cutoff, args.order, mode=args.scheme,
                                    dtype=np.longdouble)
        report["coefficient_result"] = result
    profiler.disable()
    report["profiled_wall_seconds"] = time.perf_counter() - started
    report["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report["process_cpu_seconds"] = resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime
    stats = pstats.Stats(profiler)
    rows = []
    for key, item in stats.stats.items():
        primitive_calls, total_calls, self_time, cumulative_time, _ = item
        rows.append({"file": key[0], "line": key[1], "function": key[2], "primitive_calls": primitive_calls,
                     "total_calls": total_calls, "self_seconds": self_time, "cumulative_seconds": cumulative_time})
    report["top_cumulative"] = sorted(rows, key=lambda r: r["cumulative_seconds"], reverse=True)[:40]
    report["top_self"] = sorted(rows, key=lambda r: r["self_seconds"], reverse=True)[:25]
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    stats.dump_stats(str(args.output.with_suffix(".prof")))
    print(json.dumps({k: v for k, v in report.items() if k not in ["coefficient_result", "vertex_metadata", "top_cumulative", "top_self"]}, indent=2))
    for r in report["top_cumulative"][:15]:
        print(r["function"], "calls", r["total_calls"], "self", round(r["self_seconds"], 3), "cum", round(r["cumulative_seconds"], 3))


if __name__ == "__main__":
    main()
