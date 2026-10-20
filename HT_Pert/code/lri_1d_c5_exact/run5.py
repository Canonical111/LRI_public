#!/usr/bin/env python3
"""Production driver for the exact 1D C5(Lambda) (PLAN.md sec. 5, 7; CLI as INTERFACES.md / C4P c4_run1d.py).

Tasks: one per (task chain, pattern representative) of the rs5 catalogue (assemble5.is_task_chain: K >= 4, and K = 3
without key records); palindromic chains use one representative per reversal pair with its multiplicity.  Each task
writes a checkpoint (reduced shells per prefactor vector: per-p shells and exact-weight functional shells) named by a
hash of its spec, carrying the spec, the numerics sha and the producer provenance; the file is rejected on mismatch or
non-finite / misshaped arrays.  Multi-node runs use a static partition of the cost-sorted list (no cross-node locking;
each task file is written by one partition via tmp + os.replace).  `assemble` loads every checkpoint (all must exist),
runs assemble5.compute (K = 2 and record chains serially) and windows5.compute, checks finiteness on the valid domains
and writes the result npz (INTERFACES.md schema) with provenance.

usage:
  python3 run5.py run      --Lmax L --cache DIR [--workers W] [--part i --nparts n] [--block B]
  python3 run5.py assemble --Lmax L --cache DIR --out OUT.npz
  python3 run5.py list     --Lmax L
  python3 run5.py bench    --Lmax L [--task k] [--block B]
  python3 run5.py sha      [--kind numerics|snapshot]
  python3 run5.py worstspec --Lmax L    (sha256 of the designated worst-case benchmark task spec)"""
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
from fractions import Fraction as Fr

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import words5                                         # noqa: E402
import assemble5                                      # noqa: E402
from lib5 import keys as K5                           # noqa: E402
from lib5.common import FUNCTIONALS, MOFF             # noqa: E402
from lib5.paths import slice_counts                   # noqa: E402
from lib5.series import Series5                       # noqa: E402

NUMERICS_FILES = ("lib5/common.py", "lib5/series.py", "lib5/paths.py", "lib5/density.py", "lib5/kernel5.py",
                  "lib5/shells.py", "lib5/keys.py", "rs5.py", "words5.py", "assemble5.py", "windows5.py", "run5.py",
                  "vendor/exact_fast.py")
SNAPSHOT_GLOBS = ("*.py", "lib5/*.py", "validate/*.py", "fits/*.py", "tools/*.py", "vendor/*", "inputs/*",
                  "inputs/exact5/*", "slurm/*")
NMAX = 5


def _hash_files(rel):
    h = hashlib.sha256()
    for f in rel:
        with open(os.path.join(HERE, f), "rb") as fh:
            h.update(f.encode() + b"\0" + hashlib.sha256(fh.read()).digest())
    return h.hexdigest()


def numerics_sha():
    return _hash_files(NUMERICS_FILES)


def snapshot_files():
    out = set()
    for g in SNAPSHOT_GLOBS:
        for p in glob.glob(os.path.join(HERE, g)):
            if os.path.isfile(p) and "__pycache__" not in p:
                out.add(os.path.relpath(p, HERE))
    allpy = {os.path.relpath(p, HERE) for p in glob.glob(os.path.join(HERE, "**", "*.py"), recursive=True)
             if "__pycache__" not in p and not os.path.relpath(p, HERE).startswith("proto/")}
    missing = allpy - out
    if missing:
        raise RuntimeError(f"python files outside the snapshot identity: {sorted(missing)}")
    return sorted(out)


def snapshot_sha():
    return _hash_files(snapshot_files())


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


_SER = None
_LMAX = None
_BLOCK = 32


def exec_env():
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


def _fkey(f):
    return ",".join(str(x) for x in f)


