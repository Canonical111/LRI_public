#!/usr/bin/env python3
"""Production driver: C_2..C_5 for every even L <= Lmax in the schemes raw, consistent, zeromode and the W variants
(W2, W3m, W3e) from ONE pass over the line patterns.  For each vertex sequence (kinds, eps orders) every line pattern
is a task: its density is computed once and contracted with every raw word and every decorated window word that
uses the sequence.  Tasks run in a process pool with per-task checkpoint files (resumable).

Phase 1 (parent): window l-functions (inner functions; cheap: <= 3-vertex chains at all cutoffs).
Phase 2 (pool) : pattern tasks -> per-word values {p: array over M} (decorated words: per coupling monomial).
Phase 3 (parent): assembly order by order for every scheme.
usage: python3 prod5.py --Lmax 200 --workers 16 --cache cache_L200 --out results/c5_L200.npz [--chunk 4]"""
import argparse
import hashlib
import os
import pickle
import sys
import time

import numpy as np

import engine as eg
import chains as ch
import rs
import assemble as asm
import windows5 as w5
import windowsW as ww
import schemeW as sw

P = (0, 1, 2, 3)
G1 = 1.0 / 3.0
SCHEMES = ["consistent", "zeromode", "W2", "W3m", "W3e", "Wb", "W3x", "consistent2", "zeromode2", "Z2", "Zb", "Wc"]
DIAG_KMAX = {"consistent": 3, "zeromode": 3, "consistent2": 2, "zeromode2": 2}


# --------------------------------------------------------------------------------------------- word catalogue
def catalogue(nmax, prune=True):
    """Returns (raw_words, seqs) with seqs[(kinds, derivs)] = dict:
       'raw': list of (n, verts, sops, kw) unique raw word evaluations
       'dec': list of (scheme, n, idx, verts, slices, windows) decorated window words (verts as (kind, deriv, minchi))."""
    words = asm.collect_words(nmax)
    seqs = {}

    def add(key, kind, item):
        seqs.setdefault(key, {"raw": [], "dec": []})[kind].append(item)

    for n in range(2, nmax + 1):
        for verts, lst in words[n].items():
            kinds = tuple(v[0] for v in verts)
            derivs = tuple(v[1] for v in verts)
            uniq = sorted(set(s for (_, _, s) in lst))
            minz = 6 if (prune and n == nmax and all(not any(s.startswith("E") for s in sy) for (_, sy, _) in lst)) \
                else 0
            for s in uniq:
                add((kinds, derivs), "raw", (n, verts, s, minz))
    # window words of the diagonal schemes as decorated words: D_k -> ('DZ', k) with diagonal window functions
    dec_words = {}
    E = rs.unroll(nmax, windows=True)
    for scheme, kmx in DIAG_KMAX.items():
        lst_n = {}
        for n in range(4, nmax + 1):
            lst = []
            for (c, sy, ops, pw) in E[n]:
                if not any(a[0] == "D" for a in ops):
                    continue
                ops2 = tuple(("DZ", a[1]) if a[0] == "D" else a for a in ops)
                if any(a[0] == "DZ" and a[1] > kmx for a in ops2):
                    continue
                for var in ww.decorate(ops2, pw):
                    lst.append((c, sy, var))
            lst_n[n] = lst
        dec_words[scheme] = lst_n
    for var in ["W2", "W3m", "W3e", "Wb", "W3x", "Z2", "Zb", "Wc"]:
        dec_words[var] = sw.word_list(nmax, sw.COMPONENTS[var])
    for scheme, lst_n in dec_words.items():
        for n, lst in lst_n.items():
            for idx, (c, sy, (verts, slices, windows)) in enumerate(lst):
                kinds = tuple(v[0] for v in verts)
                derivs = tuple(v[1] for v in verts)
                minz = 6 if (prune and n == nmax and not any(s.startswith("E") for s in sy)
                             and not any(spc[0] == "DZ" for _, spc in windows)) else 0
                add((kinds, derivs), "dec", (scheme, n, idx, verts, slices, windows, minz))
    return words, dec_words, seqs


