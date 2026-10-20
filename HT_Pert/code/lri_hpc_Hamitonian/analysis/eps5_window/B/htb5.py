"""Implementation B, eps^5 engine (from scratch, float64; no package code).

H(eps) = N + P/4 - eps P/4 + r(eps) M(eps) + g(eps) V(eps) + X(eps) [diagonal],
M = Pi[C(C+2B)+B^2], V = Pi[(C+B)^4/12] normal ordered, Pi = N-parity projection after a vertex,
C = sum_n u_n(eps) a_n^dag, u_n^2 = ((1-eps)/2)_n/n!.
Basis: sorted mode tuples with 4N+P <= cut4 (cut4 = 4*Lambda, Lambda may be a quarter-integer),
P <= Pmax and (optionally) Q = #nonzero-mode particles <= Qmax.

RS through eps^K (general K), vertices on psi_0..psi_{K-2}, order K via the adjoint (scalar).
Tuning: r_n, g_n on references p=0,1,3: E1-E0=(1-eps)/4, E3-E0=(3+eps)/4.

Capped spaces (Qmax=4, Pmax=7) are used ONLY for paired differences (X-linear through eps^5):
with normal ordering (all B before all C) every ladder intermediate of a C-chain has Q, P and E
no larger than the final state, so vertex matrix elements between capped states are exact.
"""
from __future__ import annotations
import time, copy, math
from fractions import Fraction as Fr
import numpy as np
from numba import njit, prange
import mpmath as mp


# ------------------------------------------------------------------ basis
@njit(cache=True)
def _gen(cut4, Pmax, Qmax, out, P_out, N_out, Q_out, fill):
    cnt = 0
    seq = np.zeros(Pmax + 1, np.int64)
    nxt = np.zeros(Pmax + 2, np.int64)
    P = 0; N = 0; Q = 0
    if fill:
        P_out[cnt] = 0; N_out[cnt] = 0; Q_out[cnt] = 0
    cnt += 1
    while True:
        if P < Pmax:
            n = nxt[P]
            qn = Q + (1 if n > 0 else 0)
            if 4 * (N + n) + P + 1 <= cut4 and qn <= Qmax:
                seq[P] = n; N += n; P += 1; Q = qn; nxt[P] = n
                if fill:
                    for i in range(P):
                        out[cnt, i] = seq[i]
                    P_out[cnt] = P; N_out[cnt] = N; Q_out[cnt] = Q
                cnt += 1
                continue
        if P == 0:
            break
        P -= 1; N -= seq[P]
        if seq[P] > 0:
            Q -= 1
        nxt[P] = seq[P] + 1
    return cnt


@njit(cache=True)
def _keys(modes, P, binom, Pmax):
    d = len(P); k = np.empty(d, np.int64)
    for s in range(d):
        r = 0
        for i in range(P[s]):
            r += binom[modes[s, i] + i, i + 1]
        k[s] = r * (Pmax + 1) + P[s]
    return k


@njit(cache=True)
def _edges(modes, P, N, Q, cut4, Pmax, Qmax, nmax, binom, keys, count_only, rows, cols, mode_of, occ_of):
    d = len(P); e = 0
    tmp = np.empty(Pmax + 1, np.int64)
    for s in range(d):
        p = P[s]
        if p >= Pmax:
            continue
        for n in range(0, nmax + 1):
            if 4 * (N[s] + n) + p + 1 > cut4:
                break
            if n > 0 and Q[s] + 1 > Qmax:
                break
            if not count_only:
                j = 0; occ = 1
                while j < p and modes[s, j] <= n:
                    tmp[j] = modes[s, j]
                    if modes[s, j] == n:
                        occ += 1
                    j += 1
                tmp[j] = n
                for i in range(j, p):
                    tmp[i + 1] = modes[s, i]
                r = 0
                for i in range(p + 1):
                    r += binom[tmp[i] + i, i + 1]
                key = r * (Pmax + 1) + p + 1
                lo = 0; hi = d - 1
                while lo < hi:
                    mid = (lo + hi) // 2
                    if keys[mid] < key:
                        lo = mid + 1
                    else:
                        hi = mid
                if keys[lo] != key:
                    raise ValueError('missing target')
                rows[e] = lo; cols[e] = s; mode_of[e] = n; occ_of[e] = occ
            e += 1
    return e


