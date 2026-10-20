#!/usr/bin/env python3
"""Independent brute-force check of the eps^5 window schemes on the package's own operators (read-only import of
lri_3d_hpc/reference/perturbative.py and its vendor vertex builder), small L, float64 (long double on x86).

Explicit window operators (WINDOW_SPEC of the 2D project, transcribed to the 3D model, x0 = 3/4):
  D^zm,(k) |z, chi> = sum_z' [h^(k)(Lref) - h^(k)(l - N_chi)]_{z'z} |z', chi>   (N_chi >= 2; none on level 0)
  D^M,(k)          = (1/4) sum_j { Delta c_1^(k-j)(N_hat), M'_j },   M' = terms of M with >= 1 bath leg
with Bloch h = X Lambda X^-1 of the level-0 sector (recursion WINDOW_SPEC 2.3 with (z - z')/2 -> x0 (z - z')),
c_1 = E_1 - E_0, auxiliary channels (z = 0..ZMAX, every even l <= L) advanced to order 3 in lock step with the
primaries (p = 0..3 at L, to order 5).  Outer channel (l = L): Lref = L, Delta c_1(N) = c_1(L) - c_1(L - N).
Auxiliary channel at l < L:  rule W (self-consistent): h(l) - h(l - N), c_1(l) - c_1(l - N);
                             rule Wc (outer-referenced): h(L) - h(l - N), c_1(L) - c_1(l - N) (also on level 0).
Variants: W2 (DZ2+DM2), W3m (+DM3), Wb (+Bloch DZ3), Wc (Wb with rule Wc), Zb (DZ2+DZ3), raw.
Wcs: Wc + (delta3/2) X_0 at eps^3 with delta3 given on the command line (X = M' weighted by +-level of its chi legs).
Degenerate partners (z >= 9) are projected out of every resolvent (zero denominators dropped).
usage: python3 brute3d_W5.py --L 6 --variants raw,W2,W3m,Wb,Wc,Zb [--delta3 x] [--out f.json]"""
import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..", "..", "lri_3d_hpc")
sys.path.insert(0, os.path.join(PKG, "reference"))
sys.path.insert(0, os.path.join(PKG, "vendor"))
import perturbative as ref  # noqa: E402
from taylor_vertices import build_taylor_vertices  # noqa: E402

X0 = 0.75
G1 = 1.0 / 3.0
ZMAX = 11
NZ = 16
ORD = 5
AUXORD = 3
DT = np.longdouble
# package basis guards (defaults 2e6 states / 2 GiB); raised via the environment for L >= 16
GUARD = dict(max_states=int(os.environ.get("BRUTE_MAX_STATES", 2_000_000)),
             max_bytes=int(os.environ.get("BRUTE_MAX_BYTES", 2 * 1024 ** 3)))


