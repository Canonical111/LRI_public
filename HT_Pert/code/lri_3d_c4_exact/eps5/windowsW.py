#!/usr/bin/env python3
"""Scheme W of ../WINDOW_SPEC.md at eps^3..eps^5 (and controlled sub-variants).

Window atoms in RS words (rs.unroll(windows=True) gives ('D', k); here D_k is expanded into components):
  ('DZ', k)      zero-mode Bloch window: jump z -> z' on the zero-mode factor, weight h^(k)_{z'z}(M) - h^(k)_{z'z}(M - sigma)
                 (normalized basis), sigma = hol level of the state it acts on; vanishes on level-0 states;
  ('DM', k, j)   (1/4){Delta c_1^(k-j), M'_j}: an M_j vertex with >= 1 chi leg; window (1/4)(c(M) - c(M - sigma)) on the
                 slice before it plus the same on the slice after it (zero on a level-0 side);
  ('DV', k, j)   (1/2){Delta c_2^(k-j), V'_j}  (scheme W+V only).
Window l-functions are coupling-monomial decompositions: dict kappa -> array over l (hol units), kappa a tuple of
coupling symbols evaluated at the target cutoff.

Word evaluation (eval_decorated): outer vertices (V/M with eps orders; DM/DV vertices restricted to >= 1 chi leg),
outer slices with sub-slices separated by jumps, windows on outer slices.  Zero windows: shells; one window:
engine.shell_w + window contraction; two windows on one slice: product weight; two windows on two different slices:
explicit 2D contraction (words with <= 3 outer vertices only).
"""
import itertools
import os
from fractions import Fraction as Fr
from math import comb, factorial

import numpy as np

import engine as eg
import chains as ch
import rs

P = (0, 1, 2, 3)
G1 = 1.0 / 3.0


# ======================================================================================= word expansion
def expand_windows(ops, pw, components):
    """Expand every ('D', k) atom of an RS term into scheme components.  components: subset of {'DZ','DM','DV'}.
    Yields (factor Fr, ops tuple, pw tuple)."""
    choices = []
    for a in ops:
        if a[0] != "D":
            choices.append([(Fr(1), a)])
            continue
        k = a[1]
        opts = []
        if "DZ" in components:
            opts.append((Fr(1), ("DZ", k)))
        if "DM" in components:
            for j in range(0, k - 1):
                opts.append((Fr(1), ("DM", k, j)))
        if "DV" in components:
            for j in range(0, k - 1):
                opts.append((Fr(1), ("DV", k, j)))
        choices.append(opts)
    for combo in itertools.product(*choices):
        f = Fr(1)
        for c, _ in combo:
            f *= c
        yield f, tuple(a for _, a in combo), pw


def decorate(ops, pw):
    """RS word -> list of decorated variants (empty if the word vanishes).  Each variant is (verts, slices, windows):
      verts   : list of (kind, deriv, min_chi_legs) (DM/DV atoms become M/V vertices with >= 1 chi leg),
      slices  : list over outer slices of (subs, jumps): subs = list of [pow, q] sub-slices, jumps = DZ orders between
                consecutive sub-slices,
      windows : list of (outer slice, spec); spec = ('DZ', k, jump index) or ('DM'/'DV', k, j).
    A DM/DV vertex carries (1/4 or 1/2)[Dc(N_before) + Dc(N_after)]: the two sides give two variants (a side that is
    the reference state |p> has N = 0 and is dropped).  P atoms become q powers; DZ or P on |p> or <p| vanish."""
    if not ops:
        return []
    if ops[0][0] in ("P", "DZ") or ops[-1][0] in ("P", "DZ"):
        return []
    verts, slices = [], []
    cur_subs, cur_jumps = [[0, 0]], []
    dmv = []                              # (vertex index, spec)
    for i, a in enumerate(ops):
        if a[0] == "P":
            cur_subs[-1][1] += 1
        elif a[0] == "DZ":
            cur_jumps.append(a[1])
            cur_subs.append([0, 0])
        else:
            if verts:
                slices.append(([tuple(x) for x in cur_subs], list(cur_jumps)))
            kind = {"V": "V", "M": "M", "DM": "M", "DV": "V"}[a[0]]
            deriv = a[1] if a[0] in ("V", "M") else a[2]
            minchi = 1 if a[0] in ("DM", "DV") else 0
            if a[0] in ("DM", "DV"):
                dmv.append((len(verts), a))
            verts.append((kind, deriv, minchi))
            cur_subs, cur_jumps = [[0, 0]], []
        if i < len(ops) - 1:
            cur_subs[-1][0] += pw[i]
    K = len(verts)
    base = []
    for s, (subs, jumps) in enumerate(slices):
        for ji, k in enumerate(jumps):
            base.append((s, ("DZ", k, ji)))
    sides = []
    for vi, spec in dmv:
        opts = []
        if vi > 0:
            opts.append((vi - 1, spec))           # slice before the vertex
        if vi < K - 1:
            opts.append((vi, spec))               # slice after the vertex
        sides.append(opts)
    out = []
    for combo in itertools.product(*sides):
        out.append((verts, slices, base + list(combo)))
    return out


