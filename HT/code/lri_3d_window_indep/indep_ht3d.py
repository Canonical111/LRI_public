"""Clean-room re-implementation of the 3D dressed-window HT finite model.

Written from the physics definition only (docs/METHOD.md formulas, re-derived),
without reading or importing the package's ht3d code.  Deliberate method
differences from the package:
  * complex Condon-Shortley Y_lm Fock space with all magnetic sectors;
  * J=0 bath space from the null space of the Casimir J^2 = J_- J_+ (dense eigh
    per species-occupation block of the M=0 sector), not an SVD null space;
  * scalar vertices <:B^k:> evaluated at an arbitrary generic sphere point
    (valid on J=0 states by rotation invariance) and checked at a second point;
  * local zero mode in a plain number-state basis, truncated to the K lowest
    eigenstates of the current local Hamiltonian (no trained density basis);
  * window fixed points by bracketed Brent root finding; tuning by scipy root.
"""
import math, itertools, time, sys, json
from collections import Counter
import numpy as np
import scipy.sparse as sp
import scipy.linalg as sla
import scipy.sparse.linalg as spla
from scipy.special import sph_harm_y, poch, gammaln
from scipy.optimize import brentq, root


# ---------------------------------------------------------------- modes
def u2(x, n, l):
    return poch(x, n + l) * poch(x - 0.5, n) / (math.factorial(n) * poch(1.5, n + l))


def mode_list(L):
    """All positive bath modes (n,l,m) with 1 <= 2n+l <= L."""
    modes = []
    for k in range(1, L + 1):
        for l in range(k % 2, k + 1, 2):
            n = (k - l) // 2
            for m in range(-l, l + 1):
                modes.append((n, l, m))
    return modes


# ---------------------------------------------------------------- Fock space
class Fock:
    """Bath Fock states with N_b = sum(2n+l) <= L; a state is a sorted tuple of mode indices."""

    def __init__(self, L):
        self.L = L
        self.modes = mode_list(L)
        self.lev = np.array([2 * n + l for n, l, m in self.modes])
        self.mm = np.array([m for n, l, m in self.modes])
        states = []

        def rec(start, budget, cur):
            states.append(tuple(cur))
            for i in range(start, len(self.modes)):
                if self.lev[i] <= budget:
                    cur.append(i)
                    rec(i, budget - self.lev[i], cur)
                    cur.pop()
        rec(0, L, [])
        self.states = states
        self.index = {s: j for j, s in enumerate(states)}
        self.N = np.array([sum(self.lev[i] for i in s) for s in states])
        self.M = np.array([sum(self.mm[i] for i in s) for s in states])
        self.P = np.array([len(s) for s in states])

    def annihilator(self, coef):
        """Sparse matrix of sum_i coef[i] a_i over the whole truncated space."""
        rows, cols, vals = [], [], []
        for j, s in enumerate(self.states):
            for i in set(s):
                occ = s.count(i)
                t = list(s)
                t.remove(i)
                rows.append(self.index[tuple(t)])
                cols.append(j)
                vals.append(coef[i] * math.sqrt(occ))
        n = len(self.states)
        return sp.csr_matrix((vals, (rows, cols)), shape=(n, n), dtype=complex)


