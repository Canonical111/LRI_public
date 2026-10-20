"""Signed-residual valley scan for the L=24 strong-coupling tuning problem (diagnostic only).

For each theta0 in THETA0S: secant in theta1 until the shadow condition f2 = E_chi - E_vac - (2-x) = 0
(well conditioned), then record the signed sigma condition f1 = E_sigma - E_vac - x there.
A sign change of f1(theta0) along f2 = 0 brackets a root; a strictly positive (or negative) minimum
of |f1| means the tuning conditions have no solution near this branch.

Uses the frozen release code unchanged (DensitySolver.spectrum, the same residual as the point driver).
usage: python -E -s scan_valley.py RELEASE_CODE_DIR BASIS_JSON X L THREADS OUT_JSON THETA0 THETA1_GUESS [THETA0 THETA1_GUESS ...]
"""
import hashlib
import json
import os
import sys
import time

for k in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[k] = "1"
code, basis, x, L, threads, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
pairs = [(float(a), float(b)) for a, b in zip(sys.argv[7::2], sys.argv[8::2])]
os.environ.setdefault("NUMBA_NUM_THREADS", str(threads))
sys.path.insert(0, code)
import numpy as np  # noqa: E402
from numba import set_num_threads  # noqa: E402
from threadpoolctl import threadpool_limits  # noqa: E402
from ht2d.density import DensitySolver  # noqa: E402

set_num_threads(threads)
raw = open(basis, "rb").read()
art = json.loads(raw)["basis_artifact"]
prov = dict(code=code, basis_sha256=hashlib.sha256(raw).hexdigest(), job=os.environ.get("SLURM_JOB_ID"),
            host=os.uname().nodename, threads=threads, f2_tol=1e-9)
u = np.asarray(art["isometry"], np.float64)
cap = u.shape[1] // 2
nz = 16
u = u[:, list(range(nz)) + list(range(cap, cap + nz))]
kw = dict(window="vacuum", window_mode="consistent", backend="tensor", ncv=40, eig_tol=1e-12, residual_tol=1e-8,
          max_eig_iter=10000, max_bath_states=10243736, max_basis_bytes=int(56 * 1024**3 / 4))
rows = []


def save():
    tmp = out + ".tmp"
    json.dump(dict(x=x, L=L, nz=nz, basis=basis, provenance=prov, rows=rows), open(tmp, "w"), indent=1)
    os.replace(tmp, out)


with threadpool_limits(limits=1, user_api="blas"):
    s = DensitySolver(L, u, art["scale"], **kw)
    s.set_delta(x)

    def f(t0, t1):
        t = time.time()
        r, _, spec, _ = s.spectrum(np.array([t0, t1]), k=3)
        row = dict(theta=[t0, t1], f1=float(r[0]), f2=float(r[1]), E_even=spec[0][0].tolist(), E_odd=spec[1][0].tolist(),
                   seconds=time.time() - t)
        rows.append(row)
        save()
        print(json.dumps(row), flush=True)
        return r

    for t0, t1 in pairs:
        # secant on theta1 for f2 = 0 (d f2/d theta1 ~ -2.5 at L=24; start with a 0.002 step)
        a, fa = t1, f(t0, t1)[1]
        b = t1 - fa / -2.5
        fb = f(t0, b)[1]
        for _ in range(4):
            if abs(fb) < 1e-9:
                break
            c = b - fb * (b - a) / (fb - fa)
            a, fa = b, fb
            b, fb = c, f(t0, c)[1]
        rows.append(dict(theta0=t0, theta1_on_f2_zero=b, f2=fb, f1_on_curve=rows[-1]["f1"], summary=True))
        save()
        print("SUMMARY", json.dumps(rows[-1]), flush=True)
