#!/usr/bin/env python3
"""Real MPI numerical checks for distributed sparse rows and the HT solver.

Run with mpiexec -n 2 or -n 4.  Fixtures exercise both floating types, native
prefix kernels, empty rank ownership, replicated seed rows, small collective
count limits, and physical L=4 coefficients through epsilon^8.  There are no
MPI floating-point reductions.  This test is intentionally small and is not
a statement about multi-node speedup.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import pickle
import sys

import numpy as np
from scipy.sparse import csr_matrix


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'code'))
sys.path.insert(0, str(ROOT/'vendor'))
from mpi_backend import DistributedSparseBackend, balanced_row_partition, shard_matrix, shard_vertices
from native_backend import load_backend
from optimized_solver import solve_coefficients


def error(a, b):
    a, b = np.asarray(a, dtype=np.longdouble), np.asarray(b, dtype=np.longdouble)
    return float(np.max(np.abs(a-b)/np.maximum(1, np.maximum(np.abs(a), np.abs(b))), initial=0))


def payload_values(result):
    values = list(result['C'])+list(result['r'])+list(result['g'])
    for group in ('energies_by_seed', 'vacuum_energies_by_subcutoff'):
        for key in sorted(result[group], key=int):
            values.extend(result[group][key])
    return np.asarray(values, dtype=np.longdouble)


def kernel_checks(comm, native):
    rows, rank, size = [], comm.Get_rank(), comm.Get_size()
    rng = np.random.default_rng(816023)
    for dtype in (np.float64, np.longdouble):
        T = np.dtype(dtype).type
        dense = rng.integers(-3, 4, size=(13, 13)).astype(dtype)
        dense = (dense+dense.T)/2
        dense[abs(dense) < 1] = 0
        dense[0, 0] = T(1) + np.ldexp(T(1), -60)
        matrix = csr_matrix(dense)
        bounds = balanced_row_partition(matrix, size)
        local = shard_matrix(matrix, *bounds[rank:rank+2])
        assert np.array_equal(local.getrow(0).toarray(), matrix.getrow(0).toarray())
        ownership = np.ones(matrix.shape[0], dtype=bool)
        ownership[bounds[rank]:bounds[rank+1]] = False
        ownership[0] = False
        assert local[ownership].nnz == 0
        mpi = DistributedSparseBackend(comm, bounds, native, dtype,
                                       max_collective_elements=8)
        for nb in (0, 1, 2, 5, 13):
            X = np.arange(nb*3, dtype=dtype).reshape(nb, 3)/T(17) + T(1)/13
            observed = mpi.csr_spmm(local, X, nrows=nb, ncols=nb)
            expected_native = native.csr_spmm(matrix, X, nrows=nb, ncols=nb)
            expected_scipy = matrix[:nb, :nb] @ X
            assert np.array_equal(observed, expected_native), (dtype, nb, rank)
            observed_error = error(observed, expected_scipy)
            assert observed_error < 2e-14, (dtype, nb, observed_error)
            rows.append({'dtype': str(np.dtype(dtype)), 'prefix': nb,
                         'native_bitwise_equal': True,
                         'max_scaled_error_vs_scipy': observed_error})
        assert mpi.collectives > mpi.calls
        assert mpi.metadata['floating_point_reductions'] is False
        # Check a nontrivial source prefix and more ranks than active rows.
        prefix = 2
        short_bounds = balanced_row_partition(matrix, size, nrows=prefix)
        tiny = shard_vertices([[matrix] for _ in range(4)], short_bounds, rank, nrows=prefix)[0][0]
        mpi_short = DistributedSparseBackend(comm, short_bounds, native, dtype,
                                             max_collective_elements=8)
        X = np.ones((prefix, 3), dtype=dtype)
        observed = mpi_short.csr_spmm(tiny, X, nrows=prefix, ncols=prefix)
        expected = native.csr_spmm(matrix, X, nrows=prefix, ncols=prefix)
        assert np.array_equal(observed, expected)
        rows.append({'dtype': str(np.dtype(dtype)), 'source_prefix_shard': prefix,
                     'native_bitwise_equal': True,
                     'empty_ranks': int(np.sum(np.diff(short_bounds) == 0))})
        if dtype == np.longdouble and np.finfo(dtype).nmant >= 60:
            sentinel = T(1) + np.ldexp(T(1), -60)
            one = csr_matrix(np.asarray([[sentinel]], dtype=dtype))
            one_bounds = balanced_row_partition(one, size)
            one_shard = shard_matrix(one, *one_bounds[rank:rank+2])
            mpi_one = DistributedSparseBackend(comm, one_bounds, native, dtype,
                                                max_collective_elements=1)
            transported = mpi_one.csr_spmm(one_shard, np.ones((1, 1), dtype=dtype),
                                           nrows=1, ncols=1)[0, 0]
            assert transported == sentinel and transported != T(float(transported))
            expected = np.asarray([sentinel, T(3)/7], dtype=dtype)
            current = expected.copy() if rank == 0 else np.zeros_like(expected)
            mpi_one.synchronize_coefficients(current)
            assert np.array_equal(current, expected)
            rows.append({'dtype': str(np.dtype(dtype)),
                         'sub_float64_spmm_signal_preserved': True,
                         'sub_float64_broadcast_signal_preserved': True,
                         'sentinel': str(sentinel)})
    return rows


def physical_checks(comm, native, cache):
    rank, size = comm.Get_rank(), comm.Get_size()
    if cache is None:
        from taylor_vertices import build_taylor_vertices
        N, P, W = build_taylor_vertices(4, degree=6, dtype=np.longdouble)
    else:
        with cache.open('rb') as f:
            data = pickle.load(f)
        assert data['cutoff'] >= 4 and data['degree'] >= 6
        N, P, W = data['N'], data['P'], data['W']
    nb = int(np.sum(N <= 4))
    bounds = balanced_row_partition(W[3][0], size, nrows=nb)
    local = shard_vertices(W, bounds, rank, nrows=nb)
    mpi = DistributedSparseBackend(comm, bounds, native, np.longdouble)
    spec = importlib.util.spec_from_file_location('frozen_reference', ROOT/'reference'/'perturbative.py')
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    trials = []
    for mode in ('raw', 'consistent'):
        reference_result = reference.solve_coefficients(N, P, W, 4, mode=mode) if rank == 0 else None
        reference_result = comm.bcast(reference_result, root=0)
        for strategy in ('recurrence', 'stationary'):
            paths = ('spmm', 'hamiltonian') if mode == 'raw' and strategy == 'recurrence' else ('hamiltonian',)
            for path in paths:
                fused = path == 'hamiltonian'
                prior_collectives = mpi.collectives
                observed = solve_coefficients(N[:nb], P[:nb], local, 4,
                    mode=mode, strategy=strategy, spmm=mpi.csr_spmm, distributed=True,
                    synchronize_coefficients=mpi.synchronize_coefficients,
                    hamiltonian_apply=mpi.apply_hamiltonian if fused else None)
                observed_error = error(payload_values(observed), payload_values(reference_result))
                assert observed_error < 5e-13, (mode, strategy, path, rank, observed_error)
                # Compare decimal strings: floating types and their padding bits
                # are not converted or reduced to perform this equality check.
                signature = {key: observed[key] for key in ('C', 'r', 'g',
                             'energies_by_seed', 'vacuum_energies_by_subcutoff')}
                signatures = comm.allgather(signature)
                assert all(other == signature for other in signatures)
                counters = observed['optimization']['counters']
                collective_count = mpi.collectives-prior_collectives
                expected_count = counters['full_applications'] if fused else counters['sparse_products']
                assert collective_count == expected_count
                trials.append({'cutoff': 4, 'scheme': mode, 'strategy': strategy,
                               'operator_path': path, 'collectives': collective_count,
                               'all_rank_results_identical': True,
                               'max_scaled_error_vs_reference': observed_error,
                               'optimization': observed['optimization']})
                if rank == 0:
                    print(json.dumps({'phase': 'physical', 'scheme': mode,
                                      'strategy': strategy, 'path': path,
                                      'passed': True}), flush=True)
    counts = comm.allgather((mpi.calls, mpi.hamiltonian_calls, mpi.collectives, mpi.sparse_kernels))
    assert all(record == counts[0] for record in counts)
    return trials, mpi.diagnostics()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trusted-cache', type=Path, help='Only a locally generated trusted pickle')
    p.add_argument('--native-cache', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    try:
        native = load_backend('native', threads=1, cache_dir=args.native_cache)
        kernels = kernel_checks(comm, native)
        if comm.Get_rank() == 0:
            print(json.dumps({'phase': 'kernels', 'passed': True,
                              'cases': len(kernels)}), flush=True)
        physical, diagnostics = physical_checks(comm, native, args.trusted_cache)
        if comm.Get_rank() == 0:
            report = {'passed': True, 'ranks': comm.Get_size(),
                      'kernel_checks': kernels, 'physical_checks': physical,
                      'mpi_diagnostics': diagnostics,
                      'scope': 'Local real-MPI correctness and chunking; not multi-node performance'}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2)+'\n')
            print(json.dumps({'passed': True, 'ranks': comm.Get_size(),
                              'kernel_cases': len(kernels), 'physical_cases': len(physical),
                              'max_scaled_error_vs_reference': max(row['max_scaled_error_vs_reference'] for row in physical)}), flush=True)
    except Exception:
        import traceback
        traceback.print_exc()
        comm.Abort(1)
        raise


if __name__ == '__main__':
    main()
