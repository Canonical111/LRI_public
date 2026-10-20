#!/usr/bin/env python3
"""3D diagram engine with the API of the 2D eps5/engine.py (../../lri_2d_coeff_expanse/.../residual_log/eps5), so that
the model-independent eps^5 modules (rs, chains, windowsW, bloch, schemeW, delta5, prod5) run unchanged.

Model: lri_3d_hpc (see ../README.md).  sigma = half slice level (slice level N = 2 sigma, inversion parity), x0 = 3/4:
slice denominator den = x0 (delta + n_lines) + 2 sigma; callers pass alpha = X0 (delta + n_lines) to slice_G.

Densities:
  * K <= 4 vertices: c4lib3d.pattern_density (validated through C4; partial-wave channels: forest, one cycle,
    K4 minus an edge); the K4 graph and anything else falls back to the generic builder below;
  * K = 5 (and fallbacks): generic angular reduction of the bundle graph into channels (weight, l per bundle):
      degree-1 vertex -> l = 0;  degree-2 vertex (series) -> equal l, factor 1/(2l+1);
      parallel bundles -> P_l1 P_l2 = sum_l (2l+1)(l1 l2 l; 0 0 0)^2 P_l;  one edge left -> l = 0;
      K4 core -> tetrahedral weight T = prod_v (3j 000)_v {6j} (-1)^(sum l)  (exact rational, Racah formula);
    each channel is a separable product of per-bundle level arrays beta_b[., l_b], built on the cropped half-level
    box by diagonal convolutions."""
import itertools
import os
import sys
from fractions import Fraction as Fr
from functools import lru_cache
from math import comb, factorial

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import c4lib3d as lib  # noqa: E402

try:
    from numba import njit
    HAVE_NUMBA = True
except Exception:  # pragma: no cover
    HAVE_NUMBA = False

X0 = 0.75
MAXLEGS = {"V": 4, "M": 2}
vcoef = lib.vcoef
DROP_ZERO_DEN = True       # degenerate partners (z >= 9 in 3D) projected out of every window object (WINDOW_SPEC 2.10); primaries never hit it


# ======================================================================================= modes
class Modes:
    """3D mode data for slice levels <= 2N (N = sigma_max): c4lib3d.Basis with eps-Taylor tables to order dmax."""

    def __init__(self, N, dmax=3, tables=None):
        self.N = N
        self.Lmax = 2 * N
        self.dmax = dmax
        if tables is None and os.environ.get("ENGINE_TABLES"):
            path = os.environ["ENGINE_TABLES"]
            if os.path.exists(path):
                z = dict(np.load(path))
                if z["00"].shape[0] == 2 * N + 1:
                    tables = z
        self.basis = lib.Basis(2 * N, T=tables, dmax=dmax)


# ======================================================================================= patterns (as 2D)
def pairs_of(K):
    return [(i, j) for i in range(K) for j in range(i + 1, K)]


_PAT_CACHE = {}


def patterns(kinds, max_lines=None, min_zero_legs=0):
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
    bundles = [b for b, v in n.items() if v]
    if not bundles:
        return set()
    A = np.array([[1.0 if b[0] <= s < b[1] else 0.0 for b in bundles] for s in range(K - 1)])
    u, sv, vt = np.linalg.svd(A)
    rank = int((sv > 1e-9).sum())
    ns = vt[rank:]
    return {b for k, b in enumerate(bundles) if len(ns) and not np.allclose(ns[:, k], 0.0)}


# ======================================================================================= zero-mode paths (as 2D)
def zero_mode_paths(z0, zlegs, z1=None):
    """Paths z0 -> ... -> z1 (normalized basis); closed paths give exact rationals, open ones floats."""
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
            c = cnum * comb(k, j)
            s2 = sq * Fr(factorial(r_prev) * factorial(r), factorial(m) ** 2)
            if i == K - 1:
                out.append((tuple(rs), c, s2))
            else:
                rec(i + 1, r, rs + [r], c, s2)

    rec(0, z0, [], 1, Fr(1))
    res = []
    for rs, c, s2 in out:
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


# ======================================================================================= angular algebra (exact)
@lru_cache(maxsize=None)
def threej0_sq(a, b, c):
    """(a b c; 0 0 0)^2, exact Fraction."""
    s = a + b + c
    if s % 2 or a > b + c or b > a + c or c > a + b:
        return Fr(0)
    g = s // 2
    t = Fr(factorial(g), factorial(g - a) * factorial(g - b) * factorial(g - c)) ** 2
    return t * Fr(factorial(b + c - a) * factorial(a + c - b) * factorial(a + b - c), factorial(s + 1))


_FACT = [1]
_PERMS4 = list(__import__('itertools').permutations(range(4)))


def _fact(n):
    while len(_FACT) <= n:
        _FACT.append(_FACT[-1] * len(_FACT))
    return _FACT[n]


