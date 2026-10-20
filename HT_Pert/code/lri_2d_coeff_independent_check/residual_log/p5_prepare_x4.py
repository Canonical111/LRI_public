#!/usr/bin/env python3
"""Phase 5 (README Sec. 12): from the spectator-response runs (results/tag/spec4_L*_a1.json, brute_desc_chi4.py --spec)
write ce_wc/x4/x4_L<L>.json = {N: X4(L, N)} (X4 = Delta c1chi^(4)(L, N) - Delta c_1^(4)(L, N), N = 2..L) and print the
RUNS string 'L:delta3:delta4chi_B' for jobs/run_ce_wcs4x.sbatch, with delta4chi_B = delta4chi - X4(L, 2)/4 (the leg
coefficient recalibrated on chi_11 once the uniform part uses c1chi).  usage: python3 p5_prepare_x4.py"""
import glob
import json
import os
from fractions import Fraction as Fr

import delta4chi as d4c

HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, "ce_wc", "x4"), exist_ok=True)
rows = {L: (d3, d4) for L, d3, d4, bf, rw in d4c.table(1)}
runs = []
for f in sorted(glob.glob(os.path.join(HERE, "results", "tag", "spec4_L*_a1.json")),
                key=lambda s: int(os.path.basename(s).split("_L")[1].split("_")[0])):
    j = json.load(open(f))
    L = j["L"]
    x4 = {N: j["spec"][f"{N}_4"]["X"] for N in range(2, L + 1, 2) if f"{N}_4" in j["spec"]}
    if len(x4) != L // 2 or L not in rows:
        print(f"# L={L}: incomplete ({len(x4)} of {L // 2} charges) or no delta4chi; skipped")
        continue
    json.dump(x4, open(os.path.join(HERE, "ce_wc", "x4", f"x4_L{L}.json"), "w"), indent=1)
    d3, d4 = rows[L]
    d4b = d4 - Fr(x4[2]) / 4
    runs.append(f"{L}:{d3}:{d4b}")
    print(f"# L={L}: X4(L,2) = {float(Fr(x4[2])):+.6f}  X4(L,4) = {float(Fr(x4.get(4, 0))):+.6f}  delta4chi = "
          f"{float(d4):+.6f}  delta4chi_B = {float(d4b):+.6f}")
print(" ".join(runs))
