"""Key amplitudes, shells, exact-weight reductions, functionals and key-pair products (PLAN.md sec. 3.3, 3.5).

A chain is (verts, sops): verts = tuple of (kind, Taylor order) (vertex 0 acts first), sops = tuple of slice operators
(pow, q) or (pow, q, mod) meaning R^pow (P - p)^q [x mod].  mod = ("D0", k1, k2) multiplies the key amplitude by
(c_P - (delta_s + n_s)/8), c_P = [P >= k1] + [P >= k2], P = p + delta_s + n_s (used by the D0 window insertions,
windows5.py; the factor is exact and depends on p, delta, n only).
Key amplitude A_p(delta) = Wick count x vertex coefficients x zero-mode path amplitude x prod_s (delta_s + n_s)^q
(-1)^pow [x mod factors]; mod = ("D0d", k1, k2, k3, k4) gives c(k1,k2) - c(k3,k4) (difference of two D0 insertions,
windows5.delta_R5_engine); shell weight 1/den^pow (shells.slice_arrays).  X_p(cut4) = sum_delta A_p(delta) cum_delta at
storage index cut4 - p + MOFF.  Functionals sum_p w_p f(p) X_p are evaluated with exact per-key weights and the top
shells of the p-shift (C4P functional_from_reduced)."""
from fractions import Fraction as Fr
from math import factorial

import numpy as np

from .common import FUNCTIONALS, MAXLEGS, MOFF, PS, vcoef
from .density import density_even
from .paths import (legs_of, pattern_key, patterns, reverse_pattern, slice_counts, zero_mode_paths)
from .shells import shell_sums, slice_arrays


def _mod_factor(mod, p, delta, nlines):
    if mod is None:
        return Fr(1)
    if mod[0] == "D0":
        P = p + delta + nlines
        c = int(P >= mod[1]) + int(P >= mod[2])
        return Fr(c) - Fr(delta + nlines, 8)
    if mod[0] == "D0d":            # difference of two D0 constants: (c(k1,k2) - c(k3,k4)); the (d+n)/8 parts cancel
        P = p + delta + nlines
        return Fr(int(P >= mod[1]) + int(P >= mod[2]) - int(P >= mod[3]) - int(P >= mod[4]))
    raise ValueError(mod)


def _sop(s):
    return (s[0], s[1], s[2] if len(s) > 2 else None)


def pattern_keys(verts, sops, n):
    """{delta: [A_0..A_3]} (exact) of pattern n; {} if no zero-mode path survives or a vertex with eps-order > 0 has
    no chi legs (its Taylor coefficient vanishes: u_0 is eps-independent)."""
    kinds = [v[0] for v in verts]
    ords = [v[1] for v in verts]
    K = len(verts)
    legs = legs_of(n, K)
    if any(ords[i] > 0 and legs[i] == 0 for i in range(K)):
        return {}
    if any(legs[i] > MAXLEGS[kinds[i]] for i in range(K)):
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
    ops = [_sop(s) for s in sops]
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
                pw, q, mod = ops[s]
                fac *= Fr(deltas[s] + nsl[s]) ** q * (-1) ** pw * _mod_factor(mod, p, deltas[s], nsl[s])
            if not ok or fac == 0:
                continue
            keyamp.setdefault(deltas, [Fr(0)] * 4)
            keyamp[deltas][p] += combf * vc * amp * fac
    return {k: v for k, v in keyamp.items() if any(x != 0 for x in v)}


