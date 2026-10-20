#!/usr/bin/env python3
"""
Reference implementation (exact, fractions.Fraction) of the eps-expansion of the 2D long-range Ising
Hamiltonian-truncation problem defined in ../SPEC.md, by plain Rayleigh-Schroedinger (RS) perturbation
theory with full-order wavefunction corrections.

Design (see README.md for the derivation):
  * basis: unnormalised monomials prod_m (B_m^dag)^{n_m}|0> in the FULL J=0 sector (both reflection
    parities; the reflection-odd states are never reached from the reflection-even references, so the
    results equal those of the reflection-even sector), fixed field parity, level N <= L,
    particle number P <= p + K for the channel with reference |p>.
  * similarity frame: phi(theta) = sum_m ( e^{iJ_m theta} B_m^dag + w_m(x) e^{-iJ_m theta} B_m ),
    [B_m, B_m'^dag] = delta.  This is S^{-1} H S with S diagonal in the occupation basis, so all
    eigenvalues are unchanged and all matrix elements are polynomials in eps with rational coefficients.
  * operators are built by literally expanding :phi^k: = sum_c C(k,c) (phi^-)^c (phi^+)^{k-c} over
    ORDERED tuples of modes and applying the ladder operators one by one (no multiset combinatorics).
  * RS: E_n = [sum_{k=1}^n W_k psi_{n-k}]_ref ; psi_n = R Q [sum_k W_k psi_{n-k} - sum_{k<n} E_k psi_{n-k}],
    R = 1/(E^0_ref - H0), intermediate normalisation.  No 2n+1 rule.
"""
from fractions import Fraction as Fr
from math import comb
import argparse, json, os, sys, time

ORD = 8   # highest order in eps that is computed


# ----------------------------------------------------------------------------- eps polynomials
def poly_mul(p, q):
    r = [Fr(0)] * (ORD + 1)
    for i, a in enumerate(p):
        if a:
            for j in range(ORD + 1 - i):
                b = q[j]
                if b:
                    r[i + j] += a * b
    return r


def poch_over_fact(a):
    """(x)_a / a! with x = 1/2 - eps/4, as a list of eps-Taylor coefficients 0..ORD (exact)."""
    p = [Fr(1)] + [Fr(0)] * ORD
    for i in range(a):
        # factor (x + i)/(i+1) = ((2i+1)/2 - eps/4)/(i+1)
        f = [Fr(0)] * (ORD + 1)
        f[0] = Fr(2 * i + 1, 2 * (i + 1))
        f[1] = Fr(-1, 4 * (i + 1))
        p = poly_mul(p, f)
    return p


# ----------------------------------------------------------------------------- modes and states
class Space:
    """J=0 Fock states of fixed field parity with level <= L and P <= Pmax (unnormalised monomials)."""

    def __init__(self, L, parity, Pmax):
        self.L, self.parity, self.Pmax = L, parity, Pmax
        self.modes = [(a, n - a) for n in range(L + 1) for a in range(n + 1)]
        self.midx = {m: i for i, m in enumerate(self.modes)}
        self.lev = [a + b for (a, b) in self.modes]
        self.J = [a - b for (a, b) in self.modes]
        self.w = [poly_mul(poch_over_fact(a), poch_over_fact(b)) for (a, b) in self.modes]
        states = []
        nz = [i for i in range(len(self.modes)) if self.lev[i] > 0]

        def rec(pos, lev, J, P, occ):
            if pos == len(nz):
                if J != 0:
                    return
                for n0 in range(0, Pmax - P + 1):
                    if (P + n0) % 2 != parity:
                        continue
                    st = dict(occ)
                    if n0:
                        st[0] = n0
                    states.append(tuple(sorted(st.items())))
                return
            i = nz[pos]
            k = 0
            while lev + k * self.lev[i] <= L and P + k <= Pmax:
                if k:
                    occ[i] = k
                rec(pos + 1, lev + k * self.lev[i], J + k * self.J[i], P + k, occ)
                k += 1
            occ.pop(i, None)

        rec(0, 0, 0, 0, {})
        self.states = states
        self.index = {s: i for i, s in enumerate(states)}
        self.level = [sum(self.lev[m] * c for m, c in s) for s in states]
        self.P = [sum(c for m, c in s) for s in states]

    def ref_index(self, p):
        return self.index[((0, p),) if p else ()]


def ordered_creation_tuples(sp, kmax):
    """dict k -> dict J -> list of (level, tuple_of_mode_indices) for ordered k-tuples, level <= L."""
    out = {}
    for k in range(kmax + 1):
        d = {}

        def rec(t, lev, J):
            if len(t) == k:
                d.setdefault(J, []).append((lev, tuple(t)))
                return
            for i in range(len(sp.modes)):
                if lev + sp.lev[i] <= sp.L:
                    t.append(i)
                    rec(t, lev + sp.lev[i], J + sp.J[i])
                    t.pop()

        rec([], 0, 0)
        out[k] = d
    return out


