#!/usr/bin/env python3
"""
ce_solver.py -- exact (multi-modular) Rayleigh-Schroedinger solver for the 2D LRI Hamiltonian truncation with
general (operator-valued) window terms D, degenerate references and descendant channels.

Channel = (structure, cutoff l, particle cap, reference vector v at eps = 0).  The eps = 0 degenerate space D0 of a
channel is every allowed state with H0(0) = E0.  W_1 = -P/4 + g1 V_0 is block diagonal over the (level, P) blocks
of D0 (proved in README sec. 4); the reference block contains v, which must be a right eigenvector of W_1 with a
simple eigenvalue E1 (left eigenvector u, u.v = 1); every other block must have E1 - W_1|B invertible.  Order n
(intermediate normalisation u.psi_n = 0):
    rhs_n = sum_{k=1}^n W_k psi_{n-k} - sum_{k=1}^{n-1} E^(k) psi_{n-k}
    D0 part fixes psi_{n-1}^{D0} :  y = G P_c rhs_n|D0,  G = (E1 - W1|D0 + v u^T)^{-1}, P_c = 1 - v u^T
    E^(n) = u . rhs_n ;  psi_n = R' rhs_n  (R' = (E0 - H0)^{-1} off D0, 0 on D0).
For level-0 references (primaries |p>, auxiliary zero-mode channels |z>) this is exactly the algorithm of
../zeromode_exact (partners for z >= 5).

Active channels (primaries + scheme auxiliaries) are advanced as in zeromode_modular: tuning after their rhs is
known; then the scheme builds its order-n window tables; then D_n psi_0 is added.  Passive channels
(descendants) are finished last at every order (they need r_n, g_n and D_n on their own reference).
"""
from fractions import Fraction as Fr
import numpy as np

import ce_core as cc
from ce_core import ORD, G1, fr_mod, mat_inv_mod, frac_nullspace, frac_inv


# ============================================================================ prime-independent channel setup
class Setup:
    def __init__(self, S, l, cap, refvec, E0, label=""):
        """refvec: {state index: Fraction} (eps = 0 reference vector, orbit basis); E0: Fraction."""
        self.label, self.l, self.cap = label, l, cap
        n = S.nl[l]
        lev, P = S.level[:n], S.P[:n]
        twoE0 = 2 * E0
        assert twoE0.denominator == 1
        twoE0 = int(twoE0)
        d2 = 2 * lev + P - twoE0
        mask = P <= cap
        D0 = np.nonzero(mask & (d2 == 0))[0]
        blocks = {}
        for i in D0:
            blocks.setdefault((int(lev[i]), int(P[i])), []).append(int(i))
        supp = [i for i, x in refvec.items() if x != 0]
        keys = {(int(lev[i]), int(P[i])) for i in supp}
        assert len(keys) == 1, f"{label}: reference not inside one (level, P) block"
        rk = keys.pop()
        assert all(i in set(D0.tolist()) for i in supp), f"{label}: reference not degenerate with E0"
        self.refblock = blocks.pop(rk)
        self.otherblocks = [blocks[k] for k in sorted(blocks)]
        self.otherkeys = sorted(blocks)
        W = S.W1_block(self.refblock)
        m = len(self.refblock)
        v = [Fr(refvec.get(i, 0)) for i in self.refblock]
        Wv = [sum(W[a][b] * v[b] for b in range(m)) for a in range(m)]
        a0 = next(a for a in range(m) if v[a] != 0)
        E1 = Wv[a0] / v[a0]
        assert all(Wv[a] == E1 * v[a] for a in range(m)), f"{label}: reference is not a W_1 eigenvector"
        A = [[W[a][b] - (E1 if a == b else 0) for b in range(m)] for a in range(m)]
        rn = frac_nullspace(A)
        ln = frac_nullspace([[A[b][a] for b in range(m)] for a in range(m)])
        assert len(rn) == 1 and len(ln) == 1, f"{label}: E1 = {E1} not simple in the reference block"
        u = ln[0]
        s = sum(x * y for x, y in zip(u, v))
        assert s != 0, f"{label}: E1 defective"
        u = [x / s for x in u]
        self.E0, self.E1, self.v, self.u = E0, E1, v, u
        self.refvec = {i: x for i, x in zip(self.refblock, v) if x != 0}
        self.uvec = {i: x for i, x in zip(self.refblock, u) if x != 0}
        self.W1R = W
        self.GPref = None
        if m > 1:
            Gm = frac_inv([[(E1 if a == b else 0) - W[a][b] + v[a] * u[b] for b in range(m)] for a in range(m)])
            Pc = [[(1 if a == b else 0) - v[a] * u[b] for b in range(m)] for a in range(m)]
            self.GPref = [[sum(Gm[a][c] * Pc[c][b] for c in range(m)) for b in range(m)] for a in range(m)]
            ev = sorted({x for x in _eigs_rational(W)}, key=float)
            self.refblock_rational_eigs = [str(x) for x in ev]
        self.dims = {"ref": m, "other": [len(b) for b in self.otherblocks]}


