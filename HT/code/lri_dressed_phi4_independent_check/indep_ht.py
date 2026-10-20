#!/usr/bin/env python3
"""
indep_ht.py -- independent Hamiltonian-truncation solver for the d=1 long-range
Ising model: generalized free field of dimension delta perturbed by
r :phi^2: + (g/12) :phi^4:, radially quantized on S^0 = {+1,-1}, with an
untruncated zero mode (sinc-DVR) and a bath of modes n>=1 truncated to total
level <= N ("product regulator").  Reflection-even sector only.

Written from the physics definition (see DERIVATION.md); does not use or
import the production code.

H = delta a0^+ a0 + sum_{n>=1} (n+delta) a_n^+ a_n + r :phi^2: + (g/12) :phi^4:
  = Hz + Hbath + sum_k L_k(q) W_k
Hz = -delta d^2/dq^2 + A q^2 + g q^4/12 + c,  A = delta/4 + r - g/2,
c = -delta/2 - r + g/4 (so that the free vacuum has energy exactly 0).
L1 = (2r-g) q + (g/3) q^3, L2 = (r-g/2) + (g/2) q^2, L3 = (g/3) q, L4 = g/12,
W_k = :X^k: restricted to even-level bath states, X = B + B^+, B = sum u_n a_n.
"""

import argparse
import json
import math
import os
import sys
import time

import numpy as np
import scipy.linalg as sla
import scipy.sparse as sp
from scipy.sparse.linalg import LinearOperator, eigsh, ArpackNoConvergence

# ----------------------------------------------------------------------------
# GFF mode data
# ----------------------------------------------------------------------------


def u2_coeffs(delta, nmax):
    """u_n^2 = (2 delta)_n / n!, Taylor coefficients of (1-z)^(-2 delta)."""
    u2 = np.empty(nmax + 1)
    u2[0] = 1.0
    for n in range(1, nmax + 1):
        u2[n] = u2[n - 1] * (2.0 * delta + n - 1) / n
    return u2