# ======================================================================================= zero-mode paths with jumps
def _paths(p, zlegs, slices, jmax, z_end=None):
    """zero-mode path enumeration: z0 = p; vertex 0; slice 0 sub-slices (with jumps of size <= jmax between them);
    vertex 1; ... ; last vertex returns to p.  Yields (zs, amp): zs[s] = tuple of zero-mode numbers of the
    sub-slices of slice s; amp = product of normalized vertex matrix elements (jumps contribute 1)."""
    K = len(zlegs)
    out = []

    def vstep(z, k):
        for zn in range(max(0, z - k), z + k + 1):
            d = zn - z
            if (d + k) % 2 or abs(d) > k:
                continue
            j = (d + k) // 2
            m = z - (k - j)
            if m < 0:
                continue
            amp = comb(k, j) * (factorial(z) * factorial(zn)) ** 0.5 / factorial(m)
            yield zn, amp

    def rec(i, z, zs, amp):
        if i == K - 1:
            target = p if z_end is None else z_end
            for zn, a in vstep(z, zlegs[i]):
                if zn == target:
                    out.append((list(zs), amp * a))
            return
        for zn, a in vstep(z, zlegs[i]):
            nsub = len(slices[i][0])
            # sub-slice zero-mode numbers: first = zn, later ones after jumps
            for jumps in itertools.product(*[range(-jmax, jmax + 1) for _ in range(nsub - 1)]):
                seq = [zn]
                ok = True
                for dj in jumps:
                    nz = seq[-1] + dj
                    if nz < 0:
                        ok = False
                        break
                    seq.append(nz)
                if not ok:
                    continue
                rec(i + 1, seq[-1], zs + [tuple(seq)], amp * a)

    rec(0, p, [], 1.0)
    return out


# ======================================================================================= decorated-word evaluation
# class probe (diagnostics only): restrict the chi-leg type of D^M vertices (M vertices with min_chi = 1):
#   zchi = one chi leg + one zero-mode leg, hop = one chi line in and one out, pc = pair creation, pa = pair annihilation
DM_TYPES = None if not os.environ.get("DM_TYPES") else set(os.environ["DM_TYPES"].split(","))


def _dm_type_ok(n, verts, K):
    for k in range(K):
        if verts[k][0] != "M" or verts[k][2] < 1:
            continue
        nin = sum(v for (i, j), v in n.items() if j == k)
        nout = sum(v for (i, j), v in n.items() if i == k)
        t = {(1, 0): "zchi", (0, 1): "zchi", (1, 1): "hop", (0, 2): "pc", (2, 0): "pa"}.get((nin, nout))
        if t not in DM_TYPES:
            return False
    return True


