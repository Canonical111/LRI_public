#!/usr/bin/env python3
"""General diagram engine for the eps-expansion of the 2D LRI level-truncated Hamiltonian (any order, K <= 5 vertices).

Same formulation as ../c4lib.py (zero mode as an oscillator with exact rational path amplitudes; chi lines by Wick
contraction; J-projected holomorphic factorization of the chi level sums; one run gives every even cutoff), extended
to
  * any number of vertices K (densities on a box with one axis per slice that carries chi lines),
  * eps-Taylor (derivative) orders d_i at any vertex (line weight sqrt(w(eps_i) w(eps_j)), Taylor in both),
  * rank reduction: a bundle whose angular momentum is fixed to zero by the slice constraints (it has no component in
    the null space of the slice-incidence matrix) contributes the rank-1 kernel D_n(u) (x) 1 instead of the
    (n+1)-term inclusion-exclusion sum (exact: only the diagonal u = ubar of its kernel is ever used),
  * general slice operators (R^pow (P-p)^q) and open zero-mode paths (start z0, end z1).

lib_opt (2026-10-14, large_L): faster no-derivative density (_density_tree): memoized tree over the inclusion-exclusion
terms (long-bundle product built once per long-bundle combination, local-bundle axis convolutions shared level by
level), parallel diagonal-convolution scatter for >= 4 long bundles, U(0) skipped, U(2m) = (1-y)^(-m) as m cumulative
sums, in-place parallel accumulation.  Switch off with ENGINE_TREE=0 (then identical to ../lib/engine.py).

Conventions (as c4lib): vertex 0 acts first; slice s lies between vertices s and s+1; a bundle (i, j), i < j, crosses
slices i..j-1; sigma_s = holomorphic level of slice s (slice level 2 sigma_s); den_s = (delta_s + n_s)/2 + 2 sigma_s
(energy of the slice state above the reference E^0_p = p/2, delta_s = zero-mode shift, n_s = number of chi lines);
R = Q/(E^0 - H0) = -1/den.
"""
import itertools
import os
from fractions import Fraction as Fr
from math import comb, factorial

import numpy as np

try:
    from numba import njit, prange
    HAVE_NUMBA = True
except Exception:  # pragma: no cover
    HAVE_NUMBA = False

MAXLEGS = {"V": 4, "M": 2}


def vcoef(kind, m):
    if kind == "V":
        return Fr(comb(4, m), 12)
    if kind == "M":
        return Fr(comb(2, m), 1)
    raise ValueError(kind)


