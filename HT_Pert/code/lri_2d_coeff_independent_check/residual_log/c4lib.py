#!/usr/bin/env python3
"""Exact finite-cutoff fourth-order coefficient C_4(L) of the 2D LRI Hamiltonian truncation (SPEC.md).

Diagram-sum formulation (derivation in README.md):
  * zero mode (0,0) treated as an oscillator (exact rational path amplitudes), non-zero modes chi by Wick
    contraction of normal-ordered theta-averaged vertices;
  * a chain of K vertices has K-1 time slices; a bundle of n chi lines between vertices i<j crosses the slices
    i..j-1; denominators depend on the zero-mode number and on the total chi level of the slice;
  * the mode weight factorizes, w_ab = v(a) v(b), v(a) = (x)_a/a!; J = a - b conservation at every vertex is
    equivalent to J = 0 in every slice, i.e. (holomorphic level) = (antiholomorphic level) = sigma in every
    slice.  With (W - 1)^n = sum_k C(n,k)(-1)^(n-k) V_k(y) V_k(ybar), V_k = (1-y)^(-k x), the J-resolved
    density of a line pattern at slice levels s = 2 sigma is
        R_n(sigma) = sum_{k <= n} c_k(n) rho_k(sigma)^2,
        rho_k(sigma) = [z^sigma] prod_bundles V_{k_b}(prod_{slices crossed} z_s).
    No angular-momentum loop has to be summed explicitly; the cost of a 4-vertex chain is O(N^4) BLAS work per
    configuration and O(N^3) per contraction, N = L_max/2, and the density does not depend on L, so a single
    run yields every even L <= L_max (shell prefix sums over max(sigma)).
"""
import itertools
import math
from fractions import Fraction as Fr
from math import comb, factorial

import numpy as np

try:
    import numba
    from numba import njit, prange
    HAVE_NUMBA = True
except Exception:  # pragma: no cover
    HAVE_NUMBA = False

G1 = Fr(1, 3)
MAXLEGS = {"V": 4, "M": 2}


def vcoef(kind, m):
    """Coefficient of :Z^{maxlegs-m}: (x) <:chi^m:> in the vertex."""
    if kind == "V":
        return Fr(comb(4, m), 12)
    if kind == "M":
        return Fr(comb(2, m), 1)
    raise ValueError(kind)


# ============================================================================ holomorphic series
class Series:
    """Holomorphic coefficient arrays at x = 1/2 up to level N."""

    def __init__(self, N, kmax=8):
        self.N = N
        v = np.zeros((kmax + 1, N + 1))
        for k in range(kmax + 1):
            v[k, 0] = 1.0
            for j in range(1, N + 1):
                v[k, j] = v[k, j - 1] * (k / 2.0 + j - 1) / j
        self.v = v
        # d/deps V_k(y) = (k/4) log(1-y) V_k(y);  log(1-y) = -sum y^n/n
        L1 = np.zeros(N + 1)
        L1[1:] = 1.0 / np.arange(1, N + 1)
        dv = np.zeros_like(v)
        for k in range(1, kmax + 1):
            dv[k] = -(k / 4.0) * np.convolve(L1, v[k])[: N + 1]
        self.dv = dv
        # per-mode quantities for the two-vertex Taylor machinery (x = 1/2 - eps/4)
        a = np.arange(N + 1)
        from scipy.special import digamma, polygamma
        h1 = digamma(0.5 + a) - digamma(0.5)
        h2 = polygamma(1, 0.5) - polygamma(1, 0.5 + a)
        self.A = -h1 / 8.0          # sqrt(v(eps) v(0)) = v exp(A eps + B eps^2 + ...)
        self.B = -h2 / 64.0


# ============================================================================ zero-mode paths
def zero_mode_paths(p, zlegs):
    """Closed paths p = r_0 -> r_1 -> ... -> r_K = p, vertex i applying :Z^{zlegs[i]}: (normal ordered).
    Yields (r_1..r_{K-1}, exact amplitude) with amplitude = prod C(k_i, j_i) * prod_{i<K} r_i! / prod m_i!."""
    K = len(zlegs)
    out = []

    def rec(i, r_prev, rs, cnum, mden):
        k = zlegs[i]
        if i == K - 1:
            targets = [p]
        else:
            targets = range(max(0, r_prev - k), r_prev + k + 1)
        for r in targets:
            d = r - r_prev
            if (d + k) % 2 or abs(d) > k:
                continue
            j = (d + k) // 2              # creations
            m = r_prev - (k - j)          # after annihilations
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


