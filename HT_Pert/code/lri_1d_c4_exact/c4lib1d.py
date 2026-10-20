#!/usr/bin/env python3
"""Exact finite-cutoff diagram sums for the d = 1 LRI frozen-cutoff Hamiltonian truncation (PLAN.md).

Model: modes n >= 0, u_n(eps)^2 = ((1-eps)/2)_n/n!, B = sum u_n a_n, phi = B + B^dag, M = :phi^2:,
V = :phi^4:/12, H = N + P/4 - eps P/4 + r M + g V, truncation 4N + P <= cut4 = 4 Lambda (frozen), sphere parity
(N even) projected after every complete vertex, references |p> = (a_0^dag)^p/sqrt(p!)|0>, p = 0..3.

Method (ported from the 2D code lri_2d_coeff_expanse/independent_check/c4_exact/c4lib.py, HT2dPert session;
zero-mode paths and pattern enumeration are copied from there, the chi densities and the cutoff are new):
  * zero mode Z = a_0 + a_0^dag as an oscillator: exact rational closed-path amplitudes;
  * chi = modes n >= 1 by Wick contraction; a bundle of n lines between two vertices has the positive series
    S_n(y) = (V_1(y) - 1)^n, V_1 = (1-y)^(-1/2); the density of a pattern is
    rho(N_1..N_{K-1}) = [z^N] prod_b S_{n_b}(prod_{slices crossed by b} z_s), restricted to N_s even in every slice;
  * slice s: n_s lines, chi level N_s, zero-mode shift delta_s = r_s - p; energy above the reference
    den_s = N_s + (delta_s + n_s)/4; cutoff 4 N_s + p + delta_s + n_s <= cut4 for every slice, i.e.
    m(N, delta) + p <= cut4 with the p-independent shell index m = max_s (4 N_s + delta_s + n_s) >= -3;
  * shells S_delta[m] do not depend on the cutoff or on p: one run gives every quarter cutoff and every p.
"""
import itertools
import math
from fractions import Fraction as Fr
from math import comb, factorial

import numpy as np

try:
    from numba import njit, prange
    HAVE_NUMBA = True
except Exception:  # pragma: no cover
    HAVE_NUMBA = False

G1 = Fr(1, 3)
MAXLEGS = {"V": 4, "M": 2}
MOFF = 3                                   # shell array index = m + MOFF  (m >= -3)
PS = (0, 1, 2, 3)
# linear functionals sum_p w_p X_p (tuning at order k >= 2):  r = -(X1-X0)/2, g = -(X3-X0+6r)/3, C = Pi X
W_R = (Fr(1, 2), Fr(-1, 2), Fr(0), Fr(0))
W_G = (Fr(-2, 3), Fr(1), Fr(0), Fr(-1, 3))
W_C = (Fr(1, 3), Fr(-1), Fr(1), Fr(-1, 3))
FUNCTIONALS = {"r": W_R, "g": W_G, "C": W_C}
PREFACTORS = {"1": lambda p: Fr(1), "Vpp": lambda p: Fr(p * (p - 1), 2), "2p": lambda p: Fr(2 * p),
              "Vpp2": lambda p: Fr(p * (p - 1), 2) ** 2}


def vcoef(kind, m):
    """Coefficient of :Z^{maxlegs-m}: (x) :chi^m: in the vertex."""
    if kind == "V":
        return Fr(comb(4, m), 12)
    if kind == "M":
        return Fr(comb(2, m), 1)
    raise ValueError(kind)


