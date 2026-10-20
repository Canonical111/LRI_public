"""Shell sums of an even-parity density for every key (1..4 slices).

out[t, i] = sum_{N : max_s E_s[t, N_s] = i} R[N] prod_s G_s[t, N_s],  i = storage index (physical m + MOFF) < M.
G_s[t, .] = 1/den^pow on the slice (0 where infeasible), E_s[t, .] = 4N + delta + n + MOFF (per key and slice).
Configurations with storage index >= M (beyond the largest cutoff) are dropped.  Parallel over the first axis with
bounded per-chunk buffers (as C4P _shell3)."""
import numpy as np

try:
    from numba import njit, prange
    HAVE_NUMBA = True
except Exception:  # pragma: no cover
    HAVE_NUMBA = False

from .common import MOFF


def slice_arrays(delta, nlines, pw, length):
    """g = 1/den^pw (den = N + (delta+n)/4 on even N = 2i; sign and (delta+n)^q are in the key amplitude), zero where
    N < n (or N > 0 on a chi-free slice); e = 4N + delta + n + MOFF (storage index)."""
    Nl = 2 * np.arange(length)
    den = Nl + (delta + nlines) / 4.0
    ok = Nl >= nlines
    if nlines == 0:
        ok = Nl == 0
    if np.any(den[ok] == 0.0):
        raise RuntimeError(f"zero energy denominator: delta={delta} n={nlines}")
    if nlines > 0 and np.any(den[ok] <= 0.0):
        raise RuntimeError(f"chi state below the reference: delta={delta} n={nlines}")
    g = np.zeros(length)
    g[ok] = 1.0 / den[ok] ** pw
    e = (4 * Nl + delta + nlines + MOFF).astype(np.int64)
    return g, e


if HAVE_NUMBA:
    @njit(cache=True)
    def _shell1(R, G0, E0, M):
        T = G0.shape[0]
        out = np.zeros((T, M))
        for i0 in range(R.shape[0]):
            r = R[i0]
            if r == 0.0:
                continue
            for t in range(T):
                m = E0[t, i0]
                if m < M:
                    out[t, m] += r * G0[t, i0]
        return out

    @njit(cache=True)
    def _shell2(R, G0, G1_, E0, E1, M):
        T = G0.shape[0]
        out = np.zeros((T, M))
        for i0 in range(R.shape[0]):
            for i1 in range(R.shape[1]):
                r = R[i0, i1]
                if r == 0.0:
                    continue
                for t in range(T):
                    m = E0[t, i0]
                    m1 = E1[t, i1]
                    if m1 > m:
                        m = m1
                    if m < M:
                        out[t, m] += r * G0[t, i0] * G1_[t, i1]
        return out

    @njit(parallel=True, cache=True)
    def _shell3(R, G0, G1_, G2, E0, E1, E2, M, nchunk):
        T = G0.shape[0]
        n0 = R.shape[0]
        buf = np.zeros((nchunk, T, M))
        for c in prange(nchunk):
            for i0 in range(c, n0, nchunk):
                for i1 in range(R.shape[1]):
                    for i2 in range(R.shape[2]):
                        r = R[i0, i1, i2]
                        if r == 0.0:
                            continue
                        for t in range(T):
                            m = E0[t, i0]
                            m1 = E1[t, i1]
                            if m1 > m:
                                m = m1
                            m2 = E2[t, i2]
                            if m2 > m:
                                m = m2
                            if m < M:
                                buf[c, t, m] += r * G0[t, i0] * G1_[t, i1] * G2[t, i2]
        return buf.sum(axis=0)

    @njit(parallel=True, cache=True)
    def _shell4(R, G0, G1_, G2, G3, E0, E1, E2, E3, M, nchunk):
        T = G0.shape[0]
        n0 = R.shape[0]
        buf = np.zeros((nchunk, T, M))
        for c in prange(nchunk):
            for i0 in range(c, n0, nchunk):
                for i1 in range(R.shape[1]):
                    for i2 in range(R.shape[2]):
                        for i3 in range(R.shape[3]):
                            r = R[i0, i1, i2, i3]
                            if r == 0.0:
                                continue
                            for t in range(T):
                                m = E0[t, i0]
                                m1 = E1[t, i1]
                                if m1 > m:
                                    m = m1
                                m2 = E2[t, i2]
                                if m2 > m:
                                    m = m2
                                m3 = E3[t, i3]
                                if m3 > m:
                                    m = m3
                                if m < M:
                                    buf[c, t, m] += r * G0[t, i0] * G1_[t, i1] * G2[t, i2] * G3[t, i3]
        return buf.sum(axis=0)


def shell_sums(R, Gs, Es, M, nchunk=64):
    R = np.ascontiguousarray(R)
    if R.ndim == 1:
        return _shell1(R, Gs[0], Es[0], M)
    if R.ndim == 2:
        return _shell2(R, Gs[0], Gs[1], Es[0], Es[1], M)
    if R.ndim == 3:
        return _shell3(R, Gs[0], Gs[1], Gs[2], Es[0], Es[1], Es[2], M, nchunk)
    if R.ndim == 4:
        return _shell4(R, Gs[0], Gs[1], Gs[2], Gs[3], Es[0], Es[1], Es[2], Es[3], M, nchunk)
    raise ValueError(R.ndim)
