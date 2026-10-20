"""Independent re-implementation of the 2D dressed-window Hamiltonian truncation.

Written from the physics specification only (docs/ORIGINAL_METHOD.md, sections 1-5); no code from the
ht2d package is used or imported.  Deliberately different numerical choices:

  * bath vertices from explicit annihilation amplitudes C_q = B^q S on a dictionary Fock representation,
    W_k = sum_p binom(k,p) C_p^T C_{k-p}  (equivalently, the theta average of :phi_b^k: between J-fixed states);
  * reflection-even states built as explicit symmetric combinations;
  * zero mode in the eigenbasis of the bare local Hamiltonian hz (computed in a large scaled-oscillator
    basis, every q0 power formed before truncation), instead of a density-optimized basis;
  * window fixed points by Newton on F(s) = lambda_min(H(s)) - s;  tuning by a finite-difference Newton.

Conventions (spec):  x = Delta_sigma, mode (a,b): energy x+a+b, spin a-b, u_ab^2 = (x)_a (x)_b / (a! b!).
  H = H0 + r avg :phi^2: + (g/12) avg :phi^4:,  q0 = a00 + a00^+, p0 = (a00 - a00^+)/i,
  hz = x p0^2/4 + A q0^2 + g q0^4/12,  A = x/4 + r - g/2,
  L1 = (2A - x/2) q0 + g q0^3/3,  L2 = (A - x/4) + g q0^2/2,  L3 = g q0/3,  L4 = g/12,
  g = 192 exp(3 t1)/x^2,  A = 4 exp(2 t1) t0 / x.
  Window: D_l(N) = Ev(l) - Ev(evenfloor(l-N)), Ev(l) self-consistent lowest even scalar level at bath cut l.
"""
from __future__ import annotations

import math
from math import comb

import numpy as np
import scipy.linalg as la
import scipy.sparse as sp
import scipy.sparse.linalg as sla


# ----------------------------------------------------------------------------------------------- bath
def poch(x, n):
    out = 1.0
    for i in range(n):
        out *= x + i
    return out


class Bath:
    """Positive circle modes (a,b), a+b>=1, all Fock states with N=sum (a+b) n_ab <= L and fixed total spin J."""

    def __init__(self, L: int, x: float, J: int = 0, reflect_even: bool = True):
        self.L, self.x, self.J = L, x, J
        self.modes = [(a, n - a) for n in range(1, L + 1) for a in range(n + 1)]
        self.level = np.array([a + b for a, b in self.modes])
        self.spin = np.array([a - b for a, b in self.modes])
        self.u = np.array([math.sqrt(poch(x, a) * poch(x, b) / (math.factorial(a) * math.factorial(b)))
                           for a, b in self.modes])
        ext = self._enumerate()
        self.ext = ext
        self.next = len(ext)
        self._build_vertices()
        if reflect_even:
            if J != 0:
                raise ValueError("reflection projection only at J=0")
            self._reflect_even()
        else:
            n = self.next
            self.Q = sp.identity(n, format="csr")
            self.N = np.array([self._N(s) for s in ext])
            self.P = np.array([self._P(s) for s in ext])
            self.W = {k: self.Wfull[k].tocsr() for k in range(1, 5)}
        self.nb = len(self.N)

    def _N(self, s):
        return sum(self.level[m] * k for m, k in s)

    def _P(self, s):
        return sum(k for _, k in s)

    def _enumerate(self):
        L, J = self.L, self.J
        modes, out = self.modes, []
        nm = len(modes)
        # remaining-capacity bound for pruning: spin can change by at most level per quantum
        def rec(i, N, Jt, occ):
            if abs(J - Jt) > L - N:
                return
            if i == nm:
                if Jt == J:
                    out.append(tuple(occ))
                return
            lev, sp_ = self.level[i], self.spin[i]
            k = 0
            while N + k * lev <= L:
                if k:
                    occ.append((i, k))
                rec(i + 1, N + k * lev, Jt + k * sp_, occ)
                if k:
                    occ.pop()
                k += 1
        rec(0, 0, 0, [])
        return out

    def _build_vertices(self):
        """C_q = B^q S as sparse matrices on the closure of the external states under lowering."""
        index = {s: i for i, s in enumerate(self.ext)}
        states = list(self.ext)
        rows, cols, vals = [], [], []
        frontier = list(range(len(states)))
        done = 0
        # lower every state in the closure once (B maps state i -> state j with amplitude u_m sqrt(n_m))
        i = 0
        while i < len(states):
            s = states[i]
            for pos, (m, k) in enumerate(s):
                t = s[:pos] + s[pos + 1:] if k == 1 else s[:pos] + ((m, k - 1),) + s[pos + 1:]
                j = index.get(t)
                if j is None:
                    j = len(states)
                    index[t] = j
                    states.append(t)
                rows.append(j); cols.append(i); vals.append(self.u[m] * math.sqrt(k))
            i += 1
        nT = len(states)
        B = sp.csr_matrix((vals, (rows, cols)), shape=(nT, nT))
        S = sp.csr_matrix((np.ones(self.next), (np.arange(self.next), np.arange(self.next))), shape=(nT, self.next))
        C = {0: S}
        for q in range(1, 5):
            C[q] = (B @ C[q - 1]).tocsr()
        self.nT = nT
        self.Wfull = {}
        for k in range(1, 5):
            W = None
            for p in range(k + 1):
                term = comb(k, p) * (C[p].T @ C[k - p])
                W = term if W is None else W + term
            W = W.tocsr()
            W.eliminate_zeros()
            self.Wfull[k] = W

    def _reflect_even(self):
        refl = {m: self.modes.index((b, a)) for m, (a, b) in enumerate(self.modes)}
        index = {s: i for i, s in enumerate(self.ext)}
        seen = set()
        r, c, v = [], [], []
        Ns, Ps = [], []
        col = 0
        for s in self.ext:
            if s in seen:
                continue
            rs = tuple(sorted((refl[m], k) for m, k in s))
            seen.add(s); seen.add(rs)
            if rs == s:
                r.append(index[s]); c.append(col); v.append(1.0)
            else:
                h = 1 / math.sqrt(2)
                r += [index[s], index[rs]]; c += [col, col]; v += [h, h]
            Ns.append(self._N(s)); Ps.append(self._P(s))
            col += 1
        Q = sp.csr_matrix((v, (r, c)), shape=(self.next, col))
        self.Q = Q
        self.N = np.array(Ns)
        self.P = np.array(Ps)
        self.W = {}
        for k in range(1, 5):
            W = (Q.T @ self.Wfull[k] @ Q).tocsr()
            W.eliminate_zeros()
            self.W[k] = W


