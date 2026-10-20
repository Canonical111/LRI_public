"""Driver: independent solver vs production records (fixed couplings) and independent re-tuning.

usage: python run_check.py RECORDS_DIR OUT_DIR NWORKERS [--only PATTERN] [--followup]
Each task writes OUT_DIR/<task id>.json atomically; existing outputs are skipped (resume).
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import json
import sys
import time
import traceback
from multiprocessing import Pool

import numpy as np

XS = ["0.125", "0.126", "0.135", "0.150", "0.175", "0.200", "0.250", "0.300", "0.350", "0.400", "0.450",
      "0.475", "0.495"]
STRONG = ["0.125", "0.126", "0.135", "0.150"]


def tasks(followup=False):
    T = []
    if followup:
        # strong coupling at large L with a converged local basis (K=24 is not converged there)
        for xs in STRONG:
            for L in (18, 20):
                T.append(dict(kind="fixed", x=xs, L=L, K=(32, 32), J=()))
        for xs in ("0.125", "0.126"):
            T.append(dict(kind="fixed", x=xs, L=22, K=(32, 32), J=()))
        T.append(dict(kind="fixed", x="0.125", L=18, K=(40, 40), J=()))
        T.append(dict(kind="fixed", x="0.175", L=20, K=(32, 32), J=()))
    if followup:
        for t in T:
            t.setdefault("M", 400)
            t["id"] = f"{t['kind']}_x{t['x']}_L{t['L']}_K{t['K'][0]}-{t['K'][1]}_M{t['M']}" + ("_J" if t["J"] else "")
        T.sort(key=lambda t: (t["L"], sum(t["K"])), reverse=True)
        return T
    for xs in XS:
        for L in (8, 10, 12):
            T.append(dict(kind="fixed", x=xs, L=L, K=(24, 24), J=(1, 2)))
        T.append(dict(kind="fixed", x=xs, L=14, K=(24, 24), J=(1, 2)))
        T.append(dict(kind="fixed", x=xs, L=16, K=(24, 24), J=()))
        T.append(dict(kind="fixed", x=xs, L=18, K=(24, 24), J=()))
        T.append(dict(kind="fixed", x=xs, L=12, K=(32, 32), J=()))
        T.append(dict(kind="fixed", x=xs, L=16, K=(32, 32), J=()))
        for L in (8, 12):
            T.append(dict(kind="tune", x=xs, L=L, K=(24, 24), J=()))
    for xs in STRONG:
        T.append(dict(kind="fixed", x=xs, L=16, K=(40, 40), J=()))
        T.append(dict(kind="fixed", x=xs, L=12, K=(48, 48), J=()))
    T.append(dict(kind="fixed", x="0.125", L=12, K=(32, 32), J=(), M=700))
    for xs in ("0.125", "0.250"):
        T.append(dict(kind="fixed", x=xs, L=20, K=(24, 24), J=()))
        T.append(dict(kind="tune", x=xs, L=16, K=(24, 24), J=()))
    for t in T:
        t.setdefault("M", 400)
        t["id"] = f"{t['kind']}_x{t['x']}_L{t['L']}_K{t['K'][0]}-{t['K'][1]}_M{t['M']}" + ("_J" if t["J"] else "")
    # rough cost model: bath size grows ~2.8x per DeltaL=2; tuning ~ 12 residual evaluations
    def cost(t):
        c = 2.8 ** ((t["L"] - 8) / 2) * (sum(t["K"]) / 48) ** 2
        return c * (12 if t["kind"] == "tune" else 1) * (3 if t["J"] else 1)
    T.sort(key=cost, reverse=True)
    return T


def record(rdir, xs, L, nz=16):
    p = os.path.join(rdir, f"x{xs}", f"L{L}_z{nz}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def run(args):
    t, rdir, odir = args
    out_path = os.path.join(odir, t["id"] + ".json")
    if os.path.exists(out_path):
        return t["id"], "skip"
    from indep_ht2d import Bath, solve_spectrum, tune
    t0 = time.time()
    try:
        rec = record(rdir, t["x"], t["L"])
        x = float(t["x"])
        Ke, Ko = t["K"]
        bath = Bath(t["L"], x)
        res = dict(task=t, host=os.uname().nodename, bath_nb=bath.nb)
        eig_tol = 1e-14 if t["L"] <= 14 else 1e-13
        if t["kind"] == "fixed":
            o = solve_spectrum(x, rec["theta"], t["L"], M=t["M"], Ke=Ke, Ko=Ko, nev=5, bath=bath, extraJ=tuple(t["J"]),
                               eig_tol=eig_tol)
        else:
            # independent seed: shift both coordinates away from the production root
            seed = np.array(rec["theta"]) + np.array([0.05, -0.05])
            th, R, hist = tune(x, seed, t["L"], bath=bath, M=t["M"], Ke=Ke, Ko=Ko, eig_tol=eig_tol)
            o = solve_spectrum(x, th, t["L"], M=t["M"], Ke=Ke, Ko=Ko, nev=5, bath=bath, eig_tol=eig_tol)
            res.update(seed=seed.tolist(), theta_tuned=th.tolist(), tune_residual=R.tolist(), tune_history=hist)
        o["Ev"] = {str(k): v for k, v in o["Ev"].items()}
        o["D"] = {str(k): v for k, v in o["D"].items()}
        o["fp_iters"] = {str(k): v for k, v in o["fp_iters"].items()}
        res["indep"] = o
        res["records"] = {}
        for nz in (12, 16, 20):
            r = record(rdir, t["x"], t["L"], nz)
            if r is None:
                continue
            res["records"][str(nz)] = dict(theta=r["theta"], Delta_thermal=r["Delta_thermal"], even=r["even_gaps"],
                                           odd=r["odd_gaps"], Ev=r["window_correction"]["Ev"],
                                           angular=r.get("diagnostics", {}).get("angular_spectra"),
                                           record_sha256=r.get("record_sha256"))
        res["seconds"] = time.time() - t0
        import resource
        res["maxrss_gib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20
        tmp = out_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(res, f)
        os.replace(tmp, out_path)
        return t["id"], f"ok {res['seconds']:.0f}s"
    except Exception:
        err = traceback.format_exc()
        with open(os.path.join(odir, t["id"] + ".err"), "w") as f:
            f.write(err)
        return t["id"], "FAILED " + err.splitlines()[-1]


if __name__ == "__main__":
    rdir, odir, nw = sys.argv[1], sys.argv[2], int(sys.argv[3])
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    os.makedirs(odir, exist_ok=True)
    T = [t for t in tasks(followup="--followup" in sys.argv) if only is None or only in t["id"]]
    print(f"{len(T)} tasks, {nw} workers", flush=True)
    with Pool(nw, maxtasksperchild=1) as pool:
        for tid, status in pool.imap_unordered(run, [(t, rdir, odir) for t in T]):
            print(time.strftime("%H:%M:%S"), tid, status, flush=True)
    print("done", flush=True)
