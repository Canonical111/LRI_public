#!/usr/bin/env python3
"""Checksum check of the S10 package (HT_Pert/code/lri_d1_full_coefficient_flow) that honours public/SCRUBBED.txt.

MANIFEST.sha256 (shipped verbatim, 85 entries) lists every file of the package as it was at the production commit
fec60a2. tests/verify_manifest.py checks it bitwise. In the public tree a few of those files may have had cluster paths
replaced by placeholders (they are then listed in public/SCRUBBED.txt by the maintainer's scrub). This check:
  * a listed file whose sha256 matches          -> ok
  * a listed file in SCRUBBED.txt that differs   -> reported as 'scrubbed' (accepted)
  * any other mismatch or missing file           -> FAIL (exit 1)
The production solver code/ragged_quotient.py is bound by the production records (provenance.code_sha256); it must
match even if listed in SCRUBBED.txt.
usage: python3 public/verify_manifest_public.py"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
RECORD_BOUND = {"code/ragged_quotient.py"}


def scrubbed():
    p = os.path.join(HERE, "SCRUBBED.txt")
    if not os.path.exists(p):
        return set()
    return {ln.strip() for ln in open(p) if ln.strip() and not ln.startswith("#")}


def main():
    scr = scrubbed()
    rows = [ln for ln in open(os.path.join(PKG, "MANIFEST.sha256")).read().splitlines() if ln.strip()]
    ok, sc, bad = 0, [], []
    for ln in rows:
        exp, rel = ln.split("  ", 1)
        p = os.path.join(PKG, rel)
        if not os.path.isfile(p):
            bad.append(f"{rel} (missing)")
            continue
        got = hashlib.sha256(open(p, "rb").read()).hexdigest()
        if got == exp:
            ok += 1
        elif rel in scr and rel not in RECORD_BOUND:
            sc.append(rel)
        else:
            bad.append(rel)
    print(f"MANIFEST.sha256: {len(rows)} entries, {ok} match, {len(sc)} scrubbed {sc}, {len(bad)} bad {bad}")
    print("verify_manifest_public", "PASS" if not bad else "FAIL")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
