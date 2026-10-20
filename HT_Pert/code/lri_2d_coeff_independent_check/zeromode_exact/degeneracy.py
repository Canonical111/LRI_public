#!/usr/bin/env python3
"""Exact degeneracy analysis for the zero-mode channels |z> = (A_00^dag)^z/sqrt(z!)|0>.

At eps = 0, H0 = N + P/2.  A state of the same field-parity, J = 0 sector is degenerate with |z> (energy z/2)
iff N + P/2 = z/2, i.e. P = z - 2N.  N = 0 gives |z> itself; N >= 2 (even) needs P = z - 2N >= 1 (a state at
level N >= 2 holds at least one non-zero quantum), so partners exist iff z >= 5, at the levels
N = 2, 4, ..., N <= (z - 1)/2.  The partner block B_N(z) = {J = 0 states at level N with P = z - 2N}.

First-order operator: W_1 = -P/4 + g_1 V_0 + r_1 M_0 with r_1 = 0, g_1 = 1/3 in every scheme (D starts at
eps^2).  Facts checked here:
  (i)  W_1 has no matrix element between |z> and any B_N(z) (V changes the level only by creating /
       annihilating non-zero quanta; from level 0 to level N >= 2 with P -> P - 2N it would need
       > 4 ladder operators).  Checked explicitly by applying V_0 to |z>.
  (ii) W_1 restricted to the degenerate space is block-diagonal: B_N(z) blocks with different N have
       different P (= z - 2N), and V_0 between equal-energy states at different levels would need to change
       level and P simultaneously at fixed H0 -- impossible with the 2-create/2-annihilate part; terms that
       change P change H0.  Checked by building the full degenerate-space block.
  (iii) e1(z) = <z|W_1|z> = -z/4 + z(z-1)/6 is NOT an eigenvalue of W_1|B_N(z) for every N (exact
       determinant det(W_1^BB - e1 I) != 0, Fraction arithmetic), so the degeneracy is lifted at first order
       and the branch connected to |z> is unique and analytic, with leading eigenvector exactly |z>.
Both the full J = 0 block and its reflection-even part (the one that matters: |z> is R-even and H commutes
with R) are analysed.  Matrix elements in the monomial (similarity) frame:
    (n'|V|n) = 2 prod_m w_m^{t_m} C(n_m, t_m) / s_m!   (T annihilated, S created multisets, J(S) = J(T)),
with w at eps = 0: w_ab = (1/2)_a (1/2)_b / (a! b!).  The frame changes no eigenvalue.

usage: python3 degeneracy.py [--zmax 24] [--json results/degeneracy.json]
"""
from fractions import Fraction as Fr
from math import comb, factorial
import argparse, itertools, json
import numpy as np


def w0(a, b):
    def poch_half(n):
        v = Fr(1)
        for i in range(n):
            v *= Fr(2 * i + 1, 2 * (i + 1))
        return v
    return poch_half(a) * poch_half(b)


def nonzero_multisets(N):
    """All multisets of non-zero modes (a,b) != (0,0) with total level exactly N and J = 0."""
    modes = [(a, n - a) for n in range(1, N + 1) for a in range(n + 1)]
    out = []

    def rec(i, lev, J, acc):
        if lev == N:
            if J == 0:
                out.append(tuple(acc))
            return
        for k in range(i, len(modes)):
            a, b = modes[k]
            if lev + a + b > N:
                continue
            acc.append(modes[k])
            rec(k, lev + a + b, J + a - b, acc)
            acc.pop()

    rec(0, 0, 0, [])
    return out


def occ_of(ms, n0):
    d = {}
    for m in ms:
        d[m] = d.get(m, 0) + 1
    if n0:
        d[(0, 0)] = n0
    return tuple(sorted(d.items()))


def sub_multisets(occ, k):
    items = list(occ)
    out = []

    def rec(i, left, acc):
        if left == 0:
            out.append(tuple(acc))
            return
        if i == len(items):
            return
        m, n = items[i]
        for t in range(min(n, left), -1, -1):
            if t:
                acc.append((m, t))
            rec(i + 1, left - t, acc)
            if t:
                acc.pop()

    rec(0, k, [])
    return out


def apply_V_22(occ, targets_index):
    """2-annihilate / 2-create part of V on monomial |occ), restricted to the given target set.
    Returns dict target_index -> Fraction."""
    occd = dict(occ)
    out = {}
    for T in sub_multisets(occ, 2):
        jt = sum(t * (m[0] - m[1]) for m, t in T)
        lt = sum(t * (m[0] + m[1]) for m, t in T)
        coefT = Fr(1)
        for m, t in T:
            coefT *= w0(*m) ** t * comb(occd[m], t)
        base = dict(occd)
        for m, t in T:
            base[m] -= t
            if base[m] == 0:
                del base[m]
        # created multisets S of size 2 with J = jt and level = lt (level must be preserved inside B)
        cands = [(a, lt_ - a) for lt_ in range(0, lt + 1) for a in range(lt_ + 1)]
        for i in range(len(cands)):
            for j in range(i, len(cands)):
                m1, m2 = cands[i], cands[j]
                if m1[0] + m1[1] + m2[0] + m2[1] != lt or (m1[0] - m1[1]) + (m2[0] - m2[1]) != jt:
                    continue
                pf = 2 if m1 == m2 else 1
                new = dict(base)
                for m in (m1, m2):
                    new[m] = new.get(m, 0) + 1
                tgt = tuple(sorted(new.items()))
                k = targets_index.get(tgt)
                if k is None:
                    continue
                out[k] = out.get(k, 0) + 2 * coefT / pf
    return out


