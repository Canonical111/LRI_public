#!/usr/bin/env python3
"""Symbolic Rayleigh-Schroedinger unrolling (non-symmetric, intermediate normalization) for H = H0 + sum_k eps^k W_k:

    phi_n = sum_{k=1}^n W_k psi_{n-k} - sum_{j=1}^{n-1} E_j psi_{n-j},   E_n = <p|phi_n>,   psi_n = R phi_n,

R = Q/(E^0_p - H0).  Atoms of W_k (shift trick: W1 -> W1 + p/4, so E_1 = g1 V_pp and E_{n>=2} unchanged):
    W_1 = g1 V_0 - (1/4) P,           P := (P - p) (diagonal)
    W_k = sum_{j=0}^{k-1} ( r_{k-j} M_j + g_{k-j} V_j ) + D_k     (r_1 = 0, g_1 = 1/3; D_k a window operator)
Each E_n term is (coefficient, word); coefficient = Fraction x monomial in symbols ('r2','g2',...,'E1','E2',...),
word = tuple of atoms (vertex 0 acts first) with R powers between consecutive atoms.  P atoms are merged into the
adjacent slice as (pow, q); see reduce_word()."""
from collections import defaultdict
from fractions import Fraction as Fr

G1 = Fr(1, 3)


def atoms_W(k, windows=False):
    """list of (coef, symbols tuple, atom)."""
    out = []
    if k == 1:
        out.append((G1, (), ("V", 0)))
        out.append((Fr(-1, 4), (), ("P",)))
        return out
    for j in range(0, k):
        o = k - j
        if o >= 2:
            out.append((Fr(1), (f"r{o}",), ("M", j)))
            out.append((Fr(1), (f"g{o}",), ("V", j)))
        elif o == 1:
            out.append((G1, (), ("V", j)))          # g_1 V_j  (r_1 = 0)
    if windows:
        out.append((Fr(1), (), ("D", k)))
    return out


def unroll(nmax, windows=False, return_psi=False):
    """Returns E[n] = list of (Fr, symbols tuple (sorted), ops tuple, pows tuple) for n = 1..nmax.
    ops[i] acts i-th; pows[i] (i < len(ops)-1) = R power between ops[i] and ops[i+1]."""
    psi = {0: [(Fr(1), (), (), ())]}
    E = {}
    for n in range(1, nmax + 1):
        phi = []
        for k in range(1, n + 1):
            for (c, sy, ops, pw) in psi[n - k]:
                for (ca, sa, atom) in atoms_W(k, windows):
                    phi.append((c * ca, tuple(sorted(sy + sa)), ops + (atom,), pw))
        Ecur = [t for t in phi]               # closing: <p| applied to phi_n
        E[n] = _merge(Ecur)
        newpsi = list(phi)
        for j in range(1, n):
            for (c, sy, ops, pw) in psi[n - j]:
                newpsi.append((-c, tuple(sorted(sy + (f"E{j}",))), ops, pw))
        # psi_n = R phi_n: every term gets one more R on the left.  For W-terms the last op has no R yet (pw shorter
        # than ops by one); for E-terms (pw length == ops length) increment the last R power.
        psi_n = []
        for (c, sy, ops, pw) in newpsi:
            if len(pw) == len(ops) - 1:
                psi_n.append((c, sy, ops, pw + (1,)))
            else:
                psi_n.append((c, sy, ops, pw[:-1] + (pw[-1] + 1,)))
        psi[n] = _merge(psi_n)
    if return_psi:
        return E, psi
    return E


def _merge(terms):
    acc = defaultdict(Fr)
    for (c, sy, ops, pw) in terms:
        acc[(sy, ops, pw)] += c
    return [(c, sy, ops, pw) for (sy, ops, pw), c in acc.items() if c != 0]


def reduce_word(ops, pw):
    """Merge P atoms into slices.  Returns None if the word vanishes (P acting on |p> or <p|P), else
    (vertices, slice_ops, dwin) with vertices = tuple of atoms (V/M/D), slice_ops = tuple of (pow, q) between
    consecutive vertices.  E-words have len(pw) == len(ops) - 1 (closing op last)."""
    if not ops:
        return None
    if ops[0][0] == "P" or ops[-1][0] == "P":
        return None
    verts, sops = [], []
    cur_pow, cur_q = 0, 0
    for i, a in enumerate(ops):
        if a[0] == "P":
            cur_q += 1
        else:
            if verts:
                sops.append((cur_pow, cur_q))
            verts.append(a)
            cur_pow, cur_q = 0, 0
        if i < len(ops) - 1:
            cur_pow += pw[i]
    return tuple(verts), tuple(sops)


if __name__ == "__main__":
    import sys
    nmax = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    E = unroll(nmax)
    for n in range(1, nmax + 1):
        words = {}
        for (c, sy, ops, pw) in E[n]:
            r = reduce_word(ops, pw)
            if r is None:
                continue
            words.setdefault(r[0], []).append((c, sy, r[1]))
        nv = {}
        for v in words:
            nv[len(v)] = nv.get(len(v), 0) + 1
        print(f"E_{n}: {len(E[n])} raw terms, {sum(len(x) for x in words.values())} nonzero words, "
              f"{len(words)} vertex sequences, by #vertices {dict(sorted(nv.items()))}")
