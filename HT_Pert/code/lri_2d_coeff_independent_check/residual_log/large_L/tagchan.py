#!/usr/bin/env python3
"""Diagrammatic (chain-sum) evaluation of the zero-mode-tagged phi channel through eps^3 and of
delta^(3)(L) = (1/4)[c_1^(3)(L - 2) - c1tag^(3)(L; 2, 2)] (WINDOW_SPEC Sec. 2.5a, scheme Wc windows, r_3 removed),
for every even L <= Lmax in one run.

Same formulation as lib/engine.py (zero mode = oscillator with exact path amplitudes, chi lines by Wick contraction,
J-projected holomorphic densities, one run gives every cutoff), with three extensions:
  * tagged zero-mode paths.  The zero-mode sector state is (n, i, o): n regular zero modes, i = 1 if X_in is present,
    o = 1 if X_out is present.  A vertex :Z^k: = sum_j C(k,j) (Z^-)^j (Z^+)^(k-j) with Z^+ = a + X_in, Z^- = a^dag +
    X_out^dag: at most one annihilator may hit X_in (factor k - j), at most one creator may create X_out (factor j, only
    if o = 0).  Start (0,1,0) = |X_in>; end (0,1,0) or (0,0,1) (glued projection <X_in| + <X_out|).  Model states
    (chi-free, total zero-mode number 1: X_in, X_out, regular |1>) are excluded from every resolvent.
  * budget offsets.  A slice state with chi level 2 sigma and tags (i, o) has budget level 2(sigma + t), t =
    i nu_in/2 + o nu_out/2 (+ u, a uniform offset).  The cutoff keeps max over slices and external states of
    (sigma + t) <= M (L = 2M).  Energy denominators and (P - p) factors use the true levels (tags are zero modes).
  * windows with budget levels.  D^M,(2) = (1/4){Delta c_1^(2)(L, N_hat), M'} with N = budget level on both sides,
    including the external states (N = nu for |X_in>, |X_out>); D^zm,(2) and D^zm,(3) on chi-free tagged states
    (the only place they act at this order): h_{z'z}(M) - h_{z'z}(M - t) on the regular zero modes.
With u = 1, no tags and no D^zm on chi-free states, the same code gives the rule-Wc auxiliary channels at
l = L - 2 (windows c_1(L) - c_1(l - N), i.e. budget offset 1): c_1^(3)(L - 2; L).

usage: python3 tagchan.py --Lmax 1000 --out results/delta3_L1000.npz [--nu 2,2]"""
import argparse
import os
import sys
import time
from fractions import Fraction as Fr
from math import comb, factorial

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
os.environ.setdefault("RS_EXACT_DIR", os.path.join(HERE, "..", "..", "rs_exact"))

import engine as eg  # noqa: E402
import rs  # noqa: E402

try:
    from numba import njit
    HAVE_NUMBA = True
except Exception:  # pragma: no cover
    HAVE_NUMBA = False

G1 = Fr(1, 3)
_RCACHE = {}          # density cache: (kinds, derivs, pattern, Ns) -> R (shared by all words and channels)


def cached_density(kinds, n, Ns, modes, derivs):
    key = (tuple(kinds), tuple(derivs), tuple(sorted(n.items())), tuple(Ns))
    if key not in _RCACHE:
        _RCACHE[key] = eg.density(list(kinds), n, Ns, modes, list(derivs))
    return _RCACHE[key]


# ======================================================================================= tagged zero-mode paths
def vertex_steps(state, k, tagmode):
    """<state'| :Z^k: |state> in the normalized basis, tags (i, o) occupation 0/1.  Yields (state', amp^2 as Fr,
    sign/int prefactor)."""
    n, i, o = state
    for j in range(k + 1):                 # creators
        ann = k - j
        tas = (0, 1) if (tagmode and i == 1 and ann >= 1) else (0,)
        for ta in tas:
            m = n - (ann - ta)
            if m < 0:
                continue
            tcs = (0, 1) if (tagmode and o == 0 and j >= 1) else (0,)
            for tc in tcs:
                n2 = m + (j - tc)
                c = comb(k, j) * (ann if ta else 1) * (j if tc else 1)
                sq = Fr(factorial(n) * factorial(n2), factorial(m) ** 2)
                yield (n2, i - ta, o + tc), c, sq


