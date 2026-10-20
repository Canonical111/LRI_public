#!/usr/bin/env python3
"""Tagged descendant channel (2D project, residual_log Sec. 11.1) in 3D: the external chi_11 line tagged.

chi_11 = one bath quantum (n = 1, l = 0) at level 2.  Its wave function is Y_00 (constant on S^2), so a tagged copy
couples exactly like the zero mode with amplitude u_10(eps) instead of 1:
  phi_local = Z + u_10(eps) (X_in + X_out^dag),  X_in absorbed only, X_out created only (once);
  tags are particles of level 2 (H0 = x + 2 each), budget charges nu_in, nu_out:
  budget level = N_b + nu_in n_in + nu_out n_out <= L (cutoff and every window use the budget level).
Tagged space: bath state b (package scalar basis), regular zero-mode number z, tags n_in, n_out in {0, 1}.
H_n = sum_c terms[n - c] (x) Q^(c) + local couplings, Q^(c) = eps^c part of :(A + A^dag)^k: with
A = a + u_10(eps) x_in (u_10 Taylor from the package's amplitude_taylor).
Windows: scheme Wc at the outer cutoff L (D^zm on the regular zero mode, budget levels; D^M = (1/4){Delta c_1(N_budget),
M'} with M' = M - :Z^2:, tag legs counted as bath legs).  Couplings and window objects from brute3d_W5.Solver(L, 'Wc').
Glued RS: reference |X_in>; model states |X_in>, |X_out>, regular |chi_11> excluded from every resolvent;
E_n = phi_n[X_in] + phi_n[X_out] (histories ending on the regular chi_11 dropped).
R_n(nu) = [eps^n](E_tag - E(phi) - 2).  Check: nu = (2, 2) reproduces the real channel (brute3d_desc, scheme Wc).
usage: python3 brute3d_tagchi.py --L 8 [--nus 0:0,2:2,2:0,0:2] [--out f.json]"""
import argparse
import json
import os
import sys
import time
from math import comb

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brute3d_W5 as bw  # noqa: E402
import taylor_vertices as tv  # noqa: E402  (package reference module; path set by brute3d_W5)

DT = bw.DT
X0 = bw.X0
ZC = 16
NORD = 3


def local_ops(u):
    """Q[c][k] = eps^c part of :(A + A^dag)^k: on (n_in, n_out, z), A = a + u(eps) x_in, A^dag = a^dag + u(eps) x_out^dag.
    Also Q2t[c] = eps^c part of Q_2 - :Z^2: (the tag legs of the local mass term, counted in M')."""
    nz = ZC + 1
    a = np.diag(np.sqrt(np.arange(1, nz, dtype=DT)), 1)
    I2 = np.eye(2, dtype=DT)
    xin = np.array([[0, 1], [0, 0]], dtype=DT)
    xoutd = np.array([[0, 0], [1, 0]], dtype=DT)
    Iz = np.eye(nz, dtype=DT)
    kron = lambda A_, B_, C_: np.kron(np.kron(A_, B_), C_)

    def Qs(s):
        A = kron(I2, I2, a) + s * kron(xin, I2, Iz)
        Ad = kron(I2, I2, a.T) + s * kron(I2, xoutd, Iz)
        out = []
        for k in range(5):
            q = np.zeros_like(A)
            for j in range(k + 1):
                q += comb(k, j) * np.linalg.matrix_power(Ad, j) @ np.linalg.matrix_power(A, k - j)
            out.append(q)
        return out
    q0, qp, qm = Qs(DT(0)), Qs(DT(1)), Qs(DT(-1))
    parts = [[q0[k], (qp[k] - qm[k]) / 2, (qp[k] + qm[k]) / 2 - q0[k]] for k in range(5)]   # t = 0, 1, 2 tag ops
    u1 = np.array(u, dtype=DT)
    u2 = np.array([sum(u1[i] * u1[c - i] for i in range(c + 1)) for c in range(len(u1))], dtype=DT)
    Q, Q2t = [], []
    for c in range(len(u1)):
        Q.append([(parts[k][0] if c == 0 else 0 * parts[k][0]) + u1[c] * parts[k][1] + u2[c] * parts[k][2]
                  for k in range(5)])
        Q2t.append(u1[c] * parts[2][1] + u2[c] * parts[2][2])
    loc = [(ni, no, z) for ni in (0, 1) for no in (0, 1) for z in range(nz)]
    return Q, Q2t, loc