# ============================================================================ series
class Series1D:
    """Line series at eps = 0 up to level N (index = chi level).

    u2[m] = (1/2)_m/m!;  chi = V_1 - 1 (u2 without the zero mode);  S[n] = chi^n (bundle of n lines);
    a[m], b[m]: log u_m(eps) = log u_m + a_m eps + b_m eps^2 + O(eps^3);
    dchi = d/deps1 [sum_m u_m(eps1) u_m(0) y^m] = u2 * a  (m >= 1);  dS[n] = n S[n-1] * dchi."""

    def __init__(self, N, nmax=8):
        from scipy.special import digamma, polygamma
        self.N = N
        u2 = np.empty(N + 1)
        u2[0] = 1.0
        for j in range(1, N + 1):
            u2[j] = u2[j - 1] * (j - 0.5) / j
        self.u2 = u2
        chi = u2.copy()
        chi[0] = 0.0
        self.chi = chi
        delta = np.zeros(N + 1)
        delta[0] = 1.0
        S = [delta]
        for n in range(1, nmax + 1):
            S.append(np.convolve(S[-1], chi)[: N + 1])
        self.S = S
        m = np.arange(N + 1)
        self.a = -(digamma(0.5 + m) - digamma(0.5)) / 4.0
        self.b = -(polygamma(1, 0.5) - polygamma(1, 0.5 + m)) / 16.0
        self.a[0] = 0.0
        self.b[0] = 0.0
        dchi = u2 * self.a
        dchi[0] = 0.0
        self.dchi = dchi
        dS = [np.zeros(N + 1)]
        for n in range(1, nmax + 1):
            dS.append(n * np.convolve(S[n - 1], dchi)[: N + 1])
        self.dS = dS


# ============================================================================ zero-mode paths (from 2D c4lib)
def zero_mode_paths(p, zlegs):
    """Closed paths p = r_0 -> r_1 -> ... -> r_K = p, vertex i applying :Z^{zlegs[i]}: (normal ordered).
    Returns [(r_1..r_{K-1}, exact amplitude)], amplitude = prod C(k_i, j_i) * prod_{i<K} r_i! / prod m_i!."""
    K = len(zlegs)
    out = []

    def rec(i, r_prev, rs, cnum, mden):
        k = zlegs[i]
        targets = [p] if i == K - 1 else range(max(0, r_prev - k), r_prev + k + 1)
        for r in targets:
            d = r - r_prev
            if (d + k) % 2 or abs(d) > k:
                continue
            j = (d + k) // 2              # creations
            m = r_prev - (k - j)          # after the annihilations
            if m < 0:
                continue
            c = cnum * comb(k, j)
            md = mden * factorial(m)
            if i == K - 1:
                num = 1
                for rr in [p] + rs:
                    num *= factorial(rr)
                out.append((tuple(rs), Fr(c * num, md)))
            else:
                rec(i + 1, r, rs + [r], c, md)

    rec(0, p, [], 1, 1)
    return out


# ============================================================================ line patterns (from 2D c4lib)
def pairs_of(K):
    return [(i, j) for i in range(K) for j in range(i + 1, K)]


def patterns(kinds, max_lines=None):
    K = len(kinds)
    prs = pairs_of(K)
    caps = [min(MAXLEGS[kinds[i]], MAXLEGS[kinds[j]]) for (i, j) in prs]
    out = []
    for ns in itertools.product(*[range(c + 1) for c in caps]):
        if max_lines is not None and sum(ns) > max_lines:
            continue
        n = dict(zip(prs, ns))
        legs = [sum(v for (a, b), v in n.items() if a == i or b == i) for i in range(K)]
        if any(legs[i] > MAXLEGS[kinds[i]] for i in range(K)):
            continue
        out.append(n)
    return out


def slice_counts(n, K):
    return [sum(v for (i, j), v in n.items() if i <= s < j) for s in range(K - 1)]


def legs_of(n, K):
    return [sum(v for (a, b), v in n.items() if a == i or b == i) for i in range(K)]


def reverse_pattern(n, K):
    return {(K - 1 - j, K - 1 - i): v for (i, j), v in n.items()}


def pattern_key(n):
    return tuple(sorted(n.items()))


# ============================================================================ densities
def toeplitz_lower(a, nrow, ncol=None):
    """T[i, j] = a[i - j] (j <= i), shape (nrow+1, ncol+1)."""
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


def conv_axis(X, a, axis):
    n = X.shape[axis] - 1
    if n == 0:
        return X * a[0]
    if a[0] == 1.0 and not np.any(a[1:n + 1]):
        return X
    T = toeplitz_lower(a, n)
    X = np.ascontiguousarray(X)
    sh = X.shape
    if axis == 0:
        return (T @ X.reshape(sh[0], -1)).reshape(sh)
    if axis == X.ndim - 1:
        return (X.reshape(-1, sh[-1]) @ T.T).reshape(sh)
    return np.matmul(T, X)