def _isqrt_fr(x):
    from math import isqrt
    a, b = x.numerator, x.denominator
    ra, rb = isqrt(a), isqrt(b)
    if ra * ra == a and rb * rb == b:
        return Fr(ra, rb)
    return None


def paths(zlegs, mode, nsl, start=None, ends=None):
    """Zero-mode paths for vertex zero-leg counts zlegs.  mode = ('tag',) or ('plain', p).  nsl[s] = chi lines on slice s
    (model-state exclusion on chi-free slices).  Optional start state / end set (for jump words).
    Returns list of (slice_states tuple, end_state, amplitude Fr)."""
    tagmode = mode[0] == "tag"
    peff = 1 if tagmode else mode[1]
    s0 = start if start is not None else ((0, 1, 0) if tagmode else (peff, 0, 0))
    if ends is None:
        ends = {(0, 1, 0), (0, 0, 1)} if tagmode else {(peff, 0, 0)}
    K = len(zlegs)
    out = []

    def rec(v, st, sts, c, sq):
        for st2, cc, sq2 in vertex_steps(st, zlegs[v], tagmode):
            if v == K - 1:
                if st2 in ends:
                    a = _isqrt_fr(sq * sq2)
                    if a is None:
                        raise RuntimeError("non-rational closed path amplitude")
                    out.append((tuple(sts), st2, c * cc * a))
                continue
            # slice v state st2: exclusion of model states on chi-free slices
            if nsl[v] == 0 and sum(st2) == peff:
                continue
            rec(v + 1, st2, sts + [st2], c * cc, sq * sq2)

    rec(0, s0, [], 1, Fr(1))
    return out


# ======================================================================================= shell kernels with offsets
if HAVE_NUMBA:
    @njit(cache=True)
    def _shell1(RG, t, text, N):
        """out[M] += RG[sigma] at M = max(sigma + t, text) (<= N)."""
        out = np.zeros(N + 1)
        for s in range(RG.shape[0]):
            M = s + t
            if text > M:
                M = text
            if M <= N:
                out[M] += RG[s]
        return out

    @njit(cache=True)
    def _shell2(R, g0, g1, t0, t1, text, N):
        out = np.zeros(N + 1)
        for a in range(R.shape[0]):
            ga = g0[a]
            if ga == 0.0:
                continue
            Ma = a + t0
            if text > Ma:
                Ma = text
            for b in range(R.shape[1]):
                r = R[a, b]
                if r == 0.0:
                    continue
                M = b + t1
                if Ma > M:
                    M = Ma
                if M <= N:
                    out[M] += r * ga * g1[b]
        return out

    @njit(cache=True)
    def _win1(RG, t, text, e, N):
        """T(M) = sum_{sigma: max(sigma + t, text) <= M} RG[sigma] (e[M] - e[M - sigma - t])."""
        out = np.zeros(N + 1)
        for M in range(N + 1):
            if text > M:
                continue
            acc = 0.0
            for s in range(RG.shape[0]):
                if s + t > M:
                    break
                acc += RG[s] * (e[M] - e[M - s - t])
            out[M] = acc
        return out
else:  # pragma: no cover
    def _shell1(RG, t, text, N):
        out = np.zeros(N + 1)
        for s in range(RG.shape[0]):
            M = max(s + t, text)
            if M <= N:
                out[M] += RG[s]
        return out

    def _shell2(R, g0, g1, t0, t1, text, N):
        out = np.zeros(N + 1)
        for a in range(R.shape[0]):
            for b in range(R.shape[1]):
                M = max(a + t0, b + t1, text)
                if M <= N:
                    out[M] += R[a, b] * g0[a] * g1[b]
        return out

    def _win1(RG, t, text, e, N):
        out = np.zeros(N + 1)
        for M in range(N + 1):
            if text > M:
                continue
            for s in range(RG.shape[0]):
                if s + t > M:
                    break
                out[M] += RG[s] * (e[M] - e[M - s - t])
        return out


