#!/usr/bin/env python3
"""
Independent second implementation (exact fractions.Fraction) of the raw / consistent / zeromode / W / W+V schemes
with primaries and descendant channels, for small L.  Shares NO code with ce_core.py / ce_solver.py:
  * operators from ref_fraction_orig.py (copy of ../rs_exact/ref_fraction.py): literal expansion of :phi^k: over
    ORDERED mode tuples, full J = 0 space (both reflection parities), one Space per field parity; M' and V' by a
    separate builder below (pure zero-mode terms skipped);
  * dict vectors of Fractions, no modular arithmetic;
  * degenerate subspace D0 (H0 = E0): the order-n equation projected on D0 is solved jointly for psi_{n-1}^{D0}
    (constrained u . y = 0) and, for descendant channels, E^(n), by Gaussian elimination of the bordered system
        [ W1|D0 - E1 , -v ] [y ; E^(n)] = -rhs|D0,   u . y = 0      (no precomputed resolvent);
  * h(l) = X Lambda X^-1 by explicit power-series inversion of X (not the recursion of WINDOW_SPEC sec. 2.3);
  * Delta c windows and D^zm built from the channel energies/vectors directly.
The set of auxiliary channels (z, order, cap) is taken from the same bookkeeping files as ce_run.py.
usage: python3 ce_fraction.py --L 4 --schemes raw,consistent,zeromode,W,W+V --out f.json
"""
from fractions import Fraction as Fr
from math import comb
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ref_fraction_orig as RF  # noqa: E402

ORD = RF.ORD
G1 = Fr(1, 3)


def build_prime(sp, kpow, prefactor, ctup):
    """like RF.build_vertex but without the terms whose ladder operators all act on mode (0,0)."""
    cols = []
    for i, s in enumerate(sp.states):
        occ = dict(s)
        N = sp.level[i]
        P = sp.P[i]
        acc = {}
        for kc in range(kpow + 1):
            ka = kpow - kc
            if P - ka + kc > sp.Pmax or ka > P:
                continue
            base = Fr(comb(kpow, kc)) * prefactor
            occ_modes = list(occ.keys())

            def ann_rec(t, cnt, coef, wpoly, Jann, levann):
                if len(t) == ka:
                    budget = sp.L - (N - levann)
                    for (lc, ct) in ctup[kc].get(Jann, ()):
                        if lc > budget:
                            continue
                        if all(m == 0 for m in t) and all(m == 0 for m in ct):
                            continue
                        new = dict(cnt)
                        for m in ct:
                            new[m] = new.get(m, 0) + 1
                        tgt = tuple(sorted((m, c) for m, c in new.items() if c))
                        j = sp.index.get(tgt)
                        if j is None:
                            continue
                        val = [coef * a for a in wpoly]
                        acc[j] = [x + y for x, y in zip(acc[j], val)] if j in acc else val
                    return
                for m in occ_modes:
                    c = cnt.get(m, 0)
                    if c == 0:
                        continue
                    cnt2 = dict(cnt)
                    cnt2[m] = c - 1
                    t.append(m)
                    ann_rec(t, cnt2, coef * c, RF.poly_mul(wpoly, sp.w[m]), Jann + sp.J[m], levann + sp.lev[m])
                    t.pop()

            ann_rec([], dict(occ), base, [Fr(1)] + [Fr(0)] * ORD, 0, 0)
        cols.append([(j, pol) for j, pol in acc.items() if any(pol)])
    return cols


def solve(A, b):
    """Gaussian elimination, A square (list of lists of Fr), returns x."""
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        p = next(r for r in range(c, n) if M[r][c] != 0)
        M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c and M[r][c] != 0:
                f = M[r][c] / M[c][c]
                M[r] = [x - f * y for x, y in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] for i in range(n)]