def key_shells(verts, sops, n, Lmax, ser, block=32, R=None, reference=False):
    """(keyamp, shells (T, 4 Lmax + 1 + MOFF), density) of pattern n; (None, None, None) if it contributes nothing."""
    K = len(verts)
    keyamp = pattern_keys(verts, sops, n)
    if not keyamp:
        return None, None, None
    nsl = slice_counts(n, K)
    if R is None:
        R = density_even(K, n, [v[1] for v in verts], ser, Lmax, block=block, reference=reference)
    if R is None:
        return None, None, None
    keys = list(keyamp)
    M = 4 * Lmax + 1 + MOFF
    ops = [_sop(s) for s in sops]
    Gs, Es = [], []
    for s in range(K - 1):
        ga, ea = [], []
        for k in keys:
            g, e = slice_arrays(k[s], nsl[s], ops[s][0], R.shape[s])
            ga.append(g)
            ea.append(e)
        Gs.append(np.ascontiguousarray(np.array(ga)))
        Es.append(np.ascontiguousarray(np.array(ea)))
    sh = shell_sums(R, Gs, Es, M)
    return {k: keyamp[k] for k in keys}, sh, R


# ============================================================================ reductions and functionals
def reduce_keys(keyamp, sh, prefs, mult=1.0):
    """Per prefactor vector f (name -> 4 Fractions): Shp[p] = sum_delta f(p) A_p S_delta (per-p shells) and
    Shw[w] = sum_delta [sum_p w_p f(p) A_p] S_delta (exact weights), times mult."""
    keys = list(keyamp)
    out = {}
    for name, f in prefs.items():
        A = [[f[p] * keyamp[k][p] for p in PS] for k in keys]
        Shp = np.zeros((4, sh.shape[1]))
        for p in PS:
            c = np.array([float(A[t][p]) for t in range(len(keys))])
            Shp[p] = mult * (c @ sh)
        Shw = {}
        for wn, w in FUNCTIONALS.items():
            c = np.array([float(sum(w[p] * A[t][p] for p in PS)) for t in range(len(keys))])
            Shw[wn] = mult * (c @ sh)
        out[name] = dict(Shp=Shp, Shw=Shw)
    return out


def add_reduced(acc, red):
    for f, d in red.items():
        if f not in acc:
            acc[f] = dict(Shp=np.zeros_like(d["Shp"]), Shw={k: np.zeros_like(v) for k, v in d["Shw"].items()})
        acc[f]["Shp"] += d["Shp"]
        for k in d["Shw"]:
            acc[f]["Shw"][k] += d["Shw"][k]
    return acc


def functional(red, wname):
    """F_w(c), c = 0..4Lmax:  cumsum(Shw)[c + MOFF] - sum_p w_p sum_{j<p} Shp[p][c - j + MOFF]."""
    w = FUNCTIONALS[wname]
    Shw = red["Shw"][wname]
    cum = np.cumsum(Shw)
    nc = len(Shw) - MOFF
    out = cum[MOFF:].copy()
    for p in PS:
        if w[p] == 0 or p == 0:
            continue
        for j in range(p):
            out -= float(w[p]) * red["Shp"][p][MOFF - j: MOFF - j + nc]
    return out


def perp(red, p):
    """X_p(c) = sum of the per-p shells up to storage index c - p + MOFF, c = 0..4Lmax."""
    cum = np.cumsum(red["Shp"][p])
    nc = len(cum) - MOFF
    return cum[MOFF - p: MOFF - p + nc]


def top(red, p, mlo, mhi):
    """sum of the per-p shells with physical index m in (c - mhi, c - mlo] for every c (cancellation-free windows)."""
    Shp = red["Shp"][p]
    nc = len(Shp) - MOFF
    out = np.zeros(nc)
    for j in range(mlo, mhi):
        idx = np.arange(nc) + MOFF - j
        ok = (idx >= 0) & (idx < len(Shp))
        out[ok] += Shp[idx[ok]]
    return out


# ============================================================================ key records and products
def records_add(recs, keyamp, sh, mult=1.0):
    for t, k in enumerate(keyamp):
        recs.append((tuple(keyamp[k]), mult * sh[t]))
    return recs