# variant probe (diagnostics only): DM_ZCHI=min evaluates the Z-chi part of D^M (one chi leg, one zero-mode leg) with the
# window of the lower-level side only, Delta c_1(l, min(N_s, N_s')), instead of the average over the two sides.
DM_ZCHI = os.environ.get("DM_ZCHI", "")


def _zchi_min_factor(n, verts, windows, K):
    fac = 1.0
    for s, spec in windows:
        if spec[0] != "DM":
            continue
        cand = [v for v in (s, s + 1) if verts[v][0] == "M" and verts[v][2] >= 1]
        if len(cand) != 1:
            continue
        v = cand[0]
        nin = sum(x for (i, j), x in n.items() if j == v)
        nout = sum(x for (i, j), x in n.items() if i == v)
        if nin + nout != 1:
            continue                                   # not a Z-chi vertex: keep the symmetric average
        before = (s == v - 1)
        low_side_before = (nout == 1)                  # creation: the lower level is before the vertex
        fac *= 2.0 if before == low_side_before else 0.0
    return fac


def eval_decorated(verts, slices, windows, N, modes, wfun, ps=P, max_lines=None, min_zero_legs=0, jmax=6,
                   z_end=None):
    """Value of a decorated word for every cutoff M (array over M) per p, decomposed by coupling monomials of the
    window functions: returns dict kappa_tuple -> {p: array}.
    wfun(spec, p, zs_slice) -> dict kappa -> l-array (the window l-function; for DZ it depends on the zero-mode numbers
    before/after the jump)."""
    K = len(verts)
    kinds = [v[0] for v in verts]
    derivs = [v[1] for v in verts]
    res = {}
    pats = eg.patterns(kinds, max_lines, min_zero_legs)
    for n in pats:
        legs = eg.legs_of(n, K)
        if any(legs[i] < verts[i][2] for i in range(K)):
            continue
        if DM_TYPES is not None and not _dm_type_ok(n, verts, K):
            continue
        wfac = _zchi_min_factor(n, verts, windows, K) if DM_ZCHI == "min" else 1.0
        if wfac == 0.0:
            continue
        if any(derivs[i] > 0 and legs[i] == 0 for i in range(K)):
            continue
        nsl = eg.slice_counts(n, K)
        # windows / jumps act only on states with chi (level >= 2)
        if any(nsl[s] == 0 for s, _ in windows):
            continue
        zl = [eg.MAXLEGS[kinds[i]] - legs[i] for i in range(K)]
        combf = Fr(1)
        for i in range(K):
            combf *= factorial(legs[i])
        for b, v in n.items():
            combf /= factorial(v)
        vc = Fr(1)
        for i in range(K):
            vc *= eg.vcoef(kinds[i], legs[i])
        pref = float(combf * vc) * wfac
        # keys
        keys = {}
        for p in ps:
            for zs, amp in _paths(p, zl, slices, jmax, None if z_end is None else z_end[p]):
                ok = True
                fq = 1.0
                for s in range(K - 1):
                    subs = slices[s][0]
                    for (pwr, q), z in zip(subs, zs[s]):
                        if nsl[s] == 0 and z == p:
                            ok = False
                            break
                        if q:
                            fq *= float(z - p + nsl[s]) ** q
                    if not ok:
                        break
                if not ok or fq == 0.0 or amp == 0.0:
                    continue
                kk = tuple(zs)
                keys.setdefault(kk, {})
                keys[kk][p] = keys[kk].get(p, 0.0) + pref * amp * fq
        if not keys:
            continue
        Ns = [N if nsl[s] > 0 else 0 for s in range(K - 1)]
        R = eg.density(kinds, n, Ns, modes, derivs)
        if R is None:
            continue
        klist = list(keys)
        _accumulate(res, R, n, nsl, Ns, slices, windows, keys, klist, N, wfun, ps)
    return res


