#!/usr/bin/env python3
"""Brute-force exact (Fraction) check of the zero-mode-aware ('corrected') window at order eps^4.

Uses ../rs_exact/ref_fraction.py READ-ONLY (imported, not modified): full Rayleigh-Schroedinger in the
truncated Fock space with exact rationals.  Channel is subclassed so that the diagonal window sees the
zero-mode occupation z of each basis state:
    corrected:   D_l(z, N) = E_z^(2)(l) - E_z^(2)(l - N)   (order eps^2 only; D_k = 0 for k >= 3),
where E_z^(2)(l) is the order-eps^2 energy of |z> = (A_00^dag)^z/sqrt(z!)|0> in the cutoff-l Hamiltonian,
obtained from auxiliary RS channels |z>, l = 0, 2, ..., L, z = 0..ZMAX, advanced in lock-step with the same
r, g.  (Only D_2 matters for C_4; higher D_k first enter C_5.)  For comparison the same driver runs the raw
and the consistent scheme (consistent: D_l(N) = E_v(l) - E_v(l - N), also D_2 only -> same C_4).
Also checks that no second-order denominator of any |z> channel vanishes, and that E_v^(2)(l) =
-(l+2)(l+4)/864.
usage: python3 brute_corrected.py --L 8 [--out brute_L8.json]"""
import argparse
import json
import os
import sys
import time
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("RS_EXACT_DIR", os.path.join(HERE, "..", "rs_exact")))
import ref_fraction as rf  # noqa: E402

ORD = 4
rf.ORD = ORD
ZMAX = 7  # |p> with p <= 3 reaches z <= p + 4 = 7 in psi_1


