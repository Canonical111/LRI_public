"""Shared helpers of the public tools of HT_Pert/code/lri_d1_fullblock_tail_response (public/ overlay).

The package itself ships verbatim (OpenAI GPT-6 astra, delivered 2026-10-07) and is bound by its own
MANIFEST.sha256 (108 files). Its scripts rewrite files under results/ when they run, so every rerun here happens on a
copy of the package made under the work directory; nothing writes into the shipped tree.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
NAME = "lri_d1_fullblock_tail_response"
THREAD_ENV = {"OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
              "MPLBACKEND": "Agg", "PYTHONDONTWRITEBYTECODE": "1"}


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def scrubbed():
    """Package-relative paths listed in public/SCRUBBED.txt (written by the maintainer's placeholder scrub)."""
    p = os.path.join(HERE, "SCRUBBED.txt")
    if not os.path.exists(p):
        return set()
    return {ln.strip() for ln in open(p, encoding="utf-8") if ln.strip() and not ln.startswith("#")}


def verify_manifest(root=PKG):
    """Check MANIFEST.sha256 against the files under root. Files listed in public/SCRUBBED.txt may differ.

    Returns (n_entries, n_identical, scrubbed_names, failures)."""
    scr = scrubbed()
    rroot = os.path.realpath(root)
    n = ok = 0
    sc, bad = [], []
    for line in open(os.path.join(root, "MANIFEST.sha256"), encoding="utf-8").read().splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        p = os.path.realpath(os.path.join(root, name))
        n += 1
        inside = p.startswith(rroot + os.sep)
        if inside and os.path.isfile(p) and sha256(p) == digest:
            ok += 1
        elif inside and name in scr and os.path.isfile(p):
            sc.append(name)
        else:
            bad.append(name)
    return n, ok, sc, bad


def copy_tree(dst):
    """Fresh copy of the shipped package at dst (without public/, public.mk, caches and the work directory)."""
    dst = os.path.abspath(dst)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    skip_top = {"public", "public.mk", ".work", ".public_out"}

    def ignore(d, names):
        out = {x for x in names if x in ("__pycache__", ".pytest_cache", ".DS_Store")}
        if os.path.abspath(d) == os.path.abspath(PKG):
            out |= {x for x in names if x in skip_top}
        out |= {x for x in names if os.path.abspath(os.path.join(d, x)) == dst
                or dst.startswith(os.path.abspath(os.path.join(d, x)) + os.sep)}
        return out

    shutil.copytree(PKG, dst, ignore=ignore)
    return dst


def run_py(args, cwd, timeout=None):
    """Run `python args...` in cwd with single-threaded BLAS; returns (returncode, stdout, stderr, seconds)."""
    t0 = time.perf_counter()
    p = subprocess.run([sys.executable] + list(args), cwd=cwd, capture_output=True, text=True,
                       env=dict(os.environ, **THREAD_ENV), timeout=timeout)
    return p.returncode, p.stdout, p.stderr, time.perf_counter() - t0


def longdouble_bits():
    import numpy as np
    return int(np.finfo(np.longdouble).nmant)
