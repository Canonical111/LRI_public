#!/usr/bin/env python3
"""
run_config.py -- run one configuration of SPEC section 7 and write <outdir>/<id>.json.

Usage
    python run_config.py c1                      # writes <this dir>/out/c1.json
    python run_config.py c6 --outdir $WORK/out
    python run_config.py toy                     # small local smoke test (Lambda=3, s=0.8, K=16, n_b=6, N=30)
    python run_config.py mytest --dsigma 0.1 --Lambda 3 --K 16 --nb 6 --N 30   # any custom id

Works from any working directory (imports indep_nrg from its own directory).  Progress lines are
printed with flush=True.  Exit status: 0 = ok, 2 = critical search failed (JSON still written).
"""

import argparse
import contextlib
import datetime
import hashlib
import io
import json
import math
import os
import platform
import socket
import sys
import time
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mpmath                       # noqa: E402
import numpy as np                  # noqa: E402
import scipy                        # noqa: E402

import indep_nrg as nrg             # noqa: E402

# id: (Delta_sigma, Lambda, K, n_b, N)    [SPEC 7]; s = 1 - 2 Delta_sigma
CONFIGS = {
    "c1": ("0.1", "3", 64, 10, 65),
    "c2": ("0.05", "3", 64, 10, 80),
    "c3": ("0.01", "3", 64, 10, 105),
    "c4": ("0.2", "3", 64, 12, 65),
    "c5": ("0.249", "3", 64, 16, 65),
    "c6": ("0.001", "3", 48, 10, 250),
    "c7": ("0.1", "2", 64, 10, 103),
    "c8": ("0.15", "2.5", 64, 10, 78),
    # local smoke tests (not part of SPEC 7)
    "toy": ("0.1", "3", 16, 6, 30),
    "toy40": ("0.1", "3", 16, 6, 40),     # long enough to show quality windows
}


def s_from_dsigma(dsigma: str) -> str:
    """s = 1 - 2 Delta_sigma as an exact decimal string, rounded to 6 decimals (e.g. '0.502')."""
    s = (Decimal(1) - 2 * Decimal(dsigma)).quantize(Decimal("0.000001"))
    return format(s.normalize(), "f")


def jsonable(x):
    """Convert numpy containers/scalars to plain JSON types; non-finite floats become null."""
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return jsonable(x.tolist())
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        f = float(x)
        return f if math.isfinite(f) else None
    return x


def sha256_of(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


def environment():
    info = {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "hostname": socket.gethostname(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "mpmath": mpmath.__version__,
        "mpmath_backend": mpmath.libmp.BACKEND,
        "env": {k: os.environ.get(k) for k in (
            "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "SLURM_JOB_ID",
            "SLURM_JOB_NODELIST", "SLURMD_NODENAME")},
        "code_sha256": {f: sha256_of(os.path.join(HERE, f))
                        for f in ("indep_nrg.py", "run_config.py", "selftest.py")},
    }
    try:
        cfg = np.show_config(mode="dicts")
        info["numpy_build_dependencies"] = cfg.get("Build Dependencies")
    except Exception:                                   # older numpy: capture the text dump
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            np.show_config()
        info["numpy_show_config_text"] = buf.getvalue()
    try:
        import threadpoolctl
        info["threadpoolctl"] = threadpoolctl.threadpool_info()
    except Exception:
        info["threadpoolctl"] = None
    return info


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id", help="configuration id (c1..c8, toy) or a custom id with all overrides")
    ap.add_argument("--outdir", default=os.path.join(HERE, "out"))
    ap.add_argument("--dsigma")
    ap.add_argument("--Lambda")
    ap.add_argument("--K", type=int)
    ap.add_argument("--nb", type=int)
    ap.add_argument("--N", type=int)
    ap.add_argument("--no-chain-check", action="store_true",
                    help="skip the chain convergence check (M+40, dps+40)")
    args = ap.parse_args(argv)

    if args.id in CONFIGS:
        dsigma, Lam, K, nb, N = CONFIGS[args.id]
    else:
        dsigma = Lam = K = nb = N = None
    dsigma = args.dsigma if args.dsigma is not None else dsigma
    Lam = args.Lambda if args.Lambda is not None else Lam
    K = args.K if args.K is not None else K
    nb = args.nb if args.nb is not None else nb
    N = args.N if args.N is not None else N
    if None in (dsigma, Lam, K, nb, N):
        ap.error("unknown id %r: give --dsigma --Lambda --K --nb --N" % args.id)
    s = s_from_dsigma(dsigma)

    T0 = time.perf_counter()

    def log(msg):
        print("[%s %9.1fs] %s" % (args.id, time.perf_counter() - T0, msg), flush=True)

    log("start %s: Delta_sigma=%s s=%s Lambda=%s K=%d n_b=%d N=%d Delta=%g  host=%s"
        % (args.id, dsigma, s, Lam, K, nb, N, nrg.DELTA_DEFAULT, socket.gethostname()))
    started = datetime.datetime.now().isoformat(timespec="seconds")

    res = nrg.run_pipeline(Lam, s, K, nb, N, convergence_check=not args.no_chain_check, log=log)

    out = {
        "id": args.id,
        "config": {"Delta_sigma": dsigma, "s": s, "Lambda": Lam, "K": K, "n_b": nb, "N": N,
                   "Delta": nrg.DELTA_DEFAULT},
        "started": started,
        "finished": datetime.datetime.now().isoformat(timespec="seconds"),
        "wall_seconds": time.perf_counter() - T0,
        "environment": environment(),
    }
    out.update(res)
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "%s.json" % args.id)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(jsonable(out), fh, indent=1, allow_nan=False)
    os.replace(tmp, path)
    log("wrote %s  (status %s)" % (path, res.get("status")))
    return 0 if res.get("status") == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
