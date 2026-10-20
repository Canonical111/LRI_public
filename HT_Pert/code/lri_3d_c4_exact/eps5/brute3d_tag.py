#!/usr/bin/env python3
"""delta^(3)(L) of the Wcs window (WINDOW_SPEC 2.5a, 2D project) for the 3D model, by brute force on the package's
operators: the phi channel with its external zero-mode line tagged.

Tagged space: bath state b (package scalar basis), regular zero-mode number z, tags n_in, n_out in {0, 1}.
  phi_local = Z + X_in (annihilation only) + X_out^dag (creation only); tags are zero-mode copies: level 0 in H0,
  energy x0 each (they are particles), budget charges nu_in, nu_out: budget level = N_b + nu_in n_in + nu_out n_out
  <= L (cutoff and every window use the budget level).  M' = terms of M with >= 1 bath leg (zero modes and tags are
  zero-mode-like).  Windows: rule Wc at the outer cutoff L (D^zm on the regular zero mode only, D^M with budget
  levels), couplings and window objects from brute3d_W5.Solver(L, 'Wc').
  Glued RS: reference |X_in>; model states |X_in>, |X_out>, |z=1> excluded from every resolvent;
  E_n = phi_n[X_in] + phi_n[X_out].
c1tag(L; nu) = E_tag(L; nu) - E_0(L);  delta^(3)(L) = (1/4) [c_1^(3)(L - 2) - c1tag^(3)(L; 2, 2)] (both include 2 r_3).
Check: c1tag(L; 0, 0) = c_1(L) through eps^3.
usage: python3 brute3d_tag.py --L 8 [--out f.json]"""
import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brute3d_W5 as bw  # noqa: E402

DT = bw.DT
X0 = bw.X0
ZC = 16                      # regular zero-mode cap


def local_ops():
    """Normal powers Q_k = :(A + A^dag)^k: on (n_in, n_out, z), A = a + x_in, A^dag = a^dag + x_out^dag."""
    nz = ZC + 1
    a = np.diag(np.sqrt(np.arange(1, nz, dtype=DT)), 1)
    I2 = np.eye(2, dtype=DT)
    xin = np.array([[0, 1], [0, 0]], dtype=DT)          # |1> -> |0>
    xoutd = np.array([[0, 0], [1, 0]], dtype=DT)        # |0> -> |1>
    Iz = np.eye(nz, dtype=DT)
    kron = lambda A_, B_, C_: np.kron(np.kron(A_, B_), C_)
    A = kron(I2, I2, a) + kron(xin, I2, Iz)
    Ad = kron(I2, I2, a.T) + kron(I2, xoutd, Iz)
    from math import comb
    Q = []
    for k in range(5):
        q = np.zeros_like(A)
        for j in range(k + 1):
            q += comb(k, j) * np.linalg.matrix_power(Ad, j) @ np.linalg.matrix_power(A, k - j)
        Q.append(q)
    loc = [(ni, no, z) for ni in (0, 1) for no in (0, 1) for z in range(nz)]
    return Q, loc


class TagChannel:
    def __init__(self, sol, nu_in, nu_out):
        self.sol = sol
        L = sol.L
        self.Nb, self.Pb = sol.Nall, sol.Pall
        self.Q, self.loc = local_ops()
        nloc = len(self.loc)
        self.ztag = np.array([z for (_, _, z) in self.loc])
        tagch = np.array([ni * nu_in + no * nu_out for (ni, no, _) in self.loc])
        ntag = np.array([ni + no for (ni, no, _) in self.loc])
        self.blev = self.Nb[:, None] + tagch[None, :]
        Ptot = self.Pb[:, None] + self.ztag[None, :] + ntag[None, :]
        self.mask = (self.blev <= L) & (Ptot % 2 == 1)
        h0 = self.Nb[:, None] + DT(X0) * Ptot
        self.E0 = DT(X0)
        self.iX = (0, self.loc.index((1, 0, 0)))
        self.oX = (0, self.loc.index((0, 1, 0)))
        self.i1 = (0, self.loc.index((0, 0, 1)))
        den = self.E0 - h0
        for m in (self.iX, self.oX, self.i1):
            den[m] = np.inf
        den[~self.mask] = np.inf
        if np.any(np.abs(den) < 1e-9):
            raise RuntimeError("unexpected degeneracy in the tagged channel")
        self.den = den
        self.Ptot = Ptot
        v = np.zeros((len(self.Nb), nloc), dtype=DT)
        v[self.iX] = 1
        self.psi = [v]
        self.E = [self.E0]

    def op(self, terms, X):
        """sum over (bath_degree, local_degree, matrix) of W X Q^T, budget-projected."""
        out = np.zeros_like(X)
        for (jb, ld, W) in terms:
            out += (W @ X) @ self.Q[ld].T
        out[~self.mask] = 0
        return out

    def H(self, n, X):
        b = self.sol.bare
        out = self.op(b.terms[n], X)
        loc_only = b.r[n] * self.Q[2] + b.g[n] / 12 * self.Q[4]
        out += X @ loc_only.T
        if n == 1:
            out -= DT(1) / 4 * self.Ptot * X
        out[~self.mask] = 0
        if n >= 2:
            out += self.windows(n, X)
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
                Mp = [(jb, 2 - jb, W) for (jb, _, W) in sol.Mp[j]]
                out += DT(0.25) * (dc * self.op(Mp, X) + self.op(Mp, dc * X))
        out[~self.mask] = 0
        return out

    def run(self, nmax=3):
        for n in range(1, nmax + 1):
            phi = np.zeros_like(self.psi[0])
            for k in range(1, n + 1):
                phi += self.H(k, self.psi[n - k])
            for j in range(1, n):
                phi -= self.E[j] * self.psi[n - j]
            En = phi[self.iX] + phi[self.oX]
            self.E.append(En)
            psi = phi / self.den
            self.psi.append(psi)
        return self.E


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    t0 = time.time()
    sol = bw.Solver(a.L, "Wc")
    sol.run()
    L = a.L
    E0 = sol.prim[0].E
    res = {"L": L, "r": [float(x) for x in sol.bare.r[:4]], "c1": {}}
    for k in (2, 3):
        res["c1"][k] = {l: float(sol.c1[k][l]) for l in sol.cuts}
    for nu in ((0, 0), (2, 2), (2, 0), (0, 2)):
        tc = TagChannel(sol, *nu)
        E = tc.run(3)
        c1tag = [float(E[n] - E0[n]) for n in range(4)]
        res[f"c1tag_{nu[0]}_{nu[1]}"] = c1tag
        print(f"L={L} nu={nu}: c1tag^(2) = {c1tag[2]:+.14f}  c1tag^(3) = {c1tag[3]:+.14f}   "
              f"[c1^(2)(L) = {float(sol.c1[2][L]):+.14f}, c1^(3)(L) = {float(sol.c1[3][L]):+.14f}]", flush=True)
    if L >= 2:
        d3 = 0.25 * (float(sol.c1[3][L - 2]) - res["c1tag_2_2"][3])
        res["delta3"] = d3
        print(f"L={L} delta^(3) = {d3:+.14f}   ({time.time() - t0:.1f}s)", flush=True)
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