# ----------------------------------------------------------------------------------------------- zero mode
class ZeroMode:
    """hz eigenbasis, Ke even + Ko odd states, operators q0^k projected after forming powers in a big basis."""

    def __init__(self, x, A, g, M=400, Ke=24, Ko=24, lam=None):
        self.x, self.A, self.g = x, A, g
        if lam is None:
            # Gaussian variational width:  E(l) = x/(4 l^2) + A l^2 + g l^4 / 4
            ls = np.exp(np.linspace(-6, 3, 4001))
            E = x / (4 * ls ** 2) + A * ls ** 2 + g * ls ** 4 / 4
            lam = ls[np.argmin(E)]
        self.lam = lam
        Mb = M + 8
        n = np.arange(Mb)
        b = np.diag(np.sqrt(n[1:]), 1)  # annihilator
        q = lam * (b + b.T)
        pm = (b - b.T)                 # p0 = pm / (i lam)  ->  p0^2 = -pm^2 / lam^2
        q2 = q @ q
        q3 = q2 @ q
        q4 = q2 @ q2
        p2 = -(pm @ pm) / lam ** 2
        cut = slice(0, M)
        q, q2, q3, q4, p2 = (m[cut, cut] for m in (q, q2, q3, q4, p2))
        hz = x * p2 / 4 + A * q2 + g * q4 / 12
        ev_idx = np.arange(0, M, 2)
        od_idx = np.arange(1, M, 2)
        we, Ve = la.eigh(hz[np.ix_(ev_idx, ev_idx)])
        wo, Vo = la.eigh(hz[np.ix_(od_idx, od_idx)])
        V = np.zeros((M, Ke + Ko))
        V[ev_idx, :Ke] = Ve[:, :Ke]
        V[od_idx, Ke:] = Vo[:, :Ko]
        self.V = V
        self.energies = np.concatenate([we[:Ke], wo[:Ko]])
        self.E0 = we[0]
        self.parity = np.array([0] * Ke + [1] * Ko)  # 0 even, 1 odd
        self.K = Ke + Ko
        proj = lambda m: V.T @ m @ V
        self.q = {1: proj(q), 2: proj(q2), 3: proj(q3), 4: proj(q4)}
        # exact parity selection
        same = self.parity[:, None] == self.parity[None, :]
        for k in self.q:
            leak = np.abs(self.q[k][same if k % 2 else ~same]).max(initial=0.0)
            assert leak < 1e-9 * max(1.0, np.abs(self.q[k]).max()), (k, leak)
            self.q[k][same if k % 2 else ~same] = 0.0
        I = np.eye(self.K)
        self.Lop = {
            1: (2 * A - x / 2) * self.q[1] + g * self.q[3] / 3,
            2: (A - x / 4) * I + g * self.q[2] / 2,
            3: g * self.q[1] / 3,
            4: g / 12 * I,
        }
        # convergence diagnostics of the primitive basis
        self.tail_weight = float(max(np.abs(Ve[-20:, :Ke]).max(), np.abs(Vo[-20:, :Ko]).max()))


