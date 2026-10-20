#!/usr/bin/env python3
"""Verify the release's SHA-256 manifest. Does not alter inputs or outputs."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    manifest = ROOT / "MANIFEST.sha256"
    if not manifest.is_file():
        print("Manifest not found.", file=sys.stderr)
        return 2
    failed = []
    count = 0
    for line in manifest.read_text().splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        target = (ROOT / relative).resolve()
        if not target.is_relative_to(ROOT):
            failed.append((relative, "unsafe path"))
            continue
        if not target.is_file():
            failed.append((relative, "missing"))
        elif hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            failed.append((relative, "hash mismatch"))
        count += 1
    if failed:
        for path, reason in failed:
            print(f"FAIL: {path}: {reason}", file=sys.stderr)
        return 1
    print(f"PASS: all {count} listed files match MANIFEST.sha256")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
