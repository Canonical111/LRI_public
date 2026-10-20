#!/usr/bin/env python3
"""A8: measure the large-cutoff tail of the exact C4(Lambda) (PLAN sec. 8).

Model:  C4(L) = A + beta log L + sum_{(j,k) in basis} c_jk L^{-j/2} (log L)^k, even L in [lo, hi].
The leading log is a model choice, never an assumption: --logs selects among
  none  : beta = 0                         (for Dconn: the hypothesis that the complete-window C4 converges)
  free  : beta fitted                      (diagnostic for both schemes)
  fixed : beta = -1/17496                  (raw only: the hypothesis beta_Dconn = 0 combined with the exact window
                                            identity beta_Dconn - beta_raw = 1/17496 from dC4_g2D ~ log L/17496)
Least squares in mpmath (60 digits); every fit reports rank, the condition number of the column-scaled design and the
max residual.  Coefficients are kept as 50-digit strings and predictions are evaluated in mpmath with the same
coefficients (only the finished predictions are converted to float64).

Blind-prediction protocol (three separate commands):
  freeze  : fits on a result whose even grid ends exactly at --hi (a file containing L > hi is refused), records the
            input sha256, the fit-code sha256 and the result's provenance, predicts hi < L <= --predict-to, writes the
            record and its sha256 with exclusive creation (an existing record is never replaced).  It prints the
            fitted intercepts but no comparison with any reference value.
  compare : only for a frozen, hash-verified record: intercepts minus the known C4 = 45.42488010356 (a test value,
            never an input).
  check   : frozen, hash-verified record vs a larger result: requires every predicted cutoff to be present and finite
            (else FAIL; --allow-partial reports the coverage explicitly), keeps (L, error) pairs together.
  explore : non-blind fits on any data (exploration only; marked as such).

usage:
  python3 fits/fits_c4_1d.py freeze  --npz results/c4_1d_L1000.npz --hi 1000 --lo 100,200,300 --scheme Dconn
                                      --logs none,free --predict-to 2000 --out fits/frozen_L1000_Dconn.json
  python3 fits/fits_c4_1d.py compare --frozen fits/frozen_L1000_Dconn.json
  python3 fits/fits_c4_1d.py check   --frozen fits/frozen_L1000_Dconn.json --npz results/c4_1d_L2000.npz
  python3 fits/fits_c4_1d.py explore --npz results/c4_1d_L400.npz --hi 400 --lo 100 --scheme raw --logs fixed,free"""
import argparse
import hashlib
import json
import math
import os
import sys

import mpmath as mp
import numpy as np

mp.mp.dps = 60
C4_EXACT = 45.42488010356   # test value only (four-loop closed form), used only by `compare`
LOG_FIXED = -1.0 / 17496

BASES = {
    # name: list of (j, k) columns  L^{-j/2} log^k L
    "P4": [(1, 0), (2, 0), (3, 0), (4, 0)],
    "P6": [(j, 0) for j in range(1, 7)],
    "L1": [(1, 0), (1, 1), (2, 0), (2, 1), (3, 0), (3, 1), (4, 0)],
    "L2": [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2), (3, 0), (3, 1), (4, 0)],
    "L3": [(1, 0), (1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2), (2, 3), (3, 0), (3, 1), (3, 2), (4, 0), (4, 1)],
    "L2x": [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2), (3, 0), (3, 1), (3, 2), (4, 0), (4, 1), (5, 0), (6, 0)],
}


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load(npz, scheme):
    d = np.load(npz)
    L = d["even_L"].astype(int)
    y = d["even_C4Dconn"] if scheme == "Dconn" else d["even_C4raw"]
    if not np.all(np.isfinite(y)) or not np.array_equal(L, np.arange(2, L[-1] + 1, 2)):
        raise SystemExit(f"{npz}: incomplete or non-finite even grid")
    return L, y, json.loads(str(d["provenance"]))


def design(L, cols, log):
    rows = []
    for x in L:
        lx = mp.log(x)
        r = [mp.mpf(1)]
        if log == "free":
            r.append(lx)
        for j, k in cols:
            r.append(mp.power(x, -mp.mpf(j) / 2) * lx ** k)
        rows.append(r)
    return mp.matrix(rows)


