#!/usr/bin/env python3
"""
ce_core.py -- prime-independent structure + modular operator layer for the complete-window study.

Adapted from ../zeromode_exact/zeromode_modular.py (copied here as zeromode_modular_orig.py, untouched):
  * reflection-even J = 0 orbit basis of one field-parity sector, states sorted by (level, P, occupation), so the
    cutoff-l space is a prefix (nl[l]);
  * vertex matrices in the similarity (monomial) frame, polynomial in eps (exact eps-coefficients 0..ORD-1);
New here:
  * 'Mp' = M' = M minus its pure zero-mode part :Z^2: (the parts of <:phi^2:>_theta with >= 1 chi leg);
  * zero-mode shift maps zshift[d][s] = index of the state with the same chi content and z_s + d zero modes;
  * exact (Fraction) extraction of small blocks of W_1 = -P/4 + g1 V_0 (degenerate-subspace analysis);
  * the generator L~_{-1}, Lbar~_{-1} of the similarity frame (descendant vectors), see desc_vector().
"""
from fractions import Fraction as Fr
from math import comb, factorial, isqrt, gcd
from bisect import bisect_right
import time
import numpy as np
import scipy.sparse as sps

ORD = 8
G1 = Fr(1, 3)
import os as _os
LOWMEM = _os.environ.get("CE_LOWMEM", "0") == "1"


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


ZSHIFTS = tuple(range(-24, 25, 2))


