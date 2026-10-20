#!/usr/bin/env python3
"""
Phase-3 regression test: order C8 (C8 = 8 T4) and the eq:C8assembly pieces.  Synthetic data only
(random points; nothing from the archive).

  1. the module's B_OLD_C8_TERMS, C8_LINEAR and C8_INHERITED equal the sympy derivation (out/C8_trace.json,
     written by derive_C8.py) and the appendix polynomial parsed from the note's TeX;
  2. C8 two ways: C8_asm (B_old + eq:C8assembly) equals 8 T4 recomputed with exact tree data, at random raw
     points (an identity: values and gradients to working precision); at points with exact tree data
     (A3[eps^0 l^1] = 6) C8_asm = C8 = 8 T4 itself; from_beta: C8 = B_old + sum coef X exactly;
  3. B_old at order D4 equals B_old at order C8; B_old8 needs exactly the 116 order-D4 scalars;
  4. partial mode (beta level and raw level): an absent new input is never zero: C8, C8_asm (and B_done8 if
     it is one of the six inherited inputs) are MISSING, C8_partial = B_old + the available terms, the absent
     ones are listed; strict mode raises and names the scalar;
  5. the leading raw scalars of J9, U, Kv, Ndelta enter with the note's exact coefficients (any point), and
     d C8 / d raw agrees with finite differences;
  6. per-replicate assembly at order C8 (one R): replicate r of B_old8 / C8 equals a direct assembly of
     replicate r; rep_se agrees with the linear propagation;
  7. replicate blocks with different R: refused by default; mixed_R="group": rep_se^2 = sum of the group
     variances (checked by hand), close to the linear propagation;
  8. merge_inputs: a block id shared by two inputs raises; independent=True renames the blocks per input;
  9. c8_combine: beta-level extras (e.g. the semi-analytic W) fill only absent new inputs; errors add in
     quadrature; giving a computed input is an error;
 10. CLI: --order C8 --allow-missing prints the C8 pieces and the missing terms; strict exits 2.
Run: python3 tests/test_c8.py   (local, about 1 minute)
"""
import json
import os
import random
import subprocess
import sys
import tempfile
from fractions import Fraction

import mpmath as mp
import sympy as sp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import lri_framework as L  # noqa: E402

random.seed(8888)
FAIL = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg, flush=True)
    if not cond:
        FAIL.append(msg)


def raises(f, exc=ValueError, text=""):
    try:
        f()
    except exc as e:
        return text in str(e)
    return False


def point(names, exact_tree=True, scale=3.0):
    pt = {n: mp.mpf(random.uniform(-scale, scale)) for n in names}
    if exact_tree:
        pt["A3[eps^0 l^1]"] = {"value": "6", "exact": True}
    return pt