def task_list(Lmax):
    plan = words5.chain_plan(NMAX)
    tasks = []
    for ch, d in sorted(plan.items(), key=lambda x: repr(x[0])):
        if not assemble5.is_task_chain(ch, d):
            continue
        verts, sops = ch
        K = len(verts)
        prefs = sorted(d["prefs"], key=_fkey)
        mirror = K5.is_palindrome(verts, sops)
        for n, mult in K5.chain_items(verts, mirror):
            ka = K5.pattern_keys(verts, sops, n)
            if not ka:
                continue
            spec = json.dumps(dict(chain=repr(ch), pattern=[[i, j, v] for (i, j), v in sorted(n.items())],
                                   mult=mult, Lmax=Lmax, prefs=[_fkey(f) for f in prefs]), sort_keys=True)
            tid = hashlib.sha1(spec.encode()).hexdigest()[:20]
            nsl = slice_counts(n, K)
            dim = sum(1 for x in nsl if x > 0)
            nj = 1 + sum(v[1] for v in verts)
            crossing = K == 5 and any(n[b] > 0 for b in ((0, 3), (0, 4), (1, 3), (1, 4)))
            full4 = K == 5 and dim == 4
            tasks.append(dict(id=tid, spec=spec, chain=ch, n=n, mult=float(mult), prefs=prefs, nkeys=len(ka),
                              worst_eligible=bool(full4 and crossing),
                              cost=task_cost(Lmax, dim, nj, len(ka), full4 and crossing)))
    tasks.sort(key=lambda t: (-t["cost"], t["id"]))
    return tasks


def task_cost(Lmax, dim, njet, nkeys, full_crossing):
    """Cost model (multiply-add equivalents): density (K=5 middle-split kernel 0.12 N^5 when all four slices are
    occupied and a crossing bundle exists; ~N^(dim+1) for the C4P/run kernels otherwise) plus the shell contraction
    (~3 x keys x H^dim).  Used for heavy-first scheduling and to pick the worst-case benchmark task."""
    N = Lmax + 1
    H = Lmax // 2 + 1
    dens = 0.12 * N ** 5 if full_crossing else float(N) ** (dim + (1 if dim >= 2 else 0))
    return float(njet) * dens + 3.0 * nkeys * float(H) ** dim


def worst_task(Lmax, tasks=None):
    """Designated worst-case benchmark task (A7a sizing): a five-vertex pattern with all four slices occupied and a
    crossing bundle (a full H^4 density through the middle-split kernel), with the most keys (largest shell
    contraction); ties broken by task id.  Deterministic for a given snapshot and Lmax."""
    tasks = tasks if tasks is not None else task_list(Lmax)
    elig = [t for t in tasks if t["worst_eligible"]]
    return max(elig, key=lambda t: (t["nkeys"], t["id"]))


def _init(Lmax, block):
    global _SER, _LMAX, _BLOCK
    _LMAX, _BLOCK = Lmax, block
    _SER = Series5(Lmax)


def ckpt_path(cache, t):
    return os.path.join(cache, f"{t['id']}.npz")


def load_ckpt(path, t, sha, with_prov=False):
    d = np.load(path, allow_pickle=False)
    if str(d["spec"]) != t["spec"] or str(d["numerics_sha"]) != sha:
        raise RuntimeError(f"checkpoint {path} does not match task spec / numerics sha")
    M = 4 * json.loads(t["spec"])["Lmax"] + 1 + MOFF
    red = {}
    for f in t["prefs"]:
        k = _fkey(f)
        red[f] = dict(Shp=d[f"{k}__Shp"], Shw={w: d[f"{k}__Shw_{w}"] for w in FUNCTIONALS})
        arrs = [red[f]["Shp"]] + list(red[f]["Shw"].values())
        if red[f]["Shp"].shape != (4, M) or any(x.shape[-1] != M for x in arrs):
            raise RuntimeError(f"checkpoint {path}: wrong array shape")
        if not all(np.all(np.isfinite(x)) for x in arrs):
            raise RuntimeError(f"checkpoint {path}: non-finite values")
    if with_prov:
        return red, json.loads(str(d["prov"]))
    return red


