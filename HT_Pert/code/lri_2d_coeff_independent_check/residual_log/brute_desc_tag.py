#!/usr/bin/env python3
"""Tagged-external descendant test (exact Fractions), scheme Wc, through eps^3.

The descendant chi_aa = A^dag_aa|0> is computed with its EXTERNAL line tagged: the initial quantum is a separate mode
X_in (absorbable only) and the final quantum a separate mode X_out (creatable only, occupation <= 1); both are copies
of the (a,a) mode (level 2a, J = 0, weight w_aa).  Every other (a,a) quantum is an ordinary internal quantum.
Gluing: the model states |X_in>, |X_out> and the regular |chi_aa> are all identified with the real |chi_aa>; they are
excluded from every resolvent, E_n = rhs_n[X_in] + rhs_n[X_out], and histories that end on the regular |chi_aa>
(double counts of the X_out histories) are dropped.  With nu_in = nu_out = 2a (tags charged to the level budget and
seen by every window) this reproduces the real chi channel exactly (validation against brute_desc.py, scheme Wc).
With nu_in = nu_out = 0 the external lines are invisible to the cutoff and to the windows ("budget-free external"),
i.e. the descendant self-energy is computed with exactly the budget of the phi self-energy.  Mixed charges give the
slice-resolved response to the in leg or the out leg alone.
usage: python3 brute_desc_tag.py --L 6 --a 1 --nu 2,2 [--nu 0,0 ...] [--out x.json]"""
import argparse
import json
import os
import sys
import time
from fractions import Fraction as Fr
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brute_W5 as bw  # noqa: E402

rf = bw.rf
G1 = Fr(1, 3)


class TagSpace:
    """J = 0 Fock states (both reflection parities) of the regular modes (level <= L) plus the tags X_in, X_out.
    level = true level (enters H0), blevel = budget level (tags count nu_in, nu_out); states with blevel <= L,
    total particle number P <= Pmax, total field parity odd (P odd)."""

    def __init__(self, L, a, nu_in, nu_out, Pmax, zero_like_tags=False):
        base = {par: rf.Space(L, par, Pmax) for par in (0, 1)}
        sp0 = base[0]
        self.L, self.Pmax = L, Pmax
        nm = len(sp0.modes)
        self.nreg = nm
        self.iX, self.oX = nm, nm + 1
        self.maa = sp0.midx.get((a, a))          # None if the cutoff is below the (a,a) mode (tags still exist)
        self.modes = list(sp0.modes) + [("Xin", a), ("Xout", a)]
        self.midx = dict(sp0.midx)
        self.lev = list(sp0.lev) + [2 * a, 2 * a]
        self.blev = list(sp0.lev) + [nu_in, nu_out]
        self.J = list(sp0.J) + [0, 0]
        waa = rf.poly_mul(rf.poch_over_fact(a), rf.poch_over_fact(a))
        self.w = list(sp0.w) + [waa, waa]
        states = []
        for (nin, nout) in ((1, 0), (0, 1), (1, 1), (0, 0)):
            nt = nin + nout
            par = (1 - nt) % 2
            bl = nin * nu_in + nout * nu_out
            b = base[par]
            for s, lv, P in zip(b.states, b.level, b.P):
                if P + nt > Pmax or lv + bl > L:
                    continue
                st = list(s)
                if nin:
                    st.append((self.iX, 1))
                if nout:
                    st.append((self.oX, 1))
                states.append(tuple(st))
        self.states = states
        self.index = {s: i for i, s in enumerate(states)}
        self.level = [sum(self.lev[m] * c for m, c in s) for s in states]
        self.blevel = [sum(self.blev[m] * c for m, c in s) for s in states]
        self.P = [sum(c for m, c in s) for s in states]
        self.ref = self.index[((self.iX, 1),)]
        self.xout = self.index[((self.oX, 1),)]
        self.chireg = self.index.get(((self.maa, 1),)) if self.maa is not None else None
        # modes treated as zero mode in the M'/V' exclusion (a = 0 tags are zero-mode copies; 'real' convention)
        self.zero_like = {0, self.iX, self.oX} if zero_like_tags else {0}