def _tetra_ratio(l12, l13, l14, l23, l24, l34):
    """Exact (num, den) integers of tetra(...); den > 0.  Racah sum over the common denominator
    prod_{k rising} f_k(tmax)! prod_{k falling} f_k(tmin)!, so every term is an integer."""
    tri = [(l12, l13, l14), (l12, l23, l24), (l13, l23, l34), (l14, l24, l34)]
    pn, pd = 1, 1
    for (x, y, z) in tri:
        s = x + y + z
        if s % 2 or x > y + z or y > x + z or z > x + y:
            return 0, 1
        g = s // 2
        pn *= _fact(g) * _fact(x + y - z) * _fact(x - y + z) * _fact(-x + y + z)
        pd *= _fact(g - x) * _fact(g - y) * _fact(g - z) * _fact(s + 1)
    a, b, c, d, e, f = l12, l13, l14, l34, l24, l23
    rise = (a + b + c, a + e + f, d + b + f, d + e + c)          # (t - r)!
    fall = (a + b + d + e, a + c + d + f, b + c + e + f)          # (r - t)!
    tmin, tmax = max(rise), min(fall)
    if tmin > tmax:
        return 0, 1
    D = 1
    for r in rise:
        D *= _fact(tmax - r)
    for r in fall:
        D *= _fact(r - tmin)
    S = 0
    for t in range(tmin, tmax + 1):
        q = 1
        for r in rise:
            q *= _fact(tmax - r) // _fact(t - r)
        for r in fall:
            q *= _fact(r - tmin) // _fact(r - t)
        S += (-1) ** t * _fact(t + 1) * q
    return pn * S, pd * D


@lru_cache(maxsize=None)
def tetra(l12, l13, l14, l23, l24, l34):
    """int prod_{i<j} P_{l_ij}(n_i . n_j) prod_i dn_i/(4 pi)  (exact Fraction):
    (-1)^(sum l) prod_v (3j 000)_v {l12 l13 l14; l34 l24 l23}; the square roots cancel
    ((-1)^(sum l) of the formula cancels against prod_v (-1)^(g_v))."""
    n, d = _tetra_ratio(l12, l13, l14, l23, l24, l34)
    return Fr(n, d)


def _edge_perm_getters():
    from operator import itemgetter
    E = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
    pos = {e: k for k, e in enumerate(E)}
    return [itemgetter(*[pos[tuple(sorted((p[i], p[j])))] for (i, j) in E]) for p in _PERMS4]


_EPERM = None


def _tetra_key(*k):
    """Canonical representative under the 24 vertex permutations (the integral is invariant)."""
    global _EPERM
    if _EPERM is None:
        _EPERM = _edge_perm_getters()
    return min(g(k) for g in _EPERM)


class ReIter:
    """Re-iterable lazy factor: each iteration calls fn(*args) afresh (no materialization); `edges` = the original
    edge indices it assigns."""

    def __init__(self, fn, edges, *args):
        self.fn, self.edges, self.args = fn, frozenset(edges), args

    def __iter__(self):
        return self.fn(*self.args)


def _edges_of(states_lists):
    return {k for st in states_lists for s in st for (k, _) in s[2]}


def angular_channels(edges, supports, lcap, inner_edge=None):
    """edges: list of (u, v) (distinct unordered vertex pairs); supports[k] = allowed l values of edge k.
    Returns the factor lists [(weight, assignment)] whose product gives the channels (channel_chunks):
    int prod_k f_k = sum_ch weight prod_k beta_k[l_k]."""
    comps = []           # composite edges: [u, v, states]; state = (l, weight, assign tuple)
    for k, (u, v) in enumerate(edges):
        comps.append([u, v, [(l, Fr(1), ((k, l),)) for l in supports[k]]])
    factors = [[(Fr(1), ())]]
    while True:
        # parallel merge
        merged = True
        while merged:
            merged = False
            seen = {}
            for i, c in enumerate(comps):
                key = (min(c[0], c[1]), max(c[0], c[1]))
                if key in seen:
                    j = seen[key]
                    u, v = key
                    between = [k for k, cc in enumerate(comps) if {cc[0], cc[1]} == {u, v}]
                    others = [k for k, cc in enumerate(comps) if (u in (cc[0], cc[1]) or v in (cc[0], cc[1]))
                              and k not in between]
                    if not others:
                        # last stage of this component: int P_l1 P_l2 = delta/(2l+1), generated lazily; with more
                        # than two parallel composites, merge two balanced halves first (sequential merging of k
                        # composites makes O(L^(2k-3)) states)
                        sts = [comps[k][2] for k in between]
                        half = (len(sts) + 1) // 2
                        c1, c2 = sts[0], sts[half]
                        for s in sts[1:half]:
                            c1 = _parallel(c1, s, lcap)
                        for s in sts[half + 1:]:
                            c2 = _parallel(c2, s, lcap)
                        for k in sorted(between, reverse=True):
                            comps.pop(k)
                        factors.append(ReIter(_final_pair, _edges_of([c1, c2]), c1, c2, inner_edge))
                        merged = True
                        break
                    comps[j][2] = _parallel(comps[j][2], c[2], lcap)
                    comps.pop(i)
                    merged = True
                    break
                seen[key] = i
        deg = {}
        for c in comps:
            deg[c[0]] = deg.get(c[0], 0) + 1
            deg[c[1]] = deg.get(c[1], 0) + 1
        if not comps:
            break
        v1 = [v for v, d in deg.items() if d == 1]
        if v1:
            v = v1[0]
            i = [k for k, c in enumerate(comps) if v in (c[0], c[1])][0]
            st = comps.pop(i)[2]
            factors.append([(w, a) for (l, w, a) in st if l == 0])
            continue
        v2 = [v for v, d in deg.items() if d == 2]
        if v2:
            v = v2[0]
            ii = [k for k, c in enumerate(comps) if v in (c[0], c[1])]
            c1, c2 = comps[ii[0]], comps[ii[1]]
            a = c1[0] if c1[1] == v else c1[1]
            b = c2[0] if c2[1] == v else c2[1]
            new = _series(c1[2], c2[2])
            for k in sorted(ii, reverse=True):
                comps.pop(k)
            comps.append([a, b, new])
            continue
        verts = sorted(deg)
        if len(verts) == 4 and len(comps) == 6 and all(d == 3 for d in deg.values()):
            factors.append(ReIter(_tetra_states, _edges_of([c[2] for c in comps]), comps, verts, inner_edge))
            comps = []
            break
        raise NotImplementedError(f"angular reduction stuck: {[(c[0], c[1]) for c in comps]}")
    return factors


