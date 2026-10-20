#!/usr/bin/env python3
"""Brute-force check of the window shifts with the package's own reference RS solver (read-only import of
lri_3d_hpc/reference/perturbative.py and its vendor vertex builder), small L only.

Schemes compared through C_4 (only the eps^2 window D2 reaches C_4):
  raw         D = 0
  consistent  package mode 'consistent'
  zeromode    D2(state) = E_z^(2)(L) - E_z^(2)(L - N_bath), z = zero-mode occupation of the state, E_z^(2)(l) the
              second-order energy of the auxiliary channel |z> at bath cutoff l (same couplings), z <= 7.

usage: python3 brute_zm.py --cutoffs 0 2 4 6 [--out results/brute_zm.json]
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..", "lri_3d_hpc")
sys.path.insert(0, os.path.join(PKG, "reference"))
sys.path.insert(0, os.path.join(PKG, "vendor"))
import perturbative as ref  # noqa: E402
from taylor_vertices import build_taylor_vertices  # noqa: E402


class ZMSeed(ref.SeedSeries):
    """Seed with a state-resolved (bath, local) window at order 2 only."""
    W2 = None

    def apply(self, n, X):
        out = self.bare.apply(n, X, self.field, self.N, self.P)
        if n == 2 and self.W2 is not None:
            out += self.W2 * X
        return out


def solve_zm(N, P, W, cutoff, order=4, nz=10, dtype=np.float64, zmax=7):
    nb = int(np.sum(N <= cutoff))
    N, P = np.asarray(N[:nb]), np.asarray(P[:nb])
    W = [[a[:nb, :nb].astype(dtype) for a in s] for s in W]
    bare = ref.BareSeries(N, P, W, nz, order, dtype)
    roots = {p: ZMSeed(bare, cutoff, p, "raw") for p in range(4)}
    aux = {(z, l): ref.SeedSeries(bare, l, z, "raw") for z in range(zmax + 1) for l in range(0, cutoff + 1, 2)}
    C = np.zeros(order + 1)
    C[0] = 1.5
    for n in range(1, order + 1):
        prov = {p: roots[p].provisional(n) for p in range(4)}
        target_sigma = -0.25 if n == 1 else 0.0
        target_chi = 0.25 if n == 1 else 0.0
        bare.r[n] = (target_sigma - prov[1] + prov[0]) / 2
        bare.g[n] = (target_chi - prov[3] + prov[0] - 6 * bare.r[n]) / 3
        for p in range(4):
            roots[p].E[n] = prov[p] + 2 * p * bare.r[n] + p * (p - 1) / 2 * bare.g[n]
        C[n] = roots[2].E[n] - roots[0].E[n]
        if n <= 2:
            for st in aux.values():
                st.E[n] = st.provisional(n)      # r_n, g_n parts cancel in every window difference
        if n == 2:
            for p, st in roots.items():
                lp = st.field ^ (st.P % 2)                       # local parity of each bath row
                z = lp[:, None] + 2 * np.arange(nz)[None, :]
                W2 = np.zeros_like(st.h0)
                for b in range(st.nb):
                    lev = int(st.N[b])
                    if lev == 0:
                        continue
                    for j in range(nz):
                        zz = int(z[b, j])
                        if zz > zmax:
                            continue                              # unreachable at order 4 from p <= 3
                        W2[b, j] = aux[(zz, cutoff)].E[2] - aux[(zz, cutoff - lev)].E[2]
                st.W2 = W2
        if n < order:
            bare.build(n)
            for st in list(roots.values()) + (list(aux.values()) if n < 2 else []):
                st.advance(n)
    return C


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoffs", type=int, nargs="+", default=[0, 2, 4, 6])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    Lmax = max(args.cutoffs)
    N, P, W = build_taylor_vertices(Lmax, degree=2, dtype=np.float64)
    rows = []
    for L in args.cutoffs:
        raw = ref.solve_coefficients(N, P, W, L, order=4, nz=10, mode="raw", dtype=np.float64)
        cons = ref.solve_coefficients(N, P, W, L, order=4, nz=10, mode="consistent", dtype=np.float64)
        zm = solve_zm(N, P, W, L)
        row = dict(L=L, C4raw=float(raw["C"][4]), C4cons=float(cons["C"][4]), C4zm=float(zm[4]))
        rows.append(row)
        print(json.dumps(row), flush=True)
    if args.out:
        json.dump(rows, open(args.out, "w"), indent=1)


if __name__ == "__main__":
    main()
