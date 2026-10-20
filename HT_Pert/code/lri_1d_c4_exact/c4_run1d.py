#!/usr/bin/env python3
"""Production driver for the exact 1D C4(Lambda) (PLAN.md sec. 5, 7).

Every (chain, line pattern) of the K >= 3 chains is one task; four-vertex patterns are evaluated for one
representative per reversal pair and multiplied by the pair multiplicity.  Each task writes a checkpoint file
(reduced shells, c4lib1d.reduce_keys) named by a hash of its spec; the file carries the spec string, Lmax and the
code hash and is rejected on mismatch.  Multi-node runs use a static partition (--part i --nparts n) of the
cost-sorted task list; there is no cross-node locking (BeeGFS flock is node-local) and none is needed, because each
task file is written by exactly one partition, via a temporary file and os.replace.

Identities: numerics_sha() hashes the files that determine checkpoint contents (checkpoints and cache directories are
keyed by it); snapshot_sha() hashes every source, validator, fit, vendored, input and Slurm file of the snapshot
(validation / A9 / gate records are keyed by it).  Checkpoints carry the producing job, host, thread and block
configuration and library versions; the assembly aggregates them into the result's provenance.

usage:
  python3 c4_run1d.py run      --Lmax 400 --cache DIR [--workers W] [--part i --nparts n] [--block 32]
  python3 c4_run1d.py assemble --Lmax 400 --cache DIR --out results/c4_1d_L400.npz
  python3 c4_run1d.py list     --Lmax 400            (task list with cost estimates)
  python3 c4_run1d.py bench    --Lmax 2000 [--task 0] (one task in-process: wall time, peak RSS)
  python3 c4_run1d.py sha      [--kind numerics|snapshot]"""
import argparse
import contextlib
import glob
import hashlib
import io
import json
import os
import platform
import sys
import time

import numpy as np

import c4lib1d as lib

HERE = os.path.dirname(os.path.abspath(__file__))
NUMERICS_FILES = ("c4lib1d.py", "c4_compute1d.py", "c4_run1d.py", "windows1d.py", "vendor/exact_fast.py")
SNAPSHOT_GLOBS = ("*.py", "validate/*.py", "fits/*.py", "vendor/*", "inputs/*", "inputs/exact5/*", "slurm/*")

# K >= 3 chains used by c4_compute1d.compute (name -> kinds, slice ops, derivative vertex, prefactors, mirror)
CHAINS = {
    "VVV_RR": (["V"] * 3, [(1, 0), (1, 0)], None, ("1",), False),
    "VVV_R2R": (["V"] * 3, [(2, 0), (1, 0)], None, ("1", "Vpp"), False),
    "VVV_RR2": (["V"] * 3, [(1, 0), (2, 0)], None, ("1", "Vpp"), False),
    "VVV_PR2R": (["V"] * 3, [(2, 1), (1, 0)], None, ("1",), False),
    "VVV_RPR2": (["V"] * 3, [(1, 0), (2, 1)], None, ("1",), False),
    "MVV_RR": (["M", "V", "V"], [(1, 0), (1, 0)], None, ("1",), False),
    "VMV_RR": (["V", "M", "V"], [(1, 0), (1, 0)], None, ("1",), False),
    "dVVV_RR": (["V"] * 3, [(1, 0), (1, 0)], 0, ("1",), False),
    "VdVV_RR": (["V"] * 3, [(1, 0), (1, 0)], 1, ("1",), False),
    "VVVV_RRR": (["V"] * 4, [(1, 0)] * 3, None, ("1",), True),
}


def _hash_files(rel):
    h = hashlib.sha256()
    for f in rel:
        with open(os.path.join(HERE, f), "rb") as fh:
            h.update(f.encode() + b"\0" + hashlib.sha256(fh.read()).digest())
    return h.hexdigest()


def numerics_sha():
    """Identity of the code that determines checkpoint contents (cache directories and checkpoints)."""
    return _hash_files(NUMERICS_FILES)


def snapshot_files():
    out = set()
    for g in SNAPSHOT_GLOBS:
        for p in glob.glob(os.path.join(HERE, g)):
            if os.path.isfile(p):
                out.add(os.path.relpath(p, HERE))
    allpy = {os.path.relpath(p, HERE) for p in glob.glob(os.path.join(HERE, "**", "*.py"), recursive=True)
             if "__pycache__" not in p}
    missing = allpy - out
    if missing:
        raise RuntimeError(f"python files outside the snapshot identity: {sorted(missing)}")
    return sorted(out)


