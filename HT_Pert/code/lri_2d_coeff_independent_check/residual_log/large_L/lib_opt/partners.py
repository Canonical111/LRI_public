#!/usr/bin/env python3
"""Degenerate-partner correction of the third-order channel energies E_z^(3)(l) for z >= 5 (level-2 partners).

The branch through |z> mixes at O(eps) with its degenerate partners B (level 2, P = z - 4) although <z|W_k|B> = 0
(../../zeromode_exact Sec. 4-5):  psi_1^B = G_B P_B W_1 psi_1^{Q'},  G_B = (E^(1)_z - W_1^{BB})^-1,  and through
psi_2 = R'(... + W_1 psi_1^B) it feeds
    dE_z^(3)(l) = T(l)^T G_B T(l),     T_F(l) = <F| W_1 R' W_1 |z>_l = g1^2 <F| V R' V |z>_l     (normalized states).
T_F (F = partner state |z_F> (x) external chi quanta) is a sum over two-vertex processes: v1 creates m internal chi
lines plus the externals attached to it (they pass through the intermediate slice), v2 absorbs the internal lines and
emits the remaining externals.  Internal lines carry J = -(J of the passing externals); their density with hol level
u and antihol level u - j is D_m^(j)(u) = sum_k C(m,k)(-1)^(m-k) U_k(u) U_k(u - j).
G_B and the partner states are taken from the exact Fock-space operators (../../rs_exact/ref_fraction.py) at L = 2
(level-2 block, L independent for L >= 2).
"""
import itertools
import os
import sys
from fractions import Fraction as Fr
from math import comb, factorial

import numpy as np

import engine as eg

HERE = os.path.dirname(os.path.abspath(__file__))
G1 = Fr(1, 3)

# partner states (normalized): list of (zF, externals) with externals = tuple of modes (a, b) (distinct)
PARTNERS = {5: [(0, ((1, 1),))],
            6: [(1, ((1, 1),)), (0, ((1, 0), (0, 1)))],
            7: [(2, ((1, 1),)), (1, ((1, 0), (0, 1)))],
            8: [(3, ((1, 1),)), (2, ((1, 0), (0, 1)))]}


def Dmj(modes, m, j, N):
    """internal m-line density with J = j: hol level u (index), antihol u - j; returns array over u (0..N)."""
    out = np.zeros(N + 1)
    for k in range(m + 1):
        c = comb(m, k) * (-1) ** (m - k)
        U = modes.U(k, 0, 0)[: N + 1 + abs(j)]
        uu = np.arange(N + 1)
        ub = uu - j
        ok = (ub >= 0) & (ub < len(U))
        t = np.zeros(N + 1)
        t[ok] = U[uu[ok]] * U[ub[ok]]
        out += c * t
    return out


def T_amp(modes, z, zF, ext, N):
    """T_F(l)/g1^2 = <F|V R' V|z>_l for l = 2M (M = 0..N); F = |zF> (x) ext (distinct modes)."""
    out = np.zeros(N + 1)
    e = len(ext)
    w = [modes.v[a] * modes.v[b] for (a, b) in ext]       # w_ab at eps = 0
    for att in itertools.product((1, 2), repeat=e):       # each external attaches to v1 (passes) or v2
        e1 = sum(1 for x in att if x == 1)
        e2 = e - e1
        lev_pass = sum(ext[i][0] + ext[i][1] for i in range(e) if att[i] == 1)
        J_pass = sum(ext[i][0] - ext[i][1] for i in range(e) if att[i] == 1)
        wext = float(np.prod([np.sqrt(x) for x in w]))
        for m in range(0, 5):
            if m + e1 > 4 or m + e2 > 4:
                continue
            vc = float(eg.vcoef("V", m + e1) * eg.vcoef("V", m + e2))
            combf = factorial(m + e1) * factorial(m + e2) / factorial(m)
            for rs, amp in eg.zero_mode_paths(z, [4 - m - e1, 4 - m - e2], zF):
                zk = rs[0]
                a = vc * combf * wext * float(amp)
                if m == 0:
                    if J_pass != 0:
                        continue
                    if zk == z and e1 == 0:
                        continue                              # Q' excludes |z>
                    den = (zk - z) / 2.0 + e1 / 2.0 + lev_pass
                    t = np.zeros(N + 1)
                    lv = lev_pass
                    t[np.arange(N + 1) * 2 >= lv] = -1.0 / den
                    out += a * t
                    continue
                j = -J_pass
                D = Dmj(modes, m, j, N)
                u = np.arange(N + 1)
                lev_int = 2 * u - j
                den = (zk - z) / 2.0 + (m + e1) / 2.0 + lev_int + lev_pass
                tl = np.zeros(N + 1)
                ok = (lev_int >= m) & (u - j >= 0)
                tl[ok] = -D[ok] / den[ok]
                # cumulative in the cutoff l = 2M: slice level lev_int + lev_pass <= 2M
                tot = lev_int + lev_pass
                acc = np.zeros(N + 2)
                for uu in np.nonzero(tl)[0]:
                    Mmin = int(np.ceil(tot[uu] / 2.0))
                    if Mmin <= N:
                        acc[Mmin] += tl[uu]
                out += a * np.cumsum(acc[: N + 1])
    return out