def tag_creation_tuples(sp, kmax):
    """dict k -> dict J -> list of (budget level, ordered tuple) over the creatable modes (regular + X_out)."""
    creat = list(range(sp.nreg)) + [sp.oX]
    out = {}
    for k in range(kmax + 1):
        d = {}

        def rec(t, bl, J, nout):
            if len(t) == k:
                d.setdefault(J, []).append((bl, tuple(t)))
                return
            for i in creat:
                if i == sp.oX and nout:
                    continue
                if bl + sp.blev[i] <= sp.L:
                    t.append(i)
                    rec(t, bl + sp.blev[i], J + sp.J[i], nout + (i == sp.oX))
                    t.pop()

        rec([], 0, 0, 0)
        out[k] = d
    return out


def build_tag_op(sp, ctup, kpow, prefactor, prime=False, legw=False):
    """S^-1 O S on the tagged space, O = prefactor <:phi^kpow:>_theta with phi^+ = regular + w_aa X_in and
    phi^- = regular + X_out^dag.  prime: drop the pure zero-mode terms (M', V').  Column lists (row, eps-poly).
    legw (kpow = 2, prime): the operator X = M'^{+-}_nu (WINDOW_SPEC Sec. 2.5a): each term weighted by
    s * (sum of the budget levels of its non-zero-like legs), s = +1 hop, -1 pair."""
    cols = []
    for i, s in enumerate(sp.states):
        occ = dict(s)
        NB = sp.blevel[i]
        P = sp.P[i]
        acc = {}
        for kc in range(kpow + 1):
            ka = kpow - kc
            if P - ka + kc > sp.Pmax or ka > P:
                continue
            base = Fr(comb(kpow, kc)) * prefactor
            occ_modes = [m for m in occ.keys() if m != sp.oX]

            def ann_rec(t, cnt, coef, wpoly, Jann, blann):
                if len(t) == ka:
                    budget = sp.L - (NB - blann)
                    for (lc, ct) in ctup[kc].get(Jann, ()):
                        if lc > budget:
                            continue
                        if prime and all(m in sp.zero_like for m in t) and all(m in sp.zero_like for m in ct):
                            continue
                        wl = 1
                        if legw:
                            # leg level = budget level: a zero-mode-like tag carries its charge (it stands for an
                            # external line of that level); the regular zero mode has level 0
                            wl = (1 if (ka == 1 and kc == 1) else -1) * sum(sp.blev[m] for m in list(t) + list(ct))
                            if wl == 0:
                                continue
                        new = dict(cnt)
                        for m in ct:
                            new[m] = new.get(m, 0) + 1
                        tgt = tuple(sorted((m, c) for m, c in new.items() if c))
                        j = sp.index.get(tgt)
                        if j is None:
                            continue
                        val = [coef * wl * x for x in wpoly]
                        acc[j] = [x + y for x, y in zip(acc[j], val)] if j in acc else val
                    return
                for m in occ_modes:
                    c = cnt.get(m, 0)
                    if c == 0:
                        continue
                    cnt2 = dict(cnt)
                    cnt2[m] = c - 1
                    t.append(m)
                    ann_rec(t, cnt2, coef * c, rf.poly_mul(wpoly, sp.w[m]), Jann + sp.J[m], blann + sp.blev[m])
                    t.pop()

            ann_rec([], dict(occ), base, [Fr(1)] + [Fr(0)] * rf.ORD, 0, 0)
        cols.append([(j, pol) for j, pol in acc.items() if any(pol)])
    return cols


