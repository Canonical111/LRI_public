"""Analytic epsilon-Taylor vertices for the supplied spherical HT regulator.

The generalized-free field dimension is x=(3-epsilon)/4.  Coefficients are
ordinary Taylor coefficients (the nth derivative divided by n!), not numerical
finite differences.  SO(3) projectors and the north-pole trace are reused from
the supplied ht3d package; only the analytic mode-amplitude algebra is new.

Set PYTHONPATH to the original archive's ``code`` directory before importing.
No source file from that archive is modified by this module.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
from scipy.sparse import csc_matrix, coo_matrix, csr_matrix
from numba import njit


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
                          return_metadata=False):
    """Return ``N, P, Ws`` for the exact spin-0 inversion-even bath.

    ``Ws[k-1][r]`` is [eps^r] int dOmega/(4pi) :X^k:, k=1..4.
    The basis is fixed at the requested *bath level* cutoff; no energy-dependent
    selection or particle-number approximation is introduced.  Float64 angular
    projectors are promoted to dtype; their original rounding is not undone.

    If return_metadata is True an additional dictionary records timings, sizes,
    projector diagnostics, and explicitly states the retained source precision.
    """
    from ht3d.basis import SphereBathBasis

    if int(cutoff) != cutoff or cutoff < 0 or int(degree) != degree or degree < 0:
        raise ValueError('Require nonnegative integer cutoff and degree')
    degree, cutoff = int(degree), int(cutoff)
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

    def images(p):
        """[number annihilated][Taylor degree], preserving external columns."""
        if p not in images_cache:
            zero = csc_matrix(blocks[p].shape, dtype=dtype)
            arr = [[blocks[p]] + [zero] * degree]
            for k in range(1, 5):
                if k > p:
                    arr.append([zero] * (degree + 1))
                    continue
                row = []
                for r in range(degree + 1):
                    value = None
                    for a in range(r + 1):
                        product = annihilator[a] @ arr[-1][r - a]
                        value = product if value is None else value + product
                    row.append(canonical(value).tocsc())
                arr.append(row)
            images_cache[p] = arr
        return images_cache[p]

    coords = [[([], [], []) for _ in range(degree + 1)] for _ in range(4)]
    for pb in sorted(by_particle):
        for old in list(images_cache):
            if old < pb:
                del images_cache[old]
        ar = images(pb)
        for diff in range(5):
            pa = pb + diff
            if pa not in by_particle:
                continue
            al = images(pa)
            for k in range(1, 5):
                if diff > k or (diff + k) % 2:
                    continue
                j = (diff + k) // 2
                multiplier = math.comb(k, j)
                for r in range(degree + 1):
                    value = None
                    for a in range(r + 1):
                        product = al[j][a].T @ ar[k - j][r - a]
                        value = product if value is None else value + product
                    value = canonical(value * multiplier).tocoo()
                    if not value.nnz:
                        continue
                    rows = by_particle[pa][value.row]
                    cols = by_particle[pb][value.col]
                    rr, cc, dd = coords[k - 1][r]
                    rr.append(rows)
                    cc.append(cols)
                    dd.append(value.data)
                    if pa != pb:
                        rr.append(cols)
                        cc.append(rows)
                        dd.append(value.data)
    matrices = []
    for by_order in coords:
        series = []
        for rr, cc, dd in by_order:
            if rr:
                W = canonical(coo_matrix((np.concatenate(dd),
                              (np.concatenate(rr), np.concatenate(cc))),
                              shape=(nB, nB)))
                # Same Hermitian averaging as ProductOperator; no small entry
                # is clipped.  This removes only roundoff antisymmetry.
                W = canonical((W + W.T) * np.dtype(dtype).type(.5))
            else:
                W = csr_matrix((nB, nB), dtype=dtype)
            series.append(W)
        matrices.append(series)
    metadata = {
        'cutoff': cutoff, 'degree': degree, 'field_dimension': '(3-epsilon)/4',
        'series_convention': 'ordinary Taylor coefficients, derivative/factorial',
        'dtype': np.dtype(dtype).name, 'projector_source_dtype': 'float64',
        'full_bath_states': len(basis.N), 'magnetic_zero_states': len(selected),
        'scalar_bath_states': nB, 'bath_graph_array_bytes': basis.nbytes,
        'vertex_array_bytes': sum(W.data.nbytes + W.indices.nbytes + W.indptr.nbytes
                                  for series in matrices for W in series),
        'vertex_nnz': [[W.nnz for W in series] for series in matrices],
        'basis_seconds': t_basis, 'projector_seconds': t_projector,
        'vertex_seconds': time.perf_counter() - started_vertices,
        'projector_diagnostics': diagnostics,
    }
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
    args = parser.parse_args()
    if args.check:
        result = check_vertices(args.cutoff, args.degree)
    else:
        _, _, _, result = build_taylor_vertices(args.cutoff, args.degree,
                                               return_metadata=True)
    rendered = json.dumps(result, indent=2, default=lambda x: x.item())
    if args.output:
        Path(args.output).write_text(rendered + '\n')
    print(rendered)


if __name__ == '__main__':
    main()
