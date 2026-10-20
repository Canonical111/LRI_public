#!/usr/bin/env python3
"""Generic assembly of r_n, g_n, C_n (n = 2..nmax) of the 1D LRI HT on the quarter grid cut4 = 0..4 Lmax
(PLAN.md sec. 3.5), driven by the rs5 catalogue (words5.terms).

For every term: coupling monomial (float arrays, order by order) x functional of its chain with its prefactor
vector (exact per-key weights, lib5.keys.functional), or for products the exact key-pair functional
(lib5.keys.product_functional); sums with math.fsum per grid point.  r_n = F_r[X^(n)], g_n = F_g[X^(n)],
C_n = F_Pi[X^(n)].  Per-p X_p (not cancellation-free; diagnostics and A3) and the p = 0 vacuum windows of
orders 4 and 5 (cancellation-free top shells; windows A (c-2, c] and B (c-4, c]) are produced too.

usage: python3 assemble5.py --Lmax 12 [--nmax 5] [--reference] [--out x.npz]"""
import argparse
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import words5                                    # noqa: E402
from lib5 import keys as K5                      # noqa: E402
from lib5.common import FUNCTIONALS, PS          # noqa: E402
from lib5.series import Series5                  # noqa: E402

WN = ("r", "g", "C")


def fsum_cols(terms, nc):
    if not terms:
        return np.zeros(nc)
    A = np.array(terms)
    return np.array([math.fsum(A[:, i]) for i in range(nc)])


def is_task_chain(ch, d):
    """Chains evaluated by production tasks (run5.py): K >= 4, and K = 3 without key records.  K = 2 chains and
    chains needed as product factors (key records) are evaluated in the assembly."""
    K = len(ch[0])
    return K >= 4 or (K == 3 and not d["records"])


def evaluate_chains(plan, Lmax, ser, chains=None, block=32, reference=False, verbose=False):
    """{chain: (reduced dict f -> {Shp, Shw}, records or None)}.  With `chains` (production), every task chain
    (is_task_chain) must be present there; everything else is evaluated serially here."""
    out = {}
    t0 = time.time()
    for ch, d in plan.items():
        verts, sops = ch
        prefs = {f: f for f in d["prefs"]} or {}
        if chains is not None and is_task_chain(ch, d):
            if ch not in chains:
                raise KeyError(f"precomputed chain missing: {ch}")
            red = chains[ch]
            for f in prefs:
                if f not in red:
                    raise KeyError(f"prefactor {f} missing for chain {ch}")
            if d["records"]:
                raise ValueError(f"records requested for an external chain {ch}")
            out[ch] = (red, None)
            continue
        red, recs = K5.eval_chain(verts, sops, Lmax, ser, prefs, keep_records=d["records"], block=block,
                                  reference=reference)
        out[ch] = (red, recs)
        if verbose:
            print(f"[{time.time() - t0:8.1f}s] chain K={len(verts)} {verts} {sops}", flush=True)
    return out


def compute(Lmax, nmax=5, chains=None, verbose=True, block=32, reference=False):
    t0 = time.time()
    nc = 4 * Lmax + 1
    ser = Series5(Lmax)
    T = words5.terms(nmax)
    plan = words5.chain_plan(nmax)
    vals = evaluate_chains(plan, Lmax, ser, chains=chains, block=block, reference=reference, verbose=verbose)

    def log(msg):
        if verbose:
            print(f"[{time.time() - t0:8.1f}s] {msg}", flush=True)

    log("chains evaluated")
    coup = {}
    res = {"cut4": np.arange(nc)}
    for n in range(2, nmax + 1):
        acc = {wn: [] for wn in WN}
        accp = {p: [] for p in PS}
        winA, winB, odd = [], [], []
        for t in T[n]:
            cf = np.full(nc, float(t["coef"]))
            for s in t["cpl"]:
                cf = cf * coup[s]
            redA, recsA = vals[t["A"]]
            if t["B"] is None:
                red = redA[t["f"]]
                for wn in WN:
                    acc[wn].append(cf * K5.functional(red, wn))
                for p in PS:
                    accp[p].append(cf * K5.perp(red, p))
                winA.append(cf * K5.top(red, 0, 0, 2))
                winB.append(cf * K5.top(red, 0, 0, 4))
                odd.append(cf * (K5.top(red, 0, 1, 2) + K5.top(red, 0, 3, 4)))     # shells m = c-1 and c-3
            else:
                recsB = vals[t["B"]][1]
                for wn, w in FUNCTIONALS.items():
                    acc[wn].append(cf * K5.product_functional(recsA, recsB, w, t["f"], nc))
                for p in PS:
                    e = tuple(1 if q == p else 0 for q in PS)
                    accp[p].append(cf * K5.product_functional(recsA, recsB, e, t["f"], nc))
                if t["f"][0] != 0:
                    f0 = float(t["f"][0])
                    w = {k: K5.product_window0(recsA, recsB, k, nc) for k in (1, 2, 3, 4)}
                    winA.append(cf * f0 * w[2])
                    winB.append(cf * f0 * w[4])
                    odd.append(cf * f0 * ((w[2] - w[1]) + (w[4] - w[3])))
        F = {wn: fsum_cols(acc[wn], nc) for wn in WN}
        coup[f"r{n}"], coup[f"g{n}"] = F["r"], F["g"]
        res[f"r{n}"], res[f"g{n}"], res[f"C{n}"] = F["r"], F["g"], F["C"]
        res[f"X{n}"] = np.array([fsum_cols(accp[p], nc) for p in PS])
        res[f"vacwinA{n}"] = fsum_cols(winA, nc)
        res[f"vacwinB{n}"] = fsum_cols(winB, nc)
        res[f"vacodd{n}"] = fsum_cols(odd, nc)
        log(f"order {n} assembled ({len(T[n])} terms)")
    res["catalogue_sha256"] = np.array(words5.catalogue_hash(nmax))
    return res


def masked(res, nmax=5):
    """Export view: tuned quantities only for cut4 >= 3, per-p X_p only for cut4 >= p (PLAN A7(b))."""
    out = dict(res)
    valid = res["cut4"] >= 3
    for n in range(2, nmax + 1):
        for k in ("r", "g", "C"):
            out[f"{k}{n}"] = np.where(valid, res[f"{k}{n}"], np.nan)
        X = np.array(res[f"X{n}"], dtype=float)
        for p in PS:
            X[p, res["cut4"] < p] = np.nan
        out[f"X{n}"] = X
        for k in ("vacwinA", "vacwinB", "vacodd"):
            out[f"{k}{n}"] = np.where(valid, res[f"{k}{n}"], np.nan)
    out["valid"] = valid
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, default=12)
    ap.add_argument("--nmax", type=int, default=5)
    ap.add_argument("--reference", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = compute(a.Lmax, a.nmax, reference=a.reference)
    for L in range(2, a.Lmax + 1, 2):
        c = 4 * L
        print(f"L={L:4d} " + " ".join(f"C{n}={res[f'C{n}'][c]:.13g}" for n in range(2, a.nmax + 1)))
    if a.out:
        np.savez(a.out, **masked(res, a.nmax))


if __name__ == "__main__":
    main()