def couplings(theta, x):
    t0, t1 = theta
    g = 192 * math.exp(3 * t1) / x ** 2
    A = 4 * math.exp(2 * t1) * t0 / x
    r = A + g / 2 - x / 4
    return A, g, r


# ----------------------------------------------------------------------------------------------- Hamiltonian
class Sector:
    """Hamiltonian on (local K) x (bath states with N<=ell) restricted to total field parity `par`."""

    def __init__(self, zm: ZeroMode, bath: Bath, ell: int, par: int):
        self.zm, self.bath, self.par = zm, bath, par
        bsel = np.nonzero(bath.N <= ell)[0]
        self.bsel = bsel
        self.N = bath.N[bsel]
        Pb = bath.P[bsel] % 2
        self.mask = (zm.parity[:, None] + Pb[None, :]) % 2 == par
        self.W = {k: bath.W[k][bsel][:, bsel].tocsr() for k in range(1, 5)}
        self.Hb = (self.N + bath.x * bath.P[bsel]).astype(float)
        self.hz = zm.energies - zm.E0
        self.dim = int(self.mask.sum())
        self.K, self.nb = zm.K, len(bsel)

    def matvec_full(self, V, D):
        out = self.hz[:, None] * V + V * (self.Hb + D)[None, :]
        for k in range(1, 5):
            LV = self.zm.Lop[k] @ V
            out += (self.W[k] @ LV.T).T
        return out

    def dense(self, D):
        if getattr(self, "_H0", None) is None:
            m = self.mask.ravel()
            H = np.kron(np.diag(self.hz), np.eye(self.nb)) + np.kron(np.eye(self.K), np.diag(self.Hb))
            for k in range(1, 5):
                H += np.kron(self.zm.Lop[k], self.W[k].toarray())
            self._H0 = H[np.ix_(m, m)]
            self._dsel = np.broadcast_to(np.arange(self.nb)[None, :], (self.K, self.nb)).ravel()[m]
            assert np.abs(self._H0 - self._H0.T).max() < 1e-12
        return self._H0 + np.diag(np.asarray(D)[self._dsel])

    def lowest(self, D, nev=1, v0=None, tol=1e-14):
        if self.dim <= DENSE_MAX:
            w, U = la.eigh(self.dense(D), subset_by_index=[0, nev - 1])
            return w, U
        m = self.mask

        def mv(v):
            V = np.zeros((self.K, self.nb))
            V[m] = v.ravel()
            return self.matvec_full(V, D)[m]

        op = sla.LinearOperator((self.dim, self.dim), matvec=mv, dtype=float)
        w, U = sla.eigsh(op, k=nev, which="SA", tol=tol, v0=v0, ncv=max(4 * nev + 20, 40), maxiter=100000)
        o = np.argsort(w)
        return w[o], U[:, o]

    def bath_weight(self, vec):
        """weight of the vector on bath level N=0 (summed over local states)."""
        V = np.zeros((self.K, self.nb))
        V[self.mask] = vec
        return float((V[:, self.N == 0] ** 2).sum())


DENSE_MAX = 2500


def window_table(zm, bath, L, fp_tol=1e-13, eig_tol=1e-14, verbose=False):
    """Consistent full-vacuum window: Ev(l) = lambda_min(H_raw,l + D_l(s)), s = Ev(l), for l = 2,4,...,L."""
    Ev = {0: 0.0}
    iters = {}
    for ell in range(2, L + 1, 2):
        sec = Sector(zm, bath, ell, 0)
        lower = np.array([Ev[ell - n] if n > 0 else 0.0 for n in sec.N])
        s = Ev[ell - 2]
        v0 = None
        for it in range(100):
            D = np.where(sec.N > 0, s - lower, 0.0)
            w, U = sec.lowest(D, 1, v0=v0, tol=eig_tol)
            v0 = U[:, 0]
            p0 = sec.bath_weight(U[:, 0])
            F = w[0] - s
            s = s + F / p0
            if abs(F) < fp_tol * max(1.0, abs(s)):
                break
        else:
            raise RuntimeError(f"window fixed point failed at ell={ell}")
        Ev[ell] = s
        iters[ell] = (it + 1, F, p0)
        if verbose:
            print(f"  ell={ell} Ev={s:.15f} it={it+1} F={F:.1e} p0={p0:.4f}", flush=True)
    EvL = Ev[L]
    Dtab = {n: (EvL - Ev[(L - n) - ((L - n) % 2)]) if n > 0 else 0.0 for n in range(0, L + 1)}
    return Ev, Dtab, iters


