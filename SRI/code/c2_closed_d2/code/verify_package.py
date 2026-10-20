#!/usr/bin/env python3
"""Check the SHA-256 inventory of the distributed C2 package (standard library only).

Run before regenerating outputs; a deliberate rerun can change timing metadata
and PDF bytes. Newly generated troubleshooting logs are ignored by this check.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    entries = json.loads((ROOT / "MANIFEST.json").read_text())["files"]
    failures = []
    for relative, expected in entries.items():
        path = ROOT / relative
        if not path.is_file():
            failures.append(f"missing: {relative}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected["sha256"]:
            failures.append(f"changed: {relative}")
    if failures:
        print("\n".join(failures))
        return 1
    print(f"PASS: all {len(entries)} distributed files match their SHA-256 digests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
