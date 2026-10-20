#!/usr/bin/env python3
"""Scheme differences DC_n = C_n(scheme) - C_n(raw), n <= 5, to large L without the 5- and raw 4-vertex chains.

X_n(scheme) - X_n(raw) = sum_{raw words} [coef_scheme - coef_raw] val + (window words of the scheme).  At order <= 5 a
raw word's coefficient contains at most one scheme-dependent symbol (r3, g3, E3, r4, g4), so the difference is linear:
Dcoef = (D symbol) x (rest, raw values).  Raw words carrying such symbols have <= 3 vertices; window words <= 4 outer
vertices.  Raw r2, g2, r3, g3, E2, E3 come from the <= 3-vertex raw words (cheap).
usage: python3 delta5.py --Lmax 1000 --workers 60 --cache dcache_L1000 --out results/dC5_L1000.npz"""
import argparse
import hashlib
import os
import pickle
import time

import numpy as np

import engine as eg
import assemble as asm
import prod5 as pr

P = (0, 1, 2, 3)
G1 = 1.0 / 3.0
SDEP = ("r3", "g3", "E3", "r4", "g4")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--schemes", default=",".join(pr.SCHEMES))
    ap.add_argument("--chunk", type=int, default=20)
    a = ap.parse_args()
    N = a.Lmax // 2
    t0 = time.time()
    schemes = a.schemes.split(",")
    words, dec_words, seqs = pr.catalogue(5, prune=True)
    modes = eg.Modes(N, 3)
    inn = pr.inner(N, modes, bloch_too=("Wb" in schemes or "Wc" in schemes))
    pr.C12[0] = inn["c1_2"]
    os.makedirs(a.cache, exist_ok=True)
    # per-process file, written atomically (concurrent shard jobs share the cache directory)
    inn_path = os.path.join(a.cache or ".", f"inner_L{a.Lmax}_{os.uname().nodename}_{os.getpid()}.pkl")
    with open(inn_path + ".tmp", "wb") as fh:
        pickle.dump(inn, fh)
    os.replace(inn_path + ".tmp", inn_path)
    print(f"[{time.time() - t0:8.1f}s] inner functions", flush=True)
    # raw words needed: orders 2, 3 (all: raw couplings) and orders 4, 5 with a scheme-dependent symbol
    need = set()
    for n in range(2, 6):
        for verts, lst in words[n].items():
            for (c, sy, sops) in lst:
                if n <= 3 or any(s in SDEP for s in sy):
                    need.add((n, verts, sops))
    tasks = []
    for key, d in seqs.items():
        kinds, derivs = key
        K = len(kinds)
        raws = [x for x in d["raw"] if (x[0], x[1], x[2]) in need]
        if raws:
            minz = min(x[3] for x in raws)
            pats = eg.patterns(list(kinds), None, minz)
            for i in range(0, len(pats), a.chunk):
                pp = pats[i: i + a.chunk]
                h = hashlib.sha1(repr(("rawd", key, [sorted(x.items()) for x in pp], a.Lmax,
                                       sorted(set((x[0], x[2]) for x in raws)))).encode()).hexdigest()[:16]
                tasks.append((len(pp) * (N + 1) ** max(1, K - 1),
                              ("raw", None, key, raws, pp, os.path.join(a.cache, f"raw_{h}.pkl"))))
        for scheme in schemes:
            items = [(nord, idx, verts, slices, windows, minz) for (sch, nord, idx, verts, slices, windows, minz)
                     in d["dec"] if sch == scheme]
            if not items:
                continue
            minz = min(x[5] for x in items)
            pats = eg.patterns(list(kinds), None, minz)
            for i in range(0, len(pats), a.chunk):
                pp = pats[i: i + a.chunk]
                h = hashlib.sha1(repr(("dec", scheme, key, a.Lmax, [sorted(x.items()) for x in pp],
                                       [(x[0], x[1]) for x in items])).encode()).hexdigest()[:16]
                tasks.append((len(pp) * (N + 1) ** max(1, K - 1),
                              ("dec", scheme, key, items, pp, os.path.join(a.cache, f"dec_{scheme}_{h}.pkl"))))
    tasks.sort(key=lambda t: -t[0])
    tasks = [t[1] for t in tasks]
    print(f"# Lmax={a.Lmax} tasks={len(tasks)} workers={a.workers}", flush=True)
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor, as_completed
    raw_vals, dec_vals = {}, {}
    done = 0
    with ProcessPoolExecutor(a.workers, mp_context=mp.get_context(os.environ.get("MP_START", "spawn")), initializer=pr._init,
                             initargs=(N, inn_path)) as pool:
        futs = [pool.submit(pr._task, t) for t in tasks]
        for fut in as_completed(futs):
            kind, scheme, out, dt, cached = fut.result()
            target = raw_vals if kind == "raw" else dec_vals
            for k, v in out.items():
                if kind == "raw":
                    acc = target.setdefault(k, {p: np.zeros(N + 1) for p in P})
                    for p in P:
                        acc[p] += v[p]
                else:
                    acc = target.setdefault(k, {})
                    for kap, dd in v.items():
                        aa = acc.setdefault(kap, {p: np.zeros(N + 1) for p in P})
                        for p in P:
                            aa[p] += dd[p]
            done += 1
            if dt > 120 or done % 200 == 0 or done == len(tasks):
                print(f"[{time.time() - t0:8.1f}s] {done}/{len(tasks)} {kind} {scheme or ''} dt={dt:.1f}s", flush=True)
    res = assemble_delta(words, dec_words, raw_vals, dec_vals, N, schemes, inn["c1_2"])
    save = {"L": 2 * np.arange(N + 1)}
    for scheme, d in res.items():
        for k, v in d.items():
            save[f"{scheme}_{k}"] = v
    np.savez(a.out, **save)
    print(f"# done in {time.time() - t0:.1f}s -> {a.out}", flush=True)
    for L in (10, 50, 100, 200, 400, 600, 1000, 2000):
        if L <= a.Lmax:
            i = L // 2
            print(f"L={L:5d} " + " ".join(f"{s}:dC5={res[s]['dC5'][i]:+.8f}" for s in schemes), flush=True)


