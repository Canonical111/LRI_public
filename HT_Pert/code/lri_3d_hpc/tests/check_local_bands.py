#!/usr/bin/env python3
"""Check precision and optional physical equivalence of local band products."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'code'))
from optimized_solver import (normal_powers, make_local_bands,
                              apply_local_block, solve_coefficients)


def error(a, b):
    a, b = np.asarray(a, dtype=np.longdouble), np.asarray(b, dtype=np.longdouble)
    return float(np.max(np.abs(a-b)/np.maximum(1, np.maximum(np.abs(a), np.abs(b))), initial=0))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--store', type=Path, help='Optional verified physical store for complete coefficient comparisons')
    p.add_argument('--cutoff', type=int, default=10)
    p.add_argument('--native-cache', type=Path)
    p.add_argument('--benchmark', action='store_true', help='Record small local-product CPU timings')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    rng, records = np.random.default_rng(18062), []
    for dtype in (np.float64, np.longdouble):
        q = normal_powers(10, dtype)
        for rows in (0, 8, 127, 128, 2243):
            X = rng.normal(size=(rows, 10)).astype(dtype)
            X.flags.writeable = False
            for degree in range(5):
                for field in (0, 1):
                    pin = field ^ (degree % 2)
                    block = q[degree][field*10:(field+1)*10, pin*10:(pin+1)*10]
                    bands = make_local_bands(block)
                    dense = apply_local_block(X, block, bands, 'dense')
                    banded = apply_local_block(X, block, bands, 'banded')
                    observed = error(dense, banded)
                    assert observed < 5e-13
                    record = {'dtype': str(np.dtype(dtype)), 'rows': rows,
                              'degree': degree, 'field': field,
                              'max_scaled_error': observed,
                              'bitwise_equal_values': bool(np.array_equal(dense, banded))}
                    if args.benchmark and dtype == np.longdouble and rows == 2243 and field == 0:
                        medians = {}
                        for mode in ('dense', 'banded'):
                            samples = []
                            for _ in range(5):
                                start = time.process_time()
                                apply_local_block(X, block, bands, mode)
                                samples.append(time.process_time()-start)
                            medians[mode] = float(np.median(samples))
                        record['median_process_cpu_seconds'] = medians
                    records.append(record)
    physical = []
    if args.store is not None:
        from vertex_store import load_vertex_store
        from native_backend import load_backend
        N, P, W, metadata = load_vertex_store(args.store)
        if args.cutoff > metadata['cutoff']:
            raise ValueError('Requested physical cutoff is not covered by the store')
        backend = load_backend('native', threads=1, cache_dir=args.native_cache)
        for mode in ('raw', 'consistent'):
            a = solve_coefficients(N, P, W, args.cutoff, mode=mode,
                local_mode='dense', spmm=backend.csr_spmm, keep_states=True)
            b = solve_coefficients(N, P, W, args.cutoff, mode=mode,
                local_mode='banded', spmm=backend.csr_spmm, keep_states=True)
            errors = {key: error(a[0][key], b[0][key]) for key in ('C', 'r', 'g')}
            for key in ('energies_by_seed', 'vacuum_energies_by_subcutoff'):
                errors[key] = max(error(value, b[0][key][seed]) for seed, value in a[0][key].items())
            errors['wavefunctions'] = errors['windows'] = 0.0
            for states_a, states_b in ((a[2], b[2]), (a[3], b[3])):
                for seed, state in states_a.items():
                    for x, y in zip(state.psi, states_b[seed].psi):
                        errors['wavefunctions'] = max(errors['wavefunctions'], error(x, y))
                    for x, y in zip(state.windows, states_b[seed].windows):
                        errors['windows'] = max(errors['windows'], error(x, y))
            assert max(errors.values()) < 5e-13
            physical.append({'cutoff': args.cutoff, 'scheme': mode, 'max_scaled_errors': errors})
    report = {'passed': True, 'primitive_cases': records, 'physical_cases': physical,
              'primitive_max_scaled_error': max(row['max_scaled_error'] for row in records),
              'working_precision_unchanged': True,
              'timing_scope': 'Primitive CPU timings only; identity products may return a read-only view, so do not interpret their ratio as whole-solver speedup'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'passed': True, 'primitive_cases': len(records),
                      'physical_cases': len(physical),
                      'primitive_max_scaled_error': report['primitive_max_scaled_error']}))


if __name__ == '__main__':
    main()
