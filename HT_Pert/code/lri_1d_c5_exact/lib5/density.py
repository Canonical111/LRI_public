"""Even-parity chi densities of a line pattern for K <= 5 vertices (PLAN.md sec. 3.4).

rho(N_1..N_{K-1}) = [z^N] prod_bundles U_b(prod_{slices crossed by b} z_s), restricted to N_s even in every slice.
* eps-Taylor orders: vertex i with order d_i > 0 distributes d_i over its incident bundles with lines (all
  compositions, Leibniz); bundle (i, j) then gets the two-ended jet U(n_b, alpha_i, beta_j) (series.Series5.U);
  a vertex with d_i > 0 and no chi legs gives zero.
* Empty slices (no line crosses them) split the chain into independent occupied runs; the density is the outer
  product of the run densities (no bundle crosses an empty slice).
* Run kernels: 1 slice: the bundle series itself; 2 slices: T01e diag(s02) T12e^T (C4P density3_even); 3 slices:
  C4P density4_stream (scatter of the long bundles, streaming over s1 blocks, in-place dgemm accumulation);
  4 slices: kernel5.density5_stream (middle split).  The C4P kernels below are copied from
  lri_1d_c4_exact/c4lib1d.py (validated there; see its PLAN A6c).
* dense_rho: all-parity reference by sequential shifted products on the full box (tests only, small N)."""
import itertools

import numpy as np

try:
    from numba import njit
    HAVE_NUMBA = True
except Exception:  # pragma: no cover
    HAVE_NUMBA = False

from .paths import pairs_of, slice_counts, legs_of


# ============================================================================ Toeplitz helpers (C4P)
def toeplitz_lower(a, nrow, ncol=None):
    from scipy.linalg import toeplitz
    ncol = nrow if ncol is None else ncol
    c = np.zeros(nrow + 1)
    k = min(nrow + 1, len(a))
    c[:k] = a[:k]
    r = np.zeros(ncol + 1)
    r[0] = c[0]
    return toeplitz(c, r)


def toeplitz_even_rows(a, N):
    """Even rows of the lower Toeplitz matrix of the series a on [0, N]: T[i, j] = a[2i - j], shape (N//2+1, N+1)."""
    return np.ascontiguousarray(toeplitz_lower(a, N)[0::2, :])


def even_part(R):
    return np.ascontiguousarray(R[tuple(slice(0, None, 2) for _ in range(R.ndim))])


# ============================================================================ dense reference (any K)
def dense_rho(K, arr, Ns):
    """All-parity rho on prod [0, Ns[s]] for bundle series arr[(i,j)] (all pairs), by sequential shifted products."""
    shape = tuple(x + 1 for x in Ns)
    X = np.zeros(shape)
    X[(0,) * (K - 1)] = 1.0
    for (i, j) in pairs_of(K):
        s = np.asarray(arr[(i, j)], dtype=float)
        sl = list(range(i, j))
        if not s[1:].any():
            X = X * s[0]
            continue
        Y = np.zeros_like(X)
        lmax = min(Ns[a] for a in sl)
        for l in range(lmax + 1):
            if l >= len(s) or s[l] == 0.0:
                continue
            src = [slice(None)] * (K - 1)
            dst = [slice(None)] * (K - 1)
            for a in sl:
                src[a] = slice(0, shape[a] - l)
                dst[a] = slice(l, shape[a])
            Y[tuple(dst)] += s[l] * X[tuple(src)]
        X = Y
    return X


