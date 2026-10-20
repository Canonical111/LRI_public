#!/usr/bin/env python3
"""
Exact (multi-modular) Rayleigh-Schroedinger solver for the ZEROMODE window scheme of the 2D LRI Hamiltonian
truncation (see README.md), with a 'consistent' mode for regression against ../rs_exact.

Built on ../rs_exact/fast_modular.py (copied as fast_modular_orig.py; the structure / vertex code below is
that code with two changes: states are sorted by (level, P, occupation) so that the cutoff-l space is a
prefix, and the zero-mode number of each state is recorded).  New here:
  * channels (z, l): the branch through |z> = (A_00^dag)^z/sqrt(z!)|0> of P_l(H0 + rM + gV)P_l + D_l, with
    D_l(z_s, N_s) = E_{z_s}(l) - E_{z_s}(l - N_s) on every state s of level N_s >= 2 (z_s = its number of
    (0,0) quanta), D = 0 on level 0;
  * degenerate RS for z >= 5 (partners B = {level N >= 2, P = z - 2N}; lifted at first order, degeneracy.py):
    the order-(n) equation projected on B fixes psi_{n-1}^B = G_B [ ... ], G_B = (E^(1) - W_1^BB)^{-1};
  * every channel advances in lock-step order by order; D^(k) for (z_s, k) outside the computed table is
    zero by default, or deliberately random ('--garbage') to demonstrate that it never enters.

All arithmetic modulo many primes q < 2^23, then CRT + rational reconstruction checked on held-out primes.
"""
from fractions import Fraction as Fr
from math import comb, factorial, isqrt, gcd
import argparse, json, os, sys, time
import numpy as np
import scipy.sparse as sps

ORD = 8


# ============================================================================ exact structure
def falling_poly(a):
    """(x)_a/a! with x = 1/2 - eps/4 as exact eps-coefficients 0..ORD."""
    c = [Fr(0)] * (ORD + 1)
    c[0] = Fr(1)
    for i in range(a):
        a0, a1 = Fr(2 * i + 1, 2 * (i + 1)), Fr(-1, 4 * (i + 1))
        new = [Fr(0)] * (ORD + 1)
        for d in range(ORD + 1):
            new[d] += c[d] * a0
            if d < ORD:
                new[d + 1] += c[d] * a1
        c = new
    return c


def pmul(p, q):
    out = [Fr(0)] * (ORD + 1)
    for i in range(ORD + 1):
        if p[i]:
            for j in range(ORD + 1 - i):
                if q[j]:
                    out[i + j] += p[i] * q[j]
    return out