def _scatter3_py(v13, v14, v24, N0, N1, N2):
    out = np.zeros((N0 + 1, N1 + 1, N2 + 1))
    for u in range(min(N0, N1, N2) + 1):
        for a in range(N0 - u + 1):
            for b in range(N2 - u + 1):
                if a + u + b <= N1:
                    out[a + u, a + u + b, u + b] += v14[u] * v13[a] * v24[b]
    return out


if HAVE_NUMBA:
    _scatter3 = njit(cache=True)(_scatter3_py)
else:  # pragma: no cover
    _scatter3 = _scatter3_py


def build_rho_dense(K, arr, Ns):
    """All-parity density rho(N) = [z^N] prod_b arr[b](z^{e_b}) on prod [0, Ns[s]] (reference implementation)."""
    if K == 2:
        return np.array(arr[(0, 1)][: Ns[0] + 1], dtype=float)
    if K == 3:
        L0 = np.zeros((Ns[0] + 1, Ns[1] + 1))
        d = min(Ns[0], Ns[1])
        L0[np.arange(d + 1), np.arange(d + 1)] = arr[(0, 2)][: d + 1]
        X = conv_axis(L0, arr[(0, 1)], 0)
        return conv_axis(X, arr[(1, 2)], 1)
    if K == 4:
        X = _scatter3(np.ascontiguousarray(arr[(0, 2)]), np.ascontiguousarray(arr[(0, 3)]),
                      np.ascontiguousarray(arr[(1, 3)]), Ns[0], Ns[1], Ns[2])
        X = conv_axis(X, arr[(0, 1)], 0)
        X = conv_axis(X, arr[(1, 2)], 1)
        return conv_axis(X, arr[(2, 3)], 2)
    raise ValueError(K)


def even_part(R):
    return np.ascontiguousarray(R[tuple(slice(0, None, 2) for _ in range(R.ndim))])


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


def density4_stream(s12, s13, s14, s23, s24, s34, N, block=32):
    """Even-parity four-vertex density R[i1, i2, i3] = rho(2 i1, 2 i2, 2 i3), i_s <= N//2, streamed over blocks of
    the slice-1 level s1 = a + u before the bundle-12 convolution (memory: R + O(block N^2))."""
    if not (isinstance(block, (int, np.integer)) and block >= 1):
        raise ValueError(f"block must be a positive integer, got {block!r}")
    H = N // 2 + 1
    R = np.zeros((H, H, H))
    T23e = toeplitz_even_rows(s23, N)                   # (H, N+1)
    T34e = toeplitz_even_rows(s34, N)
    T12e = toeplitz_even_rows(s12, N)
    v13 = np.ascontiguousarray(s13[: N + 1])
    v14 = np.ascontiguousarray(s14[: N + 1])
    v24 = np.ascontiguousarray(s24[: N + 1])
    for lo in range(0, N + 1, block):
        hi = min(N + 1, lo + block)
        B = hi - lo
        X0 = _scatter_block(v13, v14, v24, N, lo, hi)   # (N+1, B, N+1): [s2, j, s3]; zero for s2 < lo
        Y = T23e[:, lo:] @ X0[lo:].reshape(N + 1 - lo, B * (N + 1))        # (H, B*(N+1)): [N2e, j, s3]
        del X0
        Z = Y.reshape(H * B, N + 1) @ T34e.T                                # (H*B, H): [N2e, j, N3e]
        del Y
        Z = np.ascontiguousarray(Z.reshape(H, B, H).transpose(1, 0, 2)).reshape(B, H * H)
        i0 = (lo + 1) // 2                                                  # first even N1 >= lo
        if i0 < H:
            _gemm_acc(R[i0:].reshape(H - i0, H * H), T12e[i0:, lo:hi], Z)
        del Z
    return R


def _gemm_acc(C, A, B):
    """C += A @ B in place (C C-contiguous 2D view), without a temporary of the size of C: dgemm on the transposed
    (Fortran-contiguous) views, C^T += B^T A^T.  Falls back to row chunks if BLAS would copy."""
    from scipy.linalg.blas import dgemm
    Ct = C.T
    if Ct.flags.f_contiguous and C.dtype == np.float64:
        At = np.asfortranarray(np.ascontiguousarray(A).T)          # (k, m) Fortran
        Bt = B.T                                                    # (n, k), Fortran view of C-contiguous B
        if not Bt.flags.f_contiguous:
            Bt = np.asfortranarray(Bt)
        out = dgemm(1.0, Bt, At, beta=1.0, c=Ct, overwrite_c=1)
        if np.shares_memory(out, C):
            return
        C[...] = out.T                                              # BLAS copied: still correct, just slower
        return
    for a in range(0, C.shape[0], 64):
        C[a:a + 64] += A[a:a + 64] @ B


