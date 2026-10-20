#!/usr/bin/env python3
"""Compare a fresh lri_coeff output envelope with a shipped production record (C, r, g, energies, vacua).
usage: smoke_check.py NEW.json SHIPPED.json   (relative tolerance 1e-12 on every coefficient; exit 1 on failure)"""
import json
import sys

new, ref = (json.load(open(p))["payload"] for p in sys.argv[1:3])
assert new["configuration"] == ref["configuration"], (new["configuration"], ref["configuration"])


def flat(x):
    return [v for row in x for v in (flat(row) if isinstance(row, list) else [row])] if isinstance(x, list) else [x]


worst = 0.0
for k in ("C", "r", "g", "energies", "vacuum_coefficients"):
    a, b = flat(new["result"][k]), flat(ref["result"][k])
    assert len(a) == len(b), k
    worst = max([worst] + [abs(x - y) / max(1.0, abs(y)) for x, y in zip(a, b)])
ok = worst <= 1e-12
print(f"{'PASS' if ok else 'FAIL'} smoke {sys.argv[1]} vs {sys.argv[2]}: worst scaled difference {worst:.1e} (tolerance 1e-12)")
sys.exit(0 if ok else 1)
