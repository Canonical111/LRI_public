"""Analytic epsilon-Taylor vertices for the supplied spherical HT regulator.

The generalized-free field dimension is x=(3-epsilon)/4.  Coefficients are
ordinary Taylor coefficients (the nth derivative divided by n!), not numerical
finite differences.  SO(3) projectors and the north-pole trace are reused from
the supplied ht3d package; only the analytic mode-amplitude algebra is new.

The package's vendor directory contains the unchanged original ht3d modules.
No source file from that archive is modified by this module.
"""
from __future__ import annotations

import argparse
import json
import math
import time
import tempfile
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import csc_matrix, coo_matrix, csr_matrix
from numba import njit

_VENDOR = Path(__file__).resolve().parents[1] / 'vendor'
if (_VENDOR / 'ht3d').is_dir():
    sys.path.insert(0, str(_VENDOR))


class _Coordinates:
    """Append-only matrix coordinates, optionally backed by scratch files.

    The disk mode retains only one particle-pair block in Python memory while
    contractions are computed.  Final CSR construction reads one matrix's
    coordinates at a time.  Files are raw temporary arrays, never user caches.
    """
    def __init__(self, degree, n, dtype, folder=None):
        self.degree, self.n, self.dtype = degree, n, np.dtype(dtype)
        self.index_dtype = np.dtype(np.int32 if n < 2**31 else np.int64)
        self.folder = None if folder is None else Path(folder)
        self.records = {}
        for k in range(4):
            for r in range(degree + 1):
                if self.folder is None:
                    self.records[k, r] = [[], [], []]
                else:
                    self.records[k, r] = dict(count=0, files=[
                        (self.folder / f'coord-{k}-{r}-{axis}.bin').open('xb')
                        for axis in ('row', 'col', 'data')])

    def append(self, k, r, rows, cols, data):
        if self.folder is None:
            record = self.records[k, r]
            for out, a in zip(record, (rows, cols, data)):
                out.append(a)
        else:
            record = self.records[k, r]
            for out, a, dtype in zip(record['files'], (rows, cols, data),
                                      (self.index_dtype, self.index_dtype, self.dtype)):
                out.write(memoryview(np.ascontiguousarray(a, dtype=dtype)).cast('B'))
            record['count'] += len(data)

    def take(self, k, r):
        record = self.records.pop((k, r))
        if self.folder is None:
            rr, cc, dd = record
            if not rr:
                return None
            return np.concatenate(rr), np.concatenate(cc), np.concatenate(dd)
        files, count = record['files'], record['count']
        for out in files:
            out.close()
        if not count:
            return None
        return tuple(np.memmap(out.name, mode='r', dtype=dtype, shape=(count,))
                     for out, dtype in zip(files, (self.index_dtype, self.index_dtype,
                                                   self.dtype)))

    def close(self):
        if self.folder is not None:
            for record in self.records.values():
                for out in record['files']:
                    out.close()


def _sum_products(left, right, degree, transpose_left=False, counts=None):
    """Ordered Taylor convolution, skipping structurally exact zero factors."""
    value = None
    for a in range(degree + 1):
        A, B = left[a], right[degree - a]
        if not A.nnz or not B.nnz:
            if counts is not None:
                counts['zero_sparse_products_skipped'] += 1
            continue
        product = (A.T if transpose_left else A) @ B
        if counts is not None:
            counts['sparse_products_executed'] += 1
        value = product if value is None else value + product
    if value is None:
        shape = (left[0].shape[1] if transpose_left else left[0].shape[0],
                 right[0].shape[1])
        return csr_matrix(shape, dtype=np.result_type(left[0].dtype, right[0].dtype))
    return value


def _sparse_array_bytes_unique(series):
    """Array footprint of sparse layouts, counting shared zero buffers once."""
    seen = set()
    total = 0
    for matrices in series:
        for W in matrices:
            for a in (W.data, W.indices, W.indptr):
                key = (int(a.__array_interface__['data'][0]), a.nbytes)
                if key not in seen:
                    seen.add(key)
                    total += a.nbytes
    return total


def canonical(a):
    a = a.tocsr()
    a.sum_duplicates()
    a.sort_indices()
    a.eliminate_zeros()
    return a


