#!/usr/bin/env python3
"""A1 + A2 (PLAN.md): diagram sums vs exact rationals.
A1: inputs/exact_rational_validation.json (Lambda = 2, 4, 6, 8, 12): r2..r5, g2..g5, C2..C5 <= 1e-12 relative.
A2: inputs/exact5/* (12 distinct cut4): raw r2..r5, g2..g5, C2..C5 and E_0^(5) = vac_raw[-1][5] at every file;
    at the even integer cutoffs (cut4 = 8, 16, 24, 32, 48, 64): C5 of g2D (= raw + dC5_g2D), g2D+g3W (+ bubble) and
    Dconn (= raw + dC5_Dconn), all <= 1e-12 relative; the bubble identity C5(g2D+g3W) - C5(g2D) = -2 dC4_g2D
    <= 1e-13 absolute; A4, B4, A5, B5 from the vac_conn jets (x = L, L-1/2, L-1) <= 1e-12 (absolute where |x| < 0.1).
Non-finite values fail.  The engine runs the production density kernels at Lmax = 17 (--reference: the dense
all-parity reference densities instead).
usage: python3 validate/v1_exact.py [--reference]"""
import glob
import json
import os
import sys
from fractions import Fraction as F

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import assemble5                     # noqa: E402
import windows5                      # noqa: E402
from lib5.series import Series5      # noqa: E402

INP = os.path.join(HERE, "..", "inputs")
TOL = 1e-12


def main():
    Lmax = 17
    res = assemble5.compute(Lmax, 5, verbose=False, reference="--reference" in sys.argv)
    ev = windows5.compute(16, {k: (v[: 4 * 16 + 1] if isinstance(v, np.ndarray) and v.ndim == 1 and len(v) == 4 * Lmax + 1
                                   else v) for k, v in res.items()}, Series5(16))
    evi = {int(L): i for i, L in enumerate(ev["L"])}
    worst, fails = {}, []

    def chk(tag, a, b, absfloor=0.0, tol=TOL):
        b = float(b)
        d = abs(a - b) / max(abs(b), absfloor) if np.isfinite(a) else np.inf
        if d > worst.get(tag, (0, None))[0] or tag not in worst:
            worst[tag] = (max(d, worst.get(tag, (0, None))[0]), None)
        if not d <= tol:
            fails.append(f"{tag}: {a!r} vs {b!r} ({d:.2e})")

    for e in json.load(open(os.path.join(INP, "exact_rational_validation.json"))):
        c = 4 * e["cutoff"]
        for k in (2, 3, 4, 5):
            chk(f"A1 r{k}", res[f"r{k}"][c], F(e["rational_r"][k]))
            chk(f"A1 g{k}", res[f"g{k}"][c], F(e["rational_g"][k]))
            chk(f"A1 C{k}", res[f"C{k}"][c], F(e["rational_C"][k]))
    files = sorted(glob.glob(os.path.join(INP, "exact5", "*_exact5_c*.json")))
    cuts = set()
    for f in files:
        d = json.load(open(f))
        c = d["cut4"]
        cuts.add(c)
        v = d["variants"]
        for k in (2, 3, 4, 5):
            for nm in ("r", "g", "C"):
                chk(f"A2 raw {nm}{k}", res[f"{nm}{k}"][c], F(v["raw"][nm][k]))
        chk("A2 E0^(5)", res["X5"][0][c], F(d["vac_raw"][-1][5]))
        if c % 8 == 0:
            L = c // 4
            i = evi[L]
            raw = res["C5"][c]
            chk("A2 g2D C5", raw + ev["dC5_g2D"][i], F(v["g2D"]["C"][5]))
            chk("A2 g2D+g3W C5", raw + ev["dC5_g2D"][i] + ev["dC5_bubble"][i], F(v["g2D+g3W"]["C"][5]))
            chk("A2 Dconn C5", ev["C5Dconn"][i], F(v["Dconn"]["C"][5]))
            chk("A2 Dconn C4", ev["C4Dconn"][i], F(v["Dconn"]["C"][4]))
            bub = F(v["g2D+g3W"]["C"][5]) - F(v["g2D"]["C"][5])
            chk("A2 bubble identity", ev["dC5_bubble"][i], bub, absfloor=1.0, tol=1e-13)
            vc = d["vac_conn"]               # x = i/2, i = 0..2L ; last = L, -2 = L - 1/2, -3 = L - 1
            for nm, k, j in (("A4", 4, -2), ("B4", 4, -3), ("A5", 5, -2), ("B5", 5, -3)):
                ref = F(vc[-1][k]) - F(vc[j][k])
                chk(f"A2 {nm}", ev[nm][i], ref, absfloor=0.1)
    print(f"A2 files: {len(files)}, distinct cut4: {sorted(cuts)}")
    for k, (v, _) in sorted(worst.items()):
        print(f"  worst {k:22s} {v:.2e}")
    ok = not fails and len(cuts) == 12
    for f in fails[:20]:
        print("FAIL", f)
    print("PASS" if ok else f"FAIL ({len(fails)} deviations)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
