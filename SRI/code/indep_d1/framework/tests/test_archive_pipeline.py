#!/usr/bin/env python3
"""
END-TO-END PIPELINE TEST ON ARCHIVE DATA -- COMPARISON ONLY.
Feeds the archive-derived raw coefficients extracted by the spec agent
(../spec/out/archive_raw_coefficients.json; archive numbers, NOT our integration) through
lri_framework.py.  Purpose: test the module's normalization / recurrence / invariant layers on
realistic data and compare our exact internal two-kink sector with the archived two-kink
coefficients.  These numbers are NOT an independent re-derivation of the inputs.
"""
import json
import os
import sys

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import lri_framework as L  # noqa: E402

# the spec agent keeps its archive-derived files in spec/comparison/ (spec/out/ in phase 1)
SRC = next((p for p in (os.path.join(ROOT, "..", "spec", d, "archive_raw_coefficients.json")
                        for d in ("comparison", "out")) if os.path.exists(p)),
           os.path.join(ROOT, "..", "spec", "comparison", "archive_raw_coefficients.json"))
# The archive-derived file has no entry for these three required scalars (the archive's exact series
# contain no such term).  Strict mode never treats them as zero by itself, so they are declared exact
# zeros here, explicitly (the engine's pole analysis also finds no such term).
ARCHIVE_ABSENT_ZEROS = ["A3[eps^-1 l^1]", "A3[eps^2 l^1]", "Z4[eps^-2 l^1]"]


def main():
    if not os.path.exists(SRC):
        print("archive-derived raw file not available; skipping")
        return True
    mp.mp.dps = 60      # the comparison arithmetic below (the framework itself no longer sets it globally)
    fw = L.Framework("D4", dps=60)
    data = L.merge_inputs([L.load_inputs(SRC)], zeros=ARCHIVE_ABSENT_ZEROS)
    res = fw.from_raw(data)                     # strict: every other required scalar is in the file
    _, tgt = L.closed_forms(60)
    arch = json.load(open("<PROJECT>/LRI_SRI_research_compendium/data/archived/"
                          "C8_full_numerical_completion/data/F3_final_100.json"))["values"]
    ok = True
    out = {"note": "COMPARISON ONLY: archive raw coefficients through our pipeline", "beta": {}, "claims": {}}
    worst = 0
    for nm in fw.beta_names:
        x = res.beta[nm]
        if x.is_missing:
            ok = False
            print("MISSING", nm)
            continue
        d = x.v - mp.mpf(arch["beta_" + nm])
        worst = max(worst, abs(d) / (1 + abs(x.v)))
        out["beta"][nm] = {"value": mp.nstr(x.v, 50), "minus_archived_input": mp.nstr(d, 4)}
    print("25 inputs vs archived inputs: worst rel. diff", mp.nstr(worst, 3))
    ok &= worst < mp.mpf(10) ** -35
    for key in ("D2", "T2", "D3", "T3", "D4"):
        d = res.inv[key].v - tgt[key]
        out["claims"][key] = mp.nstr(d, 4)
        ok &= abs(d) < mp.mpf(10) ** -50
    for n in range(3, 8):
        d = res.C[n].v - tgt[f"C{n}"]
        out["claims"][f"C{n}"] = mp.nstr(d, 4)
        ok &= abs(d) < mp.mpf(10) ** -50
    print("differences from claimed closed forms:", out["claims"])
    chk = {k: mp.nstr(v, 3) for k, v in fw.two_kink_check.items()}
    out["two_kink_internal_vs_archive_maxreldiff"] = chk
    print("internal exact two-kink sector vs archived two-kink coefficients (max rel. diff):")
    for k, v in sorted(chk.items()):
        print(f"   {k:10s} {v}")
    big = [w for w in fw.warnings if w.startswith("supplied")]
    print("two-kink disagreements:", big if big else "none")
    ok &= not big
    json.dump(out, open(os.path.join(HERE, "archive_comparison", "result_on_archive_raw.json"), "w"), indent=1)
    print("ARCHIVE PIPELINE TEST", "PASSED" if ok else "FAILED")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
