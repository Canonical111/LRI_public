#!/usr/bin/env python3
"""Check (c): exact comparison of ce_fraction.py (independent Fraction implementation) with ce_run.py (modular):
every C_n, r_n, g_n, E_p^(n) and every descendant energy E_d^(n), n = 0..8.
usage: python3 compare_frac_mod.py frac.json mod.json [mod2.json ...]"""
import json, sys
from fractions import Fraction as Fr


def main():
    fr = json.load(open(sys.argv[1]))
    mods = {}
    for fn in sys.argv[2:]:
        d = json.load(open(fn))
        for s, blk in d["schemes"].items():
            if not s.startswith("_"):
                mods.setdefault(s, blk["values"])
    tot_bad = 0
    for s, res in fr["schemes"].items():
        if s not in mods:
            print(f"L={fr['L']} {s}: no modular result")
            continue
        m = mods[s]
        n, bad = 0, []
        for k in ("C", "r", "g"):
            for i, x in enumerate(res[k]):
                n += 1
                if Fr(x) != Fr(m[f"{k}|{i}"]):
                    bad.append(f"{k}{i}")
        for p, row in enumerate(res["E"]):
            for i, x in enumerate(row):
                n += 1
                if Fr(x) != Fr(m[f"E|{p}|{i}"]):
                    bad.append(f"E{p}^{i}")
        for dn, row in res["Edesc"].items():
            for i, x in enumerate(row):
                n += 1
                mv = m.get(f"Ed|{dn}|{i}")
                if mv is None or Fr(x) != Fr(mv):
                    bad.append(f"{dn}^{i}")
        tot_bad += len(bad)
        print(f"L={fr['L']} {s}: {n} exact quantities compared, {len(bad)} differ {bad[:8]}")
    print("ALL IDENTICAL" if tot_bad == 0 else "DIFFERENCES FOUND")


if __name__ == "__main__":
    main()