def _eigs_rational(W):
    """rational eigenvalues of a small Fraction matrix (candidates p/q tested by exact nullspace): diagnostics."""
    m = len(W)
    out = []
    # characteristic polynomial via Faddeev-LeVerrier (exact)
    import itertools
    c = [Fr(1)]
    Mk = [[Fr(0)] * m for _ in range(m)]
    I = [[Fr(int(a == b)) for b in range(m)] for a in range(m)]
    coeffs = [Fr(1)]
    for k in range(1, m + 1):
        Mk = [[sum(W[a][t] * Mk[t][b] for t in range(m)) + (coeffs[-1] if a == b else 0) for b in range(m)]
              for a in range(m)]
        AM = [[sum(W[a][t] * Mk[t][b] for t in range(m)) for b in range(m)] for a in range(m)]
        ck = -sum(AM[a][a] for a in range(m)) / k
        coeffs.append(ck)
    # roots: try rational candidates from the monic integer-scaled polynomial
    from math import lcm
    den = 1
    for x in coeffs:
        den = lcm(den, x.denominator)
    ints = [int(x * den) for x in coeffs]
    a0, an = ints[-1], ints[0]

    def divisors(x):
        x = abs(x)
        if x == 0:
            return [0]
        ds = set()
        i = 1
        while i * i <= x:
            if x % i == 0:
                ds.add(i); ds.add(x // i)
            i += 1
        return sorted(ds)
    cands = set()
    if a0 == 0:
        cands.add(Fr(0))
    for p_ in divisors(a0):
        for q_ in divisors(an):
            if q_:
                cands.add(Fr(p_, q_)); cands.add(Fr(-p_, q_))
    for x in cands:
        val = sum(cf * x ** (m - i) for i, cf in enumerate(coeffs))
        if val == 0:
            out.append(x)
    return out


# ============================================================================ channel (mod q)
class Chan:
    def __init__(self, S, ops, setup, kmax, q, name, passive=False, aux_z=None):
        self.S, self.ops, self.setup, self.q, self.name = S, ops, setup, q, name
        self.l, self.cap, self.kmax, self.passive, self.aux_z = setup.l, setup.cap, kmax, passive, aux_z
        l = self.l
        n = S.nl[l]
        self.n = n
        lev, P = S.level[:n], S.P[:n]
        self.lev = lev
        self.mask = P <= self.cap
        d2 = 2 * lev + P - int(2 * setup.E0)
        assert np.all(d2[self.mask] % 2 == 0)
        d = d2 // 2
        nzd = self.mask & (d != 0)
        inv = np.zeros(n, dtype=np.int64)
        for dv in np.unique(d[nzd]):
            inv[nzd & (d == dv)] = pow(int(-dv) % q, -1, q)
        self.Rinv = inv
        self.negP4 = (-(P % q) * pow(4, -1, q)) % q
        v = np.zeros(n, dtype=np.int64)
        for i, x in setup.refvec.items():
            v[i] = fr_mod(x, q)
        self.v = v
        self.uidx = np.array(sorted(setup.uvec), dtype=np.int64)
        self.uval = np.array([fr_mod(setup.uvec[i], q) for i in self.uidx], dtype=np.int64)
        self.refidx = np.array(setup.refblock, dtype=np.int64)
        self.blocks = []        # (idx array, GP matrix mod q)
        if setup.GPref is not None:
            self.blocks.append((self.refidx, np.array([[fr_mod(x, q) for x in row] for row in setup.GPref],
                                                      dtype=np.int64)))
        E1q = fr_mod(setup.E1, q)
        self.E1q = E1q
        for b in setup.otherblocks:
            bi = np.array(b, dtype=np.int64)
            Vb = ops.get("V", 0, l)[bi][:, bi].toarray() % q
            W = (fr_mod(G1, q) * Vb) % q
            W[np.arange(len(b)), np.arange(len(b))] = (W[np.arange(len(b)), np.arange(len(b))] + self.negP4[bi]) % q
            A = (-W) % q
            A[np.arange(len(b)), np.arange(len(b))] = (A[np.arange(len(b)), np.arange(len(b))] + E1q) % q
            G = mat_inv_mod(A, q)
            assert G is not None, f"{name}: E1 - W1|B singular mod {q} (block {len(b)})"
            self.blocks.append((bi, G))
        self.has_D0 = len(self.blocks) > 0
        self.M0v = self.mv("M", 0, v)
        self.V0v = self.mv("V", 0, v)
        self.psi = [v]
        self.E = [fr_mod(setup.E0, q)]
        self.zidx = {}           # pure zero-mode states |z'> inside this channel
        for zp in range(S.parity, S.Pmax + 1, 2):
            if zp <= self.cap:
                self.zidx[zp] = S.ref_index(zp)

    def mv(self, name, j, u):
        y = (self.ops.get(name, j, self.l) @ u)[: self.n] % self.q
        y[~self.mask] = 0
        return y

    def W1(self, u, r1, g1):
        q = self.q
        out = self.negP4 * u % q
        if r1:
            out = (out + r1 * self.mv("M", 0, u)) % q
        if g1:
            out = (out + g1 * self.mv("V", 0, u)) % q
        return out

    def proj(self, rhs):
        return int(np.dot(self.uval, rhs[self.uidx] % self.q) % self.q) if len(self.uidx) else 0

    def rhs0(self, n, r, g, scheme):
        """sum_k W_k psi_{n-k} - sum_{k<n} E^(k) psi_{n-k} without r_n M_0 psi_0, g_n V_0 psi_0, D_n psi_0."""
        q = self.q
        out = np.zeros(self.n, dtype=np.int64)
        for j in range(n):
            for name, c in (("M", r), ("V", g)):
                u = None
                for k in range(j + 1, n + 1):
                    if k == n and j == 0:
                        continue
                    ck = c[k - j]
                    if ck:
                        t = ck * self.psi[n - k] % q
                        u = t if u is None else (u + t) % q
                if u is not None:
                    out = (out + self.mv(name, j, u)) % q
        out = (out + self.negP4 * self.psi[n - 1]) % q
        for k in range(2, n):
            Dx = scheme.D_apply(k, self, self.psi[n - k])
            if Dx is not None:
                out = (out + Dx) % q
        for k in range(1, n):
            out = (out - self.E[k] * self.psi[n - k]) % q
        return out

    def bsolve(self, rhs, n, r, g):
        q = self.q
        if not self.has_D0 or n == 1:
            if n == 1 and self.has_D0:
                self.check_D0(rhs)
            return rhs
        y = np.zeros(self.n, dtype=np.int64)
        for bi, G in self.blocks:
            tb = rhs[bi] % q
            # exact int64: entries < 2^23, length < 2^17
            y[bi] = (G @ tb) % q
        assert not (self.psi[n - 1][np.concatenate([b for b, _ in self.blocks])] % q).any() or True
        self.psi[n - 1] = (self.psi[n - 1] + y) % q
        before = self.proj(rhs)
        rhs = (rhs + self.W1(y, r[1], g[1]) - self.E1q * y) % q
        self.check_D0(rhs)
        assert self.proj(rhs) == before, f"{self.name}: D0 solution changed u.rhs"
        return rhs

    def check_D0(self, rhs):
        """after the D0 solve: rhs restricted to D0 must be parallel to v (P_c rhs = 0)."""
        q = self.q
        c = self.proj(rhs)
        for bi, _ in self.blocks:
            res = (rhs[bi] - c * self.v[bi]) % q
            assert not res.any(), f"{self.name}: D0 projection of the order equation not satisfied"
        if not self.blocks:
            pass

    def add_rg(self, rhs, rn, gn):
        q = self.q
        if rn:
            rhs = (rhs + rn * self.M0v) % q
        if gn:
            rhs = (rhs + gn * self.V0v) % q
        return rhs

    def finish(self, rhs):
        En = self.proj(rhs)
        self.E.append(En)
        self.psi.append(rhs * self.Rinv % self.q)
        return En


# ============================================================================ schemes
class Raw:
    name = "raw"
    tdeg = 0

    def __init__(self, **kw):
        pass

    def aux_specs(self, L, capextra):
        return []

    def D_apply(self, k, ch, x):
        return None

    def update(self, n, chans, rh, L, rh_pre=None):
        pass

    def tables(self):
        return {}


class DiagWindow:
    """consistent (D_l(N) = E_0(l) - E_0(l - N)) or zeromode (D_l(z, N) = E_z(l) - E_z(l - N)); self-consistent."""
    tdeg = 0

    def __init__(self, mode, tiers, q, L, zrows, garbage_seed=None):
        self.name = mode
        self.mode, self.tiers, self.q, self.L = mode, tiers, q, L
        nl = L // 2 + 1
        self.known = [np.zeros((zrows, nl), dtype=bool) for _ in range(ORD + 1)]
        if garbage_seed is None:
            self.T = [np.zeros((zrows, nl), dtype=np.int64) for _ in range(ORD + 1)]
        else:
            rng = np.random.default_rng(garbage_seed + q)
            self.T = [rng.integers(0, q, size=(zrows, nl), dtype=np.int64) for _ in range(ORD + 1)]
        self._cache = {}

    def aux_specs(self, L, capextra):
        out = []
        for z, km in self.tiers.items():
            if isinstance(km, tuple):
                km, cap = km
            else:
                cap = z + 4 * (km // 2)
            for l in range(0, L + 1, 2):
                if l == L and z <= 3:
                    continue
                out.append((z, l, km, cap + capextra))
        return out

    def _sel(self, ch):
        key = id(ch)
        c = self._cache.get(key)
        if c is None:
            S = ch.S
            n = ch.n
            sel = np.nonzero(ch.mask & (ch.lev >= 2))[0]
            z = S.Z[:n][sel] if self.mode == "zeromode" else np.zeros(len(sel), dtype=np.int64)
            l0 = np.full(len(sel), ch.l // 2)
            l1 = (ch.l - ch.lev[sel]) // 2
            c = (sel, z, l0, l1)
            self._cache[key] = c
        return c

    def D_apply(self, k, ch, x):
        if k < 2:
            return None
        sel, z, l0, l1 = self._sel(ch)
        if not len(sel):
            return None
        T = self.T[k]
        coef = (T[z, l0] - T[z, l1]) % self.q
        out = np.zeros(ch.n, dtype=np.int64)
        out[sel] = coef * x[sel] % self.q
        return out

    def update(self, n, chans, rh, L, rh_pre=None):
        for c in chans:
            if c.aux_z is not None and c.kmax >= n:
                self.T[n][c.aux_z, c.l // 2] = c.E[n]
                self.known[n][c.aux_z, c.l // 2] = True

    def tables(self):
        return {"Ez": self.T, "known": self.known}


class Complete2:
    """README (residual_log) eps^2 complete window:
         D = eps^2 [ D_zm + t kappa0 {N, M'_0} ],  kappa0 = -g1^2/3 = -1/27,  t = 1/pi (formal parameter),
         D_zm |z, chi> = sum_z' [h_{z'z}(l) - h_{z'z}(l - N_chi)] |z', chi>  (N_chi >= 2),
         h_{z'z}(l) = <z'| (W_1 R_z W_1 - E^(1) R_z W_1) |z>  at cutoff l (the order-2 rhs of channel (z, l), read
         at the pure zero-mode state |z'>; level-0 parts cancel in the difference).  No D at orders >= 3."""
    name = "complete2"
    tdeg = 1

    def __init__(self, q, L, zc, tval, kappa0=Fr(-1, 27), zprime_extra=8, garbage_seed=None, chi=True, zm=True,
                 hmode="naive"):
        """hmode = 'naive': h from the order-2 rhs BEFORE the degenerate-partner solve (README formula, terms with
        <k|V|z> = 0 and E_k = E_z dropped; = ../residual_log/brute_full.py); 'bloch': after it (the zero-mode
        components of the true order-2 eigenvector equation, includes W_1 psi_1^B for z >= 5)."""
        self.hmode = hmode
        self.q, self.L, self.zc, self.tval = q, L, zc, tval
        self.kq = fr_mod(kappa0, q) * tval % q
        self.zpmax = zc + zprime_extra
        nl = L // 2 + 1
        self.H = np.zeros((self.zpmax + 1, zc + 1, nl), dtype=np.int64)
        self.known = np.zeros((self.zpmax + 1, zc + 1, nl), dtype=bool)
        self.Ez = {}
        self.chi, self.zm = chi, zm
        self._cache = {}

    def aux_specs(self, L, capextra):
        out = []
        for z in range(self.zc + 1):
            for l in range(0, L + 1, 2):
                if l == L and z <= 3:
                    continue
                out.append((z, l, 2, z + 8 + capextra))
        return out

    def _sel(self, ch):
        c = self._cache.get(id(ch))
        if c is None:
            S = ch.S
            sel = np.nonzero(ch.mask & (ch.lev >= 2) & (S.Z[:ch.n] <= self.zc))[0]
            z = S.Z[:ch.n][sel]
            l0 = ch.l // 2
            l1 = (ch.l - ch.lev[sel]) // 2
            shifts = []
            for dz in cc.ZSHIFTS:
                tg = S.zshift[dz][sel]
                ok = (tg >= 0) & (z + dz >= 0) & (z + dz <= self.zpmax)
                ok &= (tg < ch.n)
                tgc = np.where(ok, tg, 0)
                ok &= ch.mask[tgc]
                if ok.any():
                    shifts.append((dz, np.nonzero(ok)[0], tg[ok]))
            levq = ch.lev % self.q
            c = (sel, z, l0, l1, shifts, levq)
            self._cache[id(ch)] = c
        return c

    def D_apply(self, k, ch, x):
        if k != 2:
            return None
        q = self.q
        out = np.zeros(ch.n, dtype=np.int64)
        sel, z, l0, l1, shifts, levq = self._sel(ch)
        if self.zm and len(sel):
            xs = x[sel]
            for dz, pos, tg in shifts:
                zz = z[pos]
                coef = (self.H[zz + dz, zz, l0] - self.H[zz + dz, zz, l1[pos]]) % q
                out[tg] = (out[tg] + coef * xs[pos]) % q
        if self.chi and self.kq:
            y = (levq * ch.mv("Mp", 0, x) + ch.mv("Mp", 0, levq * x % q)) % q
            out = (out + self.kq * y) % q
        return out

    def update(self, n, chans, rh, L, rh_pre=None):
        for c in chans:
            if c.aux_z is None:
                continue
            if c.kmax >= n:
                self.Ez[(c.aux_z, c.l, n)] = c.E[n]
            if n != 2 or c.aux_z > self.zc:
                continue
            r = rh[id(c)] if self.hmode == "bloch" else rh_pre[id(c)]
            for zp, i in c.zidx.items():
                if zp <= self.zpmax:
                    self.H[zp, c.aux_z, c.l // 2] = int(r[i]) if zp != c.aux_z else c.E[2]
                    self.known[zp, c.aux_z, c.l // 2] = True

    def tables(self):
        return {"H2": self.H, "known": self.known}


class SchemeW:
    """WINDOW_SPEC.md scheme W (D = D^zm + D^M) or W+V (+ D^V), all orders, self-consistent at every cutoff l.
        h(l) = X Lambda X^-1 (P0 components of the branch eigenvectors, monomial frame), by the recursion
        H^(n) = X^(n) E0 - E0 X^(n) + sum_{j=1}^n X^(n-j) diag E^(j) - sum_{m=1}^{n-1} H^(m) X^(n-m);
        D^zm |z, chi> = sum_z' [h(l) - h(l - N)]_{z'z} |z', chi>  (N >= 2);
        D^M = (1/4) sum_j {Delta c_1^(j)(l, N), M'_{k-j}},  D^V = (1/2) sum_j {Delta c_2^(j)(l, N), V'_{k-j}},
        c_1 = E_1 - E_0, c_2 = E_2 - 2 E_1 + E_0 (channels z = 0, 1, 2 at every l).
    book: bookkeeping dict (channels {z: {kmax, cap}}, claimed h entries, c1/c2 orders, X/E claims).
    kD: largest window order kept (kD = 2: the eps^2-only reduction of WINDOW_SPEC sec. 5.2).
    h2naive: at order 2 use the P0 components of the rhs BEFORE the degenerate-partner solve (= brute_W.py)."""
    tdeg = 0

    def __init__(self, q, L, book, withV=False, kD=ORD, h2naive=False, garbage_seed=None, name="W",
                 zm=True, M=True, kM=ORD, nopartner=True):
        self.name, self.q, self.L, self.book, self.withV, self.kD = name, q, L, book, withV, kD
        # WINDOW_SPEC 2.10 as changed 2026-10-09: the window objects (X, h, E_z of the auxiliary channels) are
        # computed with the degenerate partners removed from the resolvent (no B-equation).  nopartner=False is
        # the earlier literal reading (branch eigenvectors, B-equation): variants WB, W+VB.
        self.aux_bsolve = not nopartner
        self.kM = kM          # diagnostic variant: D^M,(k) and D^V,(k) only for k <= kM
        self.h2naive, self.zm_on, self.M_on = h2naive, zm, M
        ch = {int(z): (d["kmax"], d["cap"]) for z, d in book["channels"].items()}
        self.chans = ch
        Zall = max(max(c for _, c in ch.values()), max(ch)) + 2
        self.Zall = Zall
        nl = L // 2 + 1
        self.nl = nl
        self.E = np.zeros((ORD + 1, Zall + 1, nl), dtype=np.int64)
        self.X = np.zeros((ORD + 1, Zall + 1, Zall + 1, nl), dtype=np.int64)
        for z in range(Zall + 1):
            self.X[0, z, z, :] = 1
        self.H = np.zeros((ORD + 1, Zall + 1, Zall + 1, nl), dtype=np.int64)
        self.c1 = np.zeros((ORD + 1, nl), dtype=np.int64)
        self.c2 = np.zeros((ORD + 1, nl), dtype=np.int64)
        self.E0 = np.array([z * pow(2, -1, q) % q for z in range(Zall + 1)], dtype=np.int64)
        self.rng = None if garbage_seed is None else np.random.default_rng(garbage_seed + q)
        if self.rng is not None:
            self.hclaim = np.zeros((ORD + 1, Zall + 1, Zall + 1), dtype=bool)
            for k, zp, z in book["h"]:
                self.hclaim[k, zp, z] = True
            self.xclaim = np.zeros((ORD + 1, Zall + 1, Zall + 1), dtype=bool)
            for key, zps in book["X"].items():
                z, j = map(int, key.split(","))
                for zp in zps:
                    self.xclaim[j, zp, z] = True
            self.eclaim = np.zeros((ORD + 1, Zall + 1), dtype=bool)
            for z, j in book["E"].items():
                self.eclaim[: j + 1, int(z)] = True
        zz = np.arange(Zall + 1)
        dist = np.abs(zz[:, None] - zz[None, :])
        self._zcache = {}
        # band: h^(k)_{z'z} and X^(k)_{z'z} vanish identically for |z' - z| > 4k (each order moves P by <= 4)
        self.band = np.array([(dist <= 4 * k) & (dist % 2 == 0) for k in range(ORD + 1)])
        self._cache = {}

    def aux_specs(self, L, capextra):
        out = []
        for z, (km, cap) in sorted(self.chans.items()):
            for l in range(0, L + 1, 2):
                if l == L and z <= 3:
                    continue
                out.append((z, l, km, cap + capextra))
        return out

    def update(self, n, chans, rh, L, rh_pre=None):
        q = self.q
        naive = self.h2naive and n == 2
        Xnaive = np.zeros_like(self.X[n]) if naive else None
        for c in chans:
            z = c.aux_z
            if z is None or c.kmax < n or z > self.Zall:
                continue
            li = c.l // 2
            self.E[n, z, li] = c.E[n]
            r = rh[id(c)]
            rp = rh_pre[id(c)] if naive else None
            for zp, i in c.zidx.items():
                if zp != z and zp <= self.Zall:
                    self.X[n, zp, z, li] = int(r[i]) * int(c.Rinv[i]) % q
                    if naive:
                        Xnaive[zp, z, li] = int(rp[i]) * int(c.Rinv[i]) % q
        if self.rng is not None:
            # garbage outside the claimed E and X entries (every l)
            bad = ~self.eclaim[n]
            self.E[n][bad, :] = self.rng.integers(0, q, size=(int(bad.sum()), self.nl))
            badx = ~self.xclaim[n] & self.band[n]
            np.fill_diagonal(badx, False)
            self.X[n][badx, :] = self.rng.integers(0, q, size=(int(badx.sum()), self.nl))
        self.c1[n] = (self.E[n, 1] - self.E[n, 0]) % q
        self.c2[n] = (self.E[n, 2] - 2 * self.E[n, 1] + self.E[n, 0]) % q
        if self.rng is not None:
            if n not in self.book["c1"]:
                self.c1[n] = self.rng.integers(0, q, size=self.nl)
            if n not in self.book["c2"]:
                self.c2[n] = self.rng.integers(0, q, size=self.nl)
        E0 = self.E0
        for li in range(self.nl):
            # alternative reading (h2naive): h^(2) from the P0 components of the order-2 rhs before the partner
            # solve (explicit second-order sum, partner terms dropped); the X table itself stays the true one
            Xn = Xnaive[:, :, li] if naive else self.X[n, :, :, li]
            Hn = (Xn * E0[None, :] - E0[:, None] * Xn) % q
            for j in range(1, n + 1):
                Hn = (Hn + self.X[n - j, :, :, li] * self.E[j, :, li][None, :]) % q
            for m in range(1, n):
                Hn = (Hn - (self.H[m, :, :, li] @ self.X[n - m, :, :, li]) % q) % q
            self.H[n, :, :, li] = Hn
        if self.rng is not None:
            badh = ~self.hclaim[n] & self.band[n]
            self.H[n][badh, :] = self.rng.integers(0, q, size=(int(badh.sum()), self.nl))

    def _sel(self, ch):
        """per channel, once: compact list of the D^zm entries (source state, target state, z, z', l - N) sorted by
        target (int32/int16 arrays; the band |dz| <= 4k is applied at use time)."""
        c = self._cache.get(id(ch))
        if c is None:
            S = ch.S
            sel = np.nonzero(ch.mask & (ch.lev >= 2))[0]
            z = S.Z[:ch.n][sel]
            l0 = ch.l // 2
            l1 = (ch.l - ch.lev[sel]) // 2
            P_, T_, D_ = [], [], []
            for dz in cc.ZSHIFTS:
                tg = S.zshift[dz][sel]
                ok = (tg >= 0) & (z + dz >= 0) & (z + dz <= self.Zall) & (z <= self.Zall) & (tg < ch.n)
                tgc = np.where(ok, tg, 0)
                ok &= ch.mask[tgc]
                if ok.any():
                    P_.append(np.nonzero(ok)[0]); T_.append(tg[ok]); D_.append(np.full(int(ok.sum()), dz, np.int8))
            if P_:
                pos = np.concatenate(P_); tg = np.concatenate(T_); dzs = np.concatenate(D_)
                order = np.argsort(tg, kind="stable")
                pos, tg, dzs = pos[order], tg[order], dzs[order]
                zz = z[pos]
                zl = (sel[pos].astype(np.int32), tg.astype(np.int32), dzs, zz.astype(np.int16),
                      (zz + dzs).astype(np.int16), l1[pos].astype(np.int16))
            else:
                zl = None
            l1all = np.where(ch.lev >= 2, (ch.l - ch.lev) // 2, l0).astype(np.int32)   # Delta c(l, 0) = 0
            c = (l0, zl, l1all)
            self._cache[id(ch)] = c
        return c

    def D_apply(self, k, ch, x):
        if k < 2 or k > self.kD:
            return None
        q = self.q
        out = np.zeros(ch.n, dtype=np.int64)
        l0, zl, l1all = self._sel(ch)
        if self.zm_on and zl is not None:
            src, tg, dzs, zz, zt, l1p = zl
            if 4 * k < 24:
                m = np.abs(dzs) <= 4 * k
                src, tg, zz, zt, l1p = src[m], tg[m], zz[m], zt[m], l1p[m]
            if len(tg):
                starts = np.flatnonzero(np.r_[True, tg[1:] != tg[:-1]])
                Hk = self.H[k]
                coef = (Hk[zt, zz, l0] - Hk[zt, zz, l1p]) % q
                vals = coef * x[src] % q          # < 2^46 each; segment sums of <= 25 terms
                out[tg[starts]] = np.add.reduceat(vals, starts) % q
        terms = []
        if self.M_on and k <= self.kM:
            terms.append(("Mp", self.c1, pow(4, -1, q)))
        if self.withV and k <= self.kM:
            terms.append(("Vp", self.c2, pow(2, -1, q)))
        for opn, cser, pref in terms:
            acc = np.zeros(ch.n, dtype=np.int64)
            for j in range(2, k + 1):
                f = (cser[j, l0] - cser[j, l1all]) % q          # Delta c^(j)(l, N_s) per state
                if not f.any():
                    continue
                acc = (acc + f * ch.mv(opn, k - j, x) + ch.mv(opn, k - j, f * x % q)) % q
            out = (out + pref * acc) % q
        return out

    def tables(self):
        return {"H": self.H, "X": self.X, "E": self.E, "c1": self.c1, "c2": self.c2}


# ============================================================================ the RS driver (one prime, one scheme)
def run_mod(structs, opsd, setups, L, q, scheme, desc_keys, Kprim=16, capextra=0):
    """setups: dict key -> Setup (primaries ('p', p), auxiliaries ('z', z, l), descendants ('d', name)).
    Returns residues of C, r, g, E_p, auxiliary energies and descendant energies."""
    inv2, inv3 = pow(2, -1, q), pow(3, -1, q)
    chans = {}
    for p in range(4):
        chans[("p", p)] = Chan(structs[p % 2], opsd[p % 2], setups[("p", p)], ORD, q, f"p{p}", aux_z=p)
    for (z, l, km, cap) in scheme.aux_specs(L, capextra):
        key = ("z", z, l, cap)
        chans[key] = Chan(structs[z % 2], opsd[z % 2], setups[key], km, q, f"z{z}l{l}", aux_z=z)
    for dk in desc_keys:
        st = setups[dk]
        par = int(st.E0 * 2) % 2
        chans[dk] = Chan(structs[par], opsd[par], st, ORD, q, f"{dk}", passive=True)
    active = [c for c in chans.values() if not c.passive]
    passive = [c for c in chans.values() if c.passive]
    r = [0] * (ORD + 1)
    g = [0] * (ORD + 1)
    xs = [inv2, (-pow(4, -1, q)) % q] + [0] * (ORD - 1)
    C = [1]
    for n in range(1, ORD + 1):
        rh, rh_pre = {}, {}
        for c in active:
            if c.kmax >= n:
                r0 = c.rhs0(n, r, g, scheme)
                rh_pre[id(c)] = r0.copy()
                if c.aux_z is not None and c.has_D0 and not getattr(scheme, "aux_bsolve", True):
                    rh[id(c)] = r0          # partners projected out of the auxiliary channel (no B-equation)
                else:
                    rh[id(c)] = c.bsolve(r0, n, r, g)
        X = {p: chans[("p", p)].proj(rh[id(chans[("p", p)])]) for p in range(4)}
        rn = (xs[n] - X[1] + X[0]) * inv2 % q
        gn = (-xs[n] - X[3] + X[0] - 6 * rn) * inv3 % q
        r[n], g[n] = rn, gn
        for c in active:
            if c.kmax >= n:
                rh[id(c)] = c.add_rg(rh[id(c)], rn, gn)
                rh_pre[id(c)] = c.add_rg(rh_pre[id(c)], rn, gn)
                c.E.append(c.proj(rh[id(c)]))
        scheme.update(n, active, rh, L, rh_pre)
        for c in active:
            if c.kmax >= n:
                Dx = scheme.D_apply(n, c, c.psi[0])
                rr = rh[id(c)]
                if Dx is not None:
                    assert c.proj(Dx) == 0, f"{c.name}: D_n psi_0 has a reference component"
                    for bi, _ in c.blocks:
                        assert not Dx[bi].any(), f"{c.name}: D_n psi_0 has a D0 component"
                    for zp, i in c.zidx.items():
                        assert Dx[i] == 0, f"{c.name}: D_n psi_0 has a pure zero-mode component"
                    rr = (rr + Dx) % q
                c.psi.append(rr * c.Rinv % q)
        for c in passive:
            rr = c.add_rg(c.rhs0(n, r, g, scheme), rn, gn)
            Dx = scheme.D_apply(n, c, c.psi[0])
            if Dx is not None:
                rr = (rr + Dx) % q
            rr = c.bsolve(rr, n, r, g)
            c.finish(rr)
        E = {p: chans[("p", p)].E[n] for p in range(4)}
        assert (E[1] - E[0] - xs[n]) % q == 0 and (E[3] - E[0] + xs[n]) % q == 0
        C.append((E[2] - E[0]) % q)
    for c in passive:
        assert c.E[1] == c.E1q, f"{c.name}: E^(1) != first-order eigenvalue"
    out = {"C": C, "r": r, "g": g, "E": [chans[("p", p)].E for p in range(4)],
           "Eaux": {f"{k[1]},{k[2]}": c.E for k, c in chans.items() if k[0] == "z"},
           "Edesc": {k[1]: c.E for k, c in chans.items() if k[0] == "d"}}
    return out, scheme