def assemble_delta(words, dec_words, raw_vals, dec_vals, N, schemes, c12=None):
    """raw couplings through order 3 (and E2, E3) from the raw values; deltas order by order (linear)."""
    base = {"r": {1: np.zeros(N + 1)}, "g": {1: np.full(N + 1, G1)}}
    E = {1: {p: np.full(N + 1, G1 * p * (p - 1) / 2.0) for p in P}}
    for n in (2, 3):
        Xn = {p: np.zeros(N + 1) for p in P}
        for verts, lst in words[n].items():
            for (c, sy, sops) in lst:
                val = raw_vals[(n, verts, sops)]
                for p in P:
                    coef = np.full(N + 1, float(c))
                    for s in sy:
                        coef = coef * (E[int(s[1:])][p] if s[0] == "E" else base[s[0]][int(s[1:])])
                    Xn[p] = Xn[p] + coef * val[p]
        base["r"][n] = -(Xn[1] - Xn[0]) / 2.0
        base["g"][n] = -(Xn[3] - Xn[0] + 6.0 * base["r"][n]) / 3.0
        E[n] = {p: Xn[p] + 2 * p * base["r"][n] + p * (p - 1) / 2.0 * base["g"][n] for p in P}
    out = {}
    for scheme in schemes:
        dr, dg, dE = {}, {}, {}
        res = {}

        def sval(s, p):
            """scheme value of a symbol whose raw value is known (orders <= 3)."""
            if s == "C12":
                return c12
            o = int(s[1:])
            if s[0] == "E":
                return E[o][p] + dE.get(o, {p: 0})[p]
            if s[0] == "r":
                return base["r"][o] + dr.get(o, 0)
            return base["g"][o] + dg.get(o, 0)

        for n in (3, 4, 5):
            dX = {p: np.zeros(N + 1) for p in P}
            if n >= 4:
                for verts, lst in words[n].items():
                    for (c, sy, sops) in lst:
                        dsym = [s for s in sy if s in SDEP]
                        if not dsym:
                            continue
                        assert len(dsym) == 1
                        s0 = dsym[0]
                        val = raw_vals[(n, verts, sops)]
                        for p in P:
                            o = int(s0[1:])
                            dv = dE[o][p] if s0[0] == "E" else (dr[o] if s0[0] == "r" else dg[o])
                            coef = np.full(N + 1, float(c)) * dv
                            for s in sy:
                                if s == s0:
                                    continue
                                coef = coef * (E[int(s[1:])][p] if s[0] == "E" else base[s[0]][int(s[1:])])
                            dX[p] = dX[p] + coef * val[p]
            for idx, (c, sy, _) in enumerate(dec_words[scheme].get(n, [])):
                for kap, d in dec_vals.get((scheme, n, idx), {}).items():
                    for p in P:
                        coef = np.full(N + 1, float(c))
                        for s in tuple(sy) + tuple(kap):
                            coef = coef * sval(s, p)
                        dX[p] = dX[p] + coef * d[p]
            dr[n] = -(dX[1] - dX[0]) / 2.0
            dg[n] = -(dX[3] - dX[0] + 6.0 * dr[n]) / 3.0
            dE[n] = {p: dX[p] + 2 * p * dr[n] + p * (p - 1) / 2.0 * dg[n] for p in P}
            res[f"dC{n}"] = asm.Pi(dX)
            res[f"dr{n}"] = dr[n]
            res[f"dg{n}"] = dg[n]
        out[scheme] = res
    return out


if __name__ == "__main__":
    main()