def main():
    mp.mp.dps = 50
    fw8 = L.Framework("C8", dps=50)
    fw4 = L.Framework("D4", dps=50)
    need8 = fw8.required_names()
    need4 = fw4.required_names()

    print("[1] embedded eq:C8assembly table vs the symbolic derivation and the note's TeX")
    tr = json.load(open(os.path.join(ROOT, "out", "C8_trace.json")))
    syms = {n: sp.Symbol(n) for n in L.BETA_NAMES_D4 + L.BETA_NAMES_C8}
    mod = sum(sp.Rational(c.numerator, c.denominator) * sp.Mul(*[syms[n] ** p for n, p in mon])
              for c, mon in L.B_OLD_C8_TERMS)
    der = sp.sympify(tr["C"]["B_old"], locals=syms)
    check(sp.expand(mod - der) == 0, f"B_OLD_C8_TERMS ({len(L.B_OLD_C8_TERMS)} terms) == derived B_old (C8_trace.json)")
    sys.path.insert(0, ROOT)
    import derive_C8 as D8
    tex, line = D8.note_appendix_Bold()
    check(sp.expand(mod - tex) == 0, f"B_OLD_C8_TERMS == appendix app:C8polynomial parsed from the TeX (l.{line})")
    lin_ok = all(sp.Rational(L.C8_LINEAR[n].numerator, L.C8_LINEAR[n].denominator) ==
                 sp.Rational(tr["C"]["C8_linear_coefficients"][n]) for n in L.C8_LINEAR)
    check(lin_ok and list(L.C8_INHERITED) == tr["C"]["inherited_record_inputs"] and tr["all_ok"],
          "C8_LINEAR, C8_INHERITED == derived; derive_C8.py all_ok")

    print("[2] C8 two ways")
    worst_v = worst_g = mp.mpf(0)
    for t in range(3):
        r = fw8.from_raw(point(need8, exact_tree=False))
        worst_v = max(worst_v, abs(r.c8_info["C8_asm_minus_8T4_exact_tree"]))
        worst_g = max(worst_g, r.c8_info["C8_asm_minus_8T4_exact_tree_gradient_max"])
    check(worst_v < 1e-40 and worst_g < 1e-40,
          f"random raw points: C8_asm - 8T4[exact tree] = {mp.nstr(worst_v, 3)} (gradients {mp.nstr(worst_g, 3)})")
    pt = point(need8)
    r = fw8.from_raw(pt)
    a, c = r.c8["C8_asm"], r.C[8]
    dg = max(abs(a.g.get(k, 0) - c.g.get(k, 0)) for k in set(a.g) | set(c.g) if k != "A3[eps^0 l^1]")
    check(abs(a.v - c.v) < 1e-40 and dg < 1e-38 and r.c8_info["8T4_minus_8T4_exact_tree"] == 0,
          f"exact tree data: C8_asm == C8 = 8 T4 ({mp.nstr(a.v - c.v, 3)}; gradients {mp.nstr(dg, 3)})")
    beta = {k: Fraction(random.randint(-99, 99), random.randint(1, 9)) for k in fw8.beta_names}
    rb = fw8.from_beta({k: mp.mpf(v.numerator) / v.denominator for k, v in beta.items()})
    exact = sp.expand(der.subs({syms[k]: sp.Rational(v.numerator, v.denominator) for k, v in beta.items()})
                      + sum(sp.Rational(L.C8_LINEAR[n].numerator, L.C8_LINEAR[n].denominator)
                            * sp.Rational(beta[n].numerator, beta[n].denominator) for n in L.C8_LINEAR))
    ex = mp.mpf(exact.p) / exact.q
    check(abs(rb.C[8].v - ex) < 1e-40 * (1 + abs(ex)) and abs(rb.c8["C8_asm"].v - ex) < 1e-40 * (1 + abs(ex)),
          f"from_beta (rational inputs): 8 T4 == C8_asm == exact rational sympy value ({mp.nstr(rb.C[8].v - ex, 3)})")

    print("[3] B_old at both orders")
    r4 = fw4.from_raw({k: v for k, v in pt.items() if k in need4})
    check(r4.c8["B_old8"].v == r.c8["B_old8"].v and set(r4.c8) == {"B_old8"},
          "B_old8 at order D4 == at order C8 (exact); order D4 reports only B_old8")
    check(fw8.required_inputs(outputs=["B_old8"])["B_old8"] == need4 and len(need4) == 116,
          "B_old8 needs exactly the 116 order-D4 scalars")

    print("[4] partial C8 (never zero)")
    full = {k: mp.mpf(random.uniform(-3, 3)) for k in fw8.beta_names}
    ok = True
    for X in L.C8_LINEAR:
        part = {k: v for k, v in full.items() if k != X}
        rp = fw8.from_beta(part, strict=False)
        bold = rp.c8["B_old8"].v
        hand = bold + sum(mp.mpf(c.numerator) / c.denominator * full[n] for n, c in L.C8_LINEAR.items() if n != X)
        ok &= abs(rp.c8["C8_partial"].v - hand) < 1e-40 * (1 + abs(hand))
        ok &= rp.c8_info["partial_missing"] == {X: [X]} and X not in rp.c8_info["terms_included"]
        ok &= rp.C[8].is_missing and rp.c8["C8_asm"].is_missing
        ok &= rp.c8["B_done8"].is_missing == (X in L.C8_INHERITED)
        ok &= raises(lambda: fw8.from_beta(part), L.MissingInputError, X)
    check(ok, "beta level, each new input absent in turn: C8_partial = B_old + the other nine terms, absent one "
              "listed; C8, C8_asm MISSING; B_done8 MISSING iff inherited; strict raises naming it")
    by = fw8.required_inputs()
    for x in ("A9[eps^0 l^1]", "Q4_vvv[eps^0 l^1]"):
        users = sorted(o for o in L.C8_LINEAR if x in by[o])
        drop = {k: v for k, v in pt.items() if k != x}
        rd = fw8.from_raw(drop, strict=False)
        hand = r.c8["B_old8"].v + sum(mp.mpf(c.numerator) / c.denominator * r.beta[n].v
                                      for n, c in L.C8_LINEAR.items() if n not in users)
        okd = (sorted(rd.c8_info["partial_missing"]) == users and rd.C[8].is_missing
               and abs(rd.c8["C8_partial"].v - hand) < 1e-40 * (1 + abs(hand))
               and all(rd.c8_info["partial_missing"][u] == [x] for u in users)
               and raises(lambda: fw8.from_raw(drop), L.MissingInputError, x))
        check(okd, f"raw level, {x} absent: MISSING {users} (named), C8_partial = B_old + the rest; strict raises")

    print("[5] note structure of the four packages; gradients vs finite differences")
    struct = {"J9": {"A9[eps^0 l^1]": 1, "Z8[eps^0 l^1]": -1, "A7_E[eps^0 l^0]": 2, "Z6_E[eps^0 l^0]": -2},
              "U": {"A7_d[eps^0 l^1]": 1, "Z6_d[eps^0 l^1]": -1, "A5_dE[eps^0 l^0]": 2, "Z4_dE[eps^0 l^0]": -2},
              "Kv": {"Q8_v[eps^0 l^1]": -4, "Q6_vv[eps^0 l^0]": 16, "Q6_vE[eps^0 l^0]": -8},
              "Ndelta": {"Q6_vd[eps^0 l^1]": -4}}
    ok = True
    for t in range(2):
        rr_ = fw8.from_raw(point(need8, exact_tree=(t == 0)))
        for o, co in struct.items():
            g = rr_.gradient(o)
            ok &= all(abs(g.get(x, 0) - c) < 1e-40 for x, c in co.items())
    check(ok, "J9, U, Kv, Ndelta: exact coefficients of their leading raw scalars (note Sec. fullpackages), "
              "at two random points")
    g = r.gradient("C8")
    worst = mp.mpf(0)
    for x in ("A9[eps^0 l^1]", "Q8_v[eps^0 l^1]", "Q4[eps^0 l^0]", "A5_v[eps^0 l^1]", "Z6[eps^-1 l^0]",
              "Q4_vvv[eps^0 l^1]"):
        h = mp.mpf(10) ** -20
        p2 = dict(pt)
        p2[x] = pt[x] + h
        p1 = dict(pt)
        p1[x] = pt[x] - h
        fd = (fw8.from_raw(p2, track=False, keep_normalized=False).C[8].v
              - fw8.from_raw(p1, track=False, keep_normalized=False).C[8].v) / (2 * h)
        worst = max(worst, abs(fd - g.get(x, 0)) / (1 + abs(fd)))
    check(worst < 1e-15, f"dC8/d raw (derivative convention) == central finite differences (worst {mp.nstr(worst, 3)})")

    print("[6] per-replicate assembly at order C8")
    Rn = 4
    base = point(need8)
    scal = {}
    for nm in need8:
        if nm == "A3[eps^0 l^1]":
            scal[nm] = base[nm]
            continue
        sc = mp.mpf("1e-7") * (1 + abs(base[nm]))
        scal[nm] = {"reps": [mp.nstr(base[nm] + sc * random.gauss(0, 1), 45) for _ in range(Rn)], "block": "b1"}
    data = {"format": L.CANONICAL_FORMAT, "convention": "derivative", "scalars": scal}
    rr = fw8.from_replicates(data)
    rep1 = {nm: (mp.mpf(v["reps"][1]) if isinstance(v, dict) and "reps" in v else v) for nm, v in scal.items()}
    d1 = fw8.from_raw(rep1, track=False, keep_normalized=False)
    check(rr.per_rep["B_old8"][1] == d1.c8["B_old8"].v and rr.per_rep["C8"][1] == d1.C[8].v
          and rr.per_rep["C8_asm"][1] == d1.c8["C8_asm"].v,
          "replicate 1 of B_old8, C8, C8_asm == direct assembly of replicate 1 (exact)")
    st = rr.stats["C8"]
    check(abs(st["rep_se"] / st["sigma_linear"] - 1) < 1e-3 and abs(st["nonlinearity"]) < 1e-3 * st["rep_se"],
          f"C8: rep_se / sigma_linear = {mp.nstr(st['rep_se'] / st['sigma_linear'], 6)} (one block: equal)")

    print("[7] replicate blocks with different R")
    scal2 = {}
    for nm, v in scal.items():
        if isinstance(v, dict) and nm.startswith("Q"):
            sc = mp.mpf("1e-7") * (1 + abs(base[nm]))
            scal2[nm] = {"reps": [mp.nstr(base[nm] + sc * random.gauss(0, 1), 45) for _ in range(6)], "block": "q6"}
        else:
            scal2[nm] = v
    data2 = {"format": L.CANONICAL_FORMAT, "convention": "derivative", "scalars": scal2}
    check(raises(lambda: fw8.from_replicates(data2), ValueError, "mixed_R='group'"), "default: refused")
    rg = fw8.from_replicates(data2, mixed_R="group")
    # by hand: vary each group alone
    means = {nm: (sum(mp.mpf(x) for x in v["reps"]) / len(v["reps"]) if isinstance(v, dict) and "reps" in v else v)
             for nm, v in scal2.items()}
    c0 = fw8.from_raw(means, track=False, keep_normalized=False).C[8].v
    var = mp.mpf(0)
    for blk, Rb in (("b1", Rn), ("q6", 6)):
        xs = []
        for r_ in range(Rb):
            vals = dict(means)
            for nm, v in scal2.items():
                if isinstance(v, dict) and v.get("block") == blk:
                    vals[nm] = mp.mpf(v["reps"][r_])
            xs.append(fw8.from_raw(vals, track=False, keep_normalized=False).C[8].v)
        m = sum(xs) / Rb
        var += sum((x - m) ** 2 for x in xs) / (Rb - 1) / Rb
    stg = rg.stats["C8"]
    check(abs(stg["rep_se"] - mp.sqrt(var)) < 1e-30 and stg["value"] == c0 and rg.meta["replicate_groups"] == {"R4": len(
        [1 for v in scal2.values() if isinstance(v, dict) and v.get("block") == "b1"]), "R6": len(
        [1 for v in scal2.values() if isinstance(v, dict) and v.get("block") == "q6"])},
          f"mixed_R='group': rep_se == hand sum of group variances; dof {mp.nstr(stg['dof'], 3)}")
    check(0.5 < stg["rep_se"] / stg["sigma_linear"] < 2,
          f"... and close to the linear propagation (ratio {mp.nstr(stg['rep_se'] / stg['sigma_linear'], 4)})")

    print("[8] merge_inputs and replicate block ids")
    i1 = {"format": L.CANONICAL_FORMAT, "convention": "derivative", "sources": ["/x/prod.json"],
          "scalars": {"A5[eps^0 l^1]": {"reps": ["1", "2", "3"], "block": "A5_base|k=0"}}}
    i2 = {"format": L.CANONICAL_FORMAT, "convention": "derivative", "sources": ["/y/c8run.json"],
          "scalars": {"A5[eps^0 l^0]": {"reps": ["1", "2", "4", "5"], "block": "A5_base|k=0"}}}
    check(raises(lambda: L.merge_inputs([i1, i2]), ValueError, "replicate block id"), "shared block id: raises")
    mg = L.merge_inputs([i1, i2], independent=True)
    check(mg["scalars"]["A5[eps^0 l^1]"]["block"] == "prod:A5_base|k=0"
          and mg["scalars"]["A5[eps^0 l^0]"]["block"] == "c8run:A5_base|k=0",
          "independent=True: blocks renamed per input ('prod:...', 'c8run:...')")

    print("[9] c8_combine with beta-level extras")
    part = {k: v for k, v in full.items() if k not in L.C8_LINEAR or k in ("U", "J9")}
    rp = fw8.from_beta(part, sigmas={"K": "1e-3"}, strict=False)
    comb = L.c8_combine(rp, {"W": ["-37.7", "1e-2"], "Kv": ["5", "0.1"]})
    cp = comb["parts"]["C8_partial"]
    hand = rp.c8["B_old8"].v + mp.mpf(3) / 4 * full["U"] + full["J9"] / 4 + 4 * mp.mpf("-37.7") + mp.mpf(5) / 32
    sB = rp.c8["B_old8"].sigma(rp.sig)
    sh = mp.sqrt(sB ** 2 + (4 * mp.mpf("1e-2")) ** 2 + (mp.mpf("0.1") / 32) ** 2)
    check(abs(cp["value"] - hand) < 1e-40 and abs(cp["sigma_linear"] - sh) < 1e-30 * sh
          and comb["partial_missing"] == sorted(["S", "L3", "M21", "M12", "N2", "Ndelta"])
          and comb["terms"]["W"]["source"] == "extra" and comb["terms"]["U"]["source"] == "assembly",
          "extras fill absent inputs; C8_partial value and sigma (quadrature) by hand; missing terms listed")
    check(raises(lambda: L.c8_combine(rp, {"U": "1"}), ValueError, "already computes"),
          "an extra for an input the assembly computes is an error")
    combr = L.c8_combine(rr, None)
    check(abs(combr["parts"]["C8_asm"]["rep_se"] - rr.stats["C8"]["rep_se"]) < 1e-12 * rr.stats["C8"]["rep_se"],
          "c8_combine on a ReplicateResult: rep_se(C8_asm) == rep_se(C8)")

    print("[10] CLI")
    with tempfile.TemporaryDirectory() as td:
        bf = os.path.join(td, "beta.json")
        json.dump({k: mp.nstr(v, 30) for k, v in full.items() if k not in ("Kv", "N2")}, open(bf, "w"))
        p = subprocess.run([sys.executable, os.path.join(ROOT, "run_framework.py"), "--beta", bf, "--order", "C8",
                            "--allow-missing", "--out", os.path.join(td, "o.json")], capture_output=True, text=True)
        o = json.load(open(os.path.join(td, "o.json"))) if p.returncode == 0 else {}
        check(p.returncode == 0 and "C8_partial" in p.stdout and "missing terms NOT included" in p.stdout
              and o.get("C8_combined", {}).get("partial_missing") == ["Kv", "N2"],
              "--order C8 --allow-missing: C8 pieces printed, missing terms Kv, N2 listed (JSON C8_combined)")
        p2 = subprocess.run([sys.executable, os.path.join(ROOT, "run_framework.py"), "--beta", bf, "--order", "C8"],
                            capture_output=True, text=True)
        check(p2.returncode == 2 and "Kv" in p2.stderr and "N2" in p2.stderr, "strict: exit 2 naming Kv and N2")

    print("FAILURES:", FAIL if FAIL else "none")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
