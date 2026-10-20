#!/usr/bin/env python3
"""Regression check of the cached reduced 4-vertex boxes (K4 / phantom) of a prod5 run: every box file in
<cache>/reduced is recomputed with the current engine (no disk cache) and compared.
usage: python3 regress_boxes.py --L 40 --dir <cache>/reduced [--workers 8]"""
import argparse
import hashlib
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import engine as eg  # noqa: E402

_JOBS = {}


class _Stop(Exception):
    pass


def collect(L):
    K = 5
    modes = eg.Modes(L // 2, 3)
    found = {}

    def spy(key, compute):
        found[hashlib.sha1(repr(key).encode()).hexdigest()[:20]] = key
        raise _Stop
    saved = eg._red_disk
    eg._red_disk = spy
    os.environ["ENGINE_REDUCE"] = "1"
    try:
        for n in eg.patterns(["V"] * 5, None, 6):
            nn = {e: n.get(e, 0) for e in eg.pairs_of(K)}
            if not (eg._has_k4(nn, K) or sum(1 for c in nn.values() if c) >= 7):
                continue
            Ns = [L // 2 if c else 0 for c in eg.slice_counts(nn, K)]
            eg._RED_CACHE.clear()
            try:
                eg.density(["V"] * 5, n, Ns, modes, [0] * 5)
            except _Stop:
                pass
    finally:
        eg._red_disk = saved
    return found


def recompute(args):
    L, h, key, path = args
    modes = eg.Modes(L // 2, 3)
    t = time.time()
    if key[0] == "ph":
        _, n2items, ph, Ns2, _ = key
        R = eg.phantom_density(4, dict(n2items), ph, list(Ns2), modes.basis)
    else:
        n2items, Ns2, _ = key
        R = eg.density_generic(4, dict(n2items), list(Ns2), modes.basis, [0] * 4)
    ref = np.load(path)
    d = float(np.max(np.abs(R - ref))) if R.shape == ref.shape else float("inf")
    return h, key[0] if key[0] == "ph" else "K4", d, float(np.max(np.abs(ref))), time.time() - t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    os.environ.pop("ENGINE_RED_DIR", None)
    found = collect(a.L)
    files = {f[4:24]: os.path.join(a.dir, f) for f in os.listdir(a.dir) if f.startswith("red_") and f.endswith(".npy") and len(f) == 28}
    jobs = [(a.L, h, found[h], p) for h, p in files.items() if h in found]
    print(f"# L={a.L}: {len(found)} distinct reduced boxes for the heavy patterns, {len(files)} files, {len(jobs)} matched",
          flush=True)
    worst = 0.0
    with ProcessPoolExecutor(a.workers) as pool:
        for h, kind, d, mx, dt in pool.map(recompute, jobs):
            worst = max(worst, d / max(mx, 1e-300))
            print(f"  {h} {kind:3s} max|new - file| = {d:.2e} (max |box| {mx:.2e}, rel {d / max(mx, 1e-300):.1e}) {dt:.0f}s",
                  flush=True)
    print(f"# worst relative deviation {worst:.2e}", flush=True)


if __name__ == "__main__":
    main()