# ============================================================================ C4P kernels (copied)
def _scatter_block_py(v13, v14, v24, N, lo, hi):
    """X0s[s2, s1 - lo, s3] for s1 in [lo, hi): sum over (a, u, b) with s1 = a+u, s2 = a+u+b, s3 = u+b, s2 <= N."""
    B = hi - lo
    out = np.zeros((N + 1, B, N + 1))
    for u in range(min(hi - 1, N) + 1):
        x14 = v14[u]
        if x14 == 0.0:
            continue
        alo = lo - u if lo - u > 0 else 0
        for a in range(alo, hi - u):
            x13 = v13[a]
            if x13 == 0.0:
                continue
            s1 = a + u
            for b in range(0, N - s1 + 1):
                out[s1 + b, s1 - lo, u + b] += x14 * x13 * v24[b]
    return out


if HAVE_NUMBA:
    _scatter_block = njit(cache=True)(_scatter_block_py)
else:  # pragma: no cover
    _scatter_block = _scatter_block_py

_INPLACE = None


def _dgemm_inplace_ok():
    global _INPLACE
    if _INPLACE is None:
        from scipy.linalg.blas import dgemm
        C = np.zeros((7, 5), order="F")
        out = dgemm(1.0, np.ones((7, 3), order="F"), np.ones((3, 5), order="F"), beta=1.0, c=C, overwrite_c=1)
        _INPLACE = bool(np.shares_memory(out, C)) and bool(np.all(C == 3.0))
    return _INPLACE


def gemm_acc(C, A, B):
    """C += A @ B in place (C a C-contiguous 2D view) without a temporary of the size of C."""
    from scipy.linalg.blas import dgemm
    Ct = C.T
    if _dgemm_inplace_ok() and Ct.flags.f_contiguous and C.dtype == np.float64:
        At = np.asfortranarray(np.ascontiguousarray(A).T)
        Bt = B.T
        if not Bt.flags.f_contiguous:
            Bt = np.asfortranarray(Bt)
        out = dgemm(1.0, Bt, At, beta=1.0, c=Ct, overwrite_c=1)
        if not np.shares_memory(out, C):
            raise RuntimeError("dgemm did not update C in place")
        return
    for a in range(0, C.shape[0], 64):
        C[a:a + 64] += A[a:a + 64] @ B


def density3_run(s01, s02, s12, N):
    """Two-slice run: R[i0, i1] = sum_c s02[c] s01[2 i0 - c] s12[2 i1 - c]."""
    T01e = toeplitz_even_rows(s01, N)
    T12e = toeplitz_even_rows(s12, N)
    return (T01e * np.asarray(s02[: N + 1])[None, :]) @ T12e.T


def density4_run(s12, s13, s14, s23, s24, s34, N, block=32):
    """Three-slice run (C4P density4_stream): R[i1, i2, i3] even parity, streamed over s1 blocks."""
    if not (isinstance(block, (int, np.integer)) and block >= 1):
        raise ValueError(f"block must be a positive integer, got {block!r}")
    H = N // 2 + 1
    R = np.zeros((H, H, H))
    T23e = toeplitz_even_rows(s23, N)
    T34e = toeplitz_even_rows(s34, N)
    T12e = toeplitz_even_rows(s12, N)
    v13 = np.ascontiguousarray(s13[: N + 1])
    v14 = np.ascontiguousarray(s14[: N + 1])
    v24 = np.ascontiguousarray(s24[: N + 1])
    for lo in range(0, N + 1, block):
        hi = min(N + 1, lo + block)
        B = hi - lo
        X0 = _scatter_block(v13, v14, v24, N, lo, hi)
        Y = T23e[:, lo:] @ X0[lo:].reshape(N + 1 - lo, B * (N + 1))
        del X0
        Z = Y.reshape(H * B, N + 1) @ T34e.T
        del Y
        Z = np.ascontiguousarray(Z.reshape(H, B, H).transpose(1, 0, 2)).reshape(B, H * H)
        i0 = (lo + 1) // 2
        if i0 < H:
            gemm_acc(R[i0:].reshape(H - i0, H * H), T12e[i0:, lo:hi], Z)
        del Z
    return R