class ZChannel(rf.Channel):
    """Channel whose window is D(k, N, z)."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.z = [dict(s).get(0, 0) for s in self.sp.states]  # mode index 0 is (0,0)

    def rhs_without_new(self, n, r, g):
        sp = self.sp
        out = {}

        def add(d, s=1):
            for k_, v in d.items():
                out[k_] = out.get(k_, 0) + s * v

        for j in range(0, n):
            for opname, coef in (("M", r), ("V", g)):
                u = {}
                for k in range(j + 1, n + 1):
                    if k == n and j == 0:
                        continue
                    c = coef[k - j]
                    if c == 0:
                        continue
                    for idx, v in self.psi[n - k].items():
                        u[idx] = u.get(idx, 0) + c * v
                if u:
                    add(self.matvec(opname, j, u))
        for idx, v in self.psi[n - 1].items():
            out[idx] = out.get(idx, 0) - Fr(sp.P[idx], 4) * v
        for k in range(1, n + 1):
            for idx, v in self.psi[n - k].items():
                d = self.Dfun(k, sp.level[idx], self.z[idx])
                if d:
                    out[idx] = out.get(idx, 0) + d * v
        for k in range(1, n):
            for idx, v in self.psi[n - k].items():
                out[idx] = out.get(idx, 0) - self.E[k] * v
        return out

    def check_denominators(self):
        """No vanishing denominator among the states reached at first order (psi_1)."""
        for idx in self.psi[1]:
            if self.E0ref - self.H0[idx] == 0:
                raise RuntimeError(f"vanishing denominator in channel {self.name}")


def run(L, K=8, verbose=True):
    t0 = time.time()
    spaces, ops = {}, {}
    for par in (0, 1):
        pmax_ref = 6 if par == 0 else 7          # aux channels up to z = 7
        sp = rf.Space(L, par, pmax_ref + K)
        ctup = rf.ordered_creation_tuples(sp, 4)
        ops[par] = {"M": rf.build_vertex(sp, 2, Fr(1), ctup), "V": rf.build_vertex(sp, 4, Fr(1, 12), ctup)}
        spaces[par] = sp
        if verbose:
            print(f"# L={L} parity={par}: {len(sp.states)} states  t={time.time() - t0:.1f}s", flush=True)
    ls = list(range(0, L + 1, 2))
    E2z = {}  # (z, l) -> E_z^(2)(l)
    zero = lambda k, N, z: 0

    def D_corr(k, N, z):
        if k != 2 or N == 0:
            return 0
        if z > ZMAX:
            # only reached in psi_2 (P <= p + 8); D_2 psi_2 enters RHS_4, whose reference component (= E_4)
            # it cannot touch (D(ref) = 0), so these states never influence E_p^(4) or C_4.
            return 0
        return E2z[(z, L)] - E2z[(z, L - N)]

    def D_cons(k, N, z):
        if k != 2 or N == 0:
            return 0
        return E2z[(0, L)] - E2z[(0, L - N)]

    aux = {(z, l): ZChannel(f"z{z}l{l}", spaces[z % 2], ops[z % 2], z, l, K, zero)
           for z in range(ZMAX + 1) for l in ls}
    schemes = {"raw": zero, "consistent": D_cons, "corrected": D_corr}
    prim = {s: {p: ZChannel(f"{s}p{p}", spaces[p % 2], ops[p % 2], p, L, K, Df) for p in range(4)}
            for s, Df in schemes.items()}
    r = [Fr(0)] * (ORD + 1)
    g = [Fr(0)] * (ORD + 1)
    xser = [Fr(1, 2), Fr(-1, 4)] + [Fr(0)] * (ORD - 1)
    C = {s: [Fr(1)] for s in schemes}
    rg = {s: ([Fr(0)] * (ORD + 1), [Fr(0)] * (ORD + 1)) for s in schemes}
    for n in range(1, ORD + 1):
        # every scheme tunes its own r_n, g_n from its own primaries (identical through n = 3)
        for s in schemes:
            rs_, gs_ = rg[s]
            ch = prim[s]
            rhs0 = {p: ch[p].rhs_without_new(n, rs_, gs_) for p in range(4)}
            X = {p: rhs0[p].get(ch[p].ref, Fr(0)) for p in range(4)}
            rn = (xser[n] - X[1] + X[0]) / 2
            gn = (-xser[n] - X[3] + X[0] - 6 * rn) / 3
            rs_[n], gs_[n] = rn, gn
            for p in range(4):
                ch[p].finish_order(n, rhs0[p], rn, gn)
            E = {p: ch[p].E[n] for p in range(4)}
            assert E[1] - E[0] == xser[n] and E[3] - E[0] == -xser[n]
            C[s].append(E[2] - E[0])
        if n <= 2:
            rs_, gs_ = rg["raw"]
            for key, ch in aux.items():
                rhs0 = ch.rhs_without_new(n, rs_, gs_)
                if n == 1:
                    ch.finish_order(n, rhs0, rs_[n], gs_[n])
                    ch.check_denominators()
                else:  # only E^(2) is needed; psi_2 may contain states degenerate with |z>, z >= 5
                    rhs = dict(rhs0)
                    for opname, c in (("M", rs_[n]), ("V", gs_[n])):
                        if c:
                            for idx, v in ch.matvec(opname, 0, {ch.ref: Fr(1)}).items():
                                rhs[idx] = rhs.get(idx, 0) + c * v
                    ch.E.append(rhs.get(ch.ref, Fr(0)))
            if n == 2:
                for key, ch in aux.items():
                    E2z[key] = ch.E[2]
        if verbose:
            print(f"# order {n}: " + "  ".join(f"{s} C_{n}={float(C[s][n]):.15g}" for s in schemes)
                  + f"  t={time.time() - t0:.1f}s", flush=True)
    ev_ok = all(E2z[(0, l)] == Fr(-(l + 2) * (l + 4), 864) for l in ls)
    return {"L": L, "K": K, "order": ORD,
            "C": {s: [str(c) for c in C[s]] for s in schemes},
            "C_float": {s: [float(c) for c in C[s]] for s in schemes},
            "r": {s: [str(c) for c in rg[s][0]] for s in schemes},
            "g": {s: [str(c) for c in rg[s][1]] for s in schemes},
            "E2z": {f"{z},{l}": str(E2z[(z, l)]) for (z, l) in sorted(E2z)},
            "checks": {"Ev2 == -(l+2)(l+4)/864": ev_ok,
                       "no vanishing first-order denominators in |z> channels, z<=7": True}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--K", type=int, default=8)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = run(a.L, a.K)
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(res, fh, indent=1)
    print(json.dumps(res["C_float"]))
