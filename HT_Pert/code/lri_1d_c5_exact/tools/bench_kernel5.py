#!/usr/bin/env python3
"""Timing benchmark of the five-vertex streaming kernel lib5/kernel5.density5_stream (PLAN sec. 3.4, input to A7a).

Pattern: the generic dense five-vertex pattern with all ten bundles present, one line each (the complete graph K5:
every V vertex carries its four legs), bundle series S_1 = V_1 - 1 at eps = 0.  The kernel cost depends only on N,
the block size and whether crossing bundles exist, not on the values.
Thread counts: --threads sets OMP/OpenBLAS/MKL/vecLib/numba thread counts BEFORE numpy is imported.
Output: one JSON line with N, block, threads, seconds (best of --repeat, JIT compile excluded and reported
separately), peak_rss_GB (process maximum resident set), per-stage wall seconds of the best run, the exact
multiply-add counts of the kernel's GEMMs per stage (stage_madds, mirroring the kernel loops) and of the crossing
kernel, the GEMM rate, R size and a checksum.  --model N1,N2,... adds predicted madds for other N (cost model only;
nothing is run for those N).
usage: python tools/bench_kernel5.py --N 48 --block 8 --threads 1 [--repeat 3] [--model 240,400]"""
import argparse
import json
import os
import platform
import sys
import time
from math import comb


def stage_madds(N, block):
    """Multiply-add counts of the GEMMs of density5_stream (generic pattern with crossing bundles), per stage,
    mirroring the kernel's loop bounds exactly; 'C' counts the inner-u terms of the numba crossing kernel."""
    H = N // 2 + 1
    # C: for each t the terms (u, x-u, y-u, t-x-y+u) >= 0 summing to t: comb(t+3, 3); total comb(N+4, 4)
    out = dict(C=comb(N + 4, 4), LR=(N + 1) ** 3, A=0, B1=0, B2a=0, B2b=0)
    chunks = 8
    for lo in range(0, H, block):
        hi = min(H, lo + block)
        nb = hi - lo
        D = 2 * (hi - 1) + 1
        cols = nb * H
        for t in range(D):
            j0 = max(0, (t + 1) // 2 - lo)
            if j0 < nb:
                out["A"] += (t + 1) * (t + 1) * (nb - j0) * H
        for d in range(D):
            out["B1"] += (N + 1 - d) * (D - d) * cols
        for w in range(N + 1):
            i3lo = (w + 1) // 2
            if i3lo < H:
                out["B2a"] += (H - i3lo) * min(D, N + 1 - w) * cols
        ch = -(-H // chunks)
        for a in range(0, H, ch):
            b = min(H, a + ch)
            out["B2b"] += (b - a) * cols * (min(2 * (b - 1), N) + 1) * H
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, required=True)
    ap.add_argument("--block", type=int, default=8)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--model", default="", help="comma-separated N values for predicted madds (no run)")
    a = ap.parse_args()
    if a.N < 2 or a.block < 1 or a.threads < 1 or a.repeat < 1:
        ap.error("need --N >= 2, --block >= 1, --threads >= 1, --repeat >= 1")
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
              "NUMBA_NUM_THREADS"):
        os.environ[k] = str(a.threads)

    import resource
    import numpy as np
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(here, ".."))
    from lib5.kernel5 import density5_stream, PAIRS5, B2B_CHUNKS

    N = a.N
    u2 = np.empty(N + 1)                       # S_1 = chi = (1/2)_m/m! for m >= 1 (C4P Series1D convention)
    u2[0] = 1.0
    for j in range(1, N + 1):
        u2[j] = u2[j - 1] * (j - 0.5) / j
    chi = u2.copy()
    chi[0] = 0.0
    s = {b: chi for b in PAIRS5}

    t0 = time.perf_counter()
    wN = min(6, N)                                                # warm-up size valid for every N >= 0
    density5_stream({b: chi[: wN + 1] for b in PAIRS5}, wN, 2)    # JIT compile / cache load, not timed
    compile_s = time.perf_counter() - t0

    best = None
    for _ in range(a.repeat):
        tm = {}
        t0 = time.perf_counter()
        R = density5_stream(s, N, a.block, timings=tm)
        dt = time.perf_counter() - t0
        if best is None or dt < best[0]:
            best = (dt, tm, float(R.sum()), float(R[-1, -1, -1, -1]))
        del R
    dt, tm, rsum, rlast = best
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_gb = rss / 2 ** 30 if sys.platform == "darwin" else rss / 2 ** 20
    assert B2B_CHUNKS == 8, "stage_madds mirrors B2B_CHUNKS = 8"
    md = stage_madds(N, a.block)
    gemm = sum(md[k] for k in ("A", "B1", "B2a", "B2b"))
    gemm_s = sum(tm.get(k, 0.0) for k in ("A", "B1", "B2a", "B2b"))
    try:
        import numba
        nthreads = numba.get_num_threads()
        layer = numba.threading_layer()
    except Exception:
        nthreads, layer = None, None
    H = N // 2 + 1
    rec = dict(N=N, block=a.block, threads=a.threads, seconds=round(dt, 6), peak_rss_GB=round(rss_gb, 4),
               stages={k: round(v, 6) for k, v in tm.items()}, compile_s=round(compile_s, 3),
               stage_madds=md, gemm_madds=gemm, gemm_GMADD_per_s=round(gemm / gemm_s / 1e9, 3) if gemm_s else None,
               R_GB=round(H ** 4 * 8 / 2 ** 30, 4), checksum_sum=rsum, checksum_last=rlast, repeat=a.repeat,
               numba_threads=nthreads, numba_layer=layer, numpy=np.__version__, host=platform.node(),
               machine=platform.machine())
    if a.model:
        rec["model_madds"] = {int(n): stage_madds(int(n), a.block) for n in a.model.split(",") if n.strip()}
    print(json.dumps(rec), flush=True)


if __name__ == "__main__":
    main()
