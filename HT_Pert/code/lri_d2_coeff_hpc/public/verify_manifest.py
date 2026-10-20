#!/usr/bin/env python3
"""Check the three checksum lists (MANIFEST.sha256 of the package, of reference/lri_d2_perturbative_C8 and of its
upstream/lri_2d_hpc_optimized) in SCRUBBED.txt mode.

The package's own tests/verify_manifest.py requires every listed file to be byte-identical. In the public tree a few
listed files may have been scrubbed (machine paths, allocation names; listed in public/SCRUBBED.txt, one path per line
relative to this folder, '#' comments allowed). For those files this script checks only that they exist; every other
listed file must match its sha256. Run from HT_Pert/code/lri_d2_coeff_hpc. Exit 1 on any mismatch."""
import hashlib
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent


def scrubbed():
    p = PKG / "public" / "SCRUBBED.txt"
    if not p.exists():
        return set()
    return {x.split("  ", 1)[-1].strip() for x in p.read_text().splitlines() if x.strip() and not x.startswith("#")}


def main():
    scr = scrubbed()
    total = bad = skipped = 0
    up = "reference/lri_d2_perturbative_C8/upstream/lri_2d_hpc_optimized"
    for man, base in ((PKG / "MANIFEST.sha256", PKG),
                      (PKG / "reference/lri_d2_perturbative_C8/MANIFEST.sha256", PKG / "reference/lri_d2_perturbative_C8"),
                      (PKG / up / "MANIFEST.sha256", PKG / up)):
        for line in man.read_text().splitlines():
            if not line.strip():
                continue
            h, rel = line.split("  ", 1)
            p = (base / rel).resolve()
            relpkg = str(p.relative_to(PKG))
            total += 1
            if not p.is_file():
                print("MISSING", relpkg)
                bad += 1
            elif relpkg in scr:
                skipped += 1
            elif hashlib.sha256(p.read_bytes()).hexdigest() != h:
                print("DIFFERS", relpkg)
                bad += 1
    print(f"verify_manifest: {total} listed, {total - bad - skipped} byte-identical, {skipped} scrubbed (present), {bad} failures")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
