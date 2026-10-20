"""Replay the saved physical coefficient grid with the final optimized solver."""
from pathlib import Path
import argparse
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'code'), str(ROOT/'vendor')]
import numpy as np
from ht3d_coefficients import validate_coefficients, source_hashes
from native_backend import load_backend
from optimized_solver import solve_coefficients
from vertex_store import load_vertex_store, atomic_json, sha256_file


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--store', type=Path, required=True)
    p.add_argument('--reference', type=Path, default=ROOT/'results/reference_coefficients_L14.json')
    p.add_argument('--cutoffs', type=int, nargs='+', default=list(range(0, 15, 2)))
    p.add_argument('--schemes', choices=('raw', 'consistent'), nargs='+', default=['raw','consistent'])
    p.add_argument('--strategies', choices=('recurrence','stationary'), nargs='+', default=['stationary'])
    p.add_argument('--threads', type=int, default=1)
    p.add_argument('--backend', choices=('native','scipy'), default='native')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    N, P, W, metadata = load_vertex_store(args.store)
    if max(args.cutoffs) > metadata['cutoff']:
        raise ValueError('The vertex store does not cover the requested grid')
    backend = load_backend(args.backend, threads=args.threads)
    rows = []
    started = time.perf_counter()
    for cutoff in args.cutoffs:
        for mode in args.schemes:
            for strategy in args.strategies:
                result = solve_coefficients(N, P, W, cutoff, order=8, mode=mode,
                                             dtype=np.longdouble, strategy=strategy,
                                             spmm=backend.csr_spmm if backend.lib else None,
                                             threads=args.threads, local_mode='banded')
                check = validate_coefficients(result, args.reference)
                rows.append(dict(cutoff=cutoff, mode=mode, strategy=strategy,
                                 validation=check, result=result))
                print(json.dumps(dict(cutoff=cutoff, mode=mode, strategy=strategy,
                                      max_scaled_error=check['max_scaled_error'])), flush=True)
    report = dict(passed=True, cases=len(rows), source_sha256=source_hashes(),
                  reference_sha256=sha256_file(args.reference),
                  store_manifest_sha256=sha256_file(args.store/'manifest.json'),
                  precision_significand_bits=int(np.finfo(np.longdouble).nmant)+1,
                  max_scaled_error=str(max(np.longdouble(r['validation']['max_scaled_error'])
                                           for r in rows)),
                  coverage='C, r, g, all four primary energy series and every subcutoff vacuum',
                  wall_seconds=time.perf_counter()-started, backend=backend.metadata, rows=rows)
    atomic_json(args.output, report)


if __name__ == '__main__':
    main()