# --------------------------------------------------------------------------------------------- phase 1
def inner(N, modes, zmax=11, bloch_too=True):
    parts3 = w5.channel_energy_parts(asm.collect_words(3), N, modes, zmax, partners=False)
    parts3np = w5.channel_energy_parts(asm.collect_words(3), N, modes, zmax, partners=False)
    parts2 = w5.channel_energy_parts(asm.collect_words(2), N, modes, zmax, kmax=2)
    h2, c1_2 = sw.inner_functions(N, modes, zmax, None)
    # DM2-induced eps^3 channel energies (self-consistent W variants)
    v, s, w = ([("V", 0, 0), ("M", 0, 1)], [([(1, 0)], [])], [(0, ("DM", 2, 0))])
    vv = ww.eval_decorated(v, s, w, N, modes, lambda spec, p, zs: {(): 0.25 * c1_2}, ps=tuple(range(zmax + 1)))
    dm2_ind = {z: (2 * G1 * vv[()][z] if () in vv else np.zeros(N + 1)) for z in range(zmax + 1)}
    H3 = H3z = None
    if bloch_too:
        import bloch
        H3 = bloch.compute_H3(N, modes, dict(parts2=parts2, parts3=parts3np, h2=h2, c1_2=c1_2, dm2_ind=dm2_ind),
                              sw.COMPONENTS["Wb"])
        H3z = bloch.compute_H3(N, modes, dict(parts2=parts2, parts3=parts3np, h2=h2, c1_2=c1_2, dm2_ind=dm2_ind),
                               sw.COMPONENTS["Zb"], with_dm=False)
    # outer-referenced auxiliary windows (scheme Wc): A_E[z] = <z|M' R V|z> (plain M'_0 insertion, no window) and the
    # Bloch h^(3) response H3M to M'_0 at eps^2 in the auxiliary Hamiltonian
    va = ww.eval_decorated([("V", 0, 0), ("M", 0, 1)], [([(1, 0)], [])], [], N, modes, None, ps=tuple(range(zmax + 1)))
    A_E = {z: (va[()][z] if () in va else np.zeros(N + 1)) for z in range(zmax + 1)}
    H3M = None
    if bloch_too:
        import bloch
        H3M = bloch.compute_H3_Mp(N, modes, A_E)
    return dict(parts2=parts2, parts3=parts3, parts3np=parts3np, h2=h2, c1_2=c1_2, dm2_ind=dm2_ind, H3=H3, H3z=H3z,
                A_E=A_E, H3M=H3M, N=N)


def wfun_factory(scheme, inn):
    N = inn["N"]
    parts2, h2, c1_2, dm2 = inn["parts2"], inn["h2"], inn["c1_2"], inn["dm2_ind"]
    parts3 = inn["parts3np"] if scheme in ("Wb", "W3x", "Zb", "Wc") else inn["parts3"]
    H3 = inn.get("H3")

    def E3(z, with_dm):
        d = {k: v.copy() for k, v in parts3[(3, z)].items()}
        if with_dm:
            d[()] = d.get((), 0) + dm2[z]
        return d

    def E2(z):
        return parts2[(2, z)]

    if scheme in DIAG_KMAX:
        def wfun(spec, p, zs):
            k, ji = spec[1], spec[2]
            zb, za = zs[ji], zs[ji + 1]
            if za != zb:
                return {(): np.zeros(N + 1)}
            z = 0 if scheme.startswith("consistent") else zb
            return E2(z) if k == 2 else E3(z, False)
        return wfun
    c1_3 = {}
    a1, a0 = E3(1, True), E3(0, True)
    for kap in set(a1) | set(a0):
        c1_3[kap] = a1.get(kap, 0) - a0.get(kap, 0)
    if scheme == "Wc":
        # c1^(3)(l; L) = c1^(3)(l) + g1 (c1^(2)(L) - c1^(2)(l)) A_c(l):  pointwise part + outer-multiplied part (C12)
        A_c = inn["A_E"][1] - inn["A_E"][0]
        c1_3[()] = c1_3.get((), 0) - G1 * c1_2 * A_c
        c1_3[("C12",)] = G1 * A_c

    def wfun(spec, p, zs):
        if spec[0] == "DM":
            k, j = spec[1], spec[2]
            return {(): 0.25 * c1_2} if k - j == 2 else {kap: 0.25 * arr for kap, arr in c1_3.items()}
        k, ji = spec[1], spec[2]
        zb, za = zs[ji], zs[ji + 1]
        if k == 2:
            if (za, zb) not in h2:
                raise KeyError(f"h2 missing for z {zb} -> {za}")
            return {(): h2[(za, zb)]}
        if scheme == "Wb":
            return H3.get((za, zb), {(): np.zeros(N + 1)})
        if scheme == "Wc":
            # h^(3)(l; L) = h^(3)(l) + (1/2)(c1^(2)(L) - c1^(2)(l)) H3M(l)
            d = dict(H3.get((za, zb), {(): np.zeros(N + 1)}))
            hm = inn["H3M"].get((za, zb), {(): np.zeros(N + 1)})[()]
            d[()] = d.get((), 0) - 0.5 * c1_2 * hm
            d[("C12",)] = 0.5 * hm
            return d
        if scheme == "Zb":
            return inn["H3z"].get((za, zb), {(): np.zeros(N + 1)})
        if za != zb:
            return {(): np.zeros(N + 1)}
        return E3(zb, True)
    return wfun