# ======================================================================================= the channel evaluator
class Channel:
    """mode = ('tag',) with charges (cin, cout) in hol units (nu/2), or ('plain', p); u = uniform budget offset.
    zm_on_chifree: apply D^zm on chi-free states with tag budget > 0 (tagged channel); never for plain/aux."""

    def __init__(self, N, modes, mode, cin=0, cout=0, u=0):
        self.N, self.modes, self.mode = N, modes, mode
        self.cin, self.cout, self.u = cin, cout, u
        self.tag = mode[0] == "tag"
        self.peff = 1 if self.tag else mode[1]

    def toff(self, st):
        """tag part of the budget offset of a zero-mode state (hol units)."""
        n, i, o = st
        return self.cin * i + self.cout * o

    def t_ref(self):
        return (self.cin if self.tag else 0) + self.u

    def t_end(self, st):
        return self.toff(st) + self.u

    # ---------------------------------------------------------------------------------------------- chains
    def chain(self, kinds, derivs, sops, window=None, minchi=None):
        """<proj| X_{K-1} s ... s X_0 |ref> for every cutoff M (array over M), K <= 3.
        sops[s] = (pow, q).  window = None, ('ref', e) [(1/4)-weighted outside: weight e(M) - e(M - t_ref)],
        ('end', e) [e(M) - e(M - t_end)] or ('slice', s, e) [e(M) - e(M - sigma_s - t_s)].  minchi[i]: minimum chi
        legs at vertex i (D^M vertices)."""
        N, modes = self.N, self.modes
        K = len(kinds)
        out = np.zeros(N + 1)
        pats = eg.patterns(list(kinds), None, 0)
        for n in pats:
            legs = eg.legs_of(n, K)
            if minchi is not None and any(legs[i] < minchi[i] for i in range(K)):
                continue
            if any(derivs[i] > 0 and legs[i] == 0 for i in range(K)):
                continue
            nsl = eg.slice_counts(n, K)
            zl = [eg.MAXLEGS[kinds[i]] - legs[i] for i in range(K)]
            if any(z < 0 for z in zl):
                continue
            combf = Fr(1)
            for i in range(K):
                combf *= factorial(legs[i])
            for b, v in n.items():
                combf /= factorial(v)
            vc = Fr(1)
            for i in range(K):
                vc *= eg.vcoef(kinds[i], legs[i])
            pref = combf * vc
            keys = {}
            for sts, end, amp in paths(zl, self.mode, nsl):
                f = Fr(1)
                for s in range(K - 1):
                    q = sops[s][1]
                    if q:
                        f *= Fr(sum(sts[s]) - self.peff + nsl[s]) ** q
                if f == 0:
                    continue
                deltas = tuple(sum(st) - self.peff for st in sts)
                ts = tuple(self.toff(st) + self.u for st in sts)
                tz = tuple(self.toff(st) for st in sts)
                key = (deltas, ts, tz, self.t_end(end))
                keys[key] = keys.get(key, Fr(0)) + pref * amp * f
            keys = {k: v for k, v in keys.items() if v != 0}
            if not keys:
                continue
            Ns = [N if nsl[s] > 0 else 0 for s in range(K - 1)]
            if K == 1:
                R = None
            else:
                R = cached_density(kinds, n, Ns, modes, derivs)
                if R is None:
                    continue
            for (deltas, ts, tz, tend), a in keys.items():
                text = max(self.t_ref(), tend)
                if K == 1:
                    val = np.zeros(N + 1)
                    if text <= N:
                        val[text] = 1.0
                    val = np.cumsum(val)
                    out += float(a) * self._wrap_const(val, window, tend)
                    continue
                gs = [eg.slice_G((deltas[s] + nsl[s]) / 2.0, sops[s][0], nsl[s], Ns[s] + 1) for s in range(K - 1)]
                if K == 2:
                    RG = np.ascontiguousarray(R * gs[0])
                    if window is not None and window[0] == "slice":
                        e = window[2]
                        val = _win1(RG, ts[0], text, np.ascontiguousarray(e), N)
                    else:
                        val = np.cumsum(_shell1(RG, ts[0], text, N))
                        val = self._wrap_const(val, window, tend)
                else:
                    if window is not None and window[0] == "slice":
                        raise NotImplementedError("slice windows on 3-vertex chains do not occur at eps^3")
                    val = np.cumsum(_shell2(np.ascontiguousarray(R), gs[0], gs[1], ts[0], ts[1], text, N))
                    val = self._wrap_const(val, window, tend)
                out += float(a) * val
        return out

    def _wrap_const(self, val, window, tend):
        if window is None:
            return val
        Ms = np.arange(self.N + 1)
        if window[0] == "ref":
            t = self.t_ref()
        elif window[0] == "end":
            t = tend
        else:
            raise ValueError(window)
        e = window[1]
        w = np.zeros(self.N + 1)
        ok = Ms - t >= 0
        w[ok] = e[Ms[ok]] - e[Ms[ok] - t]
        return val * w

    # ---------------------------------------------------------------------------------------------- D^zm words
    def dz_first(self, h_to_from, verts_after):
        """<proj| V0(zero legs only) R DZ |ref>: DZ acts on the chi-free tagged reference.  h_to_from(z', z) -> l-array.
        Returns array over M."""
        N = self.N
        out = np.zeros(N + 1)
        if not self.tag:
            return out
        t = self.cin                                    # tag budget of |X_in> (u = 0 here)
        Ms = np.arange(N + 1)
        for zp in range(2, 13, 2):
            arr = h_to_from(zp, 0)
            if arr is None:
                continue
            w = np.zeros(N + 1)
            ok = Ms - t >= 0
            w[ok] = arr[Ms[ok]] - arr[Ms[ok] - t]
            st = (zp, 1, 0)
            # R on (zp, 1, 0): den = (total - 1)/2 = zp/2, R = -1/den
            Rf = -1.0 / (zp / 2.0)
            amp = 0.0
            for st2, c, sq in vertex_steps(st, 4, True):
                if st2 in ((0, 1, 0), (0, 0, 1)):
                    amp += c * float(sq) ** 0.5 * float(eg.vcoef("V", 0))
            if amp:
                out += w * Rf * amp * (Ms >= t)
        return out

    def dz_last(self, h_to_from):
        """<proj| DZ R V0(zero legs only) |ref>."""
        N = self.N
        out = np.zeros(N + 1)
        if not self.tag:
            return out
        Ms = np.arange(N + 1)
        for st, c, sq in vertex_steps((0, 1, 0), 4, True):
            n, i, o = st
            if (i, o) not in ((1, 0), (0, 1)) or n == 0:
                continue                               # must jump to a model state; n = 0 would be a model state
            t = self.toff(st)
            if t == 0:
                continue
            den = (sum(st) - 1) / 2.0
            a = c * float(sq) ** 0.5 * float(eg.vcoef("V", 0))
            arr = h_to_from(0, n)
            if arr is None:
                continue
            w = np.zeros(N + 1)
            ok = Ms - t >= 0
            w[ok] = arr[Ms[ok]] - arr[Ms[ok] - t]
            out += w * (-1.0 / den) * a
        return out

    def dz_diag(self, arr):
        """<proj| DZ |ref> = arr(M) - arr(M - t_ref) (diagonal z = 0 -> 0 on the tagged reference)."""
        N = self.N
        out = np.zeros(N + 1)
        if not self.tag:
            return out
        Ms = np.arange(N + 1)
        t = self.cin
        ok = Ms - t >= 0
        out[ok] = arr[Ms[ok]] - arr[Ms[ok] - t]
        return out