def amplitude_taylor(n, ell, degree=7, dtype=np.longdouble):
    """u_(n,ell)((3-eps)/4), evaluated by log-series recurrences.

    u^2 = (x)_(n+ell) (x-1/2)_n / (n! (3/2)_(n+ell)).
    All factors remain positive at eps=0, so this expansion has a well-defined
    positive square-root branch.  Log coefficients are finite rational sums.
    """
    n, ell, degree = int(n), int(ell), int(degree)
    if min(n, ell, degree) < 0:
        raise ValueError('Require n, ell, degree >= 0')
    T = np.dtype(dtype).type
    x = T(3) / 4
    u2 = T(1)
    for j in range(n + ell):
        u2 *= (x + j) / (T(3) / 2 + j)
    for j in range(n):
        u2 *= (x - T(1) / 2 + j) / (j + 1)
    out = np.zeros(degree + 1, dtype=dtype)
    logs = np.zeros(degree + 1, dtype=dtype)
    out[0] = np.sqrt(u2)
    for k in range(1, degree + 1):
        total = sum(((x + j) ** (-k) for j in range(n + ell)), T(0))
        total += sum(((x - T(1) / 2 + j) ** (-k) for j in range(n)), T(0))
        logs[k] = -total / (T(2 * k) * T(4) ** k)
        out[k] = sum((T(j) * logs[j] * out[k - j]
                      for j in range(1, k + 1)), T(0)) / k
    return out


@njit(cache=True)
def _pole_pattern(selected, lookup, ptr, parents, modes, sqocc, mode_m):
    """North-pole creation edges, with amplitudes left unevaluated."""
    rowptr = np.zeros(len(selected) + 1, np.int64)
    for i in range(len(selected)):
        row = selected[i]
        count = 0
        for edge in range(ptr[row], ptr[row + 1]):
            if mode_m[modes[edge]] == 0:
                count += 1
        rowptr[i + 1] = rowptr[i] + count
    indices = np.empty(rowptr[-1], np.int64)
    edge_modes = np.empty(rowptr[-1], np.int64)
    edge_sqocc = np.empty(rowptr[-1], np.float64)
    for i in range(len(selected)):
        row, q = selected[i], rowptr[i]
        for edge in range(ptr[row], ptr[row + 1]):
            mode = modes[edge]
            if mode_m[mode] == 0:
                indices[q] = lookup[parents[edge]]
                if indices[q] < 0:
                    raise ValueError('m=0 annihilator left magnetic-zero sector')
                edge_modes[q] = mode
                edge_sqocc[q] = sqocc[edge]
                q += 1
    return rowptr, indices, edge_modes, edge_sqocc