def lstsq(A, b):
    """Column-scaled least squares via QR at mp.dps; returns coefficients, condition number, rank estimate."""
    m, n = A.rows, A.cols
    s = [mp.sqrt(mp.fsum(A[i, j] ** 2 for i in range(m))) for j in range(n)]
    As = mp.matrix(m, n)
    for i in range(m):
        for j in range(n):
            As[i, j] = A[i, j] / s[j]
    Q, R = mp.qr(As)
    diag = [abs(R[j, j]) for j in range(n)]
    rank = sum(1 for v in diag if v > mp.mpf(10) ** (-40) * max(diag))
    qtb = Q.T * b
    x = mp.lu_solve(R[:n, :n], qtb[:n])
    sv = mp.svd_r(As, compute_uv=False)
    cond = max(sv) / min(sv)
    return [x[j] / s[j] for j in range(n)], cond, rank


def fit_one(L, y, lo, hi, cols, log):
    sel = [(int(a), float(b)) for a, b in zip(L, y) if lo <= a <= hi]
    Ls = [a for a, _ in sel]
    b = mp.matrix([mp.mpf(v) - (mp.log(a) / -17496 if log == "fixed" else 0) for a, v in sel])
    A = design(Ls, cols, log)
    coef, cond, rank = lstsq(A, b)
    res = A * mp.matrix(coef) - b
    out = dict(n=len(Ls), coef=[mp.nstr(c, 50) for c in coef], cond=float(cond), rank=rank, ncol=A.cols,
               maxres=float(max(abs(r) for r in res)), A=float(coef[0]))
    out["beta"] = float(coef[1]) if log == "free" else (LOG_FIXED if log == "fixed" else 0.0)
    return out


def predict(r, cols, log, Lp):
    """Model values at Lp from the stored high-precision coefficients, evaluated in mpmath."""
    c = [mp.mpf(v) for v in r["coef"]]
    out = []
    for x in Lp:
        lx = mp.log(x)
        v = c[0]
        i = 1
        if log == "free":
            v += c[1] * lx
            i = 2
        elif log == "fixed":
            v += mp.mpf(1) / -17496 * lx
        v += mp.fsum(cc * mp.power(x, -mp.mpf(j) / 2) * lx ** k for (j, k), cc in zip(cols, c[i:]))
        out.append(float(v))
    return out


def run_fits(L, y, a):
    logs = a.logs.split(",")
    for lg in logs:
        if lg not in ("none", "free", "fixed") or (lg == "fixed" and a.scheme != "raw"):
            raise SystemExit(f"log option {lg} not allowed for scheme {a.scheme}")
    rows = []
    for name in a.bases.split(","):
        for lg in logs:
            for lo in [int(v) for v in a.lo.split(",")]:
                r = fit_one(L, y, lo, a.hi, BASES[name], lg)
                r.update(basis=name, log=lg, lo=lo, hi=a.hi)
                rows.append(r)
                print(f"{name:4s} log={lg:5s} lo={lo:4d} n={r['n']:4d} cols={r['ncol']:2d} rank={r['rank']:2d} "
                      f"cond={r['cond']:.1e} maxres={r['maxres']:.1e}  A={r['A']:.10f} beta={r['beta']:+.3e}",
                      flush=True)
    return rows


