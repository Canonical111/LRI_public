#!/usr/bin/env python3
"""
compare_c8_production.py -- SEALED comparison of out/C8_production.json with the note's numbers
(phase 3, 2026-10-03).  COMPARISON ONLY; nothing here feeds back into any result.

Refuses to run unless out/C8_production.json exists and matches the SHA-256 recorded by c8_production.py
when it was written; records that hash and the file's time in the output.  The claims are read from the
note's TeX (read-only):
  B_old  "Its full numerical value is -861.6635672354797792014971909923..."  (after eq:C8assembly)
  W      table of Sec. fullpackages, "-37.708111514952555..."
  B_done eq. in Sec. C8full, "563.404066124777663118309147204616..."   (not testable yet: listed only)
Writes out/C8_production_comparison.json and out/compare_c8_production.log.
"""
import hashlib
import json
import os
import re
import sys
import time

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
OURS = os.path.join(OUT, "C8_production.json")
NOTE = os.path.normpath(os.path.join(HERE, "..", "..", "LRI_SRI_research_compendium", "note",
                                     "LRI_perturbation_compendium.tex"))
mp.mp.dps = 40


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def claims():
    tex = open(NOTE).read()
    k = tex.index("\\label{eq:C8assembly}")
    m = re.search(r"Its full numerical value is \$(-?[0-9.]+)\\ldots", tex[k:])
    bold = m.group(1)
    m = re.search(r"\$W\$&\$(-?[0-9.]+)\\ldots\$&\$168\$", tex)
    w = m.group(1)
    m = re.search(r"B_\{\\rm done\}=(-?[0-9.]+)\\ldots", tex)
    bdone = m.group(1)
    return {"B_old": bold, "W": w, "B_done": bdone}


def main():
    if not os.path.exists(OURS) or not os.path.exists(OURS + ".sha256"):
        print("refusing: out/C8_production.json (and its .sha256) must be written first by c8_production.py")
        return 2
    h = sha256(OURS)
    rec = open(OURS + ".sha256").read().split()
    if rec[0] != h:
        print(f"refusing: out/C8_production.json changed after it was sealed ({h} != {rec[0]})")
        return 2
    ours = json.load(open(OURS))
    cl = claims()
    log = [f"sealed results: out/C8_production.json sha256 {h}, written {ours['date']} "
           f"(file mtime {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(OURS)))})",
           f"comparison run {time.strftime('%Y-%m-%d %H:%M:%S')}; claims parsed from {os.path.relpath(NOTE, HERE)}"]
    res = {"sealed_results": {"file": "out/C8_production.json", "sha256": h, "written": ours["date"]},
           "claims_from_note": cl, "comparisons": {}}
    b, s = mp.mpf(ours["B_old"]["value"]), mp.mpf(ours["B_old"]["sigma"])
    d = b - mp.mpf(cl["B_old"])
    res["comparisons"]["B_old"] = {
        "ours": ours["B_old"]["value"], "claim": cl["B_old"], "difference": mp.nstr(d, 6),
        "sigma": ours["B_old"]["sigma"], "pull": mp.nstr(d / s, 3),
        "pull_by_estimator": {k: mp.nstr(d / mp.mpf(ours["B_old"][k]), 3) for k in ("sigma_cov", "sigma_rep", "sigma_pool")},
        "relative_difference": mp.nstr(d / abs(mp.mpf(cl["B_old"])), 3)}
    w = mp.mpf(ours["W_semi_analytic"]["value"])
    dw = w - mp.mpf(cl["W"])
    res["comparisons"]["W"] = {"ours": ours["W_semi_analytic"]["value"], "claim": cl["W"], "difference": mp.nstr(dw, 4),
                               "note_digits": len(cl["W"].split(".")[1]),
                               "verdict": "agree to the note's printed digits" if abs(dw) < mp.mpf(10) ** -14 else "DIFFER"}
    part = mp.mpf(ours["C8_partial"]["value"])
    cpart = mp.mpf(cl["B_old"]) + 4 * mp.mpf(cl["W"])
    res["comparisons"]["B_old_plus_4W"] = {"ours": ours["C8_partial"]["value"], "claim_from_note_values": mp.nstr(cpart, 20),
                                           "difference": mp.nstr(part - cpart, 6),
                                           "pull": mp.nstr((part - cpart) / s, 3)}
    res["not_testable_yet"] = {"B_done": {"claim": cl["B_done"],
                                          "needs": ours["B_done"]["needs"],
                                          "claim_minus_claimed_B_old_minus_4W": mp.nstr(
                                              mp.mpf(cl["B_done"]) - cpart, 20)},
                               "C8": {"needs": ours["C8"]["needs"]}}
    for k, v in res["comparisons"].items():
        log.append(f"{k}: {json.dumps(v)}")
    log.append(f"not testable yet: {json.dumps(res['not_testable_yet'])}")
    print("\n".join(log))
    with open(os.path.join(OUT, "C8_production_comparison.json"), "w") as f:
        json.dump(res, f, indent=1)
    with open(os.path.join(OUT, "compare_c8_production.log"), "w") as f:
        f.write("\n".join(log) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
