#!/usr/bin/env python3
"""Assemble r2, g2, C2, r3, g3, C3, r4, g4, C4 (raw) of the 1D LRI HT for every quarter cutoff cut4 = 4 Lambda
<= 4 Lmax at once, from reduced chain shells (c4lib1d).  The RS chain formula is the one of the 2D code
(lri_2d_coeff_expanse/independent_check/c4_exact/c4_compute.py, README sec. 2.1); every tuning quantity is a
linear functional sum_p w_p X_p evaluated with exact per-key weights (functional_from_reduced), the product term
(f) over key pairs, and the final sums over terms with math.fsum.

usage: python3 c4_compute1d.py --Lmax 12 [--out results/x.npz]"""
import argparse
import math
import os
import time
from fractions import Fraction as Fr

import numpy as np

import c4lib1d as lib

g1 = 1.0 / 3.0
PS = lib.PS
WN = ("r", "g", "C")


def fsum_terms(terms):
    """Elementwise exact-rounded sum of a list of equal-length arrays."""
    A = np.array(terms)
    return np.array([math.fsum(A[:, i]) for i in range(A.shape[1])])


class Chain:
    """A chain contribution in reduced form: per prefactor, per-p shells and exact-weight functional shells."""

    def __init__(self, red):
        self.red = red

    def F(self, w, pref="1"):
        return lib.functional_from_reduced(self.red[pref], w)

    def X(self, p, pref="1"):
        return lib.perp_from_reduced(self.red[pref], p)

    def top(self, p, lo, hi, pref="1"):
        """sum of the per-p shells m in (c - hi, c - lo]  for every c: used for windows (no cancellation)."""
        Shp = self.red[pref]["Shp"][p]
        nc = len(Shp) - lib.MOFF
        out = np.zeros(nc)
        for j in range(lo, hi):
            idx = np.arange(nc) + lib.MOFF - j
            ok = idx >= 0
            out[ok] += Shp[idx[ok]]
        return out


def product_functional(recA, recB, w, nc):
    """sum_p w_p a_p(c) b_p(c), a_p(c) = sum_k A_p^k cum_k[c-p] (two-vertex key records), with exact
    sum_p w_p A_p B_p per key pair and the cutoff shift expanded as cum[c-p] = cum[c] - top_p."""
    def prep(rec):
        out = []
        for _, amps, sh in rec:
            cum = np.cumsum(sh)
            C = cum[lib.MOFF: lib.MOFF + nc]
            tops = []
            for p in PS:
                t = np.zeros(nc)
                for j in range(p):
                    t += sh[lib.MOFF - j: lib.MOFF - j + nc]
                tops.append(t)
            out.append((amps, C, tops))
        return out
    a, b = prep(recA), prep(recB)
    terms = []
    for Aa, Ca, ta in a:
        for Bb, Cb, tb in b:
            W = sum(w[p] * Aa[p] * Bb[p] for p in PS)
            if W != 0:
                terms.append(float(W) * Ca * Cb)
            for p in PS:
                c = w[p] * Aa[p] * Bb[p]
                if c == 0:
                    continue
                cf = float(c)
                terms.append(-cf * Ca * tb[p])
                terms.append(-cf * Cb * ta[p])
                terms.append(cf * ta[p] * tb[p])
    return fsum_terms(terms) if terms else np.zeros(nc)


def product_window0(recA, recB, nc):
    """p = 0 window of the product a(c) b(c) - a(c-4) b(c-4) = a(c) [b(c) - b(c-4)] + b(c-4) [a(c) - a(c-4)],
    with the differences taken as top-shell sums (no subtraction of cumulative values)."""
    def parts(rec):
        val = np.zeros(nc)
        win = np.zeros(nc)
        for _, amps, sh in rec:
            if amps[0] == 0:
                continue
            a0 = float(amps[0])
            cum = np.cumsum(sh)
            val += a0 * cum[lib.MOFF: lib.MOFF + nc]
            for j in range(4):
                idx = np.arange(nc) + lib.MOFF - j
                ok = idx >= 0
                win[ok] += a0 * sh[idx[ok]]
        return val, win
    va, wa = parts(recA)
    vb, wb = parts(recB)
    vb_m4 = vb - wb                     # b(c - 4), formed only to multiply the small window of a
    return va * wb + vb_m4 * wa


def product_perp(recA, recB, p, nc):
    def val(rec):
        out = np.zeros(nc)
        for _, amps, sh in rec:
            cum = np.cumsum(sh)
            out += float(amps[p]) * cum[lib.MOFF - p: lib.MOFF - p + nc]
        return out
    return val(recA) * val(recB)