def build_vertex(sp, kpow, prefactor, ctup):
    """Matrix of prefactor * <:phi^kpow:>_theta in the monomial frame, as column lists.
    Returns cols[i] = list of (row, poly).  Entries leaving the space (level > L or P > Pmax) dropped."""
    nst = len(sp.states)
    cols = []
    for i, s in enumerate(sp.states):
        occ = dict(s)
        N = sp.level[i]
        P = sp.P[i]
        acc = {}
        for kc in range(kpow + 1):          # number of creation operators
            ka = kpow - kc                   # number of annihilation operators
            if P - ka + kc > sp.Pmax or ka > P:
                continue
            base = Fr(comb(kpow, kc)) * prefactor
            # ordered annihilation tuples, applied right-to-left (order irrelevant for the coefficient)
            occ_modes = list(occ.keys())

            def ann_rec(t, cnt, coef, wpoly, Jann, levann):
                if len(t) == ka:
                    budget = sp.L - (N - levann)
                    for (lc, ct) in ctup[kc].get(Jann, ()):
                        if lc > budget:
                            continue
                        new = dict(cnt)
                        for m in ct:
                            new[m] = new.get(m, 0) + 1
                        tgt = tuple(sorted((m, c) for m, c in new.items() if c))
                        j = sp.index.get(tgt)
                        if j is None:
                            continue
                        val = [coef * a for a in wpoly]
                        if j in acc:
                            prev = acc[j]
                            acc[j] = [x + y for x, y in zip(prev, val)]
                        else:
                            acc[j] = val
                    return
                for m in occ_modes:
                    c = cnt.get(m, 0)
                    if c == 0:
                        continue
                    cnt2 = dict(cnt)
                    cnt2[m] = c - 1
                    t.append(m)
                    ann_rec(t, cnt2, coef * c, poly_mul(wpoly, sp.w[m]), Jann + sp.J[m], levann + sp.lev[m])
                    t.pop()

            ann_rec([], dict(occ), base, [Fr(1)] + [Fr(0)] * ORD, 0, 0)
        cols.append([(j, pol) for j, pol in acc.items() if any(pol)])
    return cols


# ----------------------------------------------------------------------------- RS machinery
class Channel:
    """Reference state |p> at cutoff l in a given parity space, with a diagonal correction D(N)."""

    def __init__(self, name, sp, ops, p, l, K, Dfun):
        self.name, self.sp, self.ops, self.p, self.l = name, sp, ops, p, l
        self.ref = sp.ref_index(p)
        self.allowed = [sp.level[i] <= l and sp.P[i] <= p + K for i in range(len(sp.states))]
        self.E0ref = Fr(p, 2)
        self.H0 = [sp.level[i] + Fr(sp.P[i], 2) for i in range(len(sp.states))]
        self.Dfun = Dfun          # Dfun(k, N) -> eps^k coefficient of D at level N (k >= 1)
        self.psi = [{self.ref: Fr(1)}]
        self.E = [self.E0ref]

    def matvec(self, opname, j, vec):
        cols = self.ops[opname]
        out = {}
        al = self.allowed
        for c, v in vec.items():
            for (r, pol) in cols[c]:
                a = pol[j]
                if a and al[r]:
                    out[r] = out.get(r, 0) + v * a
        return out

    def rhs_without_new(self, n, r, g):
        """sum_{k=1}^n W_k psi_{n-k} - sum_{k=1}^{n-1} E_k psi_{n-k}, with r_n = g_n = 0 in W_n."""
        sp = self.sp
        out = {}

        def add(d, s=1):
            for k_, v in d.items():
                out[k_] = out.get(k_, 0) + s * v

        # vertex parts: W_k contains sum_{j=0}^{k-1} (r_{k-j} M_j + g_{k-j} V_j)
        for j in range(0, n):
            # u = sum_{k=j+1}^{n} c_{k-j} psi_{n-k}, excluding the (k=n, j=0) term (unknown r_n, g_n)
            for opname, coef in (("M", r), ("V", g)):
                u = {}
                for k in range(j + 1, n + 1):
                    if k == n and j == 0:
                        continue
                    c = coef[k - j]
                    if c == 0:
                        continue
                    for idx, v in self.psi[n - k].items():
                        u[idx] = u.get(idx, 0) + c * v
                if u:
                    add(self.matvec(opname, j, u))
        # -P/4 in W_1
        for idx, v in self.psi[n - 1].items():
            out[idx] = out.get(idx, 0) - Fr(sp.P[idx], 4) * v
        # D_k psi_{n-k}, k = 1..n (D_n psi_0 = D_n(0) psi_0 = 0 but keep it general)
        for k in range(1, n + 1):
            for idx, v in self.psi[n - k].items():
                d = self.Dfun(k, sp.level[idx])
                if d:
                    out[idx] = out.get(idx, 0) + d * v
        # - sum_{k=1}^{n-1} E_k psi_{n-k}
        for k in range(1, n):
            for idx, v in self.psi[n - k].items():
                out[idx] = out.get(idx, 0) - self.E[k] * v
        return out

    def finish_order(self, n, rhs0, rn, gn):
        rhs = dict(rhs0)
        for opname, c in (("M", rn), ("V", gn)):
            if c:
                for idx, v in self.matvec(opname, 0, {self.ref: Fr(1)}).items():
                    rhs[idx] = rhs.get(idx, 0) + c * v
        En = rhs.get(self.ref, Fr(0))
        psi = {}
        for idx, v in rhs.items():
            if idx == self.ref or v == 0:
                continue
            psi[idx] = v / (self.E0ref - self.H0[idx])
        self.E.append(En)
        self.psi.append(psi)
        return En


