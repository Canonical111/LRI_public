"""Even-parity five-vertex (four-slice) chi density, streaming middle-split kernel (PLAN.md sec. 3.4, INTERFACES.md).

Conventions: vertices 0..4, slices 1..4 (array axes 0..3); bundle (i, j), 0 <= i < j <= 4, crosses slices i+1..j and
contributes its series s[(i, j)] in the variable z_{i+1} ... z_j.  The density is
    rho(N1, N2, N3, N4) = [z1^N1 z2^N2 z3^N3 z4^N4] prod_{(i,j)} s[(i,j)](z_{i+1} ... z_j),
and the kernel returns its even part R[i1, i2, i3, i4] = rho(2 i1, 2 i2, 2 i3, 2 i4), i_s <= N//2.
All-parity intermediates live on [0, N].  Every series entry is >= 0, so every sum below is a sum of non-negative
terms (no cancellation; structural zeros are exact zeros).

Middle split at vertex 2.  The crossing bundles 03, 04, 13, 14 enter only through
    x = l03 + l04 (slice 1),  y = l04 + l14 (slice 4),  t = l03 + l04 + l13 + l14 (slices 2 and 3):
    C(x, y, t)  = sum_u s04[u] s03[x-u] s14[y-u] s13[t-x-y+u]              (numba, parallel over t; x, y <= t)
    Lft(a, b)   = [z1^a z2^b] s01(z1) s02(z1 z2) s12(z2) = T01 diag(s02) T12^T   (all parity)
    Rgt(c, d)   = [z3^c z4^d] s23(z3) s24(z3 z4) s34(z4)
    rho(N1, N2, N3, N4) = sum_{x,y,t} C(x,y,t) Lft(N1-x, N2-t) Rgt(N3-t, N4-y), evaluated in stages
    (A)  P(N1, N2, y, t) = sum_x Lft(N1-x, N2-t) C(x, y, t)         N1, N2 even only; one GEMM per t and N2 block
    (B1) Q(N1, N2, w, v) = sum_u s24[u] P(N1, N2, w-u, v-u)          sheared: d = v - w = t - y is conserved, so for
         fixed d this is the lower Toeplitz matrix T24 acting on the diagonal view y -> P(., ., y, y+d)
    (B2) rho = sum_{v,w} s23[N3-v] s34[N4-w] Q(., ., w, v)          (B2a) v -> N3 even, per w a GEMM on the band
         w <= v <= w + N2 (Q vanishes outside it since y <= t <= N2); (B2b) w -> N4 even, one GEMM per N3 chunk
         restricted to w <= 2 N3 (lower-triangular savings).
N2 is never summed after stage A, so the whole of A, B1, B2 is streamed over blocks of `block` even N2 values:
memory (doubles) = R (H^4, H = N//2 + 1) + C ((N+1)^3) + stage-A gather table ((N+1)^2 H) + per-block temporaries
(at most P + Q ~ 2 (N+1)^2 * block * H, then Q + Z, then Z + Out).  No all-parity 4D array and no full P are ever
allocated.  Patterns without crossing bundles (s03, s04, s13, s14 all equal to [1, 0, 0, ...]) factorise:
R = Lft_even (x) Rgt_even.
Work per generic pattern: GEMM multiply-adds ~ 0.12 N^5 at N = 400, block 4 (in units of N^5: A 0.022, B1 0.033,
B2a 0.027, B2b 0.036; exact counts: tools/bench_kernel5.stage_madds), plus comb(N+4, 4) ~ N^4/24 terms in the
numba crossing kernel and an O(H^4) parallel store into R."""
import time

import numpy as np
from numpy.lib.stride_tricks import as_strided

try:
    from numba import njit, prange, get_num_threads
    HAVE_NUMBA = True
except Exception:  # pragma: no cover
    HAVE_NUMBA = False

PAIRS5 = tuple((i, j) for i in range(5) for j in range(i + 1, 5))
CROSSING = ((0, 3), (0, 4), (1, 3), (1, 4))
B2B_CHUNKS = 8                                  # N3 chunks of stage B2b (triangular restriction w <= 2 N3)


def _toeplitz_lower(a, n):
    """T[i, j] = a[i - j] (j <= i), shape (n+1, n+1)."""
    from scipy.linalg import toeplitz
    c = np.asarray(a[: n + 1], dtype=np.float64)
    r = np.zeros(n + 1)
    r[0] = c[0]
    return toeplitz(c, r)


def _toeplitz_even_rows(a, n):
    """Even rows of the lower Toeplitz matrix on [0, n]: T[i, j] = a[2i - j], shape (n//2+1, n+1)."""
    return np.ascontiguousarray(_toeplitz_lower(a, n)[0::2, :])