def snapshot_sha():
    """Identity of the whole snapshot (sources, validators, fits, vendored code, inputs, Slurm scripts): the key of
    validation / A9 / gate records."""
    return _hash_files(snapshot_files())


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def exec_env():
    """Execution configuration recorded in every checkpoint."""
    import numba
    import scipy
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        np.show_config()
    return dict(job=os.environ.get("SLURM_JOB_ID"), array_job=os.environ.get("SLURM_ARRAY_JOB_ID"),
                array_task=os.environ.get("SLURM_ARRAY_TASK_ID"), host=platform.node(), pid=os.getpid(),
                omp=os.environ.get("OMP_NUM_THREADS"), mkl=os.environ.get("MKL_NUM_THREADS"),
                numba_threads=os.environ.get("NUMBA_NUM_THREADS"), block=_BLOCK, python=platform.python_version(),
                numpy=np.__version__, scipy=scipy.__version__, numba=numba.__version__,
                blas_config_sha=hashlib.sha256(buf.getvalue().encode()).hexdigest()[:16])


def task_list(Lmax):
    tasks = []
    for name, (kinds, ops, dv, prefs, mirror) in CHAINS.items():
        K = len(kinds)
        pats = lib.patterns(kinds)
        if mirror:
            reps = {}
            for n in pats:
                key = min(lib.pattern_key(n), lib.pattern_key(lib.reverse_pattern(n, K)))
                reps.setdefault(key, [n, 0])
                reps[key][1] += 1
            items = list(reps.values())
        else:
            items = [[n, 1] for n in pats]
        for n, mult in items:
            if not lib.pattern_keys(kinds, ops, n, dv):
                continue                        # no zero-mode path survives: contributes nothing
            spec = json.dumps(dict(chain=name, pattern=[[i, j, v] for (i, j), v in sorted(n.items())],
                                   mult=mult, Lmax=Lmax), sort_keys=True)
            tid = hashlib.sha1(spec.encode()).hexdigest()[:20]
            tasks.append(dict(id=tid, spec=spec, chain=name, n=n, mult=float(mult), cost=cost(kinds, n, dv, Lmax)))
    tasks.sort(key=lambda t: (-t["cost"], t["id"]))
    return tasks


def cost(kinds, n, dv, Lmax):
    K = len(kinds)
    dim = sum(1 for x in lib.slice_counts(n, K) if x > 0)
    nterm = 1 if dv is None else max(1, sum(1 for b, v in n.items() if dv in b and v > 0))
    return float(nterm) * float(Lmax + 1) ** (dim + (1 if dim == 3 else 0))


_SER = None
_LMAX = None
_BLOCK = 32


def _init(Lmax, block):
    global _SER, _LMAX, _BLOCK
    _LMAX = Lmax
    _BLOCK = block
    _SER = lib.Series1D(Lmax)


def ckpt_path(cache, t):
    return os.path.join(cache, f"{t['id']}.npz")


def load_ckpt(path, t, sha, with_prov=False):
    d = np.load(path, allow_pickle=False)
    if str(d["spec"]) != t["spec"] or str(d["numerics_sha"]) != sha:
        raise RuntimeError(f"checkpoint {path} does not match task spec / numerics sha")
    M = 4 * json.loads(t["spec"])["Lmax"] + 1 + lib.MOFF
    red = {}
    for f in json.loads(str(d["prefs"])):
        red[f] = dict(Shp=d[f"{f}__Shp"], Shw={w: d[f"{f}__Shw_{w}"] for w in lib.FUNCTIONALS})
        arrs = [red[f]["Shp"]] + list(red[f]["Shw"].values())
        if red[f]["Shp"].shape != (4, M) or any(x.shape[-1] != M for x in arrs):
            raise RuntimeError(f"checkpoint {path}: wrong array shape")
        if not all(np.all(np.isfinite(x)) for x in arrs):
            raise RuntimeError(f"checkpoint {path}: non-finite values")
    if with_prov:
        return red, json.loads(str(d["prov"]))
    return red


def _task(args):
    t, cache, sha = args
    path = ckpt_path(cache, t)
    if os.path.exists(path):
        load_ckpt(path, t, sha)                 # validates
        return t["id"], 0.0, True
    kinds, ops, dv, prefs, _ = CHAINS[t["chain"]]
    t0 = time.time()
    keyamp, sh, R = lib.key_shells(kinds, ops, t["n"], _LMAX, _SER, dv, block=_BLOCK)
    del R
    red = lib.reduce_keys(keyamp, sh, prefs) if keyamp else None
    prov = exec_env()
    prov["seconds"] = round(time.time() - t0, 3)
    arrs = dict(spec=np.array(t["spec"]), numerics_sha=np.array(sha), prefs=np.array(json.dumps(list(prefs))),
                prov=np.array(json.dumps(prov)))
    M = 4 * _LMAX + 1 + lib.MOFF
    for f in prefs:
        Shp = red[f]["Shp"] if red else np.zeros((4, M))
        arrs[f"{f}__Shp"] = t["mult"] * Shp
        for w in lib.FUNCTIONALS:
            arrs[f"{f}__Shw_{w}"] = t["mult"] * (red[f]["Shw"][w] if red else np.zeros(M))
    for k, v in arrs.items():
        if v.dtype.kind == "f" and not np.all(np.isfinite(v)):
            raise RuntimeError(f"task {t['id']}: non-finite {k}")
    tmp = path + f".tmp{os.getpid()}.npz"
    np.savez(tmp, **arrs)
    os.replace(tmp, path)
    return t["id"], time.time() - t0, False


