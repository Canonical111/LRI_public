"""Implementation B: from-scratch Fock-space HT for the d=1 LRI (eps expansion).

H(eps) = N + P/4 - eps P/4 + r(eps) M(eps) + g(eps) V(eps) [+ X(eps) diagonal],
M = Pi[C(C+2B)+B^2], V = Pi[(C+B)^4/12] normal ordered (all C left of all B),
Pi = projection onto the N-parity sector of the state after each complete vertex,
C = sum_n u_n(eps) a_n^dag, u_n^2 = ((1-eps)/2)_n/n!, basis 4N+P <= 4*Lam, P <= Pmax.
Orthonormal Fock basis, float64, scipy sparse ladders. No package code used.
"""
from __future__ import annotations
import math, time
from fractions import Fraction as Fr
import numpy as np
import scipy.sparse as sps
from numba import njit
import mpmath as mp

# ---------------------------------------------------------------- basis
@njit(cache=True)
def _gen(L, Pmax, out, P_out, N_out, fill):
    cnt = 0
    seq = np.zeros(Pmax + 1, np.int64)
    nxt = np.zeros(Pmax + 2, np.int64)
    P = 0; N = 0
    if fill:
        P_out[cnt] = 0; N_out[cnt] = 0
    cnt += 1
    while True:
        if P < Pmax:
            n = nxt[P]
            if 4 * (N + n) + P + 1 <= 4 * L:
                seq[P] = n; N += n; P += 1; nxt[P] = n
                if fill:
                    for i in range(P):
                        out[cnt, i] = seq[i]
                    P_out[cnt] = P; N_out[cnt] = N
                cnt += 1
                continue
        if P == 0:
            break
        P -= 1; N -= seq[P]; nxt[P] = seq[P] + 1
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
def _edges(modes, P, N, L, Pmax, binom, keys, count_only, rows, cols, mode_of, occ_of):
    d = len(P); e = 0
    tmp = np.empty(Pmax + 1, np.int64)
    for s in range(d):
        p = P[s]
        if p >= Pmax:
            continue
        for n in range(0, L + 1):
            if 4 * (N[s] + n) + p + 1 > 4 * L:
                break
            if not count_only:
                # insert n into sorted sequence
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


def weight_jets(nmodes, K, dps=40):
    """u_n(eps) Taylor coefficients (float) and v_n(eps)=u_n^2 exact (Fractions)."""
    v = [Fr(1)] + [Fr(0)] * K
    vs = []
    for n in range(nmodes):
        if n:
            # v_n = v_{n-1} * (n - 1/2 - eps/2)/n
            a0 = Fr(2 * n - 1, 2 * n); a1 = Fr(-1, 2 * n)
            v = [a0 * v[k] + (a1 * v[k - 1] if k else 0) for k in range(K + 1)]
        vs.append(list(v))
    mp.mp.dps = dps
    U = np.zeros((nmodes, K + 1))
    for n, v in enumerate(vs):
        u = [mp.sqrt(mp.mpf(v[0].numerator) / v[0].denominator)]
        for k in range(1, K + 1):
            vk = mp.mpf(v[k].numerator) / v[k].denominator
            u.append((vk - mp.fsum(u[j] * u[k - j] for j in range(1, k))) / (2 * u[0]))
        U[n] = [float(x) for x in u]
    return U, vs