def binom_table(nmax, kmax):
    b = np.zeros((nmax + 1, kmax + 2), np.int64)
    for n in range(nmax + 1):
        b[n, 0] = 1
        for k in range(1, min(n, kmax + 1) + 1):
            b[n, k] = b[n - 1, k - 1] + (b[n - 1, k] if k <= n - 1 else 0)
    return b


def v_jets_exact(nmodes, K):
    """v_n(eps)=u_n^2=((1-eps)/2)_n/n! Taylor coefficients (exact Fractions), n=0..nmodes-1."""
    v = [Fr(1)] + [Fr(0)] * K
    vs = []
    for n in range(nmodes):
        if n:
            a0 = Fr(2 * n - 1, 2 * n); a1 = Fr(-1, 2 * n)
            v = [a0 * v[k] + (a1 * v[k - 1] if k else 0) for k in range(K + 1)]
        vs.append(list(v))
    return vs


def u_jets(nmodes, K, dps=40):
    vs = v_jets_exact(nmodes, K)
    mp.mp.dps = dps
    U = np.zeros((nmodes, K + 1))
    for n, v in enumerate(vs):
        u = [mp.sqrt(mp.mpf(v[0].numerator) / v[0].denominator)]
        for k in range(1, K + 1):
            vk = mp.mpf(v[k].numerator) / v[k].denominator
            u.append((vk - mp.fsum(u[j] * u[k - j] for j in range(1, k))) / (2 * u[0]))
        U[n] = [float(x) for x in u]
    return U


@njit(cache=True, parallel=True)
def lad_kernel(indptr, idx, mode, occ, Uw, x, deg):
    d = len(indptr) - 1; nx = x.shape[1]; J = Uw.shape[2]
    y = np.zeros((d, deg + 1))
    for r in prange(d):
        for e in range(indptr[r], indptr[r + 1]):
            s = idx[e]; m = mode[e]; o = occ[e]
            for k in range(min(nx, deg + 1)):
                xv = x[s, k]
                if xv != 0.:
                    for j in range(min(J, deg - k + 1)):
                        y[r, k + j] += Uw[m, o, j] * xv
    return y