def _compute_task(t):
    verts, sops = t["chain"]
    prefs = {f: f for f in t["prefs"]}
    keyamp, sh, R = K5.key_shells(verts, sops, t["n"], _LMAX, _SER, block=_BLOCK)
    del R
    M = 4 * _LMAX + 1 + MOFF
    if keyamp is None:
        return {f: dict(Shp=np.zeros((4, M)), Shw={w: np.zeros(M) for w in FUNCTIONALS}) for f in prefs}, 0
    return K5.reduce_keys(keyamp, sh, prefs, t["mult"]), len(keyamp)


def _task(args):
    t, cache, sha = args
    path = ckpt_path(cache, t)
    if os.path.exists(path):
        load_ckpt(path, t, sha)
        return t["id"], 0.0, True
    t0 = time.time()
    red, nkeys = _compute_task(t)
    prov = exec_env()
    prov["seconds"] = round(time.time() - t0, 3)
    prov["keys"] = nkeys
    arrs = dict(spec=np.array(t["spec"]), numerics_sha=np.array(sha), prov=np.array(json.dumps(prov)))
    for f, d in red.items():
        k = _fkey(f)
        arrs[f"{k}__Shp"] = d["Shp"]
        for w in FUNCTIONALS:
            arrs[f"{k}__Shw_{w}"] = d["Shw"][w]
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
    _init(8, a.block)                         # numba warm-up in the parent (on-disk cache for the workers)
    for t in tasks[:: max(1, len(tasks) // 40)]:
        verts, sops = t["chain"]
        K5.key_shells(verts, sops, t["n"], 8, _SER, block=a.block)
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
            if dt > 60 or done % 50 == 0 or done == len(mine):
                print(f"[{time.time() - t0:9.1f}s] {done}/{len(mine)} {tid} dt={dt:.1f}s"
                      f"{' (cached)' if cached else ''}", flush=True)
    print(f"# part {a.part} done in {time.time() - t0:.1f}s", flush=True)


def check_finite(out, Lmax):
    nc = 4 * Lmax + 1
    cut4 = out["cut4"]
    assert cut4.shape == (nc,) and np.array_equal(cut4, np.arange(nc))
    assert np.array_equal(out["valid"], cut4 >= 3)
    for n in range(2, NMAX + 1):
        for k in ("r", "g", "C"):
            v = out[f"{k}{n}"]
            if v.shape != (nc,) or not np.all(np.isfinite(v[cut4 >= 3])):
                raise RuntimeError(f"non-finite or misshaped {k}{n} on the valid domain")
        for p in range(4):
            if not np.all(np.isfinite(out[f"X{n}"][p][cut4 >= p])):
                raise RuntimeError(f"non-finite X{n}[{p}] on its valid domain")
    Ls = out["even_L"]
    assert np.array_equal(Ls, np.arange(2, Lmax + 1, 2))
    for k, v in out.items():
        if k.startswith("even_") and (v.shape != Ls.shape or not np.all(np.isfinite(v))):
            raise RuntimeError(f"non-finite or misshaped {k}")


def cmd_assemble(a):
    import windows5
    sha = numerics_sha()
    tasks = task_list(a.Lmax)
    missing = [t["id"] for t in tasks if not os.path.exists(ckpt_path(a.cache, t))]
    if missing:
        raise SystemExit(f"{len(missing)} of {len(tasks)} task files missing (e.g. {missing[:3]})")
    acc, producers = {}, {}
    for t in tasks:
        red, p = load_ckpt(ckpt_path(a.cache, t), t, sha, with_prov=True)
        K5.add_reduced(acc.setdefault(t["chain"], {}), red)
        key = json.dumps({k: p.get(k) for k in ("job", "array_job", "array_task", "host", "omp", "mkl",
                                                  "numba_threads", "block", "python", "numpy", "scipy", "numba",
                                                  "blas_config_sha")}, sort_keys=True)
        producers[key] = producers.get(key, 0) + 1
    t0 = time.time()
    res = assemble5.compute(a.Lmax, NMAX, chains=acc, verbose=True, block=a.block)
    ser = Series5(a.Lmax)
    ev = windows5.compute(a.Lmax, res, ser)
    out = assemble5.masked(res, NMAX)
    for k, v in ev.items():
        out["even_" + k] = np.asarray(v)
    check_finite(out, a.Lmax)
    prov = dict(numerics_sha=sha, snapshot_sha=snapshot_sha(), Lmax=a.Lmax, ntasks=len(tasks),
                catalogue_sha256=str(res["catalogue_sha256"]), cache=os.path.abspath(a.cache),
                assembly=exec_env(), producers=[dict(json.loads(k), ntasks=v) for k, v in sorted(producers.items())],
                snapshot_manifest={f: file_sha256(os.path.join(HERE, f)) for f in snapshot_files()},
                assembled=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    out["provenance"] = np.array(json.dumps(prov))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    np.savez(a.out, **out)
    print(f"# assembled in {time.time() - t0:.1f}s -> {a.out}", flush=True)
    for L in (2, 8, 16, 32, 64, 92, 118, 160, 240, 320, 400, 500):
        if L <= a.Lmax:
            i = L // 2 - 1
            print(f"L={L:5d} C5raw={ev['C5raw'][i]:.12f} C5Dconn={ev['C5Dconn'][i]:.12f} "
                  f"dC5={ev['dC5_Dconn'][i]:.12f} C4Dconn={ev['C4Dconn'][i]:.12f}", flush=True)


def cmd_bench(a):
    import resource
    tasks = task_list(a.Lmax)
    w = worst_task(a.Lmax, tasks)
    t = w if a.worst else tasks[a.task]
    _init(a.Lmax, a.block)
    t0 = time.time()
    red, nkeys = _compute_task(t)
    dt = time.time() - t0
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_gb = rss / 2 ** 20 if sys.platform != "darwin" else rss / 2 ** 30
    print(json.dumps(dict(Lmax=a.Lmax, task=("worst" if a.worst else a.task), chain=repr(t["chain"]), spec=t["spec"],
                          spec_sha=hashlib.sha256(t["spec"].encode()).hexdigest(), worst_case=(t["id"] == w["id"]),
                          seconds=round(dt, 2), peak_rss_GB=round(rss_gb, 3), block=a.block, keys=nkeys,
                          threads=os.environ.get("OMP_NUM_THREADS"), host=platform.node(),
                          snapshot_sha=snapshot_sha())), flush=True)


def cmd_list(a):
    tasks = task_list(a.Lmax)
    from collections import Counter
    print(f"# {len(tasks)} tasks, total cost units {sum(t['cost'] for t in tasks):.3e}")
    print(Counter(len(t["chain"][0]) for t in tasks))


def cmd_sha(a):
    print(numerics_sha() if a.kind == "numerics" else snapshot_sha())


def cmd_worstspec(a):
    """sha256 of the designated worst-case task spec at Lmax (checked by slurm/submit.sh against bench records)."""
    print(hashlib.sha256(worst_task(a.Lmax)["spec"].encode()).hexdigest())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("run", "assemble", "list", "bench", "sha", "worstspec"))
    ap.add_argument("--Lmax", type=int, default=None)
    ap.add_argument("--kind", default="snapshot", choices=("numerics", "snapshot"))
    ap.add_argument("--cache", default=None)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--part", type=int, default=0)
    ap.add_argument("--nparts", type=int, default=1)
    ap.add_argument("--block", type=int, default=8)
    ap.add_argument("--out", default=None)
    ap.add_argument("--task", type=int, default=0)
    ap.add_argument("--worst", action="store_true", help="bench the designated worst-case task (A7a sizing)")
    a = ap.parse_args()
    if a.cmd not in ("sha",) and (a.Lmax is None or a.Lmax < 2):
        ap.error("--Lmax >= 2 is required")
    if a.block < 1 or a.workers < 1 or a.nparts < 1 or not 0 <= a.part < a.nparts or a.task < 0:
        ap.error("need --block >= 1, --workers >= 1, --nparts >= 1, 0 <= --part < --nparts, --task >= 0")
    {"run": cmd_run, "assemble": cmd_assemble, "list": cmd_list, "bench": cmd_bench, "sha": cmd_sha,
     "worstspec": cmd_worstspec}[a.cmd](a)


if __name__ == "__main__":
    main()
