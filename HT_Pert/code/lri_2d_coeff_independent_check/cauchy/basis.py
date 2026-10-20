"""Fock basis and exact operator structure for the 2D GFF on the unit circle.

Everything here is exact (integers / Fractions); no eps-dependence is evaluated.

Modes m = (a, b), a, b >= 0, level lev_m = a + b, angular momentum J_m = a - b.
States are occupation tuples over the mode list `modes` (index 0 is the zero mode (0,0)).

Basis of one sector (field parity par = P mod 2) at cutoff L with particle cap Pcap:
  J = 0, level N <= L, P <= Pcap, P = par mod 2, reflection-even combinations
  |s>_+ = (|s> + |Rs>)/sqrt(2)  (Rs != s),   |s>_+ = |s>  (Rs == s).
The basis is sorted by (level, P, occupation) so that the cutoff-l basis is a prefix.

Normal-ordered theta-averaged vertex  < :phi^K: >_theta, K = 2 or 4:
  sum_{kc=0}^{K} binom(K,kc) sum_{ordered tuples m1..mK, J(m1..m_kc) = J(m_kc+1..mK)}
      c_m1 ... c_mK  A^dag_m1 ... A^dag_m_kc A_m_kc+1 ... A_mK ,      c_m = sqrt(w_m(x)).
For a multiset C (creators) and D (annihilators) the number of ordered tuples is
  kc!/prod(C mult!) * ka!/prod(D mult!).
A matrix element is stored as   sum_terms (num/den) * sqrt(S) * prod_m c_m^{e_m}
with integers num, den, S and an exponent "monomial" e (tuple of (mode, exponent)).
"""
from fractions import Fraction
from math import factorial, comb
from functools import lru_cache
import pickle, os


def make_modes(L):
    modes = [(0, 0)]
    for n in range(1, L + 1):
        for a in range(n, -1, -1):
            modes.append((a, n - a))
    return modes


class Space:
    """Modes and both parity sectors for cutoff L and particle cap Pcap."""

    def __init__(self, L, Pcap):
        assert L % 2 == 0
        self.L, self.Pcap = L, Pcap
        self.modes = make_modes(L)
        self.nm = len(self.modes)
        self.lev = [a + b for a, b in self.modes]
        self.J = [a - b for a, b in self.modes]
        idx = {m: i for i, m in enumerate(self.modes)}
        self.refl = [idx[(b, a)] for (a, b) in self.modes]
        self._build_states()

    # ---- state utilities -------------------------------------------------
    def R(self, s):
        out = [0] * self.nm
        for i, n in enumerate(s):
            if n:
                out[self.refl[i]] = n
        return tuple(out)

    def canon(self, s):
        rs = self.R(s)
        return min(s, rs)

    def level(self, s):
        return sum(n * self.lev[i] for i, n in enumerate(s) if n)

    def _build_states(self):
        nonzero = list(range(1, self.nm))
        configs = []

        def rec(k, lev, J, cur):
            if k == len(nonzero):
                if J == 0:
                    configs.append(tuple(cur))
                return
            i = nonzero[k]
            c = 0
            while lev + c * self.lev[i] <= self.L:
                rec(k + 1, lev + c * self.lev[i], J + c * self.J[i], cur + [c])
                c += 1

        rec(0, 0, 0, [])
        states = {0: [], 1: []}
        for cf in configs:
            npart = sum(cf)
            for n0 in range(0, self.Pcap - npart + 1):
                s = (n0,) + cf
                if self.canon(s) != s:
                    continue
                P = n0 + npart
                states[P % 2].append(s)
        self.sectors = {}
        for par in (0, 1):
            lst = sorted(states[par], key=lambda s: (self.level(s), sum(s), s))
            self.sectors[par] = {
                'states': lst,
                'index': {s: i for i, s in enumerate(lst)},
                'level': [self.level(s) for s in lst],
                'P': [sum(s) for s in lst],
                'sym': [self.R(s) == s for s in lst],
            }

    def dim(self, par, l=None):
        sec = self.sectors[par]
        if l is None:
            return len(sec['states'])
        return sum(1 for N in sec['level'] if N <= l)

    def ref_index(self, p):
        """index of |p> = (A_00^dag)^p/sqrt(p!)|0> in sector p%2."""
        s = (p,) + (0,) * (self.nm - 1)
        return self.sectors[p % 2]['index'][s]

    # ---- creation multisets ---------------------------------------------
    @lru_cache(maxsize=None)
    def create_sets(self, k, Jt, budget, start=0):
        """all multisets of k modes (indices >= start, nondecreasing) with sum J = Jt and
        sum level <= budget, as tuples of (mode, mult)."""
        if k == 0:
            return [()] if Jt == 0 else []
        out = []
        for i in range(start, self.nm):
            if self.lev[i] > budget:
                continue
            for c in range(1, k + 1):
                if c * self.lev[i] > budget:
                    break
                for rest in self.create_sets(k - c, Jt - c * self.J[i], budget - c * self.lev[i], i + 1):
                    out.append(((i, c),) + rest)
        return out

    # ---- operator application -------------------------------------------
    def apply_vertex(self, s, K):
        """< :phi^K: >_theta acting on the (unsymmetrized, normalized) occupation state s,
        projected on level <= L and P <= Pcap.  Returns list of (target, num, S, mono)
        meaning num * sqrt(S) * prod c^mono |target>  (no 1/12 here)."""
        out = []
        P = sum(s)
        levs = self.level(s)
        occ = [(i, n) for i, n in enumerate(s) if n]
        for kc in range(K + 1):
            ka = K - kc
            if P - ka + kc > self.Pcap:
                continue
            for D in _sub_multisets(occ, ka):
                s1 = list(s)
                Sfac = 1
                Jd = 0
                lev1 = levs
                multD = factorial(ka)
                for i, d in D:
                    n = s1[i]
                    Sfac *= factorial(n) // factorial(n - d)
                    s1[i] = n - d
                    Jd += self.J[i] * d
                    lev1 -= self.lev[i] * d
                    multD //= factorial(d)
                for C in self.create_sets(kc, Jd, self.L - lev1):
                    s2 = list(s1)
                    S2 = Sfac
                    multC = factorial(kc)
                    mono = {}
                    for i, c in C:
                        n = s2[i]
                        S2 *= factorial(n + c) // factorial(n)
                        s2[i] = n + c
                        multC //= factorial(c)
                        mono[i] = mono.get(i, 0) + c
                    for i, d in D:
                        mono[i] = mono.get(i, 0) + d
                    num = comb(K, kc) * multC * multD
                    out.append((tuple(s2), num, S2, tuple(sorted(mono.items()))))
        return out

    def operator(self, par, K):
        """Exact symmetrized matrix of < :phi^K: >_theta in sector par.
        Returns dict (row, col) -> dict mono -> dict S -> Fraction  (value = sum Fraction*sqrt(S)*c^mono)."""
        sec = self.sectors[par]
        index = sec['index']
        mat = {}
        for j, s in enumerate(sec['states']):
            orbit = [s] if sec['sym'][j] else [s, self.R(s)]
            for sp in orbit:
                for (u, num, S, mono) in self.apply_vertex(sp, K):
                    t = self.canon(u)
                    i = index[t]
                    # 1/(n_t n_s) with n = sqrt 2 for non-symmetric states
                    nasym = (0 if sec['sym'][i] else 1) + (0 if sec['sym'][j] else 1)
                    q = Fraction(num)
                    SS = S
                    if nasym == 1:
                        q /= 2
                        SS *= 2
                    elif nasym == 2:
                        q /= 2
                    # reduce sqrt(SS) = k*sqrt(sqfree)
                    k, sf = _sqrt_split(SS)
                    q *= k
                    e = mat.setdefault((i, j), {}).setdefault(mono, {})
                    e[sf] = e.get(sf, 0) + q
        # drop zeros
        clean = {}
        for key, md in mat.items():
            md2 = {}
            for mono, sd in md.items():
                sd2 = {S: q for S, q in sd.items() if q != 0}
                if sd2:
                    md2[mono] = sd2
            if md2:
                clean[key] = md2
        return clean