def run(L, scheme, K, verbose=True):
    t0 = time.time()
    spaces, ops = {}, {}
    for par in (0, 1):
        pmax_ref = 2 if par == 0 else 3
        sp = Space(L, par, pmax_ref + K)
        ctup = ordered_creation_tuples(sp, 4)
        ops[par] = {"M": build_vertex(sp, 2, Fr(1), ctup), "V": build_vertex(sp, 4, Fr(1, 12), ctup)}
        spaces[par] = sp
        if verbose:
            nnz = sum(len(c) for c in ops[par]["V"])
            print(f"# L={L} parity={par}: {len(sp.states)} states, V nnz={nnz}, t={time.time()-t0:.1f}s",
                  flush=True)

    ls = list(range(0, L + 1, 2))
    Ev = {}         # vacuum series per l (consistent: consistent vacua; literal: raw vacua)
    zero = lambda k, N: 0

    def make_D(l, vac):
        def D(k, N):
            if N == 0 or k >= len(vac[l]):
                return 0
            return vac[l][k] - vac[l - N][k]
        return D

    chans = {}
    if scheme == "raw":
        for p in range(4):
            chans[("p", p)] = Channel(f"p{p}", spaces[p % 2], ops[p % 2], p, L, K, zero)
    elif scheme == "consistent":
        for l in ls:
            chans[("v", l)] = Channel(f"vac{l}", spaces[0], ops[0], 0, l, K, make_D(l, Ev))
        chans[("p", 0)] = chans[("v", L)]
        for p in (1, 2, 3):
            chans[("p", p)] = Channel(f"p{p}", spaces[p % 2], ops[p % 2], p, L, K, make_D(L, Ev))
    elif scheme == "literal":
        for l in ls:
            chans[("v", l)] = Channel(f"rawvac{l}", spaces[0], ops[0], 0, l, K, zero)
        for p in range(4):
            chans[("p", p)] = Channel(f"p{p}", spaces[p % 2], ops[p % 2], p, L, K, make_D(L, Ev))
    else:
        raise ValueError(scheme)
    for l in ls:
        Ev[l] = [Fr(0)]

    r = [Fr(0)] * (ORD + 1)
    g = [Fr(0)] * (ORD + 1)
    xser = [Fr(1, 2), Fr(-1, 4)] + [Fr(0)] * (ORD - 1)
    C = [Fr(1)]
    uniq = []
    for ch in chans.values():
        if ch not in uniq:
            uniq.append(ch)
    for n in range(1, ORD + 1):
        rhs0 = {id(ch): ch.rhs_without_new(n, r, g) for ch in uniq}
        X = {p: rhs0[id(chans[("p", p)])].get(chans[("p", p)].ref, Fr(0)) for p in range(4)}
        # E_p^(n) = X_p + 2p r_n + p(p-1)/2 g_n
        rn = (xser[n] - X[1] + X[0]) / 2
        gn = (-xser[n] - X[3] + X[0] - 6 * rn) / 3
        r[n], g[n] = rn, gn
        for ch in uniq:
            ch.finish_order(n, rhs0[id(ch)], rn, gn)
        if scheme in ("consistent", "literal"):
            for l in ls:
                Ev[l].append(chans[("v", l)].E[n])
        E = {p: chans[("p", p)].E[n] for p in range(4)}
        assert E[1] - E[0] == xser[n] and E[3] - E[0] == -xser[n] + (Fr(2) if n == 0 else 0)
        C.append(E[2] - E[0])
        if verbose:
            print(f"# order {n}: C_{n} = {C[n]} = {float(C[n]):.15g}   t={time.time()-t0:.1f}s", flush=True)
    res = {
        "scheme": scheme, "L": L, "K": K,
        "C": [str(c) for c in C],
        "r": [str(c) for c in r], "g": [str(c) for c in g],
        "E": [[str(e) for e in chans[("p", p)].E] for p in range(4)],
        "vacua": ({str(l): [str(e) for e in chans[("v", l)].E] for l in ls}
                  if scheme != "raw" else {str(L): [str(e) for e in chans[("p", 0)].E]}),
    }
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--scheme", required=True, choices=["raw", "consistent", "literal"])
    ap.add_argument("--K", type=int, default=16, help="particle cap relative to reference: P <= p + K")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = run(a.L, a.scheme, a.K)
    js = json.dumps(res, indent=1)
    if a.out:
        with open(a.out, "w") as f:
            f.write(js)
    else:
        print(js)