# --------------------------------------------------------------------------------------------- phase 2
_G = {}
C12 = [None]          # c1^(2)(l) array (outer cutoff) for the Wc symbol 'C12'; set from the inner functions


def _init(N, inn_path):
    _G["N"] = N
    _G["modes"] = eg.Modes(N, 3)
    with open(inn_path, "rb") as fh:
        inn = pickle.load(fh)
    _G["wf"] = {s: wfun_factory(s, inn) for s in SCHEMES}


def _task(args):
    """args = (kind, scheme, key, items, pats, cachefile); kind 'raw' (items = raw word list) or 'dec' (items =
    decorated words of one scheme)."""
    kind, scheme, key, items, pats, cachefile = args
    if cachefile and os.path.exists(cachefile):
        with open(cachefile, "rb") as fh:
            return kind, scheme, pickle.load(fh), 0.0, True
    t = time.time()
    N, modes = _G["N"], _G["modes"]
    kinds, derivs = key
    out = {}
    for n in pats:
        legs = eg.legs_of(n, len(kinds))
        zlegs = sum(eg.MAXLEGS[kinds[i]] - legs[i] for i in range(len(kinds)))
        if kind == "raw":
            rl = [(nord, verts, sops) for (nord, verts, sops, minz) in items if zlegs >= minz]
            if not rl:
                continue
            res = _with_patterns([n], lambda: ch.eval_group(list(kinds), list(derivs), [(s_, None) for (_, _, s_) in rl],
                                                            N, modes, P))
            for (nord, verts, sops), r in zip(rl, res):
                acc = out.setdefault((nord, verts, sops), {p: np.zeros(N + 1) for p in P})
                for p in P:
                    acc[p] += r[p]
        else:
            jm = 0 if scheme in DIAG_KMAX else 6
            for (nord, idx, verts, slices, windows, minz) in items:
                if zlegs < minz:
                    continue
                r = _with_patterns([n], lambda: ww.eval_decorated(verts, slices, windows, N, modes, _G["wf"][scheme],
                                                                  jmax=jm))
                acc = out.setdefault((scheme, nord, idx), {})
                for kap, d in r.items():
                    aa = acc.setdefault(kap, {p: np.zeros(N + 1) for p in P})
                    for p in P:
                        aa[p] += d[p]
    if cachefile:
        tmp = cachefile + ".tmp"
        with open(tmp, "wb") as fh:
            pickle.dump(out, fh)
        os.replace(tmp, cachefile)
    return kind, scheme, out, time.time() - t, False


def _with_patterns(pats, fn):
    """run fn() with engine.patterns returning exactly `pats` (one pattern per task)."""
    saved = eg.patterns
    try:
        eg.patterns = lambda kinds, max_lines=None, min_zero_legs=0: pats
        return fn()
    finally:
        eg.patterns = saved


