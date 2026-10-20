#!/usr/bin/env python3
"""delta^(3)(L) of WINDOW_SPEC Sec. 2.5a from the zero-mode-tagged phi channel (brute_desc_tag.py, exact):
    delta^(3)(L) = (1/4) [ c_1^(3)(L - 2) - c1tag^(3)(L; 2, 2) ],
both on the footing of the window functions (r_3 removed: c1tag^(3) -> c1tag^(3) - 2 r_3, so that c1tag(L; 0, 0) =
c_1^(3)(L)).  With --a, also the exact chi_aa form (1/(4a)) [c_1^(3)(L - 2a) - c1tag^(3)(L; 2a, 2a)].
usage: python3 delta3.py results/tag/tag_L10_a1_phi2_2_real.json   (or --run L for small L)"""
import json
import sys
from fractions import Fraction as Fr


def delta_from(d, a=1):
    k = f"phi{2 * a}_{2 * a}_real"
    L = d["L"]
    c1 = [Fr(x) for x in d["c1_3"]]
    ls = list(range(0, L + 1, 2))
    r3 = Fr(d["r"][3])
    tag = Fr(d[k]["c1tag"][3]) - 2 * r3
    return (c1[ls.index(L - 2 * a)] - tag) / (4 * a)


if __name__ == "__main__":
    if sys.argv[1] == "--run":
        import brute_desc_tag as bt
        L = int(sys.argv[2])
        d = bt.run(L, 1, [], [(2, 2, "real")], verbose=False)
    else:
        d = json.load(open(sys.argv[1]))
    a = int(d.get("a", 1)) if sys.argv[1] != "--run" else 1
    v = delta_from(d, a)
    print(d["L"], a, v, float(v))
