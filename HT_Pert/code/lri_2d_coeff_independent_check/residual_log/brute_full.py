#!/usr/bin/env python3
"""End-to-end brute-force exact (Fraction) check of the complete second-order window scheme at small L.

Full Rayleigh-Schroedinger in the truncated Fock space (../rs_exact/ref_fraction.py, imported READ-ONLY) with
    H_L = P_L (H0 + r M + g V) P_L + eps^2 D,   D = D_zm + D_chi,
  * D_zm (full zero-mode window, ket-referenced second-order Bloch operator, all z -> z'):
        D_zm (a^dag)^z |chi> = sum_{z'} [ h_{z'z}(L) - h_{z'z}(L - N_chi) ] (a^dag)^{z'} |chi>     (N_chi >= 2),
    h_{z'z}(l) = monomial-basis coefficient of (a^dag)^{z'}|0> in W_1 R_z W_1 (a^dag)^z|0> at cutoff l, from auxiliary
    RS channels |z>, l = 0..L (R_z = Q/(E_z^0 - H0): ket-referenced).  Its z' = z part is the 'zeromode/corrected'
    window of ../c4_exact; it contains the vacuum (consistent) window.
  * D_chi = -(g1^2/(3 pi)) {N, M'}  (as brute_nm.py).
Schemes reported: raw, corrected (z' = z only), full_zm (all z'), full_zm + chi.  Compare with
    C4corr (../c4_exact), C4corr + off (offdiag_window.py), C4corr + off + dC4chi (nm_window.py).
usage: python3 brute_full.py --L 4"""
import argparse
import json
import math
import os
import sys
import time
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("RS_EXACT_DIR", os.path.join(HERE, "..", "rs_exact")))
import ref_fraction as rf  # noqa: E402
import brute_nm as bn  # noqa: E402

ORD = 4
rf.ORD = ORD
bn.rf.ORD = ORD
ZMAX = 7


class GChannel(rf.Channel):
    """Channel with a general order-eps^2 operator D given as a function vec -> vec."""

    def __init__(self, *a, Dapply=None, **kw):
        super().__init__(*a, **kw)
        self.Dapply = Dapply

    def rhs_without_new(self, n, r, g):
        out = super().rhs_without_new(n, r, g)
        if n >= 2 and self.Dapply is not None:
            for row, v in self.Dapply(self.psi[n - 2]).items():
                if self.allowed[row]:
                    out[row] = out.get(row, 0) + v
        return out