def cmd_freeze(a):
    L, y, prov = load(a.npz, a.scheme)
    if L[-1] != a.hi:
        raise SystemExit(f"freeze needs a result whose even grid ends at --hi {a.hi} (file ends at {L[-1]}): "
                         "use the Lmax = hi production result, never a larger one")
    if not a.predict_to or a.predict_to < a.hi + 2:
        raise SystemExit("freeze needs --predict-to >= --hi + 2 (a non-empty even prediction grid)")
    rows = run_fits(L, y, a)
    Lp = list(range(a.hi + 2, a.predict_to + 1, 2))
    for r in rows:
        r["pred"] = predict(r, BASES[r["basis"]], r["log"], Lp)
    rec = dict(kind="frozen blind fit", npz=os.path.abspath(a.npz), npz_sha256=sha256_file(a.npz),
               fit_code_sha256=sha256_file(os.path.abspath(__file__)), provenance_snapshot=prov.get("snapshot_sha"),
               scheme=a.scheme, hi=a.hi, predict_L=Lp, fits=rows)
    txt = json.dumps(rec, sort_keys=True)
    fd = os.open(a.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)     # never replace a frozen record
    with os.fdopen(fd, "w") as fh:
        fh.write(txt)
    h = hashlib.sha256(txt.encode()).hexdigest()
    fd = os.open(a.out + ".sha256", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(fd, "w") as fh:
        fh.write(h + "\n")
    print(f"# frozen {a.out} sha256 {h} (input sha256 {rec['npz_sha256'][:16]}..)")


def load_frozen(path):
    txt = open(path).read()
    h = hashlib.sha256(txt.encode()).hexdigest()
    stored = open(path + ".sha256").read().split()[0]
    if h != stored:
        raise SystemExit(f"frozen record hash mismatch ({h} != {stored})")
    return json.loads(txt)


def cmd_compare(a):
    P = load_frozen(a.frozen)
    print(f"# frozen record {a.frozen} (scheme {P['scheme']}, hi {P['hi']}); exact C4 = {C4_EXACT}")
    for r in P["fits"]:
        print(f"{r['basis']:4s} log={r['log']:5s} lo={r['lo']:4d}: A = {r['A']:.10f}   A - C4 = {r['A'] - C4_EXACT:+.3e}"
              f"   beta = {r['beta']:+.3e}")


def cmd_check(a):
    P = load_frozen(a.frozen)
    L, y, _ = load(a.npz, P["scheme"])
    val = dict(zip(L.tolist(), y.tolist()))
    pL = P["predict_L"]
    have = [x for x in pL if x in val]
    if not pL or not have:
        raise SystemExit(f"FAIL: no holdout cutoffs available (predicted {len(pL)}, present in {a.npz}: 0)")
    if len(have) < len(pL):
        msg = f"holdout coverage {len(have)}/{len(pL)} (missing L > {max(have) if have else P['hi']})"
        if not a.allow_partial:
            raise SystemExit("FAIL: " + msg)
        print("# PARTIAL " + msg)
    for r in P["fits"]:
        if len(r["pred"]) != len(pL) or not all(math.isfinite(v) for v in r["pred"]):
            raise SystemExit(f"FAIL: malformed predictions for {r['basis']}/{r['log']}/{r['lo']}")
        pairs = [(x, p - val[x]) for x, p in zip(pL, r["pred"]) if x in val]
        xw, dw = max(pairs, key=lambda t: abs(t[1]))
        print(f"{r['basis']:4s} log={r['log']:5s} lo={r['lo']:4d}: blind max |d| {abs(dw):.2e} at L={xw}; "
              f"d(L={pairs[-1][0]}) {pairs[-1][1]:+.2e}")


def cmd_explore(a):
    L, y, _ = load(a.npz, a.scheme)
    print(f"# EXPLORATION (not blind): {a.npz} scheme {a.scheme}, even L in [lo, {a.hi}]")
    run_fits(L, y, a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("freeze", "compare", "check", "explore"))
    ap.add_argument("--npz")
    ap.add_argument("--scheme", default="Dconn", choices=("Dconn", "raw"))
    ap.add_argument("--logs", default=None)
    ap.add_argument("--hi", type=int, default=None)
    ap.add_argument("--lo", default="100,200,300")
    ap.add_argument("--bases", default=",".join(BASES))
    ap.add_argument("--predict-to", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--frozen", default=None)
    ap.add_argument("--allow-partial", action="store_true")
    a = ap.parse_args()
    if a.logs is None:
        a.logs = "none,free" if a.scheme == "Dconn" else "fixed,free"
    {"freeze": cmd_freeze, "compare": cmd_compare, "check": cmd_check, "explore": cmd_explore}[a.cmd](a)


if __name__ == "__main__":
    main()