def nullvec(A):
    """one non-zero null vector of a small square Fraction matrix (asserts nullity 1)."""
    n = len(A)
    M = [list(r) for r in A]
    piv = []
    r = 0
    for c in range(n):
        p = next((i for i in range(r, n) if M[i][c] != 0), None)
        if p is None:
            continue
        M[r], M[p] = M[p], M[r]
        M[r] = [x / M[r][c] for x in M[r]]
        for i in range(n):
            if i != r and M[i][c] != 0:
                f = M[i][c]
                M[i] = [x - f * y for x, y in zip(M[i], M[r])]
        piv.append(c)
        r += 1
    free = [c for c in range(n) if c not in piv]
    assert len(free) == 1, f"nullity {len(free)}"
    v = [Fr(0)] * n
    v[free[0]] = Fr(1)
    for i, pc in enumerate(piv):
        v[pc] = -M[i][free[0]]
    return v


class World:
    def __init__(self, L, Pmax, withVp):
        self.L = L
        self.sp, self.ops = {}, {}
        for par in (0, 1):
            sp = RF.Space(L, par, Pmax[par])
            ctup = RF.ordered_creation_tuples(sp, 4)
            ops = {"M": RF.build_vertex(sp, 2, Fr(1), ctup), "V": RF.build_vertex(sp, 4, Fr(1, 12), ctup),
                   "Mp": build_prime(sp, 2, Fr(1), ctup)}
            if withVp:
                ops["Vp"] = build_prime(sp, 4, Fr(1, 12), ctup)
            self.sp[par], self.ops[par] = sp, ops
            sp.Z = [dict(s).get(0, 0) for s in sp.states]
            # same-chi index map
            sp.chi = {}
            for i, s in enumerate(sp.states):
                chi = tuple((m, c) for m, c in s if m != 0)
                sp.chi.setdefault(chi, {})[sp.Z[i]] = i
            sp.chikey = [tuple((m, c) for m, c in s if m != 0) for s in sp.states]


class FChan:
    def __init__(self, W, par, l, cap, refvec, E0, kmax, name, passive=False, aux_z=None):
        self.W, self.par, self.l, self.cap, self.kmax, self.name = W, par, l, cap, kmax, name
        self.passive, self.aux_z = passive, aux_z
        sp = W.sp[par]
        self.sp, self.ops = sp, W.ops[par]
        self.allowed = [sp.level[i] <= l and sp.P[i] <= cap for i in range(len(sp.states))]
        self.H0 = [sp.level[i] + Fr(sp.P[i], 2) for i in range(len(sp.states))]
        self.E0 = E0
        self.D0 = [i for i in range(len(sp.states)) if self.allowed[i] and self.H0[i] == E0]
        self.v = dict(refvec)
        # W_1 on D0 (exact), left eigenvector u of the eigenvalue of v
        W1 = self.W1mat(self.D0)
        vv = [self.v.get(i, Fr(0)) for i in self.D0]
        Wv = [sum(W1[a][b] * vv[b] for b in range(len(vv))) for a in range(len(vv))]
        a0 = next(a for a in range(len(vv)) if vv[a] != 0)
        self.E1 = Wv[a0] / vv[a0]
        assert all(Wv[a] == self.E1 * vv[a] for a in range(len(vv)))
        m = len(self.D0)
        AT = [[W1[b][a] - (self.E1 if a == b else 0) for b in range(m)] for a in range(m)]
        u = nullvec(AT)
        s = sum(x * y for x, y in zip(u, vv))
        self.u = {i: x / s for i, x in zip(self.D0, u) if x != 0}
        self.W1D = W1
        self.psi = [dict(self.v)]
        self.E = [E0]

    def W1mat(self, idx):
        pos = {j: a for a, j in enumerate(idx)}
        m = len(idx)
        out = [[Fr(0)] * m for _ in range(m)]
        for b, j in enumerate(idx):
            for (r, pol) in self.ops["V"][j]:
                if r in pos:
                    out[pos[r]][b] += G1 * pol[0]
            out[b][b] += Fr(-self.sp.P[j], 4)
        return out

    def opmul(self, name, jord, vec):
        out = {}
        cols = self.ops[name]
        for c, x in vec.items():
            for (r, pol) in cols[c]:
                a = pol[jord]
                if a and self.allowed[r]:
                    out[r] = out.get(r, 0) + a * x
        return out

    def proj(self, vec):
        return sum(x * vec.get(i, 0) for i, x in self.u.items())