class Structure:
    """Prime-independent data for one field-parity sector at cutoff L with absolute particle cap Pmax.
    States (reflection-even orbits) sorted by (level, P, occupation): the cutoff-l space is the prefix
    of length nl[l]."""

    def __init__(self, L, parity, Pmax, verbose=True):
        t0 = time.time()
        self.L, self.parity, self.Pmax = L, parity, Pmax
        modes = []
        for lev in range(L + 1):
            for a in range(lev + 1):
                modes.append((a, lev - a))
        self.modes = modes
        assert modes[0] == (0, 0)
        mid = {m: i for i, m in enumerate(modes)}
        self.refl = [mid[(b, a)] for (a, b) in modes]
        fp = [falling_poly(a) for a in range(L + 1)]
        self.wpoly = [pmul(fp[a], fp[b]) for (a, b) in modes]
        lev = [a + b for a, b in modes]
        J = [a - b for a, b in modes]
        self._lev, self._J = lev, J

        allst = []
        nz = list(range(1, len(modes)))
        stack = [(0, 0, 0, 0, ())]
        while stack:
            pos, L_, J_, P_, occ = stack.pop()
            if pos == len(nz):
                if J_ == 0:
                    for n0 in range(0, Pmax - P_ + 1):
                        if (P_ + n0) % 2 == parity:
                            st = ((0, n0),) + occ if n0 else occ
                            allst.append(tuple(sorted(st)))
                continue
            m = nz[pos]
            if L_ + lev[m] > L:
                stack.append((len(nz), L_, J_, P_, occ))
                continue
            k = 0
            while L_ + k * lev[m] <= L and P_ + k <= Pmax:
                stack.append((pos + 1, L_ + k * lev[m], J_ + k * J[m], P_ + k,
                              occ + ((m, k),) if k else occ))
                k += 1
        allst = sorted(set(allst))
        self.n_full = len(allst)
        R = self.refl

        def reflect(st):
            return tuple(sorted((R[m], c) for m, c in st))

        reps = []
        for st in allst:
            rs = reflect(st)
            if st <= rs:
                reps.append(st)

        def levof(s):
            return sum(lev[m] * c for m, c in s)

        def Pof(s):
            return sum(c for m, c in s)

        reps.sort(key=lambda s: (levof(s), Pof(s), s))
        self.states = reps
        self.size = np.array([1 if reflect(s) == s else 2 for s in reps])
        self.index = {s: i for i, s in enumerate(reps)}
        self.level = np.array([levof(s) for s in reps], dtype=np.int64)
        self.P = np.array([Pof(s) for s in reps], dtype=np.int64)
        self.Z = np.array([dict(s).get(0, 0) for s in reps], dtype=np.int64)
        self.nl = {l: int(np.searchsorted(self.level, l, side="right")) for l in range(0, L + 1, 2)}
        self.reflect = reflect
        if verbose:
            print(f"# L={L} par={parity} Pmax={Pmax}: {self.n_full} J=0 states, {len(reps)} reflection-even "
                  f"orbits  ({time.time()-t0:.1f}s)", flush=True)

        self.Smul = {}
        for k in range(5):
            d = {}

            def rec(start, k_left, lv, j, acc):
                if k_left == 0:
                    ms = {}
                    for m in acc:
                        ms[m] = ms.get(m, 0) + 1
                    pf = 1
                    for c in ms.values():
                        pf *= factorial(c)
                    d.setdefault(j, []).append((lv, tuple(sorted(ms.items())), pf))
                    return
                for m in range(start, len(modes)):
                    if lv + lev[m] > L:
                        break
                    acc.append(m)
                    rec(m, k_left - 1, lv + lev[m], j + J[m], acc)
                    acc.pop()

            rec(0, k, 0, 0, [])
            for j in d:
                d[j].sort(key=lambda t: t[0])
            self.Smul[k] = d
        self.Slev = {k: {j: [t[0] for t in lst] for j, lst in self.Smul[k].items()} for k in self.Smul}

        self.Tindex, self.Tpolys = {}, []
        self.ops = {}
        for name, kpow in (("M", 2), ("V", 4)):
            rows, cols, tids, nums, dens = self._build(kpow)
            n = len(self.states)
            order = np.lexsort((cols, rows))
            rows, cols, tids, nums, dens = rows[order], cols[order], tids[order], nums[order], dens[order]
            key = rows * n + cols
            starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]]) if len(key) else np.zeros(0, np.int64)
            urows, ucols = rows[starts], cols[starts]
            indptr = np.zeros(n + 1, dtype=np.int64)
            np.cumsum(np.bincount(urows, minlength=n), out=indptr[1:])
            maxrow = int(np.diff(indptr).max()) if n else 0
            self.ops[name] = dict(tids=tids, nums=nums, dens=dens, starts=starts,
                                  indices=ucols.astype(np.int32), indptr=indptr.astype(np.int64),
                                  n_entries=len(rows), nnz=len(starts), maxrow=maxrow)
            if verbose:
                print(f"#   {name}: {len(rows)} entries, nnz {len(starts)}, max row {maxrow}, "
                      f"{len(self.Tpolys)} T-polys ({time.time()-t0:.1f}s)", flush=True)

    def _tid(self, T):
        i = self.Tindex.get(T)
        if i is None:
            p = [Fr(1)] + [Fr(0)] * ORD
            for m, t in T:
                for _ in range(t):
                    p = pmul(p, self.wpoly[m])
            i = len(self.Tpolys)
            self.Tindex[T] = i
            self.Tpolys.append(p)
        return i

    def _build(self, kpow):
        from bisect import bisect_right
        lev = self._lev
        J = self._J
        rows, cols, tids, nums, dens = [], [], [], [], []
        L, Pmax = self.L, self.Pmax
        for o, st in enumerate(self.states):
            occ = dict(st)
            N = int(self.level[o]); P = int(self.P[o]); so = int(self.size[o])
            occ_modes = sorted(occ)
            Tlist = []

            def trec(i, k_left, acc, jt, lt, bin_):
                Tlist.append((tuple(acc), jt, lt, bin_))
                if k_left == 0:
                    return
                for ii in range(i, len(occ_modes)):
                    m = occ_modes[ii]
                    for t in range(1, min(occ[m], k_left) + 1):
                        acc.append((m, t))
                        trec(ii + 1, k_left - t, acc, jt + t * J[m], lt + t * lev[m], bin_ * comb(occ[m], t))
                        acc.pop()

            trec(0, kpow, [], 0, 0, 1)
            for (T, jt, lt, binT) in Tlist:
                ka = sum(t for _, t in T)
                kc = kpow - ka
                if P - ka + kc > Pmax:
                    continue
                lst = self.Smul[kc].get(jt)
                if not lst:
                    continue
                budget = L - N + lt
                nmax = bisect_right(self.Slev[kc][jt], budget)
                if nmax == 0:
                    continue
                tid = self._tid(T)
                base = dict(occ)
                for m, t in T:
                    c = base[m] - t
                    if c:
                        base[m] = c
                    else:
                        del base[m]
                for (ls, S, pf) in lst[:nmax]:
                    new = dict(base)
                    for m, s in S:
                        new[m] = new.get(m, 0) + s
                    tgt = tuple(sorted(new.items()))
                    o2 = self.index.get(tgt)
                    if o2 is None:
                        o2 = self.index[self.reflect(tgt)]
                    s2 = int(self.size[o2])
                    rows.append(o2); cols.append(o); tids.append(tid)
                    nums.append(2 * binT * so); dens.append(pf * s2)
        return (np.array(rows, dtype=np.int64), np.array(cols, dtype=np.int64),
                np.array(tids, dtype=np.int64), np.array(nums, dtype=np.int64), np.array(dens, dtype=np.int64))

    def ref_index(self, z):
        return self.index[((0, z),) if z else ()]