def scalar_basis(F):
    """Columns: orthonormal J=0 vectors (in M=0 Fock coordinates), grouped by species occupation."""
    m0 = np.where(F.M == 0)[0]
    m1 = {j: k for k, j in enumerate(np.where(F.M == 1)[0])}
    species = [(n, l) for n, l, m in F.modes]
    groups = {}
    for j in m0:
        sig = tuple(sorted(Counter(species[i] for i in F.states[j]).items()))
        groups.setdefault(sig, []).append(j)
    cols, Nb, Pb, maxJ2err = [], [], [], 0.0
    for sig, members in groups.items():
        # J+ from this group's M=0 states into M=1 states
        tgt = {}
        A = {}
        for c, j in enumerate(members):
            s = F.states[j]
            for i in set(s):
                n, l, m = F.modes[i]
                if m == l:
                    continue
                occ_i = s.count(i)
                ip = i + 1   # modes are ordered by m within each (n,l)
                assert F.modes[ip] == (n, l, m + 1)
                t = list(s)
                t.remove(i)
                t.append(ip)
                t = tuple(sorted(t))
                occ_p = t.count(ip)
                amp = math.sqrt(l * (l + 1) - m * (m + 1)) * math.sqrt(occ_i) * math.sqrt(occ_p)
                r = tgt.setdefault(F.index[t], len(tgt))
                A[(r, c)] = A.get((r, c), 0.0) + amp
        nm = len(members)
        if not tgt:
            V = np.eye(nm)
            ev = np.zeros(nm)
        else:
            Jp = np.zeros((len(tgt), nm))
            for (r, c), v in A.items():
                Jp[r, c] = v
            C = Jp.T @ Jp                       # = J^2 on the M=0 block
            ev, V = np.linalg.eigh(C)
        keep = ev < 0.5
        if keep.any():
            maxJ2err = max(maxJ2err, float(np.max(np.abs(ev[keep]))))
            if (~keep).any():
                assert np.min(np.abs(ev[~keep] - 2.0)) < 1e-8 or np.min(ev[~keep]) > 1.5
            for v in V[:, keep].T:
                cols.append((np.array(members), v))
                Nb.append(F.N[members[0]])
                Pb.append(F.P[members[0]])
    ri = np.concatenate([m for m, v in cols]); vv = np.concatenate([v for m, v in cols])
    ci = np.concatenate([np.full(len(m), c) for c, (m, v) in enumerate(cols)])
    S = sp.csc_matrix((vv, (ri, ci)), shape=(len(F.states), len(cols)))
    return S, np.array(Nb), np.array(Pb), maxJ2err


def mode_coefs(F, x, theta, phi):
    c = np.zeros(len(F.modes), dtype=complex)
    for i, (n, l, m) in enumerate(F.modes):
        c[i] = math.sqrt(u2(x, n, l)) * math.sqrt(4 * math.pi) * sph_harm_y(l, m, theta, phi)
    return c


def scalar_vertices(F, S, x, theta, phi, kmax=4, chunk=48):
    """W_k = S^T <:B(Omega0)^k:> S for k=1..kmax at a single sphere point."""
    Bm = F.annihilator(mode_coefs(F, x, theta, phi))   # B^-
    Bp = Bm.conj().T.tocsr()                            # B^+
    ns = S.shape[1]
    W = [np.zeros((ns, ns), dtype=complex) for _ in range(kmax)]
    St = S.T.tocsr()
    for c0 in range(0, ns, chunk):
        Sc = S[:, c0:c0 + chunk].toarray().astype(complex)
        down = [Sc]                                     # powers of B^- applied to S
        for _ in range(kmax):
            down.append(Bm @ down[-1])
        for k in range(1, kmax + 1):
            acc = np.zeros_like(Sc)
            for j in range(k + 1):
                v = down[k - j]
                for _ in range(j):
                    v = Bp @ v
                acc += math.comb(k, j) * v
            W[k - 1][:, c0:c0 + chunk] = St @ acc
    return W


# ---------------------------------------------------------------- local zero mode
class Local:
    def __init__(self, K0=400, pad=8):
        self.K0 = K0
        n = K0 + pad
        a = np.diag(np.sqrt(np.arange(1, n)), 1)
        q = a + a.T
        self.q1 = q[:K0, :K0]
        q2 = q @ q
        self.q2 = q2[:K0, :K0]
        self.q3 = (q2 @ q)[:K0, :K0]
        self.q4 = (q2 @ q2)[:K0, :K0]
        self.num = np.arange(K0)
        self.par = self.num % 2

    def reduce(self, x, r, g, K):
        """Lowest K eigenstates per parity of hz; returns energies and projected q powers."""
        A = x / 4 + r - g / 2
        hz = x * np.diag(self.num + 0.5) + (A - x / 4) * self.q2 + g / 12 * self.q4
        out = {}
        U = {}
        for p in (0, 1):
            idx = np.where(self.par == p)[0]
            e, v = np.linalg.eigh(hz[np.ix_(idx, idx)])
            U[p] = (idx, v[:, :K])
            out[('E', p)] = e[:K]
        e0 = out[('E', 0)][0]
        for p in (0, 1):
            out[('E', p)] = out[('E', p)] - e0
        for name, mat in (('q1', self.q1), ('q2', self.q2), ('q3', self.q3)):
            for p in (0, 1):
                for pp in (0, 1):
                    i1, v1 = U[p]
                    i2, v2 = U[pp]
                    out[(name, p, pp)] = v1.T @ mat[np.ix_(i1, i2)] @ v2
        out['tail'] = {p: float(np.abs(U[p][1][-20:, :]).max()) for p in (0, 1)}
        return out


