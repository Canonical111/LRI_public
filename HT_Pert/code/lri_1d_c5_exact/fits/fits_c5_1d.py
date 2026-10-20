#!/usr/bin/env python3
"""A8: measure the large-cutoff tail of the exact C5(Lambda) (PLAN A8); adapted from lri_1d_c4_exact/fits/fits_c4_1d.py.

Model:  C5(L) = A + beta log L + sum_{(j,k) in basis} c_jk L^{-j/2} (log L)^k, even L in [lo, hi], fitted to the
result's even_C5Dconn (--scheme Dconn) or even_C5raw (--scheme raw).  No exact analogue of the C4 leading log
-1/17496 is known at eps^5, so the leading log is a free model choice in both schemes (--logs):
  none : beta = 0
  free : beta fitted
Bases (BASES): P4, P6, L1, L2 of the C4 script (for comparison) and the eps^5 bases with L^{-1/2} log^3 L,
  M3 = L2 + (1, 3),  M3x = M3 + (2, 3).
Least squares in mpmath (60 digits); every fit reports n, rank, the condition number of the column-scaled design,
the max residual, A, beta and c11, the fitted coefficient of L^{-1/2} log L (input of the omega3 diagnostic of PLAN
A8; 'n/a' for a basis without that column).  Coefficients are kept as 50-digit strings with their column labels,
and predictions are evaluated in mpmath from those strings (only the finished predictions are converted to float64).

Blind-prediction protocol (three separate commands):
  freeze  : fits on a result whose even grid ends exactly at --hi (a file containing L > hi is refused: the input is
            restricted to the training range), records the input sha256, the fit-code sha256 and the result's
            provenance snapshot and the result's passing gate record (results/<sha12>/gates_L<hi>.txt bound to the input's
            sha256; refused otherwise), predicts hi < L <= --predict-to, and writes the record and its sha256 with exclusive
            creation (an existing record is never replaced; refused before any fit).  It prints the fitted intercepts
            but no comparison with any reference value.
  compare : only for a frozen, hash-verified record: intercepts minus the known C5 = -731.1394766245398 (a test value,
            never an input).
  check   : frozen, hash-verified record vs a larger result: every predicted cutoff must be present and finite (else
            FAIL; --allow-partial reports the coverage explicitly); (L, error) pairs are kept together.
  explore : non-blind fits on any data (exploration only; marked as such).

omega3 diagnostic (PLAN A8; scheme raw only): following the joint thermal model
(lri_hpc_Hamitonian/analysis/extended/analyze_joint.py, ThermalModel with free exponent), the e-series offsets of the
lower orders are subtracted with weights w1 = 3.5, w2 = -5A + 1/54 (raw gap model, A = pi + 4 log 2) and w3 = 0:
    Y(L) = C5raw(L) + e1 (C4(L) - C4) + e2 (C3(L) - C3) + e3' (C2(L) - C2),   e = eseries(L, {1: w1, 2: w2, 3: 0}),
with the exact raw C2..C4(L) of the pinned C4P production result (sha256 C4P_SHA256; the training range only) and the
known limits C2 = A/9, C3, C4 (inputs/ht_data.json "known"); then Y is fitted with columns 1, x = C2(L) - C2, -log(L) x
and the joint model's tail terms (MODELS_JOINT).  The fitted coefficient of -log(L) x is the effective omega3, compared
with the gap-fit value OMEGA3_REF = 556.214401533541 (extended_summary.json, raw model A, lo 16) only by `compare`.

usage:
  python3 fits/fits_c5_1d.py freeze  --npz results/<sha12>/c5_1d_L320.npz --hi 320 --lo 80,120,160 --scheme Dconn
                                      --logs none,free --predict-to 400 --out fits/frozen/frozen_L320_Dconn.json
  python3 fits/fits_c5_1d.py compare --frozen fits/frozen/frozen_L320_Dconn.json
  python3 fits/fits_c5_1d.py check   --frozen fits/frozen/frozen_L320_Dconn.json --npz results/<sha12>/c5_1d_L400.npz
  python3 fits/fits_c5_1d.py explore --npz results/<sha12>/c5_1d_L400.npz --lo 80 --scheme raw --bases M3,M3x"""
