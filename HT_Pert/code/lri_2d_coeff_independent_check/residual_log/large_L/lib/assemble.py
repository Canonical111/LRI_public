#!/usr/bin/env python3
"""Assemble C_2..C_nmax of the RAW scheme for every even L <= Lmax from the symbolic RS words (rs.py) evaluated by
chains.py.  Window schemes add their D-words on top (windows5.py).

Tuning at order n (x_n = 0 for n >= 2): E_p^(n) = X_p^(n) + 2p r_n + C(p,2) g_n with
    r_n = -(X_1 - X_0)/2,  g_n = -(X_3 - X_0 + 6 r_n)/3,  C_n = Pi[X^(n)] = X_2 - X_1 - (X_3 - X_0)/3.
Pruning (prune=True): order-nmax words with p-independent coefficients keep only line patterns with >= 6 zero-mode legs
(polynomial degree >= 3 in p; Pi kills the rest), which leaves C_nmax exact but r_nmax, g_nmax, E^(nmax) incomplete.
usage: python3 assemble.py --Lmax 18 --nmax 5 [--prune] [--out x.npz]"""
import argparse
import os
import time
from fractions import Fraction as Fr

import numpy as np

import engine as eg
import chains as ch
import rs

P = (0, 1, 2, 3)
G1 = 1.0 / 3.0


def Pi(f):
    return f[2] - f[1] - (f[3] - f[0]) / 3.0


def collect_words(nmax, windows=False):
    """words[n] = dict vertex-seq -> list of (coef Fr, symbols, slice_ops); single-vertex words dropped (they only carry
    the tuning terms r_n M_0, g_n V_0; V_j, M_j with j >= 1 are zero on |p>)."""
    E = rs.unroll(nmax, windows)
    words = {}
    for n in range(2, nmax + 1):
        d = {}
        for (c, sy, ops, pw) in E[n]:
            r = rs.reduce_word(ops, pw)
            if r is None:
                continue
            verts, sops = r
            if len(verts) == 1:
                continue
            d.setdefault(verts, []).append((c, sy, sops))
        words[n] = d
    return words


def evaluate_words(words, nmax, N, modes, prune=False, verbose=True, runner=None):
    """vals[(n, verts, idx)] = {p: array}.  runner(kinds, derivs, wordlist, kw) -> list of {p: array} (default serial)."""
    vals = {}
    t0 = time.time()
    for n in range(2, nmax + 1):
        for verts, lst in words[n].items():
            if any(v[0] == "D" for v in verts):
                continue                                  # window words handled elsewhere
            kinds = [v[0] for v in verts]
            derivs = [v[1] for v in verts]
            # unique slice-op sets
            uniq = sorted(set(sops for (_, _, sops) in lst))
            kw = {}
            if prune and n == nmax and all(not any(s.startswith("E") for s in sy) for (_, sy, _) in lst):
                kw["min_zero_legs"] = 6
            wl = [(s, None) for s in uniq]
            res = runner(kinds, derivs, wl, kw) if runner else ch.eval_group(kinds, derivs, wl, N, modes, P, **kw)
            for s, r in zip(uniq, res):
                vals[(n, verts, s)] = r
            if verbose:
                print(f"[{time.time() - t0:8.1f}s] n={n} {''.join(f'{k}{d}' for k, d in zip(kinds, derivs))} "
                      f"{len(uniq)} slice-op sets {kw}", flush=True)
    return vals


def assemble(words, vals, nmax, N, extra=None):
    """extra[n] = {p: array} added to X^(n) (window contributions).  Returns dict with C, r, g, E arrays."""
    sym = {}
    E = {1: {p: np.full(N + 1, G1 * p * (p - 1) / 2.0) for p in P}}
    r = {1: np.zeros(N + 1)}
    g = {1: np.full(N + 1, G1)}
    C = {}
    X = {}
    for n in range(2, nmax + 1):
        Xn = {p: np.zeros(N + 1) for p in P}
        for verts, lst in words[n].items():
            if any(v[0] == "D" for v in verts):
                continue
            for (c, sy, sops) in lst:
                val = vals[(n, verts, sops)]
                for p in P:
                    coef = np.full(N + 1, float(c))
                    for s in sy:
                        if s.startswith("E"):
                            coef = coef * E[int(s[1:])][p]
                        elif s.startswith("r"):
                            coef = coef * r[int(s[1:])]
                        elif s.startswith("g"):
                            coef = coef * g[int(s[1:])]
                        else:
                            raise ValueError(s)
                    Xn[p] = Xn[p] + coef * val[p]
        if extra and n in extra:
            for p in P:
                Xn[p] = Xn[p] + extra[n][p]
        X[n] = Xn
        r[n] = -(Xn[1] - Xn[0]) / 2.0
        g[n] = -(Xn[3] - Xn[0] + 6.0 * r[n]) / 3.0
        E[n] = {p: Xn[p] + 2 * p * r[n] + p * (p - 1) / 2.0 * g[n] for p in P}
        C[n] = Pi(Xn)
    return dict(C=C, r=r, g=g, E=E, X=X)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, default=18)
    ap.add_argument("--nmax", type=int, default=5)
    ap.add_argument("--prune", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    N = a.Lmax // 2
    modes = eg.Modes(N, 3)
    words = collect_words(a.nmax)
    vals = evaluate_words(words, a.nmax, N, modes, prune=a.prune)
    res = assemble(words, vals, a.nmax, N)
    for i in range(N + 1):
        print(f"L={2*i:4d} " + " ".join(f"C{n}={res['C'][n][i]:+.13f}" for n in range(2, a.nmax + 1)))
    if a.out:
        out = {"L": 2 * np.arange(N + 1)}
        for n in range(2, a.nmax + 1):
            out[f"C{n}"] = res["C"][n]
            out[f"r{n}"] = res["r"][n]
            out[f"g{n}"] = res["g"][n]
            for p in P:
                out[f"E{n}_p{p}"] = res["E"][n][p]
        np.savez(a.out, **out)


if __name__ == "__main__":
    main()