def cmd_run(a):
    sha = numerics_sha()
    os.makedirs(a.cache, exist_ok=True)
    tasks = task_list(a.Lmax)
    mine = [t for i, t in enumerate(tasks) if i % a.nparts == a.part]
    print(f"# Lmax={a.Lmax} tasks={len(tasks)} part={a.part}/{a.nparts} mine={len(mine)} workers={a.workers} "
          f"block={a.block} numerics_sha={sha[:12]} host={platform.node()}", flush=True)
    t0 = time.time()
    _init(4, a.block)                           # numba warm-up in the parent (on-disk cache for the workers)
    for name, (kinds, ops, dv, prefs, mirror) in CHAINS.items():
        lib.chain_reduced(kinds, ops, 4, _SER, dv, prefs, mirror=mirror)
    print(f"[{time.time() - t0:9.1f}s] warm-up done", flush=True)
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor, as_completed
    ctx = mp.get_context("spawn")
    done = 0
    with ProcessPoolExecutor(a.workers, mp_context=ctx, initializer=_init, initargs=(a.Lmax, a.block)) as pool:
        futs = [pool.submit(_task, (t, a.cache, sha)) for t in mine]
        for fut in as_completed(futs):
            tid, dt, cached = fut.result()
            done += 1
            if dt > 30 or done % 25 == 0 or done == len(mine):
                print(f"[{time.time() - t0:9.1f}s] {done}/{len(mine)} {tid} dt={dt:.1f}s"
                      f"{' (cached)' if cached else ''}", flush=True)
    print(f"# part {a.part} done in {time.time() - t0:.1f}s", flush=True)