def fock_blocks(zs=(5, 6, 7, 8)):
    """E^(1)_z - W_1^{BB} in the normalized partner basis of PARTNERS[z], from the exact operators at L = 2."""
    sys.path.insert(0, os.environ.get("RS_EXACT_DIR", os.path.join(HERE, "..", "..", "rs_exact")))
    import ref_fraction as rf
    rf.ORD = 1
    out = {}
    for z in zs:
        sp = rf.Space(2, z % 2, z + 2)
        ctup = rf.ordered_creation_tuples(sp, 4)
        V = rf.build_vertex(sp, 4, Fr(1, 12), ctup)
        midx = {m: i for i, m in enumerate(sp.modes)}

        def state(zF, ext):
            occ = {}
            if zF:
                occ[0] = zF
            for mo in ext:
                occ[midx[mo]] = occ.get(midx[mo], 0) + 1
            return sp.index[tuple(sorted(occ.items()))]

        def snorm(i):        # s_k mu_k: frame <-> normalized conversion factor
            st = dict(sp.states[i])
            f = Fr(1)
            for mi, nn in st.items():
                f *= factorial(nn)
            wprod = 1.0
            for mi, nn in st.items():
                wprod *= float(sp.w[mi][0]) ** nn
            return float(f) ** 0.5 * wprod ** 0.5

        Bi = [state(zF, ext) for (zF, ext) in PARTNERS[z]]
        nb = len(Bi)
        Vn = np.zeros((nb, nb))
        for a_, c in enumerate(Bi):
            for (r, pol) in V[c]:
                if r in Bi:
                    b_ = Bi.index(r)
                    Vn[b_, a_] += float(pol[0]) * snorm(r) / snorm(c)
        P_B = sp.P[Bi[0]]
        W1 = float(G1) * Vn + np.eye(nb) * (-(P_B - z) / 4.0)
        E1 = float(G1) * z * (z - 1) / 2.0
        out[z] = np.eye(nb) * E1 - W1
    return out


def dE3(modes, N, zs=(5, 6, 7)):
    """dict z -> dE_z^(3)(l) (l = 2M, M = 0..N)."""
    A = fock_blocks(zs)
    g1sq = float(G1 ** 2)
    out, Ts = {}, {}
    for z in zs:
        T = np.vstack([g1sq * T_amp(modes, z, zF, ext, N) for (zF, ext) in PARTNERS[z]])
        G = np.linalg.inv(A[z])
        d = np.einsum("il,ij,jl->l", T, G, T)
        d[0] = 0.0                     # no level-2 partner at cutoff 0
        out[z] = d
        Ts[z] = T
    return out, Ts


if __name__ == "__main__":
    print({z: a.tolist() for z, a in fock_blocks().items()})
    modes = eg.Modes(6, 1)
    d, T = dE3(modes, 6)
    for z in d:
        print(z, "dE3(l=2)-dE3(0) = %+.10f   (l=4)-(0) = %+.10f" % (d[z][1] - d[z][0], d[z][2] - d[z][0]))
