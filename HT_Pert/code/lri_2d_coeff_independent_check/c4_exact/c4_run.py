#!/usr/bin/env python3
"""Production driver: every chain pattern is an independent task in a process pool (dynamic scheduling,
largest first), with per-task checkpoint files so an interrupted run resumes.  Four-vertex patterns are
evaluated for one representative of each time-reversal pair (verified identical, README Sec. 4) and doubled.

usage: python3 c4_run.py --Lmax 1000 --workers 28 --cache cache_L1000 --out results/c4_L1000.npz"""
import argparse
import hashlib
import os
import sys
import time

import numpy as np

import c4lib as lib
import c4_compute as cc

_SER = None
_N = None


def _init(N):
    global _SER, _N
    _N = N
    _SER = lib.Series(N)


def _task(args):
    name, kinds, ops, dv, n, mult, cachefile = args
    if cachefile and os.path.exists(cachefile):
        d = np.load(cachefile)
        return name, {p: d[f"p{p}"] for p in range(4)}, 0.0, True
    t = time.time()
    r = lib.chain_pattern(kinds, ops, n, _N, _SER, (0, 1, 2, 3), dv)
    if r is None:
        r = {p: np.zeros(_N + 1) for p in range(4)}
    r = {p: mult * r[p] for p in range(4)}
    if cachefile:
        tmp = cachefile + ".tmp.npz"
        np.savez(tmp, **{f"p{p}": r[p] for p in range(4)})
        os.replace(tmp, cachefile)
    return name, r, time.time() - t, False


def cost(kinds, n, dv):
    K = len(kinds)
    nsl = lib.slice_counts(n, K)
    dim = sum(1 for x in nsl if x > 0)
    cfg = 1
    for v in n.values():
        cfg *= v + 1
    return (dim, cfg * (2 if dv is not None else 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cache", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-lines4", type=int, default=5)
    a = ap.parse_args()
    N = a.Lmax // 2
    if a.cache:
        os.makedirs(a.cache, exist_ok=True)
    t0 = time.time()

    # ---------------------------------------------------------------- task list (every K >= 3 chain used)
    chains = {}

    def reg(kinds, ops, dv, ml):
        name = f"{''.join(kinds)}|{ops}|{dv}|{ml}"
        chains[name] = (kinds, ops, dv, ml)
        return name

    # the same calls compute() makes (order irrelevant)
    specs = [(["V", "V", "V"], [(1, 0), (1, 0)], None), (["V", "V", "V"], [(2, 0), (1, 0)], None),
             (["V", "V", "V"], [(1, 0), (2, 0)], None), (["V", "V", "V"], [(2, 1), (1, 0)], None),
             (["V", "V", "V"], [(1, 0), (2, 1)], None), (["M", "V", "V"], [(1, 0), (1, 0)], None),
             (["V", "M", "V"], [(1, 0), (1, 0)], None), (["V", "V", "V"], [(1, 0), (1, 0)], 0),
             (["V", "V", "V"], [(1, 0), (1, 0)], 1)]
    for kinds, ops, dv in specs:
        reg(kinds, ops, dv, None)
    reg(["V"] * 4, [(1, 0)] * 3, None, a.max_lines4)
    tasks = []
    for name, (kinds, ops, dv, ml) in chains.items():
        pats = lib.patterns(kinds, ml)
        K = len(kinds)
        if K == 4:
            reps = {}
            for n in pats:
                k, kr = lib.pattern_key(n), lib.pattern_key(lib.reverse_pattern(n, K))
                key = min(k, kr)
                reps.setdefault(key, [n, 0])
                reps[key][1] += 1
            items = [(n, m) for n, m in reps.values()]
        else:
            items = [(n, 1) for n in pats]
        for n, mult in items:
            h = hashlib.sha1((name + repr(lib.pattern_key(n))).encode()).hexdigest()[:16]
            cf = os.path.join(a.cache, f"{h}.npz") if a.cache else None
            tasks.append((name, kinds, ops, dv, n, float(mult), cf))
    tasks.sort(key=lambda t: cost(t[1], t[4], t[3]), reverse=True)
    print(f"# Lmax={a.Lmax} N={N} tasks={len(tasks)} workers={a.workers}", flush=True)

    acc = {name: {p: np.zeros(N + 1) for p in range(4)} for name in chains}
    # warm-up: compile every numba kernel once in the parent (cache=True writes the on-disk cache that the
    # spawned workers load); spawn (not fork) keeps numba's threading layer fork-safe
    _init(4)
    for name, (kinds, ops, dv, ml) in chains.items():
        lib.chain(kinds, ops, 4, _SER, (0, 1, 2, 3), deriv_vertex=dv, max_lines=ml)
    print(f"[{time.time() - t0:9.1f}s] warm-up done", flush=True)
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor, as_completed
    ctx = mp.get_context("spawn")
    done = 0
    # ProcessPoolExecutor raises BrokenProcessPool if a worker dies (e.g. cgroup OOM kill), instead of hanging;
    # finished tasks are checkpointed, so a rerun resumes.
    with ProcessPoolExecutor(a.workers, mp_context=ctx, initializer=_init, initargs=(N,)) as pool:
        futs = [pool.submit(_task, t) for t in tasks]
        for fut in as_completed(futs):
            name, r, dt, cached = fut.result()
            for p in range(4):
                acc[name][p] += r[p]
            done += 1
            if dt > 10 or done % 50 == 0 or done == len(tasks):
                print(f"[{time.time() - t0:9.1f}s] {done}/{len(tasks)} {name} dt={dt:.1f}s"
                      f"{' (cached)' if cached else ''}", flush=True)

    def runner(kinds, ops, dv, ml):
        name = f"{''.join(kinds)}|{ops}|{dv}|{ml}"
        return acc[name]

    res = cc.compute(a.Lmax, max_lines4=a.max_lines4, verbose=True, chain_runner=runner)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    np.savez(a.out, **{k: v for k, v in res.items() if k != "parts"},
             **{f"partsPi_{k}": np.array([res["parts"][p][k] for p in range(4)]) for k in "abcdef"})
    print(f"# done in {time.time() - t0:.1f}s -> {a.out}", flush=True)
    for L in (2, 10, 30, 100, 200, 400, 600, 800, 1000, 1200, 1600, 2000):
        if L <= a.Lmax:
            i = L // 2
            print(f"L={L:5d} C4raw={res['C4raw'][i]:.13f} C4cons={res['C4cons'][i]:.13f} "
                  f"C4corr={res['C4corr'][i]:.13f}", flush=True)


if __name__ == "__main__":
    main()