def _crossing_kernel_py(s03, s04, s13, s14, N, nchunk):
    """Ct[t, x, y] = C(x, y, t) = sum_u s04[u] s03[x-u] s14[y-u] s13[t-x-y+u] for x, y <= t <= N (zero otherwise).
    Gather form (each (t, x, y) written once by one thread); t interleaved over nchunk chunks for load balance."""
    Ct = np.zeros((N + 1, N + 1, N + 1))
    for c in prange(nchunk):
        for t in range(c, N + 1, nchunk):
            for x in range(t + 1):
                for y in range(t + 1):
                    ulo = x + y - t
                    if ulo < 0:
                        ulo = 0
                    uhi = x if x < y else y
                    acc = 0.0
                    for u in range(ulo, uhi + 1):
                        acc += s04[u] * s03[x - u] * s14[y - u] * s13[t - x - y + u]
                    Ct[t, x, y] = acc
    return Ct


def _store_block_py(R, Out4, lo):
    """R[i1, lo + j, i3, :] = Out4[i3, j, i1, :] (parallel over i1; contiguous rows of length H)."""
    H = R.shape[0]
    nb = Out4.shape[1]
    for i1 in prange(H):
        for j in range(nb):
            for i3 in range(H):
                R[i1, lo + j, i3, :] = Out4[i3, j, i1, :]


if HAVE_NUMBA:
    _crossing_kernel = njit(parallel=True, cache=True)(_crossing_kernel_py)
    _store_block = njit(parallel=True, cache=True)(_store_block_py)
else:  # pragma: no cover
    prange = range
    _crossing_kernel = _crossing_kernel_py
    _store_block = _store_block_py

    def get_num_threads():
        return 1


def _series(s, N):
    """Validated float64 copies s[(i,j)][:N+1] of all ten bundle series (non-negative, finite)."""
    out = {}
    for b in PAIRS5:
        if b not in s:
            raise ValueError(f"density5_stream: missing bundle series {b}")
        v = np.asarray(s[b], dtype=np.float64)
        if v.ndim != 1 or v.shape[0] < N + 1:
            raise ValueError(f"density5_stream: series {b} must be 1D of length >= N+1 = {N + 1}, got {v.shape}")
        v = np.ascontiguousarray(v[: N + 1])
        if not np.all(np.isfinite(v)) or np.any(v < 0.0):
            raise ValueError(f"density5_stream: series {b} must be finite and non-negative")
        out[b] = v
    return out


def _is_unit(v):
    return v[0] == 1.0 and not np.any(v[1:])


def _tick(timings, key, t0):
    t1 = time.perf_counter()
    if timings is not None:
        timings[key] = timings.get(key, 0.0) + (t1 - t0)
    return t1