class TagChannel(bw.DChannel):
    """Glued tagged chi channel.  Reference |X_in>; model states {X_in, X_out, chi_reg}; partners = the other
    regular states degenerate with the reference (B-equation)."""

    def __init__(self, sp, ops, a, K):
        self.name, self.sp, self.ops, self.p, self.l = "tag", sp, ops, 1, sp.L
        self.ref = sp.ref
        self.model = {sp.ref, sp.xout} | ({sp.chireg} if sp.chireg is not None else set())
        self.allowed = [sp.P[i] <= 1 + K for i in range(len(sp.states))]
        self.E0ref = Fr(1, 2) + 2 * a
        self.H0 = [sp.level[i] + Fr(sp.P[i], 2) for i in range(len(sp.states))]
        self.Dfun = lambda k, N: 0
        self.psi = [{self.ref: Fr(1)}]
        self.E = [self.E0ref]
        self.Dops = {}
        self.drop_degenerate = True
        self.bequation = True

    def b_equation(self, n, rhs):
        B = [i for i in range(len(self.sp.states)) if self.allowed[i] and i not in self.model
             and self.H0[i] == self.E0ref]
        if not B or n < 2:
            return rhs
        E1 = self.E[1]
        Bset = {b: k for k, b in enumerate(B)}
        nb = len(B)
        A = [[Fr(0)] * nb for _ in range(nb)]
        for c in B:
            w = self.matvec("V", 0, {c: Fr(1)})
            for r_, v in w.items():
                if r_ in Bset:
                    A[Bset[r_]][Bset[c]] -= G1 * v
            A[Bset[c]][Bset[c]] -= Fr(-self.sp.P[c], 4)
            A[Bset[c]][Bset[c]] += E1
        bvec = [rhs.get(b, Fr(0)) for b in B]
        x = bw._solve(A, bvec)
        xd = {B[k]: x[k] for k in range(nb) if x[k] != 0}
        if xd:
            add = self.matvec("V", 0, xd)
            for r_, v in add.items():
                rhs[r_] = rhs.get(r_, 0) + G1 * v
            for r_, v in xd.items():
                rhs[r_] = rhs.get(r_, 0) + (-Fr(self.sp.P[r_], 4) - E1) * v
            for r_, v in xd.items():
                self.psi[n - 1][r_] = v
        for b in B:
            assert rhs.get(b, 0) == 0, "B part of rhs did not vanish"
        return rhs

    def finish_order(self, n, rhs0, rn, gn):
        rhs = dict(rhs0)
        rhs = self.b_equation(n, rhs)
        for opname, c in (("M", rn), ("V", gn)):
            if c:
                for idx, v in self.matvec(opname, 0, {self.ref: Fr(1)}).items():
                    rhs[idx] = rhs.get(idx, 0) + c * v
        En = rhs.get(self.sp.ref, Fr(0)) + rhs.get(self.sp.xout, Fr(0))
        psi = {}
        for idx, v in rhs.items():
            if idx in self.model or v == 0:
                continue
            den = self.E0ref - self.H0[idx]
            if den == 0:
                continue
            psi[idx] = v / den
        self.E.append(En)
        self.psi.append(psi)
        return En