class Space:
    def __init__(self, L, Pmax, K):
        t0 = time.time()
        self.L, self.Pmax, self.K = L, Pmax, K
        dummy = np.zeros((1, 1), np.int64); d1 = np.zeros(1, np.int64)
        d = _gen(L, Pmax, dummy, d1, d1, False)
        modes = -np.ones((d, Pmax), np.int64); P = np.zeros(d, np.int64); N = np.zeros(d, np.int64)
        _gen(L, Pmax, modes, P, N, True)
        binom = binom_table(L + Pmax + 2, Pmax + 1)
        keys = _keys(modes, P, binom, Pmax)
        order = np.argsort(keys, kind='stable')
        modes, P, N, keys = modes[order], P[order], N[order], keys[order]
        assert np.all(np.diff(keys) > 0)
        self.dim = d; self.modes = modes; self.P = P; self.N = N; self.keys = keys
        self.E4 = 4 * N + P                      # 4*E0 (integer)
        self.E0 = N + P / 4.0
        z = np.zeros(1, np.int64)
        ne = _edges(modes, P, N, L, Pmax, binom, keys, True, z, z, z, z)
        rows = np.empty(ne, np.int64); cols = np.empty(ne, np.int64)
        mo = np.empty(ne, np.int64); oc = np.empty(ne, np.int64)
        _edges(modes, P, N, L, Pmax, binom, keys, False, rows, cols, mo, oc)
        U, self.vjets = weight_jets(L + 1, K)
        self.U = U
        perm = np.lexsort((cols, rows))
        rows, cols, mo, oc = rows[perm], cols[perm], mo[perm], oc[perm]
        indptr = np.zeros(d + 1, np.int64)
        np.cumsum(np.bincount(rows, minlength=d), out=indptr[1:])
        sq = np.sqrt(oc.astype(float))
        self.C = []; self.B = []
        for j in range(K + 1):
            data = U[mo, j] * sq
            Cj = sps.csr_matrix((data, cols.copy(), indptr.copy()), shape=(d, d))
            self.C.append(Cj)
            self.B.append(Cj.T.tocsr())
        self.nedges = ne
        self.build_seconds = time.time() - t0

    def index(self, seq):
        seq = sorted(seq); P = len(seq)
        binom = binom_table(self.L + self.Pmax + 2, self.Pmax + 1)
        r = sum(int(binom[seq[i] + i, i + 1]) for i in range(P))
        key = r * (self.Pmax + 1) + P
        i = int(np.searchsorted(self.keys, key))
        assert self.keys[i] == key
        return i

    # jet ladder: Z_k = sum_j A_j Y_{k-j}
    def lad(self, mats, Y, deg):
        Z = np.zeros((self.dim, deg + 1))
        dY = Y.shape[1] - 1
        for j in range(deg + 1):
            w = min(dY, deg - j)
            if w < 0:
                continue
            Z[:, j:j + w + 1] += mats[j] @ Y[:, :w + 1]
        return Z

    def vertices(self, x, deg, mask):
        """x: dim x (d+1) jets. Returns (M x, V x) jets to degree deg, projected by mask."""
        if x.ndim == 1:
            x = x[:, None]
        B = lambda y: self.lad(self.B, y, deg)
        C = lambda y: self.lad(self.C, y, deg)
        b1 = B(x); c1 = C(x)
        m = C(c1 + 2 * b1)
        v = c1 / 12 + b1 / 3
        b2 = B(b1)
        m += b2
        v = C(v) + b2 / 2
        b3 = B(b2)
        v = C(v) + b3 / 3
        b4 = B(b3)
        v = C(v) + b4 / 12
        m[~mask] = 0.; v[~mask] = 0.
        return m, v


# ---------------------------------------------------------------- exact bubble jets
def bubble_S_table(Lmax, K):
    """S[L][k]: eps^k coefficient of sum_{m even, m+1<=L} w_m(eps)/(m+1-eps), w_m=(2-2eps)_m/m!.
    Exact Fractions; S[L] for integer L=0..Lmax."""
    w = [Fr(1)] + [Fr(0)] * K
    run = [Fr(0)] * (K + 1)
    S = [list(run)]
    for m in range(Lmax):
        if m:
            # w_m = w_{m-1} (m+1-2 eps)/m
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