# ============================================================================ modular pieces
def fr_mod(x, q):
    x = Fr(x)
    return (x.numerator % q) * pow(x.denominator % q, -1, q) % q


class ModOps:
    """Vertex matrices M_j, V_j (j = 0..ORD-1) mod q; leading blocks for smaller cutoffs on demand."""

    def __init__(self, S, q):
        self.q, self.S = q, S
        n = len(S.states)
        tp = np.array([[fr_mod(c, q) for c in p] for p in S.Tpolys], dtype=np.int64)
        self.mats = {}
        for name, o in S.ops.items():
            assert o["maxrow"] < (1 << 62) // (q * q), "row too long for int64 accumulation"
            dens = o["dens"]
            lut = np.zeros(int(dens.max()) + 1 if len(dens) else 1, dtype=np.int64)
            for d in np.unique(dens):
                lut[int(d)] = pow(int(d) % q, -1, q)
            coef = (o["nums"] % q) * lut[dens] % q
            for j in range(ORD):
                data = coef * tp[o["tids"], j] % q
                if len(data):
                    data = np.add.reduceat(data, o["starts"]) % q
                self.mats[(name, j, S.L)] = sps.csr_matrix((data, o["indices"], o["indptr"]), shape=(n, n))

    def get(self, name, j, l):
        A = self.mats.get((name, j, l))
        if A is None:
            n = self.S.nl[l]
            A = self.mats[(name, j, self.S.L)][:n, :n].tocsr()
            self.mats[(name, j, l)] = A
        return A


def mat_inv_mod(A, q):
    """inverse of a small dense matrix (list of lists of ints) mod q, Gauss-Jordan; None if singular."""
    n = len(A)
    M = [[int(A[i][j]) % q for j in range(n)] + [1 if i == j else 0 for j in range(n)] for i in range(n)]
    for c in range(n):
        piv = next((r for r in range(c, n) if M[r][c] % q), None)
        if piv is None:
            return None
        M[c], M[piv] = M[piv], M[c]
        iv = pow(M[c][c], -1, q)
        M[c] = [v * iv % q for v in M[c]]
        for r in range(n):
            if r != c and M[r][c]:
                f = M[r][c]
                M[r] = [(vr - f * vc) % q for vr, vc in zip(M[r], M[c])]
    return np.array([row[n:] for row in M], dtype=np.int64)