# ============================================================================ line patterns
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


# ============================================================================ densities
def toeplitz_lower(a, n):
    from scipy.linalg import toeplitz
    c = np.asarray(a[: n + 1], dtype=float)
    return toeplitz(c, np.zeros(n + 1))


def conv_axis(X, a, axis):
    """Convolve X along `axis` with the series a (truncated to the axis length)."""
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
    # middle axis of a 3D array: batched GEMM over axis 0
    return np.matmul(T, X)


if HAVE_NUMBA:
    @njit(cache=True)
    def _scatter3(v13, v14, v24, N0, N1, N2):
        out = np.zeros((N0 + 1, N1 + 1, N2 + 1))
        for u in range(min(N0, N1, N2) + 1):
            x14 = v14[u]
            if x14 == 0.0:
                continue
            for a in range(N0 - u + 1):
                x13 = v13[a]
                if x13 == 0.0:
                    continue
                s1 = a + u
                for b in range(N2 - u + 1):
                    s2 = a + u + b
                    if s2 > N1:
                        break
                    out[s1, s2, u + b] += x14 * x13 * v24[b]
        return out
else:  # pragma: no cover
    def _scatter3(v13, v14, v24, N0, N1, N2):
        out = np.zeros((N0 + 1, N1 + 1, N2 + 1))
        for u in range(min(N0, N1, N2) + 1):
            for a in range(N0 - u + 1):
                for b in range(N2 - u + 1):
                    if a + u + b <= N1:
                        out[a + u, a + u + b, u + b] += v14[u] * v13[a] * v24[b]
        return out


def build_rho(K, arr, Ns):
    """rho(sigma) = [z^sigma] prod_b A_b(z^{e_b}) on the box prod [0, Ns[s]], arr[(i,j)] = series of bundle (i,j)."""
    if K == 2:
        return np.array(arr[(0, 1)][: Ns[0] + 1], dtype=float)
    if K == 3:
        L0 = np.zeros((Ns[0] + 1, Ns[1] + 1))
        d = min(Ns[0], Ns[1])
        L0[np.arange(d + 1), np.arange(d + 1)] = arr[(0, 2)][: d + 1]
        X = conv_axis(L0, arr[(0, 1)], 0)
        X = conv_axis(X, arr[(1, 2)], 1)
        return X
    if K == 4:
        X = _scatter3(np.ascontiguousarray(arr[(0, 2)]), np.ascontiguousarray(arr[(0, 3)]),
                      np.ascontiguousarray(arr[(1, 3)]), Ns[0], Ns[1], Ns[2])
        X = conv_axis(X, arr[(0, 1)], 0)
        X = conv_axis(X, arr[(1, 2)], 1)
        X = conv_axis(X, arr[(2, 3)], 2)
        return X
    raise ValueError(K)


if HAVE_NUMBA:
    @njit(parallel=True, cache=True)
    def _acc_sq(R, X, c):
        """R += c * X**2 (flattened, in place)."""
        r = R.reshape(-1)
        x = X.reshape(-1)
        for i in prange(r.size):
            r[i] += c * x[i] * x[i]
else:  # pragma: no cover
    def _acc_sq(R, X, c):
        R += c * X * X


if HAVE_NUMBA:
    @njit(cache=True)
    def _scatter3_block(v13, v14, v24, N0, N1, N2, s3lo, s3hi):
        """Scatter of the long bundles restricted to sigma_3 in [s3lo, s3hi)."""
        out = np.zeros((N0 + 1, N1 + 1, s3hi - s3lo))
        for u in range(min(N0, N1, N2) + 1):
            x14 = v14[u]
            if x14 == 0.0:
                continue
            for a in range(N0 - u + 1):
                x13 = v13[a]
                if x13 == 0.0:
                    continue
                s1 = a + u
                blo = s3lo - u if s3lo - u > 0 else 0
                for b in range(blo, N2 - u + 1):
                    s3 = u + b
                    if s3 >= s3hi:
                        break
                    s2 = a + u + b
                    if s2 > N1:
                        break
                    out[s1, s2, s3 - s3lo] += x14 * x13 * v24[b]
        return out


