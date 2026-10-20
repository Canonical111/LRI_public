"""Implementation B, large-cutoff driver (same Hamiltonian/prescriptions as htb.py).

Differences from htb.py (pure efficiency, verified against htb.py at L<=32):
 * own numba ladder kernel (CSR by target for C, CSR by source for B), jets 0..K-1 only;
 * no vertex on psi_{K-1}: E_K uses <s|V_0|psi_{K-1}> = (V_0 e_s).psi_{K-1} (V_0 symmetric);
 * at eps^4 a diagonal correction X enters only via X^(2) on all rows (identical, = g1^2 D^(0),
   for g2D and both Dfull variants) and X^(2,3,4) on the reference row itself; so Dfull is
   evaluated only at the 5 cutoffs L'' = Lam, Lam-1/2, Lam-1, Lam-3/2, Lam-2 the 7 states need.
"""
from __future__ import annotations
import time, json, sys, gc, copy
import numpy as np
from numba import njit, prange
from htb import _gen, _keys, _edges, binom_table, weight_jets, bubble_S_table, conv

K = 4


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


class BigSpace:
    def __init__(self, L, Pmax, K=K):
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
        del order
        self.dim = d; self.P = P; self.N = N; self.keys = keys; self.binom = binom
        self.E4 = 4 * N + P
        z = np.zeros(1, np.int64)
        ne = _edges(modes, P, N, L, Pmax, binom, keys, True, z, z, z, z)
        rows = np.empty(ne, np.int64); cols = np.empty(ne, np.int64)
        mo = np.empty(ne, np.int64); oc = np.empty(ne, np.int64)
        _edges(modes, P, N, L, Pmax, binom, keys, False, rows, cols, mo, oc)
        del modes
        self.nedges = ne
        it = np.int32 if d < 2**31 else np.int64
        # C: by target row
        perm = np.argsort(rows, kind='stable')
        self.Cptr = np.zeros(d + 1, np.int64); np.cumsum(np.bincount(rows, minlength=d), out=self.Cptr[1:])
        self.Cidx = cols[perm].astype(it); self.Cmode = mo[perm].astype(np.int16); self.Cocc = oc[perm].astype(np.int8)
        # B = C^T: by source (B maps target->source)
        perm = np.argsort(cols, kind='stable')
        self.Bptr = np.zeros(d + 1, np.int64); np.cumsum(np.bincount(cols, minlength=d), out=self.Bptr[1:])
        self.Bidx = rows[perm].astype(it); self.Bmode = mo[perm].astype(np.int16); self.Bocc = oc[perm].astype(np.int8)
        del rows, cols, mo, oc, perm
        U, self.vjets = weight_jets(L + 1, K)
        J = K  # jets 0..K-1 suffice
        self.Uw = np.zeros((L + 1, Pmax + 2, J))
        for o in range(Pmax + 2):
            self.Uw[:, o, :] = U[:, :J] * np.sqrt(o)
        self.build_seconds = time.time() - t0

    def index(self, seq):
        seq = sorted(seq); P = len(seq)
        r = sum(int(self.binom[seq[i] + i, i + 1]) for i in range(P))
        key = r * (self.Pmax + 1) + P
        i = int(np.searchsorted(self.keys, key)); assert self.keys[i] == key
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


class St:
    def __init__(self, sp, s, cut4=None):
        self.sp = sp; self.s = s
        cut4 = 4 * sp.L if cut4 is None else cut4
        self.mask = (sp.N % 2 == sp.N[s] % 2) & (sp.E4 <= cut4)
        den = (sp.E4[s] - sp.E4) / 4.0
        assert (self.mask & (den == 0)).sum() == 1
        self.ok = self.mask & (den != 0)
        self.den = np.where(self.ok, den, 1.0)
        psi0 = np.zeros(sp.dim); psi0[s] = 1.
        self.psi = [psi0]; self.E = [sp.E4[s] / 4.0]
        self.F1 = -sp.P / 4.0
        self.Mj = []; self.Vj = []
        self.vert(0)

    def vert(self, m):
        Mx, Vx = self.sp.vertices(self.psi[m], K - 1 - m, self.mask)
        self.Mj.append(Mx); self.Vj.append(Vx)

    def source(self, n, r, g, X):
        """full order-n source (n<=K-1), excluding r_n,g_n first-order term."""
        t = self.F1 * self.psi[n - 1]
        for m in range(n):
            for j in range(1, n - m + 1):
                if m == 0 and j == n:
                    continue
                l = n - m - j
                if r[j] != 0.: t += r[j] * self.Mj[m][:, l]
                if g[j] != 0.: t += g[j] * self.Vj[m][:, l]
        if X is not None:
            for m in range(n - 1):
                t += X[:, n - m] * self.psi[m]
        t[~self.mask] = 0.
        return t

    def source_scalar(self, n, r, g, Xs):
        """ref component of the order-n source with n=K (no vertex on psi_{K-1}); Xs = X row s."""
        s = self.s
        t = self.F1[s] * self.psi[n - 1][s]
        for m in range(n):
            for j in range(1, n - m + 1):
                if m == 0 and j == n:
                    continue
                l = n - m - j
                if m == n - 1:   # l=0, j=1: use adjoint
                    t += r[j] * float(self.Mj[0][:, 0] @ self.psi[m]) + g[j] * float(self.Vj[0][:, 0] @ self.psi[m])
                else:
                    t += r[j] * self.Mj[m][s, l] + g[j] * self.Vj[m][s, l]
        if Xs is not None:
            for m in range(n - 1):
                t += Xs[n - m] * self.psi[m][s]
        return t

    def advance(self, n, t, rn, gn, vertex):
        t = t + rn * self.Mj[0][:, 0] + gn * self.Vj[0][:, 0]
        En = t[self.s]; self.E.append(En)
        for j in range(1, n + 1):
            t -= self.E[j] * self.psi[n - j]
        self.psi.append(np.where(self.ok, t / self.den, 0.))
        if vertex:
            self.vert(n)

    def fork(self, X):
        new = copy.copy(self)
        new.psi = list(self.psi[:3]); new.E = list(self.E[:3])
        new.Mj = list(self.Mj[:3]); new.Vj = list(self.Vj[:3])
        if X is not None:
            new.E[2] = self.E[2] + X[self.s, 2]
        return new

    def finish(self, r, g, X):
        """from order-2 base: order 3 (no vertex) and the order-4 energy (r,g fixed incl. r4,g4)."""
        st = self.fork(X)
        t = st.source(3, r, g, X); st.advance(3, t, r[3], g[3], False)
        Xs = None if X is None else X[st.s]
        e4 = st.source_scalar(4, r, g, Xs) + r[4] * self.Mj[0][self.s, 0] + g[4] * self.Vj[0][self.s, 0]
        st.E.append(e4)
        return np.array(st.E)


