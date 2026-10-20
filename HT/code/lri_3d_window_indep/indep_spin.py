"""Spin-J (highest weight M=J) sectors for the clean-room solver, vertices by full-sphere quadrature."""
import math, numpy as np, scipy.sparse as sp
from collections import Counter
from indep_ht3d import Fock, mode_coefs, Model


def hw_basis(F, J):
    """Orthonormal highest-weight vectors: M=J states annihilated by J+ (null space of the J+^T J+ Gram)."""
    mJ = np.where(F.M == J)[0]
    species = [(n, l) for n, l, m in F.modes]
    groups = {}
    for j in mJ:
        groups.setdefault(tuple(sorted(Counter(species[i] for i in F.states[j]).items())), []).append(j)
    cols, Nb, Pb = [], [], []
    for members in groups.values():
        tgt, A = {}, {}
        for c, j in enumerate(members):
            s = F.states[j]
            for i in set(s):
                n, l, m = F.modes[i]
                if m == l:
                    continue
                t = list(s); t.remove(i); t.append(i + 1); t = tuple(sorted(t))
                amp = math.sqrt(l * (l + 1) - m * (m + 1)) * math.sqrt(s.count(i)) * math.sqrt(t.count(i + 1))
                r = tgt.setdefault(F.index[t], len(tgt))
                A[(r, c)] = A.get((r, c), 0.0) + amp
        if tgt:
            Jp = np.zeros((len(tgt), len(members)))
            for (r, c), v in A.items():
                Jp[r, c] = v
            ev, V = np.linalg.eigh(Jp.T @ Jp)
        else:
            ev, V = np.zeros(len(members)), np.eye(len(members))
        for v in V[:, ev < 0.5].T:
            cols.append((np.array(members), v)); Nb.append(F.N[members[0]]); Pb.append(F.P[members[0]])
    ri = np.concatenate([m for m, v in cols]); vv = np.concatenate([v for m, v in cols])
    ci = np.concatenate([np.full(len(m), c) for c, (m, v) in enumerate(cols)])
    return sp.csc_matrix((vv, (ri, ci)), shape=(len(F.states), len(cols))), np.array(Nb), np.array(Pb)


def averaged_vertices(F, S, x, kmax=4, extra=2):
    """W_k = S^T [ int dOmega/4pi :B^k: ] S by Gauss-Legendre(cos theta) x trapezoid(phi), exact degree."""
    L = F.L
    zq, wq = np.polynomial.legendre.leggauss(L + 1 + extra)
    nphi = 2 * L + 3 + extra
    phis = 2 * math.pi * (np.arange(nphi) + 0.37) / nphi        # offset grid, still exact
    ns = S.shape[1]
    W = [np.zeros((ns, ns), dtype=complex) for _ in range(kmax)]
    Sd = S.toarray().astype(complex)
    St = S.T.tocsr()
    for z, w in zip(zq, wq):
        th = math.acos(z)
        for ph in phis:
            Bm = F.annihilator(mode_coefs(F, x, th, ph))
            Bp = Bm.conj().T.tocsr()
            down = [Sd]
            for _ in range(kmax):
                down.append(Bm @ down[-1])
            for k in range(1, kmax + 1):
                acc = np.zeros_like(Sd)
                for j in range(k + 1):
                    v = down[k - j]
                    for _ in range(j):
                        v = Bp @ v
                    acc += math.comb(k, j) * v
                W[k - 1] += (w / 2) * (1 / nphi) * (St @ acc)
    return W


class SpinModel(Model):
    """Same Hamiltonian as Model but on spin-J highest-weight bath states with inversion parity `inv`."""

    def __init__(self, L, x, J, inv, K0=400):
        import time
        from indep_ht3d import Local
        t0 = time.time()
        self.L, self.x = L, x
        F = Fock(L)
        S, Nb, Pb = hw_basis(F, J)
        sel = (Nb % 2 == inv)
        S, Nb, Pb = S[:, sel], Nb[sel], Pb[sel]
        W = averaged_vertices(F, S, x)
        self.checks = {'states': int(S.shape[1]), 'imag_max': max(float(np.abs(w.imag).max()) for w in W),
                       'asym_max': max(float(np.abs(w - w.T.conj()).max()) for w in W)}
        self.W = [w.real for w in W]
        self.Nb, self.Pb, self.par = Nb, Pb, Pb % 2
        self.loc = Local(K0)
        self.checks['setup_s'] = time.time() - t0

    def spectrum(self, r, g, K, D, f, k):
        lo = self.set_couplings(r, g, K)
        return self.lowest(f, self.L, lo, D, k)