def partitions_upto(cut):
    """All multiplicity vectors (k_1..k_cut) with sum_n n k_n <= cut."""
    out = []
    if cut == 0:
        return [()]
    cur = [0] * cut

    def rec(n, rem):
        if n > cut:
            out.append(tuple(cur))
            return
        for k in range(rem // n + 1):
            cur[n - 1] = k
            rec(n + 1, rem - n * k)
        cur[n - 1] = 0

    rec(1, cut)
    return out


class FullBath:
    """Exact bath Fock operators on ALL states (both reflection parities) of
    level <= cut.  B = sum_n s_n u_n a_n with s_n = (+1)^n (x=+1) or (-1)^n
    (x=-1)."""

    def __init__(self, delta, cut, x=+1):
        self.delta, self.cut = delta, cut
        st = partitions_upto(cut)
        self.states = st
        self.lev = np.array([sum((n + 1) * k for n, k in enumerate(s)) for s in st], dtype=int)
        self.npart = np.array([sum(s) for s in st], dtype=int)
        idx = {s: i for i, s in enumerate(st)}
        u = np.sqrt(u2_coeffs(delta, max(cut, 1)))
        rows, cols, vals = [], [], []
        for i, s in enumerate(st):
            for n in range(1, cut + 1):
                k = s[n - 1]
                if k:
                    t = list(s)
                    t[n - 1] -= 1
                    rows.append(idx[tuple(t)])
                    cols.append(i)
                    vals.append((x ** n) * u[n] * math.sqrt(k))
        D = len(st)
        self.dim = D
        B = sp.csr_matrix((vals, (rows, cols)), shape=(D, D))
        self.B = B
        Bd = B.T.tocsr()
        I = sp.identity(D, format="csr")
        Bp, Bdp = [I], [I]
        for _ in range(4):
            Bp.append((Bp[-1] @ B).tocsr())
            Bdp.append((Bdp[-1] @ Bd).tocsr())
        self.W = {}
        for k in range(1, 5):
            Wk = sp.csr_matrix((D, D))
            for m in range(k + 1):
                Wk = Wk + math.comb(k, m) * (Bdp[m] @ Bp[k - m])
            self.W[k] = Wk.tocsr()
        self.Eb = self.lev + delta * self.npart


class Bath:
    """Reflection-even (even-level) bath block with the normal-ordered
    vertices W_k = :X^k:, k=1..4, split into even (E) / odd (O) particle-number
    blocks.  States in each block are sorted by level so that level <= L is a
    prefix."""

    def __init__(self, delta, cut):
        self.delta, self.cut = delta, cut
        fb = FullBath(delta, cut, +1)
        even = np.where(fb.lev % 2 == 0)[0]
        E = [i for i in even if fb.npart[i] % 2 == 0]
        O = [i for i in even if fb.npart[i] % 2 == 1]
        E = sorted(E, key=lambda i: (fb.lev[i], i))
        O = sorted(O, key=lambda i: (fb.lev[i], i))
        self.idxE, self.idxO = np.array(E, dtype=int), np.array(O, dtype=int)
        self.levE, self.levO = fb.lev[self.idxE], fb.lev[self.idxO]
        self.npE, self.npO = fb.npart[self.idxE], fb.npart[self.idxO]
        self.EbE = self.levE + delta * self.npE
        self.EbO = self.levO + delta * self.npO

        def blk(W, a, b):
            return np.ascontiguousarray(W[a][:, b].toarray())

        self.W2EE = blk(fb.W[2], self.idxE, self.idxE)
        self.W4EE = blk(fb.W[4], self.idxE, self.idxE)
        self.W2OO = blk(fb.W[2], self.idxO, self.idxO)
        self.W4OO = blk(fb.W[4], self.idxO, self.idxO)
        self.W1EO = blk(fb.W[1], self.idxE, self.idxO)
        self.W3EO = blk(fb.W[3], self.idxE, self.idxO)
        # selection-rule checks (particle-number parity)
        for k, (a, b) in [(1, (self.idxE, self.idxE)), (1, (self.idxO, self.idxO)),
                          (3, (self.idxE, self.idxE)), (3, (self.idxO, self.idxO)),
                          (2, (self.idxE, self.idxO)), (4, (self.idxE, self.idxO))]:
            if fb.W[k][a][:, b].nnz and abs(fb.W[k][a][:, b]).max() > 0:
                raise RuntimeError("particle-parity selection rule violated")
        self.fullbath = fb

    def n_upto(self, L):
        return int(np.searchsorted(self.levE, L, side="right")), int(np.searchsorted(self.levO, L, side="right"))


# ----------------------------------------------------------------------------
# Zero mode: sinc-DVR on q_j = j h, j=-M..M, parity adapted
# ----------------------------------------------------------------------------


def sinc_T(m, h):
    """Matrix element of -d^2/dq^2 between sinc-DVR points j, j+m."""
    m = np.abs(m)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(m == 0, math.pi ** 2 / 3.0, 2.0 * (-1.0) ** m / np.where(m == 0, 1, m) ** 2)
    return out / h ** 2


class ZeroMode:
    def __init__(self, h, M):
        self.h, self.M = float(h), int(M)
        j = np.arange(M + 1)
        self.q = h * j
        J, K = np.meshgrid(j, j, indexing="ij")
        Te = sinc_T(J - K, h) + sinc_T(J + K, h)
        Te[0, :] = math.sqrt(2.0) * sinc_T(j, h)
        Te[:, 0] = math.sqrt(2.0) * sinc_T(j, h)
        Te[0, 0] = sinc_T(np.array(0), h)
        self.Te = np.ascontiguousarray(Te)
        jj = j[1:]
        J, K = np.meshgrid(jj, jj, indexing="ij")
        self.To = np.ascontiguousarray(sinc_T(J - K, h) - sinc_T(J + K, h))
        self.qe = self.q.copy()  # even combos: j=0..M
        self.qo = self.q[1:].copy()  # odd combos: j=1..M

    def qpar(self, par):
        return self.qe if par == 0 else self.qo

    def Tpar(self, par):
        return self.Te if par == 0 else self.To

    def desc(self):
        return {"h": self.h, "M": self.M, "Q": self.h * self.M, "n_even": self.M + 1, "n_odd": self.M}


# ----------------------------------------------------------------------------
# Coefficient sets (H and its derivatives in r and g, which enter linearly)
# ----------------------------------------------------------------------------


def coefs_H(delta, r, g):
    A = delta / 4.0 + r - g / 2.0
    return dict(kin=delta, bath=1.0, v2=A, v4=g / 12.0, c=-delta / 2.0 - r + g / 4.0,
                l1=(2.0 * r - g, g / 3.0), l2=(r - g / 2.0, g / 2.0), l3=g / 3.0, l4=g / 12.0)


COEF_DR = dict(kin=0.0, bath=0.0, v2=1.0, v4=0.0, c=-1.0, l1=(2.0, 0.0), l2=(1.0, 0.0), l3=0.0, l4=0.0)
COEF_DG = dict(kin=0.0, bath=0.0, v2=-0.5, v4=1.0 / 12.0, c=0.25, l1=(-1.0, 1.0 / 3.0), l2=(-0.5, 0.5),
               l3=1.0 / 3.0, l4=1.0 / 12.0)


# ----------------------------------------------------------------------------
# Sector: fixed field parity f (0 even, 1 odd), bath cutoff L
# vector = [X_E (nE x mE) ; X_O (nO x mO)] with zero-mode parity
#   pE = f (bath even particle number), pO = 1-f
# ----------------------------------------------------------------------------


class Sector:
    def __init__(self, bath, zm, f, L):
        self.bath, self.zm, self.f, self.L = bath, zm, f, L
        nE, nO = bath.n_upto(L)
        self.nE, self.nO = nE, nO
        self.pE, self.pO = f, 1 - f
        self.qE, self.qO = zm.qpar(self.pE), zm.qpar(self.pO)
        self.TE, self.TO = zm.Tpar(self.pE), zm.Tpar(self.pO)
        self.mE, self.mO = len(self.qE), len(self.qO)
        c = np.ascontiguousarray
        self.W2E, self.W4E = c(bath.W2EE[:nE, :nE]), c(bath.W4EE[:nE, :nE])
        self.W2O, self.W4O = c(bath.W2OO[:nO, :nO]), c(bath.W4OO[:nO, :nO])
        self.W1EO, self.W3EO = c(bath.W1EO[:nE, :nO]), c(bath.W3EO[:nE, :nO])
        self.W1OE, self.W3OE = c(self.W1EO.T), c(self.W3EO.T)
        self.levE, self.levO = bath.levE[:nE], bath.levO[:nO]
        self.EbE, self.EbO = bath.EbE[:nE], bath.EbO[:nO]
        self.sE = nE * self.mE
        self.dim = self.sE + nO * self.mO
        self.nmatvec = 0

    def prepare(self, co, D=None):
        """Precompute the pieces of the operator for coefficient set co and
        bath-diagonal shift D[level] (None = 0)."""
        P = {}
        dshE = np.zeros(self.nE) if D is None else D[self.levE]
        dshO = np.zeros(self.nO) if D is None else D[self.levO]
        VE = co["v2"] * self.qE ** 2 + co["v4"] * self.qE ** 4 + co["c"]
        VO = co["v2"] * self.qO ** 2 + co["v4"] * self.qO ** 4 + co["c"]
        P["dE"] = (co["bath"] * self.EbE + dshE)[:, None] + VE[None, :]
        P["dO"] = (co["bath"] * self.EbO + dshO)[:, None] + VO[None, :]
        P["kin"] = co["kin"]
        c0, c2 = co["l2"]
        b1, b3 = co["l1"]
        d1 = co["l3"]
        l4 = co["l4"]
        P["WcE"] = c0 * self.W2E + l4 * self.W4E
        P["WcO"] = c0 * self.W2O + l4 * self.W4O
        P["c2"] = c2
        P["c2qE"] = c2 * self.qE ** 2
        P["c2qO"] = c2 * self.qO ** 2
        P["WaEO"] = b1 * self.W1EO + d1 * self.W3EO
        P["WaOE"] = b1 * self.W1OE + d1 * self.W3OE
        P["b3"] = b3
        P["b3q3E"] = b3 * self.qE ** 3
        P["b3q3O"] = b3 * self.qO ** 3
        return P

    def _odd_map(self, Y, Z, src_par):
        # Z lives on the source parity's columns, already multiplied by the odd
        # function L(q_src); move it to the destination parity's columns.
        if src_par == 1:  # odd (q_1..q_M) -> even (q_0..q_M): q_0 column gets 0
            Y[:, 1:] += Z
        else:  # even -> odd: drop q_0 column (odd function vanishes there)
            Y += Z[:, 1:]

    def apply(self, x, P):
        self.nmatvec += 1
        nE, nO, mE, mO = self.nE, self.nO, self.mE, self.mO
        XE = x[: self.sE].reshape(nE, mE)
        XO = x[self.sE:].reshape(nO, mO)
        y = np.empty_like(x)
        YE = y[: self.sE].reshape(nE, mE)
        YO = y[self.sE:].reshape(nO, mO)
        if nE:
            np.multiply(P["dE"], XE, out=YE)
            if P["kin"]:
                YE += P["kin"] * (XE @ self.TE)
            YE += P["WcE"] @ XE
            if P["c2"]:
                YE += (self.W2E @ XE) * P["c2qE"][None, :]
        if nO:
            np.multiply(P["dO"], XO, out=YO)
            if P["kin"]:
                YO += P["kin"] * (XO @ self.TO)
            YO += P["WcO"] @ XO
            if P["c2"]:
                YO += (self.W2O @ XO) * P["c2qO"][None, :]
        if nE and nO:
            Z = (P["WaEO"] @ XO) * self.qO[None, :]
            if P["b3"]:
                Z += (self.W1EO @ XO) * P["b3q3O"][None, :]
            self._odd_map(YE, Z, self.pO)
            Z = (P["WaOE"] @ XE) * self.qE[None, :]
            if P["b3"]:
                Z += (self.W1OE @ XE) * P["b3q3E"][None, :]
            self._odd_map(YO, Z, self.pE)
        return y

    def dense(self, P):
        n = self.dim
        H = np.empty((n, n))
        e = np.zeros(n)
        for i in range(n):
            e[i] = 1.0
            H[:, i] = self.apply(e, P)
            e[i] = 0.0
        return H

    def level_weights(self, x, Lmax):
        """Weight of the (normalized) vector x on each bath level 0..Lmax."""
        w = np.zeros(Lmax + 1)
        XE = x[: self.sE].reshape(self.nE, self.mE)
        XO = x[self.sE:].reshape(self.nO, self.mO)
        if self.nE:
            np.add.at(w, self.levE, np.einsum("ij,ij->i", XE, XE))
        if self.nO:
            np.add.at(w, self.levO, np.einsum("ij,ij->i", XO, XO))
        return w / np.dot(x, x)

    def zero_mode_density(self, x):
        """Zero-mode reduced density on the non-negative grid points, summed
        over parity components (for the box-edge check)."""
        XE = x[: self.sE].reshape(self.nE, self.mE)
        XO = x[self.sE:].reshape(self.nO, self.mO)
        rho = np.zeros(self.zm.M + 1)
        if self.nE:
            dE = np.einsum("ij,ij->j", XE, XE)
            if self.pE == 0:
                rho += dE
            else:
                rho[1:] += dE
        if self.nO:
            dO = np.einsum("ij,ij->j", XO, XO)
            if self.pO == 0:
                rho += dO
            else:
                rho[1:] += dO
        return rho / np.dot(x, x)


# ----------------------------------------------------------------------------
# Eigensolver
# ----------------------------------------------------------------------------

DENSE_MAX = 1200


def eig_lowest(sec, P, k, v0=None, shift=None, tol=1e-11):
    """k lowest eigenpairs of the sector operator. Returns (vals, vecs, info)."""
    n = sec.dim
    k = min(k, n)
    t0 = time.time()
    nm0 = sec.nmatvec
    if n <= DENSE_MAX:
        Hd = sec.dense(P)
        w, V = np.linalg.eigh(0.5 * (Hd + Hd.T))
        vals, vecs = w[:k], V[:, :k]
        method = "dense"
    else:
        if shift is None:
            # crude estimate of the bottom of the spectrum (Gershgorin-free):
            op0 = LinearOperator((n, n), matvec=lambda x: sec.apply(x, P), dtype=float)
            w0 = eigsh(op0, k=1, which="SA", tol=1e-4, v0=v0, ncv=min(n - 1, 20), maxiter=100000,
                       return_eigenvectors=False)
            shift = float(w0[0]) - 1.0
        op = LinearOperator((n, n), matvec=lambda x: sec.apply(x, P) - shift * x, dtype=float)
        ncv = min(n - 1, max(2 * k + 1, 24 if k > 1 else 16))
        try:
            vals, vecs = eigsh(op, k=k, which="SA", tol=tol, v0=v0, ncv=ncv, maxiter=200000)
        except ArpackNoConvergence as exc:
            raise RuntimeError("ARPACK did not converge: %s" % exc)
        vals = vals + shift
        o = np.argsort(vals)
        vals, vecs = vals[o], vecs[:, o]
        method = "arpack"
    res = []
    for i in range(k):
        v = vecs[:, i]
        res.append(float(np.linalg.norm(sec.apply(v, P) - vals[i] * v)))
    info = dict(method=method, nmatvec=sec.nmatvec - nm0, time=time.time() - t0, resid=max(res))
    return np.array(vals), vecs, info


def expect(sec, P, v):
    return float(np.dot(v, sec.apply(v, P)) / np.dot(v, v))


# ----------------------------------------------------------------------------
# Problem: one (delta, cut, grid, prescription)
# ----------------------------------------------------------------------------


class Problem:
    def __init__(self, delta, cut, h, M, presc="raw", bath=None):
        assert presc in ("raw", "literal", "consistent")
        self.delta, self.cut, self.presc = delta, cut, presc
        self.bath = bath if bath is not None else Bath(delta, cut)
        self.zm = ZeroMode(h, M)
        self._sec = {}
        self._v0 = {}
        self._shift = {}
        self._scache = {}
        self.stats = dict(nmatvec=0, neig=0, eig_time=0.0, max_resid=0.0)

    def sector(self, f, L):
        key = (f, L)
        if key not in self._sec:
            self._sec[key] = Sector(self.bath, self.zm, f, L)
        return self._sec[key]

    def _solve(self, f, L, P, k, tag):
        sec = self.sector(f, L)
        key = (f, L, tag)
        v0 = self._v0.get(key)
        if v0 is not None and len(v0) != sec.dim:
            v0 = None
        shift = self._shift.get((f, L))
        vals, vecs, info = eig_lowest(sec, P, k, v0=v0, shift=shift)
        self._v0[key] = vecs[:, 0].copy()
        self._shift[(f, L)] = float(vals[0]) - 1.0
        self.stats["nmatvec"] += info["nmatvec"]
        self.stats["neig"] += 1
        self.stats["eig_time"] += info["time"]
        self.stats["max_resid"] = max(self.stats["max_resid"], info["resid"])
        return vals, vecs, info

    def _dexp(self, sec, v):
        Pr = sec.prepare(COEF_DR)
        Pg = sec.prepare(COEF_DG)
        return np.array([expect(sec, Pr, v), expect(sec, Pg, v)])

    def window_table(self, r, g):
        """Ev(L) for L=0,2,..,cut and dEv/d(r,g)."""
        cut = self.cut
        co = coefs_H(self.delta, r, g)
        Ev = np.full(cut + 1, np.nan)
        dEv = np.full((cut + 1, 2), np.nan)
        # L = 0: zero mode alone (field-even)
        sec = self.sector(0, 0)
        P = sec.prepare(co)
        vals, vecs, _ = self._solve(0, 0, P, 1, "w")
        Ev[0] = vals[0]
        dEv[0] = self._dexp(sec, vecs[:, 0])
        fp_iters = {}
        for L in range(2, cut + 1, 2):
            sec = self.sector(0, L)
            if self.presc == "literal":
                P = sec.prepare(co)
                vals, vecs, _ = self._solve(0, L, P, 1, "w")
                Ev[L] = vals[0]
                dEv[L] = self._dexp(sec, vecs[:, 0])
                continue
            # consistent: s = lambda_min(H(L) + diag(s - Ev(L-N)) on N>0)
            s = self._scache.get(L, Ev[L - 2])
            it = 0
            Fprev = None
            while True:
                it += 1
                D = np.zeros(cut + 1)
                for N in range(2, L + 1, 2):
                    D[N] = s - Ev[L - N]
                P = sec.prepare(co, D)
                vals, vecs, _ = self._solve(0, L, P, 1, "w")
                lam = vals[0]
                w = sec.level_weights(vecs[:, 0], cut)
                p0 = w[0]
                F = lam - s
                if abs(F) < 1e-13 * max(1.0, abs(s)):
                    break
                # Newton is monotone and quadratic; stagnation at the roundoff
                # floor of the eigensolver ends the iteration
                if Fprev is not None and abs(F) >= 0.25 * abs(Fprev) and abs(F) < 1e-11 * max(1.0, abs(s)):
                    break
                Fprev = F
                if it > 60:
                    raise RuntimeError("window fixed point did not converge at L=%d (F=%g)" % (L, F))
                s = s + F / p0
            Ev[L] = lam
            self._scache[L] = lam
            fp_iters[L] = it
            v = vecs[:, 0]
            dH = self._dexp(sec, v)
            corr = np.zeros(2)
            for N in range(2, L + 1, 2):
                corr += w[N] * dEv[L - N]
            dEv[L] = (dH - corr) / w[0]
        return Ev, dEv, fp_iters

    def evaluate(self, r, g, k=4):
        """Levels in both field parities (reflection-even), with derivatives."""
        cut = self.cut
        co = coefs_H(self.delta, r, g)
        out = {"r": r, "g": g}
        if self.presc == "raw":
            D = None
            Ev = dEv = None
        else:
            Ev, dEv, fp_iters = self.window_table(r, g)
            D = np.zeros(cut + 1)
            dD = np.zeros((cut + 1, 2))
            for N in range(2, cut + 1, 2):
                D[N] = Ev[cut] - Ev[cut - N]
                dD[N] = dEv[cut] - dEv[cut - N]
            out["Ev"] = Ev.tolist()
            out["dEv"] = dEv.tolist()
            out["fp_iters"] = fp_iters
        for f, name in ((0, "even"), (1, "odd")):
            sec = self.sector(f, cut)
            P = sec.prepare(co, D)
            vals, vecs, info = self._solve(f, cut, P, k, "main")
            der = []
            wts = []
            for i in range(k):
                v = vecs[:, i]
                d = self._dexp(sec, v)
                w = sec.level_weights(v, cut)
                if D is not None:
                    d = d + w @ dD
                der.append(d)
                wts.append(w.tolist())
            out[name] = vals.tolist()
            out["d" + name] = np.array(der).tolist()
            out["w" + name] = wts
            out["resid_" + name] = info["resid"]
            rho = sec.zero_mode_density(vecs[:, 0])
            out["edge_" + name] = float(rho[-3:].sum())
        if self.presc == "consistent":
            out["consistency"] = out["even"][0] - Ev[cut]
        return out


def residuals(delta, ev):
    e0 = ev["even"][0]
    return np.array([ev["odd"][0] - e0 - delta, ev["odd"][1] - e0 - (1.0 - delta)])


def jacobian(ev):
    de0 = np.array(ev["deven"][0])
    return np.array([np.array(ev["dodd"][0]) - de0, np.array(ev["dodd"][1]) - de0])


def delta_eps(ev):
    return ev["even"][1] - ev["even"][0]


def d_delta_eps(ev):
    return np.array(ev["deven"][1]) - np.array(ev["deven"][0])


def tune(prob, r0, g0, tol=1e-12, maxit=60, log=None):
    th = np.array([r0, g0], dtype=float)
    ev = prob.evaluate(*th)
    F = residuals(prob.delta, ev)
    hist = []
    for it in range(maxit):
        nF = np.max(np.abs(F))
        hist.append(dict(it=it, r=th[0], g=th[1], F=F.tolist()))
        if log:
            log("  newton it=%d r=%.15g g=%.15g |F|=%.3e" % (it, th[0], th[1], nF))
        if nF < tol:
            break
        J = jacobian(ev)
        step = -np.linalg.solve(J, F)
        lam = 1.0
        accepted = False
        while lam > 1e-4:
            thn = th + lam * step
            try:
                evn = prob.evaluate(*thn)
                Fn = residuals(prob.delta, evn)
                ok = np.all(np.isfinite(Fn))
            except Exception as exc:  # failing trial point: reject, shrink
                if log:
                    log("    trial failed (%s), shrinking" % exc)
                ok = False
            if ok and (np.max(np.abs(Fn)) < (1 - 1e-4 * lam) * nF or np.max(np.abs(Fn)) < 3 * tol):
                accepted = True
                break
            lam *= 0.5
        if not accepted:
            if nF < 1e-11:
                break  # roundoff floor reached
            raise RuntimeError("Newton line search failed at |F|=%g" % nF)
        th, ev, F = thn, evn, Fn
    ev["newton_hist"] = hist
    return th, ev


# ----------------------------------------------------------------------------
# Grid choice: Born-Oppenheimer effective potential for the zero mode
# ----------------------------------------------------------------------------


def bo_potential(delta, r, g, qs, Nbo):
    b = Bath(delta, Nbo)
    co = coefs_H(delta, r, g)
    nE, nO = len(b.EbE), len(b.EbO)
    out = np.empty(len(qs))
    for i, q in enumerate(qs):
        L1 = co["l1"][0] * q + co["l1"][1] * q ** 3
        L2 = co["l2"][0] + co["l2"][1] * q ** 2
        L3 = co["l3"] * q
        H = np.zeros((nE + nO, nE + nO))
        H[:nE, :nE] = np.diag(b.EbE) + L2 * b.W2EE + co["l4"] * b.W4EE
        H[nE:, nE:] = np.diag(b.EbO) + L2 * b.W2OO + co["l4"] * b.W4OO
        H[:nE, nE:] = L1 * b.W1EO + L3 * b.W3EO
        H[nE:, :nE] = H[:nE, nE:].T
        e0 = sla.eigh(H, eigvals_only=True, subset_by_index=[0, 0])[0]
        out[i] = co["v2"] * q ** 2 + co["v4"] * q ** 4 + co["c"] + e0
    return out


def dvr1d_levels(delta, Vfun, h, M, nlev):
    zm = ZeroMode(h, M)
    Ve, Vo = Vfun(zm.qe), Vfun(zm.qo)
    we = np.linalg.eigvalsh(delta * zm.Te + np.diag(Ve))
    wo = np.linalg.eigvalsh(delta * zm.To + np.diag(Vo))
    w = np.sort(np.concatenate([we, wo]))
    return w[:nlev]


def choose_grid(delta, r, g, Nbo=10, nlev=20, wkb_target=36.0, log=None):
    """Starting grid from the 1D Born-Oppenheimer zero-mode problem
    -delta d^2/dq^2 + V(q) + c + e_bath(q):
      * box Q: WKB decay integral int kappa dq >= wkb_target beyond the outer
        turning point of E_top = (nlev-th 1D level) + 2 (amplitude ~e^-36);
      * spacing h: lowest nlev 1D levels stable under h -> h/1.5 in that box,
        to max(2e-12, 200 eps ||H||) (roundoff-aware).
    The full problem is verified separately (solve_point)."""
    cache = {}

    def Vfun(q):
        q = np.abs(np.asarray(q, dtype=float))
        keys = np.round(q, 12)
        miss = [x for x in np.unique(keys) if x not in cache]
        if miss:
            vals = bo_potential(delta, r, g, np.array(miss), Nbo)
            cache.update(dict(zip(miss, vals)))
        return np.array([cache[x] for x in keys])

    A = delta / 4 + r - g / 2
    scales = [math.sqrt(2.0)]
    if g > 0:
        scales.append((12 * delta / g) ** (1 / 6))
    if A > 0:
        scales.append((delta / A) ** 0.25)
    ell = min(scales)
    # provisional box: V_eff rises well above the low spectrum
    qs = np.linspace(0, 4 * ell, 81)
    Vmin = Vfun(qs).min()
    Qp = 4 * ell
    hp = ell / 5
    for _ in range(30):
        lev = dvr1d_levels(delta, Vfun, hp, int(math.ceil(Qp / hp)), nlev)
        Vmin = min(Vmin, Vfun(np.linspace(0, Qp, 121)).min())
        Etop = lev[-1] + 2.0
        if Vfun(np.array([Qp]))[0] > Etop + 50.0 * max(1.0, Etop - lev[0]):
            break
        Qp *= 1.3
    # outer turning point of Etop, then WKB decay integral
    qgrid = np.linspace(0, Qp, 2001)
    V = Vfun(qgrid)
    above = np.where(V < Etop)[0]
    qt = qgrid[above[-1]] if len(above) else 0.0
    dq = ell / 100
    q0, integ, Q = qt, 0.0, None
    for _ in range(200):
        qq = q0 + dq * (np.arange(200) + 0.5)
        kap = np.sqrt(np.maximum(Vfun(qq) - Etop, 0.0) / delta)
        cum = integ + np.cumsum(kap) * dq
        hit = np.where(cum >= wkb_target)[0]
        if len(hit):
            Q = q0 + dq * (hit[0] + 1)
            break
        integ, q0 = cum[-1], q0 + 200 * dq
    if Q is None:
        raise RuntimeError("WKB box search failed")
    # spacing in the fixed box
    h = ell / 4
    for _ in range(20):
        M = int(math.ceil(Q / h))
        base = dvr1d_levels(delta, Vfun, h, M, nlev)
        fine = dvr1d_levels(delta, Vfun, h / 1.5, int(math.ceil(Q / (h / 1.5))), nlev)
        normH = delta * math.pi ** 2 / (h / 1.5) ** 2 + np.max(np.abs(Vfun(np.linspace(0, Q, 41))))
        tol = max(2e-12, 200 * 2.2e-16 * normH)
        df = np.max(np.abs(fine - base))
        if log:
            log("  grid1d Etop=%.4g qt=%.4g Q=%.5g h=%.5g M=%d dfine=%.2e tol=%.1e" % (Etop, qt, Q, h, M, df, tol))
        if df < tol:
            break
        h /= 1.25
    return h, Q


def grid_variant(h, Q, kind):
    if kind == "base":
        return h, int(math.ceil(Q / h - 1e-9))
    if kind == "fine":
        hf = h / 1.5
        return hf, int(math.ceil(Q / hf - 1e-9))
    if kind == "wide":
        return h, int(math.ceil(1.5 * Q / h - 1e-9))
    raise ValueError(kind)


# ----------------------------------------------------------------------------
# Full point solve: tune + grid verification (+ refinement loop)
# ----------------------------------------------------------------------------


CODE_VERSION = "indep_ht v2 (2026-10-08): best-of-rounds grid verification, grid_tol 1e-10"


def solve_point(delta, cut, presc, r0, g0, h=None, Q=None, grid_tol=1e-10, tune_tol=1e-12, log=print,
                verify=True, max_refine=3):
    """Tune (r, g) at (delta, cut, presc) and verify the zero-mode grid.

    Verification: at the tuned couplings the full problem (incl. the window
    table) is recomputed on a 1.5x finer and on a 1.5x wider grid; the tuned
    Delta_eps change is estimated by the linearized retune
    dDe - dDe/dtheta . J^-1 dF.  If it (or any relative level change) exceeds
    grid_tol, the offending direction is refined and the point retuned.  Real
    discretization errors fall fast under refinement, the double-precision
    floor does not; the round with the smallest check differences is kept."""
    t0 = time.time()
    if h is None:
        h, Q = choose_grid(delta, r0, g0, Nbo=min(cut, 10) if cut > 0 else 0, log=log)
        h, Q = h / 1.15, Q * 1.15  # safety margin
    bath = Bath(delta, cut)
    rounds = []
    th = (r0, g0)
    for rnd in range(max_refine + 1):
        hb, Mb = grid_variant(h, Q, "base")
        prob = Problem(delta, cut, hb, Mb, presc, bath=bath)
        log("[%s d=%.6g N=%d] grid h=%.6g Q=%.6g M=%d dim_even=%d" % (presc, delta, cut, hb, Q, Mb,
                                                                   prob.sector(0, cut).dim))
        th, ev = tune(prob, th[0], th[1], tol=tune_tol, log=log)
        rec = dict(delta=delta, N=cut, presc=presc, r=float(th[0]), g=float(th[1]),
                   A=delta / 4 + th[0] - th[1] / 2,
                   E_even=[x - ev["even"][0] for x in ev["even"]],
                   E_odd=[x - ev["even"][0] for x in ev["odd"]],
                   E_even_abs=ev["even"], E_odd_abs=ev["odd"],
                   Delta_eps=delta_eps(ev), tuning_residuals=residuals(delta, ev).tolist(),
                   grid=prob.zm.desc(), stats=prob.stats, newton_hist=ev["newton_hist"],
                   eig_resid=dict(even=ev["resid_even"], odd=ev["resid_odd"]),
                   edge_density=dict(even=ev["edge_even"], odd=ev["edge_odd"]),
                   level_weights_even0=ev["weven"][0], grid_hQ=[h, Q], code_version=CODE_VERSION)
        if presc != "raw":
            rec["Ev"] = ev["Ev"]
            rec["fp_iters"] = ev.get("fp_iters")
        if presc == "consistent":
            rec["consistency_E0_minus_Evcut"] = ev["consistency"]
        if not verify:
            rec["grid_check"] = None
            rounds.append((0.0, rec))
            break
        J = jacobian(ev)
        dDe = d_delta_eps(ev)
        checks = {}
        for kind in ("fine", "wide"):
            hv, Mv = grid_variant(h, Q, kind)
            pv = Problem(delta, cut, hv, Mv, presc, bath=bath)
            evv = pv.evaluate(*th)
            dF = residuals(delta, evv) - residuals(delta, ev)
            dD = delta_eps(evv) - delta_eps(ev)
            dth = -np.linalg.solve(J, dF)
            dD_tuned = dD + dDe @ dth
            dlev = max(np.max(np.abs(np.array(evv["even"]) - evv["even"][0] - (np.array(ev["even"]) - ev["even"][0]))),
                       np.max(np.abs(np.array(evv["odd"]) - evv["even"][0] - (np.array(ev["odd"]) - ev["even"][0]))))
            checks[kind] = dict(h=hv, M=Mv, dF=dF.tolist(), dDelta_eps_fixed=float(dD),
                                dDelta_eps_tuned_lin=float(dD_tuned), dtheta_lin=dth.tolist(),
                                max_dlevel_rel=float(dlev))
            log("  check %s: h=%.5g M=%d dF=%s dDe(fixed)=%.2e dDe(tuned,lin)=%.2e maxdlev=%.2e" % (
                kind, hv, Mv, np.array2string(dF, precision=2), dD, dD_tuned, dlev))
        rec["grid_check"] = checks
        score = max(abs(checks[k]["dDelta_eps_tuned_lin"]) for k in checks)
        score = max(score, max(checks[k]["max_dlevel_rel"] for k in checks))
        rec["grid_check_max"] = score
        rounds.append((score, rec))
        bad_f = abs(checks["fine"]["dDelta_eps_tuned_lin"]) > grid_tol or checks["fine"]["max_dlevel_rel"] > grid_tol
        bad_w = abs(checks["wide"]["dDelta_eps_tuned_lin"]) > grid_tol or checks["wide"]["max_dlevel_rel"] > grid_tol
        if not (bad_f or bad_w):
            break
        if len(rounds) >= 2 and score > 0.5 * rounds[-2][0]:
            log("  grid check not improving under refinement (%.2e -> %.2e): double-precision floor" % (
                rounds[-2][0], score))
            break
        if rnd == max_refine:
            break
        if bad_f:
            h /= 1.3
        if bad_w:
            Q *= 1.3
        log("  refining grid -> h=%.6g Q=%.6g" % (h, Q))
    best = min(rounds, key=lambda x: x[0])[1]
    if verify and best["grid_check_max"] > grid_tol:
        best["grid_warning"] = "grid check %.2e > grid_tol %.0e (floor)" % (best["grid_check_max"], grid_tol)
    best["refine_hist"] = [dict(h=r["grid_hQ"][0], Q=r["grid_hQ"][1], check_max=sc, Delta_eps=r["Delta_eps"],
                                checks=r.get("grid_check")) for sc, r in rounds]
    best["wall_time"] = time.time() - t0
    return best


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------


def jdump(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(obj, fh, indent=1, default=float)
    os.replace(tmp, path)


def _key(d, N, presc):
    return (round(float(d), 10), int(N), presc)


def load_guess(spec, log=None):
    """Read (r, g, grid) of another point from a results file.  With
    spec["wait"], poll until the producing process has written it."""
    t0 = time.time()
    while True:
        res = []
        if os.path.exists(spec["file"]):
            try:
                res = json.load(open(spec["file"]))
            except ValueError:
                res = []
        c = [x for x in res if _key(x["delta"], x["N"], x["presc"]) == _key(spec["delta"], spec["N"], spec["presc"])]
        ok = [x for x in c if "Delta_eps" in x]
        if ok:
            return ok[-1]["r"], ok[-1]["g"], ok[-1].get("grid_hQ")
        if c and "failed" in c[-1]:
            raise RuntimeError("guess_from: producer failed %r" % spec)
        if not spec.get("wait") or time.time() - t0 > spec.get("max_wait", 23.5 * 3600):
            raise RuntimeError("guess_from: no record %r" % spec)
        time.sleep(30)


def predictor(item, solved):
    """Initial (r, g) and optional grid for a point."""
    d, N, presc = item["delta"], item["N"], item["presc"]
    if "r0" in item:
        return item["r0"], item["g0"], None, "explicit"
    if "guess_from" in item:
        r, g, grid = load_guess(item["guess_from"])
        return r, g, grid, "guess_from"
    same_d = [x for x in solved if abs(x["delta"] - d) < 1e-12 and x["presc"] == presc and x["N"] != N]
    if same_d:
        x = same_d[-1]
        return x["r"], x["g"], x.get("grid_hQ"), "same delta N=%d" % x["N"]
    chain = [x for x in solved if x["N"] == N and x["presc"] == presc]
    if len(chain) >= 2 and abs(chain[-1]["delta"] - chain[-2]["delta"]) > 1e-14:
        p1, p0 = chain[-1], chain[-2]
        t = (d - p1["delta"]) / (p1["delta"] - p0["delta"])
        return p1["r"] + t * (p1["r"] - p0["r"]), p1["g"] + t * (p1["g"] - p0["g"]), None, "linear extrapolation"
    if chain:
        return chain[-1]["r"], chain[-1]["g"], None, "previous chain point"
    return 0.0, (1 - 4 * d) / 3.0, None, "first order g=eps/3"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, help="JSON task file")
    ap.add_argument("--out", required=True)
    ap.add_argument("--log", default=None)
    args = ap.parse_args()
    task = json.load(open(args.task))
    logf = open(args.log, "a") if args.log else sys.stdout

    def log(msg):
        logf.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
        logf.flush()

    log("start task %s pid %d host %s threads %s" % (args.task, os.getpid(), os.uname().nodename,
                                                     os.environ.get("OPENBLAS_NUM_THREADS")))
    results = json.load(open(args.out)) if os.path.exists(args.out) else []
    solved = [x for x in results if "Delta_eps" in x]
    done = {_key(x["delta"], x["N"], x["presc"]) for x in solved}
    queue = [dict(it) for it in task["points"]]
    while queue:
        item = queue.pop(0)
        d, N, presc = item["delta"], item["N"], item["presc"]
        if _key(d, N, presc) in done:
            continue
        r0, g0, grid, how = predictor(item, solved)
        h = Q = None
        if grid is not None and item.get("reuse_grid", True):
            h, Q = grid
        log("=== point delta=%.8g N=%d presc=%s guess r=%.12g g=%.12g (%s)%s" % (
            d, N, presc, r0, g0, how, " grid h=%.5g Q=%.5g" % (h, Q) if h else ""))
        try:
            rec = solve_point(d, N, presc, r0, g0, h=h, Q=Q, log=log, verify=item.get("verify", True))
        except Exception as exc:
            log("FAILED delta=%.8g N=%d %s: %r" % (d, N, presc, exc))
            chain = [x for x in solved if x["N"] == N and x["presc"] == presc]
            depth = item.get("depth", 0)
            if chain and depth < 8 and "r0" not in item:
                dmid = 0.5 * (chain[-1]["delta"] + d)
                log("    inserting intermediate continuation point delta=%.8g" % dmid)
                item["depth"] = depth + 1
                queue.insert(0, item)
                queue.insert(0, dict(delta=dmid, N=N, presc=presc, verify=False, depth=depth + 1, aux=True))
            else:
                results.append(dict(delta=d, N=N, presc=presc, failed=repr(exc)))
                jdump(results, args.out)
            continue
        rec["guess"] = [r0, g0, how]
        rec["aux"] = bool(item.get("aux", False)) or not item.get("verify", True)
        rec["host"] = os.uname().nodename
        results.append(rec)
        solved.append(rec)
        done.add(_key(d, N, presc))
        jdump(results, args.out)
        log("=== done delta=%.8g N=%d %s: Delta_eps=%.13f g=%.12g r=%.12g |F|=%.1e t=%.0fs" % (
            d, N, presc, rec["Delta_eps"], rec["g"], rec["r"], max(map(abs, rec["tuning_residuals"])),
            rec["wall_time"]))
    log("ALL DONE")


if __name__ == "__main__":
    main()