import argparse
import hashlib
import json
import math
import os

import mpmath as mp
import numpy as np

mp.mp.dps = 60
C5_EXACT = -731.1394766245398   # test value only (five-loop result), used only by `compare`
HERE = os.path.dirname(os.path.abspath(__file__))
C4P_NPZ = "/mnt/beegfs/zzheng1/lri_1d_c4/results/a8b57b2e8475/c4_1d_L2000.npz"
C4P_SHA256 = "62720cf5ac097f5e7f93250bc38e592c4de269b703abb5dd2544fb53994b51d2"
OMEGA3_REF = 556.214401533541
AA = math.pi + 4 * math.log(2)
W1, W2RAW = 3.5, -5 * AA + 1 / 54
MODELS_JOINT = {      # analyze_joint.py MODELS: (power p of 1/L, log power j)
    "A": [(1, 0), (1.5, 0), (1.5, 1), (2, 0)],
    "D": [(1, 0), (1, 1), (1.5, 0), (1.5, 1), (2, 0)],
    "E": [(1, 0), (1, 1), (1.5, 0), (1.5, 1), (2, 0), (2, 1)],
}
LOGS = ("none", "free")

BASES = {
    # name: list of (j, k) columns  L^{-j/2} log^k L
    "P4": [(1, 0), (2, 0), (3, 0), (4, 0)],
    "P6": [(j, 0) for j in range(1, 7)],
    "L1": [(1, 0), (1, 1), (2, 0), (2, 1), (3, 0), (3, 1), (4, 0)],
    "L2": [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2), (3, 0), (3, 1), (4, 0)],
    "M3": [(1, 0), (1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2), (3, 0), (3, 1), (4, 0)],
    "M3x": [(1, 0), (1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2), (2, 3), (3, 0), (3, 1), (4, 0)],
}


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def gate_check(npz, prov):
    """The result must be canonical: its gate record results/<sha12>/gates_L<Lmax>.txt (next to it) names the same
    snapshot, binds the result's sha256 and has no FAIL line (C5-A9-R2-001).  Returns the record's lines."""
    G = os.path.join(os.path.dirname(os.path.abspath(npz)), f"gates_L{int(prov['Lmax'])}.txt")
    if not os.path.exists(G):
        raise SystemExit(f"{npz}: no gate record {G} (only gated canonical results are fitted; --unchecked-input to "
                         "override for synthetic tests)")
    lines = open(G).read().split("\n")
    if f"snapshot_sha {prov['snapshot_sha']}" not in lines:
        raise SystemExit(f"{G} does not name the result's snapshot {prov['snapshot_sha']}")
    res = [ln for ln in lines if ln.startswith("result ")]
    if len(res) != 1 or res[0].split()[-1] != sha256_file(npz):
        raise SystemExit(f"{G} does not bind the sha256 of {npz}")
    if any(ln.startswith("FAIL") for ln in lines):
        raise SystemExit(f"{G} has FAIL lines: the result is not acceptable")
    return [ln for ln in lines if ln]