class Space:
    def __init__(self, cut4, Pmax, Qmax=None, K=5, keep_modes=True):
        t0 = time.time()
        Qmax = Pmax if Qmax is None else Qmax
        self.cut4, self.Pmax, self.Qmax, self.K = cut4, Pmax, Qmax, K
        nmax = cut4 // 4 + 1
        dummy = np.zeros((1, 1), np.int64); d1 = np.zeros(1, np.int64)
        d = _gen(cut4, Pmax, Qmax, dummy, d1, d1, d1, False)
        modes = -np.ones((d, Pmax), np.int16)
        P = np.zeros(d, np.int64); N = np.zeros(d, np.int64); Q = np.zeros(d, np.int64)
        _gen(cut4, Pmax, Qmax, modes, P, N, Q, True)
        binom = binom_table(nmax + Pmax + 2, Pmax + 1)
        keys = _keys(modes, P, binom, Pmax)
        order = np.argsort(keys, kind='stable')
        modes, P, N, Q, keys = modes[order], P[order], N[order], Q[order], keys[order]
        del order
        assert np.all(np.diff(keys) > 0)
        self.dim = d; self.P = P; self.N = N; self.Q = Q; self.keys = keys; self.binom = binom
        self.modes = modes
        self.E4 = 4 * N + P
        z = np.zeros(1, np.int64)
        ne = _edges(modes, P, N, Q, cut4, Pmax, Qmax, nmax, binom, keys, True, z, z, z, z)
        it = np.int32 if d < 2**31 else np.int64
        rows = np.empty(ne, it); cols = np.empty(ne, it)
        mo = np.empty(ne, np.int16); oc = np.empty(ne, np.int8)
        _edges(modes, P, N, Q, cut4, Pmax, Qmax, nmax, binom, keys, False, rows, cols, mo, oc)
        self.nedges = ne
        # edges are generated grouped by source (cols nondecreasing): B-CSR is the natural order
        assert ne == 0 or np.all(np.diff(cols) >= 0)
        self.Bptr = np.zeros(d + 1, np.int64); np.cumsum(np.bincount(cols, minlength=d), out=self.Bptr[1:])
        self.Bidx = rows; self.Bmode = mo; self.Bocc = oc
        perm = np.argsort(rows, kind='stable')
        self.Cptr = np.zeros(d + 1, np.int64); np.cumsum(np.bincount(rows, minlength=d), out=self.Cptr[1:])
        self.Cidx = cols[perm]; self.Cmode = mo[perm]; self.Cocc = oc[perm]
        del cols, perm
        if not keep_modes:
            del self.modes; modes = None
        U = u_jets(nmax + 1, K)
        self.U = U
        self.Uw = np.zeros((nmax + 1, Pmax + 2, K))
        for o in range(Pmax + 2):
            self.Uw[:, o, :] = U[:, :K] * np.sqrt(o)
        self.build_seconds = time.time() - t0

    def index(self, seq):
        seq = sorted(seq); P = len(seq)
        r = sum(int(self.binom[seq[i] + i, i + 1]) for i in range(P))
        key = r * (self.Pmax + 1) + P
        i = int(np.searchsorted(self.keys, key)); assert self.keys[i] == key, seq
        return i

    def Cl(self, y, deg):
        return lad_kernel(self.Cptr, self.Cidx, self.Cmode, self.Cocc, self.Uw, y, deg)

    def Bl(self, y, deg):
        return lad_kernel(self.Bptr, self.Bidx, self.Bmode, self.Bocc, self.Uw, y, deg)

    def vertices(self, x, deg, mask):
        if x.ndim == 1:
            x = x[:, None]
        x = np.ascontiguousarray(x)
        b1 = self.Bl(x, deg); c1 = self.Cl(x, deg)
        m = self.Cl(c1 + 2 * b1, deg)
        v = c1 / 12 + b1 / 3; del c1
        b2 = self.Bl(b1, deg); del b1
        m += b2
        v = self.Cl(v, deg); v += b2 / 2
        b3 = self.Bl(b2, deg); del b2
        v = self.Cl(v, deg); v += b3 / 3
        b4 = self.Bl(b3, deg); del b3
        v = self.Cl(v, deg); v += b4 / 12; del b4
        m[~mask] = 0.; v[~mask] = 0.
        return m, v