class Structure:
    """One field-parity sector at cutoff L, particle cap Pmax (reflection-even orbits, sorted by (level, P))."""

    def __init__(self, L, parity, Pmax, verbose=True, with_Mp=True, with_Vp=False, with_Xnu=False, with_MpZ=False):
        t0 = time.time()
        self.L, self.parity, self.Pmax = L, parity, Pmax
        modes = []
        for lev in range(L + 1):
            for a in range(lev + 1):
                modes.append((a, lev - a))
        self.modes = modes
        assert modes[0] == (0, 0)
        mid = {m: i for i, m in enumerate(modes)}
        self.mid = mid
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

        reps = [st for st in allst if st <= reflect(st)]

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
        n = len(reps)
        # zero-mode shift maps (same chi content, z -> z + d)
        self.zshift = {}
        for d in ZSHIFTS:
            arr = np.full(n, -1, dtype=np.int64)
            for i, s in enumerate(reps):
                z2 = self.Z[i] + d
                if z2 < 0 or self.P[i] + d > Pmax:
                    continue
                chi = tuple((m, c) for m, c in s if m != 0)
                tgt = ((0, z2),) + chi if z2 else chi
                j = self.index.get(tgt)
                if j is None:
                    j = self.index.get(reflect(tgt))
                assert j is not None
                arr[i] = j
            self.zshift[d] = arr
        if verbose:
            print(f"# L={L} par={parity} Pmax={Pmax}: {self.n_full} J=0 states, {n} reflection-even "
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
        oplist = [("M", 2, False), ("V", 4, False)] + ([("Mp", 2, True)] if with_Mp else []) + \
            ([("Vp", 4, True)] if with_Vp else []) + ([("Xnu", 2, True)] if with_Xnu else []) + \
            ([("MpZ", 2, True)] if with_MpZ else [])
        for name, kpow, skipz in oplist:
            rows, cols, tids, nums, dens = self._build(kpow, skipz, legw=(name == "Xnu"), zleg_only=(name == "MpZ"))
            order = np.lexsort((cols, rows))
            rows, cols, tids, nums, dens = rows[order], cols[order], tids[order], nums[order], dens[order]
            key = rows * n + cols
            starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]]) if len(key) else np.zeros(0, np.int64)
            urows, ucols = rows[starts], cols[starts]
            indptr = np.zeros(n + 1, dtype=np.int64)
            np.cumsum(np.bincount(urows, minlength=n), out=indptr[1:])
            maxrow = int(np.diff(indptr).max()) if n else 0
            self.ops[name] = dict(rows=rows, cols=cols, tids=tids, nums=nums, dens=dens, starts=starts,
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

    def _build(self, kpow, skip_pure_zero=False, legw=False, zleg_only=False):
        """legw (residual_log 2026-10-09, operator X = M'^{+-}_nu of WINDOW_SPEC Sec. 2.5a): every term weighted by
        s * (level of its annihilated + created legs), s = +1 for one creator and one annihilator, -1 otherwise."""
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
                Tzero = all(m == 0 for m, _ in T)
                tid = self._tid(T)
                base = dict(occ)
                for m, t in T:
                    c = base[m] - t
                    if c:
                        base[m] = c
                    else:
                        del base[m]
                for (ls, S, pf) in lst[:nmax]:
                    if skip_pure_zero and Tzero and all(m == 0 for m, _ in S):
                        continue
                    # MpZ (README Sec. 12): the Z-chi terms of M' only (at least one zero-mode leg)
                    if zleg_only and not (any(m == 0 for m, _ in T) or any(m == 0 for m, _ in S)):
                        continue
                    wleg = ((1 if (ka == 1 and kc == 1) else -1) * (lt + ls)) if legw else 1
                    if wleg == 0:
                        continue
                    new = dict(base)
                    for m, s in S:
                        new[m] = new.get(m, 0) + s
                    tgt = tuple(sorted(new.items()))
                    o2 = self.index.get(tgt)
                    if o2 is None:
                        o2 = self.index[self.reflect(tgt)]
                    s2 = int(self.size[o2])
                    rows.append(o2); cols.append(o); tids.append(tid)
                    nums.append(2 * binT * so * wleg); dens.append(pf * s2)
        return (np.array(rows, dtype=np.int64), np.array(cols, dtype=np.int64),
                np.array(tids, dtype=np.int64), np.array(nums, dtype=np.int64), np.array(dens, dtype=np.int64))

    def ref_index(self, z):
        return self.index[((0, z),) if z else ()]

    # ------------------------------------------------------------------ exact helpers
    def exact_block(self, name, j, idx_rows, idx_cols):
        """exact eps^j coefficient of op `name` restricted to rows x cols (lists of state indices)."""
        o = self.ops[name]
        rpos = {r: a for a, r in enumerate(idx_rows)}
        cpos = {c: b for b, c in enumerate(idx_cols)}
        out = [[Fr(0)] * len(idx_cols) for _ in idx_rows]
        sel = np.nonzero(np.isin(o["cols"], np.array(idx_cols, dtype=np.int64)) &
                         np.isin(o["rows"], np.array(idx_rows, dtype=np.int64)))[0]
        for e in sel:
            r, c = int(o["rows"][e]), int(o["cols"][e])
            out[rpos[r]][cpos[c]] += Fr(int(o["nums"][e]), int(o["dens"][e])) * self.Tpolys[int(o["tids"][e])][j]
        return out

    def exact_apply(self, name, j, vec):
        """exact eps^j coefficient of op `name` applied to a sparse Fraction vector {idx: val}."""
        o = self.ops[name]
        out = {}
        cols = np.array(sorted(vec), dtype=np.int64)
        sel = np.nonzero(np.isin(o["cols"], cols))[0]
        for e in sel:
            r, c = int(o["rows"][e]), int(o["cols"][e])
            v = Fr(int(o["nums"][e]), int(o["dens"][e])) * self.Tpolys[int(o["tids"][e])][j] * vec[c]
            if v:
                out[r] = out.get(r, Fr(0)) + v
        return {k: v for k, v in out.items() if v}

    def W1_block(self, idx):
        """exact W_1 = -P/4 + g1 V_0 (r_1 = 0 in every scheme) on the index set idx."""
        B = self.exact_block("V", 0, idx, idx)
        out = [[G1 * B[a][b] for b in range(len(idx))] for a in range(len(idx))]
        for a, i in enumerate(idx):
            out[a][a] += Fr(-int(self.P[i]), 4)
        return out

    # ------------------------------------------------------------------ descendants (similarity frame)
    def apply_L(self, vec, which):
        """L~_{-1} (which = 0: a -> a + 1, weight a + 1) or Lbar~_{-1} (which = 1: b -> b + 1, weight b + 1)
        on a Fraction vector over occupation tuples {occ_tuple: coeff} (monomial basis, NOT orbit-reduced)."""
        out = {}
        for st, c in vec.items():
            occ = dict(st)
            for m, nm in occ.items():
                a, b = self.modes[m]
                if which == 0:
                    m2, wgt = self.mid.get((a + 1, b)), a + 1
                else:
                    m2, wgt = self.mid.get((a, b + 1)), b + 1
                if m2 is None:
                    continue
                new = dict(occ)
                new[m] -= 1
                if new[m] == 0:
                    del new[m]
                new[m2] = new.get(m2, 0) + 1
                # A_{m2}^dag A_m on prod (A^dag)^n |0> : factor n_m (monomial basis)
                t = tuple(sorted(new.items()))
                out[t] = out.get(t, Fr(0)) + c * nm * wgt
        return {k: v for k, v in out.items() if v}

    def orbit_vector(self, vec):
        """monomial-basis vector over occupation tuples -> coordinates in the reflection-even orbit basis
        (e_o = m + Rm). Asserts the vector is reflection even."""
        out = {}
        for st, c in vec.items():
            rs = self.reflect(st)
            assert vec.get(rs, Fr(0)) == c, "descendant vector not reflection even"
            i = self.index.get(st)
            if i is None:
                continue          # the reflected partner carries the orbit coordinate
            out[i] = c
        return out


# ============================================================================ modular layer
def fr_mod(x, q):
    x = Fr(x)
    return (x.numerator % q) * pow(x.denominator % q, -1, q) % q


class ModOps:
    """Vertex matrices M_j, V_j, Mp_j (j = 0..ORD-1) mod q; leading blocks for smaller cutoffs on demand."""

    def __init__(self, S, q, names=("M", "V", "Mp", "Vp", "Xnu", "MpZ")):
        self.q, self.S = q, S
        n = len(S.states)
        tp = np.array([[fr_mod(c, q) for c in p] for p in S.Tpolys], dtype=np.int64)
        self.mats = {}
        for name in names:
            if name not in S.ops:
                continue
            o = S.ops[name]
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
                A = sps.csr_matrix((data, o["indices"], o["indptr"]), shape=(n, n))
                if LOWMEM:
                    A = A.tocsc()
                    A.sort_indices()
                self.mats[(name, j, S.L)] = A

    def get(self, name, j, l):
        """cutoff-l block.  Default: cached CSR copy of the leading n x n block.  LOWMEM: zero-copy CSC view of
        the first n columns (shape N x n; the caller drops the rows >= n)."""
        A = self.mats.get((name, j, l))
        if A is None:
            n = self.S.nl[l]
            F = self.mats[(name, j, self.S.L)]
            if LOWMEM:
                m = int(F.indptr[n])
                A = sps.csc_matrix((F.data[:m], F.indices[:m], F.indptr[:n + 1]), shape=(F.shape[0], n), copy=False)
            else:
                A = F[:n, :n].tocsr()
            self.mats[(name, j, l)] = A
        return A


def mat_inv_mod(A, q):
    """inverse of a dense square int matrix mod q (numpy Gauss-Jordan); None if singular mod q."""
    A = np.array(A, dtype=np.int64) % q
    n = A.shape[0]
    M = np.concatenate([A, np.eye(n, dtype=np.int64)], axis=1)
    for c in range(n):
        nzr = np.nonzero(M[c:, c] % q)[0]
        if len(nzr) == 0:
            return None
        piv = c + int(nzr[0])
        if piv != c:
            M[[c, piv]] = M[[piv, c]]
        iv = pow(int(M[c, c]), -1, q)
        M[c] = M[c] * iv % q
        f = M[:, c].copy()
        f[c] = 0
        nzf = np.nonzero(f)[0]
        if len(nzf):
            M[nzf] = (M[nzf] - (f[nzf, None] * M[c][None, :]) % q) % q
    return M[:, n:]


def frac_nullspace(A):
    """exact right null space of a Fraction matrix (list of lists); returns list of basis vectors."""
    m = len(A)
    nc = len(A[0]) if m else 0
    M = [list(r) for r in A]
    piv_cols = []
    r = 0
    for c in range(nc):
        p = next((i for i in range(r, m) if M[i][c] != 0), None)
        if p is None:
            continue
        M[r], M[p] = M[p], M[r]
        iv = 1 / M[r][c]
        M[r] = [x * iv for x in M[r]]
        for i in range(m):
            if i != r and M[i][c] != 0:
                f = M[i][c]
                M[i] = [x - f * y for x, y in zip(M[i], M[r])]
        piv_cols.append(c)
        r += 1
        if r == m:
            break
    free = [c for c in range(nc) if c not in piv_cols]
    basis = []
    for fc in free:
        v = [Fr(0)] * nc
        v[fc] = Fr(1)
        for i, pc in enumerate(piv_cols):
            v[pc] = -M[i][fc]
        basis.append(v)
    return basis


def frac_inv(A):
    n = len(A)
    M = [list(A[i]) + [Fr(int(i == j)) for j in range(n)] for i in range(n)]
    for c in range(n):
        p = next((i for i in range(c, n) if M[i][c] != 0), None)
        if p is None:
            return None
        M[c], M[p] = M[p], M[c]
        iv = 1 / M[c][c]
        M[c] = [x * iv for x in M[c]]
        for i in range(n):
            if i != c and M[i][c] != 0:
                f = M[i][c]
                M[i] = [x - f * y for x, y in zip(M[i], M[c])]
    return [row[n:] for row in M]


# ============================================================================ CRT / reconstruction
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


def lagrange_coeffs_mod(ts, ys, q):
    """coefficients c_0..c_{m-1} of the degree < m polynomial through (ts[i], ys[i]) mod q."""
    m = len(ts)
    coef = [0] * m
    for i in range(m):
        # basis polynomial prod_{j != i} (t - t_j)/(t_i - t_j)
        num = [1]
        den = 1
        for j in range(m):
            if j == i:
                continue
            num = [((num[k - 1] if k >= 1 else 0) - ts[j] * (num[k] if k < len(num) else 0)) % q
                   for k in range(len(num) + 1)]
            den = den * (ts[i] - ts[j]) % q
        f = ys[i] * pow(den, -1, q) % q
        for k in range(m):
            coef[k] = (coef[k] + f * num[k]) % q
    return coef
