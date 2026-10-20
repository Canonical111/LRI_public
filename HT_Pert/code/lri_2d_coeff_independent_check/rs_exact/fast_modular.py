#!/usr/bin/env python3
"""
Fast exact implementation: the same Rayleigh-Schroedinger recursion as ref_fraction.py, but
  * in the reflection-EVEN J=0 sector (orbit basis e_o = m + R m, or m if R m = m),
  * with vertex matrix elements from the closed multiset formula
        <:phi^k:>_theta / k!*(2 for both M (k=2) and V (k=4, prefactor 1/12)):
        n -> n - T + S :  2 * prod_m C(n_m, t_m) * prod_m w_m(eps)^{t_m} / prod_m s_m!
    (T = annihilated multiset, S = created multiset, J(S) = J(T)),
  * in modular arithmetic mod many ~23-bit primes (numpy/scipy sparse, int64), followed by Chinese
    remaindering and rational reconstruction, verified on held-out primes.

Outputs are exact rationals (certified by agreement on the held-out primes).
"""
from fractions import Fraction as Fr
from math import comb, factorial, isqrt, gcd
import argparse, json, os, sys, time
import numpy as np
import scipy.sparse as sps

ORD = 8
SCHEMES = ("raw", "consistent", "literal")


# ============================================================================ exact structure
def falling_poly(a):
    """(x)_a/a! with x = 1/2 - eps/4 as exact eps-coefficients 0..ORD."""
    c = [Fr(0)] * (ORD + 1)
    c[0] = Fr(1)
    for i in range(a):
        # multiply by (x+i)/(i+1),  x + i = (2i+1)/2 - eps/4
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
    """Prime-independent data for one field-parity sector at cutoff L with absolute particle cap Pmax."""

    def __init__(self, L, parity, Pmax, verbose=True):
        t0 = time.time()
        self.L, self.parity, self.Pmax = L, parity, Pmax
        modes = []
        for lev in range(L + 1):
            for a in range(lev + 1):
                modes.append((a, lev - a))
        self.modes = modes
        self.lev = np.array([a + b for a, b in modes])
        self.J = np.array([a - b for a, b in modes])
        mid = {m: i for i, m in enumerate(modes)}
        self.refl = [mid[(b, a)] for (a, b) in modes]
        wp = {}
        fp = [falling_poly(a) for a in range(L + 1)]
        self.wpoly = [pmul(fp[a], fp[b]) for (a, b) in modes]
        lev = [int(x) for x in self.lev]
        J = [int(x) for x in self.J]
        self._lev, self._J = lev, J

        # ---- all J=0 states (level <= L, parity, P <= Pmax), canonical = tuple of (mode, count) sorted
        allst = []
        nz = list(range(1, len(modes)))          # mode 0 is (0,0)
        # iterative DFS over non-zero modes
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
            # remaining modes all have level >= lev[m] (modes sorted by level)
            if L_ + lev[m] > L:
                # cannot add any more non-zero quanta; still must close with J=0
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

        reps, size = [], []
        for st in allst:
            rs = reflect(st)
            if st <= rs:
                reps.append(st)
                size.append(1 if rs == st else 2)
        self.states = reps
        self.size = np.array(size)
        self.index = {s: i for i, s in enumerate(reps)}
        self.level = np.array([sum(lev[m] * c for m, c in s) for s in reps])
        self.P = np.array([sum(c for m, c in s) for s in reps])
        self.reflect = reflect
        if verbose:
            print(f"# L={L} par={parity} Pmax={Pmax}: {self.n_full} J=0 states, {len(reps)} reflection-even "
                  f"orbits  ({time.time()-t0:.1f}s)", flush=True)

        # ---- created multisets: Smul[k][J] = list sorted by level of (level, tuple((mode,s)), prod s!)
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
                        break   # modes sorted by level
                    acc.append(m)
                    rec(m, k_left - 1, lv + lev[m], j + J[m], acc)
                    acc.pop()

            rec(0, k, 0, 0, [])
            for j in d:
                d[j].sort(key=lambda t: t[0])
            self.Smul[k] = d
        self.Slev = {k: {j: [t[0] for t in lst] for j, lst in self.Smul[k].items()} for k in self.Smul}

        # ---- vertex entries
        self.Tindex, self.Tpolys = {}, []
        self.ops = {}
        for name, kpow in (("M", 2), ("V", 4)):
            rows, cols, tids, nums, dens = self._build(kpow)
            n = len(self.states)
            # sort entries by (row, col); duplicates (same row/col, different T) are summed per prime
            order = np.lexsort((cols, rows))
            rows, cols, tids, nums, dens = rows[order], cols[order], tids[order], nums[order], dens[order]
            key = rows * n + cols
            starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]]) if len(key) else np.zeros(0, np.int64)
            urows, ucols = rows[starts], cols[starts]
            indptr = np.zeros(n + 1, dtype=np.int64)
            np.cumsum(np.bincount(urows, minlength=n), out=indptr[1:])
            maxrow = int(np.diff(indptr).max()) if n else 0
            self.ops[name] = dict(tids=tids, nums=nums, dens=dens, starts=starts,
                                  indices=ucols.astype(np.int32), indptr=indptr.astype(np.int32),
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
        lev, J = self._lev, self._J
        rows, cols, tids, nums, dens = [], [], [], [], []
        L, Pmax = self.L, self.Pmax
        for o, st in enumerate(self.states):
            occ = dict(st)
            N = int(self.level[o]); P = int(self.P[o]); so = int(self.size[o])
            occ_modes = sorted(occ)
            # enumerate annihilated sub-multisets T (|T| <= kpow)
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
                        o2 = self.index[self.reflect(tgt)]     # must exist (J=0, level, P, parity ok)
                    s2 = int(self.size[o2])
                    rows.append(o2); cols.append(o); tids.append(tid)
                    nums.append(2 * binT * so); dens.append(pf * s2)
        return (np.array(rows, dtype=np.int64), np.array(cols, dtype=np.int64),
                np.array(tids, dtype=np.int64), np.array(nums, dtype=np.int64), np.array(dens, dtype=np.int64))

    def ref_index(self, p):
        return self.index[((0, p),) if p else ()]


# ============================================================================ modular RS
def fr_mod(x, q):
    x = Fr(x)
    return (x.numerator % q) * pow(x.denominator % q, -1, q) % q


class ModOps:
    """Vertex matrices M_j, V_j (j = 0..ORD-1) mod q for one Structure (CSR, shared sparsity pattern)."""

    def __init__(self, S, q):
        self.q = q
        n = len(S.states)
        tp = np.array([[fr_mod(c, q) for c in p] for p in S.Tpolys], dtype=np.int64)   # (nT, ORD+1)
        self.mats = {}
        for name, o in S.ops.items():
            assert o["maxrow"] < (1 << 62) // (q * q), "row too long for int64 accumulation"
            dens = o["dens"]
            lut = np.zeros(int(dens.max()) + 1 if len(dens) else 1, dtype=np.int64)
            for d in np.unique(dens):
                lut[int(d)] = pow(int(d) % q, -1, q)
            coef = (o["nums"] % q) * lut[dens] % q
            mats = []
            for j in range(ORD):
                data = coef * tp[o["tids"], j] % q
                if len(data):
                    data = np.add.reduceat(data, o["starts"]) % q
                mats.append(sps.csr_matrix((data, o["indices"], o["indptr"]), shape=(n, n)))
            self.mats[name] = mats


class ModChannel:
    def __init__(self, S, ops, p, l, K, q, Dsrc):
        self.S, self.ops, self.p, self.l, self.q = S, ops, p, l, q
        self.ref = S.ref_index(p)
        self.mask = (S.level <= l) & (S.P <= p + K)
        d = S.level + (S.P - p) // 2          # E_ref^0 - H0 = -d   (integer)
        inv = np.zeros(len(S.states), dtype=np.int64)
        for i in np.nonzero(self.mask)[0]:
            if i != self.ref:
                inv[i] = pow(int(-d[i]) % q, -1, q)
        self.Rinv = inv
        self.negP4 = (-(S.P % q) * pow(4, -1, q)) % q
        self.Dsrc = Dsrc          # None or (l, vacua dict) -> D_k(N) = Ev[l][k] - Ev[l-N][k]
        e0 = np.zeros(len(S.states), dtype=np.int64)
        e0[self.ref] = 1
        self.psi = [e0]
        self.E = [Fr(p, 2).numerator * pow(Fr(p, 2).denominator, -1, q) % q]

    def Dvec(self, k):
        if self.Dsrc is None:
            return None
        l, Ev = self.Dsrc
        if k >= len(Ev[l]):
            return None
        q = self.q
        lv = self.S.level
        out = np.zeros(len(lv), dtype=np.int64)
        for N in range(0, l + 1, 2):
            val = (Ev[l][k] - Ev[l - N][k]) % q
            out[(lv == N)] = val
        out[~self.mask] = 0
        return out

    def mv(self, name, j, u):
        y = (self.ops.mats[name][j] @ u) % self.q
        y[~self.mask] = 0
        return y

    def rhs0(self, n, r, g):
        q = self.q
        out = np.zeros(len(self.S.states), dtype=np.int64)
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
        for k in range(1, n + 1):
            D = self.Dvec(k)
            if D is not None:
                out = (out + D * self.psi[n - k]) % q
        for k in range(1, n):
            out = (out - self.E[k] * self.psi[n - k]) % q
        return out

    def finish(self, rhs0, rn, gn):
        q = self.q
        rhs = rhs0.copy()
        e0 = self.psi[0]
        if rn:
            rhs = (rhs + rn * self.mv("M", 0, e0)) % q
        if gn:
            rhs = (rhs + gn * self.mv("V", 0, e0)) % q
        En = int(rhs[self.ref])
        self.E.append(En)
        self.psi.append(rhs * self.Rinv % q)
        return En


def run_scheme_mod(structs, opsd, L, K, scheme, q):
    inv2, inv3, inv4 = pow(2, -1, q), pow(3, -1, q), pow(4, -1, q)
    ls = list(range(0, L + 1, 2))
    Ev = {l: [0] for l in ls}
    ch = {}
    S = lambda p: structs[p % 2]
    O = lambda p: opsd[p % 2]
    if scheme == "raw":
        for p in range(4):
            ch[("p", p)] = ModChannel(S(p), O(p), p, L, K, q, None)
    elif scheme == "consistent":
        for l in ls:
            ch[("v", l)] = ModChannel(S(0), O(0), 0, l, K, q, (l, Ev))
        ch[("p", 0)] = ch[("v", L)]
        for p in (1, 2, 3):
            ch[("p", p)] = ModChannel(S(p), O(p), p, L, K, q, (L, Ev))
    elif scheme == "literal":
        for l in ls:
            ch[("v", l)] = ModChannel(S(0), O(0), 0, l, K, q, None)
        for p in range(4):
            ch[("p", p)] = ModChannel(S(p), O(p), p, L, K, q, (L, Ev))
    uniq = []
    for c in ch.values():
        if all(c is not u for u in uniq):
            uniq.append(c)
    r = [0] * (ORD + 1)
    g = [0] * (ORD + 1)
    xs = [inv2, (-inv4) % q] + [0] * (ORD - 1)
    C = [1]
    for n in range(1, ORD + 1):
        rh = [c.rhs0(n, r, g) for c in uniq]
        X = {}
        for p in range(4):
            c = ch[("p", p)]
            X[p] = int(rh[[i for i, u in enumerate(uniq) if u is c][0]][c.ref])
        rn = (xs[n] - X[1] + X[0]) * inv2 % q
        gn = (-xs[n] - X[3] + X[0] - 6 * rn) * inv3 % q
        r[n], g[n] = rn, gn
        for c, rr in zip(uniq, rh):
            c.finish(rr, rn, gn)
        if scheme != "raw":
            for l in ls:
                Ev[l].append(ch[("v", l)].E[n])
        E = {p: ch[("p", p)].E[n] for p in range(4)}
        assert (E[1] - E[0] - xs[n]) % q == 0 and (E[3] - E[0] + xs[n]) % q == 0
        C.append((E[2] - E[0]) % q)
    out = {"C": C, "r": r, "g": g, "E": [ch[("p", p)].E for p in range(4)]}
    if scheme == "raw":
        out["vacua"] = {L: ch[("p", 0)].E}
    else:
        out["vacua"] = {l: ch[("v", l)].E for l in ls}
    return out


# ============================================================================ driver
_G = {}


def worker(q):
    t0 = time.time()
    structs, L, K, schemes = _G["structs"], _G["L"], _G["K"], _G["schemes"]
    opsd = {par: ModOps(structs[par], q) for par in (0, 1)}
    res = {s: run_scheme_mod(structs, opsd, L, K, s, q) for s in schemes}
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
    """Rational reconstruction: a = n/d mod m with |n|, d <= sqrt(m/2). Returns Fraction or None."""
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
        # x = x mod M ; combine with a mod q
        t = ((a - x) * pow(M, -1, q)) % q
        x = x + M * t
        M *= q
    return x, M


def flatten(res):
    """Flatten a per-scheme residue dict to {key: int}."""
    out = {}
    for k in ("C", "r", "g"):
        for i, v in enumerate(res[k]):
            out[(k, i)] = v
    for p, row in enumerate(res["E"]):
        for i, v in enumerate(row):
            out[("E", p, i)] = v
    for l, row in res["vacua"].items():
        for i, v in enumerate(row):
            out[("vac", l, i)] = v
    return out


def reconstruct(per_prime, primes, n_check):
    """per_prime: {q: {key: residue}}. Use all but n_check primes to reconstruct, the rest to verify."""
    use, chk = primes[:-n_check], primes[-n_check:]
    keys = list(per_prime[primes[0]].keys())
    out, bad = {}, []
    for key in keys:
        x, M = crt_list({q: per_prime[q][key] for q in use}, use)
        f = ratrec(x, M)
        ok = f is not None and all(
            (f.numerator - f.denominator * per_prime[q][key]) % q == 0 for q in chk)
        if not ok:
            bad.append(key)
        out[key] = f
    return out, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--K", type=int, default=16)
    ap.add_argument("--schemes", default="raw,consistent,literal")
    ap.add_argument("--nprimes", type=int, default=40)
    ap.add_argument("--ncheck", type=int, default=6)
    ap.add_argument("--procs", type=int, default=1)
    ap.add_argument("--out", required=True, help="output json (all schemes)")
    a = ap.parse_args()
    t0 = time.time()
    schemes = a.schemes.split(",")
    structs = {0: Structure(a.L, 0, 2 + a.K), 1: Structure(a.L, 1, 3 + a.K)}
    _G.update(structs=structs, L=a.L, K=a.K, schemes=schemes)
    primes = primes_below(1 << 23, a.nprimes + a.ncheck)
    print(f"# structure built in {time.time()-t0:.1f}s; running {len(primes)} primes on {a.procs} procs",
          flush=True)
    per_prime = {s: {} for s in schemes}
    if a.procs > 1:
        import multiprocessing as mp
        ctx = mp.get_context("fork")
        with ctx.Pool(a.procs) as pool:
            for q, res, dt in pool.imap_unordered(worker, primes):
                for s in schemes:
                    per_prime[s][q] = flatten(res[s])
                ndone = sum(1 for _ in per_prime[schemes[0]])
                if ndone in (1, len(primes)) or ndone % 16 == 0:
                    print(f"#   {ndone}/{len(primes)} primes done (last {q}: {dt:.1f}s)", flush=True)
    else:
        for q in primes:
            q, res, dt = worker(q)
            for s in schemes:
                per_prime[s][q] = flatten(res[s])
            print(f"#   prime {q} done in {dt:.1f}s", flush=True)
    final = {}
    for s in schemes:
        rec, bad = reconstruct(per_prime[s], primes, a.ncheck)
        if bad:
            print(f"# WARNING scheme {s}: {len(bad)} quantities failed verification, e.g. {bad[:5]}", flush=True)
        maxdig = max(len(str(abs(f.numerator))) + len(str(f.denominator)) for f in rec.values() if f is not None)
        mod_digits = len(str(np.prod([int(x) for x in primes[:-a.ncheck]], dtype=object)))
        print(f"# scheme {s}: reconstructed, max num+den digits = {maxdig}, modulus digits = {mod_digits}",
              flush=True)
        final[s] = {"bad": [list(map(str, k)) for k in bad],
                    "values": {"|".join(map(str, k)): (str(v) if v is not None else None) for k, v in rec.items()},
                    "max_digits": maxdig}
        for i in range(ORD + 1):
            v = rec[("C", i)]
            print(f"#   {s} C_{i} = {v}  ~ {float(v) if v is not None else None}", flush=True)
    meta = {"L": a.L, "K": a.K, "primes": primes, "nprimes_used": a.nprimes, "ncheck": a.ncheck,
            "n_states": {par: len(structs[par].states) for par in (0, 1)},
            "n_states_full_J0": {par: structs[par].n_full for par in (0, 1)},
            "nnz_V": {par: int(structs[par].ops["V"]["nnz"]) for par in (0, 1)},
            "entries_V": {par: int(structs[par].ops["V"]["n_entries"]) for par in (0, 1)},
            "seconds": time.time() - t0}
    with open(a.out, "w") as f:
        json.dump({"meta": meta, "schemes": final}, f, indent=1)
    print(f"# wrote {a.out}  total {time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