def density4(n, ser, Ns, block=32):
    """Low-memory version of density4_ref (two full N^3 arrays: R and X1).
    X1 = (long-bundle scatter) convolved along sigma_1 with bundle 12, built in sigma_3 blocks; the sigma_2
    (bundle 23) and sigma_3 (bundle 34) convolutions act within fixed-sigma_1 slabs and are done slab-block
    by slab-block, accumulating c * X3^2 into R directly."""
    R = np.zeros(tuple(x + 1 for x in Ns))
    sgn = lambda b, kb: comb(n[b], kb) * (-1) ** (n[b] - kb)
    N0, N1, N2 = Ns
    for k13 in range(n[(0, 2)] + 1):
        for k14 in range(n[(0, 3)] + 1):
            for k24 in range(n[(1, 3)] + 1):
                cL = sgn((0, 2), k13) * sgn((0, 3), k14) * sgn((1, 3), k24)
                v13 = np.ascontiguousarray(ser.v[k13]); v14 = np.ascontiguousarray(ser.v[k14])
                v24 = np.ascontiguousarray(ser.v[k24])
                for k12 in range(n[(0, 1)] + 1):
                    X1 = np.empty((N0 + 1, N1 + 1, N2 + 1))
                    for lo in range(0, N2 + 1, block):
                        hi = min(N2 + 1, lo + block)
                        X0b = _scatter3_block(v13, v14, v24, N0, N1, N2, lo, hi)
                        X1[:, :, lo:hi] = conv_axis(X0b, ser.v[k12], 0)
                        del X0b
                    T1 = [None if k23 == 0 else toeplitz_lower(ser.v[k23], N1) for k23 in range(n[(1, 2)] + 1)]
                    T2t = [None if k34 == 0 else toeplitz_lower(ser.v[k34], N2).T.copy()
                           for k34 in range(n[(2, 3)] + 1)]
                    cc = {(k23, k34): float(cL * sgn((0, 1), k12) * sgn((1, 2), k23) * sgn((2, 3), k34))
                          for k23 in range(n[(1, 2)] + 1) for k34 in range(n[(2, 3)] + 1)}
                    for lo in range(0, N0 + 1, block):
                        hi = min(N0 + 1, lo + block)
                        Xs = X1[lo:hi]
                        for k23 in range(n[(1, 2)] + 1):
                            X2s = Xs if T1[k23] is None else np.matmul(T1[k23], Xs)
                            for k34 in range(n[(2, 3)] + 1):
                                X3s = X2s if T2t[k34] is None else np.matmul(X2s, T2t[k34])
                                _acc_sq(R[lo:hi], np.ascontiguousarray(X3s), cc[(k23, k34)])
                    del X1
    _mask_infeasible(R, n, 4, Ns)
    return R


def density4_ref(n, ser, Ns):
    """K = 4, no derivative: R_n = sum_k c_k rho_k^2, sharing the scatter of the long bundles (13, 14, 24)
    and the axis convolutions of the local bundles (12 -> axis 0, 23 -> axis 1, 34 -> axis 2)."""
    R = np.zeros(tuple(x + 1 for x in Ns))
    sgn = lambda b, kb: comb(n[b], kb) * (-1) ** (n[b] - kb)
    for k13 in range(n[(0, 2)] + 1):
        for k14 in range(n[(0, 3)] + 1):
            for k24 in range(n[(1, 3)] + 1):
                cL = sgn((0, 2), k13) * sgn((0, 3), k14) * sgn((1, 3), k24)
                X0 = _scatter3(np.ascontiguousarray(ser.v[k13]), np.ascontiguousarray(ser.v[k14]),
                               np.ascontiguousarray(ser.v[k24]), Ns[0], Ns[1], Ns[2])
                for k12 in range(n[(0, 1)] + 1):
                    X1 = conv_axis(X0, ser.v[k12], 0)
                    for k23 in range(n[(1, 2)] + 1):
                        X2 = conv_axis(X1, ser.v[k23], 1)
                        for k34 in range(n[(2, 3)] + 1):
                            X3 = np.ascontiguousarray(conv_axis(X2, ser.v[k34], 2))
                            c = cL * sgn((0, 1), k12) * sgn((1, 2), k23) * sgn((2, 3), k34)
                            _acc_sq(R, X3, float(c))
                            del X3
                        del X2
                    del X1
                del X0
    _mask_infeasible(R, n, 4, Ns)
    return R