class Chan:
    def __init__(self, bare, Nall, Pall, l, z):
        self.l, self.z = l, z
        nb = int(np.sum(Nall <= l))
        self.nb = nb
        self.N, self.P = Nall[:nb], Pall[:nb]
        self.field = z % 2
        lp = self.field ^ (self.P % 2)
        self.lp = lp
        self.zcol = lp[:, None] + 2 * np.arange(NZ)[None, :]
        totalp = self.P[:, None] + self.zcol
        h0 = self.N[:, None] + DT(X0) * totalp
        self.idx = (0, z // 2)
        den = DT(X0 * z) - h0
        den[self.idx] = 1
        bad = np.abs(den) < 1e-9
        den[bad] = np.inf                          # partners projected out
        self.den = den
        self.E = [DT(X0 * z)] + [DT(0)] * ORD
        v = np.zeros((nb, NZ), dtype=DT)
        v[self.idx] = 1
        self.psi = [v]
        self.bare = bare


def apply_terms(terms, q, X, field, P, nz):
    out = np.zeros_like(X)
    rows = [np.flatnonzero(P % 2 == p) for p in (0, 1)]
    for bath_degree, local_degree, W in terms:
        nb = X.shape[0]
        mat = W if nb == W.shape[0] else W[:nb, :nb]
        image = mat @ X
        for bpar, sel in enumerate(rows):
            f = field ^ bpar
            pin = f ^ (bath_degree % 2)
            block = q[local_degree][f * nz:(f + 1) * nz, pin * nz:(pin + 1) * nz]
            out[sel] += image[sel] @ block.T
    return out


class Solver:
    def __init__(self, L, variant, delta3=None):
        self.L, self.var = L, variant
        N, P, W = build_taylor_vertices(L, degree=ORD - 2, dtype=DT, **GUARD)
        self.Nall, self.Pall, self.W = np.asarray(N), np.asarray(P), W
        self.bare = ref.BareSeries(N, P, [[a.astype(DT) for a in s] for s in W], NZ, ORD, DT)
        self.q = self.bare.q
        # M'_j terms: degree-2 vertex, bath degree 1 (2 Z chi) and 2 (chi chi), Taylor order j, unit coefficient
        self.Mp = {j: [(jb, 2 - jb, (W[jb - 1][j] * (1 if jb == 2 else 2)).astype(DT).tocsr()) for jb in (1, 2)]
                   for j in range(ORD - 1)}
        self.delta3 = delta3
        if delta3 is not None:
            self.Xnu = self._build_X()
        self.cuts = list(range(0, L + 1, 2))
        self.prim = {p: Chan(self.bare, self.Nall, self.Pall, L, p) for p in range(4)}
        self.aux = {(z, l): Chan(self.bare, self.Nall, self.Pall, l, z)
                    for z in range(ZMAX + 1) for l in self.cuts} if variant != "raw" else {}
        for p in range(4):
            self.aux[(p, L)] = self.prim[p]
        self.h = {}          # h[n][l] = (ZMAX+1)^2 matrix
        self.c1 = {}         # c1[n] = dict l -> value
        self.comp = {"W2": {2: {"DZ", "DM"}}, "W3m": {2: {"DZ", "DM"}, 3: {"DM"}},
                     "Wb": {2: {"DZ", "DM"}, 3: {"DZ", "DM"}}, "Wc": {2: {"DZ", "DM"}, 3: {"DZ", "DM"}},
                     "Wcs": {2: {"DZ", "DM"}, 3: {"DZ", "DM"}},
                     "Zb": {2: {"DZ"}, 3: {"DZ"}}, "raw": {}}[variant]
        self.outer_ref = variant in ("Wc", "Wcs")

    def _build_X(self):
        """X = M' with every term weighted by s x (sum of the levels of its chi legs): vertices rebuilt with mode
        amplitudes u_k (1 + t N_k / 2); d/dt gives (sum of chi-leg levels)/2 x term.  Sign: hop (+), pair (-)."""
        import taylor_vertices as tv
        orig = tv.amplitude_taylor

        def amp_t(n, ell, degree=7, dtype=np.longdouble):
            u0 = orig(n, ell, 0, dtype)[0]
            out = np.zeros(degree + 1, dtype=dtype)
            out[0] = u0
            if degree >= 1:
                out[1] = u0 * (2 * n + ell) / 2
            return out
        tv.amplitude_taylor = amp_t
        try:
            N, P, Wt = build_taylor_vertices(self.L, degree=1, dtype=DT, **GUARD)
        finally:
            tv.amplitude_taylor = orig
        Nb, Pb = np.asarray(N), np.asarray(P)
        out = []
        for jb in (1, 2):
            A = (Wt[jb - 1][1] * 2).tocoo()        # (sum of chi-leg levels) x term
            dP = Pb[A.row] - Pb[A.col]
            if jb == 2:
                sgn = np.where(np.abs(dP) == 2, -1.0, 1.0)
                M = A.copy()
                M.data = A.data * sgn * (1 if jb == 2 else 2)
                out.append((jb, 0, M.tocsr().astype(DT), None))
            else:
                # Z chi: chi created (dP=+1) with local a (z-1) = hop (+), with local a^dag = pair (-);
                # chi annihilated (dP=-1) with a^dag = hop (+), with a = pair (-).  Split local Z = a + a^dag.
                cre = A.copy()
                cre.data = np.where(dP > 0, A.data, 0.0) * 2
                ann = A.copy()
                ann.data = np.where(dP < 0, A.data, 0.0) * 2
                out.append((1, 1, cre.tocsr().astype(DT), "cre"))
                out.append((1, 1, ann.tocsr().astype(DT), "ann"))
        return out

    # ---------------------------------------------------------------- window application
    def lref(self, ch):
        return self.L if (ch.l == self.L or self.outer_ref) else ch.l

    def windows(self, n, ch, X):
        out = np.zeros_like(X)
        comps = self.comp.get(n, set())
        if not comps and not (n == 3 and self.delta3 is not None):
            return out
        Lr = self.lref(ch)
        Nlev = ch.N
        if "DZ" in comps and n in self.h:
            hL = self.h[n][Lr]
            for b in range(ch.nb):
                if Nlev[b] < 2:
                    continue
                hd = hL - self.h[n][ch.l - Nlev[b]]
                for j in range(NZ):
                    x = X[b, j]
                    if x == 0:
                        continue
                    z = ch.zcol[b, j]
                    if z > ZMAX:
                        continue
                    for zp in range(z % 2, ZMAX + 1, 2):
                        c = hd[zp, z]
                        if c != 0:
                            out[b, (zp - ch.lp[b]) // 2] += c * x
        if "DM" in comps:
            for j in range(0, n - 1):
                k = n - j
                if k not in self.c1:
                    continue
                c1 = self.c1[k]
                dc = np.array([c1[Lr] - c1[ch.l - lev] for lev in Nlev], dtype=DT)
                if ch.l == self.L or not self.outer_ref:
                    dc[Nlev == 0] = 0
                Y = apply_terms(self.Mp[j], self.q, X, ch.field, ch.P, NZ)
                Z = apply_terms(self.Mp[j], self.q, dc[:, None] * X, ch.field, ch.P, NZ)
                out += DT(0.25) * (dc[:, None] * Y + Z)
        if n == 3 and self.delta3 is not None:
            out += DT(self.delta3 / 2) * self._apply_X(ch, X)
        return out

    def _apply_X(self, ch, X):
        out = np.zeros_like(X)
        nz = NZ
        rows = [np.flatnonzero(ch.P % 2 == p) for p in (0, 1)]
        a = np.diag(np.sqrt(np.arange(1, 2 * nz + 4, dtype=DT)), 1)    # annihilator on the padded local space
        ix = np.r_[np.arange(0, 2 * nz, 2), np.arange(1, 2 * nz, 2)]
        aloc = a[np.ix_(ix, ix)]
        adag = a.T[np.ix_(ix, ix)]
        for (jb, ld, Wm, kind) in self.Xnu:
            mat = Wm[: ch.nb, : ch.nb]
            image = mat @ X
            for bpar, sel in enumerate(rows):
                f = ch.field ^ bpar
                pin = f ^ (jb % 2)
                if jb == 2:
                    block = self.q[0][f * nz:(f + 1) * nz, pin * nz:(pin + 1) * nz]
                    out[sel] += image[sel] @ block.T
                else:
                    hop = aloc if kind == "cre" else adag        # chi created + Z annihilated, or the reverse
                    pair = adag if kind == "cre" else aloc
                    bh = hop[f * nz:(f + 1) * nz, pin * nz:(pin + 1) * nz]
                    bp = pair[f * nz:(f + 1) * nz, pin * nz:(pin + 1) * nz]
                    out[sel] += image[sel] @ bh.T - image[sel] @ bp.T
        return out

    def apply(self, n, ch, X):
        out = self.bare.apply(n, X, ch.field, ch.N, ch.P)
        if n >= 2:
            out += self.windows(n, ch, X)
        return out

    # ---------------------------------------------------------------- RS
    def provisional(self, n, ch):
        v = DT(0)
        for k in range(1, n):
            v += self.apply(k, ch, ch.psi[n - k])[ch.idx]
        if n == 1:
            v -= DT(ch.z) / 4
        return v

    def rhs(self, n, ch, with_dn=True):
        acc = np.zeros_like(ch.psi[0])
        for k in range(1, n + 1):
            if k == n and not with_dn:
                acc += self.bare.apply(k, ch.psi[0], ch.field, ch.N, ch.P) - ch.E[k] * ch.psi[0]
            else:
                acc += self.apply(k, ch, ch.psi[n - k]) - ch.E[k] * ch.psi[n - k]
        acc[ch.idx] = 0
        return acc

    def X_of(self, ch, n):
        """X^(n)_{z'z} = <z'| psi_n> (P0 = bath row 0)."""
        v = np.zeros(ZMAX + 1, dtype=DT)
        for j in range(NZ):
            zp = ch.lp[0] + 2 * j
            if zp <= ZMAX:
                v[zp] = ch.psi[n][0, j] if n < len(ch.psi) else 0
        return v

    def bloch(self, n):
        """h^(n)(l) for every l from X^(m), E^(m) of the auxiliary channels (m <= n)."""
        H = {}
        for l in self.cuts:
            h = np.zeros((ZMAX + 1, ZMAX + 1), dtype=DT)
            Xm = {m: np.zeros((ZMAX + 1, ZMAX + 1), dtype=DT) for m in range(n + 1)}
            for z in range(ZMAX + 1):
                ch = self.aux[(z, l)]
                for m in range(n + 1):
                    Xm[m][:, z] = self.X_of(ch, m) if m > 0 else np.eye(ZMAX + 1, dtype=DT)[:, z]
            for z in range(ZMAX + 1):
                ch = self.aux[(z, l)]
                for zp in range(ZMAX + 1):
                    if zp == z:
                        v = ch.E[n]
                    else:
                        v = DT(X0) * (z - zp) * Xm[n][zp, z]
                        for j in range(1, n + 1):
                            v += ch.E[j] * Xm[n - j][zp, z]
                    for m in range(1, n):
                        hm = self.h[m][l]
                        for zz in range(ZMAX + 1):
                            if zz != z:
                                v -= hm[zp, zz] * Xm[n - m][zz, z]
                    h[zp, z] = v
            H[l] = h
        return H

    def run(self):
        bare = self.bare
        chans_aux = [c for k, c in self.aux.items() if k[1] != self.L or k[0] > 3]
        C = [DT(1.5)] + [DT(0)] * ORD
        for n in range(1, ORD + 1):
            prov = {p: self.provisional(n, self.prim[p]) for p in range(4)}
            ts = -DT(1) / 4 if n == 1 else DT(0)
            tc = DT(1) / 4 if n == 1 else DT(0)
            bare.r[n] = (ts - prov[1] + prov[0]) / 2
            bare.g[n] = (tc - prov[3] + prov[0] - 6 * bare.r[n]) / 3
            for p in range(4):
                ch = self.prim[p]
                ch.E[n] = prov[p] + 2 * p * bare.r[n] + DT(p * (p - 1)) / 2 * bare.g[n]
            C[n] = self.prim[2].E[n] - self.prim[0].E[n]
            if n <= AUXORD:
                for ch in chans_aux:
                    ch.E[n] = self.provisional(n, ch) + 2 * ch.z * bare.r[n] + DT(ch.z * (ch.z - 1)) / 2 * bare.g[n]
            if n == ORD:
                break
            bare.build(n)
            active = list(self.prim.values()) + (chans_aux if n <= AUXORD else [])
            # psi_n without D^(n) psi_0 (its P0 part is final: D^(n)|z> has no level-0 component)
            for ch in active:
                ch.psi.append(self.rhs(n, ch, with_dn=False) / ch.den)
            if n <= AUXORD and self.var != "raw" and n >= 1:
                self.h[n] = self.bloch(n)
                self.c1[n] = {l: self.aux[(1, l)].E[n] - self.aux[(0, l)].E[n] for l in self.cuts}
            # add R D^(n) psi_0
            if n >= 2:
                for ch in active:
                    d = self.windows(n, ch, ch.psi[0])
                    d[ch.idx] = 0
                    ch.psi[n] = ch.psi[n] + d / ch.den
        return dict(C=[float(c) for c in C], r=[float(x) for x in bare.r], g=[float(x) for x in bare.g])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--variants", default="raw,W2,W3m,Wb,Wc,Zb")
    ap.add_argument("--delta3", type=float, default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = {}
    for v in a.variants.split(","):
        t0 = time.time()
        s = Solver(a.L, v, a.delta3 if v == "Wcs" else None)
        r = s.run()
        res[v] = r
        print(f"L={a.L} {v:4s} C2..C5 = " + " ".join(f"{c:+.14f}" for c in r["C"][2:6])
              + f"  ({time.time() - t0:.1f}s)", flush=True)
    if a.out:
        json.dump(dict(L=a.L, results=res), open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