def build_taylor_vertices(cutoff, degree=7, dtype=np.longdouble, basis=None,
                          max_states=2_000_000, max_bytes=2 * 1024**3,
                          return_metadata=False, *, store_path=None,
                          spill_path=None, cache_layouts=True):
    """Return ``N, P, Ws`` for the exact spin-0 inversion-even bath.

    ``Ws[k-1][r]`` is [eps^r] int dOmega/(4pi) :X^k:, k=1..4.
    The basis is fixed at the requested *bath level* cutoff; no energy-dependent
    selection or particle-number approximation is introduced.  Float64 angular
    projectors are promoted to dtype; their original rounding is not undone.

    If return_metadata is True an additional dictionary records timings, sizes,
    projector diagnostics, and explicitly states the retained source precision.

    ``store_path`` streams coordinates through temporary disk arrays and writes
    a validated mmap store one CSR matrix at a time.  The returned matrices are
    read-only mappings.  ``spill_path`` selects scratch storage for coordinates;
    with no store_path it can also reduce temporary RAM during an in-memory
    build.  Both paths are explicit: existing final stores are never overwritten.

    ``cache_layouts=False`` selects the smallest image-layout footprint.  The
    default caches CSR right operands for annihilation layers 0..2 only, avoiding
    repeated CSC-to-CSR conversion in identical sparse products.  It changes no
    arithmetic or summation order.  The extra cached array bytes are reported.
    """
    from ht3d.basis import SphereBathBasis

    if int(cutoff) != cutoff or cutoff < 0 or int(degree) != degree or degree < 0:
        raise ValueError('Require nonnegative integer cutoff and degree')
    degree, cutoff = int(degree), int(cutoff)
    if store_path is not None and Path(store_path).exists():
        raise FileExistsError(store_path)
    started = time.perf_counter()
    if basis is None:
        basis = SphereBathBasis.build(cutoff, max_states=max_states,
                                      max_bytes=max_bytes)
    elif basis.cutoff != cutoff:
        raise ValueError('Basis cutoff mismatch')
    t_basis = time.perf_counter() - started
    started_projector = time.perf_counter()
    S, N, P, keep, diagnostics = basis.highest_weight(0, 0)
    t_projector = time.perf_counter() - started_projector
    started_vertices = time.perf_counter()
    nB = len(N)
    selected = np.flatnonzero(basis.M == 0)
    lookup = np.full(len(basis.N), -1, np.int64)
    lookup[selected] = np.arange(len(selected))
    labels = np.asarray(basis.labels, dtype=np.int64).reshape(-1, 3)
    coefficients = np.empty((degree + 1, len(labels)), dtype=dtype)
    cache = {}
    for mode, (n, ell, m) in enumerate(labels):
        if (int(n), int(ell)) not in cache:
            cache[int(n), int(ell)] = amplitude_taylor(n, ell, degree, dtype)
        coefficients[:, mode] = (cache[int(n), int(ell)] *
                                  np.sqrt(np.dtype(dtype).type(2 * ell + 1)))
    ptr, ix, modes, sqocc = _pole_pattern(
        selected, lookup, basis.ptr, basis.parents, basis.modes, basis.sqocc,
        labels[:, 2])
    # Recompute sqrt(occupation) in the requested precision.  Occupations are
    # exact small integers; the archive stores their square roots in float64.
    occupations = np.rint(sqocc * sqocc).astype(np.int64)
    precise_sqocc = np.sqrt(occupations.astype(dtype))
    shape = (len(selected), len(selected))
    annihilator = [canonical(csr_matrix(
        (precise_sqocc * coefficients[r, modes], ix, ptr), shape=shape).T)
        for r in range(degree + 1)]
    smallS = S[selected].astype(dtype).tocsc()
    by_particle = {int(p): np.flatnonzero(P == p) for p in np.unique(P)}
    blocks = {p: smallS[:, rows] for p, rows in by_particle.items()}
    images_cache = {}
    counts = {'zero_sparse_products_skipped': 0, 'sparse_products_executed': 0,
              'layout_cache_array_bytes_peak': 0}

    def images(p):
        """[number annihilated][Taylor degree], preserving external columns."""
        if p not in images_cache:
            zero = csc_matrix(blocks[p].shape, dtype=dtype)
            arr = [[blocks[p]] + [zero] * degree]
            right = [None, None, None] if cache_layouts else arr
            if cache_layouts:
                # Exact zeros are skipped before multiplication; retaining
                # their compact CSC layout avoids a full-height CSR rowptr.
                zero_csr = zero
                previous = [blocks[p].tocsr()] + [zero_csr] * degree
                right[0] = previous
            else:
                previous = arr[0]
            for k in range(1, 5):
                if k > p:
                    arr.append([zero] * (degree + 1))
                    if cache_layouts and k <= 2:
                        right[k] = [zero_csr] * (degree + 1)
                    continue
                row = []
                row_csr = []
                for r in range(degree + 1):
                    value = canonical(_sum_products(annihilator, previous, r, counts=counts))
                    row.append(value.tocsc())
                    if cache_layouts:
                        row_csr.append(value)
                arr.append(row)
                previous = row_csr if cache_layouts else row
                if cache_layouts and k <= 2:
                    right[k] = row_csr
            images_cache[p] = (arr, right)
            if cache_layouts:
                footprint = _sparse_array_bytes_unique(
                    rows for _, layouts in images_cache.values() for rows in layouts)
                counts['layout_cache_array_bytes_peak'] = max(
                    counts['layout_cache_array_bytes_peak'], footprint)
        return images_cache[p]

    spill = None
    if store_path is not None or spill_path is not None:
        if spill_path is not None:
            Path(spill_path).mkdir(parents=True, exist_ok=True)
        spill = tempfile.TemporaryDirectory(prefix='ht3d-coordinates-', dir=spill_path)
    coords = _Coordinates(degree, nB, dtype, folder=None if spill is None else spill.name)
    for pb in sorted(by_particle):
        for old in list(images_cache):
            if old < pb:
                del images_cache[old]
        ar, ar_right = images(pb)
        for diff in range(5):
            pa = pb + diff
            if pa not in by_particle:
                continue
            al, al_right = images(pa)
            for k in range(1, 5):
                if diff > k or (diff + k) % 2:
                    continue
                j = (diff + k) // 2
                multiplier = math.comb(k, j)
                for r in range(degree + 1):
                    value = _sum_products(al[j], ar_right[k - j], r,
                                          transpose_left=True, counts=counts)
                    value = canonical(value * multiplier).tocoo()
                    if not value.nnz:
                        continue
                    rows = by_particle[pa][value.row]
                    cols = by_particle[pb][value.col]
                    coords.append(k - 1, r, rows, cols, value.data)
                    if pa != pb:
                        coords.append(k - 1, r, cols, rows, value.data)
    # These large intermediates are no longer needed during final CSR assembly.
    # A basis supplied by the caller is still owned by that caller, unchanged.
    full_states, graph_bytes = len(basis.N), basis.nbytes
    del ar, ar_right, al, al_right
    images_cache.clear()
    blocks.clear()
    del smallS, S, annihilator, lookup, ptr, ix, modes, sqocc, basis
    writer = None
    if store_path is not None:
        from vertex_store import VertexStoreWriter
        writer = VertexStoreWriter(store_path, N, P, cutoff, degree, dtype)
    matrices = []
    vertex_nnz = []
    vertex_array_bytes = 0
    for k in range(4):
        series = []
        nnz = []
        for r in range(degree + 1):
            arrays = coords.take(k, r)
            if arrays is not None:
                rr, cc, dd = arrays
                W = canonical(coo_matrix((dd, (rr, cc)),
                              shape=(nB, nB)))
                # Same Hermitian averaging as ProductOperator; no small entry
                # is clipped.  This removes only roundoff antisymmetry.
                W = canonical((W + W.T) * np.dtype(dtype).type(.5))
            else:
                W = csr_matrix((nB, nB), dtype=dtype)
            if arrays is not None:
                del rr, cc, dd
            nnz.append(W.nnz)
            vertex_array_bytes += W.data.nbytes + W.indices.nbytes + W.indptr.nbytes
            if writer is not None:
                writer.add(k + 1, r, W)
                del W
            else:
                series.append(W)
            del arrays
        vertex_nnz.append(nnz)
        matrices.append(series)
    coords.close()
    if spill is not None:
        spill.cleanup()
    metadata = {
        'cutoff': cutoff, 'degree': degree, 'field_dimension': '(3-epsilon)/4',
        'series_convention': 'ordinary Taylor coefficients, derivative/factorial',
        'dtype': np.dtype(dtype).name, 'projector_source_dtype': 'float64',
        'full_bath_states': full_states, 'magnetic_zero_states': len(selected),
        'scalar_bath_states': nB, 'bath_graph_array_bytes': graph_bytes,
        'vertex_array_bytes': vertex_array_bytes, 'vertex_nnz': vertex_nnz,
        'basis_seconds': t_basis, 'projector_seconds': t_projector,
        'vertex_seconds': time.perf_counter() - started_vertices,
        'projector_diagnostics': diagnostics,
        'coordinate_storage': 'scratch files' if spill is not None else 'memory',
        'cache_layouts': bool(cache_layouts),
        **counts,
    }
    if writer is not None:
        writer.finish(metadata)
        from vertex_store import load_vertex_store
        return_data = load_vertex_store(store_path, verify=False)
        return return_data if return_metadata else return_data[:3]
    out = (np.asarray(N), np.asarray(P), matrices)
    return out + (metadata,) if return_metadata else out