def _mask_infeasible(R, n, K, Ns):
    """The infeasible region (slice level 2 sigma < number of lines crossing the slice) is exactly zero."""
    for s, ns_ in enumerate(slice_counts(n, K)):
        lo = (ns_ + 1) // 2
        if lo > 0:
            idx = [slice(None)] * len(Ns)
            idx[s] = slice(0, min(lo, Ns[s] + 1))
            R[tuple(idx)] = 0.0


def density(K, n, ser, Ns, deriv_vertex=None):
    """J-projected chi density R_n(sigma) of pattern n (optionally with one first-eps-derivative vertex)."""
    prs = pairs_of(K)
    delta = np.zeros(ser.N + 1)
    delta[0] = 1.0
    R = np.zeros(tuple(x + 1 for x in Ns))
    ranges = [range(n[b] + 1) for b in prs]
    for ks in itertools.product(*ranges):
        c = 1
        for b, kb in zip(prs, ks):
            c *= comb(n[b], kb) * (-1) ** (n[b] - kb)
        arr = {b: ser.v[kb] for b, kb in zip(prs, ks)}
        rho = build_rho(K, arr, Ns)
        if deriv_vertex is None:
            R += c * rho * rho
        else:
            for b, kb in zip(prs, ks):
                if deriv_vertex in b and kb > 0:
                    arr2 = dict(arr)
                    arr2[b] = ser.dv[kb]
                    R += c * build_rho(K, arr2, Ns) * rho
    _mask_infeasible(R, n, K, Ns)
    return R


# ============================================================================ contraction
if HAVE_NUMBA:
    @njit(cache=True)
    def _shell1(R, G0, N):
        T = G0.shape[0]
        out = np.zeros((T, N + 1))
        for s0 in range(R.shape[0]):
            r = R[s0]
            if r == 0.0:
                continue
            for t in range(T):
                out[t, s0] += r * G0[t, s0]
        return out

    @njit(cache=True)
    def _shell2(R, G0, G1_, N):
        T = G0.shape[0]
        out = np.zeros((T, N + 1))
        for s0 in range(R.shape[0]):
            for s1 in range(R.shape[1]):
                r = R[s0, s1]
                if r == 0.0:
                    continue
                M = s0 if s0 > s1 else s1
                for t in range(T):
                    out[t, M] += r * G0[t, s0] * G1_[t, s1]
        return out

    @njit(parallel=True, cache=True)
    def _shell3(R, G0, G1_, G2, N):
        T = G0.shape[0]
        n0 = R.shape[0]
        buf = np.zeros((n0, T, N + 1))
        for s0p in prange(n0):
            s0 = np.int64(s0p)
            for s1 in range(R.shape[1]):
                m01 = s0 if s0 > s1 else s1
                for s2 in range(R.shape[2]):
                    r = R[s0, s1, s2]
                    if r == 0.0:
                        continue
                    M = m01 if m01 > s2 else s2
                    for t in range(T):
                        buf[s0, t, M] += r * G0[t, s0] * G1_[t, s1] * G2[t, s2]
        return buf.sum(axis=0)


def shell_sums(R, Gs, N):
    S = R.ndim
    if S == 1:
        return _shell1(R, Gs[0], N)
    if S == 2:
        return _shell2(R, Gs[0], Gs[1], N)
    return _shell3(R, Gs[0], Gs[1], Gs[2], N)


def slice_G(alpha, pw, nlines, length):
    sig = np.arange(length)
    den = alpha + 2.0 * sig
    g = np.zeros(length)
    ok = 2 * sig >= nlines
    if np.any(den[ok] == 0.0):
        raise RuntimeError("zero energy denominator")
    g[ok] = 1.0 / den[ok] ** pw
    return g