def addto(a, b, f=1):
    for k, x in b.items():
        a[k] = a.get(k, 0) + f * x
    return a


class WinTables:
    """windows of every scheme, built from the channel data."""

    def __init__(self, scheme, L, withV=False):
        self.scheme, self.L, self.withV = scheme, L, withV
        self.E = {}        # (z, l) -> list E^(k)
        self.X = {}        # (z, l) -> list of dicts {z': X^(k)_{z'z}}
        self.h = {}        # (k, l) -> dict {(z', z): value}

    def compute_h(self, n, zs, ls):
        """h^(n)(l) = [X Lambda X^-1]^(n) from the series (explicit inversion)."""
        for l in ls:
            # every channel column at this l; orders beyond a channel's kmax are 0 (same convention as the
            # modular code's tables; such entries are outside the claimed set)
            Zl = [z for z in zs if (z, l) in self.E]
            Xk = [{} for _ in range(n + 1)]
            for z in Zl:
                Xk[0][(z, z)] = Fr(1)
                for k in range(1, min(n, len(self.X[(z, l)]) - 1) + 1):
                    for zp, val in self.X[(z, l)][k].items():
                        Xk[k][(zp, z)] = val
            rows = sorted({a for k in range(n + 1) for (a, b) in Xk[k]} | set(Zl))
            Y = [{(r, r): Fr(1) for r in rows}]
            for k in range(1, n + 1):
                acc = {}
                for j in range(1, k + 1):
                    for (a, b), x in Xk[j].items():
                        for (b2, c), y in Y[k - j].items():
                            if b2 == b:
                                acc[(a, c)] = acc.get((a, c), 0) - x * y
                Y.append(acc)
            hn = {}
            for a in range(n + 1):
                for b in range(n + 1 - a):
                    c = n - a - b
                    for (r, z), x in Xk[a].items():
                        Ez = self.E.get((z, l))
                        if Ez is None or len(Ez) <= b:
                            continue
                        lam = Ez[b]
                        if lam == 0:
                            continue
                        for (z2, cc), y in Y[c].items():
                            if z2 == z:
                                hn[(r, cc)] = hn.get((r, cc), 0) + x * lam * y
            self.h[(n, l)] = hn


