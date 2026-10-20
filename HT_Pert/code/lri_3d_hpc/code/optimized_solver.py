"""Precision-preserving formal epsilon solver for the 3D HT Hamiltonian.

The recurrence backend is the reference Rayleigh--Schrodinger recurrence,
with scalar seed contractions replacing discarded full-vector applications.
The stationary backend additionally uses the Hermitian Rayleigh quotient:
wavefunctions through order m give energies through order 2*m+1.  All tuned
couplings and every required self-consistent vacuum-window coefficient are
still solved in order.  Neither backend changes the basis or its precision.

``spmm`` may be a prefix-aware callable with signature
``spmm(matrix, X, nrows=nb, ncols=nb)``.  A row-distributed MPI implementation
can be injected; it must return the global result and replicate matrix row 0
on every rank.  With ``distributed=True`` empty local terms are retained so
all ranks issue the same collectives.  Input vertices must be the real
Hermitian, explicitly symmetrized vertices produced by taylor_vertices.py.
"""
from __future__ import annotations

import json
import math
import time

import numpy as np


class LocalBands:
    """Cached nonzero local diagonals, ordered by input column at every row."""
    __slots__ = ('shape', 'terms', 'identity', 'diagonal', 'left', 'right',
                 'start', 'width', 'weights')

    def __init__(self, block):
        self.shape = block.shape
        rows, columns = block.shape
        self.terms = []
        for offset in range(1-rows, columns):
            coefficients = np.diagonal(block, offset=offset)
            if not np.any(coefficients):
                continue
            start = max(0, -offset)
            stop = min(rows, columns-offset)
            self.terms.append((start, stop, start+offset, stop+offset, coefficients))
        self.diagonal = (rows == columns and len(self.terms) == 1 and
                         self.terms[0][0:4] == (0, rows, 0, columns))
        self.identity = self.diagonal and bool(np.all(self.terms[0][4] == 1))
        self.left = self.right = self.start = self.width = 0
        self.weights = None
        if self.terms:
            first_offset = self.terms[0][2] - self.terms[0][0]
            last_offset = self.terms[-1][2] - self.terms[-1][0]
            self.left = max(0, -first_offset)
            self.right = max(0, rows+last_offset-columns)
            self.start = self.left + first_offset
            self.width = last_offset-first_offset+1
            self.weights = np.zeros((rows, self.width), dtype=block.dtype)
            for first, last, source_first, source_last, coefficients in self.terms:
                self.weights[first:last, source_first-first-first_offset] = coefficients


def make_local_bands(block):
    """Prepare a local oscillator matrix once, retaining its original dtype."""
    return LocalBands(block)


def apply_local_block(X, block, bands=None, mode='banded'):
    """Return X @ block.T with ordered band summation or the dense reference.

    Cached band weights contract a read-only sliding-window view; only the
    padded two-dimensional input is allocated.  Band coordinates are ascending
    input columns, as in the reference scalar product.  Tiny row batches and
    float64 use dense multiplication, where measured setup/BLAS costs favor it.
    Identity blocks may return X itself; callers must treat the returned array
    as read-only.  No operand is modified or downcast.
    """
    if mode == 'dense':
        return X @ block.T
    if mode != 'banded':
        raise ValueError('local mode must be dense or banded')
    if bands is None:
        bands = make_local_bands(block)
    if bands.identity:
        return X
    if bands.diagonal:
        return X * bands.terms[0][4]
    if X.shape[0] < 128 or X.dtype.itemsize <= 8:
        return X @ block.T
    if not bands.terms:
        return np.zeros((X.shape[0], block.shape[0]), dtype=X.dtype)
    padded = np.zeros((X.shape[0], X.shape[1]+bands.left+bands.right), dtype=X.dtype)
    padded[:, bands.left:bands.left+X.shape[1]] = X
    windows = np.lib.stride_tricks.sliding_window_view(padded, bands.width, axis=1)
    windows = windows[:, bands.start:bands.start+block.shape[0], :]
    return np.einsum('rjb,jb->rj', windows, bands.weights, optimize=False,
                     dtype=X.dtype, casting='no')