# ============================================================================ chains with K >= 3 (and K = 2 plain)
def chain_pattern(kinds, slice_ops, n, N, ser, ps=(0, 1, 2, 3), deriv_vertex=None):
    """Contribution of one chi-line pattern n to <p| X_K s_{K-1} ... s_1 X_1 |p>, for every cutoff
    L = 2M, M = 0..N.  Returns {p: array} or None if the pattern does not contribute."""
    K = len(kinds)
    legs = legs_of(n, K)
    if deriv_vertex is not None and legs[deriv_vertex] == 0:
        return None  # derivative of a pure zero-mode vertex vanishes
    nsl = slice_counts(n, K)
    zl = [MAXLEGS[kinds[i]] - legs[i] for i in range(K)]
    combf = Fr(1)
    for i in range(K):
        combf *= factorial(legs[i])
    for b, v in n.items():
        combf /= factorial(v)
    vc = Fr(1)
    for i in range(K):
        vc *= vcoef(kinds[i], legs[i])
    keyamp = {}
    for p in ps:
        for rs, amp in zero_mode_paths(p, zl):
            deltas = tuple(r - p for r in rs)
            ok = True
            fac = Fr(1)
            for s_ in range(K - 1):
                if nsl[s_] == 0 and deltas[s_] == 0:
                    ok = False   # Q projector: the reference state itself is excluded
                    break
                pw, q = slice_ops[s_]
                fac *= Fr(deltas[s_] + nsl[s_]) ** q * (-1) ** pw
            if not ok or fac == 0:
                continue
            keyamp.setdefault(deltas, {}).setdefault(p, Fr(0))
            keyamp[deltas][p] += combf * vc * amp * fac
    keyamp = {k: d for k, d in keyamp.items() if any(v != 0 for v in d.values())}
    if not keyamp:
        return None
    Ns = [N if nsl[s_] > 0 else 0 for s_ in range(K - 1)]
    if K == 4 and deriv_vertex is None:
        R = density4(n, ser, Ns)
    else:
        R = density(K, n, ser, Ns, deriv_vertex)
    keys = list(keyamp)
    Gs = []
    for s_ in range(K - 1):
        pw = slice_ops[s_][0]
        Gs.append(np.array([slice_G((k[s_] + nsl[s_]) / 2.0, pw, nsl[s_], Ns[s_] + 1) for k in keys]))
    sh = shell_sums(R, Gs, N)
    del R
    cum = np.cumsum(sh, axis=1)
    res = {p: np.zeros(N + 1) for p in ps}
    for t, k in enumerate(keys):
        for p, a in keyamp[k].items():
            res[p] += float(a) * cum[t]
    return res


def reverse_pattern(n, K):
    return {(K - 1 - j, K - 1 - i): v for (i, j), v in n.items()}


def pattern_key(n):
    return tuple(sorted(n.items()))


def chain(kinds, slice_ops, N, ser, ps=(0, 1, 2, 3), deriv_vertex=None, max_lines=None, verbose=False,
          pattern_filter=None):
    """<p| X_K s_{K-1} ... s_1 X_1 |p> for every cutoff L = 2M, M = 0..N.
    kinds[i] in {'V','M'} (vertex 0 acts first); slice_ops[s] = (pow, q): slice operator (P-p)^q R^pow,
    R = Q/(E0 - H0) = -1/den.  deriv_vertex: index of a vertex carrying d/deps of its weights (first order).
    Returns {p: array of length N+1} (value at cutoff L = 2M)."""
    res = {p: np.zeros(N + 1) for p in ps}
    pats = patterns(kinds, max_lines)
    if pattern_filter is not None:
        pats = [n for n in pats if pattern_filter(n)]
    for n in pats:
        r = chain_pattern(kinds, slice_ops, n, N, ser, ps, deriv_vertex)
        if r is None:
            continue
        for p in ps:
            res[p] += r[p]
        if verbose:
            print("pattern", {f"{i}{j}": v for (i, j), v in n.items() if v}, flush=True)
    return res