def load(npz, scheme):
    d = np.load(npz)
    L = d["even_L"].astype(int)
    y = d["even_C5Dconn"] if scheme == "Dconn" else d["even_C5raw"]
    if len(L) == 0 or y.shape != L.shape or not np.all(np.isfinite(y)) \
            or not np.array_equal(L, np.arange(2, L[-1] + 1, 2)):
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
    """One fit on even L in [lo, hi]; None if there are not more points than columns."""
    sel = [(int(a), float(b)) for a, b in zip(L, y) if lo <= a <= hi]
    ncol = 1 + (log == "free") + len(cols)
    if len(sel) <= ncol:
        return None
    Ls = [a for a, _ in sel]
    b = mp.matrix([mp.mpf(v) for _, v in sel])
    A = design(Ls, cols, log)
    coef, cond, rank = lstsq(A, b)
    res = A * mp.matrix(coef) - b
    off = 2 if log == "free" else 1
    c11 = coef[off + cols.index((1, 1))] if (1, 1) in cols else None
    out = dict(n=len(Ls), coef=[mp.nstr(c, 50) for c in coef], cols=[list(c) for c in cols], cond=float(cond),
               rank=rank, ncol=A.cols, maxres=float(max(abs(r) for r in res)), A=float(coef[0]),
               c11=None if c11 is None else mp.nstr(c11, 50))
    out["beta"] = float(coef[1]) if log == "free" else 0.0
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
        v += mp.fsum(cc * mp.power(x, -mp.mpf(j) / 2) * lx ** k for (j, k), cc in zip(cols, c[i:]))
        out.append(float(v))
    return out


C3_EXACT = -3.71985632290183342249        # analyze_joint.py C3 (exact three-loop value)


def known_limits():
    """C2 = A/9 (exact), C3 (exact constant above), C4 from inputs/ht_data.json "known" (exact four-loop value)."""
    k = json.load(open(os.path.join(HERE, "..", "inputs", "ht_data.json")))["known"]
    return AA / 9, C3_EXACT, float(k["C4"])


def eseries(z, w, kmax):
    """analyze_joint.eseries: e_0 = 1, e_k = sum_{j=1..k} z j w_j e_{k-j} / k  (exponential of sum_j w_j z eps^j)."""
    e = [np.ones_like(z)]
    for k in range(1, kmax + 1):
        acc = np.zeros_like(z)
        for j in range(1, k + 1):
            acc += z * j * w.get(j, 0.0) * e[k - j] / k
        e.append(acc)
    return e


def omega3_diag(L, c5raw, hi, los, c4npz):
    """Effective omega3 fits (see the module docstring); inputs restricted to even L <= hi."""
    if not os.path.exists(c4npz) or sha256_file(c4npz) != C4P_SHA256:
        raise SystemExit(f"omega3 diagnostic: C4P reference {c4npz} missing or not the pinned sha256 {C4P_SHA256[:12]}")
    d4 = np.load(c4npz)
    sel = L <= hi
    Ls = L[sel].astype(int)
    if np.any(4 * Ls >= len(d4["C4"])):
        raise SystemExit("omega3 diagnostic: the C4P reference does not cover the training range")
    C2L, C3L, C4L = (d4[k][4 * Ls] for k in ("C2", "C3", "C4"))
    lim2, lim3, lim4 = known_limits()
    z = np.log(Ls.astype(float))
    e = eseries(z, {1: W1, 2: W2RAW, 3: 0.0}, 3)
    x = C2L - lim2
    Y = c5raw[sel] + e[1] * (C4L - lim4) + e[2] * (C3L - lim3) + e[3] * x
    rows = []
    for name, terms in MODELS_JOINT.items():
        for lo in los:
            m = Ls >= lo
            n = int(m.sum())
            if n <= 3 + len(terms):
                continue
            A = mp.matrix([[mp.mpf(1), mp.mpf(float(xx)), -mp.log(int(LL)) * mp.mpf(float(xx))]
                           + [mp.power(int(LL), -mp.mpf(p)) * mp.log(int(LL)) ** j for p, j in terms]
                           for LL, xx in zip(Ls[m], x[m])])
            b = mp.matrix([mp.mpf(float(v)) for v in Y[m]])
            coef, cond, rank = lstsq(A, b)
            res = A * mp.matrix(coef) - b
            rows.append(dict(model=name, lo=int(lo), hi=int(hi), n=n, omega3_eff=float(coef[2]), A=float(coef[0]),
                             cond=float(cond), rank=rank, maxres=float(max(abs(r) for r in res))))
            print(f"omega3 diag {name} lo={lo:4d} n={n:4d} cond={float(cond):.1e} maxres={rows[-1]['maxres']:.1e} "
                  f"omega3_eff={rows[-1]['omega3_eff']:.4f}", flush=True)
    return dict(c4npz=os.path.abspath(c4npz), c4npz_sha256=C4P_SHA256, w1=W1, w2=W2RAW, limits=known_limits(),
                fits=rows)


