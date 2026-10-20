#!/usr/bin/env python3
"""
Regression test for critique item D2 (sigmas honoured on every entry point) and the covariance
input.  Synthetic random data only.

  1. from_beta / from_normalized / from_raw: sigmas= keyword == [value, sigma] form, both nonzero,
     and the derivative-convention scaling is right (raw and normalized derivative atoms);
  2. CLI --sigmas with --beta and with --normalized writes nonzero sigmas;
  3. covariance: a diagonal block reproduces independent sigmas; a full block gives exactly
     g^T C g with the gradients of Result.gradient (input convention); correlated vs anti-correlated;
     the CLI --cov reproduces the module;
  4. Result.gradient (derivative convention) agrees with a finite difference;
  5. input errors are rejected: sigma for an unsupplied input, conflicting sigmas, a sigma on an
     exact input, a non-symmetric or non-PSD block, a name in two blocks;
  6. the framework does not change the global mpmath precision.
"""
import json
import os
import random
import subprocess
import sys
import tempfile

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import lri_framework as L  # noqa: E402

random.seed(99)
FAIL = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


def close(a, b, rel=1e-20):
    return abs(a - b) <= rel * max(abs(a), abs(b), mp.mpf(10) ** -40)


def raises(f, exc=ValueError, text=""):
    try:
        f()
    except exc as e:
        return text in str(e)
    return False