# ============================================================================ two-vertex chains with eps derivatives
def _mul(a, b, N, order=2):
    """Product of truncated bivariate eps-series of holomorphic arrays: dict (i,j) -> array."""
    out = {}
    for (i1, j1), x in a.items():
        for (i2, j2), y in b.items():
            if i1 + i2 + j1 + j2 > order:
                continue
            key = (i1 + i2, j1 + j2)
            z = np.convolve(x, y)[: N + 1]
            out[key] = out.get(key, 0) + z
    return out


def two_vertex_density(m, d1, d2, ser):
    """J-projected density of a bundle of m lines between vertex 1 (eps1-derivative order d1) and vertex 2
    (order d2): d1! d2! [eps1^d1 eps2^d2] (Vt(y)Vt(ybar) - 1)^m at y = ybar levels sigma."""
    N = ser.N
    v1 = ser.v[1]
    A, B = ser.A, ser.B
    base = {(0, 0): v1, (1, 0): v1 * A, (0, 1): v1 * A, (2, 0): v1 * (B + A * A / 2), (0, 2): v1 * (B + A * A / 2),
            (1, 1): v1 * A * A}
    one = np.zeros(N + 1)
    one[0] = 1.0
    powk = {(0, 0): one}
    R = np.zeros(N + 1)
    for k in range(0, m + 1):
        if k > 0:
            powk = _mul(powk, base, N)
        c = comb(m, k) * (-1) ** (m - k)
        acc = np.zeros(N + 1)
        for (i1, j1), x in powk.items():
            i2, j2 = d1 - i1, d2 - j1
            if i2 < 0 or j2 < 0 or (i2, j2) not in powk:
                continue
            acc += x * powk[(i2, j2)]
        R += c * acc
    R *= factorial(d1) * factorial(d2)
    R[: (m + 1) // 2] = 0.0
    return R


def chain2(kinds, derivs, slice_op, N, ser, ps=(0, 1, 2, 3), per_key=False, shells=False):
    """<p| X_2 s X_1 |p>, X_i of kind kinds[i] with eps-derivative order derivs[i] (<= 2 in total).
    slice_op = (pow, q).  Returns {p: array over M} (or, with per_key, the raw (m, delta) decomposition)."""
    res = {p: np.zeros(N + 1) for p in ps}
    pw, q = slice_op
    parts = []
    for m in range(0, min(MAXLEGS[kinds[0]], MAXLEGS[kinds[1]]) + 1):
        if m == 0 and (derivs[0] or derivs[1]):
            continue
        zl = [MAXLEGS[kinds[0]] - m, MAXLEGS[kinds[1]] - m]
        pref = vcoef(kinds[0], m) * vcoef(kinds[1], m) * factorial(m)
        Rm = two_vertex_density(m, derivs[0], derivs[1], ser) if m > 0 else None
        for p in ps:
            for rs, amp in zero_mode_paths(p, zl):
                dlt = rs[0] - p
                if m == 0 and dlt == 0:
                    continue
                a = pref * amp * Fr(dlt + m) ** q * (-1) ** pw
                if a == 0:
                    continue
                if m == 0:
                    if shells:
                        val = np.zeros(N + 1)
                        val[0] = float(a) / (dlt / 2.0) ** pw
                    else:
                        val = np.full(N + 1, float(a) / (dlt / 2.0) ** pw)
                    parts.append((p, m, dlt, a, None))
                else:
                    g = slice_G((dlt + m) / 2.0, pw, m, N + 1)
                    val = float(a) * (Rm * g if shells else np.cumsum(Rm * g))
                    parts.append((p, m, dlt, a, Rm))
                res[p] += val
    if per_key:
        return res, parts
    return res


if HAVE_NUMBA:
    @njit(cache=True)
    def window_sum(h, de):
        """out[M] = sum_{sigma=1}^{M} h[sigma] * (e(M) - e(M - sigma)), e(M) = sum_{j<=M} de[j], evaluated as
        sum_sigma h[sigma] * sum_{t<sigma} de[M - t] (no subtraction of large cumulative sums)."""
        N = h.shape[0] - 1
        out = np.zeros(N + 1)
        for M in range(1, N + 1):
            S = 0.0
            acc = 0.0
            for sg in range(1, M + 1):
                S += de[M - sg + 1]
                acc += h[sg] * S
            out[M] = acc
        return out


def Pi(f):
    return f[2] - f[1] - (f[3] - f[0]) / 3.0