# --------------------------------------------------------------------------------------------- phase 3
def assemble_all(words, dec_words, raw_vals, dec_vals, nmax, N, schemes=None):
    out = {}
    for scheme in ["raw"] + list(schemes if schemes is not None else SCHEMES):
        E = {1: {p: np.full(N + 1, G1 * p * (p - 1) / 2.0) for p in P}}
        r = {1: np.zeros(N + 1)}
        g = {1: np.full(N + 1, G1)}
        C = {}
        coup = lambda s: C12[0] if s == "C12" else (r if s[0] == "r" else g)[int(s[1:])]
        for n in range(2, nmax + 1):
            Xn = {p: np.zeros(N + 1) for p in P}
            for verts, lst in words[n].items():
                for (c, sy, sops) in lst:
                    val = raw_vals.get((n, verts, sops))
                    if val is None:
                        continue
                    for p in P:
                        coef = np.full(N + 1, float(c))
                        for s in sy:
                            coef = coef * (E[int(s[1:])][p] if s[0] == "E" else coup(s))
                        Xn[p] = Xn[p] + coef * val[p]
            if scheme != "raw":
                for idx, (c, sy, _) in enumerate(dec_words[scheme].get(n, [])):
                    for kap, d in dec_vals.get((scheme, n, idx), {}).items():
                        for p in P:
                            coef = np.full(N + 1, float(c))
                            for s in tuple(sy) + tuple(kap):
                                coef = coef * (E[int(s[1:])][p] if s[0] == "E" else coup(s))
                            Xn[p] = Xn[p] + coef * d[p]
            r[n] = -(Xn[1] - Xn[0]) / 2.0
            g[n] = -(Xn[3] - Xn[0] + 6.0 * r[n]) / 3.0
            E[n] = {p: Xn[p] + 2 * p * r[n] + p * (p - 1) / 2.0 * g[n] for p in P}
            C[n] = asm.Pi(Xn)
        out[scheme] = dict(C=C, r=r, g=g)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, required=True)
    ap.add_argument("--nmax", type=int, default=5)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cache", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--noprune", action="store_true")
    ap.add_argument("--chunk", type=int, default=20, help="patterns per task for cheap sequences")
    ap.add_argument("--schemes", default=",".join(SCHEMES))
    ap.add_argument("--pclass", default="all", choices=["all", "sp"],
                    help="sp: drop the 5-vertex non-series-parallel (K4-core) patterns from the raw sums (with --raw_only); "
                         "C5 is linear in X5, so C5[all] - C5[sp] is the K4-core part")
    ap.add_argument("--shard", default=None, help="i/n: process only tasks i, i+n, ... (cache only, no assembly)")
    ap.add_argument("--raw_only", action="store_true", help="raw tasks only (schemes from delta5.py)")
    a = ap.parse_args()
    N = a.Lmax // 2
    t0 = time.time()
    words, dec_words, seqs = catalogue(a.nmax, prune=not a.noprune)
    print(f"# Lmax={a.Lmax} sequences={len(seqs)}", flush=True)
    modes = eg.Modes(N, 3)
    inn = inner(N, modes)
    C12[0] = inn["c1_2"]
    os.makedirs(a.cache or ".", exist_ok=True)
    # per-process file, written atomically (concurrent shard jobs share the cache directory)
    inn_path = os.path.join(a.cache or ".", f"inner_L{a.Lmax}_{os.uname().nodename}_{os.getpid()}.pkl")
    with open(inn_path + ".tmp", "wb") as fh:
        pickle.dump(inn, fh)
    os.replace(inn_path + ".tmp", inn_path)
    print(f"[{time.time() - t0:8.1f}s] inner functions", flush=True)
    tasks = []
    schemes = a.schemes.split(",")
    for key, d in seqs.items():
        kinds, derivs = key
        K = len(kinds)
        # raw tasks
        if d["raw"]:
            minz = min(x[3] for x in d["raw"])
            pats = eg.patterns(list(kinds), None, minz)
            if a.pclass == "sp" and K >= 5:
                pats = [x for x in pats if eg.is_series_parallel(x, K)]
            chunk = 1 if K >= 5 else max(1, a.chunk)
            for i in range(0, len(pats), chunk):
                pp = pats[i: i + chunk]
                h = hashlib.sha1(repr(("raw", key, [sorted(x.items()) for x in pp], a.Lmax, a.noprune,
                                       sorted(set((x[0], x[2]) for x in d["raw"])))).encode()).hexdigest()[:16]
                cf = os.path.join(a.cache, f"raw_{h}.pkl")
                nd = sum(1 for sx in eg.slice_counts(pp[0], K) if sx)
                cost = len(pp) * (N + 1) ** max(1, nd) * (10 if K >= 5 else 1)
                tasks.append((cost, ("raw", None, key, d["raw"], pp, cf)))
        # decorated tasks, one per (scheme, sequence)
        for scheme in schemes:
            items = [(nord, idx, verts, slices, windows, minz) for (sch, nord, idx, verts, slices, windows, minz)
                     in d["dec"] if sch == scheme]
            if not items:
                continue
            minz = min(x[5] for x in items)
            pats = eg.patterns(list(kinds), None, minz)
            h = hashlib.sha1(repr(("dec", scheme, key, a.Lmax, a.noprune, len(items),
                                   [(x[0], x[1]) for x in items])).encode()).hexdigest()[:16]
            cf = os.path.join(a.cache, f"dec_{scheme}_{h}.pkl")
            tasks.append((len(pats) * (N + 1) ** max(1, K - 1), ("dec", scheme, key, items, pats, cf)))
    tasks.sort(key=lambda t: -t[0])
    tasks = [t[1] for t in tasks]
    if a.raw_only:
        tasks = [t for t in tasks if t[0] == "raw"]
        schemes = []
    if a.shard:
        si, sn = (int(x) for x in a.shard.split("/"))
        tasks = tasks[si::sn]
    if a.cache and "ENGINE_RED_DIR" not in os.environ:
        os.environ["ENGINE_RED_DIR"] = os.path.join(a.cache, "reduced")      # K4 boxes shared by the workers
    print(f"# tasks={len(tasks)} workers={a.workers}", flush=True)
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor, as_completed
    raw_vals, dec_vals = {}, {}
    ctx = mp.get_context(os.environ.get("MP_START", "spawn"))
    done = 0
    with ProcessPoolExecutor(a.workers, mp_context=ctx, initializer=_init, initargs=(N, inn_path)) as pool:
        futs = [pool.submit(_task, t) for t in tasks]
        for fut in as_completed(futs):
            kind, scheme, out, dt, cached = fut.result()
            if kind == "raw":
                for k, v in out.items():
                    acc = raw_vals.setdefault(k, {p: np.zeros(N + 1) for p in P})
                    for p in P:
                        acc[p] += v[p]
            else:
                for k, v in out.items():
                    acc = dec_vals.setdefault(k, {})
                    for kap, dd in v.items():
                        aa = acc.setdefault(kap, {p: np.zeros(N + 1) for p in P})
                        for p in P:
                            aa[p] += dd[p]
            done += 1
            if dt > 60 or done % 500 == 0 or done == len(tasks):
                print(f"[{time.time() - t0:8.1f}s] {done}/{len(tasks)} {kind} {scheme or ''} dt={dt:.1f}s"
                      f"{' (cached)' if cached else ''}", flush=True)
    if a.shard:
        print(f"# shard {a.shard} done in {time.time() - t0:.1f}s (cache only)", flush=True)
        return
    res = assemble_all(words, dec_words, raw_vals, dec_vals, a.nmax, N, schemes)
    save = {"L": 2 * np.arange(N + 1)}
    for scheme, d in res.items():
        for n in range(2, a.nmax + 1):
            save[f"{scheme}_C{n}"] = d["C"][n]
            save[f"{scheme}_r{n}"] = d["r"][n]
            save[f"{scheme}_g{n}"] = d["g"][n]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    np.savez(a.out, **save)
    print(f"# done in {time.time() - t0:.1f}s -> {a.out}", flush=True)
    for L in (2, 4, 10, 18, 34, 50, 100, 150, 200, 300, 400):
        if L <= a.Lmax:
            i = L // 2
            print(f"L={L:4d} " + " ".join(f"{s}:C{a.nmax}={res[s]['C'][a.nmax][i]:+.10f}" for s in ["raw"] + schemes), flush=True)


if __name__ == "__main__":
    main()
