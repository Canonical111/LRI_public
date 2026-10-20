#!/usr/bin/env python3
"""Independent count of the d = 1 frozen-cutoff Fock basis (HT_Pert/code/lri_hpc_Hamitonian), pure Python.

States: the zero mode costs one quarter unit of free energy, a positive mode s costs 4s + 1 quarter units; keep the
states with total quarter-energy <= 4 Lambda (E^0 = N + P/4 <= Lambda), at most P particles in all and at most Q in
positive modes (the particle caps of the order computed: thermal C0..C7 P = 15, Q = 12; phi6 degree 5 P = 14, Q = 8;
phi6 degree 3 P = 10, Q = 4). Used by public/replay_hpcham.py to reproduce the basis_dimension of every record without
importing the solver.
usage: python3 public/count_states.py LAMBDA P Q   (e.g. 118 15 12 -> 3528133673)"""
import sys


def table(Lmax, Q):
    """t[k][e]: number of multisets of k positive modes (s <= Lmax) with total quarter-energy exactly e <= 4 Lmax."""
    E = 4 * Lmax
    t = [[0] * (E + 1) for _ in range(Q + 1)]
    t[0][0] = 1
    for s in range(1, Lmax + 1):
        w = 4 * s + 1
        for k in range(1, Q + 1):          # unbounded multiplicity: k and e ascending
            a, b = t[k], t[k - 1]
            for e in range(w, E + 1):
                a[e] += b[e - w]
    return t


def count(t, L, P, Q):
    """Basis dimension at cutoff L (L <= the table's Lmax), caps P (all particles) and Q (positive modes)."""
    E = 4 * L
    return sum(t[k][e] * (min(P - k, E - e) + 1) for k in range(Q + 1) for e in range(E + 1)
               if t[k][e] and min(P - k, E - e) >= 0)


if __name__ == '__main__':
    L, P, Q = (int(x) for x in sys.argv[1:4])
    print(count(table(L, Q), L, P, Q))