def density3_even(s01, s02, s12, N):
    """Even-parity three-vertex density R[i0, i1] = sum_c s02[c] s01[2 i0 - c] s12[2 i1 - c]
    = (T01e diag(s02) T12e^T)[i0, i1]."""
    T01e = toeplitz_even_rows(s01, N)
    T12e = toeplitz_even_rows(s12, N)
    return (T01e * np.asarray(s02[: N + 1])[None, :]) @ T12e.T


def density_even(K, n, ser, Ns, deriv_vertex=None, stream=True, block=32):
    """Even-parity density of pattern n (optionally with one first-eps-derivative vertex).
    Axes with Ns[s] = 0 have length 1 (no lines in that slice)."""
    prs = pairs_of(K)
    base = {b: ser.S[n[b]] for b in prs}
    terms = []
    if deriv_vertex is None:
        terms.append(base)
    else:
        for b in prs:
            if deriv_vertex in b and n[b] > 0:
                t = dict(base)
                t[b] = ser.dS[n[b]]
                terms.append(t)
    R = None
    for arr in terms:
        if K == 3 and stream and Ns[0] > 0 and Ns[1] > 0 and Ns[0] == Ns[1]:
            X = density3_even(arr[(0, 1)], arr[(0, 2)], arr[(1, 2)], Ns[0])
        elif K == 4 and stream and all(x > 0 for x in Ns) and len(set(Ns)) == 1:
            X = density4_stream(arr[(0, 1)], arr[(0, 2)], arr[(0, 3)], arr[(1, 2)], arr[(1, 3)], arr[(2, 3)],
                                Ns[0], block)
        else:
            X = even_part(build_rho_dense(K, arr, Ns))
        R = X if R is None else R + X
    return R


# ============================================================================ shells
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


def shell_sums(R, Gs, Es, M, nchunk=64):
    if R.ndim == 1:
        return _shell1(R, Gs[0], Es[0], M)
    if R.ndim == 2:
        return _shell2(R, Gs[0], Gs[1], Es[0], Es[1], M)
    return _shell3(R, Gs[0], Gs[1], Gs[2], Es[0], Es[1], Es[2], M, nchunk)


def slice_arrays(delta, nlines, pw, length):
    """Weights and shell indices of one slice over even chi levels N = 0, 2, .., 2(length-1).
    g = 1/den^pw, den = N + (delta + n)/4 (the sign (-1)^pw and the factor (delta + n)^q of the slice operator
    (P-p)^q R^pw are in the exact key amplitude, pattern_keys); g = 0 where N < n (infeasible).
    Shell index (offset) e = 4N + delta + n + MOFF."""
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


# ============================================================================ chains
def pattern_keys(kinds, slice_ops, n, deriv_vertex=None):
    """Exact per-key amplitudes {delta: [A_0, A_1, A_2, A_3]} of pattern n (Wick count x vertex coefficients x
    zero-mode path amplitude x slice factors (delta+n)^q (-1)^pow), Q projector applied."""
    K = len(kinds)
    legs = legs_of(n, K)
    if deriv_vertex is not None and legs[deriv_vertex] == 0:
        return {}
    nsl = slice_counts(n, K)
    zl = [MAXLEGS[kinds[i]] - legs[i] for i in range(K)]
    combf = Fr(1)
    for i in range(K):
        combf *= factorial(legs[i])
    for v in n.values():
        combf /= factorial(v)
    vc = Fr(1)
    for i in range(K):
        vc *= vcoef(kinds[i], legs[i])
    keyamp = {}
    for p in PS:
        for rs, amp in zero_mode_paths(p, zl):
            deltas = tuple(r - p for r in rs)
            fac = Fr(1)
            ok = True
            for s in range(K - 1):
                if nsl[s] == 0 and deltas[s] == 0:
                    ok = False
                    break
                pw, q = slice_ops[s]
                fac *= Fr(deltas[s] + nsl[s]) ** q * (-1) ** pw
            if not ok or fac == 0:
                continue
            keyamp.setdefault(deltas, [Fr(0)] * 4)
            keyamp[deltas][p] += combf * vc * amp * fac
    return {k: v for k, v in keyamp.items() if any(x != 0 for x in v)}