# ======================================================================================= energies through eps^3
def channel_energy(ch, n_order, r2, g2, c1_2, h2, h3_00, with_dm=True, with_dz=True):
    """E^(n) (n = 2 or 3) of the channel on the window footing: r_n, g_n first-order terms excluded.
    r2, g2 arrays over M (outer cutoff), c1_2 array over l, h2 dict (to, from) -> array, h3_00 array or None."""
    E = rs.unroll(n_order, windows=True)[n_order]
    N = ch.N
    tot = np.zeros(N + 1)
    parts = {}
    for (c, sy, ops, pw) in E:
        coef = float(c)
        arr_coef = np.ones(N + 1)
        skip = False
        for s in sy:
            if s == "E1":
                skip = True                            # shifted E1 = g1 <proj|V|ref> = 0 for p <= 1 and the tag
            elif s == "r2":
                arr_coef = arr_coef * r2
            elif s == "g2":
                arr_coef = arr_coef * g2
            elif s in ("r3", "g3"):
                skip = True                            # window footing (r_3 removed); <ref|V|ref> = 0
            else:
                raise ValueError(s)
        if f"r{n_order}" in sy or f"g{n_order}" in sy:
            skip = True                                # first-order tuning terms r_n M_0, g_n V_0 (window footing)
        if skip:
            continue
        has_d = any(a[0] == "D" for a in ops)
        if not has_d:
            red = rs.reduce_word(ops, pw)
            if red is None:
                continue
            verts, sops = red
            if len(verts) == 1:
                kind, d = verts[0]
                # single vertex <proj|X_d|ref>: only the pure zero-mode part with d = 0 survives
                if d != 0:
                    continue
                val = ch.chain([kind], [0], [], None)
            else:
                kinds = [v[0] for v in verts]
                derivs = [v[1] for v in verts]
                val = ch.chain(kinds, derivs, list(sops))
            v = coef * arr_coef * val
            tot += v
            parts[("raw",) + tuple(ops)] = parts.get(("raw",) + tuple(ops), 0) + v
            continue
        # window words
        if len(ops) == 1:
            k = ops[0][1]
            if with_dz and k == 2:
                v = coef * ch.dz_diag(h2[(0, 0)])
            elif with_dz and k == 3 and h3_00 is not None:
                v = coef * ch.dz_diag(h3_00)
            else:
                v = np.zeros(N + 1)
            tot += v
            parts[("DZdiag", k)] = v
            continue
        if len(ops) != 2:
            raise RuntimeError(f"unexpected window word {ops}")
        if any(a[0] == "P" for a in ops):
            continue                                   # (P - p) on |ref> or <proj| vanishes
        k = [a for a in ops if a[0] == "D"][0][1]
        assert k == 2
        first_is_d = ops[0][0] == "D"
        other = ops[1] if first_is_d else ops[0]
        assert other == ("V", 0)
        assert pw == (1,)
        # D^zm part
        if with_dz:
            hf = lambda to, fr: h2.get((to, fr))
            vz = ch.dz_first(hf, None) if first_is_d else ch.dz_last(hf)
            vz = coef * vz
            tot += vz
            parts[("DZ2", first_is_d)] = vz
        if with_dm:
            e4 = 0.25 * c1_2
            if first_is_d:
                kinds, minchi = ["M", "V"], [1, 0]
                v1 = ch.chain(kinds, [0, 0], [(1, 0)], ("ref", e4), minchi)
                v2 = ch.chain(kinds, [0, 0], [(1, 0)], ("slice", 0, e4), minchi)
            else:
                kinds, minchi = ["V", "M"], [0, 1]
                v1 = ch.chain(kinds, [0, 0], [(1, 0)], ("slice", 0, e4), minchi)
                v2 = ch.chain(kinds, [0, 0], [(1, 0)], ("end", e4), minchi)
            vm = coef * (v1 + v2)
            tot += vm
            parts[("DM2", first_is_d)] = vm
    return tot, parts


