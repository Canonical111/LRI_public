#!/usr/bin/env python3
"""Read-only consistency check of the HT_Pert note.

1. numbers_d1.tex and sections/repro_d1.tex equal what tools/gen_numbers_d1.py and tools/gen_repro_d1.py generate from
   data/quoted_numbers_d1.json (regenerated in a temporary copy; nothing in the note is written).
2. Inside the public tree (HT_Pert/note next to HT_Pert/results/HT_1d): data/quoted_numbers_d1.json equals
   ../results/HT_1d/quoted_numbers.json byte for byte.
3. --checksums: every file listed in MANIFEST.json (if present) has the recorded sha256.
Exit 1 on any failure."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    bad = []
    with tempfile.TemporaryDirectory() as t:
        for d in ("tools", "data", "sections"):
            shutil.copytree(os.path.join(ROOT, d), os.path.join(t, d),
                            ignore=shutil.ignore_patterns("__pycache__"))
        for g in ("gen_numbers_d1.py", "gen_repro_d1.py"):
            subprocess.run([sys.executable, "-B", os.path.join(t, "tools", g)], check=True, capture_output=True)
        for rel in ("numbers_d1.tex", os.path.join("sections", "repro_d1.tex")):
            if sha(os.path.join(t, rel)) != sha(os.path.join(ROOT, rel)):
                bad.append(f"{rel} is not current (regenerate with make numbers)")
    pub = os.path.join(ROOT, "..", "results", "HT_1d", "quoted_numbers.json")
    if os.path.exists(pub):
        if sha(pub) != sha(os.path.join(ROOT, "data", "quoted_numbers_d1.json")):
            bad.append("data/quoted_numbers_d1.json differs from ../results/HT_1d/quoted_numbers.json")
        else:
            print("data/quoted_numbers_d1.json equals ../results/HT_1d/quoted_numbers.json")
    else:
        print("public results folder not found (outside the public tree): step 2 skipped")
    if "--checksums" in sys.argv:
        man = os.path.join(ROOT, "MANIFEST.json")
        if os.path.exists(man):
            files = json.load(open(man))["files"]
            for rel, h in files.items():
                if not os.path.exists(os.path.join(ROOT, rel)) or sha(os.path.join(ROOT, rel)) != h:
                    bad.append(f"MANIFEST mismatch: {rel}")
            print(f"MANIFEST.json: {len(files)} files checked")
        else:
            print("MANIFEST.json absent (written by the maintainer at export)")
    for b in bad:
        print("FAIL:", b)
    print("check_note: " + ("FAIL" if bad else "PASS"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