def key_shells(kinds, slice_ops, n, Lmax, ser, deriv_vertex=None, R=None, stream=True, block=32):
    """Shell arrays of every key of pattern n.  Returns (keys {delta: amps}, shells (T, cut4max+1+MOFF), R)."""
    K = len(kinds)
    keyamp = pattern_keys(kinds, slice_ops, n, deriv_vertex)
    if not keyamp:
        return {}, None, None
    nsl = slice_counts(n, K)
    Ns = [Lmax if nsl[s] > 0 else 0 for s in range(K - 1)]
    if R is None:
        R = density_even(K, n, ser, Ns, deriv_vertex, stream=stream, block=block)
    keys = list(keyamp)
    M = 4 * Lmax + 1 + MOFF
    Gs, Es = [], []
    for s in range(K - 1):
        pw = slice_ops[s][0]
        ga, ea = [], []
        for k in keys:
            g, e = slice_arrays(k[s], nsl[s], pw, R.shape[s])
            ga.append(g)
            ea.append(e)
        Gs.append(np.ascontiguousarray(np.array(ga)))
        Es.append(np.ascontiguousarray(np.array(ea)))
    sh = shell_sums(R, Gs, Es, M)
    return {k: keyamp[k] for k in keys}, sh, R


def reduce_keys(keyamp, sh, prefs=("1",)):
    """Per-key reduction with exact weights.  For every prefactor f(p):
       Shp[f][p]  = sum_delta f(p) A_p(delta) S_delta              (per-p shells; X_p(c) = cumsum up to c - p)
       Shw[f][w]  = sum_delta [sum_p w_p f(p) A_p(delta)] S_delta  (exact functional weight per key)"""
    keys = list(keyamp)
    out = {}
    for f in prefs:
        fp = [PREFACTORS[f](p) for p in PS]
        A = [[fp[p] * keyamp[k][p] for p in PS] for k in keys]
        Shp = np.zeros((4, sh.shape[1]))
        for p in PS:
            c = np.array([float(A[t][p]) for t in range(len(keys))])
            Shp[p] = c @ sh
        Shw = {}
        for wn, w in FUNCTIONALS.items():
            c = np.array([float(sum(w[p] * A[t][p] for p in PS)) for t in range(len(keys))])
            Shw[wn] = c @ sh
        out[f] = dict(Shp=Shp, Shw=Shw)
    return out


def functional_from_reduced(red, wname):
    """F_w(c) for c = 0..cut4max:  cumsum(Shw)[c] - sum_p w_p sum_{j<p} Shp[p][c-j]   (indices with offset)."""
    w = FUNCTIONALS[wname]
    Shw = red["Shw"][wname]
    cum = np.cumsum(Shw)
    nc = len(Shw) - MOFF                       # c = 0..cut4max
    out = cum[MOFF:].copy()
    for p in PS:
        if w[p] == 0 or p == 0:
            continue
        for j in range(p):
            # Shp[p] at shell m = c - j  -> index c - j + MOFF
            out -= float(w[p]) * red["Shp"][p][MOFF - j: MOFF - j + nc]
    return out


def perp_from_reduced(red, p):
    """X_p(c) = sum_{m <= c - p} Shp[p][m], c = 0..cut4max."""
    cum = np.cumsum(red["Shp"][p])
    nc = len(cum) - MOFF
    return cum[MOFF - p: MOFF - p + nc]


def add_reduced(acc, red, mult=1.0):
    for f, d in red.items():
        if f not in acc:
            acc[f] = dict(Shp=np.zeros_like(d["Shp"]), Shw={k: np.zeros_like(v) for k, v in d["Shw"].items()})
        acc[f]["Shp"] += mult * d["Shp"]
        for k in d["Shw"]:
            acc[f]["Shw"][k] += mult * d["Shw"][k]
    return acc