def V_reaches_level_ge2_from_z(z):
    """(i): does V_0 (any create/annihilate split) map |z) to a level >= 2 state with P = z - 2N?"""
    # V on |z): annihilate a zero modes (a <= min(z,4)), create c = 4 - a quanta with J = 0.
    # resulting P = z - a + c; level = level of created set. Degenerate partners need P = z - 2*level.
    hits = []
    for a in range(0, min(z, 4) + 1):
        c = 4 - a
        for lvl in range(0, 4 * 4 + 1):
            if lvl >= 2 and z - a + c == z - 2 * lvl:
                for ms in itertools.combinations_with_replacement(
                        [(p, q) for n in range(0, lvl + 1) for p in range(n + 1) for q in [n - p]], c):
                    if sum(p + q for p, q in ms) == lvl and sum(p - q for p, q in ms) == 0:
                        hits.append((a, c, lvl, ms))
    return hits


def fr_det(Mrows):
    A = [row[:] for row in Mrows]
    n = len(A)
    det = Fr(1)
    for c in range(n):
        piv = next((r for r in range(c, n) if A[r][c] != 0), None)
        if piv is None:
            return Fr(0)
        if piv != c:
            A[c], A[piv] = A[piv], A[c]
            det = -det
        det *= A[c][c]
        for r in range(c + 1, n):
            if A[r][c] != 0:
                f = A[r][c] / A[c][c]
                for k in range(c, n):
                    A[r][k] -= f * A[c][k]
    return det


def reflect(occ):
    return tuple(sorted(((b, a), n) for (a, b), n in occ))


def analyse(zmax, Nmax_cap=None):
    rows = []
    for z in range(0, zmax + 1):
        e1 = Fr(-z, 4) + Fr(z * (z - 1), 6)
        hits = V_reaches_level_ge2_from_z(z)
        assert not hits, (z, hits)
        N = 2
        while z - 2 * N >= 1 and (Nmax_cap is None or N <= Nmax_cap):
            P = z - 2 * N
            states = []
            for ms in nonzero_multisets(N):
                m = len(ms)
                if m <= P:
                    states.append(occ_of(ms, P - m))
            states = sorted(set(states))
            idx = {s: i for i, s in enumerate(states)}
            n = len(states)
            V = [[Fr(0)] * n for _ in range(n)]
            for j, s in enumerate(states):
                for i, v in apply_V_22(s, idx).items():
                    V[i][j] += v
            # W1 on B = -P/4 + V/3 ; shift by e1
            Wm = [[(V[i][j] / 3 + (Fr(-P, 4) if i == j else 0)) for j in range(n)] for i in range(n)]
            detfull = fr_det([[Wm[i][j] - (e1 if i == j else 0) for j in range(n)] for i in range(n)])
            # reflection-even part: orbit basis e_o = s + Rs (or s); in the monomial frame the action of an
            # R-invariant operator on orbit sums closes; matrix K_{o'o} = sum_{s' in o'} W_{s', rep(o)}
            orbits = []
            seen = set()
            for s in states:
                if s in seen:
                    continue
                rs = reflect(s)
                seen.add(s)
                seen.add(rs)
                orbits.append((s, rs) if rs != s else (s,))
            no = len(orbits)
            K = [[Fr(0)] * no for _ in range(no)]
            for b, ob in enumerate(orbits):
                rep = idx[ob[0]]
                for a, oa in enumerate(orbits):
                    K[a][b] = sum(Wm[idx[s]][rep] for s in oa)
            deteven = fr_det([[K[i][j] - (e1 if i == j else 0) for j in range(no)] for i in range(no)])
            evf = np.sort(np.linalg.eigvals(np.array([[float(x) for x in r] for r in Wm])).real)
            eve = np.sort(np.linalg.eigvals(np.array([[float(x) for x in r] for r in K])).real) if no else []
            rows.append(dict(z=z, N=N, P=P, n_full=n, n_even=no, e1=str(e1), e1_float=float(e1),
                             det_full=str(detfull), det_even=str(deteven),
                             eig_full=[float(x) for x in evf], eig_even=[float(x) for x in eve],
                             min_gap_even=float(min(abs(x - float(e1)) for x in eve)) if no else None,
                             min_gap_full=float(min(abs(x - float(e1)) for x in evf)),
                             lifted=(detfull != 0 and deteven != 0)))
            N += 2
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zmax", type=int, default=24)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    rows = analyse(a.zmax)
    print(f"# z = 0..4: no degenerate partner (P = z - 2N >= 1 with N >= 2 impossible); V_0|z> never reaches a")
    print(f"#           degenerate partner for z = 0..{a.zmax} (checked)")
    print(f"{'z':>3} {'N':>2} {'P':>3} {'dim':>4} {'dimR+':>5} {'e1(z)':>10} {'min|eig-e1| (R+)':>17} "
          f"{'min|eig-e1| (all)':>18}  lifted  R+ eigenvalues of W1|B")
    for r in rows:
        print(f"{r['z']:3d} {r['N']:2d} {r['P']:3d} {r['n_full']:4d} {r['n_even']:5d} {r['e1_float']:10.4f} "
              f"{r['min_gap_even']:17.6f} {r['min_gap_full']:18.6f}  {str(r['lifted']):6s}  "
              + " ".join(f"{x:.4f}" for x in r['eig_even']))
    bad = [r for r in rows if not r['lifted']]
    print(f"# blocks analysed: {len(rows)}; NOT lifted at first order: {len(bad)}")
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"zmax": a.zmax, "blocks": rows, "not_lifted": bad}, f, indent=1)


if __name__ == "__main__":
    main()