def base(sp, s, r, g, cut4=None):
    st = St(sp, s, cut4)
    for n in (1, 2):
        t = st.source(n, r, g, None); st.advance(n, t, r[n], g[n], True)
    return st


def tune_all(sp, Xs_variants):
    """Tune r,g on refs 0,1,3 through K; r3,g3 shared; r4,g4 per variant.
    Returns r_raw,g_raw (through order 3), per-variant (r4,g4) and ref energies, plus the base states."""
    r = np.zeros(K + 1); g = np.zeros(K + 1)
    refs = {p: St(sp, sp.index([0] * p)) for p in (0, 1, 3)}
    for n in (1, 2, 3):
        tp = {p: refs[p].source(n, r, g, None) for p in refs}
        raw = {p: tp[p][refs[p].s] for p in refs}
        r[n] = ((-.25 if n == 1 else 0.) - (raw[1] - raw[0])) / 2
        g[n] = ((.25 if n == 1 else 0.) - (raw[3] - raw[0]) - 6 * r[n]) / 3
        for p in refs:
            refs[p].advance(n, tp[p], r[n], g[n], n < 3)
    return r, g, refs


def ref_variant(refs, r, g, X):
    """order 3 with X (r3,g3 must be X independent), tuned r4,g4 from scalar order-4 sources."""
    sts = {}
    for p, st in refs.items():
        b = st.fork(X)
        b.psi = b.psi[:3]; b.E = b.E[:3]; b.Mj = b.Mj[:3]; b.Vj = b.Vj[:3]
        t = b.source(3, r, g, X)
        e3 = t[b.s] + r[3] * st.Mj[0][st.s, 0] + g[3] * st.Vj[0][st.s, 0]
        assert abs(e3 - st.E[3]) < 1e-9 * max(1, abs(e3)), (p, e3, st.E[3])
        b.advance(3, t, r[3], g[3], False)
        sts[p] = b
    rr = r.copy(); gg = g.copy()
    raw = {p: sts[p].source_scalar(4, rr, gg, None if X is None else X[sts[p].s]) for p in sts}
    rr[4] = (-(raw[1] - raw[0])) / 2
    gg[4] = (-(raw[3] - raw[0]) - 6 * rr[4]) / 3
    E = {}
    for p, b in sts.items():
        e4 = raw[p] + rr[4] * refs[p].Mj[0][b.s, 0] + gg[4] * refs[p].Vj[0][b.s, 0]
        E[p] = np.array(b.E + [e4])
    return rr, gg, E