def chain_reduced(kinds, slice_ops, Lmax, ser, deriv_vertex=None, prefs=("1",), mirror=False, stream=True,
                  pattern_filter=None):
    """Reduced shells of a whole chain (serial).  mirror=True: one representative per reversal pair, doubled
    (valid only for reversal-symmetric chains)."""
    K = len(kinds)
    pats = patterns(kinds)
    if pattern_filter is not None:
        pats = [n for n in pats if pattern_filter(n)]
    items = [(n, 1.0) for n in pats]
    if mirror:
        reps = {}
        for n in pats:
            key = min(pattern_key(n), pattern_key(reverse_pattern(n, K)))
            reps.setdefault(key, [n, 0])
            reps[key][1] += 1
        items = [(n, float(m)) for n, m in reps.values()]
    acc = {}
    for n, mult in items:
        keyamp, sh, R = key_shells(kinds, slice_ops, n, Lmax, ser, deriv_vertex, stream=stream)
        del R                                   # release the density before the next pattern is built
        if not keyamp:
            continue
        add_reduced(acc, reduce_keys(keyamp, sh, prefs), mult)
    if not acc:
        M = 4 * Lmax + 1 + MOFF
        for f in prefs:
            acc[f] = dict(Shp=np.zeros((4, M)), Shw={k: np.zeros(M) for k in FUNCTIONALS})
    return acc


# ============================================================================ two-vertex chains with eps derivatives
def _mul(a, b, N, order=2):
    out = {}
    for (i1, j1), x in a.items():
        for (i2, j2), y in b.items():
            if i1 + i2 + j1 + j2 > order:
                continue
            key = (i1 + i2, j1 + j2)
            z = np.convolve(x, y)[: N + 1]
            out[key] = out.get(key, 0) + z
    return out


def two_vertex_series(m, d1, d2, ser):
    """d1! d2! [eps1^d1 eps2^d2] (W(y; eps1, eps2) - 1)^m, W - 1 = sum_{k>=1} u_k(eps1) u_k(eps2) y^k (all parities)."""
    N = ser.N
    c = ser.chi
    A, B = ser.a, ser.b
    base = {(0, 0): c, (1, 0): c * A, (0, 1): c * A, (2, 0): c * (B + A * A / 2), (0, 2): c * (B + A * A / 2),
            (1, 1): c * A * A}
    one = np.zeros(N + 1)
    one[0] = 1.0
    pw = {(0, 0): one}
    for _ in range(m):
        pw = _mul(pw, base, N)
    return factorial(d1) * factorial(d2) * pw.get((d1, d2), np.zeros(N + 1))


def chain2_keys(kinds, derivs, slice_op, Lmax, ser):
    """Key-level records of <p| X_2 s X_1 |p> (X_i with eps-derivative order derivs[i], total <= 2):
    list of (amps[4], shells) per (m, delta)."""
    pw, q = slice_op
    recs = []
    M = 4 * Lmax + 1 + MOFF
    for m in range(0, min(MAXLEGS[kinds[0]], MAXLEGS[kinds[1]]) + 1):
        if m == 0 and (derivs[0] or derivs[1]):
            continue
        zl = [MAXLEGS[kinds[0]] - m, MAXLEGS[kinds[1]] - m]
        pref = vcoef(kinds[0], m) * vcoef(kinds[1], m) * factorial(m)
        keyamp = {}
        for p in PS:
            for rs, amp in zero_mode_paths(p, zl):
                dlt = rs[0] - p
                if m == 0 and dlt == 0:
                    continue
                a = pref * amp * Fr(dlt + m) ** q * (-1) ** pw
                if a == 0:
                    continue
                keyamp.setdefault(dlt, [Fr(0)] * 4)
                keyamp[dlt][p] += a
        if not keyamp:
            continue
        if m == 0:
            Rm = np.array([1.0])
        else:
            Rm = even_part(two_vertex_series(m, derivs[0], derivs[1], ser)[: Lmax + 1])
        keys = list(keyamp)
        Gs, Es = [], []
        for k in keys:
            g, e = slice_arrays(k, m, pw, len(Rm))
            Gs.append(g)
            Es.append(e)
        sh = shell_sums(Rm, [np.array(Gs)], [np.array(Es)], M)
        for t, k in enumerate(keys):
            recs.append(((m, k), keyamp[k], sh[t]))
    return recs


def chain2_reduced(kinds, derivs, slice_op, Lmax, ser, prefs=("1",)):
    acc = {}
    for _, amps, sh in chain2_keys(kinds, derivs, slice_op, Lmax, ser):
        add_reduced(acc, reduce_keys({0: amps}, sh[None, :], prefs))
    return acc