def g2D_diag(sp, g, cut4, Ssub=None, K=None):
    """Package-isolated correction X = g(eps)^2 D(eps) relative to cutoff with 4*cut = cut4.
    D_i = -(S(floor(cut)) - S(floor(cut - E0_i)))/6. Returns dim x (K+1)."""
    K = sp.K if K is None else K
    S = bubble_S_table(sp.L + 1, K) if Ssub is None else Ssub
    Sf = np.array([[float(x) for x in row] for row in S])
    up = np.maximum(0, (cut4 - sp.E4) // 4)
    top = cut4 // 4
    D = -(Sf[top][None, :] - Sf[up]) / 6.0
    D[sp.E4 > cut4] = 0.
    gg = conv(g, g, K)
    X = np.zeros((sp.dim, K + 1))
    for k in range(K + 1):
        for a in range(k + 1):
            X[:, k] += gg[a] * D[:, k - a]
    return X


# ---------------------------------------------------------------- RS
class RSState:
    """RS series for a non-degenerate free state s in its N-parity sector (within an optional cutoff cut4)."""

    def __init__(self, sp, s, K, cut4=None):
        self.sp, self.s, self.K = sp, s, K
        cut4 = 4 * sp.L if cut4 is None else cut4
        self.mask = (sp.N % 2 == sp.N[s] % 2) & (sp.E4 <= cut4)
        den = (sp.E4[s] - sp.E4) / 4.0
        deg = self.mask & (den == 0)
        if deg.sum() != 1:
            raise RuntimeError('degenerate reference in sector')
        self.ok = self.mask & (den != 0)
        self.den = np.where(self.ok, den, 1.0)
        psi0 = np.zeros(sp.dim); psi0[s] = 1.0
        self.psi = [psi0]
        self.E = [sp.E4[s] / 4.0]
        self.Mj = []; self.Vj = []
        self.F1 = -sp.P / 4.0
        self._vert(0)

    def _vert(self, m):
        deg = self.K - 1 - m
        if deg < 0:
            self.Mj.append(None); self.Vj.append(None); return
        Mx, Vx = self.sp.vertices(self.psi[m], deg, self.mask)
        self.Mj.append(Mx); self.Vj.append(Vx)

    def source(self, n, r, g, X):
        """Order-n RS source excluding r_n M_0 psi_0 + g_n V_0 psi_0."""
        t = self.F1 * self.psi[n - 1]
        for m in range(n):
            for j in range(1, n - m + 1):
                if m == 0 and j == n:
                    continue
                l = n - m - j
                if r[j] != 0.:
                    t = t + r[j] * self.Mj[m][:, l]
                if g[j] != 0.:
                    t = t + g[j] * self.Vj[m][:, l]
        if X is not None:
            for m in range(n - 1):
                t = t + X[:, n - m] * self.psi[m]
        t = np.where(self.mask, t, 0.)
        return t

    def ref0(self):
        return self.Mj[0][self.s, 0], self.Vj[0][self.s, 0]

    def advance(self, n, t_partial, rn, gn, need_vertex=True):
        t = t_partial + rn * self.Mj[0][:, 0] + gn * self.Vj[0][:, 0]
        En = t[self.s]
        self.E.append(En)
        for j in range(1, n + 1):
            t = t - self.E[j] * self.psi[n - j]
        psi = np.where(self.ok, t / self.den, 0.)
        self.psi.append(psi)
        if need_vertex:
            self._vert(n)
        else:
            self.Mj.append(None); self.Vj.append(None)
        return En


def tune(sp, K, X=None, base=None, cut4=None):
    """Calibrate r_k, g_k on refs p=0,1,3 (zero-mode states). Returns r, g, dict of RSState.
    If base=(r,g,states) is given and X only acts from order kX on, reuse lower orders (not used)."""
    refs = {p: RSState(sp, sp.index([0] * p), K, cut4) for p in (0, 1, 3)}
    r = np.zeros(K + 1); g = np.zeros(K + 1)
    for n in range(1, K + 1):
        tp = {p: refs[p].source(n, r, g, X) for p in refs}
        raw = {p: tp[p][refs[p].s] for p in refs}
        r[n] = ((-.25 if n == 1 else 0.) - (raw[1] - raw[0])) / 2
        g[n] = ((.25 if n == 1 else 0.) - (raw[3] - raw[0]) - 6 * r[n]) / 3
        for p in refs:
            refs[p].advance(n, tp[p], r[n], g[n], need_vertex=(n < K))
    return r, g, refs


def run_state(sp, s, K, r, g, X=None, cut4=None):
    st = RSState(sp, s, K, cut4)
    for n in range(1, K + 1):
        t = st.source(n, r, g, X)
        st.advance(n, t, r[n], g[n], need_vertex=(n < K))
    return st


# ---------------------------------------------------------------- vacuum tables and Dfull
def vacuum_tables(L, K, r, g, sp8=None, S=None):
    """E_vac(L'') for L''=j/2, j=0..2L, through eps^K, at fixed r,g.
    raw: plain truncated vacuum energy; conn: with g^2 D relative to L'' (removes
    the vacuum's own unlinked bubble-bubble window; equals the self-consistent
    Dfull vacuum through eps^4)."""
    if sp8 is None:
        sp8 = Space(L, 8, K)
    if S is None:
        S = bubble_S_table(L + 1, K)
    s0 = sp8.index([])
    raw = np.zeros((2 * L + 1, K + 1)); conn = np.zeros((2 * L + 1, K + 1))
    for j in range(2 * L + 1):
        cut4 = 2 * j
        a = run_state(sp8, s0, K, r, g, None, cut4)
        raw[j] = a.E
        Xc = g2D_diag(sp8, g, cut4, S, K)
        b = run_state(sp8, s0, K, r, g, Xc, cut4)
        conn[j] = b.E
    return raw, conn, sp8


def dfull_diag(sp, table):
    """X_i = Evac(Lam) - Evac(Lam - E0_i), Evac at quarter-integer cutoff = Evac at floor to half-integer."""
    L = sp.L
    j = (4 * L - sp.E4) // 2          # L'' = j/2 = floor(2(L-E0))/2
    j = np.clip(j, 0, 2 * L)
    X = table[2 * L][None, :] - table[j]
    return X


def window_W(sp):
    """W_i = #{odd k in (Lam - E0_i, Lam]} (count of truncated even bubble shells)."""
    L = sp.L
    up = (4 * L - sp.E4) // 4   # floor(Lam - E0)
    # odd k with up < k <= L
    cnt = lambda x: (x + 1) // 2   # number of odd k in [1, x]
    return cnt(L) - cnt(up)


# ---------------------------------------------------------------- forking (X enters from eps^2, diagonal)
import copy as _copy

def fork(st, X, upto=2):
    """Copy an RSState after order `upto` (orders <=2 of psi are X-independent for diagonal X
    starting at eps^2); patch E_2 by X_{2,s}."""
    new = _copy.copy(st)
    new.psi = list(st.psi[:upto + 1]); new.E = list(st.E[:upto + 1])
    new.Mj = list(st.Mj[:upto + 1]); new.Vj = list(st.Vj[:upto + 1])
    if X is not None and upto >= 2:
        new.E[2] = st.E[2] + X[st.s, 2]
    return new


def base_states(sp, K, r_low, g_low, states):
    """Raw RS states through order 2 (shared), r_low/g_low used for orders 1,2."""
    out = {}
    for name, s in states.items():
        st = RSState(sp, s, K)
        for n in (1, 2):
            t = st.source(n, r_low, g_low, None)
            st.advance(n, t, r_low[n], g_low[n], need_vertex=True)
        out[name] = st
    return out


def finish(base, K, r, g, X, tune_refs=True):
    """Continue all states from order 3 with correction X; tune r_n,g_n (n>=3) on refs 0,1,3."""
    r = r.copy(); g = g.copy()
    sts = {k: fork(v, X) for k, v in base.items()}
    for p in ('p0', 'p1', 'p3'):
        if X is not None:
            assert abs(X[sts[p].s, 2]) < 1e-15, 'X_2 nonzero on a reference'
    for n in range(3, K + 1):
        tp = {k: v.source(n, r, g, X) for k, v in sts.items()}
        if tune_refs:
            raw = {p: tp['p%d' % p][sts['p%d' % p].s] for p in (0, 1, 3)}
            r[n] = (-(raw[1] - raw[0])) / 2
            g[n] = (-(raw[3] - raw[0]) - 6 * r[n]) / 3
        for k, v in sts.items():
            v.advance(n, tp[k], r[n], g[n], need_vertex=(n < K))
    return r, g, sts