def solve_spectrum(x, theta, L, M=400, Ke=24, Ko=24, nev=5, bath=None, lam=None, fp_tol=1e-13, extraJ=(),
                   eig_tol=1e-14, verbose=False):
    A, g, r = couplings(theta, x)
    zm = ZeroMode(x, A, g, M=M, Ke=Ke, Ko=Ko, lam=lam)
    if bath is None:
        bath = Bath(L, x)
    Ev, Dtab, iters = window_table(zm, bath, L, fp_tol, eig_tol, verbose)
    EvL = Ev[L]
    out = {"x": x, "theta": list(theta), "A": A, "g": g, "r": r, "L": L, "M": M, "Ke": Ke, "Ko": Ko,
           "lam": zm.lam, "zm_tail": zm.tail_weight, "Ev": Ev, "D": Dtab, "fp_iters": iters}
    for par, name in ((0, "even"), (1, "odd")):
        if nev == 0:
            continue
        k = nev if par == 0 else max(nev, 2)
        sec = Sector(zm, bath, L, par)
        D = np.array([Dtab[n] for n in sec.N])
        w, _ = sec.lowest(D, k, tol=eig_tol)
        out[name] = (w - EvL).tolist()
        out["dim_" + name] = sec.dim
    for J in extraJ:
        bJ = Bath(L, x, J=J, reflect_even=False)
        for par in (0, 1):
            sec = Sector(zm, bJ, L, par)
            D = np.array([Dtab[n] for n in sec.N])
            w, _ = sec.lowest(D, min(nev + 1, sec.dim - 1), tol=eig_tol)
            out[f"J{J}_{par}"] = (w - EvL).tolist()
    return out


def tuning_residual(x, theta, L, bath, **kw):
    A, g, r = couplings(theta, x)
    zm = ZeroMode(x, A, g, M=kw.get("M", 400), Ke=kw.get("Ke", 24), Ko=kw.get("Ko", 24))
    Ev, Dtab, _ = window_table(zm, bath, L, eig_tol=kw.get("eig_tol", 1e-14))
    sec = Sector(zm, bath, L, 1)
    D = np.array([Dtab[n] for n in sec.N])
    w, _ = sec.lowest(D, 2, tol=kw.get("eig_tol", 1e-14))
    gaps = w - Ev[L]
    return np.array([gaps[0] - x, gaps[1] - (2 - x)])


def tune(x, theta0, L, bath=None, tol=1e-11, h=1e-6, maxit=40, verbose=False, **kw):
    """Independent Newton tuning with a forward-difference Jacobian and step halving."""
    if bath is None:
        bath = Bath(L, x)
    th = np.array(theta0, float)
    R = tuning_residual(x, th, L, bath, **kw)
    hist = [(th.tolist(), float(np.abs(R).max()))]
    for it in range(maxit):
        if np.abs(R).max() < tol:
            break
        Jm = np.zeros((2, 2))
        for c in range(2):
            d = np.zeros(2); d[c] = h
            Jm[:, c] = (tuning_residual(x, th + d, L, bath, **kw) - R) / h
        step = -np.linalg.solve(Jm, R)
        lam = 1.0
        while True:
            try:
                Rn = tuning_residual(x, th + lam * step, L, bath, **kw)
                ok = np.abs(Rn).max() < np.abs(R).max() or lam < 1e-3
            except Exception:
                ok = False
                Rn = None
            if ok and Rn is not None:
                break
            lam /= 2
            if lam < 1e-4:
                raise RuntimeError("line search failed")
        th = th + lam * step
        R = Rn
        hist.append((th.tolist(), float(np.abs(R).max())))
        if verbose:
            print(f"  tune it={it} theta={th} |R|={np.abs(R).max():.2e} lam={lam}", flush=True)
    else:
        raise RuntimeError("tuning did not converge")
    return th, R, hist
