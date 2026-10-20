#!/usr/bin/env python3
"""Validation of tagchan.py against the exact brute-force rationals (L = 2..16):
  delta^(3)(L)      vs delta3.py on ../results/tag/tag_L*_a1_phi2_2_real.json (L = 6..16) and the delta3 values that the
                    Wcs runs used (../ce_wc/out_wcs/wcs_L*.json meta.args.delta3, L = 2..16);
  c1tag^(3) - 2 r_3, c1tag^(2), c_1^(3)(l; L) for every l <= L, c_1^(3)(L), r_2, g_2 vs the tagged json files;
  single-leg charges (2,0), (0,2) vs tag_L*_a1_phi2_0_real.json / phi0_2_real.json.
usage: python3 validate_small.py [Lmax=16]  (writes results/validation_small.txt)"""
import glob
import json
import os
import sys
from fractions import Fraction as Fr

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import tagchan as tc  # noqa: E402
import delta3 as d3  # noqa: E402

Lmax = int(sys.argv[1]) if len(sys.argv) > 1 else 16
res = tc.run(Lmax, 1, 1, verbose=False, also_single=True)
out = []
worst = {}


def cmp(name, L, mine, exact):
    ex = float(exact)
    d = abs(mine - ex)
    rel = d / max(abs(ex), 1e-30)
    worst[name] = max(worst.get(name, 0.0), rel)
    out.append(f"  {name:22s} L={L:3d}  tagchan {mine:+.16e}  exact {ex:+.16e}  rel.diff {rel:.1e}")


# delta3 used by the Wcs runs
for f in sorted(glob.glob(os.path.join(HERE, "..", "ce_wc", "out_wcs", "wcs_L*.json")), key=lambda x: int(x.split("_L")[-1][:-5])):
    j = json.load(open(f))
    L = int(os.path.basename(f)[5:-5])
    if L > Lmax or L < 2:
        continue
    cmp("delta3 (Wcs meta)", L, res["delta3"][L // 2], Fr(j["meta"]["args"]["delta3"]))
for f in sorted(glob.glob(os.path.join(HERE, "..", "results", "tag", "tag_L*_a1_phi2_2_real.json")),
                key=lambda x: int(x.split("tag_L")[-1].split("_")[0])):
    j = json.load(open(f))
    L = j["L"]
    if L > Lmax:
        continue
    i = L // 2
    cmp("delta3 (delta3.py)", L, res["delta3"][i], d3.delta_from(j, 1))
    r3 = Fr(j["r"][3])
    cmp("c1tag3 - 2 r3", L, res["c1tag3"][i], Fr(j["phi2_2_real"]["c1tag"][3]) - 2 * r3)
    cmp("c1tag2", L, res["c1tag2"][i], Fr(j["phi2_2_real"]["c1tag"][2]))
    cmp("r2", L, res["r2"][i], Fr(j["r"][2]))
    cmp("g2", L, res["g2"][i], Fr(j["g"][2]))
    cmp("c1_3(L) Wc", L, res["c1_3_L"][i], Fr(j["c1_3L"]))
    c13 = [Fr(x) for x in j["c1_3"]]
    cmp("c1_3(L-2; L) Wc", L, res["c1_3_Lm2"][i], c13[-2])
    for k in ("phi2_0_real", "phi0_2_real"):
        g = os.path.join(HERE, "..", "results", "tag", f"tag_L{L}_a1_{k}.json")
        if os.path.exists(g):
            jj = json.load(open(g))
            key = "c1tag3_in" if k == "phi2_0_real" else "c1tag3_out"
            cmp(f"c1tag3 - 2r3 {k[:6]}", L, res[key][i], Fr(jj[k]["c1tag"][3]) - 2 * Fr(jj["r"][3]))
    cmp("c1tag3(0,0) = c1_3(L)", L, res["c1tag3_00"][i], Fr(j["c1_3L"]))
txt = "\n".join(out) + "\n\nworst relative difference by quantity:\n" + \
      "\n".join(f"  {k:24s} {v:.2e}" for k, v in worst.items())
print(txt)
open(os.path.join(HERE, "results", "validation_small.txt"), "w").write(txt + "\n")