def run(L, K=8, verbose=True):
    t0 = time.time()
    spaces, ops, Mp = {}, {}, {}
    for par in (0, 1):
        sp = rf.Space(L, par, (6 if par == 0 else 7) + K)
        ctup = rf.ordered_creation_tuples(sp, 4)
        ops[par] = {"M": rf.build_vertex(sp, 2, Fr(1), ctup), "V": rf.build_vertex(sp, 4, Fr(1, 12), ctup)}
        Mp[par] = bn.build_Mprime(sp, ctup)
        spaces[par] = sp
        if verbose:
            print(f"# L={L} parity={par}: {len(sp.states)} states t={time.time() - t0:.1f}s", flush=True)
    ls = list(range(0, L + 1, 2))
    zero = lambda k, N: 0
    g1 = Fr(1, 3)
    r_ = [Fr(0), Fr(0)] + [Fr(0)] * (ORD - 1)
    gg = [Fr(0), g1] + [Fr(0)] * (ORD - 1)
    # auxiliary channels: psi_1 and the order-2 rhs (W1 psi_1 - E1 psi_1) restricted to pure zero-mode monomials
    h = {}
    for z in range(ZMAX + 1):
        sp = spaces[z % 2]
        for l in ls:
            ch = rf.Channel(f"z{z}l{l}", sp, ops[z % 2], z, l, K, zero)
            rhs1 = ch.rhs_without_new(1, r_, gg)
            ch.finish_order(1, rhs1, Fr(0), g1)
            rhs2 = ch.rhs_without_new(2, r_, gg)      # r2 = g2 = 0 here: l-independent anyway
            for zp in range(ZMAX + 1):
                if zp % 2 != z % 2:
                    continue
                idx = sp.ref_index(zp)
                h[(zp, z, l)] = rhs2.get(idx, Fr(0))
    if verbose:
        print(f"# aux channels done t={time.time() - t0:.1f}s", flush=True)

    def make_Dzm(par, offdiag):
        sp = spaces[par]

        def apply(vec):
            out = {}
            for c, v in vec.items():
                N = sp.level[c]
                if N == 0:
                    continue
                st = dict(sp.states[c])
                z = st.get(0, 0)
                if z > ZMAX:
                    continue
                for zp in range(z % 2, ZMAX + 1, 2):
                    if not offdiag and zp != z:
                        continue
                    d = h[(zp, z, L)] - h[(zp, z, L - N)]
                    if d == 0:
                        continue
                    st2 = dict(st)
                    if zp:
                        st2[0] = zp
                    else:
                        st2.pop(0, None)
                    j = sp.index.get(tuple(sorted(st2.items())))
                    if j is None:
                        continue
                    out[j] = out.get(j, 0) + d * v
            return out
        return apply

    kappa = Fr(-1, 27) / Fr(1)   # times 1/pi applied in float at the end: D_chi = kappa/pi {N, M'}

    def make_Dchi(par, kap):
        sp = spaces[par]
        cols = Mp[par]

        def apply(vec):
            out = {}
            for c, v in vec.items():
                for (row, val) in cols[c]:
                    out[row] = out.get(row, 0) + kap * (sp.level[row] + sp.level[c]) * val * v
            return out
        return apply

    def combine(*fs):
        def apply(vec):
            out = {}
            for f in fs:
                for k_, v in f(vec).items():
                    out[k_] = out.get(k_, 0) + v
            return out
        return apply

    schemes = {
        "raw": lambda par: None,
        "corrected": lambda par: make_Dzm(par, False),
        "full_zm": lambda par: make_Dzm(par, True),
        "chi_unit": lambda par: make_Dchi(par, Fr(1)),     # {N, M'} with unit coefficient, alone
    }
    res = {}
    for name, mk in schemes.items():
        ch = {p: GChannel(f"{name}p{p}", spaces[p % 2], ops[p % 2], p, L, K, zero, Dapply=mk(p % 2))
              for p in range(4)}
        r = [Fr(0)] * (ORD + 1)
        g = [Fr(0)] * (ORD + 1)
        xser = [Fr(1, 2), Fr(-1, 4)] + [Fr(0)] * (ORD - 1)
        C = [Fr(1)]
        for n in range(1, ORD + 1):
            rhs0 = {p: ch[p].rhs_without_new(n, r, g) for p in range(4)}
            X = {p: rhs0[p].get(ch[p].ref, Fr(0)) for p in range(4)}
            r[n] = (xser[n] - X[1] + X[0]) / 2
            g[n] = (-xser[n] - X[3] + X[0] - 6 * r[n]) / 3
            for p in range(4):
                ch[p].finish_order(n, rhs0[p], r[n], g[n])
            C.append(ch[2].E[n] - ch[0].E[n])
        res[name] = C
        if verbose:
            print(f"# {name}: C4 = {float(C[4]):.15f}  t={time.time() - t0:.1f}s", flush=True)
    kap = -1.0 / (27.0 * math.pi)
    C4 = {k: float(v[4]) for k, v in res.items()}
    out = {"L": L, "C4_raw": C4["raw"], "C4_corrected": C4["corrected"], "C4_full_zm": C4["full_zm"],
           "dC4_chi_per_unit": float(res["chi_unit"][4] - res["raw"][4]),
           "C4_W": C4["full_zm"] + kap * float(res["chi_unit"][4] - res["raw"][4]),
           "exact": {k: [str(x) for x in v] for k, v in res.items()}}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = run(a.L)
    print(json.dumps({k: v for k, v in res.items() if k != "exact"}))
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(res, fh, indent=1)