def fmt_c11(r):
    return f"{float(mp.mpf(r['c11'])):+.6e}" if r["c11"] is not None else "n/a"


def run_fits(L, y, a):
    logs = a.logs.split(",")
    for lg in logs:
        if lg not in LOGS:
            raise SystemExit(f"log option {lg} not allowed (C5: {', '.join(LOGS)}; there is no 'fixed')")
    names = a.bases.split(",")
    for name in names:
        if name not in BASES:
            raise SystemExit(f"unknown basis {name} (known: {', '.join(BASES)})")
    los = [int(v) for v in a.lo.split(",")]
    if any(lo >= a.hi for lo in los):
        raise SystemExit(f"every --lo must be < --hi {a.hi}")
    rows = []
    for name in names:
        for lg in logs:
            for lo in los:
                r = fit_one(L, y, lo, a.hi, BASES[name], lg)
                if r is None:
                    print(f"{name:4s} log={lg:5s} lo={lo:4d}: SKIPPED (not more points than columns)", flush=True)
                    continue
                r.update(basis=name, log=lg, lo=lo, hi=a.hi)
                rows.append(r)
                print(f"{name:4s} log={lg:5s} lo={lo:4d} n={r['n']:4d} cols={r['ncol']:2d} rank={r['rank']:2d} "
                      f"cond={r['cond']:.1e} maxres={r['maxres']:.1e}  A={r['A']:.10f} beta={r['beta']:+.3e} "
                      f"c11={fmt_c11(r)}", flush=True)
    return rows


def cmd_freeze(a):
    if a.out is None or a.hi is None:
        raise SystemExit("freeze needs --out and --hi")
    for p in (a.out, a.out + ".sha256"):
        if os.path.lexists(p):
            raise SystemExit(f"{p} exists: a frozen record is never replaced")
    outdir = os.path.dirname(os.path.abspath(a.out))
    os.makedirs(outdir, exist_ok=True)                     # C5-A9-R2-003 (use a directory outside the read-only snapshot)
    if not os.access(outdir, os.W_OK):
        raise SystemExit(f"{outdir} is not writable (on the cluster freeze into $C5_DATA/fits/, not the snapshot)")
    L, y, prov = load(a.npz, a.scheme)
    gates = None if a.unchecked_input else gate_check(a.npz, prov)
    if L[-1] != a.hi:
        raise SystemExit(f"freeze needs a result whose even grid ends at --hi {a.hi} (file ends at {L[-1]}): "
                         "use the Lmax = hi production result, never a larger one")
    if not a.predict_to or a.predict_to < a.hi + 2:
        raise SystemExit("freeze needs --predict-to >= --hi + 2 (a non-empty even prediction grid)")
    rows = run_fits(L, y, a)
    if not rows:
        raise SystemExit("no fit had more points than columns: nothing frozen")
    Lp = list(range(a.hi + 2, a.predict_to + 1, 2))
    for r in rows:
        r["pred"] = predict(r, BASES[r["basis"]], r["log"], Lp)
    rec = dict(kind="frozen blind fit", target="C5", npz=os.path.abspath(a.npz), npz_sha256=sha256_file(a.npz),
               fit_code_sha256=sha256_file(os.path.abspath(__file__)), provenance_snapshot=prov.get("snapshot_sha"),
               scheme=a.scheme, hi=a.hi, predict_L=Lp, fits=rows, gate_record=gates,
               input_checked=not a.unchecked_input)
    if a.scheme == "raw":
        rec["omega3_diag"] = omega3_diag(L, y, a.hi, [int(v) for v in a.lo.split(",")], a.c4npz)
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
    P = json.loads(txt)
    if P.get("target") != "C5":
        raise SystemExit(f"{path} is not a C5 record")
    code = sha256_file(os.path.abspath(__file__))
    if P["fit_code_sha256"] != code:
        print(f"# note: record frozen by fit code {P['fit_code_sha256'][:16]}.., this code is {code[:16]}.. "
              "(stored coefficients and predictions are used as frozen)")
    return P