def normal_powers(nz, dtype):
    """The reference padded normal-ordering convention, without alteration."""
    dim = 2 * nz
    a = np.diag(np.sqrt(np.arange(1, dim + 4, dtype=dtype)), 1)
    creations = [np.eye(dim + 4, dtype=dtype)]
    annihilations = [np.eye(dim + 4, dtype=dtype)]
    for _ in range(4):
        creations.append(a.T @ creations[-1])
        annihilations.append(a @ annihilations[-1])
    ix = np.r_[np.arange(0, dim, 2), np.arange(1, dim, 2)]
    result = []
    for degree in range(5):
        q = sum((math.comb(degree, j) * creations[j] @ annihilations[degree-j]
                 for j in range(degree+1)), np.zeros_like(a))
        result.append(q[np.ix_(ix, ix)])
    return result


class BareSeries:
    """Shared Taylor Hamiltonians with cached local blocks and seed rows."""

    def __init__(self, N, P, W, nz, order=8, dtype=np.longdouble,
                 spmm=None, distributed=False, hamiltonian_apply=None,
                 local_mode='banded'):
        self.N, self.P, self.W = np.asarray(N), np.asarray(P), W
        self.nz, self.order, self.dtype = int(nz), int(order), np.dtype(dtype)
        self.T = self.dtype.type
        self.spmm = spmm
        self.hamiltonian_apply = hamiltonian_apply
        self.local_mode = local_mode
        self.distributed = bool(distributed)
        self.q = normal_powers(nz, self.dtype)
        self.qblocks = {(degree, p, q):
                        mat[p*nz:(p+1)*nz, q*nz:(q+1)*nz]
                        for degree, mat in enumerate(self.q)
                        for p in (0, 1) for q in (0, 1)}
        self.qbands = {key: make_local_bands(block) for key, block in self.qblocks.items()}
        self.r = np.zeros(order+1, dtype=dtype)
        self.g = np.zeros(order+1, dtype=dtype)
        self.terms = {}
        self.seed_terms = {}
        self.local = {}
        self.local_bands = {}
        self._prefixes = {}
        self._vertex_seed_rows = {}
        self.counters = {"full_applications": 0, "seed_row_applications": 0,
                         "seed_column_applications": 0, "sparse_products": 0,
                         "full_combination_builds": 0, "seed_only_builds": 0}

    def build(self, n, full=True):
        """Build H_n once; final-order actions need only its seed rows."""
        terms, seed_terms = [], []
        self.local[n] = self.r[n] * self.q[2] + self.g[n] / 12 * self.q[4]
        self.local_bands[n] = tuple(make_local_bands(
            self.local[n][p*self.nz:(p+1)*self.nz, p*self.nz:(p+1)*self.nz]) for p in (0, 1))
        for degree, couplings, norm in ((2, self.r, self.T(1)),
                                        (4, self.g, self.T(1)/12)):
            for j in range(1, degree+1):
                matrix = None
                for i in range(1, n+1):
                    if couplings[i] == 0:
                        continue
                    if full:
                        source = self.W[j-1][n-i]
                    else:
                        key = (j-1, n-i)
                        if key not in self._vertex_seed_rows:
                            self._vertex_seed_rows[key] = self.W[j-1][n-i].getrow(0)
                        source = self._vertex_seed_rows[key]
                    val = source * (norm * math.comb(degree, j) * couplings[i])
                    matrix = val if matrix is None else matrix + val
                if matrix is None:
                    continue
                matrix = matrix.tocsr()
                matrix.sum_duplicates()
                matrix.sort_indices()
                matrix.eliminate_zeros()
                if full and (matrix.nnz or self.distributed):
                    terms.append((j, degree-j, matrix))
                row = matrix.getrow(0) if full else matrix
                # Sorted CSR indices permit zero-copy subcutoff row prefixes.
                seed_terms.append((j, degree-j, row.indices, row.data))
        self.terms[n] = terms if full else None
        self.seed_terms[n] = seed_terms
        self.counters["full_combination_builds" if full else "seed_only_builds"] += 1

    def drop(self, n):
        """Release combined CSR matrices after their stationary contribution."""
        self.terms.pop(n, None)
        keys = [key for key in self._prefixes if key[0] == n]
        for key in keys:
            del self._prefixes[key]

    def apply(self, n, X, state):
        """Full H_n action; all local parity and energy metadata are reused."""
        self.counters["full_applications"] += 1
        if self.hamiltonian_apply is not None:
            terms = self.terms.get(n)
            if terms is None:
                raise RuntimeError(f'Full H_{n} was not retained')
            self.counters["sparse_products"] += len(terms)
            return self.hamiltonian_apply(n, X, state)
        nz, nb = self.nz, state.nb
        out = np.zeros_like(X)
        qlocal = self.local[n]
        for bpar, selected in enumerate(state.rows):
            f = state.field ^ bpar
            block = qlocal[f*nz:(f+1)*nz, f*nz:(f+1)*nz]
            out[selected] += apply_local_block(X[selected], block,
                                               self.local_bands[n][f], self.local_mode)
        if n == 1:
            out += state.free_first * X
        terms = self.terms.get(n)
        if terms is None:
            raise RuntimeError(f'Full H_{n} was not retained')
        for term_index, (bath_degree, local_degree, matrix) in enumerate(terms):
            if self.spmm is None:
                if nb != matrix.shape[0]:
                    key = (n, term_index, nb)
                    if key not in self._prefixes:
                        self._prefixes[key] = matrix[:nb, :nb]
                    used = self._prefixes[key]
                else:
                    used = matrix
                image = used @ X
            else:
                image = self.spmm(matrix, X, nrows=nb, ncols=nb)
            self.counters["sparse_products"] += 1
            if local_degree == 0:
                # q_0 is the identity and these bath powers are even.  This
                # adds the same elements in the same order without gathers.
                out += image
                continue
            for bpar, selected in enumerate(state.rows):
                f = state.field ^ bpar
                pin = f ^ (bath_degree % 2)
                key = (local_degree, f, pin)
                out[selected] += apply_local_block(image[selected], self.qblocks[key],
                                                   self.qbands[key], self.local_mode)
        return out

    def seed_row(self, n, X, state):
        """Exactly the needed scalar <seed|H_n|X>, without a full action."""
        self.counters["seed_row_applications"] += 1
        nz, field, iz = self.nz, state.field, state.index[1]
        value = self.local[n][field*nz+iz, field*nz:(field+1)*nz] @ X[0]
        if n == 1:
            value -= self.T(state.seed)/4 * X[state.index]
        for bath_degree, local_degree, indices, data in self.seed_terms[n]:
            end = int(np.searchsorted(indices, state.nb))
            if end == 0:
                continue
            image = data[:end] @ X[indices[:end]]
            pin = field ^ (bath_degree % 2)
            value += self.qblocks[local_degree, field, pin][iz] @ image
        # Every self-consistent window is identically zero on the bath vacuum.
        return value

    def seed_column(self, n, state):
        """H_n|seed> from Hermitian seed rows, preserving working dtype."""
        self.counters["seed_column_applications"] += 1
        nz, field, iz = self.nz, state.field, state.index[1]
        out = np.zeros_like(state.psi[0])
        out[0] = self.local[n][field*nz:(field+1)*nz, field*nz+iz]
        if n == 1:
            out[state.index] -= self.T(state.seed)/4
        for bath_degree, local_degree, indices, data in self.seed_terms[n]:
            end = int(np.searchsorted(indices, state.nb))
            if end == 0:
                continue
            pout = field ^ (bath_degree % 2)
            column = self.qblocks[local_degree, pout, field][:, iz]
            out[indices[:end]] += data[:end, None] * column[None, :]
        return out