def density5_stream(s, N, block=8, timings=None):
    """Even-parity five-vertex (four-slice) density.
    s: dict {(i, j): 1D float64 array of length >= N+1} for all ten pairs 0 <= i < j <= 4 (bundle (i, j) crosses
       slices i..j-1); s[(i,j)][l] >= 0 is the bundle series at chi level l (a bundle with no lines is [1, 0, 0, ...]).
    Returns R, float64 array of shape (H, H, H, H), H = N//2 + 1, with
       R[i1, i2, i3, i4] = [z1^{2 i1} z2^{2 i2} z3^{2 i3} z4^{2 i4}] prod_{(i,j)} s[(i,j)](prod_{k=i}^{j-1} z_{k+1}).
    Memory: R plus O(block * H * (N+1)^2) temporaries (stream over blocks of even N2). Positive-term sums only.
    timings: optional dict; if given, wall seconds per stage are accumulated into it (keys C, LR, A, B1, B2a, B2b,
       store; 'factorised' = 1.0 when the no-crossing shortcut was taken)."""
    if not (isinstance(N, (int, np.integer)) and N >= 0):
        raise ValueError(f"N must be a non-negative integer, got {N!r}")
    if not (isinstance(block, (int, np.integer)) and block >= 1):
        raise ValueError(f"block must be a positive integer, got {block!r}")
    N = int(N)
    H = N // 2 + 1
    v = _series(s, N)
    t0 = time.perf_counter()

    # Lft = T01 diag(s02) T12^T (all parity, [a, b]); even rows/columns of the right block for the shortcut
    T01 = _toeplitz_lower(v[(0, 1)], N)
    T12 = _toeplitz_lower(v[(1, 2)], N)
    Lft = (T01 * v[(0, 2)][None, :]) @ T12.T
    del T01, T12
    T23e = _toeplitz_even_rows(v[(2, 3)], N)          # (H, N+1): s23[2 i3 - v]
    T34e = _toeplitz_even_rows(v[(3, 4)], N)          # (H, N+1): s34[2 i4 - w]
    if all(_is_unit(v[b]) for b in CROSSING):
        Rgt_e = (T23e * v[(2, 4)][None, :]) @ T34e.T  # Rgt(2 i3, 2 i4)
        Lft_e = np.ascontiguousarray(Lft[0::2, 0::2])
        R = Lft_e[:, :, None, None] * Rgt_e[None, None, :, :]
        if timings is not None:
            timings["factorised"] = 1.0
        _tick(timings, "LR", t0)
        return R
    T24 = _toeplitz_lower(v[(2, 4)], N)               # (N+1, N+1): s24[w - y]
    # stage-A operand table, split by the parity of b = N2 - t so that the columns of one GEMM are a plain view:
    # TLp[par][x, k, i1] = Lft[2 i1 - x, 2k + par]  (0 for x > 2 i1)
    xs = np.arange(N + 1)
    a_idx = 2 * np.arange(H)[None, :] - xs[:, None]   # (N+1, H)
    Lpad = np.zeros((N + 2, N + 1))
    Lpad[: N + 1] = Lft
    a_idx = np.where(a_idx >= 0, a_idx, N + 1)        # row N+1 of Lpad is zero
    TLp = [np.ascontiguousarray(Lpad[a_idx[:, None, :], np.arange(par, N + 1, 2)[None, :, None]]) for par in (0, 1)]
    del Lpad, Lft, a_idx
    t0 = _tick(timings, "LR", t0)

    Ct = _crossing_kernel(v[(0, 3)], v[(0, 4)], v[(1, 3)], v[(1, 4)], N, max(1, 4 * get_num_threads()))
    t0 = _tick(timings, "C", t0)

    R = np.zeros((H, H, H, H))
    for lo in range(0, H, block):
        hi = min(H, lo + block)
        nb = hi - lo                                   # even N2 = 2 (lo + j), j = 0..nb-1
        D = 2 * (hi - 1) + 1                           # t, y <= max N2 of the block
        cols = nb * H                                  # GEMM column index (j, i1)

        # (A) P[t, y, (j, i1)] = sum_x C[x, y, t] Lft[2 i1 - x, N2_j - t]   (y <= t; columns with N2_j < t stay 0)
        P = np.zeros((D, D, cols))
        for t in range(D):
            ct = (t + 1) // 2
            j0 = max(0, ct - lo)                       # first j with N2_j >= t
            if j0 >= nb:
                continue
            k0 = lo + j0 - ct                          # b_j = N2_j - t = 2 (lo + j - ct) + (t % 2)
            A = TLp[t % 2][: t + 1, k0: k0 + nb - j0, :].reshape(t + 1, (nb - j0) * H)
            np.matmul(Ct[t, : t + 1, : t + 1].T, A, out=P[t, : t + 1, j0 * H:])
        t0 = _tick(timings, "A", t0)

        # (B1) sheared: Q[d, w, :] = Q(w, v = w + d) = sum_{y <= w} s24[w - y] P[y + d, y, :],  w <= N - d
        Q = np.zeros((D, N + 1, cols))
        st0, st1, st2 = P.strides
        for d in range(D):
            Pd = as_strided(P[d:], shape=(D - d, cols), strides=(st0 + st1, st2))     # row y -> P[y + d, y]
            np.matmul(T24[: N + 1 - d, : D - d], Pd, out=Q[d, : N + 1 - d])
        del P
        t0 = _tick(timings, "B1", t0)

        # (B2a) Z[w, i3, :] = sum_{d} s23[2 i3 - w - d] Q[d, w, :]   (band v = w + d <= min(w + D - 1, N); 2 i3 >= w)
        Z = np.zeros((N + 1, H, cols))
        for w in range(N + 1):
            i3lo = (w + 1) // 2
            if i3lo >= H:
                continue
            dm = min(D, N + 1 - w)
            np.matmul(T23e[i3lo:, w: w + dm], Q[:dm, w], out=Z[w, i3lo:])
        del Q
        t0 = _tick(timings, "B2a", t0)

        # (B2b) Out[i3, (j, i1), i4] = sum_{w <= 2 i3} Z[w, i3, (j, i1)] s34[2 i4 - w]
        Zm = Z.reshape(N + 1, H * cols)
        Out = np.empty((H * cols, H))
        ch = -(-H // B2B_CHUNKS)
        for a in range(0, H, ch):
            b = min(H, a + ch)
            wm = min(2 * (b - 1), N) + 1
            np.matmul(Zm[:wm, a * cols: b * cols].T, T34e[:, :wm].T, out=Out[a * cols: b * cols])
        del Z, Zm
        t0 = _tick(timings, "B2b", t0)

        _store_block(R, Out.reshape(H, nb, H, H), lo)      # R[i1, lo + j, i3, i4] = Out[i3, j, i1, i4]
        del Out
        t0 = _tick(timings, "store", t0)
    return R
