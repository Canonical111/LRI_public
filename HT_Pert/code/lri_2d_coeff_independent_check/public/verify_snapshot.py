#!/usr/bin/env python3
"""Check public/SNAPSHOT.sha256 (every file of the snapshot with its sha256 as exported) in SCRUBBED.txt mode.

Files listed in public/SCRUBBED.txt (one path per line relative to this package, '#' comments allowed) were scrubbed
for publication (machine paths and names replaced by tokens); for them only presence is checked. Every other listed
file must be byte-identical. Run from HT_Pert/code/lri_2d_coeff_independent_check. Exit 1 on any failure."""
import hashlib
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent


def main():
    scr = PKG / "public" / "SCRUBBED.txt"
    scrubbed = set()
    if scr.exists():
        scrubbed = {x.split("  ", 1)[-1].strip() for x in scr.read_text().splitlines() if x.strip() and not x.startswith("#")}
    n = bad = skipped = 0
    for line in (PKG / "public" / "SNAPSHOT.sha256").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        h, rel = line.split("  ", 1)
        p = PKG / rel
        n += 1
        if not p.is_file():
            print("MISSING", rel)
            bad += 1
        elif rel in scrubbed:
            skipped += 1
        elif hashlib.sha256(p.read_bytes()).hexdigest() != h:
            print("DIFFERS", rel)
            bad += 1
    print(f"verify_snapshot: {n} listed, {n - bad - skipped} byte-identical, {skipped} scrubbed (present), {bad} failures")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