# ------------------------------------------------------------------ RS
class St:
    """RS series of a non-degenerate free state s (sector = N parity, E4 <= cut4)."""

    def __init__(self, sp, s, K, cut4=None):
        self.sp = sp; self.s = s; self.K = K
        cut4 = sp.cut4 if cut4 is None else cut4
        self.cut4 = cut4
        self.mask = (sp.N % 2 == sp.N[s] % 2) & (sp.E4 <= cut4)
        den = (sp.E4[s] - sp.E4) / 4.0
        if (self.mask & (den == 0)).sum() != 1:
            raise RuntimeError('degenerate reference in sector')
        self.ok = self.mask & (den != 0)
        self.den = np.where(self.ok, den, 1.0)
        psi0 = np.zeros(sp.dim); psi0[s] = 1.
        self.psi = [psi0]; self.E = [sp.E4[s] / 4.0]
        self.F1 = -sp.P / 4.0
        self.Mj = []; self.Vj = []
        self.vert(0)

    def vert(self, m):
        Mx, Vx = self.sp.vertices(self.psi[m], self.K - 1 - m, self.mask)
        self.Mj.append(Mx); self.Vj.append(Vx)

    def source(self, n, r, g, X):
        t = self.F1 * self.psi[n - 1]
        for m in range(n):
            for j in range(1, n - m + 1):
                if m == 0 and j == n:
                    continue
                l = n - m - j
                if r[j] != 0.: t = t + r[j] * self.Mj[m][:, l]
                if g[j] != 0.: t = t + g[j] * self.Vj[m][:, l]
        if X is not None:
            for m in range(n - 1):
                t = t + X[:, n - m] * self.psi[m]
        t = np.where(self.mask, t, 0.)
        return t

    def source_scalar(self, n, r, g, Xrow):
        """reference component of the order-n source, n = K (vertex on psi_{K-1} via adjoint)."""
        s = self.s
        t = self.F1[s] * self.psi[n - 1][s]
        for m in range(n):
            for j in range(1, n - m + 1):
                if m == 0 and j == n:
                    continue
                l = n - m - j
                if m == n - 1:
                    t += r[j] * float(self.Mj[0][:, 0] @ self.psi[m]) + g[j] * float(self.Vj[0][:, 0] @ self.psi[m])
                else:
                    t += r[j] * self.Mj[m][s, l] + g[j] * self.Vj[m][s, l]
        if Xrow is not None:
            for m in range(n - 1):
                t += Xrow[n - m] * self.psi[m][s]
        return t

    def advance(self, n, t, rn, gn, vertex):
        t = t + rn * self.Mj[0][:, 0] + gn * self.Vj[0][:, 0]
        En = t[self.s]; self.E.append(En)
        for j in range(1, n + 1):
            t = t - self.E[j] * self.psi[n - j]
        self.psi.append(np.where(self.ok, t / self.den, 0.))
        if vertex:
            self.vert(n)

    def fork(self, upto, X):
        new = copy.copy(self)
        new.psi = list(self.psi[:upto + 1]); new.E = list(self.E[:upto + 1])
        new.Mj = list(self.Mj[:upto + 1]); new.Vj = list(self.Vj[:upto + 1])
        if X is not None:
            for k in range(2, upto + 1):
                new.E[k] = self.E[k] + X[self.s, k]   # valid: psi_k (k<=upto) X-independent, X starts at eps^2
        return new

    def M00(self):
        return self.Mj[0][self.s, 0], self.Vj[0][self.s, 0]


def run_orders(states, r, g, X, n_from, K, tune=None, n_to=None):
    """Advance dict of St from order n_from..n_to (default K; order K is scalar).
    tune=(name0,name1,name3) -> solve r_n,g_n."""
    r = np.array(r, float).copy(); g = np.array(g, float).copy()
    n_to = K if n_to is None else n_to
    for n in range(n_from, n_to + 1):
        if n < K:
            tp = {k: st.source(n, r, g, X) for k, st in states.items()}
            raw = {k: tp[k][st.s] for k, st in states.items()}
        else:
            raw = {k: st.source_scalar(n, r, g, None if X is None else X[st.s]) for k, st in states.items()}
        if tune is not None:
            a0, a1, a3 = tune
            rhs1 = (-.25 if n == 1 else 0.); rhs3 = (.25 if n == 1 else 0.)
            # E_p^(n) = raw_p + r_n M_pp + g_n V_pp ; M_pp = 2p, V_pp = p(p-1)/2 for zero-mode refs
            r[n] = (rhs1 - (raw[a1] - raw[a0])) / 2
            g[n] = (rhs3 - (raw[a3] - raw[a0]) - 6 * r[n]) / 3
        for k, st in states.items():
            if n < K:
                st.advance(n, tp[k], r[n], g[n], vertex=(n < K - 1))
            else:
                m0, v0 = st.M00()
                st.E.append(raw[k] + r[n] * m0 + g[n] * v0)
    return r, g


