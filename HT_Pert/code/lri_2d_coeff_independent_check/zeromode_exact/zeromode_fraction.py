#!/usr/bin/env python3
"""
Second, independent exact implementation of the zeromode scheme (fractions.Fraction throughout), used to check
zeromode_modular.py at small L.

Differences from zeromode_modular.py (on purpose):
  * operators from ref_fraction_orig.py (copy of ../rs_exact/ref_fraction.py): literal expansion of :phi^k:
    over ORDERED mode tuples, ladder operators applied one at a time, FULL J = 0 space (both reflection
    parities; no orbit reduction);
  * one separate Space (basis + operators) per cutoff l (no prefix slicing, no masks for the level);
  * sparse dict vectors, exact Fractions, no modular arithmetic or reconstruction;
  * the degenerate partners are handled by writing the B-projection of the order-n equation explicitly,
        (E^(1) - W_1^BB) psi_{n-1}^B = P_B [ W_1 psi_{n-1}^{Q'} + sum_{k=2}^{n} W_k psi_{n-k}
                                              - sum_{k=2}^{n-1} E^(k) psi_{n-k} ],
    with W_1^BB and the right-hand side assembled from the operator columns, and solved by Fraction Gaussian
    elimination (no precomputed inverse).
usage: python3 zeromode_fraction.py --L 4 [--tiers default] [--out file.json]
"""
from fractions import Fraction as Fr
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ref_fraction_orig as RF          # noqa: E402

ORD = RF.ORD


def default_tiers():
    t = {z: 6 for z in range(7)}
    t.update({z: 4 for z in range(7, 11)})
    t.update({z: 2 for z in range(11, 15)})
    return t


def gauss_solve(A, b):
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        piv = next(r for r in range(c, n) if M[r][c] != 0)
        M[c], M[piv] = M[piv], M[c]
        for r in range(n):
            if r != c and M[r][c] != 0:
                f = M[r][c] / M[c][c]
                M[r] = [x - f * y for x, y in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] for i in range(n)]


class ZChan:
    def __init__(self, sp, ops, z, l, kmax, cap, Etab):
        self.sp, self.ops, self.z, self.l, self.kmax, self.cap = sp, ops, z, l, kmax, cap
        self.Etab = Etab                       # Etab[(z', l')] = list of E coefficients (shared, growing)
        self.ref = sp.ref_index(z)
        self.allowed = [sp.P[i] <= cap for i in range(len(sp.states))]
        self.zero = [dict(s).get(0, 0) for s in sp.states]      # mode index 0 is (0,0)
        assert sp.modes[0] == (0, 0)
        self.H0 = [sp.level[i] + Fr(sp.P[i], 2) for i in range(len(sp.states))]
        E0 = Fr(z, 2)
        self.B = [i for i in range(len(sp.states)) if self.allowed[i] and i != self.ref and self.H0[i] == E0]
        self.Bset = set(self.B)
        self.psi = [{self.ref: Fr(1)}]
        self.E = [E0]

    def D(self, k, i):
        """eps^k coefficient of D_l(z_i, N_i) on basis state i."""
        N = self.sp.level[i]
        if N == 0 or k < 2:
            return 0
        zi = self.zero[i]
        a = self.Etab.get((zi, self.l))
        b = self.Etab.get((zi, self.l - N))
        va = a[k] if a is not None and len(a) > k else 0
        vb = b[k] if b is not None and len(b) > k else 0
        return va - vb

    def matvec(self, name, j, vec):
        out = {}
        cols = self.ops[name]
        al = self.allowed
        for c, v in vec.items():
            for (rr, pol) in cols[c]:
                a = pol[j]
                if a and al[rr]:
                    out[rr] = out.get(rr, 0) + v * a
        return out

    def Wk_apply(self, k, vec, r, g):
        """W_k vec = [-P/4 delta_k1 + sum_{j<k} (r_{k-j} M_j + g_{k-j} V_j) + D_k] vec."""
        out = {}

        def add(d, s=1):
            for a, v in d.items():
                out[a] = out.get(a, 0) + s * v

        for j in range(k):
            if r[k - j]:
                add(self.matvec("M", j, vec), r[k - j])
            if g[k - j]:
                add(self.matvec("V", j, vec), g[k - j])
        for i, v in vec.items():
            if k == 1:
                out[i] = out.get(i, 0) - Fr(self.sp.P[i], 4) * v
            d = self.D(k, i)
            if d:
                out[i] = out.get(i, 0) + d * v
        return out

    def order(self, n, r, g, rn_gn=None):
        """Order-n step.  With rn_gn = None: returns X = E^(n) without the r_n, g_n terms (tuning input).
        Otherwise completes the order (second call)."""
        if rn_gn is not None:
            return self._finish(rn_gn)
        # 1) degenerate partners: fix psi_{n-1}^B from the B-projection of the order-n equation
        if n >= 2 and self.B:
            if not hasattr(self, "W1BB"):
                col = {}
                W1BB = []
                for jb, b in enumerate(self.B):
                    w = self.Wk_apply(1, {b: Fr(1)}, r, g)
                    assert w.get(self.ref, 0) == 0
                    W1BB.append([w.get(a, 0) for a in self.B])     # column jb
                self.A = [[(self.E[1] if ia == jb else 0) - W1BB[jb][ia] for jb in range(len(self.B))]
                          for ia in range(len(self.B))]
            rhs = {}

            def add(d, s=1):
                for a, v in d.items():
                    if a in self.Bset:
                        rhs[a] = rhs.get(a, 0) + s * v

            add(self.Wk_apply(1, self.psi[n - 1], r, g))         # psi_{n-1} has no B part yet
            for k in range(2, n + 1):
                if k == n:
                    # W_n psi_0 with the full r_n, g_n: no B component (checked); skip
                    w = self.Wk_apply(n, self.psi[0], r, g)
                    assert all(w.get(a, 0) == 0 for a in self.B)
                    continue
                add(self.Wk_apply(k, self.psi[n - k], r, g))
                add({a: v for a, v in self.psi[n - k].items()}, -self.E[k])
            y = gauss_solve(self.A, [rhs.get(a, 0) for a in self.B])
            for a, v in zip(self.B, y):
                assert self.psi[n - 1].get(a, 0) == 0
                if v:
                    self.psi[n - 1][a] = v
        # 2) full order-n right-hand side (r_n = g_n = 0 first)
        rr = list(r); gg = list(g)
        rr[n] = 0; gg[n] = 0
        tot = {}

        def add2(d, s=1):
            for a, v in d.items():
                tot[a] = tot.get(a, 0) + s * v

        for k in range(1, n + 1):
            add2(self.Wk_apply(k, self.psi[n - k], rr, gg))
        for k in range(1, n):
            add2(self.psi[n - k], -self.E[k])
        for a in self.B:
            assert tot.get(a, 0) == 0, "B-projection not satisfied"
        self._tot = tot
        return tot.get(self.ref, Fr(0))

    def _finish(self, rn_gn):
        rn, gn = rn_gn
        tot = self._tot
        for name, c in (("M", rn), ("V", gn)):
            if c:
                for a, v in self.matvec(name, 0, {self.ref: Fr(1)}).items():
                    tot[a] = tot.get(a, 0) + c * v
        En = tot.get(self.ref, Fr(0))
        self.E.append(En)
        psi = {}
        for a, v in tot.items():
            if a == self.ref or v == 0:
                continue
            assert a not in self.Bset
            psi[a] = v / (self.E[0] - self.H0[a])
        self.psi.append(psi)
        self.Etab[(self.z, self.l)] = self.E
        return En