def run(L, scheme, book, ztiers, dspec, Kprim=16, verbose=True):
    # W, W+V: WINDOW_SPEC 2.10 as changed 2026-10-09 (partners removed from the auxiliary-channel resolvents);
    # WB, W+VB: earlier literal reading (B-equation in the auxiliary channels)
    nopartner = scheme in ("W", "W+V")
    scheme_in = scheme
    scheme = {"WB": "W", "W+VB": "W+V"}.get(scheme, scheme)
    withV = scheme == "W+V"
    Pm_need = 19
    if scheme in ("W", "W+V"):
        Pm_need = max(Pm_need, max(d["cap"] for d in book["channels"].values()))
    if scheme in ("zeromode", "consistent"):
        Pm_need = max(Pm_need, max(c for (k, c) in ztiers.values()))
    Pmax = {0: Pm_need if Pm_need % 2 == 0 else Pm_need - 1, 1: Pm_need if Pm_need % 2 == 1 else Pm_need - 1}
    t0 = time.time()
    W = World(L, Pmax, withV)
    if verbose:
        print(f"# L={L} {scheme}: spaces {[len(W.sp[p].states) for p in (0, 1)]} built {time.time()-t0:.1f}s",
              flush=True)
    ls = list(range(0, L + 1, 2))
    chans = {}
    for p in range(4):
        sp = W.sp[p % 2]
        chans[("p", p)] = FChan(W, p % 2, L, p + Kprim, {sp.ref_index(p): Fr(1)}, Fr(p, 2), ORD, f"p{p}", aux_z=p)
    if scheme in ("W", "W+V"):
        aux = {int(z): (d["kmax"], d["cap"]) for z, d in book["channels"].items()}
    elif scheme in ("zeromode", "consistent"):
        aux = ztiers
    else:
        aux = {}
    for z, (km, cap) in aux.items():
        sp = W.sp[z % 2]
        for l in ls:
            if l == L and z <= 3:
                continue
            chans[("z", z, l)] = FChan(W, z % 2, l, cap, {sp.ref_index(z): Fr(1)}, Fr(z, 2), km, f"z{z}l{l}",
                                       aux_z=z)
    # descendants: vectors built directly (L~ = sum (a+1) A^dag_{a+1,b} A_{ab}, Lbar~ likewise)
    for kind, a in dspec:
        if 2 * a > L:
            continue
        par = 1 if kind == "odd" else 0
        sp = W.sp[par]
        mid = {m: i for i, m in enumerate(sp.modes)}
        vec = {((0, 1),) if kind == "odd" else ((0, 2),): Fr(1)}
        for which in [0] * a + [1] * a:
            new = {}
            for st, c in vec.items():
                occ = dict(st)
                for m, nm in occ.items():
                    aa, bb = sp.modes[m]
                    tgt, wgt = ((aa + 1, bb), aa + 1) if which == 0 else ((aa, bb + 1), bb + 1)
                    occ2 = dict(occ)
                    occ2[m] -= 1
                    if not occ2[m]:
                        del occ2[m]
                    occ2[mid[tgt]] = occ2.get(mid[tgt], 0) + 1
                    key = tuple(sorted(occ2.items()))
                    new[key] = new.get(key, 0) + c * nm * wgt
            vec = new
        ref = {sp.index[k]: x for k, x in vec.items() if x}
        p = 1 if kind == "odd" else 2
        chans[("d", f"{kind}{a}")] = FChan(W, par, L, p + Kprim, ref, Fr(p, 2) + 2 * a, ORD, f"{kind}{a}",
                                           passive=True)
    tab = WinTables(scheme, L, withV)
    zall = sorted({c.aux_z for c in chans.values() if c.aux_z is not None})

    def Dvec(k, ch, vec):
        """D^(k) of the scheme applied to vec in channel ch (cutoff ch.l)."""
        if k < 2 or scheme == "raw":
            return {}
        sp = ch.sp
        l = ch.l
        out = {}
        if scheme in ("consistent", "zeromode"):
            for i, x in vec.items():
                N = sp.level[i]
                if N == 0:
                    continue
                z = 0 if scheme == "consistent" else sp.Z[i]
                e1, e2 = tab.E.get((z, l)), tab.E.get((z, l - N))
                if e1 is None or e2 is None or len(e1) <= k or len(e2) <= k:
                    continue
                d = e1[k] - e2[k]
                if d:
                    out[i] = out.get(i, 0) + d * x
            return out
        # W / W+V: D^zm
        h1, h2 = tab.h.get((k, l), {}), {}
        for i, x in vec.items():
            N = sp.level[i]
            if N == 0:
                continue
            h2 = tab.h.get((k, l - N), {})
            z = sp.Z[i]
            row = sp.chi[sp.chikey[i]]
            for zp, j in row.items():
                if not ch.allowed[j] or abs(zp - z) > 4 * k:
                    continue
                d = h1.get((zp, z), 0) - h2.get((zp, z), 0)
                if d:
                    out[j] = out.get(j, 0) + d * x
        # D^M, D^V
        for opn, cfun, pref in (("Mp", lambda e: e[1] - e[0], Fr(1, 4)),
                                ("Vp", lambda e: e[2] - 2 * e[1] + e[0], Fr(1, 2))):
            if opn == "Vp" and not withV:
                continue
            for j in range(2, k + 1):
                def cval(ll):
                    es = [tab.E.get((zz, ll)) for zz in (0, 1, 2)]
                    if any(e is None or len(e) <= j for e in es[:(3 if opn == "Vp" else 2)]):
                        return None
                    return cfun([e[j] if e is not None and len(e) > j else 0 for e in es])
                cl = cval(l)
                if cl is None:
                    continue
                f = {}
                for i, x in vec.items():
                    N = sp.level[i]
                    cN = cval(l - N) if N else cl
                    f[i] = (cl - cN)
                fx = {i: f[i] * x for i, x in vec.items() if f[i]}
                y1 = ch.opmul(opn, k - j, vec)
                for r, val in y1.items():
                    N = sp.level[r]
                    cN = cval(l - N) if N else cl
                    if cl - cN:
                        out[r] = out.get(r, 0) + pref * (cl - cN) * val
                addto(out, ch.opmul(opn, k - j, fx), pref)
        return {i: x for i, x in out.items() if x}

    r = [Fr(0)] * (ORD + 1)
    g = [Fr(0)] * (ORD + 1)
    xs = [Fr(1, 2), Fr(-1, 4)] + [Fr(0)] * (ORD - 1)

    def rhs0(ch, n):
        out = {}
        for j in range(n):
            for name, c in (("M", r), ("V", g)):
                u = {}
                for k in range(j + 1, n + 1):
                    if k == n and j == 0:
                        continue
                    if c[k - j]:
                        addto(u, ch.psi[n - k], c[k - j])
                if u:
                    addto(out, ch.opmul(name, j, u))
        sp = ch.sp
        addto(out, {i: Fr(-sp.P[i], 4) * x for i, x in ch.psi[n - 1].items()})
        for k in range(2, n):
            addto(out, Dvec(k, ch, ch.psi[n - k]))
        for k in range(1, n):
            addto(out, ch.psi[n - k], -ch.E[k])
        return out

    def d0solve(ch, out, n, with_E):
        """joint solve on D0 for y = psi_{n-1}^{D0} (u.y = 0) [and E^(n)]; returns updated rhs and E^(n)."""
        D0 = ch.D0
        m = len(D0)
        if m == 1 or n == 1:
            return out, (ch.proj(out) if with_E else None)
        # unknowns: y (m) [+ E]; equations: (W1D - E1) y - E v = -rhs_D0 (m rows) and u.y = 0
        nun = m + (1 if with_E else 0)
        A, b = [], []
        vv = [ch.v.get(i, Fr(0)) for i in D0]
        for a in range(m):
            row = [ch.W1D[a][c] - (ch.E1 if a == c else 0) for c in range(m)]
            if with_E:
                row.append(-vv[a])
            A.append(row)
            b.append(-out.get(D0[a], 0))
        A.append([ch.u.get(i, Fr(0)) for i in D0] + ([Fr(0)] if with_E else []))
        b.append(Fr(0))
        if not with_E:
            # E^(n) not an unknown: the system is consistent only along v; least-norm via the u-row (square
            # after dropping one dependent row): drop the projection row u . eq, i.e. solve with E as unknown
            A = [row + [-vv[a]] for a, row in enumerate(A[:m])] + [A[m] + [Fr(0)]]
            sol = solve(A, b)
            y, E = sol[:m], sol[m]
        else:
            sol = solve(A, b)
            y, E = sol[:m], sol[m]
        yd = {D0[a]: y[a] for a in range(m) if y[a]}
        for i, x in yd.items():
            ch.psi[n - 1][i] = ch.psi[n - 1].get(i, 0) + x
        # add (W_1 - E1) y
        addto(out, ch.opmul("V", 0, yd), G1)
        addto(out, {i: Fr(-ch.sp.P[i], 4) * x for i, x in yd.items()})
        addto(out, yd, -ch.E1)
        res = [out.get(D0[a], 0) - E * vv[a] for a in range(m)]
        assert all(x == 0 for x in res), f"{ch.name}: D0 equation not satisfied"
        return out, E

    def finish_psi(ch, out):
        ps = {}
        D0s = set(ch.D0)
        for i, x in out.items():
            if i in D0s or x == 0:
                continue
            ps[i] = x / (ch.E0 - ch.H0[i])
        ch.psi.append(ps)

    C = [Fr(1)]
    active = [c for c in chans.values() if not c.passive]
    passive = [c for c in chans.values() if c.passive]
    for n in range(1, ORD + 1):
        rh = {}
        for c in active:
            if c.kmax >= n:
                out = rhs0(c, n)
                if not (nopartner and c.aux_z is not None):
                    out, _ = d0solve(c, out, n, False)
                rh[c.name] = out
        X = {p: chans[("p", p)].proj(rh[f"p{p}"]) for p in range(4)}
        r[n] = (xs[n] - X[1] + X[0]) / 2
        g[n] = (-xs[n] - X[3] + X[0] - 6 * r[n]) / 3
        for c in active:
            if c.kmax >= n:
                out = rh[c.name]
                addto(out, c.opmul("M", 0, c.psi[0]), r[n])
                addto(out, c.opmul("V", 0, c.psi[0]), g[n])
                c.E.append(c.proj(out))
                if c.aux_z is not None:
                    tab.E.setdefault((c.aux_z, c.l), [c.E0]).append(c.E[n])
                    sp = c.sp
                    Xd = {}
                    for zp in range(sp.parity, sp.Pmax + 1, 2):
                        if zp == c.aux_z or zp > c.cap:
                            continue
                        i = sp.ref_index(zp)
                        if out.get(i, 0):
                            Xd[zp] = out[i] / (c.E0 - c.H0[i])
                    lst = tab.X.setdefault((c.aux_z, c.l), [{}])
                    lst.append(Xd)
        if scheme in ("W", "W+V"):
            tab.compute_h(n, zall, ls)
        for c in active:
            if c.kmax >= n:
                out = rh[c.name]
                Dx = Dvec(n, c, c.psi[0])
                assert c.proj(Dx) == 0
                addto(out, Dx)
                finish_psi(c, out)
        for c in passive:
            out = rhs0(c, n)
            addto(out, c.opmul("M", 0, c.psi[0]), r[n])
            addto(out, c.opmul("V", 0, c.psi[0]), g[n])
            addto(out, Dvec(n, c, c.psi[0]))
            out, En = d0solve(c, out, n, True)
            c.E.append(En)
            finish_psi(c, out)
        C.append(chans[("p", 2)].E[n] - chans[("p", 0)].E[n])
        if verbose:
            print(f"#   order {n}: C_{n} = {float(C[n]):.12g}  ({time.time()-t0:.1f}s)", flush=True)
    return {"C": [str(x) for x in C], "r": [str(x) for x in r], "g": [str(x) for x in g],
            "E": [[str(x) for x in chans[("p", p)].E] for p in range(4)],
            "Edesc": {k[1]: [str(x) for x in c.E] for k, c in chans.items() if k[0] == "d"}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--schemes", default="raw,consistent,zeromode,W,W+V,WB,W+VB")
    ap.add_argument("--desc", default="odd:all,even:1-2")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    book = json.load(open(os.path.join(HERE, "results", "book_W_V_desc.json")))
    zt = {int(z): (d["kmax"], d["cap"]) for z, d in json.load(open(os.path.join(HERE, "results",
                                                                             "tiers_zeromode_desc.json"))).items()}
    ct = {int(z): (d["kmax"], d["cap"]) for z, d in json.load(open(os.path.join(HERE, "results",
                                                                             "tiers_consistent_desc.json"))).items()}
    dspec = []
    for part in a.desc.split(","):
        kind, rng = part.split(":")
        lst = range(1, a.L // 2 + 1) if rng == "all" else (
            range(int(rng.split("-")[0]), int(rng.split("-")[1]) + 1) if "-" in rng else [int(rng)])
        dspec += [(kind, x) for x in lst]
    res = {}
    for s in a.schemes.split(","):
        res[s] = run(a.L, s, book, ct if s == "consistent" else zt, dspec)
    json.dump({"L": a.L, "schemes": res}, open(a.out, "w"), indent=1)
    print(f"# wrote {a.out}")


if __name__ == "__main__":
    main()
