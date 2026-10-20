#!/usr/bin/env python3
"""Per-pattern decomposition of C_4(L) from the per-task checkpoint files of the c4_exact L_max = 2000 run
(copied read-only from symmetry:/mnt/beegfs/zzheng1/indep2d/c4_exact/cache_L2000 to data/cache_L2000).

load_patterns() rebuilds the task list of ../c4_exact/c4_run.py (same hashing) and returns, for every chain name,
a list of (pattern dict, multiplicity, {p: array over M}) so that any class of diagrams can be summed.
check_total() reassembles C_4 raw/cons/corr through c4_compute.compute and compares with results/c4_L2000.npz."""
import hashlib
import os

import numpy as np

import c4lib as lib
import c4_compute as cc

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "cache_L2000")
LMAX = 2000
SPECS = [(["V", "V", "V"], [(1, 0), (1, 0)], None), (["V", "V", "V"], [(2, 0), (1, 0)], None),
         (["V", "V", "V"], [(1, 0), (2, 0)], None), (["V", "V", "V"], [(2, 1), (1, 0)], None),
         (["V", "V", "V"], [(1, 0), (2, 1)], None), (["M", "V", "V"], [(1, 0), (1, 0)], None),
         (["V", "M", "V"], [(1, 0), (1, 0)], None), (["V", "V", "V"], [(1, 0), (1, 0)], 0),
         (["V", "V", "V"], [(1, 0), (1, 0)], 1)]


def chain_name(kinds, ops, dv, ml):
    return f"{''.join(kinds)}|{ops}|{dv}|{ml}"


def load_patterns(cache=CACHE, max_lines4=5):
    chains = {}
    for kinds, ops, dv in SPECS:
        chains[chain_name(kinds, ops, dv, None)] = (kinds, ops, dv, None)
    chains[chain_name(["V"] * 4, [(1, 0)] * 3, None, max_lines4)] = (["V"] * 4, [(1, 0)] * 3, None, max_lines4)
    out = {}
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
        lst = []
        for n, mult in items:
            h = hashlib.sha1((name + repr(lib.pattern_key(n))).encode()).hexdigest()[:16]
            f = os.path.join(cache, f"{h}.npz")
            d = np.load(f)
            lst.append((n, mult, {p: d[f"p{p}"] for p in range(4)}))   # cached values already include mult
        out[name] = lst
    return out


def chain_sums(pats):
    return {name: {p: sum(v[p] for _, _, v in lst) for p in range(4)} for name, lst in pats.items()}


def check_total(pats):
    sums = chain_sums(pats)
    runner = lambda kinds, ops, dv, ml: sums[chain_name(kinds, ops, dv, ml)]
    res = cc.compute(LMAX, max_lines4=5, verbose=False, chain_runner=runner)
    ref = np.load(os.path.join(HERE, "..", "c4_exact", "results", "c4_L2000.npz"))
    for k in ("C4raw", "C4cons", "C4corr"):
        print(k, "max |rebuilt - stored| =", np.abs(res[k] - ref[k]).max())
    return res


def components(n, K):
    """connected components of the chi-line multigraph (vertices with no chi line are singletons)."""
    parent = list(range(K))

    def f(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for (i, j), v in n.items():
        if v:
            parent[f(i)] = f(j)
    comps = {}
    for i in range(K):
        comps.setdefault(f(i), []).append(i)
    return sorted(comps.values())


def topology(n, K):
    """time-order-free label: sorted list over components of (sorted bundle sizes, number of vertices)."""
    comps = components(n, K)
    lab = []
    for c in comps:
        b = sorted((v for (i, j), v in n.items() if v and i in c and j in c), reverse=True)
        lab.append((len(c), tuple(b)))
    return tuple(sorted(lab, reverse=True))


if __name__ == "__main__":
    pats = load_patterns()
    check_total(pats)
    name4 = chain_name(["V"] * 4, [(1, 0)] * 3, None, 5)
    tops = {}
    for n, mult, v in pats[name4]:
        t = topology(n, 4)
        tops.setdefault(t, 0)
        tops[t] += 1
    for t, c in sorted(tops.items()):
        print(t, c)