def cmd_assemble(a):
    import c4_compute1d as cc
    import windows1d as wn
    sys.path.insert(0, os.path.join(HERE, "vendor"))
    import exact_fast
    sha = numerics_sha()
    tasks = task_list(a.Lmax)
    missing = [t["id"] for t in tasks if not os.path.exists(ckpt_path(a.cache, t))]
    if missing:
        raise SystemExit(f"{len(missing)} of {len(tasks)} task files missing (e.g. {missing[:3]})")
    acc = {}
    producers = {}
    for t in tasks:
        red, p = load_ckpt(ckpt_path(a.cache, t), t, sha, with_prov=True)
        lib.add_reduced(acc.setdefault(t["chain"], {}), red)
        key = json.dumps({k: p.get(k) for k in ("job", "array_job", "array_task", "host", "omp", "mkl",
                                                  "numba_threads", "block", "python", "numpy", "scipy", "numba",
                                                  "blas_config_sha")}, sort_keys=True)
        producers.setdefault(key, 0)
        producers[key] += 1
    t0 = time.time()
    res = cc.compute(a.Lmax, chains=acc, verbose=True)
    ser = lib.Series1D(a.Lmax)
    dR4 = wn.delta_R4(a.Lmax, ser)
    Ls = np.arange(2, a.Lmax + 1, 2)
    even = dict(L=Ls)
    even["fast_g2D"] = np.array([exact_fast.fast(int(L)) for L in Ls])
    even["dE0raw4_win"] = np.array([res["vac_win4_chains"][4 * L] + res["vac_win4_f"][4 * L] for L in Ls])
    even["dR4"] = np.array([dR4[int(L)] for L in Ls])
    even["dR4_closed"] = np.array([wn.h_odd(int(L) - 1) / 2916.0 for L in Ls])
    even["shift4"] = -(even["dE0raw4_win"] + even["dR4"]) / 3.0
    even["C4raw"] = np.array([res["C4"][4 * L] for L in Ls])
    even["C4Dconn"] = even["C4raw"] + even["fast_g2D"] + even["shift4"]
    out = cc.masked(res)
    for k, v in even.items():
        out["even_" + k] = v
    check_finite(out, a.Lmax)
    inputs = {f: file_sha256(os.path.join(HERE, f)) for f in snapshot_files()}
    prov = dict(numerics_sha=sha, snapshot_sha=snapshot_sha(), Lmax=a.Lmax, ntasks=len(tasks),
                cache=os.path.abspath(a.cache), assembly=exec_env(), producers=[
                    dict(json.loads(k), ntasks=v) for k, v in sorted(producers.items())],
                snapshot_manifest=inputs, assembled=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    out["provenance"] = np.array(json.dumps(prov))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    np.savez(a.out, **out)
    print(f"# assembled in {time.time() - t0:.1f}s -> {a.out}", flush=True)
    for L in (2, 10, 30, 100, 118, 200, 400, 600, 1000, 1400, 2000):
        if L <= a.Lmax:
            i = L // 2 - 1
            print(f"L={L:5d} C4raw={even['C4raw'][i]:.13f} C4Dconn={even['C4Dconn'][i]:.13f} "
                  f"shift4={even['shift4'][i]:.13f}", flush=True)


def check_finite(out, Lmax):
    """Every exported physical value is finite on its valid domain (raw: cut4 >= 3, X_p: cut4 >= p; even grid:
    all of L = 2..Lmax), and the grids have the prescribed shapes."""
    nc = 4 * Lmax + 1
    cut4 = out["cut4"]
    assert cut4.shape == (nc,) and np.array_equal(cut4, np.arange(nc))
    assert np.array_equal(out["valid"], cut4 >= 3)
    for k in ("r2", "g2", "C2", "r3", "g3", "C3", "r4", "g4", "C4"):
        if out[k].shape != (nc,) or not np.all(np.isfinite(out[k][cut4 >= 3])):
            raise RuntimeError(f"non-finite or misshaped {k} on the valid domain")
    for k in ("X2", "X3", "X4"):
        for p in lib.PS:
            if not np.all(np.isfinite(out[k][p][cut4 >= p])):
                raise RuntimeError(f"non-finite {k}[{p}] on its valid domain")
    Ls = out["even_L"]
    assert np.array_equal(Ls, np.arange(2, Lmax + 1, 2))
    for k, v in out.items():
        if k.startswith("even_") and (v.shape != Ls.shape or not np.all(np.isfinite(v))):
            raise RuntimeError(f"non-finite or misshaped {k}")


def cmd_sha(a):
    print(numerics_sha() if a.kind == "numerics" else snapshot_sha())


def cmd_bench(a):
    """Run one task in-process (default: the most expensive one) without writing a checkpoint; report wall time
    and peak RSS (for worker sizing, PLAN sec. 3.6)."""
    import resource
    tasks = task_list(a.Lmax)
    t = tasks[a.task]
    _init(a.Lmax, a.block)
    kinds, ops, dv, prefs, _ = CHAINS[t["chain"]]
    t0 = time.time()
    keyamp, sh, R = lib.key_shells(kinds, ops, t["n"], a.Lmax, _SER, dv, block=a.block)
    dt = time.time() - t0
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_gb = rss / 2 ** 20 if sys.platform != "darwin" else rss / 2 ** 30
    print(json.dumps(dict(Lmax=a.Lmax, task=a.task, chain=t["chain"], spec=t["spec"], seconds=round(dt, 2),
                          peak_rss_GB=round(rss_gb, 3), block=a.block, keys=len(keyamp),
                          threads=os.environ.get("OMP_NUM_THREADS"), host=platform.node())), flush=True)


def cmd_list(a):
    tasks = task_list(a.Lmax)
    tot = sum(t["cost"] for t in tasks)
    print(f"# {len(tasks)} tasks, total cost units {tot:.3e}")
    from collections import Counter
    print(Counter(t["chain"] for t in tasks))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("run", "assemble", "list", "bench", "sha"))
    ap.add_argument("--Lmax", type=int, default=None)
    ap.add_argument("--kind", default="snapshot", choices=("numerics", "snapshot"))
    ap.add_argument("--cache", default=None)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--part", type=int, default=0)
    ap.add_argument("--nparts", type=int, default=1)
    ap.add_argument("--block", type=int, default=32)
    ap.add_argument("--out", default=None)
    ap.add_argument("--task", type=int, default=0)
    a = ap.parse_args()
    if a.cmd != "sha" and (a.Lmax is None or a.Lmax < 2):
        ap.error("--Lmax >= 2 is required")
    if a.block < 1 or a.workers < 1 or a.nparts < 1 or not 0 <= a.part < a.nparts or a.task < 0:
        ap.error("need --block >= 1, --workers >= 1, --nparts >= 1, 0 <= --part < --nparts, --task >= 0")
    {"run": cmd_run, "assemble": cmd_assemble, "list": cmd_list, "bench": cmd_bench, "sha": cmd_sha}[a.cmd](a)


if __name__ == "__main__":
    main()
