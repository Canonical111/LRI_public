#!/usr/bin/env python3
"""Assemble C_2..C_5 from a prod5.py task cache directory (light: sums the per-task pickles, no diagram work).
Reports the tasks of the catalogue that are missing from the cache; with --allow_missing it assembles anyway
(preliminary numbers, flagged in the output file).
usage: python3 assemble_cache.py --Lmax 160 --cache dir --out x.npz [--raw_only] [--allow_missing]"""
import argparse
import hashlib
import os
import pickle

import numpy as np

import engine as eg
import prod5 as pr

P = (0, 1, 2, 3)


def expected(Lmax, raw_only, schemes):
    words, dec_words, seqs = pr.catalogue(5, prune=True)
    files = []
    for key, d in seqs.items():
        kinds, derivs = key
        K = len(kinds)
        if d["raw"]:
            minz = min(x[3] for x in d["raw"])
            pats = eg.patterns(list(kinds), None, minz)
            chunk = 1 if K >= 5 else 20
            for i in range(0, len(pats), chunk):
                pp = pats[i: i + chunk]
                h = hashlib.sha1(repr(("raw", key, [sorted(x.items()) for x in pp], Lmax, False,
                                       sorted(set((x[0], x[2]) for x in d["raw"])))).encode()).hexdigest()[:16]
                files.append((f"raw_{h}.pkl", key, pp))
        if raw_only:
            continue
        for scheme in schemes:
            items = [(nord, idx) for (sch, nord, idx, *_r) in d["dec"] if sch == scheme]
            if not items:
                continue
            h = hashlib.sha1(repr(("dec", scheme, key, Lmax, False, len(items), items)).encode()).hexdigest()[:16]
            files.append((f"dec_{scheme}_{h}.pkl", key, None))
    return words, dec_words, files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--raw_only", action="store_true")
    ap.add_argument("--allow_missing", action="store_true")
    a = ap.parse_args()
    N = a.Lmax // 2
    schemes = [] if a.raw_only else list(pr.SCHEMES)
    words, dec_words, files = expected(a.Lmax, a.raw_only, schemes)
    have = set(os.listdir(a.cache))
    missing = [(f, k, pp) for f, k, pp in files if f not in have]
    print(f"# expected {len(files)} task files, missing {len(missing)}")
    for f, k, pp in missing[:20]:
        print("   missing", f, k, pp)
    if missing and not a.allow_missing:
        raise SystemExit("missing tasks")
    raw_vals, dec_vals = {}, {}
    for f, k, pp in files:
        if f not in have:
            continue
        with open(os.path.join(a.cache, f), "rb") as fh:
            out = pickle.load(fh)
        for key, v in out.items():
            if f.startswith("raw_"):
                acc = raw_vals.setdefault(key, {p: np.zeros(N + 1) for p in P})
                for p in P:
                    acc[p] += v[p]
            else:
                acc = dec_vals.setdefault(key, {})
                for kap, dd in v.items():
                    aa = acc.setdefault(kap, {p: np.zeros(N + 1) for p in P})
                    for p in P:
                        aa[p] += dd[p]
    res = pr.assemble_all(words, dec_words, raw_vals, dec_vals, 5, N, schemes)
    save = {"L": 2 * np.arange(N + 1), "n_missing_tasks": np.array(len(missing))}
    for scheme, d in res.items():
        for n in range(2, 6):
            save[f"{scheme}_C{n}"] = d["C"][n]
            save[f"{scheme}_r{n}"] = d["r"][n]
            save[f"{scheme}_g{n}"] = d["g"][n]
    np.savez(a.out, **save)
    print(f"# -> {a.out}  (missing tasks: {len(missing)})")
    for L in (10, 34, 80, 120, 160, 200):
        if L <= a.Lmax:
            print(f"L={L:4d} raw C5 = {res['raw']['C'][5][L // 2]:+.10f}")


if __name__ == "__main__":
    main()
