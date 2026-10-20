#!/usr/bin/env python3
"""Exact finite-cutoff low-order coefficients of the 3D LRI Hamiltonian truncation (lri_3d_hpc model).

Model (pinned to lri_3d_hpc/reference/perturbative.py and reference/taylor_vertices.py):
  * GFF on S^2, x = (3 - eps)/4; modes (n, l, m), level N = 2n + l, energy x + N; zero mode (0,0,0) = local
    oscillator Z (amplitude 1 at every eps); bath chi = all other modes, amplitude u_{nl}(eps) sqrt(4 pi) Y_lm with
        u^2 = (x)_{n+l} (x - 1/2)_n / (n! (3/2)_{n+l});
    one bath line between vertices at Omega_i, Omega_j carries u^[a] u^[b] (2l+1) P_l(Omega_i . Omega_j)
    (a, b = eps-Taylor orders at its two ends); summed over l at fixed N this is the Gegenbauer C_N^(x).
  * H = H0 + r M + g V (+ window D), H0 = N_bath + x P_total, M = <:phi^2:>_Omega, V = <:phi^4:>_Omega / 12,
    bath cutoff N_bath <= L; the scalar, inversion-even sector is automatic for states reached from |p>.
  * reference states |p> = Z-occupation p, bath vacuum; tuning E1 - E0 = x, E3 - E0 = 3 - x;
    Delta = E2 - E0 = sum C_n eps^n.

Diagram sums: Wick contraction of the bath, zero-mode paths in exact rationals (as in the 2D project), angular
integrals by partial waves:
  * bundle (i, j) of n lines at total level N:  B(N; t) = sum_l beta[N, l] P_l(t)  (beta from Gauss-Legendre
    projection of the product of the line series; exact quadrature);
  * 2 vertices: int = beta[N, 0];
  * 3 vertices (triangle 01, 02, 12): sum_l beta01 beta02 beta12 / (2l+1)^2;
  * 4 vertices: forests (l = 0 parts), one cycle (single l channel, factor (2l+1)^-(k-1)), K4 minus an edge
    (channels (lc, ld) with the Gaunt-combined array of the shared edge).  K4 itself needs >= 6 lines and does
    not contribute to C_4 (Pi pruning, README).
Every slice level is <= L; densities do not depend on L, so shell sums over max(slice level) give every cutoff.
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

X0 = 0.75
G1 = Fr(1, 3)
MAXLEGS = {"V": 4, "M": 2}
TYPES = {(a, b): f"{max(a, b)}{min(a, b)}" for a in range(4) for b in range(4) if a + b <= 3}


def vcoef(kind, m):
    if kind == "V":
        return Fr(comb(4, m), 12)
    if kind == "M":
        return Fr(comb(2, m), 1)
    raise ValueError(kind)


# ============================================================================ modes, lines, quadrature
def mode_tables(Lmax, dps=40, dmax=2):
    """T[type][N, l] = u^[a] u^[b] (2l+1) at eps = 0 for N = 2n + l <= Lmax (N = 0: zero mode, excluded);
    type "ab" (a >= b, a + b <= dmax), u^[k] = eps-Taylor coefficients of u_{nl}(x(eps)), x = (3 - eps)/4:
    ln u^2 = const + sum_k a_k eps^k, a_k = -h_k/(k 4^k), h_k = sum_{j<n+l} (x+j)^-k + sum_{j<n} (x-1/2+j)^-k."""
    import mpmath as mp
    mp.mp.dps = dps
    x = mp.mpf(3) / 4
    kinds = [(a, b) for a in range(dmax + 1) for b in range(a + 1) if a + b <= dmax]
    T = {f"{a}{b}": np.zeros((Lmax + 1, Lmax + 1)) for (a, b) in kinds}
    for l in range(Lmax + 1):
        u2 = mp.mpf(1)
        for j in range(l):
            u2 *= (x + j) / (mp.mpf(3) / 2 + j)
        h = [None] + [sum((1 / (x + j) ** k for j in range(l)), mp.mpf(0)) for k in range(1, dmax + 1)]
        n = 0
        while 2 * n + l <= Lmax:
            N = 2 * n + l
            if N > 0:
                phi = [mp.mpf(0)] + [-h[k] / (k * mp.mpf(4) ** k) / 2 for k in range(1, dmax + 1)]
                e = [mp.mpf(1)]
                for m in range(1, dmax + 1):
                    e.append(sum(k * phi[k] * e[m - k] for k in range(1, m + 1)) / m)
                f = u2 * (2 * l + 1)
                for (a, b) in kinds:
                    T[f"{a}{b}"][N, l] = float(f * e[a] * e[b])
            # step n -> n+1: (x)_{n+l+1}/(x)_{n+l} = x+n+l; (x-1/2)_{n+1}/(x-1/2)_n = x-1/2+n; 1/(n+1); 1/(3/2+n+l)
            u2 *= (x + n + l) * (x - mp.mpf(1) / 2 + n) / ((n + 1) * (mp.mpf(3) / 2 + n + l))
            for k in range(1, dmax + 1):
                h[k] += 1 / (x + n + l) ** k + 1 / (x - mp.mpf(1) / 2 + n) ** k
            n += 1
    return T


def legendre_matrix(lmax, t):
    P = np.zeros((lmax + 1, len(t)))
    P[0] = 1.0
    if lmax >= 1:
        P[1] = t
    for l in range(1, lmax):
        P[l + 1] = ((2 * l + 1) * t * P[l] - l * P[l - 1]) / (l + 1)
    return P


class Basis:
    """Mode tables, Gauss-Legendre quadrature and a cache of bundle partial-wave arrays."""

    def __init__(self, Lmax, T=None, dmax=2):
        self.L = Lmax
        self.T = T if T is not None else mode_tables(Lmax, dmax=dmax)
        Q = Lmax + 2                      # exact for degree <= 2 Lmax + 3 (bundle projections)
        t, w = np.polynomial.legendre.leggauss(Q)
        self.t, self.w = t, w
        self.P = legendre_matrix(Lmax, t)
        self.S = {k: v @ self.P for k, v in self.T.items()}       # line series at the nodes [N, q]
        self.proj = (self.P * (w / 2.0)).T * (2 * np.arange(Lmax + 1) + 1)  # [q, l]
        self._cache = {}
        Nn = np.arange(Lmax + 1)[:, None]
        ll = np.arange(Lmax + 1)[None, :]
        self.pwmask = (ll <= Nn) & ((Nn - ll) % 2 == 0)
        self._gq = None

    def bundle_lines(self, types):
        """beta[N, l] of the product of single lines of the given types (tuple, order irrelevant)."""
        key = tuple(sorted(types))
        if key in self._cache:
            return self._cache[key]
        L = self.L
        if len(key) == 0:
            b = np.zeros((L + 1, L + 1))
            b[0, 0] = 1.0
        elif len(key) == 1:
            b = self.T[key[0]]
        else:
            B = self.S[key[0]]
            for ty in key[1:]:
                B = conv_rows(B, self.S[ty])
            b = B @ self.proj
            b[~self.pwmask] = 0.0
            b[: len(key)] = 0.0                 # each bath line has level >= 1
        self._cache[key] = b
        return b

    def bundle(self, n, da, db):
        """Bundle of n lines, eps-Taylor order da summed over the legs at one end, db at the other end
        (sum over ordered assignments to the lines)."""
        L = self.L
        if n == 0:
            if da or db:
                return None
            return self.bundle_lines(())
        key = ("ord", n, da, db)
        if key in self._cache:
            return self._cache[key]
        acc = None
        for avec in compositions(da, n):
            for bvec in compositions(db, n):
                types = []
                ok = True
                for a, b in zip(avec, bvec):
                    if (a, b) not in TYPES:
                        ok = False
                        break
                    types.append(TYPES[(a, b)])
                if not ok:
                    raise ValueError("Taylor order too high for a line")
                arr = self.bundle_lines(tuple(types))
                acc = arr.copy() if acc is None else acc + arr
        self._cache[key] = acc
        return acc

    def gaunt_nodes(self, beta_ab):
        """Values of a bundle at the nodes of the Gaunt quadrature, [a, q]."""
        if self._gq is None:
            Q = (3 * self.L) // 2 + 3            # exact for degree <= 3 L + 5
            t, w = np.polynomial.legendre.leggauss(Q)
            self._gq = (t, w, legendre_matrix(self.L, t))
        return beta_ab @ self._gq[2]

    def gaunt_project(self, Bq, lc, ld):
        """A[a] = sum_l0 beta_ab[a, l0] int dt/2 P_l0 P_lc P_ld (Bq from gaunt_nodes)."""
        t, w, P = self._gq
        A = Bq @ (w / 2.0 * P[lc] * P[ld])
        a = np.arange(len(A))
        A[(a % 2 != (lc + ld) % 2) | (a < abs(lc - ld))] = 0.0      # parity and triangle rule (exact zeros)
        return A


def conv_rows(A, B):
    """C[N, q] = sum_k A[k, q] B[N - k, q], truncated to the row count."""
    n = A.shape[0]
    C = np.zeros_like(A)
    for k in range(n):
        a = A[k]
        if not np.any(a):
            continue
        C[k:] += a[None, :] * B[: n - k]
    return C


def compositions(total, parts):
    """Ordered tuples of `parts` nonnegative integers summing to total."""
    if parts == 0:
        if total == 0:
            yield ()
        return
    if parts == 1:
        yield (total,)
        return
    for first in range(total + 1):
        for rest in compositions(total - first, parts - 1):
            yield (first,) + rest


# ============================================================================ zero-mode paths (as 2D)
def zero_mode_paths(p, zlegs):
    """Closed paths p = r_0 -> ... -> r_K = p, vertex i applying :Z^{zlegs[i]}:; amplitude
    prod C(k_i, j_i) * prod_{i<K} r_i! / prod m_i! (exact rational)."""
    K = len(zlegs)
    out = []

    def rec(i, r_prev, rs, cnum, mden):
        k = zlegs[i]
        targets = [p] if i == K - 1 else range(max(0, r_prev - k), r_prev + k + 1)
        for r in targets:
            d = r - r_prev
            if (d + k) % 2 or abs(d) > k:
                continue
            j = (d + k) // 2
            m = r_prev - (k - j)
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


# ============================================================================ patterns
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
        legs = legs_of(n, K)
        if any(legs[i] > MAXLEGS[kinds[i]] for i in range(K)):
            continue
        out.append(n)
    return out


def slice_counts(n, K):
    return [sum(v for (i, j), v in n.items() if i <= s < j) for s in range(K - 1)]


def legs_of(n, K):
    return [sum(v for (a, b), v in n.items() if a == i or b == i) for i in range(K)]


# ============================================================================ densities (half-level grids)
# Slice levels are even (inversion parity), N_s = 2 sigma_s.  In every angular channel each bundle array is
# supported on one level parity pi_e (partial wave l = level mod 2), so a_e = 2 alpha_e + pi_e and
# sigma_s = sum_{e in s} alpha_e + (sum_{e in s} pi_e)/2.  Grids are built on the cropped support only.
def to_half(A, S):
    """Full-level array A -> (pi, mu, v) with A[2(mu + k) + pi] = v[k], v cropped to alpha <= S."""
    nz = np.flatnonzero(A)
    if len(nz) == 0:
        return None
    pi = int(nz[0] % 2)
    if np.any(nz % 2 != pi):
        raise RuntimeError("mixed level parity in a channel array")
    mu = (int(nz[0]) - pi) // 2
    v = np.ascontiguousarray(A[pi::2][mu: S + 1])
    return pi, mu, v


def toeplitz_lower(a, n):
    """T[i, j] = a[i - j] for 0 <= j <= i <= n (a zero-padded)."""
    from scipy.linalg import toeplitz
    c = np.zeros(n + 1)
    m = min(len(a), n + 1)
    c[:m] = a[:m]
    return toeplitz(c, np.zeros(n + 1))


def build3(arrs, S, F):
    """Add sum_b v02[b] v01[i-b] v12[j-b] into F[sigma0, sigma1] (triangle 01, 02, 12)."""
    h = {e: to_half(arrs[e], S) for e in ((0, 1), (0, 2), (1, 2))}
    if any(x is None for x in h.values()):
        return
    (p01, m01, v01), (p02, m02, v02), (p12, m12, v12) = h[(0, 1)], h[(0, 2)], h[(1, 2)]
    if (p01 + p02) % 2 or (p02 + p12) % 2:
        return                                   # odd slice level: no contribution
    lo0 = (p01 + p02) // 2 + m01 + m02
    lo1 = (p02 + p12) // 2 + m02 + m12
    D0, D1 = S - lo0 + 1, S - lo1 + 1
    if D0 <= 0 or D1 <= 0:
        return
    nb = min(len(v02), D0, D1)
    A = toeplitz_lower(v01, D0 - 1)[:, :nb] * v02[None, :nb]
    Dm = toeplitz_lower(v12, D1 - 1)[:, :nb]
    F[lo0:lo0 + D0, lo1:lo1 + D1] += A @ Dm.T


if HAVE_NUMBA:
    @njit(cache=True)
    def _scatter3(v02, v03, v13, D0, D1, D2):
        """out[a+u, a+u+b, u+b] += v03[u] v02[a] v13[b] within the box D0 x D1 x D2."""
        out = np.zeros((D0, D1, D2))
        for u in range(min(len(v03), D0, D1, D2)):
            x03 = v03[u]
            if x03 == 0.0:
                continue
            for a in range(min(len(v02), D0 - u)):
                x02 = v02[a]
                if x02 == 0.0:
                    continue
                for b in range(min(len(v13), D2 - u)):
                    s1 = a + u + b
                    if s1 >= D1:
                        break
                    out[a + u, s1, u + b] += x03 * x02 * v13[b]
        return out
else:  # pragma: no cover
    def _scatter3(v02, v03, v13, D0, D1, D2):
        out = np.zeros((D0, D1, D2))
        for u in range(min(len(v03), D0, D1, D2)):
            for a in range(min(len(v02), D0 - u)):
                for b in range(min(len(v13), D2 - u)):
                    if a + u + b < D1:
                        out[a + u, a + u + b, u + b] += v03[u] * v02[a] * v13[b]
        return out


def conv_axis(X, a, axis):
    n = X.shape[axis] - 1
    if len(a) == 1 or not np.any(a[1: n + 1]):
        return X * a[0] if a[0] != 1.0 else X
    T = toeplitz_lower(a, n)
    X = np.ascontiguousarray(X)
    sh = X.shape
    if axis == 0:
        return (T @ X.reshape(sh[0], -1)).reshape(sh)
    if axis == X.ndim - 1:
        return (X.reshape(-1, sh[-1]) @ T.T).reshape(sh)
    Y = T @ np.ascontiguousarray(X.transpose(1, 0, 2)).reshape(sh[1], -1)     # middle axis: one GEMM
    return np.ascontiguousarray(Y.reshape(sh[1], sh[0], sh[2]).transpose(1, 0, 2))


E4 = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
SL4 = (((0, 1), (0, 2), (0, 3)), ((0, 2), (0, 3), (1, 2), (1, 3)), ((0, 3), (1, 3), (2, 3)))


def build4(arrs, S, F, scale=1.0):
    """Add scale * (separable 4-vertex density) into F[sigma0, sigma1, sigma2]; arrs = full-level arrays."""
    h = {}
    for e in E4:
        x = to_half(arrs[e], S)
        if x is None:
            return
        h[e] = x
    lo = []
    for sl in SL4:
        ps = sum(h[e][0] for e in sl)
        if ps % 2:
            return
        lo.append(ps // 2 + sum(h[e][1] for e in sl))
    D = [S - x + 1 for x in lo]
    if min(D) <= 0:
        return
    X = _scatter3(h[(0, 2)][2], h[(0, 3)][2], h[(1, 3)][2], D[0], D[1], D[2])
    X = conv_axis(X, h[(0, 1)][2], 0)
    X = conv_axis(X, h[(1, 2)][2], 1)
    X = conv_axis(X, h[(2, 3)][2], 2)
    if scale != 1.0:
        X *= scale
    F[lo[0]:lo[0] + D[0], lo[1]:lo[1] + D[1], lo[2]:lo[2] + D[2]] += X


def graph_cycle(edges):
    """Edge list of the unique cycle of a unicyclic graph."""
    adj = {}
    for (i, j) in edges:
        adj.setdefault(i, set()).add(j)
        adj.setdefault(j, set()).add(i)
    deg = {v: len(s) for v, s in adj.items()}
    alive = set(adj)
    changed = True
    while changed:
        changed = False
        for v in list(alive):
            if deg[v] <= 1:
                alive.remove(v)
                for w in adj[v]:
                    if w in alive:
                        deg[w] -= 1
                changed = True
    return [(i, j) for (i, j) in edges if i in alive and j in alive]


def _components(edges):
    parent = {}

    def find(v):
        while parent.setdefault(v, v) != v:
            v = parent[v]
        return v
    for (i, j) in edges:
        parent[find(i)] = find(j)
    return len({find(v) for e in edges for v in e}) if edges else 0


def is_delta(b):
    return b[0, 0] == 1.0 and not np.any(b[1:]) and not np.any(b[0, 1:])


def graph_class(n, K):
    edges = [e for e, v in n.items() if v > 0]
    V = len({x for e in edges for x in e})
    return len(edges) - V + _components(edges)


LC_SPLIT = None          # (k, K): K4-minus-edge channels restricted to l_c = k mod K (task splitting)


def density_add(basis, K, betas, S, F):
    """Add the angular-integrated, level-resolved density of one bundle configuration into F (sigma grid)."""
    if K == 2:
        b = betas[(0, 1)][:, 0]
        F[: S + 1] += b[0: 2 * S + 1: 2]
        return
    if K == 3:
        lmax = betas[(0, 1)].shape[1] - 1
        for l in range(lmax + 1):
            arrs = {e: betas[e][:, l] for e in ((0, 1), (0, 2), (1, 2))}
            if any(not np.any(a) for a in arrs.values()):
                continue
            Fl = np.zeros_like(F)
            build3(arrs, S, Fl)
            F += Fl / (2 * l + 1) ** 2
        return
    edges = [e for e in E4 if not is_delta(betas[e])]
    V = len({v for e in edges for v in e})
    cyc_number = len(edges) - V + _components(edges)
    if cyc_number == 0:
        build4({e: betas[e][:, 0] for e in E4}, S, F)
        return
    if cyc_number == 1:
        cyc = graph_cycle(edges)
        k = len(cyc)
        lmax = betas[cyc[0]].shape[1] - 1
        for l in range(lmax + 1):
            arrs = {e: (betas[e][:, l] if e in cyc else betas[e][:, 0]) for e in E4}
            if any(not np.any(arrs[e]) for e in cyc):
                continue
            build4(arrs, S, F, 1.0 / (2 * l + 1) ** (k - 1))
        return
    if cyc_number == 2 and len(edges) == 5:
        missing = [e for e in E4 if e not in edges][0]
        c, d = missing
        a, b = [v for v in range(4) if v not in missing]
        key = lambda i, j: (min(i, j), max(i, j))
        e_ab, e_ac, e_bc, e_ad, e_bd = key(a, b), key(a, c), key(b, c), key(a, d), key(b, d)
        lmax = betas[e_ab].shape[1] - 1
        Bq = basis.gaunt_nodes(betas[e_ab])
        for lc in range(lmax + 1):
            if LC_SPLIT is not None and lc % LC_SPLIT[1] != LC_SPLIT[0]:
                continue
            ac, bc = betas[e_ac][:, lc], betas[e_bc][:, lc]
            if not np.any(ac) or not np.any(bc):
                continue
            for ld in range(lmax + 1):
                ad, bd = betas[e_ad][:, ld], betas[e_bd][:, ld]
                if not np.any(ad) or not np.any(bd):
                    continue
                A = basis.gaunt_project(Bq, lc, ld)
                arrs = {e_ab: A, e_ac: ac, e_bc: bc, e_ad: ad, e_bd: bd, missing: betas[missing][:, 0]}
                build4(arrs, S, F, 1.0 / ((2 * lc + 1) * (2 * ld + 1)))
        return
    raise NotImplementedError("K4 (6 bundles) angular integral not implemented")


# ============================================================================ shell sums (sigma grids)
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
    if R.ndim == 1:
        return _shell1(R, Gs[0], N)
    if R.ndim == 2:
        return _shell2(R, Gs[0], Gs[1], N)
    return _shell3(R, Gs[0], Gs[1], Gs[2], N)


def slice_G(delta, nlines, pw, length, lev=0):
    """(-1)^pw N^lev / den^pw at slice level N = 2 sigma >= nlines; den = N + x0 (delta + nlines)."""
    N = 2.0 * np.arange(length)
    den = N + X0 * (delta + nlines)
    g = np.zeros(length)
    ok = N >= nlines
    if np.any(den[ok] == 0.0):
        raise RuntimeError("zero energy denominator")
    g[ok] = (-1.0) ** pw * N[ok] ** lev / den[ok] ** pw
    return g


# ============================================================================ chains
def deriv_distributions(n, K, derivs):
    """Distribute vertex eps-Taylor orders over the incident bundles (ordered by legs)."""
    prs = pairs_of(K)
    per_vertex = []
    for v in range(K):
        inc = [e for e in prs if v in e and n[e] > 0]
        if derivs[v] == 0:
            per_vertex.append([{}])
            continue
        per_vertex.append([{e: c for e, c in zip(inc, comp)} for comp in compositions(derivs[v], len(inc))])
    for choice in itertools.product(*per_vertex):
        orders = {e: [0, 0] for e in prs}
        for v, ch in enumerate(choice):
            for e, c in ch.items():
                orders[e][0 if e[0] == v else 1] += c
        yield {e: tuple(o) for e, o in orders.items()}


def pattern_density(basis, K, n, derivs, Ss):
    S = basis.L // 2
    F = np.zeros(tuple(x + 1 for x in Ss)) if K > 2 else np.zeros(Ss[0] + 1)
    full = np.zeros(tuple([S + 1] * (K - 1)))
    any_ = False
    for orders in deriv_distributions(n, K, derivs):
        betas = {}
        for e in pairs_of(K):
            b = basis.bundle(n[e], *orders[e])
            if b is None:
                betas = None
                break
            betas[e] = b
        if betas is None:
            continue
        density_add(basis, K, betas, S, full)
        any_ = True
    if not any_:
        return None
    sl = tuple(slice(0, x + 1) for x in Ss)
    return np.ascontiguousarray(full[sl])


def reverse_pattern(n, K):
    return {(K - 1 - j, K - 1 - i): v for (i, j), v in n.items()}


def pattern_key(n):
    return tuple(sorted(n.items()))


def chain_pattern(basis, kinds, slice_ops, n, ps, derivs, mult=1):
    """Contribution of one line pattern to <p| X_K s_{K-1} ... s_1 X_1 |p>: per-key shell values over
    sigma = L/2 (cumulate for the value at cutoff L)."""
    K = len(kinds)
    S = basis.L // 2
    legs = legs_of(n, K)
    for v in range(K):
        if derivs[v] and legs[v] == 0:
            return None
    nsl = slice_counts(n, K)
    zl = [MAXLEGS[kinds[i]] - legs[i] for i in range(K)]
    combf = Fr(mult)
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
                    ok = False
                    break
                pw, q = slice_ops[s_][:2]
                fac *= Fr(deltas[s_] + nsl[s_]) ** q
            if not ok or fac == 0:
                continue
            keyamp.setdefault(deltas, {}).setdefault(p, Fr(0))
            keyamp[deltas][p] += combf * vc * amp * fac
    keyamp = {k: d for k, d in keyamp.items() if any(v != 0 for v in d.values())}
    if not keyamp:
        return None
    Ss = [S if nsl[s_] > 0 else 0 for s_ in range(K - 1)]
    R = pattern_density(basis, K, n, derivs, Ss)
    if R is None:
        return None
    keys = list(keyamp)
    Gs = [np.array([slice_G(k[s_], nsl[s_], slice_ops[s_][0], Ss[s_] + 1,
                            slice_ops[s_][2] if len(slice_ops[s_]) > 2 else 0) for k in keys])
          for s_ in range(K - 1)]
    sh = shell_sums(R, Gs, S)
    return keys, keyamp, sh


def chain(basis, kinds, slice_ops, ps=(0, 1, 2, 3), derivs=None, max_lines=None, shells=False,
          pattern_filter=None, collect=None, mirror=False):
    """<p| X_K s_{K-1} ... s_1 X_1 |p> (vertex 0 acts first) at every even cutoff L = 2 sigma <= Lmax
    (cumulative), or per-sigma shell values with shells=True.  slice_ops[s] = (pow, q): (P - p)^q R^pow,
    R = Q/(E_p - H0).  derivs[i] = eps-Taylor order of vertex i (V_k, M_k).  mirror=True (only for
    reversal-symmetric chains) computes one pattern of each mirror pair, with weight 2."""
    K = len(kinds)
    if derivs is None:
        derivs = [0] * K
    S = basis.L // 2
    res = {p: np.zeros(S + 1) for p in ps}
    done = set()
    for n in patterns(kinds, max_lines):
        if pattern_filter is not None and not pattern_filter(n):
            continue
        mult = 1
        if mirror:
            k1, k2 = pattern_key(n), pattern_key(reverse_pattern(n, K))
            if k2 in done:
                continue
            done.add(k1)
            mult = 1 if k1 == k2 else 2
        out = chain_pattern(basis, kinds, slice_ops, n, ps, derivs, mult)
        if out is None:
            continue
        keys, keyamp, sh = out
        vals = sh if shells else np.cumsum(sh, axis=1)
        for t, k in enumerate(keys):
            for p, a in keyamp[k].items():
                res[p] += float(a) * vals[t]
                if collect is not None:
                    collect.append((dict(n), k, p, a, sh[t]))
    return res


def chain_entries(basis, kinds, slice_ops, derivs=None, max_lines=None, mirror=False, pattern_filter=None):
    """Like chain(), but keeps the zero-mode amplitude of every (pattern, key) exactly:
    returns a Lin of (amps over p = 0..3 as Fractions, cumulative array over sigma)."""
    K = len(kinds)
    if derivs is None:
        derivs = [0] * K
    lin = Lin()
    done = set()
    for n in patterns(kinds, max_lines):
        if pattern_filter is not None and not pattern_filter(n):
            continue
        mult = 1
        if mirror:
            k1, k2 = pattern_key(n), pattern_key(reverse_pattern(n, K))
            if k2 in done:
                continue
            done.add(k1)
            mult = 1 if k1 == k2 else 2
        out = chain_pattern(basis, kinds, slice_ops, n, (0, 1, 2, 3), derivs, mult)
        if out is None:
            continue
        keys, keyamp, sh = out
        cum = np.cumsum(sh, axis=1)
        for t, k in enumerate(keys):
            lin.add([keyamp[k].get(p, Fr(0)) for p in range(4)], cum[t])
    return lin


class Lin:
    """Linear combination sum_k amps_k(p) * arr_k(L) with exact zero-mode amplitudes amps_k (p = 0..3)."""

    def __init__(self, entries=None):
        self.e = list(entries) if entries else []

    def add(self, amps, arr):
        if any(a != 0 for a in amps):
            self.e.append((list(amps), np.asarray(arr, dtype=float)))

    def __add__(self, other):
        return Lin(self.e + other.e)

    def scale(self, c):
        """c: number or array over sigma (float)."""
        return Lin([(a, arr * c) for a, arr in self.e])

    def pfac(self, f):
        """multiply amps by an exact p-dependent factor f(p)."""
        out = Lin()
        for a, arr in self.e:
            out.add([a[p] * Fr(f(p)) for p in range(4)], arr)
        return out

    def times(self, other):
        out = Lin()
        for a, x in self.e:
            for b, y in other.e:
                out.add([a[p] * b[p] for p in range(4)], x * y)
        return out

    def proj(self, fn):
        """sum_k float(fn(amps_k)) * arr_k, fn exact (applied before any float arithmetic)."""
        acc = None
        for a, arr in self.e:
            w = fn(a)
            if w == 0:
                continue
            acc = float(w) * arr if acc is None else acc + float(w) * arr
        return acc

    def at(self, p):
        return self.proj(lambda a: a[p])


PI = lambda a: a[2] - a[1] - (a[3] - a[0]) / 3
R_OF = lambda a: -(a[1] - a[0]) / 2
G_OF = lambda a: -(a[3] - a[0]) / 3 + (a[1] - a[0])


def Pi(f):
    return f[2] - f[1] - (f[3] - f[0]) / 3.0