def is_series_parallel(n, K):
    """True if the angular reduction of pattern n (dict pair -> lines) needs no tetrahedral (K4) core, i.e. the
    multigraph reduces by parallel merges, degree-1 removals and series contractions (structure of angular_channels)."""
    comps = [tuple(e) for e, v in n.items() if v]
    while comps:
        comps = list({(min(u, v), max(u, v)) for (u, v) in comps})        # parallel merge
        deg = {}
        for (u, v) in comps:
            deg[u] = deg.get(u, 0) + 1
            deg[v] = deg.get(v, 0) + 1
        v1 = [x for x, d in deg.items() if d == 1]
        if v1:
            comps = [c for c in comps if v1[0] not in c]
            continue
        v2 = [x for x, d in deg.items() if d == 2]
        if v2:
            x = v2[0]
            ii = [c for c in comps if x in c]
            a = ii[0][0] if ii[0][1] == x else ii[0][1]
            b = ii[1][0] if ii[1][1] == x else ii[1][1]
            comps = [c for c in comps if x not in c] + [(a, b)]
            continue
        return False
    return True


def channel_chunks(factors, nedges, chunk=200000):
    """Yield dicts {tuple(l per edge): weight}: the product of the factor lists, with the largest factor streamed in
    chunks (bounded memory; an assignment split over two chunks is simply built twice with partial weights)."""
    gen = [k for k, fl in enumerate(factors) if not isinstance(fl, list)]
    for k in gen[1:]:
        factors[k] = list(factors[k])               # only one factor is streamed
    big = gen[0] if gen else max(range(len(factors)), key=lambda k: len(factors[k]))
    acc = {(): 1.0}
    for k, fl in enumerate(factors):
        if k == big:
            continue
        new = {}
        for a0, w0 in acc.items():
            for (w, a) in fl:
                if w == 0:
                    continue
                key = a0 + a
                new[key] = new.get(key, 0.0) + w0 * float(w)
        acc = new
    it = iter(factors[big])
    while True:
        block = list(itertools.islice(it, chunk))
        if not block:
            break
        out = {}
        for (w, a) in block:
            if w == 0:
                continue
            for a0, w0 in acc.items():
                d = dict(a0 + a)
                key = tuple(d[k] for k in range(nedges))
                out[key] = out.get(key, 0.0) + w0 * float(w)
        yield out


def _final_pair(s1, s2, inner_edge=None):
    """int P_l1 P_l2 = delta/(2l+1), generated lazily.  With inner_edge: the composite carrying it is the inner loop and
    its states (per l) are ordered by their other assignments (channels differing only in inner_edge adjacent)."""
    has = lambda s: any(k == inner_edge for st in s for (k, _) in st[2])
    if inner_edge is not None and has(s1) and not has(s2):
        s1, s2 = s2, s1
    by = {}
    for (l, w, a) in s2:
        by.setdefault(l, []).append((float(w), a))
    if inner_edge is not None:
        for l in by:
            by[l].sort(key=lambda e: tuple(x for x in e[1] if x[0] != inner_edge))
    for (l, w, a) in s1:
        w = float(w) / (2 * l + 1)
        for (w2, a2) in by.get(l, ()):
            yield (w * w2, a + a2)


def _series(s1, s2):
    by = {}
    for (l, w, a) in s2:
        by.setdefault(l, []).append((w, a))
    out = []
    for (l, w, a) in s1:
        for (w2, a2) in by.get(l, []):
            out.append((l, w * w2 / (2 * l + 1), a + a2))
    return out


def _parallel(s1, s2, lcap):
    acc = {}
    for (l1, w1, a1) in s1:
        for (l2, w2, a2) in s2:
            for l in range(abs(l1 - l2), min(l1 + l2, lcap) + 1, 2):
                g = threej0_sq(l1, l2, l)
                if g == 0:
                    continue
                key = (l, a1 + a2)
                acc[key] = acc.get(key, 0) + w1 * w2 * (2 * l + 1) * g
    out = [(l, w, a) for (l, a), w in acc.items() if w != 0]
    _note("parallel", len(out))
    return out