def run_density(arr, nsl, N, block):
    """Even-parity density of one occupied run of nsl slices; arr[(i,j)] indexed locally (vertices 0..nsl)."""
    if nsl == 1:
        return np.ascontiguousarray(np.asarray(arr[(0, 1)][: N + 1])[0::2])
    if nsl == 2:
        return density3_run(arr[(0, 1)], arr[(0, 2)], arr[(1, 2)], N)
    if nsl == 3:
        return density4_run(arr[(0, 1)], arr[(0, 2)], arr[(0, 3)], arr[(1, 2)], arr[(1, 3)], arr[(2, 3)], N, block)
    if nsl == 4:
        from .kernel5 import density5_stream
        return density5_stream(arr, N, block=block)
    raise ValueError(nsl)


def runs_of(nsl):
    """Maximal runs of occupied slices: list of (first slice, last slice)."""
    out = []
    s = 0
    S = len(nsl)
    while s < S:
        if nsl[s] == 0:
            s += 1
            continue
        t = s
        while t + 1 < S and nsl[t + 1] > 0:
            t += 1
        out.append((s, t))
        s = t + 1
    return out


def jet_terms(n, ords, K):
    """Leibniz distribution of the vertex eps-orders over incident bundles with lines.
    Yields dicts b -> (alpha, beta) (left-end, right-end orders); nothing if a vertex with order > 0 has no legs."""
    prs = pairs_of(K)
    per_vertex = []
    for v in range(K):
        d = ords[v]
        inc = [b for b in prs if v in b and n[b] > 0]
        if d == 0:
            per_vertex.append([{}])
            continue
        if not inc:
            return []
        opts = []
        for comp in itertools.product(range(d + 1), repeat=len(inc)):
            if sum(comp) != d:
                continue
            opts.append({(b, v): c for b, c in zip(inc, comp) if c})
        per_vertex.append(opts)
    terms = []
    for choice in itertools.product(*per_vertex):
        jb = {b: [0, 0] for b in prs}
        for dct in choice:
            for (b, v), c in dct.items():
                jb[b][0 if v == b[0] else 1] += c
        terms.append({b: tuple(x) for b, x in jb.items()})
    return terms


def density_even(K, n, ords, ser, N, block=32, reference=False):
    """Even-parity density of pattern n with vertex Taylor orders ords, on the box N_s <= N for occupied slices
    (axes of length 1 for empty slices).  reference=True: dense all-parity build (tests)."""
    nsl = slice_counts(n, K)
    terms = jet_terms(n, ords, K)
    if not terms:
        return None
    shape = tuple((N // 2 + 1) if x > 0 else 1 for x in nsl)
    R = None
    for jb in terms:
        arr = {b: ser.U(n[b], *jb[b]) for b in pairs_of(K)}
        if reference:
            Ns = [N if x > 0 else 0 for x in nsl]
            X = even_part(dense_rho(K, arr, Ns))
        else:
            X = None
            for (s0, s1) in runs_of(nsl):
                loc = {}
                for a in range(s0, s1 + 2):
                    for b in range(a + 1, s1 + 2):
                        loc[(a - s0, b - s0)] = arr[(a, b)]
                Rr = run_density(loc, s1 - s0 + 1, N, block)
                sh = [1] * (K - 1)
                for k in range(s0, s1 + 1):
                    sh[k] = Rr.shape[k - s0]
                Rr = Rr.reshape(sh)                   # a view: no copy of a full run density
                X = Rr if X is None else X * Rr       # outer product only across several runs
                del Rr
            if X is None:                             # no occupied slice: chi-free pattern, density 1 at N = 0
                X = np.ones(shape)
            # pure-zero-mode slices contribute the product of the bundles' level-0 factors (=1 for chi-only series)
        if X.shape != shape:
            raise RuntimeError(f"density shape {X.shape} != {shape}")
        if R is None:
            R = X                                     # take ownership (no copy)
        else:
            R += X                                    # in place (one live full density per extra jet term)
        del X
    return R
