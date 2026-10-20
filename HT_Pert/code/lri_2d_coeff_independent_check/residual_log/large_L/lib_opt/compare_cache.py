#!/usr/bin/env python3
"""Per-task comparison of two prod5 caches (same Lmax): every task file present in both.
usage: compare_cache.py new_dir ref_dir out.txt"""
import os, pickle, sys
import numpy as np
a, b, outf = sys.argv[1], sys.argv[2], sys.argv[3]
fa = sorted(f for f in os.listdir(a) if f.startswith("raw_"))
common = [f for f in fa if os.path.exists(os.path.join(b, f))]
worst, wf, n = 0.0, None, 0
for f in common:
    x = pickle.load(open(os.path.join(a, f), "rb")); y = pickle.load(open(os.path.join(b, f), "rb"))
    assert set(x) == set(y), f
    for k in y:
        for p in y[k]:
            sc = np.abs(y[k][p]).max()
            d = float(np.abs(x[k][p] - y[k][p]).max() / sc) if sc > 0 else float(np.abs(x[k][p]).max())
            if d > worst:
                worst, wf = d, f
    n += 1
msg = f"compare_cache {a} vs {b}: {n} common task files; worst norm-relative difference {worst:.2e} ({wf})"
print(msg)
open(outf, "w").write(msg + "\n")
