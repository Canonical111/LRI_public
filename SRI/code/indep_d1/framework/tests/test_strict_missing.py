#!/usr/bin/env python3
"""
Regression test for critique item D1 (strict mode; absent inputs are never zero).
Synthetic random data only (no archive numbers).

  1. the module's required lists equal the shipped out/required_inputs_{D4,C8}.json;
  2. all 116 required scalars supplied -> every output present, no warnings;
  3. STRICT (default): dropping ANY single required scalar (each of the 116 at order D4 and each of
     the 201 at order C8), or giving it as null, raises MissingInputError naming exactly that scalar;
  4. NON-STRICT: for a set of drops (the reviewer's seven, the top and lowest powers of atoms, the
     7- and 8-kink scalars, random others) every output that depends on the dropped scalar is MISSING
     and names it, every other output is unchanged, and normalized entries that need it are MISSING;
  5. load_spec_raw keeps null -> absent (strict raises);
  6. a nonzero coefficient below the structural lowest power is an error; an explicit zero there is accepted;
  7. from_normalized and from_beta are strict too (every required normalized / beta input);
  8. strict validation can be restricted to some outputs (outputs=[...]); the others then report MISSING.
"""
import json
import os
import random
import sys
import time

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import lri_framework as L  # noqa: E402

random.seed(2026)
FAIL = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


def strict_raises(fw, raw, expect, **kw):
    try:
        fw.from_raw(raw, **kw)
    except L.MissingInputError as e:
        return e.missing == sorted(expect)
    return False


