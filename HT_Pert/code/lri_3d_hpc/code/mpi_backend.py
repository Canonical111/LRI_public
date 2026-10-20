"""MPI row distribution for the unchanged real Hermitian HT coefficient solver.

Sparse operator values are divided between ranks.  Wavefunction vectors and the
small energy/window series are replicated, and each sparse application gathers
disjoint output rows.  There is no floating-point MPI sum and no dtype conversion.
This is a memory-saving matrix distribution, not a fully distributed-vector
eigensolver.  Use job arrays for independent cutoffs when communication dominates.

mpi4py is optional: importing this module does not initialize MPI.
"""
from __future__ import annotations

import time
import weakref

import numpy as np
from scipy.sparse import csr_matrix
from optimized_solver import apply_local_block


def balanced_row_partition(matrix, nranks, nrows=None):
    """Contiguous rows balanced by the dominant vertex's nonzero count."""
    nrows = matrix.shape[0] if nrows is None else int(nrows)
    if int(nranks) != nranks or nranks < 1 or not 0 <= nrows <= matrix.shape[0]:
        raise ValueError('Invalid row-partition dimensions')
    # One extra unit per row gives empty rows nonzero scheduling weight.
    weights = np.diff(matrix.indptr[:nrows+1]).astype(np.int64) + 1
    cumulative = np.r_[np.int64(0), np.cumsum(weights, dtype=np.int64)]
    total = int(cumulative[-1])
    bounds = [0]
    for rank in range(1, int(nranks)):
        target = (total * rank) // int(nranks)
        bounds.append(int(np.searchsorted(cumulative, target, side='left')))
    bounds.append(nrows)
    return np.asarray(bounds, dtype=np.int64)


def _csr_from_buffers(data, indices, indptr, shape, sorted_indices):
    value = csr_matrix((data, indices, indptr), shape=shape, copy=False)
    # Keep the selected index width and avoid scipy's automatic narrowing copy.
    value.data, value.indices, value.indptr = data, indices, indptr
    value.has_sorted_indices = bool(sorted_indices)
    return value


def _rows_sorted(indices, ptr):
    """Whether every row of this CSR slice has nondecreasing column indices.

    Scans only the given rows, so a rank never reads index arrays it does not
    own (``has_sorted_indices`` on a full mmap-backed store scans all rows).
    """
    if len(indices) < 2:
        return True
    descending = np.diff(indices) < 0
    # A decrease is allowed only across a row boundary: position i compares
    # entries i and i+1, so the comparison before each interior row start is exempt.
    starts = np.asarray(ptr[1:-1], dtype=np.int64)
    starts = starts[(starts >= 1) & (starts < len(indices))]
    descending[starts-1] = False
    return not bool(descending.any())


def shard_matrix(matrix, lo, hi, nrows=None):
    """Global-shaped CSR with owned rows and the Hermitian seed row replicated.

    Row zero is necessary for scalar seed contractions and seed-column actions
    on every rank.  It is never counted twice by the collective sparse product.
    Input data may be a read-only mmap; only the owned values are copied.
    """
    nrows = matrix.shape[0] if nrows is None else int(nrows)
    lo, hi = int(lo), int(hi)
    if not (0 <= lo <= hi <= nrows <= matrix.shape[0]):
        raise ValueError('Invalid shard range')
    if matrix.shape[0] != matrix.shape[1] or matrix.format != 'csr':
        raise ValueError('Expected a square CSR matrix')
    dtype = matrix.indptr.dtype
    ptr = np.zeros(nrows+1, dtype=dtype)
    start, stop = int(matrix.indptr[lo]), int(matrix.indptr[hi])
    own_data, own_indices = matrix.data[start:stop], matrix.indices[start:stop]
    own_ptr = matrix.indptr[lo:hi+1] - start
    seed_end = int(matrix.indptr[1]) if nrows else 0
    seed_data, seed_indices = matrix.data[:seed_end], matrix.indices[:seed_end]
    sorted_indices = (_rows_sorted(own_indices, own_ptr) and
                      _rows_sorted(seed_indices, np.asarray([0, seed_end])))
    if nrows < matrix.shape[1]:
        # Slice only this rank's rows, so loading a larger store does not
        # transiently materialize a complete smaller-cutoff vertex on each rank.
        own = _csr_from_buffers(own_data, own_indices, own_ptr,
                                (hi-lo, matrix.shape[1]), sorted_indices)[:, :nrows]
        own_data, own_indices, own_ptr = own.data, own.indices, own.indptr
        keep = seed_indices < nrows
        seed_data, seed_indices = seed_data[keep], seed_indices[keep]
    own_count, seed_count = len(own_data), len(seed_data)
    if lo == 0 and hi > 0:
        data, indices = own_data.copy(), own_indices.copy()
        ptr[:hi+1] = own_ptr
        ptr[hi+1:] = own_count
    else:
        data = np.concatenate((seed_data, own_data))
        indices = np.concatenate((seed_indices, own_indices))
        if nrows:
            ptr[1:] = seed_count
        if hi > lo:
            ptr[lo:hi+1] = own_ptr + seed_count
            ptr[hi+1:] = seed_count + own_count
    return _csr_from_buffers(data, indices, ptr, (nrows, nrows), sorted_indices)