def _prep(recs, nc):
    out = []
    for amps, sh in recs:
        cum = np.cumsum(sh)
        C = cum[MOFF: MOFF + nc]
        tops = []
        for p in PS:
            t = np.zeros(nc)
            for j in range(p):
                t += sh[MOFF - j: MOFF - j + nc]
            tops.append(t)
        out.append((amps, C, tops))
    return out


def product_functional(recsA, recsB, w, f, nc):
    """sum_p w_p f(p) a_p(c) b_p(c) over key pairs with exact sum_p w_p f(p) A_p B_p (C4P product_functional)."""
    a, b = _prep(recsA, nc), _prep(recsB, nc)
    terms = []
    for Aa, Ca, ta in a:
        for Bb, Cb, tb in b:
            Wk = sum(w[p] * f[p] * Aa[p] * Bb[p] for p in PS)
            if Wk != 0:
                terms.append(float(Wk) * Ca * Cb)
            for p in PS:
                c = w[p] * f[p] * Aa[p] * Bb[p]
                if c == 0:
                    continue
                cf = float(c)
                terms.append(-cf * Ca * tb[p])
                terms.append(-cf * Cb * ta[p])
                terms.append(cf * ta[p] * tb[p])
    if not terms:
        return np.zeros(nc)
    return _fsum_cols(np.array(terms))


def _fsum_cols(A):
    import math
    return np.array([math.fsum(A[:, i]) for i in range(A.shape[1])])


def product_window0(recsA, recsB, mhi, nc):
    """p = 0 window of a product: a(c) b(c) - a(c - mhi) b(c - mhi) as a(c) [b(c) - b(c-mhi)] + b(c-mhi) [a(c) -
    a(c-mhi)], differences as top-shell sums."""
    def parts(recs):
        val = np.zeros(nc)
        win = np.zeros(nc)
        for amps, sh in recs:
            if amps[0] == 0:
                continue
            a0 = float(amps[0])
            val += a0 * np.cumsum(sh)[MOFF: MOFF + nc]
            for j in range(mhi):
                idx = np.arange(nc) + MOFF - j
                ok = idx >= 0
                win[ok] += a0 * sh[idx[ok]]
        return val, win
    va, wa = parts(recsA)
    vb, wb = parts(recsB)
    return va * wb + (vb - wb) * wa


# ============================================================================ chains
def is_palindrome(verts, sops):
    return tuple(reversed(verts)) == tuple(verts) and tuple(reversed([_sop(s) for s in sops])) == tuple(
        _sop(s) for s in sops)


def chain_items(verts, mirror):
    """[(pattern, multiplicity)] over all patterns (or one representative per reversal pair if mirror)."""
    K = len(verts)
    pats = patterns([v[0] for v in verts])
    if not mirror:
        return [(n, 1) for n in pats]
    reps = {}
    for n in pats:
        key = min(pattern_key(n), pattern_key(reverse_pattern(n, K)))
        reps.setdefault(key, [n, 0])
        reps[key][1] += 1
    return [(n, m) for n, m in reps.values()]


def eval_chain(verts, sops, Lmax, ser, prefs, keep_records=False, block=32, reference=False):
    """Serial evaluation of a whole chain: reduced shells per prefactor (+ key records if requested).  Uses the
    pattern mirror only for palindromic chains and only when records are not needed."""
    mirror = is_palindrome(verts, sops) and not keep_records
    acc = {}
    recs = [] if keep_records else None
    M = 4 * Lmax + 1 + MOFF
    for n, mult in chain_items(verts, mirror):
        keyamp, sh, R = key_shells(verts, sops, n, Lmax, ser, block=block, reference=reference)
        del R
        if keyamp is None:
            continue
        add_reduced(acc, reduce_keys(keyamp, sh, prefs, float(mult)))
        if keep_records:
            records_add(recs, keyamp, sh)
    for name in prefs:
        if name not in acc:
            acc[name] = dict(Shp=np.zeros((4, M)), Shw={w: np.zeros(M) for w in FUNCTIONALS})
    return acc, recs