class TagChiChannel:
    def __init__(self, sol, nu_in, nu_out):
        self.sol = sol
        L = sol.L
        self.Nb, self.Pb = sol.Nall, sol.Pall
        u = tv.amplitude_taylor(1, 0, NORD, DT)
        self.Q, self.Q2t, self.loc = local_ops(u)
        nloc = len(self.loc)
        self.ztag = np.array([z for (_, _, z) in self.loc])
        tagch = np.array([ni * nu_in + no * nu_out for (ni, no, _) in self.loc])
        ntag = np.array([ni + no for (ni, no, _) in self.loc])
        self.blev = self.Nb[:, None] + tagch[None, :]
        Ptot = self.Pb[:, None] + self.ztag[None, :] + ntag[None, :]
        self.mask = (self.blev <= L) & (Ptot % 2 == 1)
        h0 = self.Nb[:, None] + 2 * ntag[None, :] + DT(X0) * Ptot
        self.E0 = DT(X0) + 2
        self.iX = (0, self.loc.index((1, 0, 0)))
        self.oX = (0, self.loc.index((0, 1, 0)))
        rows = [b for b in range(len(self.Nb)) if self.Nb[b] == 2 and self.Pb[b] == 1]
        if len(rows) != 1:
            raise RuntimeError("expected one scalar one-quantum level-2 bath state")
        self.ichi = (rows[0], self.loc.index((0, 0, 0)))
        den = self.E0 - h0
        for m in (self.iX, self.oX, self.ichi):
            den[m] = np.inf
        den[~self.mask] = np.inf
        if np.any(np.abs(den) < 1e-9):
            raise RuntimeError("unexpected degeneracy in the tagged chi channel")
        self.den = den
        self.Ptot = Ptot
        v = np.zeros((len(self.Nb), nloc), dtype=DT)
        v[self.iX] = 1
        self.psi = [v]
        self.E = [self.E0]

    def op(self, terms, X, Ql):
        out = np.zeros_like(X)
        for (jb, ld, W) in terms:
            out += (W @ X) @ Ql[ld].T
        return out

    def H(self, n, X):
        b = self.sol.bare
        out = np.zeros_like(X)
        for c in range(0, n):
            k = n - c
            if c >= len(self.Q):
                break
            out += self.op(b.terms[k], X, self.Q[c])
            out += X @ (b.r[k] * self.Q[c][2] + b.g[k] / 12 * self.Q[c][4]).T
        if n == 1:
            out -= DT(1) / 4 * self.Ptot * X
        out[~self.mask] = 0
        if n >= 2:
            out += self.windows(n, X)
        return out

    def Mp_apply(self, j, X):
        """M'_j X: eps^j part of M' = 2 W0 (x) Q_1 + W1 (x) Q_0 + (Q_2 - :Z^2:), tag amplitudes convolved."""
        sol = self.sol
        out = np.zeros_like(X)
        for c in range(0, j + 1):
            if c >= len(self.Q):
                break
            for (jb, _, W) in sol.Mp[j - c]:
                out += (W @ X) @ self.Q[c][2 - jb].T
            out += X @ self.Q2t[c].T if c == j else 0 * X
        return out

    def windows(self, n, X):
        sol = self.sol
        L = sol.L
        out = np.zeros_like(X)
        comps = sol.comp.get(n, set())
        if "DZ" in comps and n in sol.h:
            hL = sol.h[n][L]
            rows, cols = np.nonzero((X != 0) & (self.blev >= 2))
            for b, c in zip(rows, cols):
                ni, no, z = self.loc[c]
                if z > bw.ZMAX:
                    continue
                hd = hL - sol.h[n][L - self.blev[b, c]]
                for zp in range(z % 2, bw.ZMAX + 1, 2):
                    if hd[zp, z] != 0:
                        out[b, self.loc.index((ni, no, zp))] += hd[zp, z] * X[b, c]
        if "DM" in comps:
            for j in range(0, n - 1):
                k = n - j
                c1 = sol.c1[k]
                dc = np.vectorize(lambda lev: c1[L] - c1[L - lev] if 0 < lev <= L else DT(0), otypes=[object])(self.blev)
                dc = dc.astype(DT)
                out += DT(0.25) * (dc * self.Mp_apply(j, X) + self.Mp_apply(j, dc * X))
        out[~self.mask] = 0
        return out

    def run(self, nmax=NORD):
        for n in range(1, nmax + 1):
            phi = np.zeros_like(self.psi[0])
            for k in range(1, n + 1):
                phi += self.H(k, self.psi[n - k])
            for j in range(1, n):
                phi -= self.E[j] * self.psi[n - j]
            self.E.append(phi[self.iX] + phi[self.oX])
            self.psi.append(phi / self.den)
        return self.E


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--nus", default="0:0,2:2,2:0,0:2")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    t0 = time.time()
    sol = bw.Solver(a.L, "Wc")
    sol.run()
    Ephi = sol.prim[1].E
    res = {"L": a.L}
    for s in a.nus.split(","):
        nu = tuple(int(x) for x in s.split(":"))
        tc = TagChiChannel(sol, *nu)
        E = tc.run(NORD)
        R = [float(E[n] - Ephi[n]) for n in range(NORD + 1)]
        R[0] -= 2.0
        res[f"R_{nu[0]}_{nu[1]}"] = R
        print(f"L={a.L} nu={nu}: R_1 = {R[1]:+.3e}  R_2 = {R[2]:+.12f}  R_3 = {R[3]:+.12f}  ({time.time() - t0:.1f}s)",
              flush=True)
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