# ======================================================================================= per-mode eps-Taylor series
class Modes:
    """v_a = (1/2)_a/a!;  e_a^[m] = [eps^m] exp(phi_a(eps)),  phi_a(eps) = (1/2) ln(v_a(eps)/v_a(0)), x = 1/2 - eps/4,
    so that sqrt(v_a(eps_i) v_a(eps_j)) = v_a * sum_{alpha,beta} e_a^[alpha] e_a^[beta] eps_i^alpha eps_j^beta."""

    def __init__(self, N, dmax=3):
        self.N, self.dmax = N, dmax
        a = np.arange(N + 1)
        v = np.ones(N + 1)
        for j in range(1, N + 1):
            v[j] = v[j - 1] * (j - 0.5) / j
        self.v = v
        # phi_a(eps) = -sum_m eps^m H_a^(m) / (2 m 2^m),  H_a^(m) = sum_{t<a} (2t+1)^-m
        phi = np.zeros((dmax + 1, N + 1))
        for m in range(1, dmax + 1):
            t = np.arange(N, dtype=float)
            Hm = np.concatenate([[0.0], np.cumsum((2 * t + 1) ** (-float(m)))])[: N + 1]
            phi[m] = -Hm / (2.0 * m * 2.0 ** m)
        # exp of the series
        e = np.zeros((dmax + 1, N + 1))
        e[0] = 1.0
        for m in range(1, dmax + 1):     # e^[m] = (1/m) sum_{k=1}^m k phi^[k] e^[m-k]
            acc = np.zeros(N + 1)
            for k in range(1, m + 1):
                acc += k * phi[k] * e[m - k]
            e[m] = acc / m
        self.e = e
        self._U = {}
        self._D = {}

    def line(self, al, be):
        return self.v * self.e[al] * self.e[be]

    def U(self, k, al, be):
        """[eps_i^al eps_j^be] (sum_a sqrt(v_a(eps_i) v_a(eps_j)) y^a)^k, y-series of length N+1."""
        key = (k, al, be)
        if key in self._U:
            return self._U[key]
        N = self.N
        if k == 0:
            out = np.zeros(N + 1)
            if al == 0 and be == 0:
                out[0] = 1.0
        else:
            out = np.zeros(N + 1)
            for a1 in range(al + 1):
                for b1 in range(be + 1):
                    out += np.convolve(self.line(a1, b1), self.U(k - 1, al - a1, be - b1))[: N + 1]
        self._U[key] = out
        return out

    def sqrtD(self, n):
        key = ("sqrt", n)
        if key not in self._D:
            d = self.D(n, 0, 0)
            if np.any(d < -1e-300):
                raise ValueError("negative J=0 density")
            self._D[key] = np.sqrt(np.maximum(d, 0.0))
        return self._D[key]

    def D(self, n, al, be):
        """diagonal kernel of an n-line bundle: [eps_i^al eps_j^be] sum_k C(n,k)(-1)^(n-k) U_k(u) U_k(u) (hol and antihol
        at the same level u).  D(n,0,0) = R_n of c4lib (J = 0 density of n lines at level 2u)."""
        key = (n, al, be)
        if key in self._D:
            return self._D[key]
        out = np.zeros(self.N + 1)
        for k in range(n + 1):
            c = comb(n, k) * (-1) ** (n - k)
            for a1 in range(al + 1):
                for b1 in range(be + 1):
                    out += c * self.U(k, a1, b1) * self.U(k, al - a1, be - b1)
        out[: (n + 1) // 2] = 0.0
        self._D[key] = out
        return out


# ======================================================================================= patterns
def pairs_of(K):
    return [(i, j) for i in range(K) for j in range(i + 1, K)]


_PAT_CACHE = {}


def patterns(kinds, max_lines=None, min_zero_legs=0):
    """All chi-line patterns (dict (i,j) -> n_ij > 0) with legs_i <= MAXLEGS, optional total-line cap and minimum
    number of zero-mode legs.  Recursive enumeration with leg budgets (cached)."""
    key = (tuple(kinds), max_lines, min_zero_legs)
    if key in _PAT_CACHE:
        return _PAT_CACHE[key]
    K = len(kinds)
    prs = pairs_of(K)
    cap = [MAXLEGS[k] for k in kinds]
    total_legs = sum(cap)
    maxl = max_lines if max_lines is not None else 10 ** 9
    maxl = min(maxl, (total_legs - min_zero_legs) // 2)
    out = []
    left = list(cap)
    cur = {}

    def rec(idx, nlines):
        if idx == len(prs):
            out.append(dict(cur))
            return
        i, j = prs[idx]
        top = min(left[i], left[j], maxl - nlines)
        for v in range(top + 1):
            if v:
                cur[(i, j)] = v
            left[i] -= v
            left[j] -= v
            rec(idx + 1, nlines + v)
            left[i] += v
            left[j] += v
            if v:
                del cur[(i, j)]

    rec(0, 0)
    _PAT_CACHE[key] = out
    return out


def legs_of(n, K):
    return [sum(v for (a, b), v in n.items() if a == i or b == i) for i in range(K)]


def slice_counts(n, K):
    return [sum(v for (i, j), v in n.items() if i <= s < j) for s in range(K - 1)]


def cycle_bundles(n, K):
    """bundles with a nonzero component in the null space of the slice-incidence matrix (free angular momentum)."""
    bundles = [b for b, v in n.items() if v]
    if not bundles:
        return set()
    A = np.array([[1.0 if b[0] <= s < b[1] else 0.0 for b in bundles] for s in range(K - 1)])
    u, sv, vt = np.linalg.svd(A)
    rank = int((sv > 1e-9).sum())
    ns = vt[rank:]
    return {b for k, b in enumerate(bundles) if len(ns) and not np.allclose(ns[:, k], 0.0)}


# ======================================================================================= zero-mode paths
def zero_mode_paths(z0, zlegs, z1=None):
    """Paths z0 = r_0 -> r_1 -> ... -> r_K = z1 (z1 = z0 if None), vertex i applying :Z^{zlegs[i]}: (normal ordered).
    Yields (r_1..r_{K-1}, amplitude) with amplitude = prod_i <r_{i+1}| :Z^k_i: |r_i> in the NORMALIZED basis
    (sqrt factors combined exactly: returned as (rational, sqrt-argument rational) -> float product for open paths;
    for closed paths the sqrt argument is a perfect product and the amplitude is rational)."""
    if z1 is None:
        z1 = z0
    K = len(zlegs)
    out = []

    def rec(i, r_prev, rs, cnum, sq):
        k = zlegs[i]
        targets = [z1] if i == K - 1 else range(max(0, r_prev - k), r_prev + k + 1)
        for r in targets:
            d = r - r_prev
            if (d + k) % 2 or abs(d) > k:
                continue
            j = (d + k) // 2
            m = r_prev - (k - j)
            if m < 0:
                continue
            # <r| (a^dag)^j a^(k-j) |r_prev> = sqrt(r_prev!/m!) sqrt(r!/m!)
            c = cnum * comb(k, j)
            s2 = sq * Fr(factorial(r_prev) * factorial(r), factorial(m) ** 2)
            if i == K - 1:
                out.append((tuple(rs), c, s2))
            else:
                rec(i + 1, r, rs + [r], c, s2)

    rec(0, z0, [], 1, Fr(1))
    res = []
    for rs, c, s2 in out:
        # closed paths: s2 is a perfect square of a rational
        num, den = s2.numerator, s2.denominator
        rn, rd = _isqrt(num), _isqrt(den)
        if rn is not None and rd is not None:
            res.append((rs, Fr(c) * Fr(rn, rd)))
        else:
            res.append((rs, float(c) * float(s2) ** 0.5))
    return res


def _isqrt(x):
    from math import isqrt
    r = isqrt(x)
    return r if r * r == x else None


# ======================================================================================= density on a box
if HAVE_NUMBA:
    @njit(cache=True, nogil=True)
    def _scatter(shape, spans, series, nb):
        """out[sigma] = sum_{u_b} prod_b series[b, u_b], sigma_s = sum_{b: spans[b,0] <= s < spans[b,1]} u_b.
        shape: (S,) box extents (+1); spans: (nb, 2) slice ranges; series: (nb, Nmax+1)."""
        S = shape.shape[0]
        out = np.zeros(int(np.prod(shape)))
        strides = np.ones(S, dtype=np.int64)
        for s in range(S - 2, -1, -1):
            strides[s] = strides[s + 1] * shape[s + 1]
        if nb == 0:
            out[0] = 1.0
            return out
        # max level of each bundle = min extent over its slices
        umax = np.zeros(nb, dtype=np.int64)
        for b in range(nb):
            mm = 1 << 60
            for s in range(spans[b, 0], spans[b, 1]):
                if shape[s] - 1 < mm:
                    mm = shape[s] - 1
            umax[b] = mm
        u = np.zeros(nb, dtype=np.int64)
        sig = np.zeros(S, dtype=np.int64)
        while True:
            # evaluate current tuple
            ok = True
            for s in range(S):
                if sig[s] >= shape[s]:
                    ok = False
                    break
            if ok:
                w = 1.0
                for b in range(nb):
                    w *= series[b, u[b]]
                if w != 0.0:
                    idx = 0
                    for s in range(S):
                        idx += sig[s] * strides[s]
                    out[idx] += w
            # odometer increment
            b = nb - 1
            while b >= 0:
                if u[b] < umax[b]:
                    u[b] += 1
                    for s in range(spans[b, 0], spans[b, 1]):
                        sig[s] += 1
                    break
                else:
                    for s in range(spans[b, 0], spans[b, 1]):
                        sig[s] -= u[b]
                    u[b] = 0
                    b -= 1
            if b < 0:
                break
        return out


if HAVE_NUMBA:
    @njit(cache=True, nogil=True)
    def _diag_conv(X, shape, lo, hi, f):
        """Y[sigma] = sum_u f[u] X[sigma - u (e_lo + ... + e_{hi-1})] on the flattened box (one bundle crossing the
        slices lo..hi-1): the generating-function product with f(z_lo ... z_{hi-1})."""
        S = shape.shape[0]
        total = X.shape[0]
        strides = np.ones(S, dtype=np.int64)
        for s in range(S - 2, -1, -1):
            strides[s] = strides[s + 1] * shape[s + 1]
        step = 0
        for s in range(lo, hi):
            step += strides[s]
        nf = f.shape[0]
        Y = np.zeros(total)
        for idx in range(total):
            r = idx
            m = 1 << 60
            for s in range(S):
                q = r // strides[s]
                r -= q * strides[s]
                if lo <= s < hi and q < m:
                    m = q
            if m > nf - 1:
                m = nf - 1
            acc = 0.0
            for u in range(m + 1):
                acc += f[u] * X[idx - u * step]
            Y[idx] = acc
        return Y


if HAVE_NUMBA:
    @njit(parallel=True, cache=True)
    def _diag_conv_par(X, shape, lo, hi, f):
        """_diag_conv with prange over the output index (every Y[idx] is written by one iteration; the inner sum has
        the same order as _diag_conv, so the result is bitwise identical)."""
        S = shape.shape[0]
        total = X.shape[0]
        strides = np.ones(S, dtype=np.int64)
        for s in range(S - 2, -1, -1):
            strides[s] = strides[s + 1] * shape[s + 1]
        step = 0
        for s in range(lo, hi):
            step += strides[s]
        nf = f.shape[0]
        Y = np.zeros(total)
        for ip in prange(total):
            idx = np.int64(ip)
            r = idx + 0
            m = 1 << 60
            for s in range(S):
                q = r // strides[s]
                r -= q * strides[s]
                if lo <= s < hi and q < m:
                    m = q
            if m > nf - 1:
                m = nf - 1
            acc = 0.0
            for u in range(m + 1):
                acc += f[u] * X[idx - u * step]
            Y[idx] = acc
        return Y

    @njit(parallel=True, cache=True)
    def _acc_sq4(R, X, c):
        """R += c * X * X elementwise for 4D arrays of any strides (same per-element operation order as numpy's
        R += c * X * X)."""
        n0, n1, n2, n3 = X.shape
        for a in prange(n0):
            for b in range(n1):
                for d in range(n2):
                    for e in range(n3):
                        x = X[a, b, d, e]
                        R[a, b, d, e] += c * x * x


if HAVE_NUMBA:
    @njit(parallel=True, cache=True)
    def _cumsum3(X3):
        """cumulative sum along axis 1 of a C-contiguous (pre, n, post) array; same sequential order as np.cumsum."""
        pre, n, post = X3.shape
        Y = np.empty_like(X3)
        nb = (post + 255) // 256
        for t in prange(pre * nb):
            a = t // nb
            b0 = (t % nb) * 256
            b1 = b0 + 256
            if b1 > post:
                b1 = post
            for c in range(b0, b1):
                Y[a, 0, c] = X3[a, 0, c]
            for j in range(1, n):
                for c in range(b0, b1):
                    Y[a, j, c] = Y[a, j - 1, c] + X3[a, j, c]
        return Y

    @njit(parallel=True, cache=True)
    def _acc_sq_flat(R, X, c):
        """R += c * X * X on flat C-contiguous arrays."""
        for i in prange(R.shape[0]):
            x = X[i]
            R[i] += c * x * x


if HAVE_NUMBA:
    @njit(parallel=True, cache=True)
    def _diag_conv4(X, lo, hi, f):
        """_diag_conv for a C-contiguous 4D box, streaming order: for every output element the sum over u runs in
        increasing u starting from 0.0, exactly as in _diag_conv (bitwise identical result)."""
        n0, n1, n2, n3 = X.shape
        e0 = 1 if (lo <= 0 < hi) else 0
        e1 = 1 if (lo <= 1 < hi) else 0
        e2 = 1 if (lo <= 2 < hi) else 0
        e3 = 1 if (lo <= 3 < hi) else 0
        nf = f.shape[0]
        Y = np.zeros_like(X)
        for a in prange(n0):
            for u in range(nf):
                if e0 == 1 and u > a:
                    break
                b0 = u * e1
                c0 = u * e2
                d0 = u * e3
                if b0 >= n1 or c0 >= n2 or d0 >= n3:
                    break
                fu = f[u]
                asrc = a - u * e0
                for b in range(b0, n1):
                    bs = b - u * e1
                    for c in range(c0, n2):
                        cs = c - u * e2
                        for d in range(d0, n3):
                            Y[a, b, c, d] += fu * X[asrc, bs, cs, d - u * e3]
        return Y


def _split3(sh, axis):
    pre = 1
    for x in sh[:axis]:
        pre *= x
    post = 1
    for x in sh[axis + 1:]:
        post *= x
    return pre, sh[axis], post


def conv_axis_c(X, a, axis):
    """conv_axis for C-contiguous arrays without moveaxis copies: batched GEMM on the (pre, n, post) view."""
    X = np.ascontiguousarray(X)
    sh = X.shape
    pre, n, post = _split3(sh, axis)
    if n == 1:
        return X * a[0]
    T = _toeplitz(a, n - 1)
    if post == 1:
        Y = X.reshape(pre, n) @ T.T
    elif pre == 1:
        Y = T @ X.reshape(n, post)
    else:
        Y = np.matmul(T, X.reshape(pre, n, post))
    return np.ascontiguousarray(Y).reshape(sh)


def cumsum_axis_c(X, axis):
    X = np.ascontiguousarray(X)
    sh = X.shape
    pre, n, post = _split3(sh, axis)
    if not HAVE_NUMBA:
        return np.cumsum(X, axis=axis)
    return _cumsum3(X.reshape(pre, n, post)).reshape(sh)


def _toeplitz(a, n):
    from scipy.linalg import toeplitz
    c = np.asarray(a[: n + 1], dtype=float)
    return toeplitz(c, np.zeros(n + 1))


def conv_axis(X, a, axis):
    n = X.shape[axis] - 1
    if n == 0:
        return X * a[0]
    T = _toeplitz(a, n)
    Xm = np.moveaxis(X, axis, 0)
    sh = Xm.shape
    Y = (T @ Xm.reshape(sh[0], -1)).reshape(sh)
    return np.moveaxis(Y, 0, axis)


def build_rho(K, bundles, series, Ns):
    """rho(sigma) = [z^sigma] prod_b series_b(prod_{s in b} z_s) on the box prod_s [0, Ns[s]].
    bundles: list of (i, j); series: list of y-series (length >= max N + 1)."""
    S = K - 1
    shape = np.array([x + 1 for x in Ns], dtype=np.int64)
    local = [(b, f) for b, f in zip(bundles, series) if b[1] - b[0] == 1]
    longb = [(b, f) for b, f in zip(bundles, series) if b[1] - b[0] > 1]
    Nmax = max(Ns) if Ns else 0
    if longb and len(longb) > S + 1:
        # many long bundles: sequential diagonal convolutions, O(nlong N^(S+1)) instead of the O(N^nlong) odometer
        X = np.zeros(int(np.prod(shape)))
        X[0] = 1.0
        for b, f in longb:
            m = min(len(f), Nmax + 1)
            X = _diag_conv(X, shape, b[0], b[1], np.ascontiguousarray(f[:m], dtype=np.float64))
        X = X.reshape(tuple(shape))
    elif longb:
        spans = np.array([[b[0], b[1]] for b, _ in longb], dtype=np.int64)
        ser = np.zeros((len(longb), Nmax + 1))
        for k, (_, f) in enumerate(longb):
            m = min(len(f), Nmax + 1)
            ser[k, :m] = f[:m]
        X = _scatter(shape, spans, ser, len(longb)).reshape(tuple(shape))
    else:
        X = np.zeros(tuple(shape))
        X[(0,) * S] = 1.0
    for b, f in local:
        X = conv_axis(X, f, b[0])
    return X


def density(kinds, n, Ns, modes, derivs=None):
    """J-projected chi density with eps-Taylor orders derivs[i] at vertex i:
    R^(d)(sigma) = [prod eps_i^d_i] sum_k c_k rho_k^hol(sigma) rho_k^anti(sigma), with rank-1 kernels for pinned bundles."""
    K = len(kinds)
    if derivs is None:
        derivs = [0] * K
    bundles = [b for b, v in n.items() if v]
    cyc = cycle_bundles(n, K)
    # derivative slots: (bundle index, side, vertex) ; side 0 = hol, 1 = anti; pinned bundles: only side 0
    slots_by_vertex = {i: [] for i in range(K)}
    for bi, b in enumerate(bundles):
        sides = (0, 1) if b in cyc else (0,)
        for side in sides:
            for v in b:
                slots_by_vertex[v].append((bi, side, v))
    # enumerate distributions of d_i units over the slots of vertex i
    per_vertex = []
    for i in range(K):
        di = derivs[i]
        sl = slots_by_vertex[i]
        if di == 0:
            per_vertex.append([{}])
            continue
        if not sl:
            return None  # derivative of a vertex with no chi legs: zero (w_00 does not depend on eps)
        opts = []
        for comp in _compositions(di, len(sl)):
            opts.append({sl[k]: comp[k] for k in range(len(sl)) if comp[k]})
        per_vertex.append(opts)
    shape = tuple(x + 1 for x in Ns)
    R = np.zeros(shape)
    cyc_list = [bi for bi, b in enumerate(bundles) if b in cyc]
    ones = np.ones(modes.N + 1)
    nod = all(d == 0 for d in derivs)
    if nod and os.environ.get("ENGINE_TREE", "1") == "1":
        R = _density_tree(K, n, Ns, modes, bundles, cyc)
        for s, ns_ in enumerate(slice_counts(n, K)):
            lo = (ns_ + 1) // 2
            if lo > 0:
                idx = [slice(None)] * len(Ns)
                idx[s] = slice(0, min(lo, Ns[s] + 1))
                R[tuple(idx)] = 0.0
        return R
    nth = int(os.environ.get("ENGINE_THREADS", "1"))
    if nth > 1:
        return _density_threaded(K, n, Ns, modes, bundles, cyc, cyc_list, per_vertex, nod, ones, shape, nth)
    for combo in itertools.product(*per_vertex):
        assign = {}
        for d in combo:
            assign.update(d)

        def orders(bi, side):
            b = bundles[bi]
            return assign.get((bi, side, b[0]), 0), assign.get((bi, side, b[1]), 0)

        for ks in itertools.product(*[range(n[bundles[bi]] + 1) for bi in cyc_list]):
            c = 1
            kmap = {}
            for bi, k in zip(cyc_list, ks):
                nb = n[bundles[bi]]
                c *= comb(nb, k) * (-1) ** (nb - k)
                kmap[bi] = k
            if nod:
                # no eps derivatives: pinned bundles use sqrt(R_n) on both sides -> hol = anti, one build
                ser = [modes.U(kmap[bi], 0, 0) if b in cyc else modes.sqrtD(n[b]) for bi, b in enumerate(bundles)]
                rh = build_rho(K, bundles, ser, Ns)
                R += c * rh * rh
                continue
            ser_h, ser_a = [], []
            for bi, b in enumerate(bundles):
                if b in cyc:
                    ser_h.append(modes.U(kmap[bi], *orders(bi, 0)))
                    ser_a.append(modes.U(kmap[bi], *orders(bi, 1)))
                else:
                    ser_h.append(modes.D(n[b], *orders(bi, 0)))
                    ser_a.append(ones)
            rh = build_rho(K, bundles, ser_h, Ns)
            ra = build_rho(K, bundles, ser_a, Ns)
            R += c * rh * ra
    # infeasible region exactly zero
    for s, ns_ in enumerate(slice_counts(n, K)):
        lo = (ns_ + 1) // 2
        if lo > 0:
            idx = [slice(None)] * len(Ns)
            idx[s] = slice(0, min(lo, Ns[s] + 1))
            R[tuple(idx)] = 0.0
    return R


def _build_long(shape, Ns, longb, series):
    """product of the long bundles (spanning >= 2 slices) on the box: odometer scatter for <= 3 long bundles (as
    build_rho), parallel sequential diagonal convolutions for more."""
    S = len(Ns)
    shp = np.array(shape, dtype=np.int64)
    Nmax = max(Ns) if Ns else 0
    if not longb:
        X = np.zeros(int(np.prod(shp)))
        X[0] = 1.0
        return X.reshape(shape)
    if len(longb) <= 3 or not HAVE_NUMBA:
        spans = np.array([[b[0], b[1]] for b in longb], dtype=np.int64)
        ser = np.zeros((len(longb), Nmax + 1))
        for k, f in enumerate(series):
            m = min(len(f), Nmax + 1)
            ser[k, :m] = f[:m]
        return _scatter(shp, spans, ser, len(longb)).reshape(shape)
    strides = np.ones(S, dtype=np.int64)
    for s_ in range(S - 2, -1, -1):
        strides[s_] = strides[s_ + 1] * shp[s_ + 1]
    X = np.zeros(int(np.prod(shp)))
    # first bundle on a delta: exactly its series along its diagonal
    b, f = longb[0], series[0]
    umax = min(int(shp[s_]) - 1 for s_ in range(b[0], b[1]))
    umax = min(umax, len(f) - 1)
    step = int(sum(strides[s_] for s_ in range(b[0], b[1])))
    X[np.arange(umax + 1) * step] = f[: umax + 1]
    for b, f in zip(longb[1:], series[1:]):
        m = min(len(f), Nmax + 1)
        X = _diag_conv_par(X, shp, b[0], b[1], np.ascontiguousarray(f[:m], dtype=np.float64))
    return X.reshape(shape)


def conv_axis_fft(X, a, axis, J=None):
    """axis convolution by real FFT (scipy.fft, multithreaded), with the first J entries along the axis computed exactly
    (direct sums), where the FFT's norm-wise error would be largest relative to the (small) values."""
    import scipy.fft as sf
    n = X.shape[axis]
    if J is None:
        J = int(os.environ.get("ENGINE_FFT_J", "24"))
    if n <= 2 * J:
        return conv_axis(X, a, axis)
    nth = int(os.environ.get("OMP_NUM_THREADS", "1"))
    nfft = sf.next_fast_len(2 * n - 1, real=True)
    f = np.asarray(a[:n], dtype=float)
    Ff = sf.rfft(f, n=nfft)
    shp = [1] * X.ndim
    shp[axis] = Ff.shape[0]
    Xf = sf.rfft(X, n=nfft, axis=axis, workers=nth)
    Xf *= Ff.reshape(shp)
    Y = sf.irfft(Xf, n=nfft, axis=axis, workers=nth)
    del Xf
    sl = [slice(None)] * X.ndim
    sl[axis] = slice(0, n)
    Y = np.ascontiguousarray(Y[tuple(sl)])
    # exact head: y_j = sum_{i <= j} f_{j-i} x_i for j < J
    Xh = np.moveaxis(X, axis, 0)[:J]
    T = _toeplitz(f, J - 1)
    head = np.tensordot(T, Xh, axes=(1, 0))
    Ym = np.moveaxis(Y, axis, 0)
    Ym[:J] = head
    return Y


def _conv_fast(X, f, axis, k):
    """axis convolution with the bundle series f; k = U index for cycle bundles (None for pinned sqrtD series):
    U(0) = identity (skipped), U(2m) = (1-y)^(-m) as m cumulative sums, otherwise Toeplitz (conv_axis) or, with
    ENGINE_CONV=fft, the hybrid FFT convolution."""
    if k == 0:
        return X
    if k is not None and k % 2 == 0 and os.environ.get("ENGINE_CUMSUM", "1") == "1":
        Y = X
        for _ in range(k // 2):
            Y = cumsum_axis_c(Y, axis)
        return Y
    if os.environ.get("ENGINE_CONV", "toeplitz") == "fft":
        return conv_axis_fft(X, f, axis)
    return conv_axis_c(X, f, axis)


def _density_tree(K, n, Ns, modes, bundles, cyc):
    """no-derivative density sum_k c_k rho_k^2 with the inclusion-exclusion terms evaluated as a memoized tree."""
    shape = tuple(x + 1 for x in Ns)
    longb = [b for b in bundles if b[1] - b[0] > 1]
    local = [b for b in bundles if b[1] - b[0] == 1]

    def options(b):
        nb = n[b]
        if b in cyc:
            return [(comb(nb, k) * (-1) ** (nb - k), k, modes.U(k, 0, 0)) for k in range(nb + 1)]
        return [(1, None, modes.sqrtD(nb))]

    R = np.zeros(shape)
    if os.environ.get("ENGINE_ORDER", "1") == "1":
        # shallow levels first for bundles with few options (pinned: 1): the deepest level is evaluated once per leaf
        local = sorted(local, key=lambda b: ((n[b] + 1) if b in cyc else 1, b))
    long_opts = [options(b) for b in longb]
    loc_opts = [options(b) for b in local]
    four = len(shape) == 4 and HAVE_NUMBA

    def recurse(X, j, c):
        if j == len(local):
            if HAVE_NUMBA:
                _acc_sq_flat(R.reshape(-1), np.ascontiguousarray(X).reshape(-1), float(c))
            else:
                R[...] += c * X * X
            return
        b = local[j]
        for (cl, k, f) in loc_opts[j]:
            Y = _conv_fast(X, f, b[0], k)
            recurse(Y, j + 1, c * cl)
            del Y

    if len(longb) <= 3 or len(shape) != 4 or not HAVE_NUMBA or os.environ.get("ENGINE_LONGTREE", "1") != "1":
        for combo in itertools.product(*long_opts):
            c0 = 1
            for (cl, _, _) in combo:
                c0 *= cl
            X = _build_long(shape, list(Ns), longb, [f for (_, _, f) in combo])
            recurse(X, 0, c0)
            del X
        return R
    # >= 4 long bundles on a 4D box: memoized tree over the long bundles as well (pinned / few options first);
    # first bundle placed on its diagonal, the others by the parallel per-element diagonal convolution
    # (_diag_conv4, the streaming variant, is bitwise identical but ~10x slower at N = 150: not used)
    order = sorted(range(len(longb)), key=lambda i: ((n[longb[i]] + 1) if longb[i] in cyc else 1, longb[i]))
    lb = [longb[i] for i in order]
    lo_ = [long_opts[i] for i in order]
    Nmax = max(Ns)

    def place_first(b, f):
        X = np.zeros(shape)
        umax = min(shape[s_] - 1 for s_ in range(b[0], b[1]))
        umax = min(umax, len(f) - 1)
        idx = [np.zeros(umax + 1, dtype=np.int64)] * 4
        u = np.arange(umax + 1)
        idx = tuple(u if (b[0] <= s_ < b[1]) else np.zeros(umax + 1, dtype=np.int64) for s_ in range(4))
        X[idx] = f[: umax + 1]
        return X

    def lrec(X, j, c):
        if j == len(lb):
            recurse(X, 0, c)
            return
        b = lb[j]
        for (cl, k, f) in lo_[j]:
            if j == 0:
                Y = place_first(b, f)
            else:
                m = min(len(f), Nmax + 1)
                Y = _diag_conv_par(np.ascontiguousarray(X).reshape(-1), np.array(shape, dtype=np.int64), b[0], b[1],
                                   np.ascontiguousarray(f[:m], dtype=np.float64)).reshape(shape)
            lrec(Y, j + 1, c * cl)
            del Y

    lrec(None, 0, 1)
    return R


def _density_terms(n, bundles, cyc, cyc_list, per_vertex, nod, ones, modes):
    """the (coefficient, hol series, anti series or None) terms of density(), in the serial order."""
    for combo in itertools.product(*per_vertex):
        assign = {}
        for d in combo:
            assign.update(d)

        def orders(bi, side):
            b = bundles[bi]
            return assign.get((bi, side, b[0]), 0), assign.get((bi, side, b[1]), 0)

        for ks in itertools.product(*[range(n[bundles[bi]] + 1) for bi in cyc_list]):
            c = 1
            kmap = {}
            for bi, k in zip(cyc_list, ks):
                nb = n[bundles[bi]]
                c *= comb(nb, k) * (-1) ** (nb - k)
                kmap[bi] = k
            if nod:
                yield c, [modes.U(kmap[bi], 0, 0) if b in cyc else modes.sqrtD(n[b]) for bi, b in enumerate(bundles)], None
                continue
            ser_h, ser_a = [], []
            for bi, b in enumerate(bundles):
                if b in cyc:
                    ser_h.append(modes.U(kmap[bi], *orders(bi, 0)))
                    ser_a.append(modes.U(kmap[bi], *orders(bi, 1)))
                else:
                    ser_h.append(modes.D(n[b], *orders(bi, 0)))
                    ser_a.append(ones)
            yield c, ser_h, ser_a


def _density_threaded(K, n, Ns, modes, bundles, cyc, cyc_list, per_vertex, nod, ones, shape, nth):
    """density() with the independent box builds run in a thread pool (BLAS releases the GIL); partial sums are
    combined in a fixed order, so the result is deterministic (differs from the serial sum only by rounding)."""
    from concurrent.futures import ThreadPoolExecutor
    terms = list(_density_terms(n, bundles, cyc, cyc_list, per_vertex, nod, ones, modes))

    def work(idx):
        acc = np.zeros(shape)
        for t in idx:
            c, sh, sa = terms[t]
            rh = build_rho(K, bundles, sh, Ns)
            if sa is None:
                acc += c * rh * rh
            else:
                acc += c * rh * build_rho(K, bundles, sa, Ns)
        return acc

    groups = [list(range(i, len(terms), nth)) for i in range(min(nth, len(terms)))]
    with ThreadPoolExecutor(len(groups)) as ex:
        parts = list(ex.map(work, groups))
    R = np.zeros(shape)
    for pt in parts:
        R += pt
    for s, ns_ in enumerate(slice_counts(n, K)):
        lo = (ns_ + 1) // 2
        if lo > 0:
            idx = [slice(None)] * len(Ns)
            idx[s] = slice(0, min(lo, Ns[s] + 1))
            R[tuple(idx)] = 0.0
    return R


def _compositions(total, parts):
    if parts == 1:
        yield (total,)
        return
    for first in range(total + 1):
        for rest in _compositions(total - first, parts - 1):
            yield (first,) + rest


# ======================================================================================= shell contraction
if HAVE_NUMBA:
    @njit(parallel=True, cache=True)
    def _shell_nd(Rf, shape, Gs, N):
        """out[t, M] = sum_{max sigma = M} R[sigma] prod_s G[s, t, sigma_s]; Rf flattened, Gs (S, T, Nmax+1)."""
        S = shape.shape[0]
        T = Gs.shape[1]
        n0 = shape[0]
        inner = 1
        for s in range(1, S):
            inner *= shape[s]
        buf = np.zeros((n0, T, N + 1))
        for i0 in prange(n0):
            idx = np.zeros(S, dtype=np.int64)
            for k in range(inner):
                r = Rf[i0 * inner + k]
                if r == 0.0:
                    continue
                rem = k
                for s in range(S - 1, 0, -1):
                    idx[s] = rem % shape[s]
                    rem //= shape[s]
                idx[0] = i0
                M = 0
                for s in range(S):
                    if idx[s] > M:
                        M = idx[s]
                for t in range(T):
                    w = r
                    for s in range(S):
                        w *= Gs[s, t, idx[s]]
                    buf[i0, t, M] += w
        return buf.sum(axis=0)


def shell_sums(R, Gs_list, N):
    """Gs_list[s] = array (T, Ns+1).  Returns (T, N+1) shell sums (value contributed at max sigma = M)."""
    S = R.ndim
    T = Gs_list[0].shape[0]
    Nmax = max(g.shape[1] for g in Gs_list)
    Gs = np.zeros((S, T, Nmax))
    for s in range(S):
        Gs[s, :, : Gs_list[s].shape[1]] = Gs_list[s]
    shape = np.array(R.shape, dtype=np.int64)
    return _shell_nd(np.ascontiguousarray(R).reshape(-1), shape, Gs, N)


DROP_ZERO_DEN = False      # True only inside the no-partner Bloch construction (degenerate partners dropped)


def slice_G(alpha, pw, nlines, length, weight=None):
    """(-1)^pw / den^pw on a slice with den = alpha + 2 sigma; infeasible levels zero; optional extra weight(sigma)."""
    sig = np.arange(length)
    den = alpha + 2.0 * sig
    g = np.zeros(length)
    ok = 2 * sig >= nlines
    if np.any(den[ok] == 0.0):
        if not DROP_ZERO_DEN:
            raise RuntimeError("zero energy denominator")
        ok = ok & (den != 0.0)
    g[ok] = (-1.0) ** pw / den[ok] ** pw
    if weight is not None:
        g = g * weight[:length]
    return g


# ======================================================================================= window-resolved shells
if HAVE_NUMBA:
    @njit(parallel=True, cache=True)
    def _shell_w0(Rf, shape, Gs, N):
        """window slice = axis 0.  out[a, t, m] = sum_{sigma_0 = a, max_{s>=1} sigma_s = m} R prod_s G[s,t,sigma_s]."""
        S = shape.shape[0]
        T = Gs.shape[1]
        n0 = shape[0]
        inner = 1
        for s in range(1, S):
            inner *= shape[s]
        buf = np.zeros((n0, T, N + 1))
        for a in prange(n0):
            idx = np.zeros(S, dtype=np.int64)
            for k in range(inner):
                r = Rf[a * inner + k]
                if r == 0.0:
                    continue
                rem = k
                m = 0
                for s in range(S - 1, 0, -1):
                    idx[s] = rem % shape[s]
                    rem //= shape[s]
                    if idx[s] > m:
                        m = idx[s]
                for t in range(T):
                    w = r * Gs[0, t, a]
                    for s in range(1, S):
                        w *= Gs[s, t, idx[s]]
                    buf[a, t, m] += w
        return buf


def shell_w(R, Gs_list, N, sw):
    """(T, Nsw+1, N+1) array f[t, a, m] (window slice level a, max of the other slices m)."""
    S = R.ndim
    order = [sw] + [s for s in range(S) if s != sw]
    Rp = np.ascontiguousarray(np.transpose(R, order))
    T = Gs_list[0].shape[0]
    Nmax = max(g.shape[1] for g in Gs_list)
    Gs = np.zeros((S, T, Nmax))
    for k, s in enumerate(order):
        Gs[k, :, : Gs_list[s].shape[1]] = Gs_list[s]
    shape = np.array(Rp.shape, dtype=np.int64)
    buf = _shell_w0(Rp.reshape(-1), shape, Gs, N)
    return np.transpose(buf, (1, 0, 2))


def window_contract(f, e):
    """f[a, m] from shell_w for one key; e = array e(l), l = 0..N (hol units).  Returns
    T(M) = sum_{a <= M, m <= M} f[a, m] (e(M) - e(M - a)) for M = 0..N."""
    na, N1 = f.shape
    N = N1 - 1
    F = np.cumsum(f, axis=1)                  # F[a, M] = sum_{m <= M} f[a, m]
    out = np.zeros(N + 1)
    for M in range(N + 1):
        amax = min(M, na - 1)
        a = np.arange(amax + 1)
        out[M] = np.dot(F[: amax + 1, M], e[M] - e[M - a])
    return out
