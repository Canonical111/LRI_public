#!/usr/bin/env python3
"""Collect the finite-cutoff HT coefficients C_n(L) of the 2D LRI from the per-run JSON envelopes.

Reads every results/*/d*/<scheme>_L<L>.json under lri_2d_coeff_expanse/results (only the payload.result
block: C, r, g, energies) and writes ht_coefficients.csv (one row per scheme, L; duplicates across campaigns
must agree to 1e-12 relative or the script stops). Nothing from the solver source is read.
"""
import csv
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.normpath(os.path.join(HERE, "..", "..", "results"))
OUT = os.path.join(HERE, "ht_coefficients.csv")


def main():
    rows = {}
    for path in sorted(glob.glob(os.path.join(RESULTS, "*", "d*", "*_L*.json"))):
        with open(path) as fh:
            env = json.load(fh)
        res = env["payload"]["result"]
        scheme, L, deg = res["scheme"], int(res["cutoff"]), int(res["degree"])
        C = [float(c) for c in res["C"]]
        key = (scheme, L)
        rec = {"scheme": scheme, "L": L, "degree": deg, "source": os.path.relpath(path, RESULTS)}
        for n, c in enumerate(C):
            rec[f"C{n}"] = repr(c)
        for n, c in enumerate(res["r"]):
            rec[f"r{n}"] = repr(float(c))
        for n, c in enumerate(res["g"]):
            rec[f"g{n}"] = repr(float(c))
        if key in rows:
            old = rows[key]
            for n in range(min(len(C), old["degree"] + 1, deg + 1)):
                a, b = float(old[f"C{n}"]), C[n]
                if abs(a - b) > 1e-12 * max(1.0, abs(a)):
                    sys.exit(f"inconsistent duplicate {key} C{n}: {a} vs {b} ({old['source']}, {path})")
            if deg <= old["degree"]:
                continue
        rows[key] = rec
    if not rows:
        sys.exit("no envelopes found under " + RESULTS)
    maxdeg = max(r["degree"] for r in rows.values())
    fields = ["scheme", "L", "degree"] + [f"C{n}" for n in range(maxdeg + 1)] \
        + [f"r{n}" for n in range(maxdeg + 1)] + [f"g{n}" for n in range(maxdeg + 1)] + ["source"]
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for key in sorted(rows):
            w.writerow(rows[key])
    Ls = sorted({k[1] for k in rows})
    print(f"wrote {OUT}: {len(rows)} rows, schemes {sorted({k[0] for k in rows})}, L = {Ls}")


if __name__ == "__main__":
    main()