# ======================================================================================= inner functions
def inner_small(N, modes, with_h3=True):
    """h2 (normalized, ket-referenced, to <- from), c1_2, raw E_z^(2) for z = 0..3 (tuning), and the rule-Wc h^(3)_00(l; L)
    pieces (kappa-decomposed: (), r2, g2, C12)."""
    import windows5 as w5
    import assemble as asm
    import schemeW as sw
    import windowsW as ww
    zmax = 11
    h2, c1_2 = sw.inner_functions(N, modes, zmax, None)
    parts2 = w5.channel_energy_parts(asm.collect_words(2), N, modes, zmax, kmax=2)
    X2 = {p: parts2[(2, p)][()] for p in range(4)}
    r2 = -(X2[1] - X2[0]) / 2.0
    g2 = -(X2[3] - X2[0] + 6.0 * r2) / 3.0
    res = dict(h2=h2, c1_2=c1_2, r2=r2, g2=g2, X2=X2)
    if with_h3:
        import bloch
        zl = 1                                         # only z = 0 (h^(3)_00) and z = 1 are needed here
        parts3np = w5.channel_energy_parts(asm.collect_words(3), N, modes, zl, partners=False)
        v, s, w = ([("V", 0, 0), ("M", 0, 1)], [([(1, 0)], [])], [(0, ("DM", 2, 0))])
        vv = ww.eval_decorated(v, s, w, N, modes, lambda spec, p, zs: {(): 0.25 * c1_2}, ps=tuple(range(zl + 1)))
        dm2_ind = {z: (2 * float(G1) * vv[()][z] if () in vv else np.zeros(N + 1)) for z in range(zl + 1)}
        H3 = bloch.compute_H3(N, modes, dict(parts2=parts2, parts3=parts3np, h2=h2, c1_2=c1_2, dm2_ind=dm2_ind),
                              sw.COMPONENTS["Wb"], zk=(0,), zpmax=0)
        va = ww.eval_decorated([("V", 0, 0), ("M", 0, 1)], [([(1, 0)], [])], [], N, modes, None,
                               ps=tuple(range(zl + 1)))
        A_E = {z: (va[()][z] if () in va else np.zeros(N + 1)) for z in range(zl + 1)}
        # rule Wc: h^(3)(l; L) = h^(3)(l) + (1/2)(c1^(2)(L) - c1^(2)(l)) H3M(l),  H3M_00 = 2 g1 A_E[0]
        res.update(H3_00=H3[(0, 0)], H3M_00=2 * float(G1) * A_E[0], parts3np=parts3np, dm2_ind=dm2_ind, A_E=A_E)
    return res