def run(L, a, nus, phinus=(), K=8, verbose=True):
    rf.ORD = 5
    bw.ORD = 5
    t0 = time.time()
    spaces, ops, Mp = {}, {}, {}
    for par in (0, 1):
        sp = rf.Space(L, par, bw.ZMAX + K)
        ctup = rf.ordered_creation_tuples(sp, 4)
        ops[par] = {"M": rf.build_vertex(sp, 2, Fr(1), ctup), "V": rf.build_vertex(sp, 4, Fr(1, 12), ctup)}
        Mp[par] = bw.build_Mprime_poly(sp, ctup)
        spaces[par] = sp
    if verbose:
        print(f"# regular spaces built t={time.time() - t0:.1f}s", flush=True)
    ls = list(range(0, L + 1, 2))
    zero = lambda k, N: 0
    r = [Fr(0)] * 6
    g = [Fr(0)] * 6
    g[1] = G1
    xser = [Fr(1, 2), Fr(-1, 4)] + [Fr(0)] * 4
    aux = {(z, l): bw.DChannel(f"z{z}l{l}", spaces[z % 2], ops[z % 2], z, l, K, zero, drop_degenerate=True,
                               bequation=False)
           for z in range(bw.ZMAX + 1) for l in ls}
    prim = {p: bw.DChannel(f"p{p}", spaces[p % 2], ops[p % 2], p, L, K, zero) for p in range(4)}
    tags = {}
    for nu in nus:
        tsp = TagSpace(L, a, nu[0], nu[1], 1 + K)
        tct = tag_creation_tuples(tsp, 4)
        tops = {"M": build_tag_op(tsp, tct, 2, Fr(1)), "V": build_tag_op(tsp, tct, 4, Fr(1, 12))}
        tMp = build_tag_op(tsp, tct, 2, Fr(1), prime=True)
        tags[nu] = (tsp, tops, tMp, TagChannel(tsp, tops, a, K))
        if verbose:
            print(f"# tagged space nu={nu}: {len(tsp.states)} states, t={time.time() - t0:.1f}s", flush=True)
    for pn in phinus:                     # zero-mode-tagged phi channel: c1 with charged external lines
        tsp = TagSpace(L, 0, pn[0], pn[1], 1 + K, zero_like_tags=(pn[2] == "real"))
        tct = tag_creation_tuples(tsp, 4)
        tops = {"M": build_tag_op(tsp, tct, 2, Fr(1)), "V": build_tag_op(tsp, tct, 4, Fr(1, 12))}
        tMp = build_tag_op(tsp, tct, 2, Fr(1), prime=True)
        tags[pn] = (tsp, tops, tMp, TagChannel(tsp, tops, 0, K))
        if verbose:
            print(f"# phi-tagged space {pn}: {len(tsp.states)} states, t={time.time() - t0:.1f}s", flush=True)
    h = {}

    def tune(n):
        rhs0 = {p: prim[p].rhs_without_new(n, r, g) for p in range(4)}
        X = {p: rhs0[p].get(prim[p].ref, Fr(0)) for p in range(4)}
        r[n] = (xser[n] - X[1] + X[0]) / 2
        g[n] = (-xser[n] - X[3] + X[0] - 6 * r[n]) / 3
        for p in range(4):
            prim[p].finish_order(n, rhs0[p], r[n], g[n])

    for c_ in aux.values():
        c_.finish_order(1, c_.rhs_without_new(1, r, g), r[1], g[1])
    for (z, l), c_ in aux.items():
        rhs2 = c_.rhs_without_new(2, r, g)
        for zp in range(z % 2, bw.ZMAX + 1, 2):
            h[(zp, z, l)] = rhs2.get(spaces[z % 2].ref_index(zp), Fr(0))

    def c1_2(l):
        return h[(1, 1, l)] - h[(0, 0, l)]

    def make_D2(l, sp, cols, lev, lref):
        def apply(vec):
            o = {}
            for c, v in vec.items():
                N = lev(c)
                if N <= 0:
                    continue
                st = dict(sp.states[c])
                z = st.get(0, 0)
                if z <= bw.ZMAX:
                    for zp in range(z % 2, bw.ZMAX + 1, 2):
                        d = h[(zp, z, l)] - h[(zp, z, l - N)]
                        if d == 0:
                            continue
                        st2 = dict(st)
                        if zp:
                            st2[0] = zp
                        else:
                            st2.pop(0, None)
                        j = sp.index.get(tuple(sorted(st2.items())))
                        if j is not None:
                            o[j] = o.get(j, 0) + d * v
            for c, v in vec.items():
                N = lev(c)
                for (row, pol) in cols[c]:
                    Nr = lev(row)
                    if Nr > l:
                        continue
                    w = Fr(1, 4) * ((c1_2(lref) - c1_2(l - Nr)) + (c1_2(lref) - c1_2(l - N)))
                    if w and pol[0]:
                        o[row] = o.get(row, 0) + w * pol[0] * v
            return o
        return apply

    lev_std = lambda par: (lambda i: spaces[par].level[i])
    for p in range(4):
        prim[p].Dops = {2: make_D2(L, spaces[p % 2], Mp[p % 2], lev_std(p % 2), L)}
    for nu, (tsp, tops, tMp, ch) in tags.items():
        ch.Dops = {2: make_D2(L, tsp, tMp, (lambda s_: (lambda i: s_.blevel[i]))(tsp), L)}
    for n in (1, 2):
        tune(n)
        for nu, (tsp, tops, tMp, ch) in tags.items():
            ch.finish_order(n, ch.rhs_without_new(n, r, g), r[n], g[n])
    for (z, l), c_ in aux.items():
        c_.Dops = {2: make_D2(l, spaces[z % 2], Mp[z % 2], lev_std(z % 2), L)}
        c_.finish_order(2, c_.rhs_without_new(2, r, g), r[2], g[2])
    for (z, l), c_ in aux.items():
        if z < 8:
            c_.finish_order(3, c_.rhs_without_new(3, r, g), Fr(0), Fr(0))
    h3 = {}
    for l in ls:
        for z in range(7):
            sp = spaces[z % 2]
            c_ = aux[(z, l)]
            idx = lambda zz: sp.ref_index(zz)
            X = {n_: {zz: c_.psi[n_].get(idx(zz), Fr(0)) for zz in range(z % 2, bw.ZMAX + 1, 2) if zz != z}
                 for n_ in (1, 2, 3)}

            def h1m(zp, zz):
                w = c_.matvec("V", 0, {idx(zz): Fr(1)})
                return G1 * w.get(idx(zp), Fr(0)) + (Fr(-zz, 4) if zp == zz else 0)
            for zp in range(z % 2, 7, 2):
                v = (Fr(z - zp, 2) * X[3][zp] + c_.E[1] * X[2][zp] + c_.E[2] * X[1][zp]) if zp != z else c_.E[3]
                for zz in range(z % 2, bw.ZMAX + 1, 2):
                    if zz == z:
                        continue
                    hz = h1m(zp, zz)
                    if hz:
                        v -= hz * X[2][zz]
                    if X[1][zz]:
                        v -= h[(zp, zz, l)] * X[1][zz]
                h3[(zp, z, l)] = v

    def c1_3(l):
        return aux[(1, l)].E[3] - aux[(0, l)].E[3]

    def make_D3(l, sp, cols, lev):
        def apply(vec):
            o = {}
            for c, v in vec.items():
                N = lev(c)
                if N <= 0:
                    continue
                z = dict(sp.states[c]).get(0, 0)
                if z <= 6:
                    st = dict(sp.states[c])
                    for zp in range(z % 2, 7, 2):
                        d = h3[(zp, z, l)] - h3[(zp, z, l - N)]
                        if d == 0:
                            continue
                        st2 = dict(st)
                        if zp:
                            st2[0] = zp
                        else:
                            st2.pop(0, None)
                        j = sp.index.get(tuple(sorted(st2.items())))
                        if j is not None:
                            o[j] = o.get(j, 0) + d * v
            for c, v in vec.items():
                N = lev(c)
                for (row, pol) in cols[c]:
                    Nr = lev(row)
                    if Nr > l:
                        continue
                    w3 = Fr(1, 4) * ((c1_3(l) - c1_3(l - Nr)) + (c1_3(l) - c1_3(l - N)))
                    w2 = Fr(1, 4) * ((c1_2(l) - c1_2(l - Nr)) + (c1_2(l) - c1_2(l - N)))
                    val = w3 * pol[0] + w2 * pol[1]
                    if val:
                        o[row] = o.get(row, 0) + val * v
            return o
        return apply

    for p in range(4):
        prim[p].Dops[3] = make_D3(L, spaces[p % 2], Mp[p % 2], lev_std(p % 2))
    for nu, (tsp, tops, tMp, ch) in tags.items():
        ch.Dops[3] = make_D3(L, tsp, tMp, (lambda s_: (lambda i: s_.blevel[i]))(tsp))
    tune(3)
    res = {"L": L, "a": a, "c1_2": [str(c1_2(l)) for l in ls], "c1_3": [str(c1_3(l)) for l in ls]}
    res["c1_2L"], res["c1_3L"] = str(c1_2(L)), str(c1_3(L))
    res["r"], res["g"] = [str(x) for x in r[:4]], [str(x) for x in g[:4]]
    for nu, (tsp, tops, tMp, ch) in tags.items():
        ch.finish_order(3, ch.rhs_without_new(3, r, g), r[3], g[3])
        if len(nu) == 3:
            c = [ch.E[n] - prim[0].E[n] for n in range(4)]
            key = f"phi{nu[0]}_{nu[1]}_{nu[2]}"
            res[key] = {"c1tag": [str(x) for x in c], "c1tag_float": [float(x) for x in c]}
            if verbose:
                print(f"# L={L} phi-tag {nu}: c1tag_2 = {float(c[2]):+.12f} (c1_2(L) = {float(c1_2(L)):+.12f})  "
                      f"c1tag_3 = {float(c[3]):+.12f} (c1_3(L) = {float(c1_3(L)):+.12f})", flush=True)
            continue
        R = [ch.E[n] - prim[1].E[n] for n in range(4)]
        R[0] -= 2 * a
        key = f"nu{nu[0]}_{nu[1]}"
        res[key] = {"R": [str(x) for x in R], "R_float": [float(x) for x in R]}
        if verbose:
            print(f"# L={L} a={a} nu={nu}: R_2 = {float(R[2]):+.12f}  R_3 = {float(R[3]):+.12f}  "
                  f"t={time.time() - t0:.1f}s", flush=True)
    # slice-resolved self-window on the chi line (eps^3): replace w_aa Delta c1^(3)(L, 2a) by
    # w_aa [c1^(3)(L) - c1tag^(3)(L; 2a, 2a)]
    w0 = rf.poch_over_fact(a)[0] ** 2
    for conv in ("real", "chi"):
        k = f"phi{2 * a}_{2 * a}_{conv}"
        if k in res and f"nu{2 * a}_{2 * a}" in res and L - 2 * a >= 0:
            R3 = Fr(res[f"nu{2 * a}_{2 * a}"]["R"][3])
            # c1tag includes the tuned r_3 (c1tag(L; 0, 0) = 0); c1_3 excludes r_3: compare on the same footing
            new = R3 + w0 * (c1_3(L - 2 * a) - (Fr(res[k]["c1tag"][3]) - 2 * r[3]))
            res[f"R3_slice_{conv}"] = str(new)
            if verbose:
                print(f"# L={L} a={a} R_3(Wc) = {float(R3):+.12f} -> slice-resolved self-window ({conv}): "
                      f"{float(new):+.12f}", flush=True)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--a", type=int, default=1)
    ap.add_argument("--nu", action="append", default=None, help="nu_in,nu_out (repeatable)")
    ap.add_argument("--phinu", action="append", default=[], help="nu_in,nu_out,conv (conv = real|chi; repeatable)")
    ap.add_argument("--out", default=None)
    x = ap.parse_args()
    nus = [] if x.nu == ["none"] else [tuple(int(t) for t in s.split(",")) for s in (x.nu or [f"{2 * x.a},{2 * x.a}", "0,0"])]
    phinus = [(int(s.split(",")[0]), int(s.split(",")[1]), s.split(",")[2]) for s in x.phinu]
    res = run(x.L, x.a, nus, phinus)
    if x.out:
        json.dump(res, open(x.out, "w"), indent=1)