def main():
    t0 = time.time()
    fw = L.Framework("D4", dps=30)
    need = fw.required_names()
    print("[1] required lists vs shipped files")
    for order, n_exp in (("D4", 116), ("C8", 201)):
        names = need if order == "D4" else L.Framework("C8", dps=30).required_names()
        shipped = json.load(open(os.path.join(ROOT, "out", f"required_inputs_{order}.json")))["flat_names"]
        check(len(names) == n_exp and names == shipped, f"{order}: {len(names)} required, identical to the shipped list")
    base = {nm: mp.mpf(random.uniform(-3, 3)) for nm in need}

    print("[2] complete input")
    r0 = fw.from_raw(base)
    outs0 = r0.outputs()
    check(not any(x.is_missing for x in outs0.values()), f"all {len(outs0)} outputs present")
    check(not r0.warnings, "no warnings (no spurious 'treated as ZERO' messages)")
    check(r0.unused == [], "no unused inputs")

    print("[3] strict: drop each single required scalar")
    bad = [nm for nm in need if not strict_raises(fw, {k: v for k, v in base.items() if k != nm}, [nm])]
    check(not bad, f"D4: all {len(need)} single drops raise MissingInputError naming the dropped scalar {bad[:3]}")
    bad = [nm for nm in need[::7] if not strict_raises(fw, {**base, nm: None}, [nm])]
    check(not bad, "null values count as absent (every 7th scalar tested)")
    fw8 = L.Framework("C8", dps=30)
    need8 = fw8.required_names()
    base8 = {nm: mp.mpf(random.uniform(-3, 3)) for nm in need8}
    bad = [nm for nm in need8 if not strict_raises(fw8, {k: v for k, v in base8.items() if k != nm}, [nm])]
    check(not bad, f"C8: all {len(need8)} single drops raise {bad[:3]}")
    try:
        fw.from_raw({k: v for k, v in base.items() if not k.startswith("A3_v[")})
        ok = False
    except L.MissingInputError as e:
        ok = sorted(e.missing) == sorted(k for k in need if k.startswith("A3_v[")) and "A3_v[eps^0 l^1]" in str(e)
    check(ok, "dropping a whole atom lists every one of its scalars")

    print("[4] non-strict: MISSING flags, other outputs unchanged")
    reviewer = ["A5[eps^1 l^1]", "Q4[eps^1 l^1]", "A3[eps^1 l^1]", "Z4[eps^0 l^0]", "A3_v[eps^1 l^0]",
                "Q6[eps^0 l^0]", "A3[eps^0 l^1]"]
    groups = [[x] for x in reviewer] + [["A3[eps^2 l^0]", "A3[eps^2 l^1]"], ["Z4[eps^-2 l^0]", "Z4[eps^-2 l^1]"],
                                        ["A7_v[eps^0 l^1]"], ["Q8[eps^0 l^1]"], ["A3_vvv[eps^0 l^1]"]]
    groups += [[x] for x in random.sample([n for n in need if [n] not in groups], 6)]
    # structural dependence (required list of each output); an output can depend structurally on a
    # scalar while its numerical gradient cancels identically -> it is flagged too (conservative)
    struct = fw.required_inputs(outputs=list(outs0))
    for drop in groups:
        raw = {k: v for k, v in base.items() if k not in drop}
        r = fw.from_raw(raw, strict=False)
        dep = {o for o, x in outs0.items() if any(x.g.get(d, 0) != 0 for d in drop)}
        sdep = {o for o in outs0 if set(drop) & set(struct[o])}
        flagged = {o for o, x in r.outputs().items() if x.is_missing}
        named = all(set(drop) & set(r.outputs()[o].miss) for o in flagged)
        same = all(r.outputs()[o].v == outs0[o].v for o in outs0 if o not in flagged)
        norm_ok = all(x.is_missing for nm, x in r.normalized.items()
                      if not r0.normalized[nm].is_missing and any(r0.normalized[nm].g.get(d, 0) != 0 for d in drop))
        extra = sorted(flagged - dep)
        check(dep and dep <= flagged and flagged == sdep and named and same and norm_ok,
              f"drop {', '.join(drop):34s}: {len(dep):2d} dependent outputs, all MISSING and naming it; others "
              f"unchanged" + (f" (also flagged, structural with cancelling gradient: {extra})" if extra else ""))

    print("[5] load_spec_raw: null kept as absent")
    spec = {"A3_base": {"0": {"0": None, "1": "6"}}}
    flat = L.load_spec_raw(spec)
    check(flat.get("A3[eps^0 l^0]", 1) is None and "A3[eps^0 l^0]" in flat, "null survives the adapter")
    raw = dict(base)
    raw.update(flat)
    check(strict_raises(fw, raw, ["A3[eps^0 l^0]"]), "and strict mode raises for it")

    print("[6] coefficients below the structural lowest power")
    try:
        fw.from_raw({**base, "Z4[eps^-3 l^0]": "1e-20"})
        ok = False
    except ValueError as e:
        ok = "structural" in str(e)
    check(ok, "nonzero Z4[eps^-3 l^0] is an error")
    r = fw.from_raw({**base, "Z4[eps^-3 l^0]": {"value": 0, "exact": True}})
    check(r.C[7].v == r0.C[7].v, "an explicit exact zero there is accepted (and unused)")

    print("[7] normalized and beta levels are strict")
    nneed = fw.required_names(level="normalized")
    nbase = {nm: mp.mpf(random.uniform(-3, 3)) for nm in nneed}
    rn = fw.from_normalized(nbase)
    check(not any(x.is_missing for x in rn.outputs().values()), f"{len(nneed)} normalized inputs: all outputs present")
    bad = []
    for nm in nneed:
        try:
            fw.from_normalized({k: v for k, v in nbase.items() if k != nm})
            bad.append(nm)
        except L.MissingInputError as e:
            if e.missing != [nm]:
                bad.append(nm)
    check(not bad, f"every single normalized drop raises {bad[:3]}")
    k2 = "K2_v[l^0]"
    rk = fw.from_normalized({**nbase, k2: "1.25"})
    check(any(k2 in w and "supplied value is used" in w for w in rk.warnings) and rk.C[7].v != rn.C[7].v
          and k2 in rk.C[7].g, "a supplied K2 coefficient overrides the exact one (phase-1 contract), with a warning")
    bneed = fw.required_names(level="beta")
    check(bneed == sorted(fw.beta_names), f"beta level needs all {len(bneed)} inputs")
    bbase = {nm: mp.mpf(random.uniform(-5, 5)) for nm in bneed}
    bad = []
    for nm in bneed:
        try:
            fw.from_beta({k: v for k, v in bbase.items() if k != nm})
            bad.append(nm)
        except L.MissingInputError as e:
            if e.missing != [nm]:
                bad.append(nm)
    check(not bad, "every single beta drop raises")
    rb = fw.from_beta({k: v for k, v in bbase.items() if k != "K"}, strict=False)
    check(rb.C[7].is_missing and not rb.C[6].is_missing, "non-strict beta: C7 MISSING without K, C6 present")

    print("[8] strict check restricted to some outputs")
    c5need = fw.required_names(outputs=["C5"])
    raw = {k: v for k, v in base.items() if k in c5need}
    r = fw.from_raw(raw, outputs=["C5"])
    check(not r.C[5].is_missing and r.C[5].v == r0.C[5].v and r.C[7].is_missing and r.beta["K"].is_missing,
          f"outputs=['C5'] needs {len(c5need)} scalars; C5 exact, C7 and K MISSING")
    check(strict_raises(fw, raw, sorted(set(need) - set(c5need))), "the same input fails the default (all-output) check")

    print(f"({time.time() - t0:.0f} s)")
    print("STRICT/MISSING TEST", "PASSED" if not FAIL else f"FAILED ({len(FAIL)})")
    return not FAIL


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