def shard_vertices(W, bounds, rank, nrows=None):
    lo, hi = map(int, bounds[int(rank):int(rank)+2])
    nrows = W[0][0].shape[0] if nrows is None else int(nrows)
    result = []
    patterns = {}
    for series in W:
        row = []
        for matrix in series:
            shard = shard_matrix(matrix, lo, hi, nrows)
            key = (id(matrix.indices), id(matrix.indptr))
            if key in patterns:
                shard.indices, shard.indptr = patterns[key]
            else:
                patterns[key] = (shard.indices, shard.indptr)
            row.append(shard)
        result.append(row)
    return result


class DistributedSparseBackend:
    """Collective prefix SpMM, returning the full product on every rank."""

    def __init__(self, comm, bounds, local_backend, dtype=np.longdouble,
                 *, max_collective_elements=2**31-1):
        from mpi4py import MPI
        self.comm, self.MPI = comm, MPI
        self.rank, self.size = comm.Get_rank(), comm.Get_size()
        self.bounds = np.asarray(bounds, dtype=np.int64)
        if (self.bounds.shape != (self.size+1,) or self.bounds[0] != 0 or
                np.any(np.diff(self.bounds) < 0)):
            raise ValueError('Invalid shared row partition')
        self.dtype = np.dtype(dtype)
        if self.dtype == np.dtype(np.longdouble):
            self.mpi_dtype = MPI.LONG_DOUBLE
        elif self.dtype == np.dtype(np.float64):
            self.mpi_dtype = MPI.DOUBLE
        else:
            raise TypeError('MPI solver supports float64 and longdouble only')
        f = np.finfo(self.dtype)
        fingerprint = (self.dtype.str, self.dtype.itemsize, int(f.nmant),
                       int(f.maxexp), self.mpi_dtype.Get_size(), self.mpi_dtype.Get_extent())
        records = self.comm.allgather(fingerprint)
        if any(record != fingerprint for record in records):
            raise ValueError('Ranks disagree on the real/MPI floating-point ABI')
        if (self.mpi_dtype.Get_size() != self.dtype.itemsize or
                self.mpi_dtype.Get_extent() != (0, self.dtype.itemsize)):
            raise ValueError('MPI real datatype does not match the NumPy buffer layout')
        self.local_backend = local_backend
        self.max_elements = int(max_collective_elements)
        if self.max_elements < 1:
            raise ValueError('max_collective_elements must be positive')
        self._views = {}
        self.calls = self.collectives = self.received_elements = 0
        self.hamiltonian_calls = self.sparse_kernels = 0
        self.kernel_seconds = self.gather_seconds = 0.0
        self.metadata = dict(backend='mpi-row-distributed', ranks=self.size,
                             row_bounds=self.bounds.tolist(),
                             precision_significand_bits=int(f.nmant)+1,
                             local_backend=local_backend.metadata,
                             vectors_replicated=True, seed_row_replicated=True,
                             floating_point_reductions=False,
                             mpi_library=MPI.Get_library_version().strip())

    def _row_view(self, matrix, nb):
        lo = min(int(self.bounds[self.rank]), nb)
        hi = min(int(self.bounds[self.rank+1]), nb)
        key = (id(matrix), nb)
        cached = self._views.get(key)
        if cached is not None and cached[0]() is matrix:
            return cached[1], lo, hi
        first, last = int(matrix.indptr[lo]), int(matrix.indptr[hi])
        ptr = matrix.indptr[lo:hi+1] - first
        view = _csr_from_buffers(matrix.data[first:last], matrix.indices[first:last],
                                 ptr, (hi-lo, matrix.shape[1]), matrix.has_sorted_indices)
        # Cache row views without extending the parent Hamiltonian's lifetime.
        reference = weakref.ref(matrix, lambda unused, key=key: self._views.pop(key, None))
        self._views[key] = (reference, view)
        return view, lo, hi

    def csr_spmm(self, matrix, X, *, nrows=None, ncols=None):
        nb = matrix.shape[0] if nrows is None else int(nrows)
        nc = X.shape[0] if ncols is None else int(ncols)
        if (nb != nc or not 0 <= nb <= int(self.bounds[-1]) or
                X.ndim != 2 or X.shape[0] != nc or X.dtype != self.dtype or
                matrix.dtype != self.dtype):
            raise ValueError('Collective SpMM requires matching real square-prefix inputs')
        width = X.shape[1]
        if width < 1 or width > self.max_elements:
            raise ValueError('Invalid right-hand-side width for the collective limit')
        view, lo, hi = self._row_view(matrix, nb)
        begin = time.perf_counter()
        local = self.local_backend.csr_spmm(view, X, nrows=hi-lo, ncols=nc)
        self.kernel_seconds += time.perf_counter()-begin
        self.sparse_kernels += 1
        self.calls += 1
        return self._gather_rows(local, nb, width, lo, hi)

    def _gather_rows(self, local, nb, width, lo, hi):
        result = np.empty((nb, width), dtype=self.dtype)
        begin = time.perf_counter()
        # Chunk by output rows so this also works with MPI implementations
        # whose vector collective counts and displacements are 32-bit integers.
        chunk_rows = max(1, self.max_elements // width)
        for first in range(0, nb, chunk_rows):
            last = min(nb, first+chunk_rows)
            starts = np.clip(self.bounds[:-1], first, last)
            stops = np.clip(self.bounds[1:], first, last)
            counts = ((stops-starts)*width).tolist()
            displacements = ((starts-first)*width).tolist()
            send_lo, send_hi = max(lo, first), min(hi, last)
            if send_hi > send_lo:
                send = local[send_lo-lo:send_hi-lo]
            else:
                send = local[:0]
            self.comm.Allgatherv([send, self.mpi_dtype],
                                [result[first:last], counts, displacements, self.mpi_dtype])
            self.collectives += 1
        self.gather_seconds += time.perf_counter()-begin
        self.received_elements += nb*width
        return result

    def apply_hamiltonian(self, n, X, state):
        """One gather for an entire Taylor Hamiltonian, not one per bath term.

        Each rank starts from the same local oscillator and free term as the
        serial solver, then adds sparse terms in the same order.  Only its owned
        rows are evaluated.  The scalar window is subsequently added by the
        shared SeedSeries.apply method.  This reduces both message count and
        vector traffic by roughly the number of nonzero bath terms.
        """
        bare, nb, width = state.bare, state.nb, state.bare.nz
        if (X.dtype != self.dtype or X.shape != (nb, width) or
                width < 1 or width > self.max_elements):
            raise ValueError('Invalid distributed Hamiltonian state buffer')
        terms = bare.terms.get(n)
        if terms is None:
            raise ValueError('Requested Hamiltonian has been released')
        lo = min(int(self.bounds[self.rank]), nb)
        hi = min(int(self.bounds[self.rank+1]), nb)
        begin = time.perf_counter()
        local = np.zeros((hi-lo, width), dtype=self.dtype)
        selected_rows = tuple(np.flatnonzero(state.P[lo:hi] % 2 == parity)
                              for parity in (0, 1))
        oscillator = bare.local[n]
        for bath_parity, selected in enumerate(selected_rows):
            field = state.field ^ bath_parity
            block = oscillator[field*width:(field+1)*width,
                               field*width:(field+1)*width]
            local[selected] += apply_local_block(X[lo:hi][selected], block,
                                                 bare.local_bands[n][field], bare.local_mode)
        if n == 1:
            local += state.free_first[lo:hi] * X[lo:hi]
        for bath_degree, local_degree, matrix in terms:
            view, unused_lo, unused_hi = self._row_view(matrix, nb)
            image = self.local_backend.csr_spmm(view, X, nrows=hi-lo, ncols=nb)
            self.sparse_kernels += 1
            if local_degree == 0:
                local += image
                continue
            for bath_parity, selected in enumerate(selected_rows):
                field = state.field ^ bath_parity
                input_parity = field ^ (bath_degree % 2)
                key = (local_degree, field, input_parity)
                local[selected] += apply_local_block(image[selected], bare.qblocks[key],
                                                     bare.qbands[key], bare.local_mode)
        self.kernel_seconds += time.perf_counter()-begin
        self.hamiltonian_calls += 1
        return self._gather_rows(local, nb, width, lo, hi)

    def diagnostics(self):
        return dict(self.metadata, sparse_calls=self.calls, collectives=self.collectives,
                    full_hamiltonian_calls=self.hamiltonian_calls,
                    local_sparse_kernels=self.sparse_kernels,
                    kernel_seconds=self.kernel_seconds, gather_seconds=self.gather_seconds,
                    gathered_elements_per_rank=self.received_elements)

    def synchronize_coefficients(self, values):
        """Keep coupling-zero decisions and the vacuum hierarchy identical.

        Rank zero supplies a few scalar series entries at each perturbative
        order.  This is a direct real-buffer broadcast, never a reduction.
        """
        if values.dtype != self.dtype or not values.flags.c_contiguous:
            raise ValueError('Coefficient synchronization requires a matching contiguous real buffer')
        self.comm.Bcast([values, self.mpi_dtype], root=0)