def g2D_full(sp, g, cut4, S):
    Sf = np.array([[float(x) for x in row] for row in S])
    up = np.maximum(0, (cut4 - sp.E4) // 4); top = cut4 // 4
    D = -(Sf[top][None, :] - Sf[up]) / 6.0
    D[sp.E4 > cut4] = 0.
    gg = conv(g, g, K)
    X = np.zeros((sp.dim, K + 1))
    for k in range(K + 1):
        for a in range(k + 1):
            X[:, k] += gg[a] * D[:, k - a]
    return X


def vacuum_at(sp8, r, g, j_list, S):
    """E_vac(j/2) raw and conn (g2D relative to j/2) through eps^K, full RS on the P<=8 space."""
    s0 = sp8.index([])
    out = {}
    for j in j_list:
        cut4 = 2 * j
        res = []
        for conn in (False, True):
            X = g2D_full(sp8, g, cut4, S) if conn else None
            st = St(sp8, s0, cut4)
            for n in (1, 2, 3):
                t = st.source(n, r, g, X); st.advance(n, t, r[n], g[n], n < 3)
            e4 = st.source_scalar(4, r, g, None if X is None else X[s0])   # r4,g4 terms vanish on |0>
            res.append(np.array(st.E + [e4]))
        out[j] = res
    return out


STATES = {'p0': [], 'p1': [0], 'p2': [0, 0], 'p3': [0, 0, 0], 'd1': [1], 'd2': [0, 1], 'd3': [0, 0, 1]}


def run(L, verbose=True):
    T = {}; t0 = time.time()
    sp = BigSpace(L, 11); T['build'] = time.time() - t0
    S = bubble_S_table(L + 1, K)
    idx = {k: sp.index(v) for k, v in STATES.items()}
    t = time.time()
    r, g, refs = tune_all(sp, None); T['tune'] = time.time() - t
    # vacuum at needed cutoffs
    t = time.time()
    sp8 = BigSpace(L, 8)
    jneed = sorted({(4 * L - sp.E4[i]) // 2 for i in idx.values()})
    vac = vacuum_at(sp8, r, g, jneed, S)
    dim8 = sp8.dim; del sp8; gc.collect(); T['vac'] = time.time() - t
    # variant diagonals
    Xg = g2D_full(sp, g, 4 * L, S)
    W = {k: int(((L + 1) // 2) - (((4 * L - sp.E4[i]) // 4 + 1) // 2)) for k, i in idx.items()}
    rowvals = {}
    for k, i in idx.items():
        j = (4 * L - sp.E4[i]) // 2
        row_g = Xg[i].copy()
        row_g3 = row_g.copy(); row_g3[3] += g[1] ** 3 * W[k]
        row_dr = vac[2 * L][0] - vac[j][0]
        row_dc = vac[2 * L][1] - vac[j][1]
        rowvals[k] = {'g2D': row_g, 'g2D+g3W': row_g3, 'Dfull_raw': row_dr, 'Dfull_c': row_dc}
        assert abs(row_dr[2] - row_g[2]) < 1e-12 and abs(row_dc[2] - row_g[2]) < 1e-12, (k, row_dr, row_g)
    variants = ['raw', 'g2D', 'g2D+g3W', 'Dfull_raw', 'Dfull_c']
    def Xof(v):
        if v == 'raw':
            return None
        X = Xg.copy()
        for k, i in idx.items():
            X[i] = rowvals[k][v]
        return X
    res = {'L': L, 'dim': sp.dim, 'dim8': dim8, 'nedges': int(sp.nedges), 'r3': r.tolist(), 'g3': g.tolist(), 'W': W,
           'vac': {str(j): [v[0].tolist(), v[1].tolist()] for j, v in vac.items()},
           'rows': {k: {v: x.tolist() for v, x in d.items()} for k, d in rowvals.items()},
           'variants': {}}
    t = time.time()
    tuned = {}
    for v in variants:
        X = Xof(v)
        rr, gg, E = ref_variant(refs, r, g, X)
        tuned[v] = (rr, gg, {'p0': E[0], 'p1': E[1], 'p3': E[3]})
        del X
    del refs; gc.collect(); T['refvar'] = time.time() - t
    t = time.time()
    for k in ('p2', 'd1', 'd2', 'd3'):
        b = base(sp, idx[k], r, g)
        for v in variants:
            X = Xof(v)
            rr, gg, Ed = tuned[v]
            Ed[k] = b.finish(rr, gg, X)
            del X
        del b; gc.collect()
    T['states'] = time.time() - t
    for v in variants:
        rr, gg, E = tuned[v]
        d = {'r': rr.tolist(), 'g': gg.tolist(), 'C': (E['p2'] - E['p0']).tolist(),
             'tune1': (E['p1'] - E['p0']).tolist(), 'tune3': (E['p3'] - E['p0']).tolist(),
             'E': {k: x.tolist() for k, x in E.items()}}
        for p in (1, 2, 3):
            d['spacing_d%d' % p] = (E['d%d' % p] - E['p%d' % p]).tolist()
        res['variants'][v] = d
    T['total'] = time.time() - t0
    res['timing'] = T
    if verbose:
        print(f"L={L} dim={sp.dim} dim8={dim8} edges={sp.nedges} T={ {k: round(x, 1) for k, x in T.items()} }", flush=True)
        for v, d in res['variants'].items():
            print(f"  {v:10s} r4={d['r'][4]:+.12f} g4={d['g'][4]:+.12f} C4={d['C'][4]:.12f} d1={np.array(d['spacing_d1'][2:])} d2={np.array(d['spacing_d2'][2:])} d3={np.array(d['spacing_d3'][2:])}", flush=True)
    return res


if __name__ == '__main__':
    for L in [int(a) for a in sys.argv[1:]]:
        res = run(L)
        json.dump(res, open(f'big_L{L}.json', 'w'), indent=1)