def run(L, tiers, capextra=0, verbose=True):
    t0 = time.time()
    Pm = {0: 18 + capextra, 1: 19 + capextra}
    for z, k in tiers.items():
        Pm[z % 2] = max(Pm[z % 2], z + 4 * (k // 2) + capextra)
    spaces = {}
    for l in range(0, L + 1, 2):
        for par in (0, 1):
            sp = RF.Space(l, par, Pm[par])
            ctup = RF.ordered_creation_tuples(sp, 4)
            ops = {"M": RF.build_vertex(sp, 2, Fr(1), ctup), "V": RF.build_vertex(sp, 4, Fr(1, 12), ctup)}
            spaces[(l, par)] = (sp, ops)
        if verbose:
            print(f"# spaces l={l}: {[len(spaces[(l, p)][0].states) for p in (0, 1)]} states "
                  f"(t={time.time()-t0:.1f}s)", flush=True)
    Etab = {}
    ch = {}
    for z, km in tiers.items():
        for l in range(0, L + 1, 2):
            if l == L and z <= 3:
                continue
            sp, ops = spaces[(l, z % 2)]
            ch[(z, l)] = ZChan(sp, ops, z, l, km, z + 4 * (km // 2) + capextra, Etab)
    for p in range(4):
        sp, ops = spaces[(L, p % 2)]
        ch[(p, L)] = ZChan(sp, ops, p, L, ORD, p + 16 + capextra, Etab)
    for c in ch.values():
        Etab[(c.z, c.l)] = c.E
    r = [Fr(0)] * (ORD + 1)
    g = [Fr(0)] * (ORD + 1)
    xser = [Fr(1, 2), Fr(-1, 4)] + [Fr(0)] * (ORD - 1)
    C = [Fr(1)]
    for n in range(1, ORD + 1):
        X = {}
        for key, c in ch.items():
            if c.kmax >= n:
                X[key] = c.order(n, r, g)
        Xp = {p: X[(p, L)] for p in range(4)}
        rn = (xser[n] - Xp[1] + Xp[0]) / 2
        gn = (-xser[n] - Xp[3] + Xp[0] - 6 * rn) / 3
        r[n], g[n] = rn, gn
        for key, c in ch.items():
            if c.kmax >= n:
                c.order(n, r, g, (rn, gn))
        E = {p: ch[(p, L)].E[n] for p in range(4)}
        assert E[1] - E[0] == xser[n] and E[3] - E[0] == -xser[n]
        C.append(E[2] - E[0])
        if verbose:
            print(f"# order {n}: C_{n} = {float(C[n]):.15g}  t={time.time()-t0:.1f}s", flush=True)
    return {"L": L, "C": [str(x) for x in C], "r": [str(x) for x in r], "g": [str(x) for x in g],
            "E": [[str(x) for x in ch[(p, L)].E] for p in range(4)],
            "Ez": {f"{z},{l}": [str(x) for x in c.E] for (z, l), c in ch.items()},
            "seconds": time.time() - t0}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--capextra", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = run(a.L, default_tiers(), a.capextra)
    js = json.dumps(res, indent=1)
    if a.out:
        with open(a.out, "w") as f:
            f.write(js)
    else:
        print(js)