# ---------------------------------------------------------------- model
class Model:
    def __init__(self, L, x, point=(1.1, 0.7), point2=(2.3, -1.9), K0=400):
        t0 = time.time()
        self.L, self.x = L, x
        F = Fock(L)
        S, Nb, Pb, j2err = scalar_basis(F)
        sel = (Nb % 2 == 0)            # inversion even
        S, Nb, Pb = S[:, sel], Nb[sel], Pb[sel]
        W = scalar_vertices(F, S, x, *point)
        W2 = scalar_vertices(F, S, x, *point2)
        self.checks = {
            'fock_states': len(F.states), 'm0_states': int((F.M == 0).sum()),
            'scalar_states': int(S.shape[1]), 'J2_null_max': j2err,
            'orth': float(np.abs((S.T @ S).toarray() - np.eye(S.shape[1])).max()),
            'imag_max': max(float(np.abs(w.imag).max()) for w in W),
            'asym_max': max(float(np.abs(w - w.T.conj()).max()) for w in W),
            'point_dependence': max(float(np.abs(a - b).max()) for a, b in zip(W, W2)),
        }
        par = Pb % 2
        self.W = [w.real for w in W]
        odd_even = 0.0
        for k, w in enumerate(self.W, 1):
            mask = (par[:, None] != par[None, :]) if k % 2 == 0 else (par[:, None] == par[None, :])
            odd_even = max(odd_even, float(np.abs(w[mask]).max()) if mask.any() else 0.0)
        self.checks['parity_violation'] = odd_even
        self.Nb, self.Pb, self.par = Nb, Pb, par
        self.loc = Local(K0)
        self.checks['setup_s'] = time.time() - t0

    # ---- Hamiltonian application in a field-parity sector at bath cutoff ell
    def sector(self, f, ell, lo, Dvec):
        """Return (dim, matvec, diag) for field parity f, bath cutoff ell, local data lo, window shift Dvec."""
        blocks = []
        for pl in (0, 1):
            pb = (f - pl) % 2
            ib = np.where((self.par == pb) & (self.Nb <= ell))[0]
            blocks.append((pl, ib))
        Kl = len(lo[('E', 0)])
        dims = [Kl * len(ib) for pl, ib in blocks]
        offs = np.cumsum([0] + dims)
        x = self.x
        Wsub = {}
        for a, (pl, ia) in enumerate(blocks):
            for b, (pm, ib) in enumerate(blocks):
                Wsub[(a, b)] = [w[np.ix_(ia, ib)] for w in self.W]
        bathdiag = [self.Nb[ib] + x * self.Pb[ib] + Dvec[self.Nb[ib]] for pl, ib in blocks]
        Lj = self.Lj

        def mv(v):
            out = np.empty_like(v)
            Vs = [v[offs[a]:offs[a + 1]].reshape(Kl, -1) for a in range(2)]
            for a, (pl, ia) in enumerate(blocks):
                Y = lo[('E', pl)][:, None] * Vs[a] + Vs[a] * bathdiag[a][None, :]
                for b, (pm, ib) in enumerate(blocks):
                    if Vs[b].shape[1] == 0 or Vs[a].shape[1] == 0:
                        continue
                    for j in range(4):
                        Lm = Lj[j][(pl, pm)]
                        if Lm is None:
                            continue
                        Y = Y + Lm @ Vs[b] @ Wsub[(a, b)][j].T
                out[offs[a]:offs[a + 1]] = Y.ravel()
            return out
        return int(offs[-1]), mv

    def dense(self, f, ell, lo, Dvec):
        """Explicit Kronecker assembly of the same sector Hamiltonian (row-major local x bath)."""
        blocks = []
        for pl in (0, 1):
            pb = (f - pl) % 2
            blocks.append((pl, np.where((self.par == pb) & (self.Nb <= ell))[0]))
        Kl = len(lo[('E', 0)])
        rowsH = []
        for a, (pl, ia) in enumerate(blocks):
            row = []
            for b, (pm, ib) in enumerate(blocks):
                Hab = np.zeros((Kl * len(ia), Kl * len(ib)))
                if a == b:
                    bd = self.Nb[ia] + self.x * self.Pb[ia] + Dvec[self.Nb[ia]]
                    Hab += np.diag(np.kron(lo[('E', pl)], np.ones(len(ia))) + np.kron(np.ones(Kl), bd))
                for j in range(4):
                    Lm = self.Lj[j][(pl, pm)]
                    if Lm is not None and len(ia) and len(ib):
                        Hab += np.kron(Lm, self.W[j][np.ix_(ia, ib)])
                row.append(Hab)
            rowsH.append(row)
        H = np.block(rowsH)
        return 0.5 * (H + H.T)

    def lowest(self, f, ell, lo, Dvec, k):
        n, mv = self.sector(f, ell, lo, Dvec)
        if n <= 2500:
            return sla.eigvalsh(self.dense(f, ell, lo, Dvec), subset_by_index=[0, k - 1])
        op = spla.LinearOperator((n, n), matvec=mv, dtype=float)
        vals = spla.eigsh(op, k=k, which='SA', tol=1e-14, ncv=max(4 * k, 40), maxiter=100000,
                          return_eigenvectors=False)
        return np.sort(vals)

    def set_couplings(self, r, g, K):
        x = self.x
        lo = self.loc.reduce(x, r, g, K)
        A = x / 4 + r - g / 2
        Lj = []
        I = {p: np.eye(K) for p in (0, 1)}
        L1 = {(p, pp): ((2 * A - x / 2) * lo[('q1', p, pp)] + g / 3 * lo[('q3', p, pp)]) if p != pp else None
              for p in (0, 1) for pp in (0, 1)}
        L2 = {(p, pp): ((A - x / 4) * I[p] + g / 2 * lo[('q2', p, pp)]) if p == pp else None
              for p in (0, 1) for pp in (0, 1)}
        L3 = {(p, pp): (g / 3 * lo[('q1', p, pp)]) if p != pp else None for p in (0, 1) for pp in (0, 1)}
        L4 = {(p, pp): (g / 12 * I[p]) if p == pp else None for p in (0, 1) for pp in (0, 1)}
        self.Lj = [L1, L2, L3, L4]
        return lo

    def solve(self, r, g, K=30, window=True, nroots=3):
        lo = self.set_couplings(r, g, K)
        L = self.L
        Ev = {0: 0.0}
        Ev[0] = self.lowest(0, 0, lo, np.zeros(L + 1), 1)[0]
        if window:
            for ell in range(2, L + 1, 2):
                def Dvec(v):
                    D = np.zeros(L + 1)
                    for N in range(1, ell + 1):
                        D[N] = v - Ev[2 * ((ell - N) // 2)]
                    return D

                def Fv(v):
                    return self.lowest(0, ell, lo, Dvec(v), 1)[0] - v
                a = Ev[ell - 2]
                fa = Fv(a)
                step = 0.05 + abs(fa)
                b = a - step if fa < 0 else a + step
                while Fv(b) * fa > 0:
                    step *= 2
                    if not np.isfinite(step) or step > 1e3:
                        raise RuntimeError('window bracket failed')
                    b = a - step if fa < 0 else a + step
                Ev[ell] = brentq(Fv, min(a, b), max(a, b), xtol=1e-15, rtol=1e-15, maxiter=200)
            D = np.zeros(L + 1)
            for N in range(1, L + 1):
                D[N] = Ev[L] - Ev[2 * ((L - N) // 2)]
        else:
            D = np.zeros(L + 1)
        ev = self.lowest(0, L, lo, D, nroots)
        od = self.lowest(1, L, lo, D, nroots)
        E0 = ev[0]
        return {'even': ev - E0, 'odd': od - E0, 'Ev': Ev, 'E0': E0, 'tail': lo['tail'],
                'fixed_point_residual': (E0 - Ev[L]) if window else None}

    def tune(self, r0, g0, K=30, window=True, tol=1e-12):
        x = self.x

        def res(p):
            try:
                s = self.solve(p[0], p[1], K, window, nroots=2)
            except Exception:
                return [1e3, 1e3]
            return [s['odd'][0] - x, s['odd'][1] - (3 - x)]
        sol = root(res, [r0, g0], method='hybr', options={'xtol': 1e-14})
        s = self.solve(sol.x[0], sol.x[1], K, window, nroots=3)
        return sol.x, s, float(np.max(np.abs(res(sol.x)))), sol.success