class Table:
    """E_z^(k)(l) residues, T[k][z, l//2]; entries never computed are 0 (default) or random ('garbage')."""

    def __init__(self, zrows, L, q, garbage_seed=None):
        self.q = q
        nl = L // 2 + 1
        self.known = [np.zeros((zrows, nl), dtype=bool) for _ in range(ORD + 1)]
        if garbage_seed is None:
            self.T = [np.zeros((zrows, nl), dtype=np.int64) for _ in range(ORD + 1)]
        else:
            rng = np.random.default_rng(garbage_seed + q)
            self.T = [rng.integers(0, q, size=(zrows, nl), dtype=np.int64) for _ in range(ORD + 1)]

    def set(self, k, z, l, v):
        self.T[k][z, l // 2] = v
        self.known[k][z, l // 2] = True


class Chan:
    """Branch through |z> at cutoff l, through order kmax, particle cap P <= cap."""

    def __init__(self, S, ops, z, l, kmax, cap, q, tab, dmode):
        self.S, self.ops, self.z, self.l, self.kmax, self.cap, self.q = S, ops, z, l, kmax, cap, q
        self.tab, self.dmode = tab, dmode
        n = S.nl[l]
        self.n = n
        self.ref = S.ref_index(z)
        assert self.ref < n and S.P[self.ref] == z
        lev, P, Zs = S.level[:n], S.P[:n], S.Z[:n]
        self.mask = P <= cap
        d = lev + (P - z) // 2                      # H0(state) - z/2 at eps = 0 (integer; P = z mod 2)
        idx = np.arange(n)
        self.Bidx = np.nonzero(self.mask & (d == 0) & (idx != self.ref))[0]
        assert np.all(lev[self.Bidx] >= 2)
        inv = np.zeros(n, dtype=np.int64)
        nzd = self.mask & (d != 0)
        for dv in np.unique(d[nzd]):
            inv[nzd & (d == dv)] = pow(int(-dv) % q, -1, q)
        self.Rinv = inv
        self.negP4 = (-(P % q) * pow(4, -1, q)) % q
        self.Dsel = np.nonzero(self.mask & (lev >= 2))[0]
        self.Dz = Zs[self.Dsel]
        self.Dl0 = np.full(len(self.Dsel), l // 2)
        self.Dl1 = (l - lev[self.Dsel]) // 2
        e0 = np.zeros(n, dtype=np.int64)
        e0[self.ref] = 1
        self.e0 = e0
        self.M0e = self.mv("M", 0, e0)
        self.V0e = self.mv("V", 0, e0)
        if len(self.Bidx):
            assert not self.M0e[self.Bidx].any() and not self.V0e[self.Bidx].any()
        self.psi = [e0]
        Ez0 = Fr(z, 2)
        self.E = [Ez0.numerator * pow(Ez0.denominator, -1, q) % q]
        self.G = None

    def Dvec(self, k):
        out = np.zeros(self.n, dtype=np.int64)
        if k < 2 or not len(self.Dsel):
            return out
        T = self.tab.T[k]
        zz = self.Dz if self.dmode == "zeromode" else np.zeros_like(self.Dz)
        out[self.Dsel] = (T[zz, self.Dl0] - T[zz, self.Dl1]) % self.q
        return out

    def mv(self, name, j, u):
        y = (self.ops.get(name, j, self.l) @ u) % self.q
        y[~self.mask] = 0
        return y

    def W1(self, u, r1, g1):
        out = self.negP4 * u % self.q
        if r1:
            out = (out + r1 * self.mv("M", 0, u)) % self.q
        if g1:
            out = (out + g1 * self.mv("V", 0, u)) % self.q
        return out

    def rhs0(self, n, r, g):
        q = self.q
        out = np.zeros(self.n, dtype=np.int64)
        for j in range(n):
            for name, c in (("M", r), ("V", g)):
                u = np.zeros_like(out)
                any_ = False
                for k in range(j + 1, n + 1):
                    if k == n and j == 0:
                        continue
                    ck = c[k - j]
                    if ck:
                        u = (u + ck * self.psi[n - k]) % q
                        any_ = True
                if any_:
                    out = (out + self.mv(name, j, u)) % q
        out = (out + self.negP4 * self.psi[n - 1]) % q
        for k in range(2, n):
            out = (out + self.Dvec(k) * self.psi[n - k]) % q
        for k in range(1, n):
            out = (out - self.E[k] * self.psi[n - k]) % q
        return out

    def bsolve(self, rhs, n, r, g):
        """fix psi_{n-1} on the degenerate partners from the B-projection of the order-n equation."""
        q = self.q
        B = self.Bidx
        if not len(B):
            return rhs
        if n == 1:
            assert not rhs[B].any(), "order-1 equation on B must be trivially satisfied"
            return rhs
        if self.G is None:
            r1, g1 = r[1], g[1]
            E1 = self.E[1]
            nb = len(B)
            W = np.zeros((nb, nb), dtype=np.int64)
            for name, c in (("M", r1), ("V", g1)):
                if c:
                    sub = self.ops.get(name, 0, self.l)[B][:, B].toarray() % q
                    W = (W + c * sub) % q
            W[np.arange(nb), np.arange(nb)] = (W[np.arange(nb), np.arange(nb)] + self.negP4[B]) % q
            A = (-W) % q
            A[np.arange(nb), np.arange(nb)] = (A[np.arange(nb), np.arange(nb)] + E1) % q
            G = mat_inv_mod(A.tolist(), q)
            assert G is not None, f"E1 - W1BB singular mod {q} (z={self.z}, l={self.l})"
            self.G = G
            self.r1g1 = (r1, g1)
        y = np.zeros(self.n, dtype=np.int64)
        tb = rhs[B] % q
        yb = np.zeros(len(B), dtype=np.int64)
        for i in range(len(B)):          # small dense product, exact in Python ints
            yb[i] = int(sum(int(self.G[i, j]) * int(tb[j]) for j in range(len(B))) % q)
        y[B] = yb
        assert not self.psi[n - 1][B].any()
        self.psi[n - 1] = (self.psi[n - 1] + y) % q
        before = int(rhs[self.ref])
        rhs = (rhs + self.W1(y, *self.r1g1) - self.E[1] * y) % q
        assert not rhs[B].any(), "B-projection of the order-n equation not satisfied"
        assert int(rhs[self.ref]) == before, "W_1 connects B to the reference"
        return rhs

    def finish(self, rhs, rn, gn):
        q = self.q
        rhs = rhs.copy()
        if rn:
            rhs = (rhs + rn * self.M0e) % q
        if gn:
            rhs = (rhs + gn * self.V0e) % q
        En = int(rhs[self.ref])
        self.E.append(En)
        self.psi.append(rhs * self.Rinv % q)
        return En


def default_tiers():
    """k_max(z) needed for D through eps^8 (bookkeeping.py)."""
    t = {}
    for z in range(0, 7):
        t[z] = 6
    for z in range(7, 11):
        t[z] = 4
    for z in range(11, 15):
        t[z] = 2
    return t


def run_mod(structs, opsd, L, q, tiers, capextra=0, dmode="zeromode", garbage_seed=None, Kprim=16):
    """dmode = 'zeromode' (D depends on the zero-mode number of the state) or 'consistent' (D uses E_0)."""
    inv2, inv3 = pow(2, -1, q), pow(3, -1, q)
    ls = list(range(0, L + 1, 2))
    zrows = max(structs[0].Pmax, structs[1].Pmax) + 1
    tab = Table(zrows, L, q, garbage_seed)
    ch = {}
    for z, km in tiers.items():
        for l in ls:
            if l == L and z <= 3:
                continue
            cap = z + 4 * (km // 2) + capextra
            ch[(z, l)] = Chan(structs[z % 2], opsd[z % 2], z, l, km, cap, q, tab, dmode)
    for p in range(4):
        ch[(p, L)] = Chan(structs[p % 2], opsd[p % 2], p, L, ORD, p + Kprim + capextra, q, tab, dmode)
    r = [0] * (ORD + 1)
    g = [0] * (ORD + 1)
    xs = [inv2, (-pow(4, -1, q)) % q] + [0] * (ORD - 1)
    C = [1]
    for n in range(1, ORD + 1):
        active = [c for c in ch.values() if c.kmax >= n]
        rh = {}
        for key, c in ch.items():
            if c.kmax >= n:
                rh[key] = c.bsolve(c.rhs0(n, r, g), n, r, g)
        X = {p: int(rh[(p, L)][ch[(p, L)].ref]) for p in range(4)}
        rn = (xs[n] - X[1] + X[0]) * inv2 % q
        gn = (-xs[n] - X[3] + X[0] - 6 * rn) * inv3 % q
        r[n], g[n] = rn, gn
        for key, c in ch.items():
            if c.kmax >= n:
                c.finish(rh[key], rn, gn)
                tab.set(n, c.z, c.l, c.E[n])
        E = {p: ch[(p, L)].E[n] for p in range(4)}
        assert (E[1] - E[0] - xs[n]) % q == 0 and (E[3] - E[0] + xs[n]) % q == 0
        C.append((E[2] - E[0]) % q)
    out = {"C": C, "r": r, "g": g, "E": [ch[(p, L)].E for p in range(4)],
           "Ez": {f"{z},{l}": c.E for (z, l), c in ch.items()}}
    return out


# ============================================================================ driver
_G = {}


def worker(q):
    t0 = time.time()
    a = _G["args"]
    structs = _G["structs"]
    opsd = {par: ModOps(structs[par], q) for par in (0, 1)}
    res = {}
    for name, kw in _G["variants"]:
        res[name] = run_mod(structs, opsd, a["L"], q, **kw)
    return q, res, time.time() - t0


def primes_below(top, count):
    out = []
    n = top - 1
    while len(out) < count:
        if n % 2 and all(n % d for d in range(3, isqrt(n) + 1, 2)):
            out.append(n)
        n -= 2
    return out


def ratrec(a, m):
    a %= m
    bound = isqrt(m // 2)
    r0, r1 = m, a
    s0, s1 = 0, 1
    while r1 > bound:
        qq = r0 // r1
        r0, r1 = r1, r0 - qq * r1
        s0, s1 = s1, s0 - qq * s1
    if s1 == 0 or abs(s1) > bound:
        return None
    n, d = (r1, s1) if s1 > 0 else (-r1, -s1)
    if gcd(n, d) != 1:
        return None
    return Fr(n, d)


def crt_list(res_by_prime, primes):
    M = 1
    x = 0
    for q in primes:
        a = res_by_prime[q]
        t = ((a - x) * pow(M, -1, q)) % q
        x = x + M * t
        M *= q
    return x, M


def flatten(res):
    out = {}
    for k in ("C", "r", "g"):
        for i, v in enumerate(res[k]):
            out[f"{k}|{i}"] = v
    for p, row in enumerate(res["E"]):
        for i, v in enumerate(row):
            out[f"E|{p}|{i}"] = v
    for zl, row in res["Ez"].items():
        for i, v in enumerate(row):
            out[f"Ez|{zl}|{i}"] = v
    return out


def reconstruct(per_prime, primes, n_check):
    use, chk = primes[:-n_check], primes[-n_check:]
    keys = list(per_prime[primes[0]].keys())
    out, bad = {}, []
    for key in keys:
        x, M = crt_list({q: per_prime[q][key] for q in use}, use)
        f = ratrec(x, M)
        ok = f is not None and all((f.numerator - f.denominator * per_prime[q][key]) % q == 0 for q in chk)
        if not ok:
            bad.append(key)
        out[key] = f
    return out, bad


def parse_tiers(s):
    if s in (None, "", "default"):
        return default_tiers()
    t = {}
    for part in s.split(","):
        zr, k = part.split(":")
        if "-" in zr:
            a, b = map(int, zr.split("-"))
        else:
            a = b = int(zr)
        for z in range(a, b + 1):
            t[z] = int(k)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--tiers", default="default", help="e.g. '0-6:6,7-10:4,11-14:2' (z-range:k_max)")
    ap.add_argument("--capextra", type=int, default=0, help="raise every channel cap by this")
    ap.add_argument("--variants", default="zeromode",
                    help="comma list of: zeromode, garbage, consistent")
    ap.add_argument("--nprimes", type=int, default=64)
    ap.add_argument("--ncheck", type=int, default=8)
    ap.add_argument("--procs", type=int, default=1)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t0 = time.time()
    tiers = parse_tiers(a.tiers)
    need_cap = max([z + 4 * (k // 2) for z, k in tiers.items()] + [19]) + a.capextra
    Pm = {0: need_cap if need_cap % 2 == 0 else need_cap - 1, 1: need_cap if need_cap % 2 == 1 else need_cap - 1}
    Pm = {0: max(Pm[0], 18 + a.capextra), 1: max(Pm[1], 19 + a.capextra)}
    structs = {par: Structure(a.L, par, Pm[par]) for par in (0, 1)}
    variants = []
    for v in a.variants.split(","):
        if v == "zeromode":
            variants.append(("zeromode", dict(tiers=tiers, capextra=a.capextra, dmode="zeromode")))
        elif v == "garbage":
            variants.append(("garbage", dict(tiers=tiers, capextra=a.capextra, dmode="zeromode",
                                             garbage_seed=12345)))
        elif v == "consistent":
            variants.append(("consistent", dict(tiers={0: 6}, capextra=a.capextra, dmode="consistent")))
        else:
            raise ValueError(v)
    _G.update(structs=structs, args=vars(a), variants=variants)
    primes = primes_below(1 << 23, a.nprimes + a.ncheck)
    print(f"# structure built in {time.time()-t0:.1f}s; tiers {tiers}; capextra {a.capextra}; "
          f"variants {[v for v, _ in variants]}; {len(primes)} primes on {a.procs} procs", flush=True)
    per_prime = {v: {} for v, _ in variants}
    if a.procs > 1:
        import multiprocessing as mp
        ctx = mp.get_context("fork")
        with ctx.Pool(a.procs) as pool:
            for q, res, dt in pool.imap_unordered(worker, primes):
                for v in res:
                    per_prime[v][q] = flatten(res[v])
                nd = len(per_prime[variants[0][0]])
                if nd in (1, len(primes)) or nd % 16 == 0:
                    print(f"#   {nd}/{len(primes)} primes done (last {q}: {dt:.1f}s)", flush=True)
    else:
        for q in primes:
            q, res, dt = worker(q)
            for v in res:
                per_prime[v][q] = flatten(res[v])
            print(f"#   prime {q} done in {dt:.1f}s", flush=True)
    final = {}
    for v, _ in variants:
        rec, bad = reconstruct(per_prime[v], primes, a.ncheck)
        if bad:
            print(f"# WARNING variant {v}: {len(bad)} quantities failed verification, e.g. {bad[:5]}", flush=True)
        maxdig = max(len(str(abs(f.numerator))) + len(str(f.denominator)) for f in rec.values() if f is not None)
        mod_digits = len(str(np.prod([int(x) for x in primes[:-a.ncheck]], dtype=object)))
        print(f"# variant {v}: max num+den digits = {maxdig}, modulus digits = {mod_digits}, "
              f"failed = {len(bad)}", flush=True)
        final[v] = {"bad": bad, "values": {k: (str(x) if x is not None else None) for k, x in rec.items()},
                    "max_digits": maxdig, "modulus_digits": mod_digits}
        for i in range(ORD + 1):
            x = rec[f"C|{i}"]
            print(f"#   {v} C_{i} = {float(x) if x is not None else None!r}", flush=True)
    meta = {"L": a.L, "tiers": {str(z): k for z, k in tiers.items()}, "capextra": a.capextra,
            "Pmax": Pm, "primes": primes, "nprimes_used": a.nprimes, "ncheck": a.ncheck,
            "n_states": {par: len(structs[par].states) for par in (0, 1)},
            "n_states_full_J0": {par: structs[par].n_full for par in (0, 1)},
            "nnz_V": {par: int(structs[par].ops["V"]["nnz"]) for par in (0, 1)},
            "seconds": time.time() - t0}
    with open(a.out, "w") as f:
        json.dump({"meta": meta, "variants": final}, f, indent=1)
    print(f"# wrote {a.out}  total {time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
