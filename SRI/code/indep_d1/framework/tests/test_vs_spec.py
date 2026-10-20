#!/usr/bin/env python3
"""Cross-agent check: our derived input formulas (out/beta_input_formulas.json, from J0 beta = R1)
versus the spec agent's expansions (../spec/out/input_definitions.json). Skips if absent."""
import json
import os
import re
import sys

import sympy as sp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPEC = os.path.join(ROOT, "..", "spec", "out", "input_definitions.json")


def conv(s):
    def rep(m):
        E, X, n, k, a, b = m.group(1), m.group(2), m.group(3), m.group(4), int(m.group(5)), int(m.group(6))
        suf = "v" * a + "d" * b + ("E" if E else "")
        return f"{X}{n}_{k}" + (f"_{suf}" if suf else "")
    return re.sub(r"(E?)([CK])(\d)_([01])\[v(\d)d(\d)\]", rep, s)


def main():
    if not os.path.exists(SPEC):
        print("spec definitions not available; skipping")
        return True
    mine = json.load(open(os.path.join(ROOT, "out", "beta_input_formulas.json")))
    theirs = json.load(open(SPEC))
    ok = True
    for nm, info in theirs.items():
        d = sp.expand(sp.sympify(conv(info["expansion_in_normalized_atoms"])) - sp.sympify(mine[nm]))
        ok &= d == 0
        if d != 0:
            print("DIFF", nm, d)
    print(f"{len(theirs)} input expansions vs spec agent:", "ALL IDENTICAL" if ok else "DIFFERENCES")
    print("SPEC CROSS-CHECK", "PASSED" if ok else "FAILED")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