# ------------------------------------------------------------------ diagonal corrections
def bubble_S_table(Lmax, K):
    """S[L][k]: eps^k coefficient of sum_{m even, m+1<=L} w_m(eps)/(m+1-eps), w_m=(2-2eps)_m/m!. Exact."""
    w = [Fr(1)] + [Fr(0)] * K
    run = [Fr(0)] * (K + 1)
    S = [list(run)]
    for m in range(Lmax):
        if m:
            w = [Fr(m + 1, m) * w[k] - (Fr(2, m) * w[k - 1] if k else 0) for k in range(K + 1)]
        if m % 2 == 0:
            den = [Fr(1, (m + 1) ** (j + 1)) for j in range(K + 1)]
            for k in range(K + 1):
                run[k] += sum(w[a] * den[k - a] for a in range(k + 1))
        S.append(list(run))
    return S


def conv(a, b, K):
    out = np.zeros(K + 1)
    for i in range(min(len(a), K + 1)):
        for j in range(min(len(b), K + 1 - i)):
            out[i + j] += a[i] * b[j]
    return out


def g2D_diag(E4, g, cut4, Sf, K):
    """package correction g(eps)^2 D(eps), relative to cutoff cut4/4. E4: array of 4*E0."""
    up = np.maximum(0, (cut4 - E4) // 4); top = cut4 // 4
    D = -(Sf[top][None, :] - Sf[up]) / 6.0
    D[E4 > cut4] = 0.
    gg = conv(g, g, K)
    X = np.zeros((len(E4), K + 1))
    for k in range(K + 1):
        for a in range(k + 1):
            X[:, k] += gg[a] * D[:, k - a]
    return X


def window_W(E4, cut4):
    """#odd integers k in (Lam - E0, Lam], Lam = cut4/4."""
    cnt = lambda x: (x + 1) // 2
    top = cut4 // 4; up = np.maximum(0, (cut4 - E4) // 4)
    return cnt(top) - cnt(up)


def g2D3W_diag(E4, g, cut4, Sf, K):
    X = g2D_diag(E4, g, cut4, Sf, K)
    X[:, 3] += g[1] ** 3 * window_W(E4, cut4)
    return X


def half_index(E4, cut4):
    """index j of the vacuum cutoff L''=j/2 = floor_half(Lam - E0)."""
    return np.maximum(0, (cut4 - E4) // 2)


def table_diag(E4, cut4, table):
    """X_i = Evac(Lam) - Evac(floor_half(Lam-E0_i)); table[j] = Evac(j/2)."""
    jtop = cut4 // 2
    j = half_index(E4, cut4)
    return table[jtop][None, :] - table[j]


# ------------------------------------------------------------------ vacuum
def vacuum_energy(sp8, r, g, K, cut4, X=None):
    s0 = sp8.index([])
    st = St(sp8, s0, K, cut4)
    run_orders({'v': st}, r, g, X, 1, K, tune=None)
    return np.array(st.E)


def vacuum_tables(sp8, r, g, K, Sf, jlist, conn=True, raw=True):
    """E_vac(j/2) for j in jlist, through eps^K. conn: with X_{L''} = [g^2D]_{2,3} + g1^3 W relative to
    L'' on intermediates (the self-consistent Dconn vacuum through eps^5)."""
    out = {}
    for j in jlist:
        c4 = 2 * j
        res = {}
        if raw:
            res['raw'] = vacuum_energy(sp8, r, g, K, c4, None)
        if conn:
            Xc = g2D3W_diag(sp8.E4, g, c4, Sf, K)
            Xc[:, 4:] = 0.
            res['conn'] = vacuum_energy(sp8, r, g, K, c4, Xc)
        out[j] = res
    return out