def check_vertices(cutoff=4, degree=7):
    """Independent fixed-x construction checks, with no spectral targets."""
    from ht3d.basis import SphereBathBasis
    from ht3d.operators import ProductOperator
    basis = SphereBathBasis.build(cutoff)
    N, P, W, metadata = build_taylor_vertices(
        cutoff, degree, basis=basis, return_metadata=True)
    checks = []
    for eps in (0., .16, .08, .04, .02):
        op = ProductOperator(basis, .75 - eps / 4, nz=2)
        errs = []
        for k in range(4):
            predicted = W[k][-1]
            for j in range(degree - 1, -1, -1):
                predicted = predicted * np.longdouble(eps) + W[k][j]
            difference = predicted - op.W[k].astype(np.longdouble)
            scale = max(1., float(np.max(np.abs(op.W[k].data), initial=0.)))
            errs.append(float(np.max(np.abs(difference.data), initial=0.)) / scale)
        checks.append({'epsilon': eps, 'max_scaled_errors_by_vertex': errs})
    metadata['checks'] = checks
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cutoff', type=int, default=4)
    parser.add_argument('--degree', type=int, default=7)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output')
    parser.add_argument('--store', help='New .npy CSR store directory; enables coordinate spilling')
    parser.add_argument('--spill', help='Scratch directory for temporary coordinate files')
    parser.add_argument('--max-states', type=int, default=2_000_000)
    parser.add_argument('--max-bytes', type=int, default=2 * 1024**3)
    parser.add_argument('--no-layout-cache', action='store_true',
                        help='Use less image-layout memory, with repeated sparse conversions')
    args = parser.parse_args()
    if args.check:
        result = check_vertices(args.cutoff, args.degree)
    else:
        _, _, _, result = build_taylor_vertices(args.cutoff, args.degree,
                                               return_metadata=True,
                                               store_path=args.store, spill_path=args.spill,
                                               max_states=args.max_states, max_bytes=args.max_bytes,
                                               cache_layouts=not args.no_layout_cache)
    rendered = json.dumps(result, indent=2, default=lambda x: x.item())
    if args.output:
        Path(args.output).write_text(rendered + '\n')
    print(rendered)


if __name__ == '__main__':
    main()