def cmd_compare(a):
    P = load_frozen(a.frozen)
    print(f"# frozen record {a.frozen} (scheme {P['scheme']}, hi {P['hi']}); exact C5 = {C5_EXACT}")
    for r in P["fits"]:
        print(f"{r['basis']:4s} log={r['log']:5s} lo={r['lo']:4d}: A = {r['A']:.10f}   A - C5 = {r['A'] - C5_EXACT:+.3e}"
              f"   beta = {r['beta']:+.3e}   c11 = {fmt_c11(r)}")
    if "omega3_diag" in P:
        print(f"# omega3 diagnostic (reference omega3 = {OMEGA3_REF} from the phi6 gap fit)")
        for r in P["omega3_diag"]["fits"]:
            print(f"omega3 {r['model']} lo={r['lo']:4d}: omega3_eff = {r['omega3_eff']:.4f}   "
                  f"- omega3 = {r['omega3_eff'] - OMEGA3_REF:+.4f}   intercept {r['A']:.6f}   cond {r['cond']:.1e}")


def cmd_check(a):
    P = load_frozen(a.frozen)
    L, y, prov = load(a.npz, P["scheme"])
    if not a.unchecked_input:
        gate_check(a.npz, prov)
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
    print(f"# blind check of {a.frozen} (scheme {P['scheme']}, hi {P['hi']}) against {a.npz} "
          f"(sha256 {sha256_file(a.npz)[:16]}..)")
    for r in P["fits"]:
        if len(r["pred"]) != len(pL) or not all(math.isfinite(v) for v in r["pred"]):
            raise SystemExit(f"FAIL: malformed predictions for {r['basis']}/{r['log']}/{r['lo']}")
        pairs = [(x, p - val[x]) for x, p in zip(pL, r["pred"]) if x in val]
        xw, dw = max(pairs, key=lambda t: abs(t[1]))
        print(f"{r['basis']:4s} log={r['log']:5s} lo={r['lo']:4d}: blind max |d| {abs(dw):.2e} at L={xw}; "
              f"d(L={pairs[-1][0]}) {pairs[-1][1]:+.2e}")


def cmd_explore(a):
    L, y, _ = load(a.npz, a.scheme)
    if a.hi is None:
        a.hi = int(L[-1])
    print(f"# EXPLORATION (not blind): {a.npz} scheme {a.scheme}, even L in [lo, {a.hi}]")
    run_fits(L, y, a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("freeze", "compare", "check", "explore"))
    ap.add_argument("--npz")
    ap.add_argument("--scheme", default="Dconn", choices=("Dconn", "raw"))
    ap.add_argument("--logs", default="none,free")
    ap.add_argument("--hi", type=int, default=None)
    ap.add_argument("--lo", default="80,120,160")
    ap.add_argument("--bases", default=",".join(BASES))
    ap.add_argument("--predict-to", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--frozen", default=None)
    ap.add_argument("--allow-partial", action="store_true")
    ap.add_argument("--unchecked-input", action="store_true",
                    help="skip the gate-record check (synthetic tests only; recorded in the frozen record)")
    ap.add_argument("--c4npz", default=C4P_NPZ, help="pinned C4P production result (omega3 diagnostic, raw scheme)")
    a = ap.parse_args()
    {"freeze": cmd_freeze, "compare": cmd_compare, "check": cmd_check, "explore": cmd_explore}[a.cmd](a)


if __name__ == "__main__":
    main()