class SeedSeries:
    """One primary or subcutoff vacuum, with intermediate normalization."""

    def __init__(self, bare, cutoff, seed, mode):
        self.bare, self.cutoff, self.seed, self.mode = bare, int(cutoff), int(seed), mode
        self.nb = int(np.searchsorted(bare.N, cutoff, side='right'))
        self.N, self.P = bare.N[:self.nb], bare.P[:self.nb]
        self.field = seed % 2
        self.rows = tuple(np.flatnonzero(self.P % 2 == p) for p in (0, 1))
        localp = self.field ^ (self.P % 2)
        self.totalp = self.P[:, None] + localp[:, None] + 2*np.arange(bare.nz)[None, :]
        self.h0 = self.N[:, None] + bare.T(3)/4 * self.totalp
        self.free_first = -bare.T(1)/4 * self.totalp
        self.E = np.zeros(bare.order+1, dtype=bare.dtype)
        self.E[0] = bare.T(3)*seed/4
        self.denominator = self.E[0] - self.h0
        self.index = (0, seed//2)
        self.denominator[self.index] = 1
        if np.any(self.denominator == 0):
            raise ValueError('Seed is degenerate in retained symmetry sector')
        v = np.zeros_like(self.h0, dtype=bare.dtype)
        v[self.index] = 1
        self.psi = [v]
        self.windows = [np.zeros(self.nb, dtype=bare.dtype) for _ in range(bare.order+1)]
        self.window_indices = (self.cutoff-self.N)//2
        self.max_recursion_residual = bare.T(0)
        self.norm = None
        self.numerator = None
        self.wavefunction_order = None

    def apply(self, n, X):
        out = self.bare.apply(n, X, self)
        if self.mode == 'consistent':
            out += self.windows[n][:, None] * X
        return out

    def provisional(self, n):
        if n == 1:
            return -self.bare.T(self.seed)/4
        return sum((self.bare.seed_row(k, self.psi[n-k], self)
                    for k in range(1, n)), self.bare.T(0))

    def advance(self, n):
        accum = np.zeros_like(self.psi[0])
        for k in range(1, n+1):
            image = self.bare.seed_column(k, self) if k == n else self.apply(k, self.psi[n-k])
            accum += image - self.E[k] * self.psi[n-k]
        scale = max(self.bare.T(1), abs(self.E[n]))
        self.max_recursion_residual = max(self.max_recursion_residual,
                                         abs(accum[self.index])/scale)
        accum[self.index] = 0
        new = accum / self.denominator
        new[self.index] = 0
        self.psi.append(new)

    def prepare_stationary(self):
        """Initialize ||phi||^2 and <phi|(H0-E0)|phi> at future orders."""
        order, T = self.bare.order, self.bare.T
        self.wavefunction_order = m = len(self.psi)-1
        self.norm = np.zeros(order+1, dtype=self.bare.dtype)
        self.numerator = np.zeros(order+1, dtype=self.bare.dtype)
        h0_minus_seed = self.h0 - self.E[0]
        for i in range(m+1):
            for j in range(i, m+1):
                n = i+j
                if n > order:
                    break
                factor = T(1 if i == j else 2)
                self.norm[n] += factor * np.sum(self.psi[i]*self.psi[j], dtype=self.bare.dtype)
                if n > m:
                    self.numerator[n] += factor * np.sum(
                        self.psi[i]*h0_minus_seed*self.psi[j], dtype=self.bare.dtype)

    def accumulate_stationary(self, n):
        """Add H_n and its window to all not-yet-solved Ritz coefficients."""
        order, m, T = self.bare.order, self.wavefunction_order, self.bare.T
        first = max(m+1, n+1)
        for j in range(max(1, first-n), min(m, order-n)+1):
            self.numerator[n+j] += 2*self.bare.seed_row(n, self.psi[j], self)
        for i in range(1, min(m, (order-n)//2)+1):
            first_j = max(i, first-n-i)
            last_j = min(m, order-n-i)
            if first_j > last_j:
                continue
            image = self.apply(n, self.psi[i])
            for j in range(first_j, last_j+1):
                factor = T(1 if i == j else 2)
                self.numerator[n+i+j] += factor * np.sum(
                    self.psi[j]*image, dtype=self.bare.dtype)

    def stationary_provisional(self, n):
        return self.numerator[n] - sum((self.E[k]*self.norm[n-k]
                                       for k in range(1, n)), self.bare.T(0))


def solve_coefficients(N, P, W, cutoff, order=8, nz=10, mode='consistent',
                       dtype=np.longdouble, keep_states=False, progress=False,
                       strategy='stationary', spmm=None, distributed=False,
                       backend=None, threads=1, backend_cache=None,
                       synchronize_coefficients=None, hamiltonian_apply=None,
                       local_mode='banded'):
    """Solve the unchanged finite HT coefficient problem.

    ``strategy='recurrence'`` retains psi through order-1 and uses the original
    energy recurrence. ``'stationary'`` retains only floor(order/2), while
    preserving all energies, r, g, and self-consistent window coefficients
    through ``order``.  In stationary mode ``keep_states`` returns these shorter
    wavefunction series and releases combined sparse Hamiltonians after use.

    ``backend`` selects 'auto', 'native', or 'scipy' from native_backend; if it
    is None and no ``spmm`` is supplied, SciPy is used with cached subcutoffs.
    An injected MPI ``spmm`` must be collective and preserve longdouble.
    ``synchronize_coefficients`` may broadcast an in-place dtype-preserving
    buffer of the current couplings and every state energy after each order;
    this ensures identical subsequent collective paths on heterogeneous ranks.
    ``hamiltonian_apply(n, X, state)`` may fuse a complete bare Hamiltonian
    application across owned matrix rows into one collective; SeedSeries still
    adds the exact window afterwards.  It must return the global bare result.
    ``local_mode`` chooses an equivalent banded or dense local oscillator
    multiplication.  Both retain the selected working precision.
    """
    if mode not in ('raw', 'consistent'):
        raise ValueError('mode must be raw or consistent')
    if strategy not in ('recurrence', 'stationary'):
        raise ValueError('strategy must be recurrence or stationary')
    if local_mode not in ('dense', 'banded'):
        raise ValueError('local mode must be dense or banded')
    if int(order) != order or order < 2:
        raise ValueError('Require an integer order >= 2')
    if int(cutoff) != cutoff or cutoff < 0 or cutoff % 2:
        raise ValueError('Require an even nonnegative bath cutoff')
    if int(nz) != nz or nz < 1:
        raise ValueError('Require a positive integer nz')
    order, nz, cutoff = int(order), int(nz), int(cutoff)
    dtype = np.dtype(dtype)
    if dtype not in (np.dtype(np.float64), np.dtype(np.longdouble)):
        raise ValueError('Supported working dtypes are float64 and longdouble')
    required = 3 + 4*(order//2)
    if 2*nz-1 < required:
        raise ValueError(f'Local occupation cap must be at least {required} at order {order}')
    N, P = np.asarray(N), np.asarray(P)
    if N.ndim != 1 or P.shape != N.shape or N.size == 0:
        raise ValueError('N and P must be nonempty equal-length one-dimensional arrays')
    if N[0] != 0 or P[0] != 0 or np.any(N[1:] < N[:-1]):
        raise ValueError('Scalar basis must start with its vacuum and be ordered by level')
    if np.any(N % 2) or np.any(N < 0) or np.any(P < 0):
        raise ValueError('Require the inversion-even scalar bath with nonnegative N and P')
    if len(W) != 4 or any(len(s) < order-1 for s in W):
        raise ValueError('Need four bath vertices with derivatives through order-2')
    nb = int(np.searchsorted(N, cutoff, side='right'))
    if nb < 1:
        raise ValueError('No bath vacuum was retained')
    N, P = N[:nb], P[:nb]
    vertices = []
    for series in W:
        selected = []
        for matrix in series[:order-1]:
            if matrix.shape[0] != matrix.shape[1] or matrix.shape[0] < nb:
                raise ValueError('Bath vertex dimensions do not cover the requested cutoff')
            matrix = matrix.tocsr(copy=False).astype(dtype, copy=False)
            if matrix.shape[0] != nb:
                matrix = matrix[:nb, :nb]
            selected.append(matrix)
        vertices.append(selected)
    backend_metadata = {"backend": 'injected' if spmm is not None else 'scipy',
                        "threads": None if spmm is not None else int(threads)}
    if spmm is not None:
        owner = getattr(spmm, '__self__', None)
        supplied_metadata = getattr(owner, 'metadata', None)
        if isinstance(supplied_metadata, dict):
            backend_metadata = supplied_metadata.copy()
    if backend is not None:
        if spmm is not None:
            raise ValueError('Pass an injected spmm or backend selection, not both')
        from native_backend import load_backend
        selected_backend = load_backend(backend, threads=threads, cache_dir=backend_cache)
        spmm = selected_backend.csr_spmm
        backend_metadata = selected_backend.metadata
    if distributed and spmm is None and hamiltonian_apply is None:
        raise ValueError('distributed=True requires a collective operator application')
    bare = BareSeries(N, P, vertices, nz, order, dtype, spmm, distributed,
                      hamiltonian_apply, local_mode)
    roots = {p: SeedSeries(bare, cutoff, p, mode) for p in range(4)}
    vacua = ({ell: SeedSeries(bare, ell, 0, mode) for ell in range(0, cutoff, 2)}
             if mode == 'consistent' else {})
    vacua[cutoff] = roots[0]
    all_states = list(vacua.values()) + [roots[p] for p in (1, 2, 3)]
    C = np.zeros(order+1, dtype=dtype)
    C[0] = bare.T(3)/2
    started, tuning = time.perf_counter(), []
    m = order//2 if strategy == 'stationary' else order-1
    for n in range(1, order+1):
        use_stationary = strategy == 'stationary' and n > m
        evaluate = (lambda st: st.stationary_provisional(n)) if use_stationary else (lambda st: st.provisional(n))
        provisional = {p: evaluate(roots[p]) for p in range(4)}
        for ell, state in vacua.items():
            state.E[n] = provisional[0] if ell == cutoff else evaluate(state)
        target_sigma = -bare.T(1)/4 if n == 1 else bare.T(0)
        target_chi = bare.T(1)/4 if n == 1 else bare.T(0)
        bare.r[n] = (target_sigma-provisional[1]+provisional[0])/2
        bare.g[n] = (target_chi-provisional[3]+provisional[0]-6*bare.r[n])/3
        for p in (1, 2, 3):
            roots[p].E[n] = provisional[p] + 2*p*bare.r[n] + bare.T(p*(p-1))/2*bare.g[n]
        if synchronize_coefficients is not None:
            current = np.asarray([bare.r[n], bare.g[n]] + [state.E[n] for state in all_states],
                                 dtype=dtype)
            synchronize_coefficients(current)
            bare.r[n], bare.g[n] = current[:2]
            for state, value in zip(all_states, current[2:]):
                state.E[n] = value
        C[n] = roots[2].E[n] - roots[0].E[n]
        tuning.append({'order': n,
            'sigma_residual': float(roots[1].E[n]-roots[0].E[n]-target_sigma),
            'chi_residual': float(roots[3].E[n]-roots[0].E[n]-target_chi)})
        if mode == 'consistent':
            egrid = np.asarray([vacua[ell].E[n] for ell in range(0, cutoff+1, 2)], dtype=dtype)
            for state in all_states:
                state.windows[n] = egrid[state.cutoff//2] - egrid[state.window_indices]
        if n < order:
            bare.build(n, full=n < order-1)
            if not use_stationary:
                for state in all_states:
                    state.advance(n)
            if strategy == 'stationary' and n == m:
                for state in all_states:
                    state.prepare_stationary()
                for k in range(1, n+1):
                    for state in all_states:
                        state.accumulate_stationary(k)
                    bare.drop(k)
            elif use_stationary:
                for state in all_states:
                    state.accumulate_stationary(n)
                bare.drop(n)
        if progress:
            print(json.dumps({'cutoff': cutoff, 'mode': mode, 'order': n,
                'C': float(C[n]), 'r': float(bare.r[n]), 'g': float(bare.g[n]),
                'seconds': time.perf_counter()-started}), flush=True)
    result = {
        'dimension': 3, 'cutoff': cutoff,
        'cutoff_definition': 'bath N_b=sum(2n+l) occupancy <= L',
        'epsilon': '2s-3', 'x': '(3-epsilon)/4',
        'thermal_expansion': 'Delta_thermal = sum_n C[n] epsilon^n; C0=3/2, C1=-1/6',
        'scheme': mode, 'order': order, 'arithmetic': str(dtype),
        'arithmetic_significand_bits': int(np.finfo(dtype).nmant+1),
        'scalar_bath_states': nb, 'local_occupation_max': 2*nz-1,
        'dimension_per_field_parity': nb*nz,
        'C': [str(x) for x in C], 'r': [str(x) for x in bare.r], 'g': [str(x) for x in bare.g],
        'energies_by_seed': {str(p): [str(x) for x in roots[p].E] for p in range(4)},
        'vacuum_energies_by_subcutoff': {str(ell): [str(x) for x in st.E] for ell, st in vacua.items()},
        'tuning_residuals': tuning,
        'max_scaled_seed_recursion_residual': float(max(st.max_recursion_residual for st in all_states)),
        'seconds': time.perf_counter()-started,
        'scope': 'finite-cutoff formal coefficients; no continuum extrapolation or complete connected matching',
        'optimization': {'strategy': strategy, 'wavefunction_order': m,
                         'recursion_residual_through_order': m,
                         'stationary_energy_order_guarantee': 2*m+1 if strategy == 'stationary' else None,
                         'backend': backend_metadata, 'distributed': bool(distributed),
                         'coefficients_synchronized': synchronize_coefficients is not None,
                         'fused_hamiltonian_application': hamiltonian_apply is not None,
                         'local_mode': local_mode,
                         'banded_min_rows': 128,
                         'banded_float64_uses_dense': True,
                         'counters': bare.counters.copy(),
                         'hermitian_seed_columns': True,
                         'all_window_orders_retained': True},
    }
    return (result, bare, roots, vacua) if keep_states else result