def main():
    mp.mp.dps = 40          # the test's own reference arithmetic
    fw = L.Framework("D4", dps=40)
    print("[1] sigmas= keyword on every entry point")
    bneed = fw.required_names(level="beta")
    beta = {nm: mp.mpf(random.uniform(-5, 5)) for nm in bneed}
    rk = fw.from_beta(beta, sigmas={"a": "1e-3", "K": "2e-3"})
    rt = fw.from_beta({**beta, "a": (beta["a"], "1e-3"), "K": [beta["K"], "2e-3"]})
    sk, st = rk.inv["D4"].sigma(rk.sig), rt.inv["D4"].sigma(rt.sig)
    check(sk > 0 and close(sk, st), f"from_beta: sigma(D4) keyword {mp.nstr(sk, 6)} == pair form {mp.nstr(st, 6)}")
    check(close(rk.inv["D2"].sigma(rk.sig), mp.mpf("1e-3") / 2, 1e-12), "from_beta: sigma(D2) = sigma(a)/2 (D2 = -a/2 + ...)")
    nneed = fw.required_names(level="normalized")
    norm = {nm: mp.mpf(random.uniform(-3, 3)) for nm in nneed}
    nm_d = "C3_vv[l^1]"            # a derivative atom: input / 2! internally
    rk = fw.from_normalized(norm, sigmas={nm_d: "1e-3"})
    rt = fw.from_normalized({**norm, nm_d: [norm[nm_d], "1e-3"]})
    sk, st = rk.beta["A"].sigma(rk.sig), rt.beta["A"].sigma(rt.sig)
    gA = rk.gradient("A")[nm_d]
    check(sk > 0 and close(sk, st) and close(sk, abs(gA) * mp.mpf("1e-3"), 1e-12),
          f"from_normalized: sigma(A) keyword == pair form == |dA/d{nm_d}| * 1e-3 = {mp.nstr(sk, 6)}")
    rneed = fw.required_names()
    raw = {nm: mp.mpf(random.uniform(-3, 3)) for nm in rneed}
    sig = {"A7_v[eps^0 l^1]": "1e-3", "A3_vv[eps^0 l^0]": "2e-4"}
    rk = fw.from_raw(raw, sigmas=sig)
    rt = fw.from_raw({**raw, **{k: [raw[k], s] for k, s in sig.items()}})
    sk, st = rk.C[7].sigma(rk.sig), rt.C[7].sigma(rt.sig)
    g = rk.gradient("C7")
    ref = mp.sqrt(sum((g[k] * mp.mpf(s)) ** 2 for k, s in sig.items()))
    check(sk > 0 and close(sk, st) and close(sk, ref, 1e-12), f"from_raw: sigma(C7) keyword == pair == hand {mp.nstr(sk, 6)}")
    check(close(g["A7_v[eps^0 l^1]"], mp.mpf(-1) / 8, 1e-25), "dC7/dA7_v[eps^0 l^1] = -1/8 exactly (C7 contains -Omega/8)")

    print("[2] CLI --sigmas with --beta and --normalized")
    tmp = tempfile.mkdtemp(prefix="fwtest_")
    for flag, data, sfile in (("--beta", beta, {"a": "1e-3"}), ("--normalized", norm, {nm_d: "1e-3"})):
        fin, fsig, fout = (os.path.join(tmp, x) for x in ("in.json", "sig.json", "out.json"))
        json.dump({k: mp.nstr(v, 40) for k, v in data.items()}, open(fin, "w"))
        json.dump(sfile, open(fsig, "w"))
        p = subprocess.run([sys.executable, os.path.join(ROOT, "run_framework.py"), flag, fin, "--sigmas", fsig,
                            "--dps", "30", "--out", fout], capture_output=True, text=True)
        out = json.load(open(fout)) if p.returncode == 0 else {}
        s = out.get("invariants", {}).get("D2", {}).get("sigma") if flag == "--beta" else \
            out.get("beta", {}).get("A", {}).get("sigma")
        check(p.returncode == 0 and s is not None and float(s) > 0, f"CLI {flag} --sigmas: sigma = {s}")

    print("[3] covariance blocks")
    names = ["A3_v[eps^0 l^0]", "A3_vv[eps^0 l^0]", "Q4_d[eps^0 l^1]", "A5[eps^0 l^1]"]
    sd = [mp.mpf("1e-4"), mp.mpf("3e-4"), mp.mpf("2e-4"), mp.mpf("5e-4")]
    diag = {"names": names, "matrix": [[sd[a] ** 2 if a == b else 0 for b in range(4)] for a in range(4)]}
    r1 = fw.from_raw(raw, cov=diag)
    r2 = fw.from_raw(raw, sigmas=dict(zip(names, sd)))
    check(close(r1.C[7].sigma(r1.sig), r2.C[7].sigma(r2.sig), 1e-25), "diagonal block == independent sigmas")
    rho = [[1, 0.9, -0.5, 0.2], [0.9, 1, -0.3, 0.1], [-0.5, -0.3, 1, 0.4], [0.2, 0.1, 0.4, 1]]
    C = [[mp.mpf(rho[a][b]) * sd[a] * sd[b] for b in range(4)] for a in range(4)]
    r3 = fw.from_raw(raw, cov={"names": names, "matrix": C})
    for o in ("C6", "C7", "D4", "Omega"):
        g = r3.gradient(o)
        ref = mp.sqrt(sum(g.get(names[a], 0) * C[a][b] * g.get(names[b], 0) for a in range(4) for b in range(4)))
        check(close(r3.sigma(o), ref, 1e-25), f"{o}: sigma = sqrt(g^T C g) with input-convention gradients ({mp.nstr(ref, 5)})")
    pair = names[:2]
    g = r3.gradient("C7")
    for c, lab in ((1, "correlated"), (-1, "anti-correlated")):
        Cp = [[sd[0] ** 2, c * sd[0] * sd[1]], [c * sd[0] * sd[1], sd[1] ** 2]]
        rr = fw.from_raw(raw, cov={"names": pair, "matrix": Cp})
        ref = abs(g[pair[0]] * sd[0] + c * g[pair[1]] * sd[1])
        check(close(rr.C[7].sigma(rr.sig), ref, 1e-20), f"fully {lab} pair: sigma(C7) = |g1 s1 {'+' if c > 0 else '-'} g2 s2|")
    fin, fcov, fout = (os.path.join(tmp, x) for x in ("raw.json", "cov.json", "outc.json"))
    json.dump({k: mp.nstr(v, 40) for k, v in raw.items()}, open(fin, "w"))
    json.dump({"names": names, "matrix": [[mp.nstr(x, 30) for x in row] for row in C]}, open(fcov, "w"))
    p = subprocess.run([sys.executable, os.path.join(ROOT, "run_framework.py"), "--raw", fin, "--cov", fcov,
                        "--dps", "40", "--out", fout], capture_output=True, text=True)
    s = json.load(open(fout))["C"]["C7"]["sigma"] if p.returncode == 0 else None
    check(s is not None and abs(float(s) / float(r3.C[7].sigma(r3.sig)) - 1) < 1e-3, f"CLI --cov reproduces the module ({s})")

    print("[4] gradient in the input (derivative) convention vs finite difference")
    h = mp.mpf(10) ** -12
    for nm in ("A3_vv[eps^0 l^0]", "A3_vvd[eps^0 l^0]", "Q4_vd[eps^0 l^1]", "A3_dE[eps^0 l^0]"):
        rp = fw.from_raw({**raw, nm: raw[nm] + h}, track=False)
        rm = fw.from_raw({**raw, nm: raw[nm] - h}, track=False)
        with mp.workdps(40):
            fd = (rp.C[7].v - rm.C[7].v) / (2 * h)
        an = r3.gradient("C7")[nm]
        check(abs(fd - an) < 1e-15 * (1 + abs(an)), f"dC7/d{nm}: gradient {mp.nstr(an, 12)}  finite diff {mp.nstr(fd, 12)}")

    print("[5] rejected inputs")
    one = "A3_v[eps^0 l^0]"
    check(raises(lambda: fw.from_raw(raw, sigmas={"A9[eps^0 l^1]": 1}), ValueError, "not supplied"), "sigma for an unsupplied input")
    check(raises(lambda: fw.from_raw({**raw, one: [raw[one], "1e-3"]}, sigmas={one: "2e-3"}), ValueError, "conflicting"),
          "conflicting sigmas (entry vs keyword)")
    check(raises(lambda: fw.from_raw({**raw, one: {"value": raw[one], "exact": True}}, sigmas={one: "1e-3"}), ValueError,
                 "exact"), "sigma on an exact input")
    bad = {"names": pair, "matrix": [[1, 0.5], [0.4, 1]]}
    check(raises(lambda: fw.from_raw(raw, cov=bad), ValueError, "symmetric"), "non-symmetric block")
    bad = {"names": pair, "matrix": [[1, 2], [2, 1]]}
    check(raises(lambda: fw.from_raw(raw, cov=bad), ValueError, "semidefinite"), "non-PSD block")
    blocks = [{"names": [one], "matrix": [[1e-8]]}, {"names": [one], "matrix": [[1e-8]]}]
    check(raises(lambda: fw.from_raw(raw, cov=blocks), ValueError, "more than one"), "name in two blocks")
    check(raises(lambda: fw.from_raw({**raw, one: [raw[one], "1e-3"]}, cov={"names": [one], "matrix": [["4e-6"]]}),
                 ValueError, "disagrees"), "sigma inconsistent with the covariance diagonal")
    # gate review 2026-10-03: non-finite numbers are rejected at parse time (values, replicates, sigmas)
    check(all(raises(lambda b=b: fw.from_raw({**raw, one: b}), ValueError, "not a finite number")
              for b in ("nan", float("nan"), "inf", "-inf", {"reps": [raw[one], "nan", raw[one]]},
                        [raw[one], "nan"])),
          "NaN/inf value, replicate or sigma rejected")

    print("[6] global precision untouched")
    mp.mp.dps = 17
    fw6 = L.Framework("D4", dps=40)
    fw6.from_raw(raw)
    fw6.from_beta(beta)
    L.closed_forms(60)
    check(mp.mp.dps == 17, f"mp.mp.dps is still 17 after Framework(dps=40) calls and closed_forms(60) (now {mp.mp.dps})")
    print("ERROR-MODEL TEST", "PASSED" if not FAIL else f"FAILED ({len(FAIL)})")
    return not FAIL


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