_TF = {}          # raw sextuple -> value (bounded: cleared when large)
_TC = {}          # canonical sextuple -> value (24x smaller, kept)
_TF_MAX = int(os.environ.get("ENGINE_TF_MAX", 500_000))
_TC_MAX = int(os.environ.get("ENGINE_TC_MAX", 3_000_000))


def tetra_f(l12, l13, l14, l23, l24, l34):
    k = (l12, l13, l14, l23, l24, l34)
    v = _TF.get(k)
    if v is None:
        if not (_tri_ok(l12, l13, l14) and _tri_ok(l12, l23, l24) and _tri_ok(l13, l23, l34)
                and _tri_ok(l14, l24, l34)):
            v = 0.0
        else:
            c = _tetra_key(*k)
            v = _TC.get(c)
            if v is None:
                n, d = _tetra_ratio(*c)
                v = n / d if n else 0.0          # int/int true division: correctly rounded
                if len(_TC) >= _TC_MAX:
                    _TC.clear()
                _TC[c] = v
        if len(_TF) >= _TF_MAX:
            _TF.clear()
        _TF[k] = v
    return v


def _tri_ok(a, b, c):
    return (a + b + c) % 2 == 0 and a <= b + c and b <= a + c and c <= a + b


def _tetra_states(comps, verts, inner_edge=None):
    """K4 core: nested enumeration with the triangle/parity rule checked at each vertex as soon as its three edges
    are fixed (vertex triads: 0:(01,02,03) 1:(01,12,13) 2:(02,12,23) 3:(03,13,23)).  The composite edge carrying
    original edge `inner_edge` is made the innermost loop (vertices relabelled; the weight is permutation invariant) and
    its states are ordered by their other assignments, so that channels differing only in that edge are adjacent."""
    if inner_edge is not None:
        for c in comps:
            if any(k == inner_edge for (k, _) in (x for st in c[2] for x in st[2])):
                rest = [v for v in verts if v not in (c[0], c[1])]
                verts = rest + [c[0], c[1]]
                break
    idx = {v: k for k, v in enumerate(verts)}
    pos = {}
    for c in comps:
        i, j = sorted((idx[c[0]], idx[c[1]]))
        pos[(i, j)] = [(l, float(w), a) for (l, w, a) in c[2]]
    if inner_edge is not None:
        pos[(2, 3)].sort(key=lambda st: (tuple(x for x in st[2] if x[0] != inner_edge), st[0]))
    s01, s02, s03, s12, s13, s23 = (pos[(0, 1)], pos[(0, 2)], pos[(0, 3)], pos[(1, 2)], pos[(1, 3)], pos[(2, 3)])
    for a01 in s01:
        for a02 in s02:
            for a03 in s03:
                if not _tri_ok(a01[0], a02[0], a03[0]):
                    continue
                w0 = a01[1] * a02[1] * a03[1]
                for a12 in s12:
                    for a13 in s13:
                        if not _tri_ok(a01[0], a12[0], a13[0]):
                            continue
                        w1 = w0 * a12[1] * a13[1]
                        for a23 in s23:
                            if not (_tri_ok(a02[0], a12[0], a23[0]) and _tri_ok(a03[0], a13[0], a23[0])):
                                continue
                            t = tetra_f(a01[0], a02[0], a03[0], a12[0], a13[0], a23[0])
                            if t == 0.0:
                                continue
                            yield (t * w1 * a23[1], a01[2] + a02[2] + a03[2] + a12[2] + a13[2] + a23[2])


def channel_stream(factors, nedges, es):
    """Yield (l tuple over all edges, weight) for the product of the factors, ordered so that channels differing only
    in edge `es` are adjacent: the factor assigning `es` is the innermost loop (its entries sorted by their other
    assignments when it is a list; tetrahedral and final-pair factors put es innermost themselves).  Lazy factors
    (ReIter) are re-iterated, never materialized; the other factors are nested outside."""
    fes = None
    for k, fl in enumerate(factors):
        if isinstance(fl, ReIter):
            if es in fl.edges:
                fes = k
        elif any(any(kk == es for (kk, _) in a) for (_, a) in fl):
            fes = k
    if fes is None:
        return
    inner = factors[fes]
    if isinstance(inner, list):
        inner = sorted(inner, key=lambda e: tuple(x for x in e[1] if x[0] != es))
        _note("stream_inner_list", len(inner))
    others = [factors[k] for k in range(len(factors)) if k != fes]
    others.sort(key=lambda fl: (isinstance(fl, ReIter), len(fl) if isinstance(fl, list) else 0))

    def rec(i, base, wb):
        if i == len(others):
            for (w, a) in inner:
                if w == 0:
                    continue
                d = dict(base + a)
                yield tuple(d[k] for k in range(nedges)), wb * float(w)
            return
        for (w, a) in others[i]:
            if w == 0:
                continue
            yield from rec(i + 1, base + a, wb * float(w))
    yield from rec(0, (), 1.0)