def _sub_multisets(occ, k):
    """multisets of size k drawn from occupied modes occ=[(i,n)], as tuples (i,d)."""
    if k == 0:
        return [()]
    out = []

    def rec(pos, left, cur):
        if left == 0:
            out.append(tuple(cur))
            return
        if pos == len(occ):
            return
        i, n = occ[pos]
        for d in range(min(n, left), -1, -1):
            rec(pos + 1, left - d, cur + [(i, d)] if d else cur)

    rec(0, k, [])
    return out


@lru_cache(maxsize=None)
def _sqrt_split(n):
    """n = k^2 * sf with sf squarefree."""
    k = 1
    sf = 1
    m = n
    p = 2
    while p * p <= m:
        e = 0
        while m % p == 0:
            m //= p
            e += 1
        k *= p ** (e // 2)
        if e % 2:
            sf *= p
        p += 1
    sf *= m
    return k, sf


def load_or_build(L, Pcap, cache_dir=None):
    """Space plus exact M (K=2) and V (K=4, with the 1/12) structures for both sectors, cached."""
    if cache_dir is not None:
        fn = os.path.join(cache_dir, f"ops_L{L}_P{Pcap}.pkl")
        if os.path.exists(fn):
            with open(fn, 'rb') as f:
                return pickle.load(f)
    sp = Space(L, Pcap)
    ops = {}
    for par in (0, 1):
        M = sp.operator(par, 2)
        V = sp.operator(par, 4)
        for key in V:
            for mono in V[key]:
                for S in V[key][mono]:
                    V[key][mono][S] /= 12
        ops[par] = {'M': M, 'V': V}
    sp.create_sets.cache_clear()
    data = (sp, ops)
    if cache_dir is not None:
        os.makedirs(cache_dir, exist_ok=True)
        tmp = fn + f".tmp{os.getpid()}"
        with open(tmp, 'wb') as f:
            pickle.dump(data, f)
        os.replace(tmp, fn)
    return data
