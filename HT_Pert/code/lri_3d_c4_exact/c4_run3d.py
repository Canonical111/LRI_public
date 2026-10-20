#!/usr/bin/env python3
"""Production driver: C_2, C_3, C_4 (raw / consistent) of the 3D model for every even L <= L_max.

The four-vertex chain (the only expensive piece) is split into one task per mirror-reduced line pattern, run in a
process pool with per-task checkpoint files (a rerun skips finished tasks); two- and three-vertex chains run in
the main process.

usage: python3 c4_run3d.py --Lmax 200 --workers 16 --threads 4 --cache CACHE_DIR --out results/c4_L200.npz
"""
import argparse
import os
import sys


def _early_threads():
    t = "1"
    for i, a in enumerate(sys.argv):
        if a == "--threads" and i + 1 < len(sys.argv):
            t = sys.argv[i + 1]
    for v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
        os.environ[v] = t


_early_threads()

import json  # noqa: E402
import time  # noqa: E402
from fractions import Fraction as Fr  # noqa: E402
import multiprocessing as mp  # noqa: E402

import numpy as np  # noqa: E402

import c4lib3d as lib  # noqa: E402
import c4_compute3d as comp  # noqa: E402

_B = None


def _init(tables_path, Lmax):
    global _B
    T = dict(np.load(tables_path))
    _B = lib.Basis(Lmax, T=T)


def task_name(n):
    return "p_" + "_".join(f"{i}{j}{v}" for (i, j), v in sorted(n.items()))


def run_task(args):
    n, mult, path, split = args
    if os.path.exists(path):
        return path, 0.0, "cached"
    t0 = time.time()
    lib.LC_SPLIT = split
    out = lib.chain_pattern(_B, "VVVV", [(1, 0)] * 3, n, (0, 1, 2, 3), [0, 0, 0, 0], mult)
    lib.LC_SPLIT = None
    tmp = path + ".tmp.npz"
    if out is None:
        np.savez(tmp, empty=np.array(1))
    else:
        keys, keyamp, sh = out
        amps = [[str(keyamp[k].get(p, Fr(0))) for p in range(4)] for k in keys]
        np.savez(tmp, keys=np.array(keys, dtype=np.int64).reshape(len(keys), -1), sh=sh,
                 amps=np.array(json.dumps(amps)))
    os.replace(tmp, path)
    return path, time.time() - t0, "done"


def tasks_for(Lmax, cache, max_lines=5, nsplit=16):
    """K4-minus-edge patterns (graph class 2) are split into nsplit subtasks (l_c = k mod nsplit); shell sums are
    linear in the density, so the subtask files simply add."""
    done, out = set(), []
    for n in lib.patterns("VVVV", max_lines):
        k1, k2 = lib.pattern_key(n), lib.pattern_key(lib.reverse_pattern(n, 4))
        if k2 in done:
            continue
        done.add(k1)
        mult = 1 if k1 == k2 else 2
        cls = lib.graph_class(n, 4)
        if cls == 2 and nsplit > 1:
            for k in range(nsplit):
                out.append((cls, sum(n.values()), n, mult,
                            os.path.join(cache, task_name(n) + f"_lc{k}of{nsplit}.npz"), (k, nsplit)))
        else:
            out.append((cls, sum(n.values()), n, mult, os.path.join(cache, task_name(n) + ".npz"), None))
    out.sort(key=lambda x: (-x[0], -x[1]))          # expensive classes first
    return out


def assemble_T4_lin(task_list):
    lin = lib.Lin()
    for (_, _, n, mult, path, _split) in task_list:
        z = np.load(path)
        if "empty" in z:
            continue
        amps = json.loads(str(z["amps"]))
        cum = np.cumsum(z["sh"], axis=1)
        for t, row in enumerate(amps):
            lin.add([Fr(x) for x in row], cum[t])
    return lin


def assemble_T4(task_list, S):
    T4 = {p: np.zeros(S + 1) for p in range(4)}
    for (_, _, n, mult, path, _split) in task_list:
        z = np.load(path)
        if "empty" in z:
            continue
        amps = json.loads(str(z["amps"]))
        cum = np.cumsum(z["sh"], axis=1)
        for t, row in enumerate(amps):
            for p in range(4):
                a = Fr(row[p])
                if a != 0:
                    T4[p] += float(a) * cum[t]
    return T4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, required=True)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only4", action="store_true", help="stop after the four-vertex tasks")
    args = ap.parse_args()
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:9.1f}s] {m}", flush=True)
    os.makedirs(args.cache, exist_ok=True)
    tables = os.path.join(args.cache, f"tables_L{args.Lmax}.npz")
    if not os.path.exists(tables):
        T = lib.mode_tables(args.Lmax)
        np.savez(tables + ".tmp.npz", **T)
        os.replace(tables + ".tmp.npz", tables)
    log("mode tables ready")
    tl = tasks_for(args.Lmax, args.cache)
    todo = [(n, mult, path, split) for (_, _, n, mult, path, split) in tl if not os.path.exists(path)]
    log(f"{len(tl)} four-vertex tasks, {len(todo)} to run, {args.workers} workers x {args.threads} threads")
    if todo:
        ctx = mp.get_context(os.environ.get("MP_START", "spawn"))
        with ctx.Pool(args.workers, initializer=_init, initargs=(tables, args.Lmax)) as pool:
            k = 0
            for path, dt, st in pool.imap_unordered(run_task, todo):
                k += 1
                log(f"task {k}/{len(todo)} {os.path.basename(path)} {st} {dt:.1f}s")
    if args.only4:
        return
    S = args.Lmax // 2
    T4 = assemble_T4_lin(tl)
    log("four-vertex chain assembled")
    B = lib.Basis(args.Lmax, T=dict(np.load(tables)))
    res = comp.compute_exact(args.Lmax, basis=B, T4lin=T4, verbose=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    np.savez(args.out, **{k: v for k, v in res.items() if k != "parts"},
             **{"part_" + k: v for k, v in res["parts"].items()})
    log(f"wrote {args.out}")
    for j in range(0, S + 1, max(1, S // 20)):
        print(f"L={2 * j:5d} C2={res['C2'][j]:.15f} C3={res['C3'][j]:.15f} C4raw={res['C4raw'][j]:.12f} "
              f"C4cons={res['C4cons'][j]:.12f}", flush=True)


if __name__ == "__main__":
    main()
