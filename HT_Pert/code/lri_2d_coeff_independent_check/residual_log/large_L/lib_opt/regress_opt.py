#!/usr/bin/env python3
"""Regression test of lib_opt (this directory) against cached production task results of the unmodified code.

For a selection of raw tasks (pattern task of prod5.py --raw_only) at a given Lmax: re-evaluate the task with this
directory's engine and compare every output array {(n, verts, sops): {p: array over M}} with the pickle in the
production cache (same file name: the sha1 task hash of prod5.py).  Reports per task: features (K, density
dimension, number of long bundles, inclusion-exclusion terms), wall time, and the worst norm-relative difference
max|new - old| / max|old| over all arrays (and the worst elementwise relative difference over entries with
|old| > 1e-8 max|old|).  Optionally (--orig k) also times the first k selected tasks with ENGINE_TREE=0, i.e. the
original algorithm (identical to ../lib/engine.py), for the speedup.
usage: python3 regress_opt.py --Lmax 300 --cache DIR --select SPEC [--orig 2] --out FILE"""
import argparse
import hashlib
import os
import pickle
import random
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as eg  # noqa: E402
import chains as ch  # noqa: E402
import prod5 as pr  # noqa: E402

P = (0, 1, 2, 3)


def task_list(Lmax):
    words, dec_words, seqs = pr.catalogue(5, prune=True)
    N = Lmax // 2
    out = []
    for key, d in seqs.items():
        kinds, derivs = key
        K = len(kinds)
        if not d["raw"]:
            continue
        minz = min(x[3] for x in d["raw"])
        pats = eg.patterns(list(kinds), None, minz)
        chunk = 1 if K >= 5 else 20
        for i in range(0, len(pats), chunk):
            pp = pats[i: i + chunk]
            h = hashlib.sha1(repr(("raw", key, [sorted(x.items()) for x in pp], Lmax, False,
                                   sorted(set((x[0], x[2]) for x in d["raw"])))).encode()).hexdigest()[:16]
            n = pp[0]
            cyc = eg.cycle_bundles(n, K)
            nk = 1
            for b, v in n.items():
                if v and b in cyc:
                    nk *= v + 1
            nl = sum(1 for b, v in n.items() if v and b[1] - b[0] > 1)
            nd = sum(1 for sx in eg.slice_counts(n, K) if sx)
            out.append(dict(file=f"raw_{h}.pkl", key=key, items=d["raw"], pats=pp, K=K, nd=nd, nl=nl, nk=nk,
                            lines=sum(n.values())))
    return out, N


def run_task(t, N, modes):
    kinds, derivs = t["key"]
    out = {}
    for n in t["pats"]:
        legs = eg.legs_of(n, len(kinds))
        zlegs = sum(eg.MAXLEGS[kinds[i]] - legs[i] for i in range(len(kinds)))
        rl = [(nord, verts, sops) for (nord, verts, sops, minz) in t["items"] if zlegs >= minz]
        if not rl:
            continue
        res = pr._with_patterns([n], lambda: ch.eval_group(list(kinds), list(derivs), [(s_, None) for (_, _, s_) in rl],
                                                           N, modes, P))
        for (nord, verts, sops), r in zip(rl, res):
            acc = out.setdefault((nord, verts, sops), {p: np.zeros(N + 1) for p in P})
            for p in P:
                acc[p] += r[p]
    return out


def compare(new, old):
    worst, worst_el = 0.0, 0.0
    assert set(new) == set(old), "different output keys"
    for k in old:
        for p in P:
            a, b = new[k][p], old[k][p]
            sc = np.abs(b).max()
            if sc == 0.0:
                worst = max(worst, float(np.abs(a).max()))
                continue
            worst = max(worst, float(np.abs(a - b).max() / sc))
            m = np.abs(b) > 1e-8 * sc
            if m.any():
                worst_el = max(worst_el, float((np.abs(a - b)[m] / np.abs(b[m])).max()))
    return worst, worst_el


def select(tasks, spec, have, seed=7):
    """spec: comma list of K:nd:nl:nkmin:count (use * for any); only cached tasks; heaviest nk first within a class,
    then random."""
    random.seed(seed)
    chosen = []
    for item in spec.split(","):
        K, nd, nl, nkmin, cnt = item.split(":")
        pool = [t for t in tasks if t["file"] in have and t not in chosen
                and (K == "*" or t["K"] == int(K)) and (nd == "*" or t["nd"] == int(nd))
                and (nl == "*" or t["nl"] == int(nl)) and t["nk"] >= int(nkmin)]
        pool.sort(key=lambda t: -t["nk"])
        chosen += pool[: int(cnt)]
    return chosen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--select", required=True)
    ap.add_argument("--orig", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tasks, N = task_list(a.Lmax)
    have = set(os.listdir(a.cache))
    chosen = select(tasks, a.select, have)
    modes = eg.Modes(N, 3)
    lines = [f"# regress_opt.py Lmax={a.Lmax} cache={a.cache} host={os.uname().nodename} "
             f"OMP={os.environ.get('OMP_NUM_THREADS')} NUMBA={os.environ.get('NUMBA_NUM_THREADS')}",
             "# file K nd n_long n_terms lines | t_new[s] normrel elemrel | (t_orig[s])"]
    print(lines[0], flush=True)
    for i, t in enumerate(chosen):
        old = pickle.load(open(os.path.join(a.cache, t["file"]), "rb"))
        os.environ["ENGINE_TREE"] = "1"
        t0 = time.time()
        new = run_task(t, N, modes)
        dt = time.time() - t0
        nr, er = compare(new, old)
        extra = ""
        if i < a.orig:
            os.environ["ENGINE_TREE"] = "0"
            t0 = time.time()
            o2 = run_task(t, N, modes)
            dto = time.time() - t0
            nr2, _ = compare(o2, old)
            extra = f" | orig {dto:.1f}s (orig vs cache {nr2:.1e})"
            os.environ["ENGINE_TREE"] = "1"
        line = (f"{t['file']} K={t['K']} nd={t['nd']} nl={t['nl']} nk={t['nk']} lines={t['lines']} | "
                f"{dt:.1f}s {nr:.2e} {er:.2e}{extra}")
        lines.append(line)
        print(line, flush=True)
    worst = max(float(l.split("|")[1].split()[1]) for l in lines[2:]) if len(lines) > 2 else float("nan")
    lines.append(f"# worst norm-relative difference over {len(chosen)} tasks: {worst:.2e}")
    print(lines[-1], flush=True)
    open(a.out, "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