# ======================================================================================= generic box builder
if HAVE_NUMBA:
    @njit(cache=True)
    def _diag_conv(X, shape, strides, mask, v):
        """Y[sigma + u d] += v[u] X[sigma], d = indicator(mask) (flattened arrays, C order)."""
        S = shape.shape[0]
        Y = np.zeros_like(X)
        step = 0
        for s in range(S):
            if mask[s]:
                step += strides[s]
        idx = np.zeros(S, dtype=np.int64)
        for f in range(X.shape[0]):
            x = X[f]
            if x != 0.0:
                rem = f
                room = 1 << 60
                for s in range(S):
                    idx[s] = rem // strides[s]
                    rem -= idx[s] * strides[s]
                    if mask[s]:
                        r = shape[s] - 1 - idx[s]
                        if r < room:
                            room = r
                umax = min(v.shape[0] - 1, room)
                for u in range(umax + 1):
                    Y[f + u * step] += v[u] * x
        return Y
else:  # pragma: no cover
    def _diag_conv(X, shape, strides, mask, v):
        raise RuntimeError("numba required")


def build_box(spans, halves, F, weight):
    """Add weight * (separable density) into F (sigma box of K-1 slices).  halves[b] = c4lib3d.to_half(...) of the
    level array of bundle b (one level parity), spans[b] = (i, j): bundle crosses slices i..j-1."""
    nsl = F.ndim
    lo = []
    for s in range(nsl):
        ps = 0
        mu = 0
        for b, (i, j) in enumerate(spans):
            if i <= s < j:
                ps += halves[b][0]
                mu += halves[b][1]
        if ps % 2:
            return
        lo.append(ps // 2 + mu)
    shp = F.shape
    D = [shp[s] - lo[s] for s in range(nsl)]
    if min(D) <= 0:
        return
    shape = np.array(D, dtype=np.int64)
    strides = np.ones(nsl, dtype=np.int64)
    for s in range(nsl - 2, -1, -1):
        strides[s] = strides[s + 1] * D[s + 1]
    X = np.zeros(int(np.prod(D)))
    X[0] = 1.0
    for b, (i, j) in enumerate(spans):
        mask = np.array([1 if i <= s < j else 0 for s in range(nsl)], dtype=np.int64)
        X = _diag_conv(X, shape, strides, mask, halves[b][2])
    sl = tuple(slice(lo[s], lo[s] + D[s]) for s in range(nsl))
    F[sl] += weight * X.reshape(D)


_ES_CACHE = {}


def _choose_presum(bundles, supports, ltrial=6):
    """Bundle index to pre-sum: maximize channels per group (distinct l of the other bundles) in a trial enumeration
    with supports truncated to l <= ltrial (structure only; ties -> larger support, then lower index)."""
    key = (tuple(bundles), tuple(min(len(s), ltrial + 1) for s in supports))
    if key in _ES_CACHE:
        return _ES_CACHE[key]
    sup_t = [[l for l in s if l <= ltrial] for s in supports]
    chans = {}
    for ch in channel_chunks(angular_channels(bundles, sup_t, ltrial), len(bundles)):
        for ls, w in ch.items():
            if w != 0.0:
                chans[ls] = 1
    best, bscore = 0, None
    for k in range(len(bundles)):
        ng = len({ls[:k] + ls[k + 1:] for ls in chans})
        score = (len(chans) / max(1, ng), len(supports[k]), -k)
        if bscore is None or score > bscore:
            best, bscore = k, score
    _ES_CACHE[key] = best
    return best


def _build_group(rest, arr, es, bundles, halves, S, F):
    """Box of one channel group (l of every bundle but es fixed; es pre-summed into the level array arr)."""
    ls = rest[:es] + (None,) + rest[es:]
    hs = [halves.get((k, l)) if k != es else None for k, l in enumerate(ls)]
    if any(h is None for k, h in enumerate(hs) if k != es):
        return
    for par in (0, 1):
        a = arr.copy()
        a[par ^ 1::2] = 0.0
        hh = lib.to_half(a, S) if np.any(a) else None
        if hh is None:
            continue
        hs[es] = (hh[0], hh[1], np.ascontiguousarray(hh[2], dtype=np.float64))
        build_box(bundles, hs, F, 1.0)


def density_generic(K, n, Ns, basis, derivs):
    S = max(Ns) if Ns else 0
    bundles = [b for b, v in n.items() if v]
    F = np.zeros(tuple(x + 1 for x in Ns))
    if not bundles:
        F[(0,) * (K - 1)] = 1.0
        return F
    lcap = basis.L
    for orders in lib.deriv_distributions(n, K, derivs):
        betas = {}
        for b in bundles:
            beta = basis.bundle(n[b], *orders[b])
            if beta is None:
                betas = None
                break
            betas[b] = beta
        if betas is None:
            continue
        supports = [[l for l in range(betas[b].shape[1]) if np.any(betas[b][:, l])] for b in bundles]
        halves = {}
        for k, b in enumerate(bundles):
            for l in supports[k]:
                hh = lib.to_half(betas[b][:, l], S)
                if hh is not None:
                    halves[(k, l)] = (hh[0], hh[1], np.ascontiguousarray(hh[2], dtype=np.float64))
        # the box build is linear in each bundle's level array: pre-sum one bundle (the one whose l is least fixed by
        # the others: most channels per group in a trial enumeration with small l)
        es = _choose_presum(bundles, supports)
        bs = betas[bundles[es]]
        cur, arr = None, None
        for ls, w in channel_stream(angular_channels(bundles, supports, lcap, inner_edge=es), len(bundles), es):
            if w == 0.0:
                continue
            rest = ls[:es] + ls[es + 1:]
            if rest != cur:
                if cur is not None:
                    _build_group(cur, arr, es, bundles, halves, S, F)
                cur, arr = rest, np.zeros(bs.shape[0])
            arr += w * bs[:, ls[es]]
        if cur is not None:
            _build_group(cur, arr, es, bundles, halves, S, F)
    return F


_RED_CACHE = {}
SIZES = {}          # debug: largest materialized list per site (ENGINE_DEBUG_SIZES=1)
_DBG = os.environ.get("ENGINE_DEBUG_SIZES") == "1"


def _note(site, n):
    if _DBG and n > SIZES.get(site, 0):
        SIZES[site] = n


def _has_k4(n, K):
    E = {e for e, v in n.items() if v}
    return any(all((min(a, b), max(a, b)) in E for a, b in itertools.combinations(q, 2))
               for q in itertools.combinations(range(K), 4))


def _dup_embed(R, idx_full, shp):
    """Diagonal embedding of a reduced box R into the full box (shape shp): full slice s takes reduced axis
    idx_full[s] (None -> 0); entries beyond shp dropped (the map is injective)."""
    H = np.zeros(shp)
    if R.ndim == 0:
        H[(0,) * len(shp)] = R
        return H
    T = np.indices(R.shape).reshape(R.ndim, -1)
    vals = R.reshape(-1)
    keep = vals != 0.0
    T, vals = T[:, keep], vals[keep]
    sig = []
    ok = np.ones(vals.shape, dtype=bool)
    for s, ti in enumerate(idx_full):
        col = np.zeros(vals.shape, dtype=np.int64) if ti is None else T[ti]
        ok &= col < shp[s]
        sig.append(col)
    np.add.at(H, tuple(c[ok] for c in sig), vals[ok])
    return H


def _red_disk(key, compute):
    """Reduced boxes shared by the worker processes through ENGINE_RED_DIR (one computes under an O_EXCL lock file,
    the others wait for the result).  Without ENGINE_RED_DIR: compute."""
    d = os.environ.get("ENGINE_RED_DIR")
    if not d:
        return compute()
    import hashlib
    import time as _t
    os.makedirs(d, exist_ok=True)
    h = hashlib.sha1(repr(key).encode()).hexdigest()[:20]
    f = os.path.join(d, f"red_{h}.npy")
    lock = f + ".lock"
    while True:
        if os.path.exists(f):
            return np.load(f)
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            _t.sleep(2.0)
            continue
        try:
            R = compute()
            tmp = f + f".tmp{os.getpid()}.npy"
            np.save(tmp, R)
            os.replace(tmp, f)
        finally:
            os.close(fd)
            os.remove(lock)
        return R


def reduced_density(n, K, Ns, basis):
    """Density of a pattern with a vertex v of degree 0 (isolated) or 1 (pendant line, l = 0 forced) from the density of
    the pattern without v (cached: all K4+pendant / K4+isolated time orderings share a few 4-vertex boxes).
    Removing v merges slices v-1 and v (diagonal embedding) or drops a boundary slice; the pendant line is then
    convolved along its span.  Derivative orders must be zero.  Returns None if no such vertex."""
    deg = [sum(v for e, v in n.items() if x in e) for x in range(K)]
    cand = [x for x in range(K) if deg[x] == 0] + [x for x in range(K) if deg[x] == 1]
    if not cand:
        return None
    v = cand[0]
    pend = [e for e, c in n.items() if c and v in e]
    lab = lambda x: x if x < v else x - 1
    n2 = {}
    for (a, b), c in n.items():
        if c and v not in (a, b):
            n2[(lab(a), lab(b))] = c
    n2 = {e: n2.get(e, 0) for e in pairs_of(K - 1)}
    sc2 = slice_counts(n2, K - 1)
    S = max(Ns)
    Ns2 = [S if sc2[t] else 0 for t in range(K - 2)]
    key = (tuple(sorted(n2.items())), tuple(Ns2), basis.L)
    R2 = _RED_CACHE.get(key)
    if R2 is None:
        R2 = _red_disk(key, lambda: density_generic(K - 1, n2, Ns2, basis, [0] * (K - 1)))
        if len(_RED_CACHE) > 64:
            _RED_CACHE.clear()
        _RED_CACHE[key] = R2
    shp = tuple(x + 1 for x in Ns)
    # map full slice s -> reduced slice t: s < v -> s; s >= v -> s - 1 (slice v-1 and v merge into v-1)
    idx_full = []
    for s in range(K - 1):
        if v == 0 and s == 0:
            idx_full.append(None)
        elif v == K - 1 and s == K - 2:
            idx_full.append(None)
        else:
            idx_full.append(s if s < v else s - 1)
    G = _dup_embed(R2, idx_full, shp)
    if pend:
        (a, b) = pend[0]
        beta = basis.bundle(1, 0, 0)
        hh = lib.to_half(beta[:, 0], S)
        if hh is None:
            return np.zeros(shp)
        pi, mu, vv = hh
        if pi:
            return np.zeros(shp)
        vv = np.concatenate([np.zeros(mu), np.asarray(vv, dtype=np.float64)])
        nsl = K - 1
        mask = np.array([1 if a <= s < b else 0 for s in range(nsl)], dtype=np.int64)
        shape = np.array(shp, dtype=np.int64)
        strides = np.ones(nsl, dtype=np.int64)
        for s in range(nsl - 2, -1, -1):
            strides[s] = strides[s + 1] * shp[s + 1]
        G = _diag_conv(G.ravel(), shape, strides, mask, vv).reshape(shp)
    return G


def phantom_density(K, n, ph, Ns, basis):
    """G[l] = level density of pattern n (derivative orders 0) with an extra angular-only edge ph = (a, b) carrying
    partial wave l: its state weight is 1, it adds no level, and it carries the level parity l mod 2 along its span
    (half representation (l % 2, 0, [1])), so that two single lines of partial wave l replacing it complete the slice
    parities.  Returns array [l, box]."""
    S = max(Ns) if Ns else 0
    bundles = [b for b, v in n.items() if v]
    lcap = basis.L
    shp = tuple(x + 1 for x in Ns)
    G = np.zeros((lcap + 1,) + shp)
    betas = {b: basis.bundle(n[b], 0, 0) for b in bundles}
    supports = [[l for l in range(betas[b].shape[1]) if np.any(betas[b][:, l])] for b in bundles]
    halves = {}
    for k, b in enumerate(bundles):
        for l in supports[k]:
            hh = lib.to_half(betas[b][:, l], S)
            if hh is not None:
                halves[(k, l)] = (hh[0], hh[1], np.ascontiguousarray(hh[2], dtype=np.float64))
    edges = bundles + [tuple(ph)]
    kp = len(bundles)
    sup = supports + [list(range(lcap + 1))]
    one = np.ones(1)
    cur, wl = None, None

    def flush(rest, wl):
        hs = [halves.get((k, l)) for k, l in enumerate(rest)]
        if any(h is None for h in hs):
            return
        for par in (0, 1):
            ls_ = [l for l in wl if l % 2 == par]
            if not ls_:
                continue
            box = np.zeros(shp)
            build_box(edges, hs + [(par, 0, one)], box, 1.0)
            if not np.any(box):
                continue
            for l in ls_:
                G[l] += wl[l] * box
    for ls, w in channel_stream(angular_channels(edges, sup, lcap, inner_edge=kp), len(edges), kp):
        if w == 0.0:
            continue
        rest = ls[:kp]
        if rest != cur:
            if cur is not None:
                flush(cur, wl)
            cur, wl = rest, {}
        wl[ls[kp]] = wl.get(ls[kp], 0.0) + w
    if cur is not None:
        flush(cur, wl)
    return G


def series_reduced_density(n, K, Ns, basis):
    """Density of a pattern with a vertex v carrying exactly two single lines to distinct vertices a, b (series:
    equal partial wave l) from the phantom density of the pattern without v (cached across patterns):
    F = sum_l (2l+1)^-1 conv_{line(a,v)}^l conv_{line(v,b)}^l Dup_v(G_l).  Derivative orders must be zero.
    Returns None if no such vertex."""
    deg = [sum(c for e, c in n.items() if x in e) for x in range(K)]
    v = None
    for x in range(K):
        inc = [e for e, c in n.items() if c and x in e]
        if deg[x] == 2 and len(inc) == 2 and all(n[e] == 1 for e in inc):
            v = x
            break
    if v is None:
        return None
    inc = [e for e, c in n.items() if c and v in e]
    nb = [e[0] if e[1] == v else e[1] for e in inc]
    lab = lambda x: x if x < v else x - 1
    n2 = {}
    for (a, b), c in n.items():
        if c and v not in (a, b):
            n2[(lab(a), lab(b))] = c
    n2 = {e: n2.get(e, 0) for e in pairs_of(K - 1)}
    ph = tuple(sorted((lab(nb[0]), lab(nb[1]))))
    # reduced slices: the phantom spans the merged region too
    sc2 = slice_counts(n2, K - 1)
    S = max(Ns)
    Ns2 = [S if (sc2[t] or ph[0] <= t < ph[1]) else 0 for t in range(K - 2)]
    key = ("ph", tuple(sorted(n2.items())), ph, tuple(Ns2), basis.L)
    G = _RED_CACHE.get(key)
    if G is None:
        G = _red_disk(key, lambda: phantom_density(K - 1, n2, ph, Ns2, basis))
        if len(_RED_CACHE) > 64:
            _RED_CACHE.clear()
        _RED_CACHE[key] = G
    shp = tuple(x + 1 for x in Ns)
    nsl = K - 1
    idx_full = []
    for s in range(nsl):
        if (v == 0 and s == 0) or (v == K - 1 and s == K - 2):
            idx_full.append(None)
        else:
            idx_full.append(s if s < v else s - 1)
    beta = basis.bundle(1, 0, 0)
    shape = np.array(shp, dtype=np.int64)
    strides = np.ones(nsl, dtype=np.int64)
    for s in range(nsl - 2, -1, -1):
        strides[s] = strides[s + 1] * shp[s + 1]
    F = np.zeros(shp)
    for l in range(G.shape[0]):
        Gl = G[l]
        if not np.any(Gl):
            continue
        H = _dup_embed(Gl, idx_full, shp)
        hh = lib.to_half(beta[:, l], S)
        if hh is None:
            continue
        vv = np.concatenate([np.zeros(hh[1]), np.asarray(hh[2], dtype=np.float64)])
        X = H.ravel()
        masks = []
        for e in inc:
            a, b = e
            masks.append(np.array([1 if a <= s < b else 0 for s in range(nsl)], dtype=np.int64))
            X = _diag_conv(X, shape, strides, masks[-1], vv)
        # slices crossed by both series lines carry parity 2 pi (the phantom covers only singly crossed slices):
        # sigma there gains pi
        both = masks[0] * masks[1]
        if hh[0] and np.any(both):
            X = _diag_conv(X, shape, strides, both, np.array([0.0, 1.0]))
        F += X.reshape(shp) / (2 * l + 1)
    return F


def density(kinds, n, Ns, modes, derivs=None):
    """Angular-integrated level density of line pattern n on the sigma box prod_s [0, Ns[s]]."""
    K = len(kinds)
    if derivs is None:
        derivs = [0] * K
    basis = modes.basis
    n = {e: n.get(e, 0) for e in pairs_of(K)}          # c4lib3d expects every pair
    legs = legs_of(n, K)
    if any(derivs[i] > 0 and legs[i] == 0 for i in range(K)):
        return None
    R = None
    if K == 5 and not any(derivs) and os.environ.get("ENGINE_REDUCE", "1") == "1":
        nbund = sum(1 for c in n.values() if c)
        if _has_k4(n, K):
            R = reduced_density(n, K, list(Ns), basis)
        elif nbund >= 7:
            R = series_reduced_density(n, K, list(Ns), basis)
    if R is not None:
        pass
    elif K <= 4 and os.environ.get("ENGINE_GENERIC") != "1":
        try:
            R = lib.pattern_density(basis, K, n, derivs, list(Ns))
        except NotImplementedError:
            R = density_generic(K, n, Ns, basis, derivs)
    else:
        R = density_generic(K, n, Ns, basis, derivs)
    if R is None:
        return None
    for s, ns_ in enumerate(slice_counts(n, K)):     # infeasible region (slice level < number of lines) exactly zero
        lo = (ns_ + 1) // 2
        if lo > 0 and R.ndim:
            idx = [slice(None)] * R.ndim
            idx[s] = slice(0, min(lo, R.shape[s]))
            R[tuple(idx)] = 0.0
    return R


# ======================================================================================= shells (as 2D)
if HAVE_NUMBA:
    from numba import prange

    @njit(parallel=True, cache=True)
    def _shell_nd(Rf, shape, Gs, N):
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

    @njit(parallel=True, cache=True)
    def _shell_w0(Rf, shape, Gs, N):
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


def shell_sums(R, Gs_list, N):
    if R.ndim == 0:
        R = R.reshape(1)
    S = R.ndim
    T = Gs_list[0].shape[0]
    Nmax = max(g.shape[1] for g in Gs_list)
    Gs = np.zeros((S, T, Nmax))
    for s in range(S):
        Gs[s, :, : Gs_list[s].shape[1]] = Gs_list[s]
    shape = np.array(R.shape, dtype=np.int64)
    return _shell_nd(np.ascontiguousarray(R).reshape(-1), shape, Gs, N)


def slice_G(alpha, pw, nlines, length, weight=None):
    """(-1)^pw / den^pw, den = alpha + 2 sigma (alpha = X0 (delta + n_lines)); infeasible levels zero."""
    sig = np.arange(length)
    den = alpha + 2.0 * sig
    g = np.zeros(length)
    ok = 2 * sig >= nlines
    if np.any(np.abs(den[ok]) < 1e-12):
        if not DROP_ZERO_DEN:
            raise RuntimeError("zero energy denominator")
        ok = ok & (np.abs(den) >= 1e-12)
    g[ok] = (-1.0) ** pw / den[ok] ** pw
    if weight is not None:
        g = g * weight[:length]
    return g


def shell_w(R, Gs_list, N, sw):
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
    na, N1 = f.shape
    N = N1 - 1
    F = np.cumsum(f, axis=1)
    out = np.zeros(N + 1)
    for M in range(N + 1):
        amax = min(M, na - 1)
        a = np.arange(amax + 1)
        out[M] = np.dot(F[: amax + 1, M], e[M] - e[M - a])
    return out