def _accumulate(res, R, n, nsl, Ns, slices, windows, keys, klist, N, wfun, ps):
    S = len(slices)
    # group (key, p) items; slice factor uses delta = z - p
    items = [(kk, p, a) for kk in klist for p, a in keys[kk].items()]
    Gs = []
    for s in range(S):
        rows = []
        for kk, p, a in items:
            g = np.ones(Ns[s] + 1)
            for (pwr, q), z in zip(slices[s][0], kk[s]):
                if pwr:
                    g = g * eg.slice_G(eg.X0 * (z - p + nsl[s]), pwr, nsl[s], Ns[s] + 1)
            rows.append(g)
        Gs.append(np.array(rows))
    nw = len(windows)
    if nw == 0:
        sh = eg.shell_sums(R, Gs, N)
        cum = np.cumsum(sh, axis=1)
        for t, (kk, p, a) in enumerate(items):
            d = res.setdefault((), {q: np.zeros(N + 1) for q in ps})
            d[p] += a * cum[t]
        return
    wslices = sorted(set(s for s, _ in windows))
    if len(wslices) == 1:
        sw = wslices[0]
        f = eg.shell_w(R, Gs, N, sw)                 # (T, Nsw+1, N+1)
        F = np.cumsum(f, axis=2)
        for t, (kk, p, a) in enumerate(items):
            wf = [wfun(spec, p, kk[s]) for s, spec in windows]
            for kap_combo in itertools.product(*[list(x.items()) for x in wf]):
                kap = tuple(sorted(sum((list(kc[0]) for kc in kap_combo), [])))
                es = [kc[1] for kc in kap_combo]
                val = _wcontract(F[t], es)
                d = res.setdefault(kap, {q: np.zeros(N + 1) for q in ps})
                d[p] += a * val
        return
    if len(wslices) == 2 and R.ndim == 2:
        s1, s2 = wslices
        for t, (kk, p, a) in enumerate(items):
            Rw = R * Gs[0][t][:, None] * Gs[1][t][None, :]
            wf1 = [wfun(spec, p, kk[s]) for s, spec in windows if s == s1]
            wf2 = [wfun(spec, p, kk[s]) for s, spec in windows if s == s2]
            for c1 in itertools.product(*[list(x.items()) for x in wf1]):
                for c2 in itertools.product(*[list(x.items()) for x in wf2]):
                    kap = tuple(sorted(sum((list(kc[0]) for kc in c1 + c2), [])))
                    val = _wcontract2(Rw if s1 == 0 else Rw.T, [kc[1] for kc in c1], [kc[1] for kc in c2], N)
                    d = res.setdefault(kap, {q: np.zeros(N + 1) for q in ps})
                    d[p] += a * val
        return
    raise NotImplementedError(f"windows on slices {wslices} with density dim {R.ndim}")


def _wcontract(F, es):
    """F[a, M] = sum_{m <= M} f[a, m]; es = list of l-arrays; returns T(M) = sum_{a<=M} F[a, M] prod_i (e_i(M) - e_i(M-a))."""
    na, N1 = F.shape
    out = np.zeros(N1)
    for M in range(N1):
        amax = min(M, na - 1)
        a = np.arange(amax + 1)
        w = np.ones(amax + 1)
        for e in es:
            w = w * (e[M] - e[M - a])
        out[M] = np.dot(F[: amax + 1, M], w)
    return out


def _wcontract2(Rw, es1, es2, N):
    """2D: Rw[a, b] (already times slice factors); T(M) = sum_{a,b <= M} Rw prod(e1(M)-e1(M-a)) prod(e2(M)-e2(M-b))."""
    na, nb = Rw.shape
    out = np.zeros(N + 1)
    for M in range(N + 1):
        A = min(M, na - 1)
        B = min(M, nb - 1)
        wa = np.ones(A + 1)
        for e in es1:
            wa = wa * (e[M] - e[M - np.arange(A + 1)])
        wb = np.ones(B + 1)
        for e in es2:
            wb = wb * (e[M] - e[M - np.arange(B + 1)])
        out[M] = wa @ Rw[: A + 1, : B + 1] @ wb
    return out