def compute(Lmax, chains=None, verbose=True, stream=True):
    """chains: optional dict name -> reduced dict for the K >= 3 chains (from the production driver)."""
    t0 = time.time()
    ser = lib.Series1D(Lmax)
    nc = 4 * Lmax + 1

    def log(msg):
        if verbose:
            print(f"[{time.time() - t0:8.1f}s] {msg}", flush=True)

    P2 = ("1", "Vpp", "2p", "Vpp2")
    c2 = lambda kinds, d, op: Chain(lib.chain2_reduced(kinds, d, op, Lmax, ser, P2))
    VV_R = c2(["V", "V"], [0, 0], (1, 0))
    VV_R2 = c2(["V", "V"], [0, 0], (2, 0))
    VV_R3 = c2(["V", "V"], [0, 0], (3, 0))
    VV_PR2 = c2(["V", "V"], [0, 0], (2, 1))
    VV_PR3 = c2(["V", "V"], [0, 0], (3, 1))
    VV_P2R3 = c2(["V", "V"], [0, 0], (3, 2))
    MV_R = c2(["M", "V"], [0, 0], (1, 0))
    MM_R = c2(["M", "M"], [0, 0], (1, 0))
    MV_R2 = c2(["M", "V"], [0, 0], (2, 0))
    MV_PR2 = c2(["M", "V"], [0, 0], (2, 1))
    VdV_R = c2(["V", "V"], [1, 0], (1, 0))
    VdV_R2 = c2(["V", "V"], [1, 0], (2, 0))
    VdV_PR2 = c2(["V", "V"], [1, 0], (2, 1))
    VddV_R = c2(["V", "V"], [2, 0], (1, 0))
    VdVd_R = c2(["V", "V"], [1, 1], (1, 0))
    MdV_R = c2(["M", "V"], [1, 0], (1, 0))
    MVd_R = c2(["M", "V"], [0, 1], (1, 0))
    recVV_R = lib.chain2_keys(["V", "V"], [0, 0], (1, 0), Lmax, ser)
    recVV_R2 = lib.chain2_keys(["V", "V"], [0, 0], (2, 0), Lmax, ser)
    log("two-vertex pieces done")

    def ch(name, kinds, ops, dv=None, prefs=("1",), mirror=False):
        if chains is not None:
            if name not in chains or any(f not in chains[name] for f in prefs):
                raise KeyError(f"precomputed chain {name} (prefactors {prefs}) missing")
            return Chain(chains[name])
        return Chain(lib.chain_reduced(kinds, ops, Lmax, ser, dv, prefs, mirror=mirror, stream=stream))

    VVV_RR = ch("VVV_RR", ["V"] * 3, [(1, 0), (1, 0)])
    VVV_R2R = ch("VVV_R2R", ["V"] * 3, [(2, 0), (1, 0)], prefs=("1", "Vpp"))
    VVV_RR2 = ch("VVV_RR2", ["V"] * 3, [(1, 0), (2, 0)], prefs=("1", "Vpp"))
    VVV_PR2R = ch("VVV_PR2R", ["V"] * 3, [(2, 1), (1, 0)])
    VVV_RPR2 = ch("VVV_RPR2", ["V"] * 3, [(1, 0), (2, 1)])
    MVV_RR = ch("MVV_RR", ["M", "V", "V"], [(1, 0), (1, 0)])
    VMV_RR = ch("VMV_RR", ["V", "M", "V"], [(1, 0), (1, 0)])
    dVVV_RR = ch("dVVV_RR", ["V"] * 3, [(1, 0), (1, 0)], dv=0)
    VdVV_RR = ch("VdVV_RR", ["V"] * 3, [(1, 0), (1, 0)], dv=1)
    log("three-vertex pieces done")
    T4 = ch("VVVV_RRR", ["V"] * 4, [(1, 0)] * 3, mirror=True)
    log("four-vertex chain done")

    # ------------------------------------------------------------------ order 2
    def lin(w, terms):
        """terms: list of (coef array or float, Chain, prefactor)."""
        return fsum_terms([np.broadcast_to(np.asarray(c, dtype=float), (nc,)) * ch.F(w, f) for c, ch, f in terms])

    def perp(p, terms):
        return fsum_terms([np.broadcast_to(np.asarray(c, dtype=float), (nc,)) * ch.X(p, f) for c, ch, f in terms])

    T2 = [(g1 ** 2, VV_R, "1")]
    r2, g2, C2 = (lin(w, T2) for w in WN)
    # ------------------------------------------------------------------ order 3
    T3 = [(2 * g1 * r2, MV_R, "1"), (2 * g1 * g2, VV_R, "1"), (2 * g1 * g1, VdV_R, "1"),
          (g1 ** 3, VVV_RR, "1"), (-g1 ** 3, VV_R2, "Vpp"), (-g1 ** 2 / 4.0, VV_PR2, "1")]
    r3, g3, C3 = (lin(w, T3) for w in WN)
    # ------------------------------------------------------------------ order 4 (raw)
    T4t = [
        # (a) 2 g1 [r3 <VRM> + g3 <VRV> + g2 <VRV'> + g1/2 <VRV''> + r2 <VRM'>]
        (2 * g1 * r3, MV_R, "1"), (2 * g1 * g3, VV_R, "1"), (2 * g1 * g2, VdV_R, "1"),
        (g1 * g1, VddV_R, "1"), (2 * g1 * r2, MdV_R, "1"),
        # (b)
        (r2 ** 2, MM_R, "1"), (g2 ** 2, VV_R, "1"), (g1 ** 2, VdVd_R, "1"), (2 * r2 * g2, MV_R, "1"),
        (2 * r2 * g1, MVd_R, "1"), (2 * g2 * g1, VdV_R, "1"),
        # (c)
        (2 * g1 * r2 * g1, MVV_RR, "1"), (-2 * g1 * r2 * g1, MV_R2, "Vpp"), (-2 * g1 * r2 * 0.25, MV_PR2, "1"),
        (2 * g1 * g2 * g1, VVV_RR, "1"), (-2 * g1 * g2 * g1, VV_R2, "Vpp"), (-2 * g1 * g2 * 0.25, VV_PR2, "1"),
        (2 * g1 * g1 * g1, dVVV_RR, "1"), (-2 * g1 * g1 * g1, VdV_R2, "Vpp"), (-2 * g1 * g1 * 0.25, VdV_PR2, "1"),
        # (d)
        (g1 ** 2 * r2, VMV_RR, "1"), (-g1 ** 2 * r2, VV_R2, "2p"), (g1 ** 2 * g2, VVV_RR, "1"),
        (-g1 ** 2 * g2, VV_R2, "Vpp"), (g1 ** 3, VdVV_RR, "1"),
        # (e)
        (g1 ** 4, T4, "1"), (-g1 ** 4, VVV_R2R, "Vpp"), (-g1 ** 4, VVV_RR2, "Vpp"), (g1 ** 4, VV_R3, "Vpp2"),
        (-g1 ** 3 / 4.0, VVV_PR2R, "1"), (-g1 ** 3 / 4.0, VVV_RPR2, "1"), (2 * g1 ** 3 / 4.0, VV_PR3, "Vpp"),
        (g1 ** 2 / 16.0, VV_P2R3, "1"),
    ]
    out = {}
    for w in WN:
        f = -g1 ** 4 * product_functional(recVV_R, recVV_R2, lib.FUNCTIONALS[w], nc)
        out[w] = fsum_terms([lin(w, T4t), f])
    r4, g4, C4 = out["r"], out["g"], out["C"]
    # per-p values (not cancellation-free; diagnostics and the vacuum window)
    X = {}
    for k, T in ((2, T2), (3, T3)):
        X[k] = np.array([perp(p, T) for p in PS])
    X[4] = np.array([fsum_terms([perp(p, T4t), -g1 ** 4 * product_perp(recVV_R, recVV_R2, p, nc)]) for p in PS])
    # vacuum (p = 0) window of the eps^4 energy: E0^(4)(c) - E0^(4)(c - 4) from shells (no cancellation);
    # the product term (f) is a product of two P = 4 single-slice chains and has no shells at even Lambda in the
    # window; it is included exactly via per-p values difference only as a check below.
    vac_win4 = fsum_terms([np.broadcast_to(np.asarray(c, dtype=float), (nc,)) * ch.top(0, 0, 4, f)
                           for c, ch, f in T4t])
    fwin = -g1 ** 4 * product_window0(recVV_R, recVV_R2, nc)
    log("assembled")
    cut4 = np.arange(nc)
    return dict(cut4=cut4, Lam=cut4 / 4.0, r2=r2, g2=g2, C2=C2, r3=r3, g3=g3, C3=C3, r4=r4, g4=g4, C4=C4,
                X2=X[2], X3=X[3], X4=X[4], vac_win4_chains=vac_win4, vac_win4_f=fwin)


def masked(res):
    """Export view with the validity mask of PLAN A7(i): tuned quantities only for cut4 >= 3 (all references
    |p>, p <= 3, exist), per-p X_p only for cut4 >= p.  Rows outside are NaN; a boolean 'valid' is added."""
    out = dict(res)
    valid = res["cut4"] >= 3
    for k in ("r2", "g2", "C2", "r3", "g3", "C3", "r4", "g4", "C4", "vac_win4_chains", "vac_win4_f"):
        out[k] = np.where(valid, res[k], np.nan)
    for k in ("X2", "X3", "X4"):
        X = np.array(res[k], dtype=float)
        for p in PS:
            X[p, res["cut4"] < p] = np.nan
        out[k] = X
    out["valid"] = valid
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, default=12)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = compute(a.Lmax)
    for L in range(2, a.Lmax + 1, 2):
        c = 4 * L
        print(f"L={L:5d} C2={res['C2'][c]:.15f} C3={res['C3'][c]:.15f} C4={res['C4'][c]:.13f}")
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        np.savez(a.out, **masked(res))


if __name__ == "__main__":
    main()
