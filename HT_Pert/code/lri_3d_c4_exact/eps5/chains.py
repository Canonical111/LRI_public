#!/usr/bin/env python3
"""Chain evaluation on top of engine.py.

A chain ("word") is a sequence of K vertices (kind V or M, eps-Taylor order d) acting on |p> (vertex 0 first), with
slice operators (pow, q) = R^pow (P - p)^q on the K-1 slices, optionally an extra slice weight array per slice.
<p| X_{K-1} s_{K-2} ... s_0 X_0 |p> is returned for every even cutoff L = 2M (cumulative in M), for each p.

eval_group() evaluates many words that share the vertex sequence: the density of each line pattern is computed once.
"""
from fractions import Fraction as Fr
from math import factorial

import numpy as np

import engine as eg


def word_keyamps(kinds, n, ps, slice_ops_list, z_end=None, exclude_level0=False):
    """For each word (slice ops), dict deltas -> {p: amplitude} including vertex factors, Wick counts, zero-mode path
    amplitudes and the (P-p)^q factors.  The Q projector removes slices with no chi lines and delta = 0 (or every
    chi-free slice if exclude_level0).  z_end: dict p -> end zero-mode number (open paths) or None (closed)."""
    K = len(kinds)
    legs = eg.legs_of(n, K)
    nsl = eg.slice_counts(n, K)
    zl = [eg.MAXLEGS[kinds[i]] - legs[i] for i in range(K)]
    if any(z < 0 for z in zl):
        return None
    combf = Fr(1)
    for i in range(K):
        combf *= factorial(legs[i])
    for b, v in n.items():
        combf /= factorial(v)
    vc = Fr(1)
    for i in range(K):
        vc *= eg.vcoef(kinds[i], legs[i])
    pref = combf * vc
    paths = {}
    for p in ps:
        z1 = None if z_end is None else z_end[p]
        for rs, amp in eg.zero_mode_paths(p, zl, z1):
            deltas = tuple(r - p for r in rs)
            ok = True
            for s in range(K - 1):
                if nsl[s] == 0 and (deltas[s] == 0 or exclude_level0):
                    ok = False
                    break
            if ok:
                paths.setdefault(deltas, {}).setdefault(p, 0)
                paths[deltas][p] += amp
    out = []
    for sops in slice_ops_list:
        ka = {}
        for deltas, d in paths.items():
            f = 1
            for s in range(K - 1):
                q = sops[s][1]
                if q:
                    f *= Fr(deltas[s] + nsl[s]) ** q
            if f == 0:
                continue
            for p, a in d.items():
                val = pref * a * f if isinstance(a, Fr) else float(pref) * a * float(f)
                if val != 0:
                    ka.setdefault(deltas, {})[p] = val
        out.append(ka)
    return out, nsl


def eval_group(kinds, derivs, words, N, modes, ps=(0, 1, 2, 3), max_lines=None, min_zero_legs=0,
               pattern_filter=None, z_end=None, exclude_level0=False, return_patterns=False):
    """words: list of (slice_ops, weights) with slice_ops = tuple of (pow, q) per slice and weights = None or a tuple of
    per-slice arrays (or None) multiplying the slice factor.  Returns list (per word) of {p: array over M}."""
    K = len(kinds)
    res = [{p: np.zeros(N + 1) for p in ps} for _ in words]
    per_pattern = [] if return_patterns else None
    if K == 1:
        # single vertex: <p|X|p>, level 0 only (diagonal zero-mode part); no slices
        for n in [dict()]:
            zl = [eg.MAXLEGS[kinds[0]]]
            for wi, _ in enumerate(words):
                for p in ps:
                    z1 = p if z_end is None else z_end[p]
                    for rs, amp in eg.zero_mode_paths(p, zl, z1):
                        if derivs[0] == 0:
                            res[wi][p] += float(eg.vcoef(kinds[0], 0) * amp) if isinstance(amp, Fr) else \
                                float(eg.vcoef(kinds[0], 0)) * amp
        return res
    pats = eg.patterns(kinds, max_lines, min_zero_legs)
    if pattern_filter is not None:
        pats = [n for n in pats if pattern_filter(n)]
    sops_list = [w[0] for w in words]
    for n in pats:
        r = word_keyamps(kinds, n, ps, sops_list, z_end, exclude_level0)
        if r is None:
            continue
        kas, nsl = r
        if not any(kas):
            continue
        # derivative of a vertex with no chi legs vanishes
        legs = eg.legs_of(n, K)
        if any(derivs[i] > 0 and legs[i] == 0 for i in range(K)):
            continue
        Ns = [N if nsl[s] > 0 else 0 for s in range(K - 1)]
        R = eg.density(kinds, n, Ns, modes, derivs)
        if R is None:
            continue
        for wi, (sops, wts) in enumerate(words):
            ka = kas[wi]
            if not ka:
                continue
            keys = list(ka)
            Gs = []
            for s in range(K - 1):
                pw = sops[s][0]
                wt = None if (wts is None or wts[s] is None) else wts[s]
                Gs.append(np.array([eg.slice_G(eg.X0 * (k[s] + nsl[s]), pw, nsl[s], Ns[s] + 1, wt) for k in keys]))
            sh = eg.shell_sums(R, Gs, N)
            cum = np.cumsum(sh, axis=1)
            for t, k in enumerate(keys):
                for p, a in ka[k].items():
                    res[wi][p] += float(a) * cum[t]
            if return_patterns:
                per_pattern.append((wi, n, {p: sum(float(ka[k][p]) * cum[t] for t, k in enumerate(keys) if p in ka[k])
                                            for p in ps}))
    if return_patterns:
        return res, per_pattern
    return res