def h3_00_at(inn, Mout):
    """rule-Wc h^(3)_00(l; L) as an l-array for the outer cutoff Mout (hol)."""
    d = inn["H3_00"]
    r2, g2, c12 = inn["r2"][Mout], inn["g2"][Mout], inn["c1_2"]
    arr = np.zeros_like(c12)
    for kap, a in d.items():
        f = 1.0
        for s in kap:
            f *= {"r2": r2, "g2": g2}[s]
        arr = arr + f * a
    arr = arr + 0.5 * (c12[Mout] - c12) * inn["H3M_00"]
    return arr


# ======================================================================================= driver
def tag_E3(ch, inn, r2, g2, c12, h2):
    """E^(3) of a tagged channel including the D^zm,(3) diagonal on the reference (rule-Wc h^(3)_00(l; L) per M)."""
    N = ch.N
    E3, _ = channel_energy(ch, 3, r2, g2, c12, h2, None)
    dz3 = np.zeros(N + 1)
    t = ch.cin
    for M in range(N + 1):
        if M - t < 0:
            continue
        arr = h3_00_at(inn, M)
        dz3[M] = arr[M] - arr[M - t]
    return E3 + dz3


def run(Lmax, cin=1, cout=1, verbose=True, also_single=False, nus=()):
    N = Lmax // 2
    t0 = time.time()
    modes = eg.Modes(N, 3)
    inn = inner_small(N, modes, with_h3=True)
    if verbose:
        print(f"[{time.time() - t0:7.1f}s] inner functions (N = {N})", flush=True)
    r2, g2, c12, h2 = inn["r2"], inn["g2"], inn["c1_2"], inn["h2"]
    out = {"L": 2 * np.arange(N + 1)}
    # --- vacuum and phi channels at the outer cutoff (u = 0): E^(2), E^(3)
    chans = {"p0": Channel(N, modes, ("plain", 0)), "p1": Channel(N, modes, ("plain", 1)),
             "tag": Channel(N, modes, ("tag",), cin, cout)}
    if also_single:
        chans["tag_in"] = Channel(N, modes, ("tag",), cin, 0)
        chans["tag_out"] = Channel(N, modes, ("tag",), 0, cout)
        chans["tag00"] = Channel(N, modes, ("tag",), 0, 0)
    E2, E3 = {}, {}
    for name, ch in chans.items():
        E2[name], _ = channel_energy(ch, 2, r2, g2, c12, h2, None)
        if ch.tag:
            # h^(3)_00(l; L) depends on the outer cutoff through r2, g2, c1_2(L): evaluate the DZ3 diagonal per M
            E3[name], parts = channel_energy(ch, 3, r2, g2, c12, h2, None)
            dz3 = np.zeros(N + 1)
            t = ch.cin
            for M in range(N + 1):
                if M - t < 0:
                    continue
                arr = h3_00_at(inn, M)
                dz3[M] = arr[M] - arr[M - t]
            E3[name] = E3[name] + dz3
            out[f"{name}_dz3"] = dz3
        else:
            E3[name], _ = channel_energy(ch, 3, r2, g2, c12, h2, None)
        if verbose:
            print(f"[{time.time() - t0:7.1f}s] channel {name} done", flush=True)
    # --- rule-Wc auxiliary channels at l = L - 2 (uniform offset u = 1, no tags, no D^zm on chi-free states)
    aux = {"a0": Channel(N, modes, ("plain", 0), u=1), "a1": Channel(N, modes, ("plain", 1), u=1)}
    for name, ch in aux.items():
        E3[name], _ = channel_energy(ch, 3, r2, g2, c12, h2, None, with_dz=False)
        E2[name], _ = channel_energy(ch, 2, r2, g2, c12, h2, None, with_dz=False)
    if verbose:
        print(f"[{time.time() - t0:7.1f}s] auxiliary channels done", flush=True)
    c1_3_Lm2 = E3["a1"] - E3["a0"]                      # c_1^(3)(L - 2; L), window footing
    c1_3_L = E3["p1"] - E3["p0"]                        # c_1^(3)(L), window footing
    c1tag3 = E3["tag"] - E3["p0"]                       # c1tag^(3)(L; nu) - 2 r_3
    c1tag2 = E2["tag"] - E2["p0"] + 2 * r2              # c1tag^(2)(L; nu) incl. 2 r_2 (as stored by the brute force)
    delta3 = 0.25 * (c1_3_Lm2 - c1tag3)
    delta2 = 0.25 * ((E2["a1"] - E2["a0"]) - (E2["tag"] - E2["p0"]))
    out.update(c1_3_Lm2=c1_3_Lm2, c1_3_L=c1_3_L, c1tag3=c1tag3, c1tag2=c1tag2, delta3=delta3, delta2=delta2,
               r2=r2, g2=g2, c1_2=c12)
    for name in E3:
        out[f"E3_{name}"] = E3[name]
        out[f"E2_{name}"] = E2[name]
    # --- larger symmetric charges nu = 2a (the exact chi_aa form of README Sec. 11.2 in the zero-mode proxy):
    #     delta_nu(L) = (1/(2 nu)) [c_1^(3)(L - nu; L) - c1tag^(3)(L; nu, nu)]  (per unit leg level)
    for nu in nus:
        a = nu // 2
        cht = Channel(N, modes, ("tag",), a, a)
        e3t = tag_E3(cht, inn, r2, g2, c12, h2)
        e3a1, _ = channel_energy(Channel(N, modes, ("plain", 1), u=a), 3, r2, g2, c12, h2, None, with_dz=False)
        e3a0, _ = channel_energy(Channel(N, modes, ("plain", 0), u=a), 3, r2, g2, c12, h2, None, with_dz=False)
        out[f"c1tag3_nu{nu}"] = e3t - E3["p0"]
        out[f"c1_3_Lm{nu}"] = e3a1 - e3a0
        out[f"delta3_nu{nu}"] = (out[f"c1_3_Lm{nu}"] - out[f"c1tag3_nu{nu}"]) / (2.0 * nu)
        if verbose:
            print(f"[{time.time() - t0:7.1f}s] charge nu = {nu} done", flush=True)
    if also_single:
        out["c1tag3_in"] = E3["tag_in"] - E3["p0"]
        out["c1tag3_out"] = E3["tag_out"] - E3["p0"]
        out["c1tag3_00"] = E3["tag00"] - E3["p0"]
    if verbose:
        print(f"[{time.time() - t0:7.1f}s] done", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, required=True)
    ap.add_argument("--nu", default="2,2")
    ap.add_argument("--single", action="store_true", help="also the single-leg charges and the zero-charge check")
    ap.add_argument("--nus", default="", help="extra symmetric charges nu (even), e.g. 4,6,8")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    nin, nout = (int(x) for x in a.nu.split(","))
    assert nin % 2 == 0 and nout % 2 == 0
    nus = tuple(int(x) for x in a.nus.split(",") if x)
    res = run(a.Lmax, nin // 2, nout // 2, also_single=a.single, nus=nus)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    np.savez(a.out, **res)
    L = res["L"]
    for Lv in (2, 4, 6, 8, 10, 12, 14, 16, 20, 50, 100, 200, 400, 600, 800, 1000, 1500, 2000, 3000, 4000):
        if Lv <= a.Lmax:
            i = Lv // 2
            print(f"L={Lv:5d} delta3={res['delta3'][i]:+.15f} c1tag3={res['c1tag3'][i]:+.12f} "
                  f"c1_3(L-2;L)={res['c1_3_Lm2'][i]:+.12f}" +
                  "".join(f" d_nu{nu}={res[f'delta3_nu{nu}'][i]:+.12f}" for nu in nus), flush=True)


if __name__ == "__main__":
    main()
